<script>
	import { tick } from 'svelte';
	import { beforeNavigate } from '$app/navigation';
	import { post, errorMessage } from '$lib/api.js';
	import {
		validateMoney,
		formatMoney,
		formatSigned,
		moneyClass,
		centsToInput
	} from '$lib/money.js';
	import { localeTag, t } from '$lib/i18n.svelte.js';
	import { toast, setBottomGap } from '$lib/toast.svelte.js';

	/**
	 * The "night sheet": date/place/roster as chips, one labelled money row per selected
	 * player, running remainder + save in a sticky bar. Optimized for one thumb at the table.
	 * `onsubmit` returning `false` means "not saved" — the draft stays put; see `doSubmit`.
	 * @type {{
	 *   groupId: number|string,
	 *   catalogs: { participants: import('$lib/types.js').Participant[], places: import('$lib/types.js').Named[] },
	 *   night?: import('$lib/types.js').Night|null,
	 *   lastNight?: import('$lib/types.js').Night|null,
	 *   editing?: boolean,
	 *   saving?: boolean,
	 *   onsubmit: (payload: import('$lib/types.js').NightPayload) => unknown,
	 *   oncancel: () => void
	 * }}
	 */
	let {
		groupId,
		catalogs,
		night = null,
		lastNight = null,
		editing = false,
		saving = false,
		onsubmit,
		oncancel
	} = $props();

	// ---------- date ----------
	/** Local date, not UTC: toISOString() would roll over to tomorrow after 21h no Brasil. */
	/** @param {Date} d */
	function ymd(d) {
		return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(
			d.getDate()
		).padStart(2, '0')}`;
	}
	const now = new Date();
	const today = ymd(now);
	const yesterday = ymd(new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1));

	// The sheet is a draft seeded from `night`/`lastNight`/`catalogs` and then owned by the user;
	// every `$state(...)` below reads those props exactly once, on purpose. Tracking them would
	// throw away half-entered amounts whenever the parent refetched.
	// svelte-ignore state_referenced_locally
	let date = $state(night?.date ?? today);
	// Reveal the native picker only when the date isn't one of the two chips.
	// svelte-ignore state_referenced_locally
	let showDateInput = $state(!!night?.date && night.date !== today && night.date !== yesterday);

	// ---------- place ----------
	// svelte-ignore state_referenced_locally
	let places = $state([...catalogs.places]);
	// New nights inherit the last night's place — the group almost always plays in the same spot.
	/** `''` is the "no place" chip; a number is a place id. */
	// svelte-ignore state_referenced_locally
	let place_id = $state(
		/** @type {number|''} */ (night ? (night.place_id ?? '') : (lastNight?.place_id ?? ''))
	);
	let newPlace = $state('');
	let addingPlace = $state(false);
	let showNewPlace = $state(false);

	// ---------- roster ----------
	// svelte-ignore state_referenced_locally
	let participants = $state([...catalogs.participants]);
	let newParticipant = $state('');
	let addingParticipant = $state(false);

	/**
	 * One money row: the amounts stay as the raw input strings until save, so a half-typed
	 * "1.2" survives a re-render instead of being rounded out from under the cursor.
	 * @typedef {{ participant_id: number, buy_in: string, cash_out: string }} Row
	 */

	/** One row per player at the table, in selection order. @type {Row[]} */
	// svelte-ignore state_referenced_locally
	let rows = $state(
		(night?.entries ?? []).map((e) => ({
			participant_id: e.participant_id,
			buy_in: centsToInput(e.buy_in_cents),
			cash_out: centsToInput(e.cash_out_cents)
		}))
	);

	const nameById = $derived(new Map(participants.map((p) => [p.id, p.name])));
	const selectedIds = $derived(new Set(rows.map((r) => r.participant_id)));

	/** Active players, plus anyone already in the sheet (an edited night may hold inactive ones). */
	const rosterChips = $derived(participants.filter((p) => p.active || selectedIds.has(p.id)));

	/** Lineup of the reference night, for "same table as last night". */
	const lastLineup = $derived(
		editing || !lastNight ? [] : (lastNight.entries ?? []).map((e) => e.participant_id)
	);
	const lastLineupMissing = $derived(lastLineup.filter((id) => !selectedIds.has(id)));

	// ---------- standard buy-in ----------
	/**
	 * Most common buy-in of a night — the group's de-facto standard.
	 * @param {import('$lib/types.js').Night|null} n
	 * @returns {number|null}
	 */
	function standardBuyIn(n) {
		/** buy-in cents -> how many players paid it. @type {Map<number, number>} */
		const counts = new Map();
		for (const e of n?.entries ?? []) {
			if (!e.buy_in_cents) continue;
			counts.set(e.buy_in_cents, (counts.get(e.buy_in_cents) ?? 0) + 1);
		}
		let best = null;
		let bestCount = 0;
		for (const [amount, count] of counts) {
			// Ties go to the smaller amount: the table's floor is the likelier standard.
			if (count > bestCount || (count === bestCount && best !== null && amount < best)) {
				best = amount;
				bestCount = count;
			}
		}
		return best;
	}

	// When editing, the night's own values are the better reference than some other night's.
	const historyDefault = $derived(standardBuyIn(editing ? night : lastNight));
	// No history at all: the first buy-in typed tonight becomes tonight's default.
	let typedDefault = $state(/** @type {number|null} */ (null));
	const defaultBuyIn = $derived(historyDefault ?? typedDefault);

	/**
	 * With no history, tonight's first buy-in sets tonight's default. Read on `change`
	 * (blur/Enter), not on every keystroke — "5" on the way to "50" is not a default.
	 */
	/** @param {string} value */
	function rememberTypedDefault(value) {
		if (historyDefault !== null || typedDefault !== null) return;
		const amount = validateMoney(value);
		if (amount) typedDefault = amount;
	}

	// ---------- money ----------
	/** @param {string} v */
	const cents = (v) => validateMoney(v) ?? 0;
	/** @param {string} v */
	const bad = (v) => validateMoney(v) === null;

	const potCents = $derived(rows.reduce((s, r) => s + cents(r.buy_in), 0));
	const paidOutCents = $derived(rows.reduce((s, r) => s + cents(r.cash_out), 0));
	/** What's still on the table: buy-ins minus everything handed back. */
	const remainderCents = $derived(potCents - paidOutCents);
	const balanced = $derived(remainderCents === 0);
	/** Balanced *and* with money on the table — an untouched sheet isn't a closed pot. */
	const closed = $derived(balanced && potCents > 0);
	const hasInvalid = $derived(rows.some((r) => bad(r.buy_in) || bad(r.cash_out)));

	/** @param {string} v */
	function isBlank(v) {
		return String(v ?? '').trim() === '';
	}
	/** @param {Row} r */
	function touched(r) {
		return !isBlank(r.buy_in) || !isBlank(r.cash_out);
	}
	/** @param {Row} r */
	function profitOf(r) {
		return cents(r.cash_out) - cents(r.buy_in);
	}
	/**
	 * How many default buy-ins this total is, when it's a clean multiple (0 = don't annotate).
	 * @param {Row} r
	 */
	function rebuyCount(r) {
		const unit = defaultBuyIn;
		const total = validateMoney(r.buy_in);
		if (!unit || !total || total % unit !== 0) return 0;
		const n = total / unit;
		return n >= 2 ? n : 0;
	}

	/** Index of the single player still missing a cash-out, when the rest is settled. */
	const suggestIndex = $derived.by(() => {
		if (remainderCents <= 0) return -1;
		const empty = rows.reduce(
			(acc, r, i) => (isBlank(r.cash_out) ? [...acc, i] : acc),
			/** @type {number[]} */ ([])
		);
		return empty.length === 1 ? empty[0] : -1;
	});

	// ---------- actions ----------
	/** @param {string} value */
	function pickDate(value) {
		date = value;
		showDateInput = false;
	}

	/** @param {number} id */
	function togglePlayer(id) {
		if (selectedIds.has(id)) {
			rows = rows.filter((r) => r.participant_id !== id);
			return;
		}
		rows = [
			...rows,
			{ participant_id: id, buy_in: defaultBuyIn ? centsToInput(defaultBuyIn) : '', cash_out: '' }
		];
	}

	/** Additive on purpose: seeds the usual table, the user keeps tapping from there. */
	function sameTableAsLastNight() {
		const extra = lastLineupMissing.map((id) => ({
			participant_id: id,
			buy_in: defaultBuyIn ? centsToInput(defaultBuyIn) : '',
			cash_out: ''
		}));
		rows = [...rows, ...extra];
	}

	/** @param {number} i */
	function rebuy(i) {
		const unit = defaultBuyIn;
		if (!unit) return;
		const total = validateMoney(rows[i].buy_in);
		if (total === null) return; // don't clobber something we can't read
		rows[i].buy_in = centsToInput(total + unit);
	}

	/** @param {number} i */
	function fillRemainder(i) {
		rows[i].cash_out = centsToInput(remainderCents);
	}

	async function addParticipant() {
		const name = newParticipant.trim();
		if (!name) return;
		addingParticipant = true;
		try {
			const p = await post(`/groups/${groupId}/participants`, { name });
			participants = [...participants, { id: p.id, name: p.name, active: true }].sort((a, b) =>
				a.name.localeCompare(b.name)
			);
			newParticipant = '';
			if (!selectedIds.has(p.id)) togglePlayer(p.id); // quick-create means "they're playing"
		} catch (e) {
			// A side quest, not a save: keep the form banner for what blocks the save.
			toast.error(errorMessage(e));
		} finally {
			addingParticipant = false;
		}
	}

	async function addPlace() {
		const name = newPlace.trim();
		if (!name) return;
		addingPlace = true;
		try {
			const p = await post(`/groups/${groupId}/places`, { name });
			places = [...places, p].sort((a, b) => a.name.localeCompare(b.name));
			place_id = p.id;
			newPlace = '';
			showNewPlace = false;
		} catch (e) {
			toast.error(errorMessage(e));
		} finally {
			addingPlace = false;
		}
	}

	/**
	 * Enter never submits the night: move to the next field instead.
	 * @param {KeyboardEvent & { currentTarget: HTMLInputElement }} ev
	 */
	function enterNext(ev) {
		if (ev.key !== 'Enter') return;
		ev.preventDefault();
		const el = ev.currentTarget;
		const form = el.form;
		if (!form) return;
		const fields = /** @type {(HTMLInputElement|HTMLSelectElement)[]} */ ([
			...form.querySelectorAll('input, select')
		]).filter((f) => !f.disabled);
		fields[fields.indexOf(el) + 1]?.focus();
	}

	/** @type {HTMLDivElement|undefined} */
	let barEl = $state();

	// ---------- draft ----------
	// Deliberately not reactive: the key a draft was saved under has to stay the key it's read
	// back and cleared under, for the whole life of this form.
	// svelte-ignore state_referenced_locally
	const draftKey = editing
		? `pokerdex.draft.night.edit.${night?.id}`
		: `pokerdex.draft.night.${groupId}`;

	function formState() {
		return {
			date,
			showDateInput,
			place_id,
			typedDefault,
			rows: rows.map((r) => ({ ...r }))
		};
	}

	const stateJson = $derived(JSON.stringify(formState()));
	const pristineJson = JSON.stringify(formState());
	const dirty = $derived(stateJson !== pristineJson);

	/** @type {{savedAt: string, state: any}|null} */
	let draftPrompt = $state(readDraft());
	let submitting = $state(false);
	let formError = $state('');
	let confirming = $state(false);
	/** @type {HTMLButtonElement|undefined} */
	let confirmButton = $state();

	function readDraft() {
		try {
			const raw = localStorage.getItem(draftKey);
			if (!raw) return null;
			const parsed = JSON.parse(raw);
			return parsed?.state ? parsed : null;
		} catch {
			return null; // storage blocked or garbage — no draft, no drama
		}
	}

	function clearDraft() {
		try {
			localStorage.removeItem(draftKey);
		} catch {
			// nothing to do; the draft just lingers
		}
	}

	function restoreDraft() {
		const s = draftPrompt?.state;
		draftPrompt = null;
		if (!s) return;
		date = s.date ?? date;
		showDateInput = !!s.showDateInput;
		place_id = s.place_id ?? '';
		typedDefault = s.typedDefault ?? null;
		rows = (s.rows ?? []).map((/** @type {Row} */ r) => ({
			participant_id: r.participant_id,
			buy_in: r.buy_in ?? '',
			cash_out: r.cash_out ?? ''
		}));
	}

	function discardDraft() {
		draftPrompt = null;
		clearDraft();
	}

	// Debounced autosave. Never while the restore banner is up: that would overwrite
	// the very draft we're offering.
	$effect(() => {
		const json = stateJson;
		if (!dirty || draftPrompt || submitting) return;
		const timer = setTimeout(() => {
			try {
				localStorage.setItem(
					draftKey,
					JSON.stringify({ savedAt: new Date().toISOString(), state: JSON.parse(json) })
				);
			} catch {
				// private mode / quota — the form still works, just without a safety net
			}
		}, 500);
		return () => clearTimeout(timer);
	});

	// Any edit invalidates a pending "save unbalanced?" confirmation.
	$effect(() => {
		stateJson;
		confirming = false;
	});

	$effect(() => {
		if (confirming) tick().then(() => confirmButton?.focus());
	});

	/** @param {string} iso */
	function draftDate(iso) {
		const d = new Date(iso);
		if (Number.isNaN(d.getTime())) return iso;
		return d.toLocaleString(localeTag(), {
			day: '2-digit',
			month: 'short',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	/**
	 * Keep toasts clear of the sticky bar. What matters is the bar's distance from the *viewport
	 * bottom*, not its height: sticky stops at the end of the form, so the bar can sit above the
	 * fold — and it reflows to two rows below 420px. Hence measuring instead of a constant.
	 */
	$effect(() => {
		const el = barEl;
		if (!el) return;
		const update = () => setBottomGap(window.innerHeight - el.getBoundingClientRect().top);
		update();
		const ro = new ResizeObserver(update);
		ro.observe(el);
		window.addEventListener('scroll', update, { passive: true });
		window.addEventListener('resize', update);
		return () => {
			ro.disconnect();
			window.removeEventListener('scroll', update);
			window.removeEventListener('resize', update);
			setBottomGap(0);
		};
	});

	beforeNavigate((nav) => {
		if (!dirty || submitting) return;
		if (!confirm(t('night.leaveConfirm'))) nav.cancel();
	});

	/** @param {BeforeUnloadEvent} ev */
	function onBeforeUnload(ev) {
		if (!dirty || submitting) return;
		ev.preventDefault();
		ev.returnValue = '';
	}

	// ---------- save ----------
	/** @param {SubmitEvent} ev */
	function submit(ev) {
		ev.preventDefault();
		formError = '';
		if (hasInvalid) {
			formError = t('night.fixAmounts');
			return;
		}
		// Never PUT over a night we failed to load: that would wipe its entries.
		if (editing && !night?.id) {
			formError = t('night.notLoaded');
			return;
		}
		if (!balanced && !confirming) {
			confirming = true;
			return;
		}
		doSubmit();
	}

	async function doSubmit() {
		confirming = false;
		submitting = true;
		const payload = {
			date,
			place_id: place_id ? Number(place_id) : null,
			// A selected player with both fields empty never played — dropping the row keeps a
			// phantom 0/0 night out of their history.
			entries: rows.filter(touched).map((r) => ({
				participant_id: Number(r.participant_id),
				buy_in_cents: cents(r.buy_in),
				cash_out_cents: cents(r.cash_out)
			}))
		};
		const ok = await onsubmit(payload);
		if (ok === false) {
			submitting = false;
			return;
		}
		clearDraft();
	}
</script>

<svelte:window onbeforeunload={onBeforeUnload} />

<form class="pd-stack sheet" onsubmit={submit}>
	{#if draftPrompt}
		<div class="pd-toast pd-toast-warn draft">
			<span>{t('night.draftFound', { date: draftDate(draftPrompt.savedAt) })}</span>
			<span class="row draft-actions">
				<button type="button" class="pd-btn pd-btn-ghost pd-btn-sm" onclick={restoreDraft}>
					{t('night.draftRestore')}
				</button>
				<button type="button" class="pd-btn pd-btn-ghost pd-btn-sm" onclick={discardDraft}>
					{t('night.draftDiscard')}
				</button>
			</span>
		</div>
	{/if}

	<!-- ---------- when / where ---------- -->
	<div class="pd-card pd-stack">
		<div class="block">
			<span class="blabel" id="date-label">{t('night.date')}</span>
			<div class="chips" role="group" aria-labelledby="date-label">
				<button
					type="button"
					class="chip tap"
					class:on={!showDateInput && date === today}
					onclick={() => pickDate(today)}
				>
					{t('night.today')}
				</button>
				<button
					type="button"
					class="chip tap"
					class:on={!showDateInput && date === yesterday}
					onclick={() => pickDate(yesterday)}
				>
					{t('night.yesterday')}
				</button>
				<button
					type="button"
					class="chip tap"
					class:on={showDateInput}
					onclick={() => (showDateInput = true)}
				>
					{t('night.otherDate')}
				</button>
			</div>
			{#if showDateInput}
				<input
					id="date"
					type="date"
					aria-label={t('night.date')}
					bind:value={date}
					onkeydown={enterNext}
					required
				/>
			{/if}
		</div>

		<div class="block">
			<span class="blabel" id="place-label">{t('night.place')}</span>
			<div class="chips" role="group" aria-labelledby="place-label">
				<button
					type="button"
					class="chip tap"
					class:on={place_id === ''}
					onclick={() => (place_id = '')}
				>
					{t('night.noPlace')}
				</button>
				{#each places as p (p.id)}
					<button
						type="button"
						class="chip tap"
						class:on={Number(place_id) === p.id}
						onclick={() => (place_id = p.id)}
					>
						📍 {p.name}
					</button>
				{/each}
				{#if !showNewPlace}
					<button type="button" class="chip tap ghost" onclick={() => (showNewPlace = true)}>
						{t('night.addPlace')}
					</button>
				{/if}
			</div>
			{#if showNewPlace}
				<div class="inline-add">
					<input
						aria-label={t('night.placePlaceholder')}
						placeholder={t('night.placePlaceholder')}
						bind:value={newPlace}
						onkeydown={(e) => e.key === 'Enter' && (e.preventDefault(), addPlace())}
					/>
					<button
						type="button"
						class="pd-btn pd-btn-primary pd-btn-sm"
						disabled={addingPlace}
						onclick={addPlace}
					>
						{t('common.save')}
					</button>
					<button
						type="button"
						class="pd-btn pd-btn-ghost pd-btn-sm"
						aria-label={t('common.cancel')}
						onclick={() => (showNewPlace = false)}
					>
						✕
					</button>
				</div>
			{/if}
		</div>
	</div>

	<!-- ---------- roster ---------- -->
	<div class="pd-card pd-stack">
		<div class="spread">
			<span class="blabel" id="roster-label">{t('night.whoPlayed')}</span>
			{#if rows.length}
				<span class="faint count">{t('night.atTable', { count: rows.length })}</span>
			{/if}
		</div>

		{#if lastLineupMissing.length}
			<button type="button" class="chip tap same-table" onclick={sameTableAsLastNight}>
				{t('night.sameTable')}
			</button>
		{/if}

		{#if rosterChips.length}
			<div class="chips" role="group" aria-labelledby="roster-label">
				{#each rosterChips as p (p.id)}
					<button
						type="button"
						class="chip tap"
						class:on={selectedIds.has(p.id)}
						aria-pressed={selectedIds.has(p.id)}
						onclick={() => togglePlayer(p.id)}
					>
						{p.name}
					</button>
				{/each}
			</div>
		{:else}
			<p class="faint hint">{t('night.noPlayersYet')}</p>
		{/if}

		<div class="inline-add">
			<input
				aria-label={t('night.newPlayer')}
				placeholder={t('night.newPlayer')}
				bind:value={newParticipant}
				onkeydown={(e) => e.key === 'Enter' && (e.preventDefault(), addParticipant())}
			/>
			<button
				type="button"
				class="pd-btn pd-btn-ghost pd-btn-sm"
				disabled={addingParticipant}
				onclick={addParticipant}
			>
				{t('common.add')}
			</button>
		</div>
	</div>

	<!-- ---------- money ---------- -->
	{#if rows.length}
		<!-- card-tight: every horizontal pixel goes to the amount inputs at 375px -->
		<div class="pd-card pd-card-tight pd-stack money-card">
			<div class="spread">
				<span class="blabel">{t('night.amounts')}</span>
				{#if defaultBuyIn}
					<span class="faint count">
						{t('night.standardBuyIn', { amount: formatMoney(defaultBuyIn) })}
					</span>
				{/if}
			</div>

			<div class="mrows">
				{#each rows as row, i (row.participant_id)}
					<div class="mrow">
						<div class="mtop">
							<span class="mname">{nameById.get(row.participant_id) ?? '—'}</span>
							{#if touched(row) && !bad(row.buy_in) && !bad(row.cash_out)}
								<span class="money {moneyClass(profitOf(row))}">{formatSigned(profitOf(row))}</span>
							{/if}
							<button
								type="button"
								class="x hit-44"
								aria-label={t('common.remove')}
								title={t('common.remove')}
								onclick={() => togglePlayer(row.participant_id)}
							>
								✕
							</button>
						</div>

						<div class="mfields">
							<div class="field">
								<label for={`bi-${row.participant_id}`}>{t('night.buyInCol')}</label>
								<div class="amount">
									<input
										id={`bi-${row.participant_id}`}
										inputmode="decimal"
										class:invalid={bad(row.buy_in)}
										aria-invalid={bad(row.buy_in)}
										placeholder={t('money.placeholder')}
										bind:value={row.buy_in}
										onchange={() => rememberTypedDefault(row.buy_in)}
										onkeydown={enterNext}
									/>
									{#if defaultBuyIn}
										<button
											type="button"
											class="plus"
											disabled={bad(row.buy_in)}
											title={t('night.rebuyTitle', { amount: formatMoney(defaultBuyIn) })}
											onclick={() => rebuy(i)}
										>
											+1
										</button>
									{/if}
								</div>
								{#if bad(row.buy_in)}
									<span class="err">{t('night.invalidAmount')}</span>
								{:else if rebuyCount(row)}
									<span class="ann faint">
										{t('night.rebuyMultiple', {
											count: rebuyCount(row),
											amount: formatMoney(defaultBuyIn)
										})}
									</span>
								{/if}
							</div>

							<div class="field">
								<label for={`co-${row.participant_id}`}>{t('night.cashOutCol')}</label>
								<input
									id={`co-${row.participant_id}`}
									inputmode="decimal"
									class:invalid={bad(row.cash_out)}
									aria-invalid={bad(row.cash_out)}
									placeholder={t('money.placeholder')}
									bind:value={row.cash_out}
									onkeydown={enterNext}
								/>
								{#if bad(row.cash_out)}
									<span class="err">{t('night.invalidAmount')}</span>
								{:else if suggestIndex === i}
									<button type="button" class="chip tap suggest" onclick={() => fillRemainder(i)}>
										{t('night.fillRemainder', { amount: formatMoney(remainderCents) })}
									</button>
								{/if}
							</div>
						</div>
					</div>
				{/each}
			</div>
		</div>
	{/if}

	{#if formError}
		<div class="pd-toast pd-toast-error">{formError}</div>
	{/if}

	<!-- ---------- sticky bar ---------- -->
	<div class="bar" bind:this={barEl}>
		{#if confirming}
			<div class="confirm" role="alert">
				<span>{t('night.confirmUnbalanced', { amount: formatMoney(Math.abs(remainderCents)) })}</span>
				<span class="row">
					<button
						type="button"
						class="pd-btn pd-btn-primary pd-btn-sm"
						bind:this={confirmButton}
						onclick={doSubmit}
					>
						{t('night.saveAnyway')}
					</button>
					<button type="button" class="pd-btn pd-btn-ghost pd-btn-sm" onclick={() => (confirming = false)}>
						{t('common.cancel')}
					</button>
				</span>
			</div>
		{/if}

		<div class="bar-inner">
			<div class="sums">
				<span class="sum">
					<span class="faint slabel">{t('night.pot')}</span>
					<span class="money">{formatMoney(potCents)}</span>
				</span>
				<span class="sum">
					<span class="faint slabel">
						{closed ? t('night.potClosedShort') : t('night.toDistribute')}
					</span>
					<span class="money rem" class:ok={closed} class:over={remainderCents < 0}>
						{closed ? '✓' : formatMoney(remainderCents)}
					</span>
				</span>
			</div>
			<div class="bactions">
				<button type="button" class="pd-btn pd-btn-ghost" onclick={() => oncancel()}>
					{t('common.cancel')}
				</button>
				<button class="pd-btn pd-btn-primary save" disabled={saving || submitting || rows.length === 0}>
					{saving || submitting ? t('night.saving') : t('night.save')}
				</button>
			</div>
		</div>
	</div>
</form>

<style>
	.sheet {
		/* room for the sticky bar so the last row is never trapped under it */
		padding-bottom: 8px;
	}
	.block {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	.blabel {
		font-size: 0.82rem;
		font-weight: 600;
		color: var(--text-muted);
	}
	.count {
		font-size: 0.8rem;
	}
	.hint {
		margin: 0;
		font-size: 0.85rem;
	}
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}
	/* Chips double as the primary controls here, so they need a real touch target. */
	.tap {
		min-height: 44px;
		padding: 8px 14px;
		font-size: 0.9rem;
		cursor: pointer;
		color: var(--text);
		transition:
			background 0.12s ease,
			border-color 0.12s ease,
			color 0.12s ease;
	}
	.tap:hover {
		border-color: var(--felt-bright);
	}
	.tap.on {
		background: rgba(124, 58, 237, 0.2);
		border-color: var(--felt-bright);
		color: var(--felt-bright);
	}
	.tap.ghost {
		background: transparent;
		border-style: dashed;
		color: var(--text-muted);
	}
	.same-table {
		align-self: flex-start;
		background: rgba(255, 210, 63, 0.1);
		border-color: rgba(255, 210, 63, 0.35);
		color: var(--gold);
	}
	.same-table:hover {
		border-color: var(--gold);
	}
	.inline-add {
		display: flex;
		gap: 8px;
		align-items: center;
	}
	.inline-add input {
		flex: 1;
		min-width: 0;
	}

	/* ---------- money rows ---------- */
	.mrows {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	.mrow {
		border: 1px solid var(--border-soft);
		border-radius: var(--radius-sm);
		padding: 10px;
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	/* Amounts read as numbers, and every pixel of width counts on a phone. */
	.mrow input {
		font-size: 0.9rem;
		padding: 10px 8px;
		font-variant-numeric: tabular-nums;
	}
	.mtop {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto 40px;
		align-items: center;
		gap: 8px;
	}
	.mname {
		font-weight: 600;
	}
	.mfields {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 10px;
		align-items: start;
	}
	.amount {
		display: flex;
		gap: 6px;
		align-items: stretch;
	}
	.amount input {
		min-width: 0;
	}
	.plus {
		flex: 0 0 auto;
		min-width: 44px;
		min-height: 44px;
		border-radius: var(--radius-sm);
		border: 1px solid var(--border-color);
		background: var(--surface-2);
		color: var(--text);
		font-weight: 700;
		font-size: 0.85rem;
		cursor: pointer;
	}
	.plus:hover:not(:disabled) {
		border-color: var(--felt-bright);
		color: var(--felt-bright);
	}
	.plus:disabled {
		opacity: 0.45;
		cursor: not-allowed;
	}
	.ann {
		font-size: 0.75rem;
	}
	.err {
		font-size: 0.75rem;
		color: var(--red);
	}
	.invalid {
		border-color: var(--red);
	}
	.suggest {
		align-self: stretch;
		justify-content: center;
		min-height: 44px;
		font-size: 0.78rem;
		background: rgba(96, 165, 250, 0.12);
		border-color: rgba(96, 165, 250, 0.35);
		color: var(--blue);
	}
	/* Dropping someone from the night: 40×44 visible box, widened to 44 by the .hit-44 overlay. */
	.x {
		display: grid;
		place-items: center;
		min-width: 40px;
		min-height: 44px;
		background: none;
		border: none;
		border-radius: var(--radius-sm);
		color: var(--text-faint);
		cursor: pointer;
		font-size: 0.9rem;
		padding: 0;
		line-height: 1;
	}
	.x:hover {
		color: var(--red);
		background: rgba(240, 88, 106, 0.1);
	}

	/* ---------- sticky bar ---------- */
	.bar {
		position: sticky;
		bottom: 0;
		z-index: 20;
		margin: 4px -20px 0;
		padding: 10px 20px calc(10px + env(safe-area-inset-bottom));
		background: rgba(12, 10, 18, 0.94);
		backdrop-filter: blur(10px);
		border-top: 1px solid var(--border-color);
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	@media (min-width: 700px) {
		/* on wide screens, keep the bar inside the form column instead of full-bleed */
		.bar {
			margin: 4px 0 0;
			border: 1px solid var(--border-color);
			border-radius: var(--radius);
			padding: 12px 18px;
			bottom: 12px;
		}
	}
	.bar-inner {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
	}
	.sums {
		display: flex;
		gap: 16px;
	}
	.sum {
		display: flex;
		flex-direction: column;
		line-height: 1.2;
	}
	.slabel {
		font-size: 0.7rem;
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}
	.rem {
		font-size: 1.05rem;
	}
	.rem.ok {
		color: var(--green-pos);
	}
	.rem.over {
		color: var(--red);
	}
	.bactions {
		display: flex;
		gap: 8px;
	}
	.save {
		min-height: 44px;
	}
	.confirm {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 10px;
		background: rgba(231, 196, 107, 0.1);
		border: 1px solid rgba(231, 196, 107, 0.3);
		color: var(--gold);
		border-radius: var(--radius-sm);
		padding: 10px 12px;
		font-size: 0.88rem;
	}
	.draft {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 10px;
	}
	.draft-actions {
		gap: 8px;
	}

	/* 560px = the app's "small" breakpoint (was an ad-hoc 420) */
	@media (max-width: 560px) {
		.bar-inner {
			flex-direction: column;
			align-items: stretch;
		}
		.sums {
			justify-content: space-between;
		}
		.bactions {
			display: grid;
			grid-template-columns: 1fr 2fr;
		}
	}
</style>
