<script>
	import { onMount } from 'svelte';

	/** @type {{ evolution: { dates: string[], series: Array<{name:string, points:{date:string, cumulative_cents:number}[]}> } }} */
	let { evolution } = $props();

	let canvas;
	/** @type {import('chart.js').Chart | null} */
	let chart = null;

	const PALETTE = ['#9d5cff', '#ffd23f', '#c084fc', '#60a5fa', '#f0586a', '#4ade80', '#f59e0b', '#e879f9'];

	function labelFor(d) {
		return new Date(d + 'T00:00:00').toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' });
	}

	async function render() {
		const { Chart } = await import('chart.js/auto');
		if (chart) chart.destroy();
		if (!canvas) return;

		const labels = evolution.dates.map(labelFor);
		const datasets = evolution.series.map((s, i) => {
			const color = PALETTE[i % PALETTE.length];
			return {
				label: s.name,
				data: s.points.map((p) => p.cumulative_cents / 100),
				borderColor: color,
				backgroundColor: color,
				tension: 0.3,
				borderWidth: 2,
				pointRadius: 2,
				pointHoverRadius: 5
			};
		});

		chart = new Chart(canvas, {
			type: 'line',
			data: { labels, datasets },
			options: {
				responsive: true,
				maintainAspectRatio: false,
				interaction: { mode: 'index', intersect: false },
				plugins: {
					legend: {
						labels: { color: '#9a92b5', usePointStyle: true, pointStyle: 'line', padding: 16 }
					},
					tooltip: {
						callbacks: {
							label: (ctx) =>
								`${ctx.dataset.label}: ${ctx.parsed.y.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}`
						}
					}
				},
				scales: {
					x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#645c80' } },
					y: {
						grid: { color: 'rgba(255,255,255,0.05)' },
						ticks: {
							color: '#645c80',
							callback: (v) => 'R$ ' + Number(v).toLocaleString('pt-BR')
						}
					}
				}
			}
		});
	}

	onMount(() => {
		render();
		return () => chart?.destroy();
	});

	// Re-render when data changes.
	$effect(() => {
		if (evolution) render();
	});
</script>

{#if evolution.dates.length === 0}
	<div class="empty">Sem dados para o gráfico ainda.</div>
{:else}
	<div class="chart-wrap">
		<canvas bind:this={canvas}></canvas>
	</div>
{/if}

<style>
	.chart-wrap {
		position: relative;
		height: 320px;
		width: 100%;
	}
</style>
