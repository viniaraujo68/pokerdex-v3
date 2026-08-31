<script>
	import './layout.css';
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { navigating } from '$app/stores';
	import { page } from '$app/state';
	import { RoutingContext, setRoutingContext } from '@viniaraujo68/plinth/routing';
	import { AppShell } from '@viniaraujo68/plinth/shell';
	import {
		readThemePreference,
		setThemeContext,
		ThemeContext,
		ThemeController,
		ThemeToggle
	} from '@viniaraujo68/plinth/theme';
	import { setUserContext } from '@viniaraujo68/plinth/user';
	import { Toaster } from '@viniaraujo68/plinth/toast';
	import { routes } from '$lib/routes.js';
	import { user } from '$lib/user.js';
	import { auth, loadUser } from '$lib/stores/auth.svelte.js';
	import { i18n, setLocale, t } from '$lib/i18n.svelte.js';

	let { children } = $props();

	setRoutingContext(new RoutingContext(routes, page));
	setUserContext(user);

	/* The cookie is read on the client only: the authenticated routes are `ssr = false`, so there
	   is no server render to seed. The first paint is already correct anyway — `hooks.server.js`
	   stamps `data-theme` on `<html>` from the same cookie before the shell leaves the server. */
	setThemeContext(new ThemeContext(browser ? readThemePreference() : 'system'));

	onMount(loadUser);

	const isPublicScoreboard = $derived(page.route.id?.startsWith('/g/') ?? false);

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

<!-- Exactly once, unconditionally: this hidden checkbox is what the theme stylesheet keys on. -->
<ThemeController />

