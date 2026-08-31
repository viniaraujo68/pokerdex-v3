<script>
	import { auth, changePassword, logoutEverywhere } from '$lib/stores/auth.svelte.js';
	import { errorMessage } from '$lib/http.js';
	import { goto } from '$app/navigation';
	import { t } from '$lib/i18n.svelte.js';
	import { toast } from '@viniaraujo68/plinth/toast';

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
	<div class="mx-auto flex max-w-[460px] flex-col gap-4">
		<div>
			<h1 class="text-2xl font-semibold tracking-tight">{t('account.title')}</h1>
			<p class="mt-1 text-base-content/80">
				{t('account.subtitle', { name: auth.user.username })}
			</p>
		</div>

		<form class="card flex flex-col gap-4 bg-base-100 p-5" onsubmit={submit}>
			<h2 class="text-lg font-semibold">{t('account.changePassword')}</h2>
			<div class="flex flex-col gap-1.5">
				<label class="text-xs font-medium text-base-content/80" for="cur">
					{t('account.currentPassword')}
				</label>
				<input
					id="cur"
					class="input w-full"
					type="password"
					bind:value={current}
					autocomplete="current-password"
					required
				/>
			</div>
			<div class="flex flex-col gap-1.5">
				<label class="text-xs font-medium text-base-content/80" for="new">
					{t('account.newPassword')}
				</label>
				<input
					id="new"
					class="input w-full"
					type="password"
					bind:value={next}
					autocomplete="new-password"
					minlength="6"
					required
				/>
			</div>
			<div class="flex flex-col gap-1.5">
				<label class="text-xs font-medium text-base-content/80" for="cfm">
					{t('account.confirmPassword')}
				</label>
				<input
					id="cfm"
					class="input w-full"
					type="password"
					bind:value={confirm}
					autocomplete="new-password"
					minlength="6"
					required
				/>
			</div>
			<button class="btn btn-primary" disabled={busy}>
				{busy ? t('common.saving') : t('account.changePassword')}
			</button>
		</form>

		<div class="card flex flex-col gap-4 bg-base-100 p-5">
			<h2 class="text-lg font-semibold">{t('account.sessions')}</h2>
			<p class="text-base-content/80">{t('account.logoutAllHint')}</p>
			<button class="btn" onclick={logoutAll} disabled={leaving}>{t('account.logoutAll')}</button>
		</div>
	</div>
{/if}
