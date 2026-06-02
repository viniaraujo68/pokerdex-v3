<script>
	import '../app.css';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { auth, loadUser, logout } from '$lib/stores/auth.svelte.js';

	let { children } = $props();

	onMount(loadUser);

	async function handleLogout() {
		await logout();
		goto('/');
	}

	const isPublic = $derived($page.url.pathname.startsWith('/g/'));
</script>

<header class="nav">
	<div class="container nav-inner">
		<a href="/" class="brand">
			<span class="logo">♠</span>
			<span class="brand-name">Pokerdex</span>
		</a>

		{#if !isPublic}
			<nav class="nav-actions">
				<a href="/explorar" class="explore-link">Explorar</a>
				{#if auth.ready && auth.user}
					<span class="muted user">👤 {auth.user.username}</span>
					<button class="btn btn-ghost btn-sm" onclick={handleLogout}>Sair</button>
				{:else if auth.ready}
					<a href="/login" class="btn btn-ghost btn-sm">Entrar</a>
					<a href="/register" class="btn btn-primary btn-sm">Criar conta</a>
				{/if}
			</nav>
		{/if}
	</div>
</header>

<main class="container page">
	{@render children()}
</main>

<footer class="foot">
	<div class="container faint">Pokerdex · noites de poker do seu grupo ♠ ♥ ♣ ♦</div>
</footer>

<style>
	.nav {
		position: sticky;
		top: 0;
		z-index: 50;
		background: rgba(11, 15, 13, 0.8);
		backdrop-filter: blur(12px);
		border-bottom: 1px solid var(--border);
	}
	.nav-inner {
		display: flex;
		align-items: center;
		justify-content: space-between;
		height: 64px;
	}
	.brand {
		display: flex;
		align-items: center;
		gap: 10px;
	}
	.logo {
		display: grid;
		place-items: center;
		width: 34px;
		height: 34px;
		border-radius: 9px;
		background: linear-gradient(180deg, var(--felt-bright), var(--felt-deep));
		color: #ffffff;
		font-size: 1.2rem;
		font-weight: 800;
	}
	.brand-name {
		font-family: var(--font-display);
		font-weight: 800;
		font-size: 1.2rem;
		letter-spacing: -0.02em;
	}
	.nav-actions {
		display: flex;
		align-items: center;
		gap: 10px;
	}
	.user {
		font-size: 0.9rem;
	}
	.explore-link {
		font-size: 0.9rem;
		font-weight: 600;
		color: var(--text-muted);
		padding: 6px 4px;
	}
	.explore-link:hover {
		color: var(--felt-bright);
	}
	.page {
		padding-top: 32px;
		padding-bottom: 64px;
		min-height: calc(100vh - 64px - 60px);
	}
	.foot {
		border-top: 1px solid var(--border-soft);
		padding: 20px 0;
		font-size: 0.82rem;
		text-align: center;
	}
	@media (max-width: 560px) {
		.user {
			display: none;
		}
	}
</style>
