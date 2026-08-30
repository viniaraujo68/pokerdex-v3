<script>
	import './layout.css';
	import './legacy-preflight.css';
	import '../app.css';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { navigating, page } from '$app/stores';
	import { auth, loadUser, logout } from '$lib/stores/auth.svelte.js';
	import { i18n, setLocale, t } from '$lib/i18n.svelte.js';
	import Toasts from '$lib/components/Toasts.svelte';

	let { children } = $props();

	onMount(loadUser);

	async function handleLogout() {
		await logout();
		goto('/');
	}

	const isPublic = $derived($page.url.pathname.startsWith('/g/'));

	/* ---------- navigation progress ----------
	   Most navigations here resolve from cache in a few frames, and a bar that flashes on
	   every click reads as jank. So the bar is armed on a GRACE_MS timer: only a navigation
	   still running after that shows anything, which in practice means the ones that are
	   actually waiting on the network. */
	const GRACE_MS = 150;
	let showProgress = $state(false);

	$effect(() => {
		if (!$navigating) {
			showProgress = false;
			return;
		}
		const timer = setTimeout(() => (showProgress = true), GRACE_MS);
		// Runs when $navigating changes or the layout unmounts — a fast navigation is
		// disarmed here before the bar ever paints.
		return () => clearTimeout(timer);
	});
</script>

<!-- Progress, not percentage: SvelteKit exposes no load fraction, so this is an indeterminate
     sweep. aria-hidden because `navigating` is not something to narrate on every click; the
     destination page's own heading is the real announcement. -->
{#if showProgress}
	<div class="navbar-progress" aria-hidden="true"><span></span></div>
{/if}

<header class="nav">
	<div class="container nav-inner">
		<a href="/" class="brand">
			<span class="logo">♠</span>
			<span class="brand-name">Pokerdex</span>
		</a>

		<div class="nav-right">
			{#if !isPublic}
				<nav class="nav-actions">
					<a href="/explore" class="explore-link">{t('nav.explore')}</a>
					{#if auth.ready && auth.user}
						<a href="/account" class="user" title={t('nav.account')}>👤 {auth.user.username}</a>
						<button class="btn btn-ghost btn-sm" onclick={handleLogout}>{t('nav.logout')}</button>
					{:else if auth.ready}
						<a href="/login" class="btn btn-ghost btn-sm">{t('nav.login')}</a>
						<a href="/register" class="btn btn-primary btn-sm">{t('nav.register')}</a>
					{/if}
				</nav>
			{:else if auth.ready && !auth.user}
				<!-- Public scoreboards stay chrome-free, but a visitor who likes what they see
				     needs one way in. Owners already have the full nav elsewhere. -->
				<nav class="nav-actions">
					<a href="/register" class="btn btn-primary btn-sm">{t('nav.register')}</a>
				</nav>
			{/if}

			<!-- Always visible, public scoreboards included. -->
			<div class="lang" role="group" aria-label={t('nav.language')}>
				<button
					class="lang-opt"
					class:sel={i18n.locale === 'pt'}
					aria-pressed={i18n.locale === 'pt'}
					title={t('nav.switchToPt')}
					onclick={() => setLocale('pt')}>PT</button
				>
				<button
					class="lang-opt"
					class:sel={i18n.locale === 'en'}
					aria-pressed={i18n.locale === 'en'}
					title={t('nav.switchToEn')}
					onclick={() => setLocale('en')}>EN</button
				>
			</div>
		</div>
	</div>
</header>

<main class="container page">
	{@render children()}
</main>

<footer class="foot">
	<div class="container faint">{t('footer.tagline')}</div>
</footer>

<!-- One overlay for the whole app: it outlives navigations, so a toast fired just before a
     goto() is still on screen when the next page renders. -->
<Toasts />

<style>
	/* Above .nav (z-index 50) — the header is sticky, so a bar underneath it would vanish
	   under the backdrop blur. */
	.navbar-progress {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		z-index: 60;
		height: 2px;
		overflow: hidden;
		/* No track colour: on a page that hasn't changed yet, a full-width grey line looks
		   like a border that just appeared. Only the moving span is visible. */
		background: transparent;
		pointer-events: none;
	}
	.navbar-progress span {
		display: block;
		width: 40%;
		height: 100%;
		border-radius: 0 2px 2px 0;
		background: linear-gradient(90deg, transparent, var(--felt-bright));
		animation: navbar-progress-sweep 1.1s ease-in-out infinite;
	}
	@keyframes navbar-progress-sweep {
		from {
			transform: translateX(-100%);
		}
		to {
			transform: translateX(250%);
		}
	}

	/* app.css clamps every animation to 0.01ms under reduced motion, which would leave this
	   parked off-screen and invisible. Same call as the .spinner there: swap the motion for a
	   static state rather than losing the indicator — a calm full-width bar. */
	@media (prefers-reduced-motion: reduce) {
		.navbar-progress span {
			width: 100%;
			animation: none !important;
			background: var(--felt-bright);
		}
	}

	.nav {
		position: sticky;
		top: 0;
		z-index: 50;
		background: rgba(12, 10, 18, 0.8);
		backdrop-filter: blur(12px);
		border-bottom: 1px solid var(--border-color);
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
	.nav-right {
		display: flex;
		align-items: center;
		gap: 12px;
	}
	.nav-actions {
		display: flex;
		align-items: center;
		gap: 10px;
	}
	.lang {
		display: flex;
		border: 1px solid var(--border-color);
		border-radius: var(--radius-sm);
		overflow: hidden;
		background: var(--bg-elev);
	}
	.lang-opt {
		background: none;
		border: none;
		color: var(--text-faint);
		font-family: var(--font);
		font-size: 0.72rem;
		font-weight: 700;
		letter-spacing: 0.04em;
		padding: 6px 9px;
		cursor: pointer;
		transition:
			background 0.12s ease,
			color 0.12s ease;
	}
	.lang-opt:hover:not(.sel) {
		color: var(--text);
	}
	.lang-opt.sel {
		background: var(--surface-2);
		color: var(--felt-bright);
	}
	.user {
		font-size: 0.9rem;
		color: var(--text-muted);
		padding: 6px 4px;
	}
	.user:hover {
		color: var(--felt-bright);
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
		flex: 1;
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
		.nav-actions {
			gap: 6px;
		}
		.nav-right {
			gap: 8px;
		}
	}
	@media (max-width: 400px) {
		.brand-name {
			display: none;
		}
	}
</style>
