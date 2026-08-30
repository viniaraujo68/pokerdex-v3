<script>
	import { auth, changePassword, logoutEverywhere } from '$lib/stores/auth.svelte.js';
	import { errorMessage } from '$lib/api.js';
	import { goto } from '$app/navigation';
	import { t } from '$lib/i18n.svelte.js';
	import { toast } from '$lib/toast.svelte.js';

	// Client-side guard: this page has no server load, so bounce anonymous visitors to login
	// once the auth probe has settled (auth.ready).
	$effect(() => {
		if (auth.ready && !auth.user) goto('/login?next=/account');
	});

	let current = $state('');
	let next = $state('');
	let confirm = $state('');
	let busy = $state(false);
	let leaving = $state(false);

	/** @param {SubmitEvent} ev */
	async function submit(ev) {
		ev.preventDefault();
		if (next.length < 6) {
			toast.error(t('auth.passwordTooShort'));
			return;
		}
		if (next !== confirm) {
			toast.error(t('account.passwordMismatch'));
			return;
		}
		busy = true;
		try {
			await changePassword(current, next);
			toast.success(t('account.passwordChanged'));
			current = next = confirm = '';
		} catch (e) {
			toast.error(errorMessage(e));
		} finally {
			busy = false;
		}
	}

	async function logoutAll() {
		leaving = true;
		try {
			await logoutEverywhere();
			goto('/login');
		} catch (e) {
			toast.error(errorMessage(e));
			leaving = false;
		}
	}
</script>

<svelte:head>
	<title>{t('title.account')}</title>
</svelte:head>

{#if auth.ready && auth.user}
	<div class="account pd-stack">
		<div>
			<h1>{t('account.title')}</h1>
			<p class="muted">{t('account.subtitle', { name: auth.user.username })}</p>
		</div>

		<form class="pd-card pd-stack" onsubmit={submit}>
			<h2>{t('account.changePassword')}</h2>
			<div class="field">
				<label for="cur">{t('account.currentPassword')}</label>
				<input
					id="cur"
					type="password"
					bind:value={current}
					autocomplete="current-password"
					required
				/>
			</div>
			<div class="field">
				<label for="new">{t('account.newPassword')}</label>
				<input
					id="new"
					type="password"
					bind:value={next}
					autocomplete="new-password"
					minlength="6"
					required
				/>
			</div>
			<div class="field">
				<label for="cfm">{t('account.confirmPassword')}</label>
				<input
					id="cfm"
					type="password"
					bind:value={confirm}
					autocomplete="new-password"
					minlength="6"
					required
				/>
			</div>
			<button class="pd-btn pd-btn-primary" disabled={busy}>
				{busy ? t('common.saving') : t('account.changePassword')}
			</button>
		</form>

		<div class="pd-card pd-stack">
			<h2>{t('account.sessions')}</h2>
			<p class="muted">{t('account.logoutAllHint')}</p>
			<button class="pd-btn pd-btn-ghost" onclick={logoutAll} disabled={leaving}>
				{t('account.logoutAll')}
			</button>
		</div>
	</div>
{/if}

<style>
	.account {
		max-width: 460px;
		margin: 0 auto;
	}
	h2 {
		font-size: 1.1rem;
		margin: 0;
	}
</style>
