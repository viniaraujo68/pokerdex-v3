<script>
	import './layout.css';
	import './legacy-preflight.css';
	import '../app.css';
	import { onMount } from 'svelte';
	import { navigating } from '$app/stores';
	import { page } from '$app/state';
	import { RoutingContext, setRoutingContext } from '@viniaraujo68/plinth/routing';
	import { AppShell } from '@viniaraujo68/plinth/shell';
	import { setUserContext } from '@viniaraujo68/plinth/user';
	import { routes } from '$lib/routes.js';
	import { user } from '$lib/user.js';
	import { loadUser } from '$lib/stores/auth.svelte.js';
	import { i18n, setLocale, t } from '$lib/i18n.svelte.js';
	import Toasts from '$lib/components/Toasts.svelte';

	let { children } = $props();

	setRoutingContext(new RoutingContext(routes, page));
	setUserContext(user);

	onMount(loadUser);

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

<div class="shell-host">
	<AppShell
		navLabel={t('nav.main')}
		collapseLabel={t('nav.collapse')}
		moreLabel={t('nav.more')}
		closeLabel={t('common.close')}
		logoutLabel={t('nav.logout')}
	>
		{#snippet brand({ collapsed })}
			<a href="/" class="brand">
				<span class="logo">♠</span>
				{#if !collapsed}<span class="brand-name">Pokerdex</span>{/if}
			</a>
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

		<div class="shell-page">
			<div class="container page">
				{@render children()}
			</div>

			<footer class="foot">
				<div class="container faint">{t('footer.tagline')}</div>
			</footer>
		</div>
	</AppShell>
</div>

<!-- One overlay for the whole app: it outlives navigations, so a toast fired just before a
     goto() is still on screen when the next page renders. -->
<Toasts />

<style>
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

	.shell-host {
		height: 100dvh;
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
	.lang {
		display: flex;
		border: 1px solid var(--border-color);
		border-radius: var(--radius-sm);
		overflow: hidden;
		background: var(--bg-elev);
	}
	:global(.plinth-shell.collapsed) .lang {
		flex-direction: column;
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
		border-top: 1px solid var(--border-soft);
		padding: 20px 0;
		font-size: 0.82rem;
		text-align: center;
	}
</style>
