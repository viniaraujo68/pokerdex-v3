<script>
	import { formatSigned, formatMoney, moneyClass } from '$lib/money.js';

	/** @type {{ ranking: Array<any> }} */
	let { ranking } = $props();

	const medals = ['🥇', '🥈', '🥉'];

	const columns = [
		{ key: 'name', label: 'Participante', align: 'left' },
		{ key: 'total_profit_cents', label: 'Lucro total', align: 'right' },
		{ key: 'nights_played', label: 'Noites', align: 'right' },
		{ key: 'avg_profit_cents', label: 'Média/noite', align: 'right' },
		{ key: 'roi', label: 'ROI', align: 'right' }
	];

	let sortKey = $state('total_profit_cents');
	let sortDir = $state('desc'); // 'asc' | 'desc'

	// Canonical standing comes from the backend order (sorted by total profit desc),
	// so the "#"/medal stays attached to each person even when sorting by another column.
	const ranked = $derived(ranking.map((r, i) => ({ ...r, rank: i + 1 })));

	const sorted = $derived.by(() => {
		const dir = sortDir === 'asc' ? 1 : -1;
		const val = (r) => {
			const v = r[sortKey];
			return v == null ? -Infinity : v;
		};
		return [...ranked].sort((a, b) => {
			if (sortKey === 'name') return dir * a.name.localeCompare(b.name);
			return dir * (val(a) - val(b));
		});
	});

	function sortBy(key) {
		if (sortKey === key) {
			sortDir = sortDir === 'asc' ? 'desc' : 'asc';
		} else {
			sortKey = key;
			sortDir = key === 'name' ? 'asc' : 'desc';
		}
	}

	function arrow(key) {
		if (sortKey !== key) return '';
		return sortDir === 'asc' ? ' ↑' : ' ↓';
	}

	function roiText(r) {
		return r.roi != null ? (r.roi * 100).toFixed(0) + '%' : '—';
	}
</script>

{#if ranking.length === 0}
	<div class="empty">Nenhum participante com noites registradas.</div>
{:else}
	<!-- Desktop: table -->
	<div class="table">
		<div class="thead">
			<span class="col-rank">#</span>
			{#each columns as c}
				<button class="th" class:active={sortKey === c.key} style:text-align={c.align} onclick={() => sortBy(c.key)}>
					{c.label}{arrow(c.key)}
				</button>
			{/each}
		</div>
		{#each sorted as r (r.participant_id)}
			<div class="trow">
				<span class="col-rank rank">{r.rank <= 3 ? medals[r.rank - 1] : r.rank}</span>
				<span class="name">{r.name}</span>
				<span class="num money {moneyClass(r.total_profit_cents)}">{formatSigned(r.total_profit_cents)}</span>
				<span class="num muted">{r.nights_played}</span>
				<span class="num money {moneyClass(r.avg_profit_cents)}">{formatMoney(r.avg_profit_cents)}</span>
				<span class="num {r.roi != null ? moneyClass(r.roi) : 'faint'}">{roiText(r)}</span>
			</div>
		{/each}
	</div>

	<!-- Mobile: sort bar + cards -->
	<div class="mobile">
		<div class="sortbar">
			<span class="sb-label faint">Ordenar:</span>
			{#each columns as c}
				<button class="sb" class:active={sortKey === c.key} onclick={() => sortBy(c.key)}>
					{c.label}{arrow(c.key)}
				</button>
			{/each}
		</div>
		<div class="cards">
			{#each sorted as r (r.participant_id)}
				<div class="rcard">
					<span class="rc-rank">{r.rank <= 3 ? medals[r.rank - 1] : r.rank}</span>
					<div class="rc-mid">
						<span class="rc-name">{r.name}</span>
						<span class="rc-sub faint">
							{r.nights_played} noites · méd {formatMoney(r.avg_profit_cents)} · ROI {roiText(r)}
						</span>
					</div>
					<span class="rc-profit money {moneyClass(r.total_profit_cents)}">{formatSigned(r.total_profit_cents)}</span>
				</div>
			{/each}
		</div>
	</div>
{/if}

<style>
	/* ---------- Desktop table ---------- */
	.table {
		display: flex;
		flex-direction: column;
	}
	.thead,
	.trow {
		display: grid;
		grid-template-columns: 40px 1fr 130px 72px 120px 72px;
		align-items: center;
		gap: 8px;
		padding: 12px 6px;
	}
	.thead {
		border-bottom: 1px solid var(--border);
	}
	.th {
		background: none;
		border: none;
		cursor: pointer;
		font-size: 0.74rem;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: var(--text-faint);
		font-weight: 600;
		font-family: inherit;
		padding: 2px;
		white-space: nowrap;
		transition: color 0.12s ease;
	}
	.th:hover {
		color: var(--text-muted);
	}
	.th.active {
		color: var(--felt-bright);
	}
	.trow {
		border-bottom: 1px solid var(--border-soft);
	}
	.trow:last-child {
		border-bottom: none;
	}
	.col-rank {
		text-align: center;
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

	/* ---------- Mobile cards ---------- */
	.mobile {
		display: none;
	}
	.sortbar {
		display: flex;
		align-items: center;
		gap: 6px;
		overflow-x: auto;
		padding-bottom: 10px;
		margin-bottom: 4px;
		-webkit-overflow-scrolling: touch;
	}
	.sb-label {
		font-size: 0.78rem;
		white-space: nowrap;
	}
	.sb {
		background: var(--surface-2);
		border: 1px solid var(--border);
		color: var(--text-muted);
		border-radius: 999px;
		padding: 5px 11px;
		font-size: 0.78rem;
		font-weight: 600;
		white-space: nowrap;
		cursor: pointer;
		font-family: inherit;
	}
	.sb.active {
		background: rgba(124, 58, 237, 0.18);
		border-color: var(--felt-bright);
		color: var(--felt-bright);
	}
	.cards {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.rcard {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 12px;
		border: 1px solid var(--border-soft);
		border-radius: 10px;
		background: var(--bg-elev);
	}
	.rc-rank {
		font-size: 1.1rem;
		min-width: 24px;
		text-align: center;
		font-variant-numeric: tabular-nums;
	}
	.rc-mid {
		display: flex;
		flex-direction: column;
		gap: 2px;
		min-width: 0;
		flex: 1;
	}
	.rc-name {
		font-weight: 700;
	}
	.rc-sub {
		font-size: 0.74rem;
	}
	.rc-profit {
		font-size: 1.05rem;
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
	}

	@media (max-width: 600px) {
		.table {
			display: none;
		}
		.mobile {
			display: block;
		}
	}
</style>
