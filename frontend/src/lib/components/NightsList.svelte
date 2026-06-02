<script>
	import NightCard from './NightCard.svelte';

	/** @type {{ nights: any[], editable?: boolean, onEdit?: Function, onDelete?: Function }} */
	let { nights, editable = false, onEdit, onDelete } = $props();

	let placeFilter = $state('');
	let dateFrom = $state('');
	let dateTo = $state('');
	/** @type {Set<number>} */
	let selectedPlayers = $state(new Set());

	// Distinct places present across the nights.
	const places = $derived.by(() => {
		const map = new Map();
		for (const n of nights) if (n.place_id) map.set(n.place_id, n.place_name);
		return [...map].map(([id, name]) => ({ id, name })).sort((a, b) => a.name.localeCompare(b.name));
	});

	// Distinct participants present across the nights.
	const players = $derived.by(() => {
		const map = new Map();
		for (const n of nights) for (const e of n.entries) map.set(e.participant_id, e.participant_name);
		return [...map].map(([id, name]) => ({ id, name })).sort((a, b) => a.name.localeCompare(b.name));
	});

	const filtered = $derived(
		nights.filter((n) => {
			if (placeFilter && n.place_id !== Number(placeFilter)) return false;
			if (dateFrom && n.date < dateFrom) return false;
			if (dateTo && n.date > dateTo) return false;
			if (selectedPlayers.size) {
				const present = new Set(n.entries.map((e) => e.participant_id));
				for (const pid of selectedPlayers) if (!present.has(pid)) return false; // AND
			}
			return true;
		})
	);

	const hasFilters = $derived(
		placeFilter !== '' || dateFrom !== '' || dateTo !== '' || selectedPlayers.size > 0
	);

	function togglePlayer(id) {
		const next = new Set(selectedPlayers);
		next.has(id) ? next.delete(id) : next.add(id);
		selectedPlayers = next;
	}

	function clearFilters() {
		placeFilter = '';
		dateFrom = '';
		dateTo = '';
		selectedPlayers = new Set();
	}
</script>

{#if nights.length === 0}
	<div class="card empty">Nenhuma noite registrada ainda. 🃏</div>
{:else}
	<div class="card card-tight filters">
		<div class="ftop">
			<div class="frow">
				<label for="pf">Local</label>
				<select id="pf" bind:value={placeFilter}>
					<option value="">Todos os locais</option>
					{#each places as p}<option value={p.id}>{p.name}</option>{/each}
				</select>
			</div>
			<div class="frow">
				<label for="df">De</label>
				<input id="df" type="date" bind:value={dateFrom} max={dateTo || undefined} />
			</div>
			<div class="frow">
				<label for="dt">Até</label>
				<input id="dt" type="date" bind:value={dateTo} min={dateFrom || undefined} />
			</div>
		</div>

		<div class="frow players">
			<span class="flabel">Participantes presentes</span>
			<div class="chips">
				{#each players as p}
					<button
						type="button"
						class="chip toggle"
						class:on={selectedPlayers.has(p.id)}
						onclick={() => togglePlayer(p.id)}
					>
						{p.name}
					</button>
				{/each}
			</div>
			{#if selectedPlayers.size > 1}
				<span class="faint hint">mostrando noites em que todos os selecionados jogaram</span>
			{/if}
		</div>

		<div class="fmeta">
			<span class="muted">{filtered.length} de {nights.length} noites</span>
			{#if hasFilters}
				<button class="btn btn-ghost btn-sm" onclick={clearFilters}>Limpar filtros</button>
			{/if}
		</div>
	</div>

	{#if filtered.length === 0}
		<div class="card empty">Nenhuma noite com esses filtros.</div>
	{:else}
		<div class="stack">
			{#each filtered as night (night.id)}
				<NightCard {night} {editable} {onEdit} {onDelete} />
			{/each}
		</div>
	{/if}
{/if}

<style>
	.filters {
		display: flex;
		flex-direction: column;
		gap: 14px;
		margin-bottom: 16px;
	}
	.ftop {
		display: flex;
		flex-wrap: wrap;
		gap: 14px;
	}
	.ftop .frow {
		flex: 1;
		min-width: 150px;
	}
	.frow {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.flabel {
		font-size: 0.82rem;
		font-weight: 600;
		color: var(--text-muted);
		margin-bottom: 2px;
	}
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}
	.toggle {
		cursor: pointer;
		background: var(--surface-2);
		transition:
			background 0.12s ease,
			border-color 0.12s ease,
			color 0.12s ease;
	}
	.toggle:hover {
		border-color: var(--felt-bright);
	}
	.toggle.on {
		background: rgba(124, 58, 237, 0.2);
		border-color: var(--felt-bright);
		color: var(--felt-bright);
	}
	.hint {
		font-size: 0.78rem;
	}
	.fmeta {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
		border-top: 1px solid var(--border-soft);
		padding-top: 12px;
		font-size: 0.9rem;
	}
</style>
