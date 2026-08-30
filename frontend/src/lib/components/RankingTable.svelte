<script>
	import { formatSigned, formatMoney, moneyClass } from '$lib/money.svelte.js';
	import { t } from '$lib/i18n.svelte.js';

	/** @type {{ ranking: import('$lib/types.js').RankingRow[] }} */
	let { ranking } = $props();

	const medals = ['🥇', '🥈', '🥉'];

	/** @type {{ key: keyof import('$lib/types.js').RankingRow, label: string, align: 'left'|'right' }[]} */
	const columns = $derived([
		{ key: 'name', label: t('ranking.player'), align: 'left' },
		{ key: 'total_profit_cents', label: t('ranking.totalProfit'), align: 'right' },
		{ key: 'nights_played', label: t('ranking.nights'), align: 'right' },
		{ key: 'avg_profit_cents', label: t('ranking.avgPerNight'), align: 'right' },
		{ key: 'roi', label: t('ranking.roi'), align: 'right' }
	]);

	/** Column the table is sorted by. @type {keyof import('$lib/types.js').RankingRow} */
	let sortKey = $state('total_profit_cents');
	/** @type {'asc'|'desc'} */
	let sortDir = $state('desc');

	// The "#"/medal follows the current sort: it's the row's position in the order on screen,
	// so re-sorting (e.g. by nights played) renumbers everyone to match what's displayed.
	/** @typedef {import('$lib/types.js').RankingRow & { rank: number }} Ranked */
	const sorted = $derived.by(() => {
		const dir = sortDir === 'asc' ? 1 : -1;
		/** Missing values sort last in either direction's "worst" end. @param {import('$lib/types.js').RankingRow} r */
		const val = (r) => {
			const v = r[sortKey];
			return typeof v === 'number' ? v : -Infinity;
		};
		return [...ranking]
			.sort((a, b) => {
				if (sortKey === 'name') return dir * a.name.localeCompare(b.name);
				return dir * (val(a) - val(b));
			})
			.map((r, i) => ({ ...r, rank: i + 1 }));
	});

	/** @param {keyof import('$lib/types.js').RankingRow} key */
	function sortBy(key) {
		if (sortKey === key) {
			sortDir = sortDir === 'asc' ? 'desc' : 'asc';
		} else {
			sortKey = key;
			sortDir = key === 'name' ? 'asc' : 'desc';
		}
	}

	/** @param {keyof import('$lib/types.js').RankingRow} key */
	function arrow(key) {
		if (sortKey !== key) return '';
		return sortDir === 'asc' ? ' ↑' : ' ↓';
	}

	/** `aria-sort` belongs on the columnheader — the arrow glyph is decoration for sighted users. */
	/** @param {keyof import('$lib/types.js').RankingRow} key */
	function ariaSort(key) {
		if (sortKey !== key) return 'none';
		return sortDir === 'asc' ? 'ascending' : 'descending';
	}

	/** @param {import('$lib/types.js').RankingRow} r */
	function roiText(r) {
		return r.roi != null ? (r.roi * 100).toFixed(0) + '%' : '—';
	}
</script>

{#if ranking.length === 0}
	<div class="empty">{t('ranking.empty')}</div>
{:else}
	<!-- Desktop: table. The wrapper owns the horizontal overflow so a narrow card scrolls the
	     grid internally instead of widening the document. -->
	<div class="table-wrap">
		<div class="rank-table" role="table" aria-label={t('tab.ranking')}>
			<div class="thead" role="row">
				<span class="col-rank" role="columnheader">#</span>
				{#each columns as c (c.key)}
					<span class="th-cell" role="columnheader" aria-sort={ariaSort(c.key)}>
						<button
							class="th"
							class:active={sortKey === c.key}
							style:text-align={c.align}
							aria-label={t('ranking.sortByColumn', { column: c.label })}
							onclick={() => sortBy(c.key)}
						>
							{c.label}{arrow(c.key)}
						</button>
					</span>
				{/each}
			</div>
			{#each sorted as r (r.participant_id)}
				<div class="trow" role="row">
					<span class="col-rank rank" role="cell">{r.rank <= 3 ? medals[r.rank - 1] : r.rank}</span>
					<span class="name" role="cell">{r.name}</span>
					<span class="num money {moneyClass(r.total_profit_cents)}" role="cell">{formatSigned(r.total_profit_cents)}</span>
					<span class="num muted" role="cell">{r.nights_played}</span>
					<span class="num money {moneyClass(r.avg_profit_cents)}" role="cell">{formatMoney(r.avg_profit_cents)}</span>
					<span class="num {r.roi != null ? moneyClass(r.roi) : 'faint'}" role="cell">{roiText(r)}</span>
				</div>
			{/each}
		</div>
	</div>

	<!-- Mobile: sort bar + cards -->
	<div class="mobile">
		<div class="sortbar" role="group" aria-label={t('ranking.sortBy')}>
			<span class="sb-label faint" aria-hidden="true">{t('ranking.sortBy')}</span>
			{#each columns as c (c.key)}
				<button
					class="sb"
					class:active={sortKey === c.key}
					aria-pressed={sortKey === c.key}
					aria-label={t('ranking.sortByColumn', { column: c.label })}
					onclick={() => sortBy(c.key)}
				>
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
							{t('ranking.cardSub', {
								count: r.nights_played,
								avg: formatMoney(r.avg_profit_cents),
								roi: roiText(r)
							})}
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
	.table-wrap {
		overflow-x: auto;
		-webkit-overflow-scrolling: touch;
	}
	.rank-table {
		display: flex;
		flex-direction: column;
		/* Sum of the fixed columns + gaps (~486px) plus room for a name. Below this the wrapper
		   scrolls; above it every row is exactly the container width, so the columns line up. */
		min-width: 520px;
	}
	.thead,
	.trow {
		display: grid;
		/* minmax(0, 1fr), not 1fr: a long name must wrap instead of stretching its own row wider
		   than the header — that's what used to break the alignment and the card's width. */
		grid-template-columns: 40px minmax(0, 1fr) 130px 72px 120px 72px;
		align-items: center;
		gap: 8px;
		padding: 12px 6px;
	}
	.thead {
		border-bottom: 1px solid var(--border-color);
	}
	.th-cell {
		display: flex;
		min-width: 0;
	}
	.th {
		flex: 1;
		min-width: 0;
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
		min-width: 0;
		overflow-wrap: anywhere;
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
		border: 1px solid var(--border-color);
		color: var(--text-muted);
		border-radius: 999px;
		/* these are the only way to re-sort on a phone — give them a thumb-sized target */
		min-height: 44px;
		padding: 5px 14px;
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

	/* 700px (the app's "mid" breakpoint), not 600: between ~600 and 680 the fixed-column grid was
	   wider than the card, which pushed a horizontal scrollbar onto <body>. */
	@media (max-width: 700px) {
		.table-wrap {
			display: none;
		}
		.mobile {
			display: block;
		}
	}
</style>
