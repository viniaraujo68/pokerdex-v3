<script>
	import { post } from '$lib/api.js';
	import { parseMoney, formatMoney, formatSigned, moneyClass, centsToInput } from '$lib/money.js';

	/** @type {{ groupId: number|string, catalogs: any, night?: any, saving?: boolean, onsubmit: Function, oncancel: Function }} */
	let { groupId, catalogs, night = null, saving = false, onsubmit, oncancel } = $props();

	const today = new Date().toISOString().slice(0, 10);

	let date = $state(night?.date ?? today);
	let place_id = $state(night?.place_id ?? '');

	let participants = $state([...catalogs.participants]);
	let places = $state([...catalogs.places]);

	let newPlace = $state('');
	let addingPlace = $state(false);
	let showNewPlace = $state(false);

	/** @type {{participant_id: any, buy_in: string, cash_out: string}[]} */
	let rows = $state(
		night?.entries?.length
			? night.entries.map((e) => ({
					participant_id: e.participant_id,
					buy_in: centsToInput(e.buy_in_cents),
					cash_out: centsToInput(e.cash_out_cents)
				}))
			: [{ participant_id: '', buy_in: '', cash_out: '' }]
	);

	let newParticipant = $state('');
	let addingParticipant = $state(false);

	const potCents = $derived(rows.reduce((s, r) => s + parseMoney(r.buy_in), 0));
	const balanceCents = $derived(
		rows.reduce((s, r) => s + (parseMoney(r.cash_out) - parseMoney(r.buy_in)), 0)
	);
	const balanced = $derived(Math.abs(balanceCents) < 1);

	const usedIds = $derived(new Set(rows.map((r) => Number(r.participant_id)).filter(Boolean)));

	function addRow() {
		rows = [...rows, { participant_id: '', buy_in: '', cash_out: '' }];
	}
	function removeRow(i) {
		rows = rows.filter((_, idx) => idx !== i);
	}

	async function addParticipant() {
		const name = newParticipant.trim();
		if (!name) return;
		addingParticipant = true;
		try {
			const p = await post(`/groups/${groupId}/participants`, { name });
			participants = [...participants, { id: p.id, name: p.name, active: true }].sort((a, b) =>
				a.name.localeCompare(b.name)
			);
			newParticipant = '';
			// auto-assign to first empty row, else add a row
			const empty = rows.findIndex((r) => !r.participant_id);
			if (empty >= 0) rows[empty].participant_id = p.id;
			else rows = [...rows, { participant_id: p.id, buy_in: '', cash_out: '' }];
		} catch (e) {
			alert(e.message);
		} finally {
			addingParticipant = false;
		}
	}

	async function addPlace() {
		const name = newPlace.trim();
		if (!name) return;
		addingPlace = true;
		try {
			const p = await post(`/groups/${groupId}/places`, { name });
			places = [...places, p].sort((a, b) => a.name.localeCompare(b.name));
			place_id = p.id;
			newPlace = '';
			showNewPlace = false;
		} catch (e) {
			alert(e.message);
		} finally {
			addingPlace = false;
		}
	}

	function profitOf(r) {
		return parseMoney(r.cash_out) - parseMoney(r.buy_in);
	}

	function submit(ev) {
		ev.preventDefault();
		const entries = rows
			.filter((r) => r.participant_id)
			.map((r) => ({
				participant_id: Number(r.participant_id),
				buy_in_cents: parseMoney(r.buy_in),
				cash_out_cents: parseMoney(r.cash_out)
			}));
		onsubmit({
			date,
			place_id: place_id ? Number(place_id) : null,
			entries
		});
	}

	const activeParticipants = $derived(participants.filter((p) => p.active));
</script>

