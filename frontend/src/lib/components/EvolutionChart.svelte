<script>
	import { onMount } from 'svelte';
	import { getThemeContext } from '@viniaraujo68/plinth/theme';
	import { formatMoney, formatMoneyAxis } from '$lib/money.svelte.js';
	import { i18n, localeTag, t } from '$lib/i18n.svelte.js';

	/** @type {{ evolution: import('$lib/types.js').Evolution }} */
	let { evolution } = $props();

	const theme = getThemeContext();

	/** $state so the render effect below re-runs when `bind:this` first hands us the element. */
	let canvas = $state(/** @type {HTMLCanvasElement|undefined} */ (undefined));
	/** @type {import('chart.js').Chart | null} */
	let chart = null;
	/** Guards against two renders overlapping across the dynamic `import()` await. */
	let renderTicket = 0;

	/**
	 * Series palette, written as CSS colour expressions. Chart.js paints to a canvas, where
	 * `var(--x)` means nothing and `light-dark()` — which every theme token is declared through —
	 * cannot be read back off a custom property at all: `getPropertyValue` hands back the literal
	 * `light-dark(a, b)` text. So each entry is resolved through a real element instead (see
	 * `colorResolver`), which is also what makes the palette follow a subtree `[data-theme]`.
	 * The last two are outside the theme: eight series need more hues than it defines.
	 */
	const PALETTE = [
		'var(--color-primary)',
		'var(--color-warning)',
		'var(--color-info)',
		'var(--color-success)',
		'var(--color-error)',
		'var(--color-secondary)',
		'#d946ef',
		'#0d9488'
	];

	/**
	 * Resolves any CSS colour expression against the chart's own place in the tree, by parking a
	 * probe element there and reading its computed `color` back as `rgb(...)`.
	 * @param {HTMLElement} host
	 */
	function colorResolver(host) {
		const probe = document.createElement('span');
		probe.style.position = 'absolute';
		probe.style.visibility = 'hidden';
		probe.style.pointerEvents = 'none';
		host.appendChild(probe);
		return {
			/** @param {string} expression @param {string} fallback */
			read(expression, fallback) {
				probe.style.color = '';
				probe.style.color = expression;
				return getComputedStyle(probe).color || fallback;
			},
			done() {
				probe.remove();
			}
		};
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

		const resolve = colorResolver(canvas.parentElement ?? document.body);
		const ink = (/** @type {number} */ percent, /** @type {string} */ fallback) =>
			resolve.read(`color-mix(in oklch, var(--color-base-content) ${percent}%, transparent)`, fallback);
		const legendColor = ink(80, '#9a92b5');
		const axisColor = ink(65, '#857da3');
		// The gridlines are the page's own ink at a hairline strength, not part of the palette.
		const gridColor = ink(10, 'rgba(127,127,127,0.12)');

		const labels = dates.map(labelFor);
		const datasets = series.map((s, i) => {
			const color = resolve.read(PALETTE[i % PALETTE.length], '#6f4bd4');
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

		resolve.done();
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
		// Both tracked: `preference` catches an explicit pick (including one that lands on the
		// scheme the OS was already showing), `dark` catches the OS moving under "system".
		theme.preference;
		theme.dark;
		if (!canvas || !dates || !series) return;
		render(dates, series);
	});
</script>

{#if evolution.dates.length === 0}
	<div class="px-5 py-12 text-center text-base-content/65">{t('chart.empty')}</div>
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
