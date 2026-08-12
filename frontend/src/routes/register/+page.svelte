<script>
	import { register } from '$lib/stores/auth.svelte.js';
	import { errorMessage } from '$lib/api.js';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { t } from '$lib/i18n.svelte.js';
	import { safeNext, withNext } from '$lib/nav.js';

	/** Preserved through the login ↔ register hop, so the bounce still lands. */
	const next = $derived(safeNext($page.url.searchParams.get('next')));

	let username = $state('');
	let password = $state('');
	let error = $state('');
	let busy = $state(false);

	/** @param {SubmitEvent} ev */
	async function submit(ev) {
		ev.preventDefault();
		if (password.length < 6) {
			error = t('auth.passwordTooShort');
			return;
		}
		busy = true;
		error = '';
		try {
			await register(username, password);
			goto(next ?? '/');
		} catch (e) {
			error = errorMessage(e);
			busy = false;
		}
	}
</script>

<svelte:head>
	<title>{t('title.register')}</title>
</svelte:head>

<!-- .auth / .auth-alt / .link are shared with /login, so they live in app.css -->
<div class="auth">
	<form class="card stack" onsubmit={submit}>
		<h1>{t('auth.register')}</h1>
		<p class="muted">{t('auth.registerSubtitle')}</p>
		{#if error}<div class="toast toast-error">{error}</div>{/if}
		<div class="field">
			<label for="u">{t('auth.username')}</label>
			<input id="u" bind:value={username} autocomplete="username" minlength="3" required />
		</div>
		<div class="field">
			<label for="p">{t('auth.password')}</label>
			<input id="p" type="password" bind:value={password} autocomplete="new-password" minlength="6" required />
		</div>
		<button class="btn btn-primary" disabled={busy}>{busy ? t('auth.registering') : t('auth.register')}</button>
		<p class="muted auth-alt">
			{t('auth.hasAccount')}
			<a href={withNext('/login', next)} class="link">{t('auth.login')}</a>
		</p>
	</form>
</div>
