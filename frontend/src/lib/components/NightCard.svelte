<script>
	import { formatMoney, formatSigned, moneyClass, centsToInput, validateMoney } from '$lib/money.svelte.js';
	import { errorMessage } from '$lib/http.js';
	import { settle } from '$lib/settle.js';
	import { localeTag, t } from '$lib/i18n.svelte.js';

	/**
	 * @type {{
	 *   night: import('$lib/types.js').Night,
	 *   editable?: boolean,
	 *   onEdit?: (night: import('$lib/types.js').Night) => void,
	 *   onDelete?: (night: import('$lib/types.js').Night) => void,
	 *   onQuickEdit?: (
	 *     night: import('$lib/types.js').Night,
	 *     entry: import('$lib/types.js').Entry,
	 *     amounts: { buy_in_cents: number, cash_out_cents: number }
	 *   ) => Promise<void>
	 * }}
	 */
	let { night, editable = false, onEdit, onDelete, onQuickEdit } = $props();

	let open = $state(false);
	/** Ties the header button to the panel it opens, for `aria-controls`. */
	const bodyId = $derived(`night-${night.id}-detail`);

	/** @param {string} d */
	function fmtDate(d) {
		return new Date(d + 'T00:00:00').toLocaleDateString(localeTag(), {
			day: '2-digit',
			month: 'long',
			year: 'numeric'
		});
	}

	const sorted = $derived([...night.entries].sort((a, b) => b.profit_cents - a.profit_cents));
	const balanced = $derived(Math.abs(night.balance_cents) < 1);

	/** Who pays whom. Only meaningful with a closed pot — otherwise the transfers can't add up. */
	const transfers = $derived(
		balanced
			? settle(sorted.map((e) => ({ name: e.participant_name, profit_cents: e.profit_cents })))
			: []
	);

	// ---------- inline quick edit (one entry at a time) ----------
	/** @type {number|null} */
	let editingId = $state(null);
	let buyIn = $state('');
	let cashOut = $state('');
	let savingEntry = $state(false);
	let entryError = $state('');

	/** @param {import('$lib/types.js').Entry} e */
	function startEdit(e) {
		editingId = e.id;
		buyIn = centsToInput(e.buy_in_cents);
		cashOut = centsToInput(e.cash_out_cents);
		entryError = '';
	}

	function cancelEdit() {
		editingId = null;
		entryError = '';
	}

	/** @param {import('$lib/types.js').Entry} e */
	async function saveEntry(e) {
		const buy_in_cents = validateMoney(buyIn);
		const cash_out_cents = validateMoney(cashOut);
		if (buy_in_cents === null || cash_out_cents === null) {
			entryError = t('night.invalidAmount');
			return;
		}
		savingEntry = true;
		entryError = '';
		try {
			await onQuickEdit?.(night, e, { buy_in_cents, cash_out_cents });
			editingId = null;
		} catch (err) {
			entryError = t('card.quickEditFailed', { message: errorMessage(err) });
		} finally {
			savingEntry = false;
		}
	}

	/** @param {KeyboardEvent} ev @param {import('$lib/types.js').Entry} e */
	function onKey(ev, e) {
		if (ev.key === 'Enter') {
			ev.preventDefault();
			saveEntry(e);
		} else if (ev.key === 'Escape') {
			ev.preventDefault();
			cancelEdit();
		}
	}
</script>

