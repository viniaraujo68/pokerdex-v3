<script>
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { get, del } from '$lib/api.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import RankingTable from '$lib/components/RankingTable.svelte';
	import Records from '$lib/components/Records.svelte';
	import EvolutionChart from '$lib/components/EvolutionChart.svelte';
	import NightsList from '$lib/components/NightsList.svelte';
	import GroupSettings from '$lib/components/GroupSettings.svelte';

	const groupId = $derived($page.params.id);

	let group = $state(null);
	let nights = $state([]);
	let stats = $state(null);
	let evolution = $state(null);
	let loading = $state(true);
	let error = $state('');
	let tab = $state('nights');

	const tabs = [
		{ id: 'nights', label: 'Noites' },
		{ id: 'ranking', label: 'Ranking' },
		{ id: 'stats', label: 'Estatísticas' },
		{ id: 'settings', label: 'Config' }
	];

	$effect(() => {
		if (auth.ready && !auth.user) goto('/login');
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
			error = e.status === 403 ? 'Você não tem acesso a este grupo.' : e.message;
		} finally {
			loading = false;
		}
	}

	async function refreshData() {
		[nights, stats, evolution] = await Promise.all([
			get(`/groups/${groupId}/nights`),
			get(`/groups/${groupId}/stats`),
			get(`/groups/${groupId}/evolution`)
		]);
	}

	function onGroupChange(updated) {
		if (updated) group = { ...group, ...updated };
		else refreshData();
	}

	async function deleteNight(night) {
		if (!confirm('Excluir esta noite? As estatísticas serão recalculadas.')) return;
		await del(`/groups/${groupId}/nights/${night.id}`);
		await refreshData();
	}
</script>

{#if loading}
	<div class="center"><div class="spinner"></div></div>
{:else if error}
	<div class="toast toast-error">{error}</div>
	<a href="/" class="btn btn-ghost" style="margin-top:16px">← Meus grupos</a>
{:else if group}
	<div class="spread head">
		<div>
			<a href="/" class="muted back">← Meus grupos</a>
			<h1>{group.name}</h1>
			{#if group.description}<p class="muted">{group.description}</p>{/if}
		</div>
		<a href={`/groups/${groupId}/nights/new`} class="btn btn-primary">+ Nova noite</a>
	</div>

	<div class="tabs">
		{#each tabs as t}
			<button class="tab" class:active={tab === t.id} onclick={() => (tab = t.id)}>{t.label}</button>
		{/each}
	</div>

	{#if tab === 'nights'}
		<NightsList
			{nights}
			editable
			onEdit={(n) => goto(`/groups/${groupId}/nights/new?edit=${n.id}`)}
			onDelete={deleteNight}
		/>
	{:else if tab === 'ranking'}
		<div class="card"><RankingTable ranking={stats.ranking} /></div>
	{:else if tab === 'stats'}
		<div class="stack">
			<Records records={stats.records} totalNights={stats.total_nights} />
			<div class="card stack">
				<h3>Evolução do lucro</h3>
				<EvolutionChart {evolution} />
			</div>
		</div>
	{:else if tab === 'settings'}
		<GroupSettings {group} onchange={onGroupChange} />
	{/if}
{/if}

<style>
	.center {
		display: grid;
		place-items: center;
		min-height: 40vh;
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
	.tabs {
		display: flex;
		gap: 4px;
		border-bottom: 1px solid var(--border);
		margin-bottom: 24px;
		overflow-x: auto;
	}
	.tab {
		background: none;
		border: none;
		border-bottom: 2px solid transparent;
		color: var(--text-muted);
		padding: 10px 16px;
		font-size: 0.95rem;
		font-weight: 600;
		cursor: pointer;
		white-space: nowrap;
	}
	.tab.active {
		color: var(--felt-bright);
		border-bottom-color: var(--felt-bright);
	}
	.tab:hover {
		color: var(--text);
	}
</style>
