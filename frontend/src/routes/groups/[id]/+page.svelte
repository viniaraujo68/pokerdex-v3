<script>
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { get, del, put, errorMessage, errorStatus } from '$lib/http.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import RankingTable from '$lib/components/RankingTable.svelte';
	import Records from '$lib/components/Records.svelte';
	import EvolutionChart from '$lib/components/EvolutionChart.svelte';
	import NightsList from '$lib/components/NightsList.svelte';
	import GroupSettings from '$lib/components/GroupSettings.svelte';
	import TabBar from '$lib/components/TabBar.svelte';
	import { t } from '$lib/i18n.svelte.js';
	import { toast } from '@viniaraujo68/plinth/toast';
	import { loginUrl } from '$lib/nav.js';
	import { unbalancedBadgeEnabled } from '$lib/prefs.svelte.js';

	// The route can't match without an `id`, but `$page.params` is a loose string map — the
	// cast says what `[id]` guarantees instead of defaulting to '' and building `/groups//…` URLs.
	const groupId = $derived(/** @type {string} */ ($page.params.id));

	let group = $state(/** @type {import('$lib/types.js').Group|null} */ (null));
	let nights = $state(/** @type {import('$lib/types.js').Night[]} */ ([]));
	let stats = $state(/** @type {import('$lib/types.js').Stats|null} */ (null));
	let evolution = $state(/** @type {import('$lib/types.js').Evolution|null} */ (null));
	let loading = $state(true);
	let error = $state('');

	// ---------- tabs live in the URL ----------
	// Derived from the URL (not local state) so Back/Forward and a shared link both land on
	// the right tab; `setTab` pushes a history entry so Back means "previous tab".
	const TAB_IDS = ['nights', 'ranking', 'stats', 'settings'];
	const DEFAULT_TAB = 'nights';
	const tab = $derived.by(() => {
		const requested = $page.url.searchParams.get('tab');
		return requested && TAB_IDS.includes(requested) ? requested : DEFAULT_TAB;
	});

	const tabs = $derived([
		{ id: 'nights', label: t('tab.nights') },
		{ id: 'ranking', label: t('tab.ranking') },
		{ id: 'stats', label: t('tab.stats') },
		{ id: 'settings', label: t('tab.settings') }
	]);

	/** @param {string} id */
	function setTab(id) {
		if (id === tab) return;
		const url = new URL($page.url);
		if (id === DEFAULT_TAB) url.searchParams.delete('tab');
		else url.searchParams.set('tab', id);
		goto(url, { keepFocus: true, noScroll: true });
	}

	// ---------- unbalanced-nights warning (opt-out, per group, per device) ----------
	const showUnbalancedBadge = $derived(group ? unbalancedBadgeEnabled(group.id) : false);

	/**
	 * Legacy imports carry cash-outs but no buy-ins, so their pots can never close — counting
	 * them would bury the handful of nights that actually have a typo.
	 * @param {import('$lib/types.js').Night} n
	 */
	function isLegacyNight(n) {
		return n.entries.length > 0 && n.entries.every((e) => e.buy_in_cents === 0);
	}
	const unbalancedCount = $derived(
		nights.filter((n) => n.balance_cents !== 0 && !isLegacyNight(n)).length
	);

	$effect(() => {
		if (auth.ready && !auth.user) goto(loginUrl($page.url));
	});

	$effect(() => {
		if (groupId && auth.user) loadAll();
	});

	async function loadAll() {
		loading = true;
		error = '';
		try {
			[group, nights, stats, evolution] = await Promise.all([
				get(`/groups/${groupId}`),
				get(`/groups/${groupId}/nights`),
				get(`/groups/${groupId}/stats`),
				get(`/groups/${groupId}/evolution`)
			]);
		} catch (e) {
			error = errorStatus(e) === 403 ? t('group.accessDenied') : errorMessage(e);
		} finally {
			loading = false;
		}
	}

	async function refreshData() {
		try {
			[nights, stats, evolution] = await Promise.all([
				get(`/groups/${groupId}/nights`),
				get(`/groups/${groupId}/stats`),
				get(`/groups/${groupId}/evolution`)
			]);
		} catch (e) {
			toast.error(t('group.refreshFailed', { message: errorMessage(e) }));
		}
	}

	/** @param {import('$lib/types.js').Group} [updated] */
	function onGroupChange(updated) {
		// `group` is necessarily loaded here (the settings tab only renders once it is), but the
		// merge still needs a base object to spread over.
		if (updated) group = group ? { ...group, ...updated } : updated;
		else refreshData();
	}

	/**
	 * Inline fix of a single entry from the night card. The API only takes whole nights, so
	 * we rebuild every entry from what the card already has and swap in the edited one.
	 * @param {import('$lib/types.js').Night} night
	 * @param {import('$lib/types.js').Entry} entry
	 * @param {{ buy_in_cents: number, cash_out_cents: number }} amounts
	 */
	async function quickEditEntry(night, entry, amounts) {
		const payload = {
			date: night.date,
			place_id: night.place_id ?? null,
			entries: night.entries.map((e) => ({
				participant_id: e.participant_id,
				buy_in_cents: e.id === entry.id ? amounts.buy_in_cents : e.buy_in_cents,
				cash_out_cents: e.id === entry.id ? amounts.cash_out_cents : e.cash_out_cents
			}))
		};
		await put(`/groups/${groupId}/nights/${night.id}`, payload); // let the card show the error
		await refreshData();
	}

	/** @param {import('$lib/types.js').Night} night */
	async function deleteNight(night) {
		// Still a native confirm: the destructive-action dialog is the next wave's job.
		if (!confirm(t('night.deleteConfirm'))) return;
		try {
			await del(`/groups/${groupId}/nights/${night.id}`);
		} catch (e) {
			toast.error(t('night.deleteFailed', { message: errorMessage(e) }));
			return;
		}
		toast.success(t('toast.nightDeleted'));
		await refreshData();
	}
