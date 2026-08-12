<script>
	import { tick } from 'svelte';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { get, post, errorMessage } from '$lib/api.js';
	import { goto } from '$app/navigation';
	import Modal from '$lib/components/Modal.svelte';
	import GroupCard from '$lib/components/GroupCard.svelte';
	import { t } from '$lib/i18n.svelte.js';

	/** Dashboard once we know who's logged in; the landing (and the skeleton) stay "Pokerdex". */
	const title = $derived(auth.ready && auth.user ? t('title.myGroups') : t('title.home'));

	let groups = $state(/** @type {import('$lib/types.js').Group[]} */ ([]));
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
	let createError = $state('');

	// The visibility picker is a radiogroup: arrows move the selection, and only the checked
	// option sits in the Tab order (roving tabindex).
	const VISIBILITIES = ['public', 'private'];
	/** @param {KeyboardEvent} e */
	function onVisKey(e) {
		if (!['ArrowRight', 'ArrowDown', 'ArrowLeft', 'ArrowUp'].includes(e.key)) return;
		e.preventDefault();
		// With exactly two options, "next" and "previous" are the same hop.
		visibility = VISIBILITIES[(VISIBILITIES.indexOf(visibility) + 1) % VISIBILITIES.length];
		tick().then(() => document.getElementById(`vis-${visibility}`)?.focus());
	}

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
			error = errorMessage(e);
		} finally {
			loading = false;
		}
	}

	/** @param {SubmitEvent} ev */
	async function createGroup(ev) {
		ev.preventDefault();
		creating = true;
		createError = '';
		try {
			const g = await post('/groups', { name, description, visibility });
			goto(`/groups/${g.id}`);
		} catch (e) {
			// mostrado dentro do modal — fora dele ficaria escondido atrás do overlay
			createError = errorMessage(e);
			creating = false;
		}
	}
</script>

<svelte:head>
	<title>{title}</title>
	<meta name="description" content={t('home.tagline')} />
</svelte:head>

{#if !auth.ready || loading}
	<!-- Skeleton of the dashboard we're most likely about to render: a heading and a card grid. -->
	<div class="skel" role="status">
		<span class="sr-only">{t('common.loading')}</span>
		<div class="sk sk-h1"></div>
		<div class="sk sk-line sk-sub"></div>
		<div class="groups grid">
			{#each [0, 1, 2] as i (i)}
				<div class="card sk-card">
					<div class="sk sk-line sk-cardtitle"></div>
					<div class="sk sk-line sk-cardline"></div>
					<div class="sk-chips">
						<div class="sk sk-chip"></div>
						<div class="sk sk-chip"></div>
					</div>
				</div>
			{/each}
		</div>
	</div>
{:else if !auth.user}
	<!-- Landing -->
	<section class="hero">
		<span class="logo-big">♠</span>
		<h1>Pokerdex</h1>
		<p class="muted lead">{t('home.tagline')}</p>
		<div class="row hero-cta">
			<a href="/register" class="btn btn-primary">{t('nav.register')}</a>
			<a href="/login" class="btn btn-ghost">{t('nav.login')}</a>
		</div>
	</section>
{:else}
	<!-- Dashboard -->
	<div class="spread head">
		<div>
			<h1>{t('home.myGroups')}</h1>
			<p class="muted">{t('home.greeting', { name: auth.user.username })}</p>
		</div>
		<button class="btn btn-primary" onclick={() => (showForm = !showForm)}>{t('home.newGroup')}</button>
	</div>

	{#if error}<div class="toast toast-error">{error}</div>{/if}

	{#if showForm}
		<Modal title={t('group.create')} onclose={() => (showForm = false)}>
			<form class="stack" onsubmit={createGroup}>
				{#if createError}<div class="toast toast-error">{createError}</div>{/if}
				<div class="field">
					<label for="g-name">{t('group.nameLabel')}</label>
					<!-- svelte-ignore a11y_autofocus -->
				<input id="g-name" bind:value={name} autofocus required />
				</div>
				<div class="field">
					<label for="g-desc">{t('common.description')} <span class="faint">{t('common.optional')}</span></label>
					<input id="g-desc" bind:value={description} />
				</div>
				<div class="field">
					<span class="lbl" id="vis-label">{t('group.visibility')}</span>
					<div class="vis" role="radiogroup" aria-labelledby="vis-label">
						<button
							type="button"
							id="vis-public"
							class="vis-opt"
							class:sel={visibility === 'public'}
							role="radio"
							aria-checked={visibility === 'public'}
							tabindex={visibility === 'public' ? 0 : -1}
							onkeydown={onVisKey}
							onclick={() => (visibility = 'public')}
						>
							<span class="vis-ic" aria-hidden="true">🌐</span>
							<span class="vis-t">{t('group.public')}</span>
							<span class="vis-d faint">{t('group.publicHint')}</span>
						</button>
						<button
							type="button"
							id="vis-private"
							class="vis-opt"
							class:sel={visibility === 'private'}
							role="radio"
							aria-checked={visibility === 'private'}
							tabindex={visibility === 'private' ? 0 : -1}
							onkeydown={onVisKey}
							onclick={() => (visibility = 'private')}
						>
							<span class="vis-ic" aria-hidden="true">🔒</span>
							<span class="vis-t">{t('group.private')}</span>
							<span class="vis-d faint">{t('group.privateHint')}</span>
						</button>
					</div>
				</div>
				<div class="row mactions">
					<button type="button" class="btn btn-ghost" onclick={() => (showForm = false)}>{t('common.cancel')}</button>
					<button class="btn btn-primary" disabled={creating || !name}>
						{creating ? t('group.creating') : t('group.create')}
					</button>
				</div>
			</form>
		</Modal>
	{/if}

	{#if groups.length === 0}
		<div class="card empty stack empty-cta">
			<p>{t('home.empty')}</p>
			<button class="btn btn-primary" onclick={() => (showForm = true)}>{t('home.newGroup')}</button>
		</div>
	{:else}
		{#if groups.length > 3}
			<input class="search" placeholder={t('home.searchPlaceholder')} bind:value={query} />
		{/if}
		{#if filteredGroups.length === 0}
			<div class="card empty">{t('home.noResults', { query })}</div>
		{:else}
			<div class="groups grid">
				{#each filteredGroups as g (g.id)}
					<GroupCard group={g} href={`/groups/${g.id}`} visibility={g.visibility} />
				{/each}
			</div>
		{/if}
	{/if}
{/if}

<style>
	/* ---------- loading skeleton (mirrors the dashboard head + group grid) ---------- */
	.skel {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	.sk-h1 {
		height: 30px;
		width: min(240px, 60%);
	}
	.sk-sub {
		width: min(160px, 45%);
		margin-bottom: 14px;
	}
	.sk-card {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	.sk-cardtitle {
		height: 18px;
		width: 60%;
	}
	.sk-cardline {
		width: 85%;
	}
	.sk-chips {
		display: flex;
		gap: 8px;
		margin-top: auto;
	}
	.sk-chip {
		height: 22px;
		width: 84px;
		border-radius: 999px;
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
	.empty-cta {
		align-items: center;
	}
	.empty-cta p {
		margin: 0;
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
	@media (max-width: 560px) {
		/* two columns of hint text at 375px is four words per line — stack instead */
		.vis {
			grid-template-columns: 1fr;
		}
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
</style>
