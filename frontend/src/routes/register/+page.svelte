<script>
	import { register } from '$lib/stores/auth.svelte.js';
	import { goto } from '$app/navigation';

	let username = $state('');
	let password = $state('');
	let error = $state('');
	let busy = $state(false);

	async function submit(ev) {
		ev.preventDefault();
		if (password.length < 6) {
			error = 'A senha precisa ter ao menos 6 caracteres.';
			return;
		}
		busy = true;
		error = '';
		try {
			await register(username, password);
			goto('/');
		} catch (e) {
			error = e.message;
			busy = false;
		}
	}
</script>

<div class="auth">
	<form class="card stack" onsubmit={submit}>
		<h1>Criar conta</h1>
		<p class="muted">Crie sua conta e abra seu primeiro grupo.</p>
		{#if error}<div class="toast toast-error">{error}</div>{/if}
		<div class="field">
			<label for="u">Usuário</label>
			<input id="u" bind:value={username} autocomplete="username" minlength="3" required />
		</div>
		<div class="field">
			<label for="p">Senha</label>
			<input id="p" type="password" bind:value={password} autocomplete="new-password" minlength="6" required />
		</div>
		<button class="btn btn-primary" disabled={busy}>{busy ? 'Criando…' : 'Criar conta'}</button>
		<p class="muted small">Já tem conta? <a href="/login" class="link">Entrar</a></p>
	</form>
</div>

<style>
	.auth {
		max-width: 400px;
		margin: 6vh auto 0;
	}
	.small {
		font-size: 0.9rem;
		text-align: center;
		margin: 0;
	}
	.link {
		color: var(--felt-bright);
		font-weight: 600;
	}
</style>