</script>

<svelte:head>
	<title>{group ? t('title.group', { name: group.name }) : t('title.home')}</title>
</svelte:head>

{#if loading}
	<!-- Skeleton, not a spinner: it reserves the real geometry, so nothing jumps on arrival. -->
	<div class="skel" role="status">
		<span class="sr-only">{t('common.loading')}</span>
		<div class="sk sk-h1"></div>
		<div class="sk sk-line sk-desc"></div>
		<div class="sk-tabs">
			{#each TAB_IDS as id (id)}<div class="sk sk-tab"></div>{/each}
		</div>
		{#each [0, 1, 2] as i (i)}
			<div class="pd-card pd-card-tight sk-card">
				<div class="sk sk-line sk-date"></div>
				<div class="sk-chips">
					<div class="sk sk-chip"></div>
					<div class="sk sk-chip"></div>
					<div class="sk sk-chip"></div>
				</div>
			</div>
		{/each}
	</div>
{:else if error}
	<div class="pd-alert pd-alert-error">{error}</div>
	<a href="/" class="pd-btn pd-btn-ghost" style="margin-top:16px">{t('group.back')}</a>
{:else if group && stats && evolution}
	<div class="spread head">
		<div>
			<a href="/" class="muted back">{t('group.back')}</a>
			<h1>{group.name}</h1>
			{#if group.description}<p class="muted">{group.description}</p>{/if}
		</div>
		<a href={`/groups/${groupId}/nights/new`} class="pd-btn pd-btn-primary">{t('group.newNight')}</a>
	</div>

	<TabBar {tabs} active={tab} onChange={setTab} label={t('tab.sections')} controls="group-panel" />

	{#if showUnbalancedBadge && unbalancedCount > 0}
		{#if tab === 'nights'}
			<!-- already where the button would take you: a plain chip, not a dead control -->
			<span class="chip chip-gold warn">{t('group.unbalanced', { count: unbalancedCount })}</span>
		{:else}
			<button
				class="chip chip-gold warn tappable"
				title={t('group.unbalancedGoTo')}
				onclick={() => setTab('nights')}
			>
				{t('group.unbalanced', { count: unbalancedCount })}
			</button>
		{/if}
	{/if}

	<div id="group-panel" role="tabpanel" aria-labelledby={`tab-${tab}`}>
		{#if tab === 'nights'}
			<NightsList
				{nights}
				editable
				newNightHref={`/groups/${groupId}/nights/new`}
				onEdit={(n) => goto(`/groups/${groupId}/nights/new?edit=${n.id}`)}
				onDelete={deleteNight}
				onQuickEdit={quickEditEntry}
			/>
		{:else if tab === 'ranking'}
			<div class="pd-card"><RankingTable ranking={stats.ranking} /></div>
		{:else if tab === 'stats'}
			<div class="pd-stack">
				<Records records={stats.records} totalNights={stats.total_nights} />
				<div class="pd-card pd-stack">
					<h3>{t('stats.evolution')}</h3>
					<EvolutionChart {evolution} />
				</div>
			</div>
		{:else if tab === 'settings'}
			<GroupSettings {group} onchange={onGroupChange} />
		{/if}
	</div>
{/if}

<style>
	/* ---------- loading skeleton (mirrors head + tabs + night cards) ---------- */
	.skel {
		display: flex;
		flex-direction: column;
		gap: 16px;
	}
	.sk-h1 {
		height: 30px;
		width: min(280px, 70%);
	}
	.sk-desc {
		width: min(200px, 50%);
		margin-bottom: 8px;
	}
	.sk-tabs {
		display: flex;
		gap: 4px;
		border-bottom: 1px solid var(--border-color);
		padding-bottom: 10px;
		margin-bottom: 8px;
	}
	.sk-tab {
		height: 18px;
		width: 72px;
	}
	.sk-card {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	.sk-date {
		height: 16px;
		width: 40%;
	}
	.sk-chips {
		display: flex;
		gap: 6px;
	}
	.sk-chip {
		height: 22px;
		width: 68px;
		border-radius: 999px;
	}
	.head {
		align-items: flex-start;
		margin-bottom: 20px;
	}
	.back {
		font-size: 0.9rem;
		display: inline-block;
		margin-bottom: 8px;
	}
	@media (max-width: 560px) {
		.head {
			flex-direction: column;
			align-items: stretch;
			gap: 12px;
		}
		.head :global(.pd-btn) {
			width: 100%;
		}
	}
	/* The 24px the TabBar leaves under itself is what the pull-up below borrows against. */
	.warn {
		display: inline-flex;
		align-items: flex-start;
		/* pulled up under the tab rule so it reads as part of that band */
		margin: -14px 0 20px;
		padding: 6px 12px;
		font-size: 0.8rem;
		text-align: left;
		line-height: 1.35;
		max-width: 100%;
	}
	@media (max-width: 560px) {
		/* Two lines of warning text at 320–390px: give the pull-up less rope so the wrap can't
		   ride into the tab rule. */
		.warn {
			margin-top: -6px;
		}
	}
	.tappable {
		cursor: pointer;
	}
	.tappable:hover {
		border-color: var(--gold);
		color: var(--gold);
	}
</style>
