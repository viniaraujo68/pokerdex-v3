<script>
	import { auth } from '$lib/stores/auth.svelte.js';
	import { get, post } from '$lib/api.js';
	import { goto } from '$app/navigation';
	import Modal from '$lib/components/Modal.svelte';

	let groups = $state([]);
	let loading = $state(true);
	let error = $state('');
	let query = $state('');

	const filteredGroups = $derived(
		query.trim()
			? groups.filter((g) => g.name.toLowerCase().includes(query.trim().toLowerCase()))
			: groups
	);

	// create-group form
	let showForm = $state(false);
	let name = $state('');
	let description = $state('');
	let visibility = $state('public');
	let creating = $state(false);

	$effect(() => {
		if (auth.ready) {
			if (auth.user) loadGroups();
			else loading = false;
		}
	});

	async function loadGroups() {
		loading = true;
		try {
			groups = await get('/groups');
		} catch (e) {
			error = e.message;
		} finally {
			loading = false;
		}
	}

	async function createGroup(ev) {
		ev.preventDefault();
		creating = true;
		error = '';
		try {
			const g = await post('/groups', { name, description, visibility });
			goto(`/groups/${g.id}`);
		} catch (e) {
			error = e.message;
			creating = false;
		}
	}
</script>

{#if !auth.ready || loading}
	<div class="center"><div class="spinner"></div></div>
{:else if !auth.user}
	<!-- Landing -->
	<section class="hero">
		<span class="logo-big">♠</span>
		<h1>Pokerdex</h1>
		<p class="muted lead">As noites de poker do seu grupo, organizadas.</p>
		<div class="row hero-cta">
			<a href="/register" class="btn btn-primary">Criar conta</a>
			<a href="/login" class="btn btn-ghost">Entrar</a>
		</div>
	</section>
{:else}
	<!-- Dashboard -->
	<div class="spread head">
		<div>
			<h1>Meus grupos</h1>
			<p class="muted">Olá, {auth.user.username} 👋</p>
		</div>
		<button class="btn btn-primary" onclick={() => (showForm = !showForm)}>+ Novo grupo</button>
	</div>

	{#if error}<div class="toast toast-error">{error}</div>{/if}

	{#if showForm}
		<Modal title="Criar grupo" onclose={() => (showForm = false)}>
			<form class="stack" onsubmit={createGroup}>
				<div class="field">
					<label for="g-name">Nome do grupo</label>
					<!-- svelte-ignore a11y_autofocus -->
				<input id="g-name" bind:value={name} placeholder="Sextodex" autofocus required />
				</div>
				<div class="field">
					<label for="g-desc">Descrição <span class="faint">(opcional)</span></label>
					<input id="g-desc" bind:value={description} />
				</div>
				<div class="field">
					<span class="lbl">Visibilidade</span>
					<div class="vis">
						<button
							type="button"
							class="vis-opt"
							class:sel={visibility === 'public'}
							onclick={() => (visibility = 'public')}
						>
							<span class="vis-ic">🌐</span>
							<span class="vis-t">Público</span>
							<span class="vis-d faint">Qualquer um com o link vê e aparece no Explorar</span>
						</button>
						<button
							type="button"
							class="vis-opt"
							class:sel={visibility === 'private'}
							onclick={() => (visibility = 'private')}
						>
							<span class="vis-ic">🔒</span>
							<span class="vis-t">Privado</span>
							<span class="vis-d faint">Só os donos têm acesso</span>
						</button>
					</div>
				</div>
				<div class="row mactions">
					<button type="button" class="btn btn-ghost" onclick={() => (showForm = false)}>Cancelar</button>
					<button class="btn btn-primary" disabled={creating || !name}>
						{creating ? 'Criando…' : 'Criar grupo'}
					</button>
				</div>
			</form>
		</Modal>
	{/if}

	{#if groups.length === 0}
		<div class="card empty">Você ainda não tem grupos. Crie o primeiro! ♠</div>
	{:else}
		{#if groups.length > 3}
			<input class="search" placeholder="🔎 Buscar nos meus grupos…" bind:value={query} />
		{/if}
		{#if filteredGroups.length === 0}
			<div class="card empty">Nenhum grupo encontrado para “{query}”.</div>
		{:else}
			<div class="groups grid">
				{#each filteredGroups as g}
					<a href={`/groups/${g.id}`} class="card group">
						<div class="spread">
							<h3>{g.name}</h3>
							<span class="chip {g.visibility === 'public' ? 'chip-felt' : ''}">
								{g.visibility === 'public' ? 'público' : 'privado'}
							</span>
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
	{/if}
{/if}

<style>
	.center {
		display: grid;
		place-items: center;
		min-height: 40vh;
	}
	.hero {
		text-align: center;
		max-width: 560px;
		margin: 12vh auto 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 14px;
	}
	.logo-big {
		display: grid;
		place-items: center;
		width: 72px;
		height: 72px;
		border-radius: 18px;
		background: linear-gradient(180deg, var(--felt-bright), var(--felt-deep));
		color: #fff;
		font-size: 2.4rem;
		box-shadow: var(--shadow-lg);
	}
	.hero h1 {
		font-size: clamp(2.2rem, 6vw, 3rem);
	}
	.lead {
		font-size: 1.1rem;
	}
	.hero-cta {
		margin-top: 10px;
	}
	.head {
		margin-bottom: 24px;
	}
	@media (max-width: 560px) {
		.head {
			flex-direction: column;
			align-items: stretch;
			gap: 12px;
		}
		.head :global(.btn) {
			width: 100%;
		}
		.search {
			max-width: none;
		}
	}
	.lbl {
		font-size: 0.82rem;
		font-weight: 600;
		color: var(--text-muted);
	}
	.vis {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 10px;
	}
	.vis-opt {
		display: flex;
		flex-direction: column;
		gap: 3px;
		text-align: left;
		padding: 12px 14px;
		border-radius: 10px;
		border: 1px solid var(--border);
		background: var(--bg-elev);
		color: var(--text);
		cursor: pointer;
		transition:
			border-color 0.12s ease,
			background 0.12s ease;
	}
	.vis-opt:hover {
		border-color: var(--felt);
	}
	.vis-opt.sel {
		border-color: var(--felt-bright);
		background: rgba(124, 58, 237, 0.14);
	}
	.vis-ic {
		font-size: 1.2rem;
	}
	.vis-t {
		font-weight: 700;
		font-family: var(--font-display);
	}
	.vis-d {
		font-size: 0.74rem;
		line-height: 1.3;
	}
	.mactions {
		justify-content: flex-end;
		margin-top: 4px;
	}
	.search {
		max-width: 360px;
		margin-bottom: 18px;
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
