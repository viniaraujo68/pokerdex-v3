<script>
	import { tick } from 'svelte';
	import { beforeNavigate } from '$app/navigation';
	import { post, errorMessage } from '$lib/http.js';
	import {
		validateMoney,
		formatMoney,
		formatSigned,
		moneyClass,
		centsToInput
	} from '$lib/money.svelte.js';
	import { localeTag, t } from '$lib/i18n.svelte.js';
	import { toast } from '@viniaraujo68/plinth/toast';

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

	// ---------- default buy-in ----------
	/**
	 * Tonight's default buy-in: a helper the user owns, never a field of the night. It seeds the
	 * rows and drives the rebuy stepper, and is never part of the payload.
	 */
	let defaultBuyInInput = $state('');
	const defaultBuyIn = $derived(validateMoney(defaultBuyInInput) || null);

	function applyDefaultToBlankRows() {
		const amount = defaultBuyIn;
		if (!amount) return;
		const seeded = centsToInput(amount);
		rows = rows.map((r) => (isBlank(r.buy_in) ? { ...r, buy_in: seeded } : r));
	}

	/**
	 * While the helper is still empty, the first buy-in typed into a row becomes the default —
	 * one amount typed instead of one per player. Read on `change` (blur/Enter), not on every
	 * keystroke: "5" on the way to "50" is not a default.
	 */
	/** @param {string} value */
	function mirrorFirstTypedBuyIn(value) {
		if (!isBlank(defaultBuyInInput)) return;
		const amount = validateMoney(value);
		if (!amount) return;
		defaultBuyInInput = centsToInput(amount);
		applyDefaultToBlankRows();
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
			defaultBuyInInput,
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
		defaultBuyInInput = s.defaultBuyInInput ?? '';
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

<form class="sheet flex flex-col gap-4" onsubmit={submit}>
	{#if draftPrompt}
		<div class="alert alert-soft alert-warning draft">
			<span>{t('night.draftFound', { date: draftDate(draftPrompt.savedAt) })}</span>
			<span class="flex items-center gap-2">
				<button type="button" class="btn btn-sm" onclick={restoreDraft}>
					{t('night.draftRestore')}
				</button>
				<button type="button" class="btn btn-sm" onclick={discardDraft}>
					{t('night.draftDiscard')}
				</button>
			</span>
		</div>
	{/if}

	<!-- ---------- when / where ---------- -->
	<div class="card flex flex-col gap-4 bg-base-100 p-5">
		<div class="block">
			<span class="blabel" id="date-label">{t('night.date')}</span>
			<div class="chips" role="group" aria-labelledby="date-label">
				<button
					type="button"
					class="btn btn-sm tap"
					class:btn-soft={!showDateInput && date === today}
					class:btn-primary={!showDateInput && date === today}
					onclick={() => pickDate(today)}
				>
					{t('night.today')}
				</button>
				<button
					type="button"
					class="btn btn-sm tap"
					class:btn-soft={!showDateInput && date === yesterday}
					class:btn-primary={!showDateInput && date === yesterday}
					onclick={() => pickDate(yesterday)}
				>
					{t('night.yesterday')}
				</button>
				<button
					type="button"
					class="btn btn-sm tap"
					class:btn-soft={showDateInput}
					class:btn-primary={showDateInput}
					onclick={() => (showDateInput = true)}
				>
					<svg
						class="icon"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
						aria-hidden="true"
					>
						<rect x="3.4" y="5.2" width="17.2" height="15.4" rx="2.6" />
						<path d="M3.4 10.2h17.2M8 2.8v3.2M16 2.8v3.2" />
					</svg>
					{t('night.otherDate')}
				</button>
			</div>
			{#if showDateInput}
				<input
					id="date"
					class="input w-full"
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
					class="btn btn-sm tap"
					class:btn-soft={place_id === ''}
					class:btn-primary={place_id === ''}
					onclick={() => (place_id = '')}
				>
					{t('night.noPlace')}
				</button>
				{#each places as p (p.id)}
					<button
						type="button"
						class="btn btn-sm tap"
						class:btn-soft={Number(place_id) === p.id}
						class:btn-primary={Number(place_id) === p.id}
						onclick={() => (place_id = p.id)}
					>
						<svg
							class="icon"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
							aria-hidden="true"
						>
							<path d="M12 21.2c4.4-4.3 6.6-7.7 6.6-10.3a6.6 6.6 0 1 0-13.2 0c0 2.6 2.2 6 6.6 10.3Z" />
							<circle cx="12" cy="10.4" r="2.4" />
						</svg>
						{p.name}
					</button>
				{/each}
				{#if !showNewPlace}
					<button
						type="button"
						class="btn btn-sm btn-dash tap"
						onclick={() => (showNewPlace = true)}
					>
						{t('night.addPlace')}
					</button>
				{/if}
			</div>
			{#if showNewPlace}
				<div class="inline-add">
					<input
						class="input w-full"
						aria-label={t('night.placePlaceholder')}
						placeholder={t('night.placePlaceholder')}
						bind:value={newPlace}
						onkeydown={(e) => e.key === 'Enter' && (e.preventDefault(), addPlace())}
					/>
					<button type="button" class="btn btn-sm btn-primary" disabled={addingPlace} onclick={addPlace}>
						{t('common.save')}
					</button>
					<button
						type="button"
						class="btn btn-sm"
						aria-label={t('common.cancel')}
						onclick={() => (showNewPlace = false)}
					>
						<svg
							class="icon"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
							aria-hidden="true"
						>
							<path d="m6.4 6.4 11.2 11.2M17.6 6.4 6.4 17.6" />
						</svg>
					</button>
				</div>
			{/if}
		</div>
	</div>

	<!-- ---------- roster ---------- -->
	<div class="card flex flex-col gap-4 bg-base-100 p-5">
		<div class="flex items-center justify-between gap-3">
			<span class="blabel" id="roster-label">{t('night.whoPlayed')}</span>
			{#if rows.length}
				<span class="text-[0.8rem] text-base-content/65">
					{t('night.atTable', { count: rows.length })}
				</span>
			{/if}
		</div>

		{#if lastLineupMissing.length}
			<button
				type="button"
				class="btn btn-sm btn-soft btn-warning tap same-table"
				onclick={sameTableAsLastNight}
			>
				<svg
					class="icon"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
					aria-hidden="true"
				>
					<path d="M3.2 12a8.8 8.8 0 1 0 8.8-8.8 9.5 9.5 0 0 0-6.6 2.7L3.2 8" />
					<path d="M3.2 3.2v4.9h4.9" />
				</svg>
				{t('night.sameTable')}
			</button>
		{/if}

		{#if rosterChips.length}
			<div class="chips" role="group" aria-labelledby="roster-label">
				{#each rosterChips as p (p.id)}
					<button
						type="button"
						class="btn btn-sm tap"
						class:btn-soft={selectedIds.has(p.id)}
						class:btn-primary={selectedIds.has(p.id)}
						aria-pressed={selectedIds.has(p.id)}
						onclick={() => togglePlayer(p.id)}
					>
						{p.name}
					</button>
				{/each}
			</div>
		{:else}
			<p class="m-0 text-[0.85rem] text-base-content/65">{t('night.noPlayersYet')}</p>
		{/if}

		<div class="inline-add">
			<input
				class="input w-full"
				aria-label={t('night.newPlayer')}
				placeholder={t('night.newPlayer')}
				bind:value={newParticipant}
				onkeydown={(e) => e.key === 'Enter' && (e.preventDefault(), addParticipant())}
			/>
			<button type="button" class="btn btn-sm" disabled={addingParticipant} onclick={addParticipant}>
				{t('common.add')}
			</button>
		</div>

		<div class="helper">
			<label class="mlabel" for="default-buy-in">{t('night.defaultBuyIn')}</label>
			<input
				id="default-buy-in"
				class="input hinput"
				inputmode="decimal"
				class:invalid={bad(defaultBuyInInput)}
				aria-invalid={bad(defaultBuyInInput)}
				aria-describedby="default-buy-in-hint"
				placeholder={t('money.placeholder')}
				bind:value={defaultBuyInInput}
				onchange={applyDefaultToBlankRows}
				onkeydown={enterNext}
			/>
			{#if bad(defaultBuyInInput)}
				<span class="err">{t('night.invalidAmount')}</span>
			{/if}
			<span class="hint text-base-content/65" id="default-buy-in-hint">
				{t('night.defaultBuyInHint')}
			</span>
		</div>
	</div>

	<!-- ---------- money ---------- -->
	{#if rows.length}
		<!-- card-tight: every horizontal pixel goes to the amount inputs at 375px -->
		<div class="card flex flex-col gap-4 bg-base-100 p-4">
			<span class="blabel">{t('night.amounts')}</span>

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
								<svg
									class="icon"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="2"
									stroke-linecap="round"
									stroke-linejoin="round"
									aria-hidden="true"
								>
									<path d="m6.4 6.4 11.2 11.2M17.6 6.4 6.4 17.6" />
								</svg>
							</button>
						</div>

						<div class="mfields">
							<div class="flex flex-col gap-1.5">
								<label class="mlabel" for={`bi-${row.participant_id}`}>{t('night.buyInCol')}</label>
								<div class="amount">
									<input
										id={`bi-${row.participant_id}`}
										class="input w-full"
										inputmode="decimal"
										class:invalid={bad(row.buy_in)}
										aria-invalid={bad(row.buy_in)}
										placeholder={t('money.placeholder')}
										bind:value={row.buy_in}
										onchange={() => mirrorFirstTypedBuyIn(row.buy_in)}
										onkeydown={enterNext}
									/>
									{#if defaultBuyIn}
										<button
											type="button"
											class="btn plus"
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
									<span class="ann text-base-content/65">
										{t('night.rebuyMultiple', {
											count: rebuyCount(row),
											amount: formatMoney(defaultBuyIn)
										})}
									</span>
								{/if}
							</div>

							<div class="flex flex-col gap-1.5">
								<label class="mlabel" for={`co-${row.participant_id}`}>{t('night.cashOutCol')}</label>
								<input
									id={`co-${row.participant_id}`}
									class="input w-full"
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
									<button
										type="button"
										class="btn btn-sm btn-soft btn-info suggest"
										onclick={() => fillRemainder(i)}
									>
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
		<div class="alert alert-soft alert-error">{formError}</div>
	{/if}

	<!-- ---------- sticky bar ---------- -->
	<div class="bar">
		{#if confirming}
			<div class="alert alert-soft alert-warning confirm" role="alert">
				<span>{t('night.confirmUnbalanced', { amount: formatMoney(Math.abs(remainderCents)) })}</span>
				<span class="flex items-center gap-2">
					<button
						type="button"
						class="btn btn-sm btn-primary"
						bind:this={confirmButton}
						onclick={doSubmit}
					>
						{t('night.saveAnyway')}
					</button>
					<button type="button" class="btn btn-sm" onclick={() => (confirming = false)}>
						{t('common.cancel')}
					</button>
				</span>
			</div>
		{/if}

		<div class="bar-inner">
			<div class="sums">
				<span class="sum">
					<span class="slabel text-base-content/65">{t('night.pot')}</span>
					<span class="money">{formatMoney(potCents)}</span>
				</span>
				<span class="sum">
					<span class="slabel text-base-content/65">
						{closed ? t('night.potClosedShort') : t('night.toDistribute')}
					</span>
					<span
						class="money rem"
						class:money-pos={closed}
						class:money-neg={remainderCents < 0}
					>
						{#if closed}
							<svg
								class="icon check"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
								role="img"
								aria-label={t('night.potClosedShort')}
							>
								<path d="m4.8 12.8 4.6 4.6L19.2 7" />
							</svg>
						{:else}
							{formatMoney(remainderCents)}
						{/if}
					</span>
				</span>
			</div>
			<div class="bactions">
				<button type="button" class="btn" onclick={() => oncancel()}>{t('common.cancel')}</button>
				<button class="btn btn-primary" disabled={saving || submitting || rows.length === 0}>
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
		font-size: 0.75rem;
		font-weight: 500;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: color-mix(in oklch, var(--color-base-content) 65%, transparent);
	}
	.mlabel {
		font-size: 0.75rem;
		font-weight: 500;
		color: color-mix(in oklch, var(--color-base-content) 80%, transparent);
	}
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}
	/* Chips double as the primary controls here, so they need a real touch target. */
	.tap {
		min-height: 44px;
		font-size: 0.9rem;
	}
	.same-table {
		align-self: flex-start;
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
	.icon {
		width: 1em;
		height: 1em;
		flex: 0 0 auto;
	}
	.check {
		width: 1.1em;
		height: 1.1em;
	}

	.helper {
		display: flex;
		flex-direction: column;
		gap: 6px;
		align-items: flex-start;
		padding-top: 12px;
		border-top: 1px dashed color-mix(in oklch, var(--color-base-content) 15%, transparent);
	}
	.hinput {
		width: 9rem;
		font-family: var(--font-mono);
		font-variant-numeric: tabular-nums;
	}
	.hint {
		font-size: 0.75rem;
		max-width: 44ch;
		line-height: 1.35;
	}

	/* ---------- money rows ---------- */
	.mrows {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	.mrow {
		border: 1px solid color-mix(in oklch, var(--color-base-content) 10%, transparent);
		border-radius: var(--radius-field);
		padding: 10px;
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	/* Amounts read as numbers, and every pixel of width counts on a phone. */
	.mrow input {
		font-family: var(--font-mono);
		font-size: 0.9rem;
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
		height: auto;
		font-weight: 600;
		font-size: 0.85rem;
	}
	.plus:hover:not(:disabled) {
		border-color: color-mix(in oklch, var(--color-primary) 55%, transparent);
		color: var(--ink-primary);
	}
	.ann {
		font-size: 0.75rem;
	}
	.err {
		font-size: 0.75rem;
		color: var(--color-error);
	}
	.invalid {
		border-color: var(--color-error);
	}
	.suggest {
		align-self: stretch;
		min-height: 44px;
		height: auto;
		font-size: 0.78rem;
	}
	/* Dropping someone from the night: 40×44 visible box, widened to 44 by the .hit-44 overlay. */
	.x {
		display: grid;
		place-items: center;
		min-width: 40px;
		min-height: 44px;
		background: none;
		border: none;
		border-radius: var(--radius-field);
		color: color-mix(in oklch, var(--color-base-content) 65%, transparent);
		cursor: pointer;
		font-size: 0.9rem;
		padding: 0;
		line-height: 1;
	}
	.x:hover {
		color: var(--color-error);
		background: color-mix(in oklch, var(--color-error) 10%, transparent);
	}

	/* ---------- sticky bar ---------- */
	.bar {
		position: sticky;
		bottom: 0;
		z-index: 20;
		margin: 4px -20px 0;
		padding: 10px 20px calc(10px + env(safe-area-inset-bottom));
		background: color-mix(in oklch, var(--color-base-100) 92%, transparent);
		backdrop-filter: blur(10px);
		border-top: 1px solid color-mix(in oklch, var(--color-base-content) 15%, transparent);
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	@media (min-width: 700px) {
		/* on wide screens, keep the bar inside the form column instead of full-bleed */
		.bar {
			margin: 4px 0 0;
			border: 1px solid color-mix(in oklch, var(--color-base-content) 15%, transparent);
			border-radius: var(--radius-box);
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
		letter-spacing: 0.06em;
	}
	.rem {
		font-size: 1.05rem;
	}
	.bactions {
		display: flex;
		gap: 8px;
	}
	.bactions .btn {
		min-height: 44px;
		height: auto;
	}
	.confirm {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 10px;
		font-size: 0.88rem;
	}
	.draft {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 10px;
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
