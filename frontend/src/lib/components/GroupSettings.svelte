<script>
	import { get, post, patch, del } from '$lib/api.js';
	import { goto } from '$app/navigation';
	import Modal from './Modal.svelte';

	/** @type {{ group: any, onchange: Function }} */
	let { group, onchange } = $props();

	let participants = $state([]);
	let lists = $state({ places: [] });
	let error = $state('');

	// delete-group flow (double confirmation: type the group name)
	let showDelete = $state(false);
	let confirmName = $state('');
	let deleting = $state(false);

	async function deleteGroup() {
		deleting = true;
		try {
			await del(`/groups/${group.id}`);
			goto('/');
		} catch (e) {
			error = e.message;
			deleting = false;
			showDelete = false;
		}
	}

	// group settings form
	let name = $state(group.name);
	let description = $state(group.description);
	let visibility = $state(group.visibility);
	let savingGroup = $state(false);

	$effect(() => {
		loadAll();
	});

	async function loadAll() {
		try {
			const [pp, places] = await Promise.all([
				get(`/groups/${group.id}/participants`),
				get(`/groups/${group.id}/places`)
			]);
			participants = pp;
			lists = { places };
		} catch (e) {
			error = e.message;
		}
	}

	async function saveGroup() {
		savingGroup = true;
		error = '';
		try {
			const updated = await patch(`/groups/${group.id}`, { name, description, visibility });
			onchange(updated);
		} catch (e) {
			error = e.message;
		} finally {
			savingGroup = false;
		}
	}

	async function rotateToken() {
		const updated = await post(`/groups/${group.id}/rotate-share-token`);
		onchange(updated);
	}

	// catalog handlers (places only)
	let drafts = $state({ places: '', participant: '' });

	async function addItem(kind) {
		const value = drafts[kind].trim();
		if (!value) return;
		try {
			const item = await post(`/groups/${group.id}/${kind}`, { name: value });
			lists[kind] = [...lists[kind], item].sort((a, b) => a.name.localeCompare(b.name));
			drafts[kind] = '';
		} catch (e) {
			error = e.message;
		}
	}

	async function removeItem(kind, id) {
		try {
			await del(`/groups/${group.id}/${kind}/${id}`);
			lists[kind] = lists[kind].filter((x) => x.id !== id);
		} catch (e) {
			error = e.message;
		}
	}

	async function addParticipant() {
		const value = drafts.participant.trim();
		if (!value) return;
		try {
			const p = await post(`/groups/${group.id}/participants`, { name: value });
			participants = [...participants, p].sort((a, b) => a.name.localeCompare(b.name));
			drafts.participant = '';
			onchange();
		} catch (e) {
			error = e.message;
		}
	}

	async function removeParticipant(p) {
		try {
			await del(`/groups/${group.id}/participants/${p.id}`);
			await loadAll();
			onchange();
		} catch (e) {
			error = e.message;
		}
	}

	const shareUrl = $derived(
		typeof window !== 'undefined'
			? `${window.location.origin}/g/${group.slug}` +
					(group.visibility !== 'public' && group.share_token ? `?t=${group.share_token}` : '')
			: ''
	);

	function copyShare() {
		navigator.clipboard?.writeText(shareUrl);
	}

	const catalogMeta = [{ kind: 'places', title: '📍 Locais' }];
</script>

