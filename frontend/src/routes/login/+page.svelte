<script>
	import { login } from '$lib/stores/auth.svelte.js';
	import { errorMessage } from '$lib/api.js';
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

<!-- .auth / .auth-alt / .pd-link are shared with /register, so they live in app.css -->
<div class="auth">
	<form class="pd-card pd-stack" onsubmit={submit}>
		<h1>{t('auth.login')}</h1>
		<p class="muted">{t('auth.loginSubtitle')}</p>
		{#if error}<div class="pd-toast pd-toast-error">{error}</div>{/if}
		<div class="field">
			<label for="u">{t('auth.username')}</label>
			<input id="u" bind:value={username} autocomplete="username" required />
		</div>
		<div class="field">
			<label for="p">{t('auth.password')}</label>
			<input id="p" type="password" bind:value={password} autocomplete="current-password" required />
		</div>
		<button class="pd-btn pd-btn-primary" disabled={busy}>{busy ? t('auth.loggingIn') : t('auth.login')}</button>
		<p class="muted auth-alt">
			{t('auth.noAccount')}
			<a href={withNext('/register', next)} class="pd-link">{t('auth.createOne')}</a>
		</p>
	</form>
</div>