<form class="stack" onsubmit={submit}>
	<div class="card stack">
		<div class="grid meta-grid">
			<div class="field">
				<label for="date">Data</label>
				<input id="date" type="date" bind:value={date} required />
			</div>
			<div class="field">
				<label for="place">Local</label>
				{#if showNewPlace}
					<div class="newp">
						<input
							placeholder="Nome do local"
							bind:value={newPlace}
							onkeydown={(e) => e.key === 'Enter' && (e.preventDefault(), addPlace())}
						/>
						<button type="button" class="btn btn-primary btn-sm" disabled={addingPlace} onclick={addPlace}>
							Salvar
						</button>
						<button type="button" class="btn btn-ghost btn-sm" onclick={() => (showNewPlace = false)}>
							✕
						</button>
					</div>
				{:else}
					<div class="newp">
						<select id="place" bind:value={place_id}>
							<option value="">—</option>
							{#each places as p}<option value={p.id}>{p.name}</option>{/each}
						</select>
						<button type="button" class="btn btn-ghost btn-sm" onclick={() => (showNewPlace = true)}>
							+ Local
						</button>
					</div>
				{/if}
			</div>
		</div>
	</div>

	<div class="card stack">
		<div class="spread">
			<h3>Participantes</h3>
			<div class="pot">
				<span class="muted">Pote</span>
				<span class="money">{formatMoney(potCents)}</span>
			</div>
		</div>

		<div class="rows">
			<div class="rhead">
				<span>Participante</span>
				<span>Buy-in</span>
				<span>Cash-out</span>
				<span class="num">Lucro</span>
				<span></span>
			</div>
			{#each rows as row, i}
				<div class="erow">
					<select bind:value={row.participant_id}>
						<option value="">Selecione…</option>
						{#each activeParticipants as p}
							<option value={p.id} disabled={usedIds.has(p.id) && Number(row.participant_id) !== p.id}>
								{p.name}
							</option>
						{/each}
					</select>
					<input inputmode="decimal" placeholder="0,00" bind:value={row.buy_in} />
					<input inputmode="decimal" placeholder="0,00" bind:value={row.cash_out} />
					<span class="num money {moneyClass(profitOf(row))}">{formatSigned(profitOf(row))}</span>
					<button type="button" class="x" onclick={() => removeRow(i)} title="Remover">✕</button>
				</div>
			{/each}
		</div>

		<div class="row addrow">
			<button type="button" class="btn btn-ghost btn-sm" onclick={addRow}>+ Linha</button>
			<div class="newp">
				<input
					placeholder="Novo participante…"
					bind:value={newParticipant}
					onkeydown={(e) => e.key === 'Enter' && (e.preventDefault(), addParticipant())}
				/>
				<button type="button" class="btn btn-ghost btn-sm" disabled={addingParticipant} onclick={addParticipant}>
					Adicionar
				</button>
			</div>
		</div>

		{#if !balanced}
			<div class="toast toast-warn">
				⚠️ O pote não fecha — diferença de {formatSigned(balanceCents)}.
			</div>
		{:else if rows.some((r) => r.participant_id)}
			<div class="toast toast-success">✓ Pote fechado certinho.</div>
		{/if}
	</div>

	<div class="row">
		<button class="btn btn-primary" disabled={saving}>{saving ? 'Salvando…' : 'Salvar noite'}</button>
		<button type="button" class="btn btn-ghost" onclick={() => oncancel()}>Cancelar</button>
	</div>
</form>

<style>
	.meta-grid {
		grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
	}
	.pot {
		display: flex;
		flex-direction: column;
		align-items: flex-end;
		font-size: 1.2rem;
	}
	.pot .muted {
		font-size: 0.75rem;
	}
	.rows {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.rhead,
	.erow {
		display: grid;
		grid-template-columns: 1.6fr 1fr 1fr 110px 32px;
		gap: 10px;
		align-items: center;
	}
	.rhead {
		font-size: 0.75rem;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: var(--text-faint);
	}
	.rhead .num,
	.erow .num {
		text-align: right;
	}
	.x {
		background: none;
		border: none;
		color: var(--text-faint);
		cursor: pointer;
		font-size: 0.9rem;
		padding: 4px;
	}
	.x:hover {
		color: var(--red);
	}
	.addrow {
		flex-wrap: wrap;
		justify-content: space-between;
	}
	.newp {
		display: flex;
		gap: 8px;
		flex: 1;
		max-width: 320px;
	}
	@media (max-width: 600px) {
		.meta-grid {
			grid-template-columns: 1fr;
		}
		.newp {
			max-width: none;
		}
		.addrow {
			flex-direction: column;
			align-items: stretch;
			gap: 10px;
		}
		.rhead {
			display: none;
		}
		.erow {
			grid-template-columns: 1fr 1fr;
			gap: 8px;
			padding: 10px;
			border: 1px solid var(--border-soft);
			border-radius: 8px;
		}
		.erow select {
			grid-column: 1 / -1;
		}
	}
</style>
