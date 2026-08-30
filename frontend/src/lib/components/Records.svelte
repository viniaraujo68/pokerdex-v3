<script>
	import { formatSigned, moneyClass } from '$lib/money.js';
	import { localeTag, t } from '$lib/i18n.svelte.js';

	/** @type {{ records: import('$lib/types.js').GroupRecord[], totalNights: number }} */
	let { records, totalNights } = $props();

	/** @param {string|null} d */
	function fmtDate(d) {
		return d ? new Date(d + 'T00:00:00').toLocaleDateString(localeTag()) : '';
	}

	// The backend ships Portuguese record labels; map the known ones, pass others through.
	/** @type {Record<string, string>} */
	const RECORD_KEYS = {
		'Maior vitória numa noite': 'records.bestWin',
		'Maior derrota numa noite': 'records.worstLoss'
	};
	/** @param {string} label */
	function recordLabel(label) {
		const key = RECORD_KEYS[label];
		return key ? t(key) : label;
	}
</script>

<div class="records">
	<div class="rec pd-card-tight pd-card">
		<span class="rec-label">{t('records.totalNights')}</span>
		<span class="rec-value">{totalNights}</span>
	</div>
	{#each records as rec (rec.label)}
		<div class="rec pd-card-tight pd-card">
			<span class="rec-label">{recordLabel(rec.label)}</span>
			{#if rec.value_cents != null}
				<span class="rec-value money {moneyClass(rec.value_cents)}">{formatSigned(rec.value_cents)}</span>
				<span class="rec-meta faint">{rec.participant_name ?? '?'} · {fmtDate(rec.night_date)}</span>
			{:else}
				<span class="rec-value faint">—</span>
			{/if}
		</div>
	{/each}
</div>

<style>
	.records {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
		gap: 14px;
	}
	.rec {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.rec-label {
		font-size: 0.8rem;
		color: var(--text-muted);
	}
	.rec-value {
		font-size: 1.5rem;
		font-weight: 700;
		font-family: var(--font-display);
	}
	.rec-meta {
		font-size: 0.78rem;
	}
</style>
