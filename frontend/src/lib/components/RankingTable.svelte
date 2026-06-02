<script>
	import { formatSigned, formatMoney, moneyClass } from '$lib/money.js';

	/** @type {{ ranking: Array<any> }} */
	let { ranking } = $props();

	const medals = ['🥇', '🥈', '🥉'];
</script>

{#if ranking.length === 0}
	<div class="empty">Nenhum participante com noites registradas.</div>
{:else}
	<div class="table">
		<div class="thead">
			<span>#</span>
			<span>Participante</span>
			<span class="num">Lucro total</span>
			<span class="num hide-sm">Noites</span>
			<span class="num hide-sm">Média/noite</span>
			<span class="num hide-sm">ROI</span>
		</div>
		{#each ranking as r, i}
			<div class="trow">
				<span class="rank">{medals[i] ?? i + 1}</span>
				<span class="name">{r.name}</span>
				<span class="num money {moneyClass(r.total_profit_cents)}">{formatSigned(r.total_profit_cents)}</span>
				<span class="num muted hide-sm">{r.nights_played}</span>
				<span class="num money hide-sm {moneyClass(r.avg_profit_cents)}">{formatMoney(r.avg_profit_cents)}</span>
				<span class="num hide-sm {r.roi != null ? moneyClass(r.roi) : 'faint'}">
					{r.roi != null ? (r.roi * 100).toFixed(0) + '%' : '—'}
				</span>
			</div>
		{/each}
	</div>
{/if}

<style>
	.table {
		display: flex;
		flex-direction: column;
	}
	.thead,
	.trow {
		display: grid;
		grid-template-columns: 36px 1fr 130px 70px 120px 70px;
		align-items: center;
		gap: 8px;
		padding: 12px 6px;
	}
	.thead {
		font-size: 0.78rem;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: var(--text-faint);
		border-bottom: 1px solid var(--border);
	}
	.trow {
		border-bottom: 1px solid var(--border-soft);
	}
	.trow:last-child {
		border-bottom: none;
	}
	.num {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
	.rank {
		font-size: 1rem;
	}
	.name {
		font-weight: 600;
	}
	@media (max-width: 640px) {
		.thead,
		.trow {
			grid-template-columns: 30px 1fr 120px;
		}
		.hide-sm {
			display: none;
		}
	}
</style>
