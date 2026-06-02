<script>
	import { formatSigned, moneyClass } from '$lib/money.js';

	/** @type {{ records: Array<any>, totalNights: number }} */
	let { records, totalNights } = $props();

	function fmtDate(d) {
		return d ? new Date(d + 'T00:00:00').toLocaleDateString('pt-BR') : '';
	}
</script>

<div class="records">
	<div class="rec card-tight card">
		<span class="rec-label">Noites registradas</span>
		<span class="rec-value">{totalNights}</span>
	</div>
	{#each records as rec}
		<div class="rec card-tight card">
			<span class="rec-label">{rec.label}</span>
			{#if rec.participant_name}
				<span class="rec-value money {moneyClass(rec.value_cents)}">{formatSigned(rec.value_cents)}</span>
				<span class="rec-meta faint">{rec.participant_name} · {fmtDate(rec.night_date)}</span>
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
