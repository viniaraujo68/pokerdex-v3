<script>
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { get, post, put } from '$lib/api.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import NightForm from '$lib/components/NightForm.svelte';

	const groupId = $derived($page.params.id);
	const editId = $derived($page.url.searchParams.get('edit'));

	let catalogs = $state(null);
	let night = $state(null);
	let loading = $state(true);
	let saving = $state(false);
	let error = $state('');

	$effect(() => {
		if (auth.ready && !auth.user) goto('/login');
	});

	$effect(() => {
		if (groupId) load();
	});

	async function load() {
		loading = true;
		try {
			const [participants, places] = await Promise.all([
				get(`/groups/${groupId}/participants`),
				get(`/groups/${groupId}/places`)
			]);
			catalogs = { participants, places };
			if (editId) night = await get(`/groups/${groupId}/nights/${editId}`);
		} catch (e) {
			error = e.message;
		} finally {
			loading = false;
		}
	}

	async function save(payload) {
		saving = true;
		error = '';
		try {
			if (editId) await put(`/groups/${groupId}/nights/${editId}`, payload);
			else await post(`/groups/${groupId}/nights`, payload);
			goto(`/groups/${groupId}`);
		} catch (e) {
			error = e.message;
			saving = false;
		}
	}
</script>

<div class="head">
	<a href={`/groups/${groupId}`} class="muted back">← Voltar ao grupo</a>
	<h1>{editId ? 'Editar noite' : 'Nova noite'}</h1>
</div>

{#if error}<div class="toast toast-error">{error}</div>{/if}

{#if loading || !catalogs}
	<div class="center"><div class="spinner"></div></div>
{:else}
	<NightForm
		{groupId}
		{catalogs}
		{night}
		{saving}
		onsubmit={save}
		oncancel={() => goto(`/groups/${groupId}`)}
	/>
{/if}

<style>
	.head {
		margin-bottom: 20px;
	}
	.back {
		font-size: 0.9rem;
		display: inline-block;
		margin-bottom: 8px;
	}
	.center {
		display: grid;
		place-items: center;
		min-height: 30vh;
	}
</style>