<div class="pd-card pd-card-tight night">
	<button
		type="button"
		class="head"
		aria-expanded={open}
		aria-controls={bodyId}
		onclick={() => (open = !open)}
	>
		<div class="head-left">
			<span class="date">{fmtDate(night.date)}</span>
			<div class="meta">
				{#if night.place_name}<span class="chip">📍 {night.place_name}</span>{/if}
				<span class="chip">👥 {night.entries.length}</span>
				<span class="chip chip-gold">💰 {formatMoney(night.total_pot_cents)}</span>
			</div>
		</div>
		<span class="caret" class:open>⌄</span>
	</button>

	{#if !balanced}
		<div class="warn">{t('night.potMismatch', { amount: formatSigned(night.balance_cents) })}</div>
	{/if}

	{#if open}
		<div id={bodyId}>
			<div class="entries">
				{#each sorted as e (e.id)}
					{#if editingId === e.id}
						<div class="qedit">
							<span class="ename">{e.participant_name}</span>
							<div class="qfields">
								<div class="field">
									<label for={`qb-${e.id}`}>{t('night.buyInCol')}</label>
									<input
										id={`qb-${e.id}`}
										inputmode="decimal"
										placeholder={t('money.placeholder')}
										bind:value={buyIn}
										onkeydown={(ev) => onKey(ev, e)}
									/>
								</div>
								<div class="field">
									<label for={`qc-${e.id}`}>{t('night.cashOutCol')}</label>
									<input
										id={`qc-${e.id}`}
										inputmode="decimal"
										placeholder={t('money.placeholder')}
										bind:value={cashOut}
										onkeydown={(ev) => onKey(ev, e)}
									/>
								</div>
							</div>
							{#if entryError}<div class="qerr">{entryError}</div>{/if}
							<div class="qactions">
								<button
									class="pd-btn pd-btn-primary pd-btn-sm"
									disabled={savingEntry}
									onclick={() => saveEntry(e)}
								>
									{savingEntry ? t('common.saving') : t('common.save')}
								</button>
								<button class="pd-btn pd-btn-ghost pd-btn-sm" disabled={savingEntry} onclick={cancelEdit}>
									{t('common.cancel')}
								</button>
							</div>
						</div>
					{:else}
						<div class="entry">
							<span class="ename">{e.participant_name}</span>
							<span class="ebuy faint">
								{t('night.buyInInline', { amount: formatMoney(e.buy_in_cents) })}
							</span>
							<span class="ecash faint">
								{t('night.cashOutInline', { amount: formatMoney(e.cash_out_cents) })}
							</span>
							<span class="money {moneyClass(e.profit_cents)}">{formatSigned(e.profit_cents)}</span>
							{#if editable && onQuickEdit}
								<button
									type="button"
									class="pencil hit-44"
									title={t('card.editEntry', { name: e.participant_name })}
									aria-label={t('card.editEntry', { name: e.participant_name })}
									onclick={() => startEdit(e)}
								>
									✎
								</button>
							{:else}
								<span></span>
							{/if}
						</div>
					{/if}
				{/each}
			</div>

			{#if transfers.length}
				<div class="settle">
					<span class="slabel faint">{t('card.settlement')}</span>
					<ul class="tlist">
						{#each transfers as tr (tr.from + '\u2192' + tr.to)}
							<li>
								<span class="tnames">{tr.from} → {tr.to}</span>
								<span class="money">{formatMoney(tr.cents)}</span>
							</li>
						{/each}
					</ul>
				</div>
			{/if}

			{#if editable}
				<div class="actions">
					<button class="pd-btn pd-btn-ghost pd-btn-sm" onclick={() => onEdit?.(night)}>
						{t('common.edit')}
					</button>
					<button class="pd-btn pd-btn-danger pd-btn-sm" onclick={() => onDelete?.(night)}>
						{t('common.delete')}
					</button>
				</div>
			{/if}
		</div>
	{/if}
</div>

<style>
	.head {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 12px;
		width: 100%;
		background: none;
		border: none;
		color: inherit;
		cursor: pointer;
		text-align: left;
		padding: 0;
	}
	.date {
		font-weight: 700;
		font-family: var(--font-display);
		font-size: 1.05rem;
	}
	.meta {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
		margin-top: 8px;
	}
	.caret {
		font-size: 1.4rem;
		color: var(--text-faint);
		transition: transform 0.2s ease;
		line-height: 1;
	}
	.caret.open {
		transform: rotate(180deg);
	}
	.warn {
		margin-top: 12px;
		font-size: 0.82rem;
		color: var(--gold);
	}
	.entries {
		margin-top: 14px;
		border-top: 1px solid var(--border-soft);
		padding-top: 10px;
		display: flex;
		flex-direction: column;
	}
	.entry {
		display: grid;
		grid-template-columns: 1fr auto auto 110px 32px;
		gap: 10px;
		align-items: center;
		padding: 7px 0;
		border-bottom: 1px solid var(--border-soft);
		font-size: 0.9rem;
	}
	.entry:last-child {
		border-bottom: none;
	}
	.ename {
		font-weight: 600;
	}
	.entry .money {
		text-align: right;
	}
	.pencil {
		background: none;
		border: none;
		color: var(--text-faint);
		cursor: pointer;
		font-size: 0.95rem;
		padding: 8px 4px;
		line-height: 1;
	}
	.pencil:hover {
		color: var(--felt-bright);
	}
	.qedit {
		display: flex;
		flex-direction: column;
		gap: 8px;
		padding: 10px;
		margin: 6px 0;
		border: 1px solid var(--felt);
		border-radius: var(--radius-sm);
		background: var(--bg-elev);
	}
	.qfields {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 10px;
	}
	.qactions {
		display: flex;
		gap: 8px;
	}
	.qerr {
		font-size: 0.78rem;
		color: var(--red);
	}
	.settle {
		margin-top: 14px;
		border-top: 1px solid var(--border-soft);
		padding-top: 10px;
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.slabel {
		font-size: 0.72rem;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		font-weight: 600;
	}
	.tlist {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.tlist li {
		display: flex;
		justify-content: space-between;
		gap: 12px;
		font-size: 0.88rem;
	}
	.tnames {
		font-weight: 600;
	}
	.actions {
		display: flex;
		gap: 8px;
		margin-top: 14px;
	}
	@media (max-width: 560px) {
		.entry {
			grid-template-columns: 1fr 100px 32px;
		}
		.ebuy,
		.ecash {
			display: none;
		}
	}
</style>
