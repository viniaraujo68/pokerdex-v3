<script>
	import { formatMoney, formatSigned, moneyClass } from '$lib/money.js';

	/** @type {{ night: any, editable?: boolean, onEdit?: Function, onDelete?: Function }} */
	let { night, editable = false, onEdit, onDelete } = $props();

	let open = $state(false);

	function fmtDate(d) {
		return new Date(d + 'T00:00:00').toLocaleDateString('pt-BR', {
			day: '2-digit',
			month: 'long',
			year: 'numeric'
		});
	}

	const sorted = $derived([...night.entries].sort((a, b) => b.profit_cents - a.profit_cents));
	const balanced = $derived(Math.abs(night.balance_cents) < 1);
</script>

<div class="card card-tight night">
	<button class="head" onclick={() => (open = !open)}>
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
		<div class="warn">⚠️ O pote não fecha — diferença de {formatSigned(night.balance_cents)}</div>
	{/if}

	{#if open}
		<div class="entries">
			{#each sorted as e}
				<div class="entry">
					<span class="ename">{e.participant_name}</span>
					<span class="ebuy faint">buy-in {formatMoney(e.buy_in_cents)}</span>
					<span class="ecash faint">saiu {formatMoney(e.cash_out_cents)}</span>
					<span class="money {moneyClass(e.profit_cents)}">{formatSigned(e.profit_cents)}</span>
				</div>
			{/each}
		</div>
		{#if editable}
			<div class="actions">
				<button class="btn btn-ghost btn-sm" onclick={() => onEdit?.(night)}>Editar</button>
				<button class="btn btn-danger btn-sm" onclick={() => onDelete?.(night)}>Excluir</button>
			</div>
		{/if}
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
		text-transform: capitalize;
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
		grid-template-columns: 1fr auto auto 110px;
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
	.actions {
		display: flex;
		gap: 8px;
		margin-top: 14px;
	}
	@media (max-width: 560px) {
		.entry {
			grid-template-columns: 1fr 100px;
		}
		.ebuy,
		.ecash {
			display: none;
		}
	}
</style>
