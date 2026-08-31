<script>
	import { login } from '$lib/stores/auth.svelte.js';
	import { errorMessage } from '$lib/http.js';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { t } from '$lib/i18n.svelte.js';
	import { safeNext, withNext } from '$lib/nav.js';

	/** Where the page that bounced us here wants us back. Sanitized: never off-origin. */
	const next = $derived(safeNext($page.url.searchParams.get('next')));

	let username = $state('');
	let password = $state('');
	let error = $state('');
	let busy = $state(false);

	/** @param {SubmitEvent} ev */
	async function submit(ev) {
		ev.preventDefault();
		busy = true;
		error = '';
		try {
			await login(username, password);
			goto(next ?? '/');
		} catch (e) {
			error = errorMessage(e);
			busy = false;
		}
	}
</script>

<svelte:head>
	<title>{t('title.login')}</title>
</svelte:head>

<div class="mx-auto mt-[6vh] max-w-[400px]">
	<form class="card flex flex-col gap-4 bg-base-100 p-5" onsubmit={submit}>
		<h1 class="text-xl font-semibold tracking-tight">{t('auth.login')}</h1>
		<p class="-mt-2 text-base-content/80">{t('auth.loginSubtitle')}</p>
		{#if error}<div class="alert alert-soft alert-error">{error}</div>{/if}
		<div class="flex flex-col gap-1.5">
			<label class="text-xs font-medium text-base-content/80" for="u">{t('auth.username')}</label>
			<input id="u" class="input w-full" bind:value={username} autocomplete="username" required />
		</div>
		<div class="flex flex-col gap-1.5">
			<label class="text-xs font-medium text-base-content/80" for="p">{t('auth.password')}</label>
			<input
				id="p"
				class="input w-full"
				type="password"
				bind:value={password}
				autocomplete="current-password"
				required
			/>
		</div>
		<button class="btn btn-primary" disabled={busy}>
			{busy ? t('auth.loggingIn') : t('auth.login')}
		</button>
		<p class="text-center text-sm text-base-content/80">
			{t('auth.noAccount')}
			<a href={withNext('/register', next)} class="link link-primary font-medium">
				{t('auth.createOne')}
			</a>
		</p>
	</form>
</div>
