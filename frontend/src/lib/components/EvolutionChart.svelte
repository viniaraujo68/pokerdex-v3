<script>
	import { onMount, untrack } from 'svelte';
	import { getThemeContext } from '@viniaraujo68/plinth/theme';
	import { formatMoney, formatMoneyAxis, formatSigned } from '$lib/money.svelte.js';
	import { i18n, localeTag, t } from '$lib/i18n.svelte.js';

	/** @type {{ evolution: import('$lib/types.js').Evolution }} */
	let { evolution } = $props();

	const theme = getThemeContext();

	/**
	 * @typedef {object} Series
	 * @property {string} id
	 * @property {string} label
	 * @property {string} color CSS colour expression, resolved per scheme by the probe.
	 * @property {(number|null)[]} values Cents, `null` where the series has no data yet.
	 */

	const SLOT_COUNT = 8;
	const OTHERS_ID = 'others';
	const DIRECT_LABEL_MAX_SERIES = 4;
	const DIRECT_LABEL_MIN_CANVAS = 520;
	const DIRECT_LABEL_MAX_WIDTH = 120;
	const DIRECT_LABEL_GAP = 15;

	/** $state so the render effect below re-runs when `bind:this` first hands us the element. */
	let canvas = $state(/** @type {HTMLCanvasElement|undefined} */ (undefined));
	/** @type {import('chart.js').Chart | null} */
	let chart = null;
	/** Guards against two renders overlapping across the dynamic `import()` await. */
	let renderTicket = 0;

	let hiddenIds = $state(/** @type {string[]} */ ([]));

	const series = $derived(buildSeries(evolution));
	const hiddenCount = $derived(series.filter((s) => hiddenIds.includes(s.id)).length);
	const allHidden = $derived(series.length > 0 && hiddenCount === series.length);

	/**
	 * Resolves any CSS colour expression against the chart's own place in the tree, by parking a
	 * probe element there and reading its computed `color` back as `rgb(...)`.
	 *
	 * Chart.js paints to a canvas, where `var(--x)` means nothing and `light-dark()` — which every
	 * theme token and every series slot is declared through — cannot be read back off a custom
	 * property at all: `getPropertyValue` hands back the literal `light-dark(a, b)` text. Going
	 * through a real element in the chart's subtree is also what makes both the theme colours and
	 * the series palette follow a subtree `[data-theme]`.
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

	/**
	 * @param {import('$lib/types.js').EvolutionSeries} s
	 * @param {number} length
	 * @returns {(number|null)[]}
	 */
	function centsOf(s, length) {
		return Array.from({ length }, (_, i) => s.points[i]?.cumulative_cents ?? null);
	}

	/**
	 * @param {(number|null)[][]} lists
	 * @param {number} length
	 * @returns {(number|null)[]}
	 */
	function sumOf(lists, length) {
		return Array.from({ length }, (_, i) => {
			const present = lists.map((l) => l[i]).filter((v) => v !== null);
			return present.length === 0 ? null : present.reduce((a, b) => a + Number(b), 0);
		});
	}

	/**
	 * @param {import('$lib/types.js').Evolution|undefined} data
	 * @returns {Series[]}
	 */
	function buildSeries(data) {
		const incoming = data?.series ?? [];
		const length = data?.dates?.length ?? 0;
		/** @type {Map<number, number>} */
		const slots = new Map();
		[...incoming]
			.sort((a, b) => a.participant_id - b.participant_id)
			.slice(0, SLOT_COUNT)
			.forEach((s, i) => slots.set(s.participant_id, i + 1));

		/** @type {Series[]} */
		const built = [];
		/** @type {import('$lib/types.js').EvolutionSeries[]} */
		const rest = [];
		for (const s of incoming) {
			const slot = slots.get(s.participant_id);
			if (slot === undefined) {
				rest.push(s);
				continue;
			}
			built.push({
				id: String(s.participant_id),
				label: s.name,
				color: `var(--series-${slot})`,
				values: centsOf(s, length)
			});
		}
		if (rest.length > 0) {
			built.push({
				id: OTHERS_ID,
				label: t('chart.others', { count: rest.length }),
				color: 'var(--series-other)',
				values: sumOf(
					rest.map((s) => centsOf(s, length)),
					length
				)
			});
		}
		return built;
	}

	/** @param {Series} s */
	function currentValue(s) {
		for (let i = s.values.length - 1; i >= 0; i--) {
			if (s.values[i] !== null) return s.values[i];
		}
		return null;
	}

	/** @param {string} id */
	function isHidden(id) {
		return hiddenIds.includes(id);
	}

	/** @param {string} id */
	function toggle(id) {
		hiddenIds = isHidden(id) ? hiddenIds.filter((h) => h !== id) : [...hiddenIds, id];
		syncVisibility();
	}

	function showAll() {
		hiddenIds = [];
		syncVisibility();
	}

	function syncVisibility() {
		if (!chart) return;
		series.forEach((s, i) => chart?.setDatasetVisibility(i, !isHidden(s.id)));
		chart.update();
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
	 * @param {Series[]} entries
	 */
	async function render(dates, entries) {
		const ticket = ++renderTicket;
		const { Chart } = await import('chart.js/auto');
		if (ticket !== renderTicket) return; // superseded while the module was loading
		if (chart) chart.destroy();
		if (!canvas) return;

		const host = canvas.parentElement ?? document.body;
		const resolve = colorResolver(host);
		const ink = (/** @type {number} */ percent, /** @type {string} */ fallback) =>
			resolve.read(`color-mix(in oklch, var(--color-base-content) ${percent}%, transparent)`, fallback);
		const textColor = ink(85, '#c8cee0');
		const axisColor = ink(65, '#857da3');
		// The gridlines and the crosshair are the page's own ink at hairline strength, never
		// part of the series palette.
		const gridColor = ink(10, 'rgba(127,127,127,0.12)');
		const crosshairColor = ink(28, 'rgba(127,127,127,0.3)');
		const surface = resolve.read('var(--color-base-100)', '#ffffff');
		const fontFamily = getComputedStyle(host).fontFamily;
		const labelFont = `500 11px ${fontFamily}`;

		const hiddenNow = untrack(() => new Set(hiddenIds));
		const labels = dates.map(labelFor);
		const pointRadius = dates.length <= 24 ? 4 : 0;

		const datasets = entries.map((s) => {
			const color = resolve.read(s.color, '#6f4bd4');
			return {
				label: s.label,
				// null = before this player's first night; Chart.js skips those points.
				data: s.values.map((v) => (v === null ? null : v / 100)),
				borderColor: color,
				backgroundColor: color,
				hidden: hiddenNow.has(s.id),
				tension: 0.3,
				borderWidth: 2,
				pointRadius,
				pointBorderColor: surface,
				pointBorderWidth: pointRadius > 0 ? 2 : 0,
				pointHoverRadius: 5,
				pointHoverBorderColor: surface,
				pointHoverBorderWidth: 2
			};
		});

		const padding = { top: 8, right: 8, bottom: 0, left: 0 };

		/** @param {import('chart.js').Chart} c */
		function visibleIndexes(c) {
			return c.data.datasets.map((_, i) => i).filter((i) => c.isDatasetVisible(i));
		}

		/** @param {import('chart.js').Chart} c */
		function directLabelsFit(c) {
			const shown = visibleIndexes(c);
			return (
				shown.length >= 1 && shown.length <= DIRECT_LABEL_MAX_SERIES && c.width >= DIRECT_LABEL_MIN_CANVAS
			);
		}

		const crosshair = {
			id: 'crosshair',
			/** @param {import('chart.js').Chart} c */
			beforeDatasetsDraw(c) {
				const active = c.getActiveElements();
				if (active.length === 0) return;
				const { x } = active[0].element;
				const ctx = c.ctx;
				ctx.save();
				ctx.beginPath();
				ctx.lineWidth = 1;
				ctx.strokeStyle = crosshairColor;
				ctx.moveTo(x, c.chartArea.top);
				ctx.lineTo(x, c.chartArea.bottom);
				ctx.stroke();
				ctx.restore();
			}
		};

		const directLabels = {
			id: 'directLabels',
			/** @param {import('chart.js').Chart} c */
			beforeLayout(c) {
				if (!directLabelsFit(c)) {
					padding.right = 8;
					return;
				}
				c.ctx.save();
				c.ctx.font = labelFont;
				const widest = visibleIndexes(c).reduce(
					(max, i) => Math.max(max, c.ctx.measureText(String(c.data.datasets[i].label)).width),
					0
				);
				c.ctx.restore();
				padding.right = 10 + Math.min(Math.ceil(widest), DIRECT_LABEL_MAX_WIDTH);
			},
			/** @param {import('chart.js').Chart} c */
			afterDatasetsDraw(c) {
				if (!directLabelsFit(c)) return;
				/** @type {{ x: number, y: number, text: string }[]} */
				const placed = [];
				for (const i of visibleIndexes(c)) {
					const values = c.data.datasets[i].data;
					let last = -1;
					for (let k = values.length - 1; k >= 0; k--) {
						if (values[k] !== null && values[k] !== undefined) {
							last = k;
							break;
						}
					}
					if (last < 0) continue;
					const element = c.getDatasetMeta(i).data[last];
					if (!element) continue;
					placed.push({ x: element.x, y: element.y, text: String(c.data.datasets[i].label) });
				}
				placed.sort((a, b) => a.y - b.y);
				let floor = c.chartArea.top + 6;
				for (const p of placed) {
					p.y = Math.min(Math.max(p.y, floor), c.chartArea.bottom);
					floor = p.y + DIRECT_LABEL_GAP;
				}
				const ctx = c.ctx;
				ctx.save();
				ctx.font = labelFont;
				ctx.fillStyle = textColor;
				ctx.textAlign = 'left';
				ctx.textBaseline = 'middle';
				for (const p of placed) ctx.fillText(p.text, p.x + 8, p.y, DIRECT_LABEL_MAX_WIDTH);
				ctx.restore();
			}
		};

		chart = new Chart(canvas, {
			type: 'line',
			data: { labels, datasets },
			plugins: [crosshair, directLabels],
			options: {
				responsive: true,
				maintainAspectRatio: false,
				layout: { padding },
				interaction: { mode: 'index', intersect: false },
				plugins: {
					legend: { display: false },
					tooltip: {
						backgroundColor: surface,
						borderColor: ink(14, 'rgba(127,127,127,0.16)'),
						borderWidth: 1,
						titleColor: axisColor,
						bodyColor: textColor,
						padding: 10,
						cornerRadius: 8,
						boxPadding: 4,
						usePointStyle: true,
						// Hide players who hadn't joined yet at this date (null points).
						filter: (item) => item.parsed.y !== null,
						itemSort: (a, b) => (b.parsed.y ?? 0) - (a.parsed.y ?? 0),
						callbacks: {
							labelPointStyle: () => ({ pointStyle: 'line', rotation: 0 }),
							labelColor: (ctx) => {
								const color = String(ctx.dataset.borderColor);
								return { borderColor: color, backgroundColor: color, borderWidth: 2 };
							},
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
	 * stop re-running on a locale change. `hiddenIds` is deliberately NOT tracked: a toggle is
	 * handled in place by syncVisibility(), and re-rendering on it would throw away the
	 * transition and re-run the whole build for a visibility flip.
	 */
	$effect(() => {
		const dates = evolution?.dates;
		const entries = series;
		i18n.locale; // tracked: labelFor()/the money callbacks are locale-dependent
		// Both tracked: `preference` catches an explicit pick (including one that lands on the
		// scheme the OS was already showing), `dark` catches the OS moving under "system".
		theme.preference;
		theme.dark;
		if (!canvas || !dates || !entries) return;
		render(dates, entries);
	});
</script>

{#if evolution.dates.length === 0}
	<div class="px-5 py-12 text-center text-base-content/65">{t('chart.empty')}</div>
{:else}
	<div class="evolution">
		<div class="chart-wrap">
			<canvas bind:this={canvas}></canvas>
			{#if allHidden}
				<p class="empty-overlay">{t('chart.allHidden')}</p>
			{/if}
		</div>

		{#if series.length >= 2}
			<div class="legend" role="group" aria-label={t('chart.series')}>
				{#each series as s (s.id)}
					<button
						type="button"
						class="chip"
						class:off={isHidden(s.id)}
						aria-pressed={!isHidden(s.id)}
						onclick={() => toggle(s.id)}
					>
						<span class="swatch" style="--swatch: {s.color}"></span>
						<span class="name">{s.label}</span>
						<span class="value">{formatSigned(currentValue(s))}</span>
					</button>
				{/each}
				{#if hiddenCount > 0}
					<button type="button" class="reset" onclick={showAll}>{t('chart.showAll')}</button>
				{/if}
			</div>
		{/if}
	</div>
{/if}

<style>
	.evolution {
		--series-1: light-dark(#2a78d6, #3987e5);
		--series-2: light-dark(#eb6834, #d95926);
		--series-3: light-dark(#1baf7a, #199e70);
		--series-4: light-dark(#eda100, #c98500);
		--series-5: light-dark(#e87ba4, #d55181);
		--series-6: light-dark(#008300, #008300);
		--series-7: light-dark(#4a3aa7, #9085e9);
		--series-8: light-dark(#e34948, #e66767);
		--series-other: color-mix(in oklch, var(--color-base-content) 45%, var(--color-base-100));
		display: flex;
		flex-direction: column;
		gap: 14px;
	}

	.chart-wrap {
		position: relative;
		height: 320px;
		width: 100%;
	}

	.empty-overlay {
		position: absolute;
		inset: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		margin: 0;
		font-size: 0.85rem;
		color: color-mix(in oklch, var(--color-base-content) 60%, transparent);
		pointer-events: none;
	}

	.legend {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}

	.chip {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		min-height: 36px;
		padding: 6px 12px;
		border: 1px solid color-mix(in oklch, var(--color-base-content) 14%, transparent);
		border-radius: var(--radius-field, 0.5rem);
		background-color: var(--color-base-100);
		font-size: 0.8rem;
		line-height: 1.2;
		cursor: pointer;
		transition:
			background-color 0.15s,
			border-color 0.15s,
			opacity 0.15s;
	}

	.chip:hover {
		background-color: color-mix(in oklch, var(--color-base-content) 6%, var(--color-base-100));
	}

	.chip:focus-visible,
	.reset:focus-visible {
		outline: 2px solid var(--color-primary);
		outline-offset: 2px;
	}

	.swatch {
		flex: none;
		width: 12px;
		height: 12px;
		border-radius: 3px;
		background-color: var(--swatch);
	}

	.name {
		font-weight: 500;
		color: var(--color-base-content);
	}

	.value {
		color: color-mix(in oklch, var(--color-base-content) 62%, transparent);
		font-variant-numeric: tabular-nums;
	}

	.chip.off {
		border-style: dashed;
		background-color: transparent;
	}

	.chip.off .swatch {
		background-color: transparent;
		box-shadow: inset 0 0 0 2px var(--swatch);
	}

	.chip.off .name {
		color: color-mix(in oklch, var(--color-base-content) 55%, transparent);
		text-decoration: line-through;
	}

	.chip.off .value {
		color: color-mix(in oklch, var(--color-base-content) 40%, transparent);
	}

	.reset {
		min-height: 36px;
		padding: 6px 12px;
		border: 1px solid transparent;
		border-radius: var(--radius-field, 0.5rem);
		background-color: color-mix(in oklch, var(--color-primary) 12%, transparent);
		color: var(--color-primary);
		font-size: 0.8rem;
		font-weight: 600;
		cursor: pointer;
	}

	.reset:hover {
		background-color: color-mix(in oklch, var(--color-primary) 20%, transparent);
	}

	@media (max-width: 560px) {
		.chip,
		.reset {
			min-height: 44px;
		}
	}
</style>
