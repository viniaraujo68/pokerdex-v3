<script>
	import { onMount } from 'svelte';
	import { formatMoney, formatMoneyAxis } from '$lib/money.svelte.js';
	import { i18n, localeTag, t } from '$lib/i18n.svelte.js';

	/** @type {{ evolution: import('$lib/types.js').Evolution }} */
	let { evolution } = $props();

	/** $state so the render effect below re-runs when `bind:this` first hands us the element. */
	let canvas = $state(/** @type {HTMLCanvasElement|undefined} */ (undefined));
	/** @type {import('chart.js').Chart | null} */
	let chart = null;
	/** Guards against two renders overlapping across the dynamic `import()` await. */
	let renderTicket = 0;

	/**
	 * Series palette as `[custom property, fallback]`. Chart.js needs concrete colours (it
	 * paints to a canvas, where `var(--x)` means nothing), so the tokens are resolved off
	 * `:root` at render time — a token edit in app.css lands here with no change to this file.
	 * The last three have no token of their own; they only exist to keep 8 series apart.
	 */
	const PALETTE = [
		['--felt-bright', '#9d5cff'],
		['--gold', '#ffd23f'],
		['', '#c084fc'],
		['--blue', '#60a5fa'],
		['--red', '#f0586a'],
		['--green-pos', '#4ade80'],
		['', '#f59e0b'],
		['', '#e879f9']
	];

	/** Resolved token values for one render. @returns {(name: string, fallback: string) => string} */
	function tokenReader() {
		const styles = typeof document === 'undefined' ? null : getComputedStyle(document.documentElement);
		return (name, fallback) => (name && styles?.getPropertyValue(name).trim()) || fallback;
	}

	/** @param {string} d */
	function labelFor(d) {
		return new Date(d + 'T00:00:00').toLocaleDateString(localeTag(), {
			day: '2-digit',
			month: 'short'
		});
	}

	/**
	 * @param {string[]} dates
	 * @param {import('$lib/types.js').EvolutionSeries[]} series
	 */
	async function render(dates, series) {
		const ticket = ++renderTicket;
		const { Chart } = await import('chart.js/auto');
		if (ticket !== renderTicket) return; // superseded while the module was loading
		if (chart) chart.destroy();
		if (!canvas) return;

		const token = tokenReader();
		const legendColor = token('--text-muted', '#9a92b5');
		const axisColor = token('--text-faint', '#857da3');
		// No token for the gridlines: a hairline of the page's own white, not part of the palette.
		const gridColor = 'rgba(255,255,255,0.05)';

		const labels = dates.map(labelFor);
		const datasets = series.map((s, i) => {
			const [name, fallback] = PALETTE[i % PALETTE.length];
			const color = token(name, fallback);
			return {
				label: s.name,
				// null = before this player's first night; Chart.js skips those points.
				data: s.points.map((p) => (p.cumulative_cents === null ? null : p.cumulative_cents / 100)),
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
						labels: { color: legendColor, usePointStyle: true, pointStyle: 'line', padding: 16 }
					},
					tooltip: {
						// Hide players who hadn't joined yet at this date (null points).
						filter: (item) => item.parsed.y !== null,
						callbacks: {
							// `?? 0` is unreachable — the filter above drops null points — but the
							// callback's own type doesn't know that.
							label: (ctx) => `${ctx.dataset.label}: ${formatMoney((ctx.parsed.y ?? 0) * 100)}`
						}
					}
				},
				scales: {
					x: { grid: { color: gridColor }, ticks: { color: axisColor } },
					y: {
						grid: { color: gridColor },
						ticks: {
							color: axisColor,
							callback: (v) => formatMoneyAxis(Number(v) * 100)
						}
					}
				}
			}
		});
	}

	// Cleanup only. `onMount(render)` used to run alongside the $effect below, building the chart
	// twice on every mount (two Chart instances racing for one canvas).
	onMount(() => () => chart?.destroy());

	/**
	 * The single render path: mount, new data, and locale switch (axis/tooltip formats) all come
	 * through here. Everything reactive is read *before* the first await inside render() — the
	 * dynamic `import('chart.js')` would otherwise end the tracked scope and the effect would
	 * stop re-running on a locale change.
	 */
	$effect(() => {
		const dates = evolution?.dates;
		const series = evolution?.series;
		i18n.locale; // tracked: labelFor()/the money callbacks are locale-dependent
		if (!canvas || !dates || !series) return;
		render(dates, series);
	});
</script>

{#if evolution.dates.length === 0}
	<div class="empty">{t('chart.empty')}</div>
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
