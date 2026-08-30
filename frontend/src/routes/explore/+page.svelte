<script>
	import { get, errorMessage } from '$lib/api.js';
	import { t } from '$lib/i18n.svelte.js';
	import GroupCard from '$lib/components/GroupCard.svelte';

	/** @type {{ data: { groups: import('$lib/types.js').PublicGroupSummary[], status: number } }} */
	let { data } = $props();

	let query = $state('');
	let searching = $state(false);
	/** The query whose results are currently on screen, for the "no results" message. */
	let shownQuery = $state('');
	/** @type {ReturnType<typeof setTimeout>|undefined} */
	let timer;

	/** Results of the latest client search; until one lands, the server's listing stands. */
	let searched = $state(/** @type {import('$lib/types.js').PublicGroupSummary[]|null} */ (null));
	const results = $derived(searched ?? data.groups);

	/** Same idea for the failure state: the load's status until a client search overrides it. */
	let searchStatus = $state(/** @type {number|null} */ (null));
	/** Message from a client search that failed (already localized by api.js). */
	let searchError = $state('');
	const status = $derived(searchStatus ?? data.status);
	const error = $derived(
		searchError ||
			(status === 200 ? '' : status === 0 ? t('error.body') : t('error.http', { status }))
	);

	/**
	 * Monotonic request id. Typing fires overlapping requests and they can come back out of
	 * order, so anything but the newest reply is dropped instead of overwriting the grid.
	 */
	let latest = 0;
	/** Not `$state`: flipping it must not re-run the effect that reads it. */
	let firstRun = true;

	$effect(() => {
		// debounce search on query change
		const q = query;
		if (firstRun) {
			firstRun = false;
			// The load already fetched the empty query — no need to do it again. If it failed,
			// though, an immediate retry from the browser is exactly what we want.
			if (q === '' && data.status === 200) return;
		}
		clearTimeout(timer);
		timer = setTimeout(() => search(q), 250);
		return () => clearTimeout(timer);
	});

	/** @param {string} q */
	async function search(q) {
		const ticket = ++latest;
		searching = true;
		try {
			const found = await get(`/public?q=${encodeURIComponent(q.trim())}`);
			if (ticket !== latest) return; // a newer keystroke already won
			searched = found;
			shownQuery = q;
			searchError = '';
			searchStatus = 200;
		} catch (e) {
			if (ticket !== latest) return;
			searchError = errorMessage(e);
		} finally {
			// Only the newest request may clear the indicator, or an early reply would hide the
			// fact that a later one is still in flight.
			if (ticket === latest) searching = false;
		}
	}
</script>

<svelte:head>
	<title>{t('title.explore')}</title>
	<meta name="description" content={t('explore.subtitle')} />
</svelte:head>

<div class="head">
	<h1>{t('explore.title')}</h1>
	<p class="muted">{t('explore.subtitle')}</p>
</div>

<div class="searchbar">
	<input class="search" placeholder={t('explore.searchPlaceholder')} bind:value={query} />
	<!-- Subtle and inline: the results below stay put while this is up. The live region itself is
	     always mounted so the text landing inside it is what gets announced. -->
	<span class="searching" role="status">
		{#if searching}
			<span class="spinner spinner-sm" aria-hidden="true"></span>
			<span class="faint">{t('explore.searching')}</span>
		{/if}
	</span>
</div>

{#if error}
	<div class="pd-toast pd-toast-error">{error}</div>
{:else if results.length === 0}
	<div class="pd-card empty">
		{shownQuery.trim() ? t('explore.noResults', { query: shownQuery }) : t('explore.empty')}
	</div>
{:else}
	<!-- `stale` only dims: replacing the grid with a spinner on every keystroke made the page
	     flash and lose the user's place. -->
	<div class="groups pd-grid" class:stale={searching}>
		{#each results as g (g.slug)}
			<GroupCard group={g} href={`/g/${g.slug}`} />
		{/each}
	</div>
{/if}

<style>
	.head {
		margin-bottom: 20px;
	}
	.searchbar {
		display: flex;
		align-items: center;
		gap: 12px;
		flex-wrap: wrap;
		margin-bottom: 24px;
	}
	/* Fixed basis: the input's width must not depend on whether the indicator is showing. */
	.search {
		flex: 0 0 min(420px, 100%);
	}
	.searching {
		display: flex;
		align-items: center;
		gap: 8px;
		min-height: 20px;
		font-size: 0.82rem;
		flex: 0 0 auto;
	}
	.spinner-sm {
		width: 14px;
		height: 14px;
		border-width: 2px;
	}
	.stale {
		opacity: 0.55;
		transition: opacity 0.15s ease;
	}
	.groups {
		grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
	}
</style>