{#if error}<div class="toast toast-error">{error}</div>{/if}

<div class="settings stack">
	<!-- Group basics -->
	<div class="card stack">
		<h3>Grupo</h3>
		<div class="field">
			<label for="s-name">Nome</label>
			<input id="s-name" bind:value={name} />
		</div>
		<div class="field">
			<label for="s-desc">Descrição</label>
			<input id="s-desc" bind:value={description} />
		</div>
		<div class="field">
			<label for="s-vis">Visibilidade</label>
			<select id="s-vis" bind:value={visibility}>
				<option value="public">Público</option>
				<option value="private">Privado</option>
			</select>
		</div>
		<div>
			<button class="btn btn-primary btn-sm" disabled={savingGroup} onclick={saveGroup}>
				Salvar alterações
			</button>
		</div>
	</div>

	<!-- Public link -->
	<div class="card stack">
		<h3>Link público</h3>
		{#if visibility === 'public'}
			<p class="muted small">Qualquer pessoa com este link vê o placar (somente leitura).</p>
		{:else}
			<p class="muted small">
				Grupo privado: o link só funciona com o token abaixo. Gire o token para revogar links
				antigos.
			</p>
		{/if}
		<div class="share">
			<input readonly value={shareUrl} />
			<button class="btn btn-ghost btn-sm" onclick={copyShare}>Copiar</button>
		</div>
		{#if visibility !== 'public'}
			<div>
				<button class="btn btn-ghost btn-sm" onclick={rotateToken}>🔄 Gerar novo token</button>
			</div>
		{/if}
	</div>

	<!-- Participants -->
	<div class="card stack">
		<h3>Participantes</h3>
		<div class="adder">
			<input
				placeholder="Nome do participante"
				bind:value={drafts.participant}
				onkeydown={(e) => e.key === 'Enter' && (e.preventDefault(), addParticipant())}
			/>
			<button class="btn btn-ghost btn-sm" onclick={addParticipant}>Adicionar</button>
		</div>
		<div class="tags">
			{#each participants as p}
				<span class="chip" class:inactive={!p.active}>
					{p.name}
					<button class="chip-x" title="Remover" onclick={() => removeParticipant(p)}>✕</button>
				</span>
			{/each}
			{#if participants.length === 0}<span class="faint small">Nenhum participante ainda.</span>{/if}
		</div>
	</div>

	<!-- Catalogs -->
	<div class="catalogs grid">
		{#each catalogMeta as meta}
			<div class="card stack">
				<h3>{meta.title}</h3>
				<div class="adder">
					<input
						placeholder="Adicionar…"
						bind:value={drafts[meta.kind]}
						onkeydown={(e) => e.key === 'Enter' && (e.preventDefault(), addItem(meta.kind))}
					/>
					<button class="btn btn-ghost btn-sm" onclick={() => addItem(meta.kind)}>+</button>
				</div>
				<div class="tags">
					{#each lists[meta.kind] as item}
						<span class="chip">
							{item.name ?? item.label}
							<button class="chip-x" onclick={() => removeItem(meta.kind, item.id)}>✕</button>
						</span>
					{/each}
					{#if lists[meta.kind].length === 0}<span class="faint small">vazio</span>{/if}
				</div>
			</div>
		{/each}
	</div>

	<!-- Danger zone -->
	<div class="card stack danger">
		<h3>Zona de perigo</h3>
		<p class="muted small">
			Excluir o grupo apaga <strong>permanentemente</strong> todas as noites, participantes e locais.
			Não dá pra desfazer.
		</p>
		<div>
			<button class="btn btn-danger btn-sm" onclick={() => { showDelete = true; confirmName = ''; }}>
				Excluir grupo
			</button>
		</div>
	</div>
</div>

{#if showDelete}
	<Modal title="Excluir grupo" onclose={() => (showDelete = false)}>
		<div class="stack">
			<p class="muted">
				Isso vai apagar <strong>{group.name}</strong> e tudo dentro dele para sempre. Para confirmar,
				digite o nome do grupo abaixo:
			</p>
			<input
				placeholder={group.name}
				bind:value={confirmName}
				onkeydown={(e) => e.key === 'Enter' && confirmName === group.name && deleteGroup()}
			/>
			<div class="row mactions">
				<button class="btn btn-ghost" onclick={() => (showDelete = false)}>Cancelar</button>
				<button
					class="btn btn-danger"
					disabled={confirmName !== group.name || deleting}
					onclick={deleteGroup}
				>
					{deleting ? 'Excluindo…' : 'Excluir permanentemente'}
				</button>
			</div>
		</div>
	</Modal>
{/if}

<style>
	.small {
		font-size: 0.85rem;
		margin: 0;
	}
	.danger {
		border-color: rgba(240, 88, 106, 0.4);
	}
	.danger h3 {
		color: var(--red);
	}
	.mactions {
		justify-content: flex-end;
		margin-top: 4px;
	}
	.adder {
		display: flex;
		gap: 8px;
	}
	.share {
		display: flex;
		gap: 8px;
	}
	.share input {
		font-size: 0.85rem;
		color: var(--text-muted);
	}
	.tags {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}
	.chip {
		gap: 4px;
	}
	.chip.inactive {
		opacity: 0.5;
	}
	.chip-x {
		background: none;
		border: none;
		color: var(--text-faint);
		cursor: pointer;
		padding: 0 2px;
		font-size: 0.8rem;
	}
	.chip-x:hover {
		color: var(--text);
	}
	.catalogs {
		grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
	}
</style>