<!-- Progress, not percentage: SvelteKit exposes no load fraction, so this is an indeterminate
     sweep. aria-hidden because `navigating` is not something to narrate on every click; the
     destination page's own heading is the real announcement. -->
{#if showProgress}
	<div class="navbar-progress" aria-hidden="true"><span></span></div>
{/if}

{#snippet brandMark(collapsed = false)}
	<a href="/" class="brand">
		<span class="logo">♠</span>
		{#if !collapsed}<span class="brand-name">Pokerdex</span>{/if}
	</a>
{/snippet}

{#snippet langToggle()}
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
{/snippet}

{#snippet tagline()}
	<footer class="foot">
		<div class="container text-base-content/65">{t('footer.tagline')}</div>
	</footer>
{/snippet}

{#if isPublicScoreboard}
	<header class="public-nav">
		<div class="container public-nav-inner">
			{@render brandMark()}

			<div class="public-nav-right">
				{#if auth.ready && !auth.user}
					<a href="/register" class="btn btn-sm btn-primary">{t('nav.register')}</a>
				{/if}
				{@render langToggle()}
				<ThemeToggle iconOnly />
			</div>
		</div>
	</header>

	<main class="container page">
		{@render children()}
	</main>

	{@render tagline()}
{:else}
	<div class="shell-host">
		<AppShell
			navLabel={t('nav.main')}
			collapseLabel={t('nav.collapse')}
			moreLabel={t('nav.more')}
			closeLabel={t('common.close')}
			logoutLabel={t('nav.logout')}
		>
			{#snippet brand({ collapsed })}
				{@render brandMark(collapsed)}
			{/snippet}

			{#snippet icon(route)}
				{@const name = route.meta.icon}
				<svg
					class="size-5"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.75"
					stroke-linecap="round"
					stroke-linejoin="round"
					aria-hidden="true"
				>
					{#if name === 'home'}
						<path d="M3 10.5 12 3l9 7.5" />
						<path d="M5 9.5V21h14V9.5" />
					{:else if name === 'explore'}
						<circle cx="12" cy="12" r="9" />
						<path d="m15.5 8.5-2 5-5 2 2-5z" />
					{:else if name === 'account'}
						<circle cx="12" cy="8" r="3.5" />
						<path d="M5 20a7 7 0 0 1 14 0" />
					{:else if name === 'login'}
						<path d="M10 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h4" />
						<path d="m15 8 4 4-4 4M19 12H9" />
					{:else if name === 'register'}
						<circle cx="9" cy="8" r="3.5" />
						<path d="M2.5 20a6.5 6.5 0 0 1 13 0" />
						<path d="M19 8v6M22 11h-6" />
					{/if}
				</svg>
			{/snippet}

			{#snippet footer()}
				<div class="shell-controls">
					{@render langToggle()}
					<ThemeToggle iconOnly />
				</div>
			{/snippet}

			<div class="shell-page">
				<div class="container page">
					{@render children()}
				</div>

				{@render tagline()}
			</div>
		</AppShell>
	</div>
{/if}

<!-- One overlay for the whole app, outside both branches: it outlives navigations, so a toast
     fired just before a goto() is still on screen when the next page renders. -->
<Toaster
	class="z-[80]"
	position="top-end"
	label={t('toast.region')}
	dismissLabel={t('common.close')}
/>

<style>
	.container {
		width: 100%;
		max-width: 1080px;
		margin: 0 auto;
		padding: 0 20px;
	}

	/* Above the shell — the progress bar is fixed to the viewport, the shell is not. */
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
		background: linear-gradient(90deg, transparent, var(--color-primary));
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

	/* layout.css clamps every animation to 0.01ms under reduced motion, which would leave this
	   parked off-screen and invisible. Swap the motion for a static state rather than losing the
	   indicator — a calm full-width bar. */
	@media (prefers-reduced-motion: reduce) {
		.navbar-progress span {
			width: 100%;
			animation: none !important;
			background: var(--color-primary);
		}
	}

	.shell-host {
		height: 100dvh;
	}

	.public-nav {
		position: sticky;
		top: 0;
		z-index: 50;
		background: color-mix(in oklch, var(--color-base-100) 82%, transparent);
		backdrop-filter: blur(12px);
		border-bottom: 1px solid color-mix(in oklch, var(--color-base-content) 12%, transparent);
	}
	.public-nav-inner {
		display: flex;
		align-items: center;
		justify-content: space-between;
		height: 64px;
	}
	.public-nav-right {
		display: flex;
		align-items: center;
		gap: 12px;
	}
	@media (max-width: 560px) {
		.public-nav-right {
			gap: 8px;
		}
	}
	@media (max-width: 400px) {
		.public-nav .brand-name {
			display: none;
		}
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
		border-radius: var(--radius-field);
		background-color: var(--color-primary);
		color: var(--color-primary-content);
		font-size: 1.2rem;
		font-weight: 700;
	}
	.brand-name {
		font-weight: 700;
		font-size: 1.15rem;
		letter-spacing: -0.02em;
	}

	.shell-controls {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	:global(.plinth-shell.collapsed .shell-sidebar) .shell-controls {
		flex-direction: column;
	}
	:global(.plinth-sheet) .shell-controls {
		flex-direction: row;
	}

	.lang {
		display: flex;
		border: 1px solid color-mix(in oklch, var(--color-base-content) 15%, transparent);
		border-radius: var(--radius-field);
		overflow: hidden;
		background: var(--color-base-100);
	}
	:global(.plinth-shell.collapsed .shell-sidebar) .lang {
		flex-direction: column;
	}
	:global(.plinth-sheet) .lang {
		flex-direction: row;
	}
	:global(.plinth-sheet) .lang-opt {
		min-height: 2.25rem;
		padding: 6px 14px;
	}
	.lang-opt {
		background: none;
		border: none;
		color: color-mix(in oklch, var(--color-base-content) 65%, transparent);
		font-family: inherit;
		font-size: 0.72rem;
		font-weight: 600;
		letter-spacing: 0.04em;
		padding: 6px 9px;
		cursor: pointer;
		transition:
			background 0.12s ease,
			color 0.12s ease;
	}
	.lang-opt:hover:not(.sel) {
		color: var(--color-base-content);
	}
	.lang-opt.sel {
		background: color-mix(in oklch, var(--color-primary) 14%, transparent);
		color: var(--ink-primary);
	}

	.shell-page {
		display: flex;
		min-height: 100%;
		flex-direction: column;
	}
	.page {
		flex: 1;
		padding-top: 32px;
		padding-bottom: 64px;
	}
	.foot {
		border-top: 1px solid color-mix(in oklch, var(--color-base-content) 10%, transparent);
		padding: 20px 0;
		font-size: 0.82rem;
		text-align: center;
	}
</style>
