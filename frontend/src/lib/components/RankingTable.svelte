<script>
	import { DataTable } from '@viniaraujo68/plinth/table';
	import { formatSigned, formatMoney, moneyClass } from '$lib/money.svelte.js';
	import { t, localeTag } from '$lib/i18n.svelte.js';

	/** @type {{ ranking: import('$lib/types.js').RankingRow[] }} */
	let { ranking } = $props();

	/** @typedef {import('$lib/types.js').RankingRow} Row */

	const PODIUM = 3;

	/** @type {import('@viniaraujo68/plinth/table').SortState} */
	let sort = $state({ key: 'total_profit_cents', direction: 'desc' });

	/** @type {import('@viniaraujo68/plinth/table').Column<Row>[]} */
	const columns = $derived([
		{ key: 'rank', label: '#', sortable: false, align: 'center', class: 'w-12', cell: rankCell },
		{ key: 'name', label: t('ranking.player'), class: 'font-semibold', cell: nameCell },
		{
			key: 'total_profit_cents',
			label: t('ranking.totalProfit'),
			numeric: true,
			cell: totalProfitCell
		},
		{ key: 'nights_played', label: t('ranking.nights'), numeric: true, cell: nightsCell },
		{ key: 'avg_profit_cents', label: t('ranking.avgPerNight'), numeric: true, cell: avgCell },
		{ key: 'roi', label: t('ranking.roi'), numeric: true, cell: roiCell }
	]);

	/** @param {number} index */
	const tier = (index) => (index < PODIUM ? String(index + 1) : undefined);

	/** @param {Row} r */
	const roiText = (r) => (r.roi != null ? (r.roi * 100).toFixed(0) + '%' : '—');
</script>

{#snippet rankCell(/** @type {Row} */ _r, /** @type {number} */ index)}
	<span class="rank" data-tier={tier(index)}>{index + 1}</span>
{/snippet}

{#snippet nameCell(/** @type {Row} */ r)}
	<span class="name">{r.name}</span>
{/snippet}

{#snippet totalProfitCell(/** @type {Row} */ r)}
	<span class="money {moneyClass(r.total_profit_cents)}">{formatSigned(r.total_profit_cents)}</span>
{/snippet}

{#snippet nightsCell(/** @type {Row} */ r)}
	<span class="text-base-content/80">{r.nights_played}</span>
{/snippet}

{#snippet avgCell(/** @type {Row} */ r)}
	<span class="money {moneyClass(r.avg_profit_cents)}">{formatMoney(r.avg_profit_cents)}</span>
{/snippet}

{#snippet roiCell(/** @type {Row} */ r)}
	<span class={r.roi != null ? moneyClass(r.roi) : 'text-base-content/65'}>{roiText(r)}</span>
{/snippet}

{#snippet playerCard(/** @type {Row} */ r, /** @type {number} */ index)}
	<div class="rcard">
		<span class="rank rc-rank" data-tier={tier(index)}>{index + 1}</span>
		<div class="rc-mid">
			<span class="rc-name">{r.name}</span>
			<span class="rc-sub text-base-content/65">
				{t('ranking.cardSub', {
					count: r.nights_played,
					avg: formatMoney(r.avg_profit_cents),
					roi: roiText(r)
				})}
			</span>
		</div>
		<span class="rc-profit money {moneyClass(r.total_profit_cents)}">
			{formatSigned(r.total_profit_cents)}
		</span>
	</div>
{/snippet}

{#if ranking.length === 0}
	<div class="px-5 py-12 text-center text-base-content/65">{t('ranking.empty')}</div>
{:else}
	<div class="ranking">
		<DataTable
			rows={ranking}
			{columns}
			rowKey={(r) => r.participant_id}
			bind:sort
			locale={localeTag()}
			label={t('tab.ranking')}
			sortLabel={(column) => t('ranking.sortByColumn', { column: column.label })}
			card={playerCard}
		/>
	</div>
{/if}

<style>
	.ranking :global(.table) {
		--table-ink-muted: var(--ink-muted);
	}

	.rank {
		display: inline-grid;
		place-items: center;
		min-width: 1.55em;
		min-height: 1.55em;
		padding: 0 0.3em;
		border-radius: 999px;
		font-size: 0.95rem;
		font-variant-numeric: tabular-nums;
		line-height: 1;
		color: var(--ink-muted);
	}
	.rank[data-tier] {
		font-weight: 700;
		color: var(--ink-primary);
		box-shadow: inset 0 0 0 1px color-mix(in oklch, var(--color-primary) 32%, transparent);
	}
	.rank[data-tier='2'] {
		background: color-mix(in oklch, var(--color-primary) 15%, transparent);
	}
	.rank[data-tier='1'] {
		background: var(--color-primary);
		color: var(--color-primary-content);
		box-shadow: none;
	}
	.name {
		overflow-wrap: anywhere;
	}

	.rcard {
		display: flex;
		align-items: center;
		gap: 12px;
	}
	.rc-rank {
		flex: none;
		font-size: 1rem;
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
</style>
