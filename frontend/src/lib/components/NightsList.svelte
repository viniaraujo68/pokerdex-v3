<script>
	import NightCard from './NightCard.svelte';
	import { t } from '$lib/i18n.svelte.js';

	/**
	 * `newNightHref` is what makes the empty state actionable. It's a prop and not derived
	 * from `editable` because this same component renders the public scoreboard, where a
	 * visitor has nowhere to create a night.
	 * @type {{
	 *   nights: import('$lib/types.js').Night[],
	 *   editable?: boolean,
	 *   newNightHref?: string,
	 *   onEdit?: (night: import('$lib/types.js').Night) => void,
	 *   onDelete?: (night: import('$lib/types.js').Night) => void,
	 *   onQuickEdit?: (
	 *     night: import('$lib/types.js').Night,
	 *     entry: import('$lib/types.js').Entry,
	 *     amounts: { buy_in_cents: number, cash_out_cents: number }
	 *   ) => Promise<void>
	 * }}
	 */
	let { nights, editable = false, newNightHref = '', onEdit, onDelete, onQuickEdit } = $props();

	let placeFilter = $state('');
	let dateFrom = $state('');
	let dateTo = $state('');
	/** @type {Set<number>} */
	let selectedPlayers = $state(new Set());

	// Distinct places present across the nights.
	const places = $derived.by(() => {
		/** @type {Map<number, string>} */
		const map = new Map();
		// `place_name` is only null when `place_id` is, so the `?? ''` never fires — it's here so
		// a malformed pairing sorts oddly instead of throwing inside `localeCompare`.
		for (const n of nights) if (n.place_id) map.set(n.place_id, n.place_name ?? '');
		return [...map].map(([id, name]) => ({ id, name })).sort((a, b) => a.name.localeCompare(b.name));
	});

	// Distinct participants present across the nights.
	const players = $derived.by(() => {
		/** @type {Map<number, string>} */
		const map = new Map();
		for (const n of nights) for (const e of n.entries) map.set(e.participant_id, e.participant_name);
		return [...map].map(([id, name]) => ({ id, name })).sort((a, b) => a.name.localeCompare(b.name));
	});

	const filtered = $derived(
		nights.filter((n) => {
			if (placeFilter && n.place_id !== Number(placeFilter)) return false;
			if (dateFrom && n.date < dateFrom) return false;
			if (dateTo && n.date > dateTo) return false;
			if (selectedPlayers.size) {
				const present = new Set(n.entries.map((e) => e.participant_id));
				for (const pid of selectedPlayers) if (!present.has(pid)) return false; // AND
			}
			return true;
		})
	);

	const activeFilterCount = $derived(
		(placeFilter !== '' ? 1 : 0) +
			(dateFrom !== '' ? 1 : 0) +
			(dateTo !== '' ? 1 : 0) +
			selectedPlayers.size
	);
	const hasFilters = $derived(activeFilterCount > 0);

	/**
	 * On a phone the filter card used to fill the screen before a single night showed up, so it
	 * collapses behind a summary row there. On desktop the CSS keeps the body open regardless and
	 * hides the toggle — this flag only ever matters under the small breakpoint.
	 */
	let filtersOpen = $state(false);

	// Client-side pagination: render in chunks to keep the DOM light.
	const PAGE = 20;
	let shown = $state(PAGE);

	// Reset pagination whenever the filters change.
	$effect(() => {
		placeFilter;
		dateFrom;
		dateTo;
		selectedPlayers;
		shown = PAGE;
	});

	const paged = $derived(filtered.slice(0, shown));

	/** @param {number} id */
	function togglePlayer(id) {
		const next = new Set(selectedPlayers);
		next.has(id) ? next.delete(id) : next.add(id);
		selectedPlayers = next;
	}

	function clearFilters() {
		placeFilter = '';
		dateFrom = '';
		dateTo = '';
		selectedPlayers = new Set();
	}
</script>

