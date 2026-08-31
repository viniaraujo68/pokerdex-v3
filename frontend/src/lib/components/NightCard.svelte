<script>
	import { formatMoney, formatSigned, moneyClass, centsToInput, validateMoney } from '$lib/money.svelte.js';
	import { errorMessage } from '$lib/http.js';
	import { settle } from '$lib/settle.js';
	import { t } from '$lib/i18n.svelte.js';
	import { formatNightDate } from '$lib/dates.js';
	import Icon from './Icon.svelte';

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
	let settleOpen = $state(false);
	/** Ties the header button to the panel it opens, for `aria-controls`. */
	const bodyId = $derived(`night-${night.id}-detail`);
	const settleId = $derived(`night-${night.id}-settlement`);

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

<div class="card bg-base-100 p-4">
	<button
		type="button"
		class="head"
		aria-expanded={open}
		aria-controls={bodyId}
		onclick={() => (open = !open)}
	>
		<div>
			<span class="date">{formatNightDate(night.date)}</span>
			<div class="meta">
				{#if night.place_name}
					<span class="badge badge-soft">
						<Icon name="place" />
						{night.place_name}
					</span>
				{/if}
				<span class="badge badge-soft">
					<Icon name="players" />
					{night.entries.length}
				</span>
				<span class="badge badge-soft badge-warning">
					<Icon name="pot" />
					{formatMoney(night.total_pot_cents)}
				</span>
			</div>
		</div>
		<span class="caret" class:open><Icon name="chevron" /></span>
	</button>

	{#if !balanced}
		<div class="warn money-warn">
			<Icon name="warning" />
			{t('night.potMismatch', { amount: formatSigned(night.balance_cents) })}
		</div>
	{/if}

	{#if open}
		<div id={bodyId}>
			<div class="entries">
				{#each sorted as e (e.id)}
					{#if editingId === e.id}
						<div class="qedit">
							<span class="ename">{e.participant_name}</span>
							<div class="qfields">
								<div class="flex flex-col gap-1.5">
									<label class="qlabel" for={`qb-${e.id}`}>{t('night.buyInCol')}</label>
									<input
										id={`qb-${e.id}`}
										class="input w-full"
										inputmode="decimal"
										placeholder={t('money.placeholder')}
										bind:value={buyIn}
										onkeydown={(ev) => onKey(ev, e)}
									/>
								</div>
								<div class="flex flex-col gap-1.5">
									<label class="qlabel" for={`qc-${e.id}`}>{t('night.cashOutCol')}</label>
									<input
										id={`qc-${e.id}`}
										class="input w-full"
										inputmode="decimal"
										placeholder={t('money.placeholder')}
										bind:value={cashOut}
										onkeydown={(ev) => onKey(ev, e)}
									/>
								</div>
							</div>
							{#if entryError}<div class="qerr">{entryError}</div>{/if}
							<div class="qactions">
								<button class="btn btn-sm btn-primary" disabled={savingEntry} onclick={() => saveEntry(e)}>
									{savingEntry ? t('common.saving') : t('common.save')}
								</button>
								<button class="btn btn-sm" disabled={savingEntry} onclick={cancelEdit}>
									{t('common.cancel')}
								</button>
							</div>
						</div>
					{:else}
						<div class="entry">
							<span class="ename">{e.participant_name}</span>
							<span class="ebuy text-base-content/65">
								{t('night.buyInInline', { amount: formatMoney(e.buy_in_cents) })}
							</span>
							<span class="ecash text-base-content/65">
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
									<Icon name="edit" class="size-4" />
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
					<button
						type="button"
						class="slabel text-base-content/65"
						aria-expanded={settleOpen}
						aria-controls={settleId}
						onclick={() => (settleOpen = !settleOpen)}
					>
						{t('card.settlement')}
						<span class="scaret" class:open={settleOpen}><Icon name="chevron" /></span>
					</button>
					{#if settleOpen}
						<ul class="tlist" id={settleId}>
							{#each transfers as tr (tr.from + '\u2192' + tr.to)}
								<li>
									<span class="tnames">{tr.from} → {tr.to}</span>
									<span class="money">{formatMoney(tr.cents)}</span>
								</li>
							{/each}
						</ul>
					{/if}
				</div>
			{/if}

			{#if editable}
				<div class="actions">
					<button class="btn btn-sm" onclick={() => onEdit?.(night)}>{t('common.edit')}</button>
					<button class="btn btn-sm btn-soft btn-error" onclick={() => onDelete?.(night)}>
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
		font-weight: 600;
		font-size: 1.05rem;
		letter-spacing: -0.01em;
	}
	.meta {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
		margin-top: 8px;
	}
	.caret {
		display: grid;
		place-items: center;
		font-size: 1.15rem;
		color: color-mix(in oklch, var(--color-base-content) 65%, transparent);
		transition: transform 0.2s ease;
		line-height: 1;
	}
	.caret.open {
		transform: rotate(180deg);
	}
	.warn {
		display: flex;
		align-items: center;
		gap: 6px;
		margin-top: 12px;
		font-size: 0.82rem;
	}
	.warn :global(svg) {
		flex: none;
	}
	.entries {
		margin-top: 14px;
		border-top: 1px solid color-mix(in oklch, var(--color-base-content) 10%, transparent);
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
		border-bottom: 1px solid color-mix(in oklch, var(--color-base-content) 10%, transparent);
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
		display: inline-grid;
		place-items: center;
		justify-self: center;
		background: none;
		border: none;
		color: color-mix(in oklch, var(--color-base-content) 65%, transparent);
		cursor: pointer;
		padding: 8px 4px;
		line-height: 1;
	}
	.pencil:hover {
		color: var(--ink-primary);
	}
	.qedit {
		display: flex;
		flex-direction: column;
		gap: 8px;
		padding: 10px;
		margin: 6px 0;
		border: 1px solid color-mix(in oklch, var(--color-primary) 45%, transparent);
		border-radius: var(--radius-field);
		background: color-mix(in oklch, var(--color-primary) 6%, var(--color-base-100));
	}
	.qlabel {
		font-size: 0.75rem;
		font-weight: 500;
		color: color-mix(in oklch, var(--color-base-content) 80%, transparent);
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
		color: var(--color-error);
	}
	.settle {
		margin-top: 14px;
		border-top: 1px solid color-mix(in oklch, var(--color-base-content) 10%, transparent);
		padding-top: 10px;
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.slabel {
		display: flex;
		align-items: center;
		gap: 5px;
		align-self: flex-start;
		min-height: 1.75rem;
		border: 0;
		background: none;
		padding: 0;
		font-size: 0.6875rem;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		font-weight: 500;
		cursor: pointer;
	}
	.slabel:hover {
		color: var(--color-base-content);
	}
	.scaret {
		display: grid;
		place-items: center;
		font-size: 0.9rem;
		transition: transform 0.2s ease;
		line-height: 1;
	}
	.scaret.open {
		transform: rotate(180deg);
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
