<script>
	import { page } from '$app/stores';
	import { get } from '$lib/api.js';
	import RankingTable from '$lib/components/RankingTable.svelte';
	import Records from '$lib/components/Records.svelte';
	import EvolutionChart from '$lib/components/EvolutionChart.svelte';
	import NightsList from '$lib/components/NightsList.svelte';

	const slug = $derived($page.params.slug);
	const token = $derived($page.url.searchParams.get('t'));

	let data = $state(null);
	let loading = $state(true);
	let error = $state('');
	let tab = $state('ranking');

	$effect(() => {
		if (slug) load();
	});

	async function load() {
		loading = true;
		error = '';
		try {
			const q = token ? `?t=${encodeURIComponent(token)}` : '';
			data = await get(`/public/${slug}${q}`);
		} catch (e) {
			error =
				e.status === 403
					? 'Este grupo é privado. Você precisa de um link com token válido.'
					: e.status === 404
						? 'Grupo não encontrado.'
						: e.message;
		} finally {
			loading = false;
		}
	}
</script>

{#if loading}
	<div class="center"><div class="spinner"></div></div>
{:else if error}
	<div class="card empty">{error}</div>
{:else if data}
	<div class="head">
		<span class="chip chip-felt">placar público ♠</span>
		<h1>{data.name}</h1>
		{#if data.description}<p class="muted">{data.description}</p>{/if}
	</div>

	<div class="tabs">
		<button class="tab" class:active={tab === 'ranking'} onclick={() => (tab = 'ranking')}>Ranking</button>
		<button class="tab" class:active={tab === 'stats'} onclick={() => (tab = 'stats')}>Estatísticas</button>
		<button class="tab" class:active={tab === 'nights'} onclick={() => (tab = 'nights')}>Noites</button>
	</div>

	{#if tab === 'ranking'}
		<div class="card"><RankingTable ranking={data.stats.ranking} /></div>
	{:else if tab === 'stats'}
		<div class="stack">
			<Records records={data.stats.records} totalNights={data.stats.total_nights} />
			<div class="card stack">
				<h3>Evolução do lucro</h3>
				<EvolutionChart evolution={data.evolution} />
			</div>
		</div>
	{:else if tab === 'nights'}
		<NightsList nights={data.nights} />
	{/if}

	<p class="foot-cta faint">
		Quer registrar as noites do seu grupo? <a href="/" class="link">Conheça o Pokerdex</a>
	</p>
{/if}

<style>
	.center {
		display: grid;
		place-items: center;
		min-height: 40vh;
	}
	.head {
		display: flex;
		flex-direction: column;
		gap: 8px;
		align-items: center;
		text-align: center;
		margin-bottom: 24px;
	}
	.head h1 {
		font-size: 2.2rem;
	}
	.tabs {
		display: flex;
		gap: 4px;
		justify-content: center;
		border-bottom: 1px solid var(--border);
		margin-bottom: 24px;
	}
	.tab {
		background: none;
		border: none;
		border-bottom: 2px solid transparent;
		color: var(--text-muted);
		padding: 10px 16px;
		font-weight: 600;
		cursor: pointer;
	}
	.tab.active {
		color: var(--felt-bright);
		border-bottom-color: var(--felt-bright);
	}
	.foot-cta {
		text-align: center;
		margin-top: 40px;
		font-size: 0.9rem;
	}
	.link {
		color: var(--felt-bright);
		font-weight: 600;
	}
</style>