{#if nights.length === 0}
	<div class="card items-center gap-4 bg-base-100 px-5 py-12 text-center">
		<p class="text-base-content/65">{t('nights.empty')}</p>
		{#if newNightHref}
			<a href={newNightHref} class="btn btn-primary">{t('group.newNight')}</a>
		{/if}
	</div>
{:else}
	<div class="card filters bg-base-100 p-4">
		<!-- Mobile-only disclosure; `display:none` above the small breakpoint. -->
		<button
			type="button"
			class="fsummary"
			aria-expanded={filtersOpen}
			aria-controls="nights-filters"
			onclick={() => (filtersOpen = !filtersOpen)}
		>
			<span class="fs-label">{t('filters.title')}</span>
			{#if activeFilterCount > 0}
				<span class="badge badge-soft badge-primary flex-none">
					{t('filters.activeCount', { count: activeFilterCount })}
				</span>
			{/if}
			<span class="fs-caret" class:open={filtersOpen} aria-hidden="true">⌄</span>
		</button>

		<div class="fbody" id="nights-filters" class:open={filtersOpen}>
			<div class="ftop">
				<div class="frow">
					<label class="flabel" for="pf">{t('filters.place')}</label>
					<select id="pf" class="select w-full" bind:value={placeFilter}>
						<option value="">{t('filters.allPlaces')}</option>
						{#each places as p (p.id)}<option value={p.id}>{p.name}</option>{/each}
					</select>
				</div>
				<div class="frow">
					<label class="flabel" for="df">{t('filters.from')}</label>
					<input
						id="df"
						class="input w-full"
						type="date"
						bind:value={dateFrom}
						max={dateTo || undefined}
					/>
				</div>
				<div class="frow">
					<label class="flabel" for="dt">{t('filters.to')}</label>
					<input
						id="dt"
						class="input w-full"
						type="date"
						bind:value={dateTo}
						min={dateFrom || undefined}
					/>
				</div>
			</div>

			<div class="frow players">
				<span class="flabel mb-0.5" id="players-filter-label">{t('filters.playersPresent')}</span>
				<div class="flex flex-wrap gap-2" role="group" aria-labelledby="players-filter-label">
					{#each players as p (p.id)}
						<button
							type="button"
							class="btn btn-sm toggle-chip"
							class:btn-soft={selectedPlayers.has(p.id)}
							class:btn-primary={selectedPlayers.has(p.id)}
							aria-pressed={selectedPlayers.has(p.id)}
							onclick={() => togglePlayer(p.id)}
						>
							{p.name}
						</button>
					{/each}
				</div>
				{#if selectedPlayers.size > 1}
					<span class="text-[0.78rem] text-base-content/65">{t('filters.andHint')}</span>
				{/if}
			</div>
		</div>

		<div class="fmeta">
			<span class="text-base-content/80">
				{t('filters.nightCount', {
					shown: filtered.length,
					total: nights.length,
					count: nights.length
				})}
			</span>
			{#if hasFilters}
				<button class="btn btn-sm" onclick={clearFilters}>{t('filters.clear')}</button>
			{/if}
		</div>
	</div>

	{#if filtered.length === 0}
		<div class="card bg-base-100 px-5 py-12 text-center text-base-content/65">
			{t('nights.noneWithFilters')}
		</div>
	{:else}
		<div class="flex flex-col gap-4">
			{#each paged as night (night.id)}
				<NightCard {night} {editable} {onEdit} {onDelete} {onQuickEdit} />
			{/each}
		</div>
		{#if filtered.length > shown}
			<button class="btn mt-1 w-full" onclick={() => (shown += PAGE)}>
				{t('nights.showMore', { remaining: filtered.length - shown })}
			</button>
		{/if}
	{/if}
{/if}

<style>
	.filters {
		display: flex;
		flex-direction: column;
		gap: 14px;
		margin-bottom: 16px;
	}
	/* ---------- mobile disclosure ---------- */
	.fsummary {
		display: none; /* desktop: no toggle, the body is always open */
	}
	.fbody {
		display: flex;
		flex-direction: column;
		gap: 14px;
	}
	@media (max-width: 560px) {
		.fsummary {
			display: flex;
			align-items: center;
			gap: 10px;
			width: 100%;
			min-height: 44px;
			background: none;
			border: none;
			padding: 0;
			color: var(--color-base-content);
			font-family: inherit;
			font-size: 0.92rem;
			font-weight: 600;
			cursor: pointer;
			text-align: left;
		}
		.fs-label {
			flex: 1;
			min-width: 0;
		}
		.fs-caret {
			flex: 0 0 auto;
			font-size: 1.3rem;
			line-height: 1;
			color: color-mix(in oklch, var(--color-base-content) 65%, transparent);
			transition: transform 0.2s ease;
		}
		.fs-caret.open {
			transform: rotate(180deg);
		}
		.fbody {
			display: none;
		}
		.fbody.open {
			display: flex;
		}
	}
	.ftop {
		display: flex;
		flex-wrap: wrap;
		gap: 14px;
	}
	.ftop .frow {
		flex: 1;
		min-width: 150px;
	}
	.frow {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.flabel {
		font-size: 0.75rem;
		font-weight: 500;
		color: color-mix(in oklch, var(--color-base-content) 80%, transparent);
	}
	/* thumb-sized: these chips are the main filter control on a phone */
	.toggle-chip {
		min-height: 44px;
	}
	.fmeta {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
		border-top: 1px solid color-mix(in oklch, var(--color-base-content) 10%, transparent);
		padding-top: 12px;
		font-size: 0.9rem;
	}
</style>
