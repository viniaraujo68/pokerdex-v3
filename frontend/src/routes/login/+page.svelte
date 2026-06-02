<script>
	import { login } from '$lib/stores/auth.svelte.js';
	import { goto } from '$app/navigation';

	let username = $state('');
	let password = $state('');
	let error = $state('');
	let busy = $state(false);

	async function submit(ev) {
		ev.preventDefault();
		busy = true;
		error = '';
		try {
			await login(username, password);
			goto('/');
		} catch (e) {
			error = e.message;
			busy = false;
		}
	}
</script>

<div class="auth">
	<form class="card stack" onsubmit={submit}>
		<h1>Entrar</h1>
		<p class="muted">Acesse seus grupos.</p>
		{#if error}<div class="toast toast-error">{error}</div>{/if}
		<div class="field">
			<label for="u">Usuário</label>
			<input id="u" bind:value={username} autocomplete="username" required />
		</div>
		<div class="field">
			<label for="p">Senha</label>
			<input id="p" type="password" bind:value={password} autocomplete="current-password" required />
		</div>
		<button class="btn btn-primary" disabled={busy}>{busy ? 'Entrando…' : 'Entrar'}</button>
		<p class="muted small">Não tem conta? <a href="/register" class="link">Criar uma</a></p>
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
