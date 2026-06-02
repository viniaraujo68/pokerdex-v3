<script>
	import { get } from '$lib/api.js';

	let query = $state('');
	let results = $state([]);
	let loading = $state(true);
	let error = $state('');
	let timer;

	$effect(() => {
		// debounce search on query change
		const q = query;
		clearTimeout(timer);
		timer = setTimeout(() => search(q), 250);
		return () => clearTimeout(timer);
	});

	async function search(q) {
		loading = true;
		error = '';
		try {
			results = await get(`/public?q=${encodeURIComponent(q.trim())}`);
		} catch (e) {
			error = e.message;
		} finally {
			loading = false;
		}
	}
</script>

<div class="head">
	<h1>Explorar grupos</h1>
	<p class="muted">Descubra placares públicos de outros grupos.</p>
</div>

<input class="search" placeholder="🔎 Buscar grupos públicos pelo nome…" bind:value={query} />

{#if loading}
	<div class="center"><div class="spinner"></div></div>
{:else if error}
	<div class="toast toast-error">{error}</div>
{:else if results.length === 0}
	<div class="card empty">
		{query.trim() ? `Nenhum grupo público para “${query}”.` : 'Nenhum grupo público ainda.'}
	</div>
{:else}
	<div class="groups grid">
		{#each results as g}
			<a href={`/g/${g.slug}`} class="card group">
				<div class="spread">
					<h3>{g.name}</h3>
					<span class="chip chip-felt">público</span>
				</div>
				{#if g.description}<p class="muted desc">{g.description}</p>{/if}
				<div class="row stats">
					<span class="chip">🃏 {g.night_count} noites</span>
					<span class="chip">👥 {g.participant_count} participantes</span>
				</div>
			</a>
		{/each}
	</div>
{/if}

<style>
	.head {
		margin-bottom: 20px;
	}
	.search {
		max-width: 420px;
		margin-bottom: 24px;
	}
	.center {
		display: grid;
		place-items: center;
		min-height: 30vh;
	}
	.groups {
		grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
	}
	.group {
		display: flex;
		flex-direction: column;
		gap: 12px;
		transition:
			transform 0.12s ease,
			border-color 0.15s ease;
	}
	.group:hover {
		transform: translateY(-3px);
		border-color: var(--felt);
	}
	.desc {
		font-size: 0.9rem;
		margin: 0;
	}
	.stats {
		flex-wrap: wrap;
		margin-top: auto;
	}
</style>
