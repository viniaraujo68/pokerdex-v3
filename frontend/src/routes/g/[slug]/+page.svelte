<script>
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import RankingTable from '$lib/components/RankingTable.svelte';
	import Records from '$lib/components/Records.svelte';
	import EvolutionChart from '$lib/components/EvolutionChart.svelte';
	import NightsList from '$lib/components/NightsList.svelte';
	import TabBar from '$lib/components/TabBar.svelte';
	import { t } from '$lib/i18n.svelte.js';

	/** Fetched in `+page.js` so the scoreboard is in the server-rendered HTML. */
	/** @type {{ data: { group: any, status: number } }} */
	let { data } = $props();

	const group = $derived(data.group);
	/** Present only on private groups, which are shared as `/g/<slug>?t=<token>`. */
	const token = $derived($page.url.searchParams.get('t'));

	// Localized here rather than in the load: the load runs on the server (where the locale is
	// still the pt-BR default), while this re-renders when the visitor switches language.
	// No 404 branch: the load turns a missing slug into a real `error(404)` so crawlers get the
	// right status, and `+error.svelte` takes over. 403 lands here on purpose — see +page.js.
	const error = $derived(
		data.status === 200
			? ''
			: data.status === 403
				? t('public.errorPrivate')
				: data.status === 0
					? t('error.body')
					: t('error.http', { status: data.status })
	);

	// Tab in the URL, like the owner's group page — a shared link keeps its tab, and Back
	// walks the tabs instead of leaving the scoreboard. `?t=` (share token) rides along.
	const TAB_IDS = ['ranking', 'stats', 'nights'];
	const DEFAULT_TAB = 'ranking';
	const tab = $derived.by(() => {
		const requested = $page.url.searchParams.get('tab');
		return requested && TAB_IDS.includes(requested) ? requested : DEFAULT_TAB;
	});

	const tabs = $derived([
		{ id: 'ranking', label: t('tab.ranking') },
		{ id: 'stats', label: t('tab.stats') },
		{ id: 'nights', label: t('tab.nights') }
	]);

	/** @param {string} id */
	function setTab(id) {
		if (id === tab) return;
		const url = new URL($page.url);
		if (id === DEFAULT_TAB) url.searchParams.delete('tab');
		else url.searchParams.set('tab', id);
		goto(url, { keepFocus: true, noScroll: true });
	}

	// ---------- unfurl metadata (WhatsApp/Discord/Twitter paste this page a lot) ----------
	const title = $derived(group ? t('title.public', { name: group.name }) : t('title.home'));
	const metaDescription = $derived.by(() => {
		if (!group) return '';
		const counts = t('public.metaCounts', {
			nights: t('group.nightCount', { count: group.stats.total_nights }),
			players: t('group.playerCount', { count: group.stats.ranking.length })
		});
		return [group.description, counts, t('public.metaTagline')].filter(Boolean).join(' · ');
	});
	/** Canonical, token-free: the share token must not end up in an unfurl card. */
	const shareUrl = $derived($page.url.origin + $page.url.pathname);
</script>

<svelte:head>
	<title>{title}</title>
	{#if group}
		<meta name="description" content={metaDescription} />
		<meta property="og:type" content="website" />
		<meta property="og:site_name" content="Pokerdex" />
		<meta property="og:title" content={title} />
		<meta property="og:description" content={metaDescription} />
		<meta property="og:url" content={shareUrl} />
	{/if}
	{#if token}
		<!-- Reached through a private group's share link: readable by whoever has the link,
		     but it has no business in a search index. -->
		<meta name="robots" content="noindex" />
	{/if}
</svelte:head>

{#if error}
	<div class="card bg-base-100 px-5 py-12 text-center text-base-content/65">{error}</div>
{:else if group}
	<div class="head">
		<span class="badge badge-soft badge-primary">{t('public.badge')}</span>
		<h1 class="text-[2rem] font-semibold tracking-tight">{group.name}</h1>
		{#if group.description}<p class="text-base-content/80">{group.description}</p>{/if}
	</div>

	<TabBar
		{tabs}
		active={tab}
		onChange={setTab}
		label={t('tab.sections')}
		controls="public-panel"
		idPrefix="ptab"
		center
	/>

	<div id="public-panel" role="tabpanel" aria-labelledby={`ptab-${tab}`}>
		{#if tab === 'ranking'}
			<div class="card bg-base-100 p-5"><RankingTable ranking={group.stats.ranking} /></div>
		{:else if tab === 'stats'}
			<div class="flex flex-col gap-4">
				<Records records={group.stats.records} totalNights={group.stats.total_nights} />
				<div class="card flex flex-col gap-4 bg-base-100 p-5">
					<h3 class="font-semibold">{t('stats.evolution')}</h3>
					<EvolutionChart evolution={group.evolution} />
				</div>
			</div>
		{:else if tab === 'nights'}
			<NightsList nights={group.nights} />
		{/if}
	</div>

	<p class="mt-10 text-center text-sm text-base-content/65">
		{t('public.cta')}
		<a href="/" class="link link-primary font-medium">{t('public.ctaLink')}</a>
	</p>
{/if}

<style>
	.head {
		display: flex;
		flex-direction: column;
		gap: 8px;
		align-items: center;
		text-align: center;
		margin-bottom: 24px;
	}
</style>
