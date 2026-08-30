<script>
	import { get, post, patch, del, errorMessage } from '$lib/http.js';
	import { goto } from '$app/navigation';
	import Modal from './Modal.svelte';
	import { t } from '$lib/i18n.svelte.js';
	import { toast } from '@viniaraujo68/plinth/toast';
	import { unbalancedBadgeEnabled, setUnbalancedBadge } from '$lib/prefs.svelte.js';

	/**
	 * `onchange` with a group means "this is the new group"; with no argument it means
	 * "something under the group moved, refetch" — see the parent's `onGroupChange`.
	 * @type {{
	 *   group: import('$lib/types.js').Group,
	 *   onchange: (updated?: import('$lib/types.js').Group) => void
	 * }}
	 */
	let { group, onchange } = $props();

	let participants = $state(/** @type {import('$lib/types.js').Participant[]} */ ([]));
	/** The catalogs, keyed by the API path segment that owns them. */
	let lists = $state({ places: /** @type {import('$lib/types.js').Named[]} */ ([]) });
	/** Only the initial load gets an inline message — with no catalog, empty cards would lie. */
	let loadError = $state('');

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
			toast.error(errorMessage(e));
			deleting = false;
			showDelete = false;
		}
	}

	// group settings form (a draft: nothing here is live until "Salvar alterações")
	// Reading `group` once is the point: these are the form's *initial* values. Following the
	// prop would overwrite whatever the user is typing the moment the parent refetches.
	// svelte-ignore state_referenced_locally
	let name = $state(group.name);
	// svelte-ignore state_referenced_locally
	let description = $state(group.description);
	// svelte-ignore state_referenced_locally
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
			loadError = '';
		} catch (e) {
			loadError = errorMessage(e);
		}
	}

	async function saveGroup() {
		savingGroup = true;
		try {
			const updated = await patch(`/groups/${group.id}`, { name, description, visibility });
			onchange(updated);
			toast.success(t('toast.settingsSaved'));
		} catch (e) {
			toast.error(errorMessage(e));
		} finally {
			savingGroup = false;
		}
	}

	// ---------- share link ----------
	// Everything below reads the SAVED group, never the form draft: a link built from an
	// unsaved `visibility` would 403 the moment someone opened it.
	const savedPublic = $derived(group.visibility === 'public');
	const hasToken = $derived(!!group.share_token);
	/** A private group with no token has no shareable URL at all — don't fake one. */
	const linkReady = $derived(savedPublic || hasToken);
	const visibilityDirty = $derived(visibility !== group.visibility);

	const shareUrl = $derived(
		typeof window !== 'undefined' && linkReady
			? `${window.location.origin}/g/${group.slug}` +
					(savedPublic ? '' : `?t=${group.share_token}`)
			: ''
	);

	let rotating = $state(false);

	/** Also the "generate the first link" action: the endpoint mints a token either way. */
	async function rotateToken() {
		rotating = true;
		const first = !hasToken;
		try {
			const updated = await post(`/groups/${group.id}/rotate-share-token`);
			onchange(updated);
			toast.success(first ? t('toast.linkGenerated') : t('toast.tokenRotated'));
		} catch (e) {
			toast.error(errorMessage(e));
		} finally {
			rotating = false;
		}
	}

	async function copyShare() {
		if (!shareUrl) return;
		try {
			// No clipboard API on http:// origins or older WebViews — say so instead of no-op'ing.
			if (!navigator.clipboard) throw new Error('clipboard unavailable');
			await navigator.clipboard.writeText(shareUrl);
			toast.success(t('toast.linkCopied'));
		} catch {
			toast.error(t('toast.copyFailed'));
		}
	}

	// ---------- per-group options ----------
	const showUnbalanced = $derived(unbalancedBadgeEnabled(group.id));

	// ---------- catalog handlers (places only) ----------
	/** The `kind` the handlers below are keyed by — one catalog today, hence the single member. */
	/** @typedef {'places'} CatalogKind */

	let drafts = $state({ places: '', participant: '' });

	/** @param {CatalogKind} kind */
	async function addItem(kind) {
		const value = drafts[kind].trim();
		if (!value) return;
		try {
			const item = await post(`/groups/${group.id}/${kind}`, { name: value });
			lists[kind] = [...lists[kind], item].sort((a, b) => a.name.localeCompare(b.name));
			drafts[kind] = '';
			toast.success(t('toast.placeAdded', { name: item.name }));
		} catch (e) {
			toast.error(errorMessage(e));
		}
	}

	/** @param {CatalogKind} kind @param {number} id */
	async function removeItem(kind, id) {
		try {
			await del(`/groups/${group.id}/${kind}/${id}`);
			lists[kind] = lists[kind].filter((x) => x.id !== id);
		} catch (e) {
			toast.error(errorMessage(e));
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
			toast.success(t('toast.participantAdded', { name: p.name }));
		} catch (e) {
			toast.error(errorMessage(e));
		}
	}

	/** @param {import('$lib/types.js').Participant} p */
	async function removeParticipant(p) {
		try {
			await del(`/groups/${group.id}/participants/${p.id}`);
			await loadAll();
			onchange();
		} catch (e) {
			toast.error(errorMessage(e));
		}
	}

	/**
	 * Undo of the soft delete above: PATCH takes a partial body, so no name to echo back.
	 * @param {import('$lib/types.js').Participant} p
	 */
	async function reactivateParticipant(p) {
		try {
			const updated = await patch(`/groups/${group.id}/participants/${p.id}`, { active: true });
			participants = participants.map((x) => (x.id === updated.id ? updated : x));
			onchange();
			toast.success(t('toast.participantReactivated', { name: updated.name }));
		} catch (e) {
			toast.error(errorMessage(e));
		}
	}

	const hasInactive = $derived(participants.some((p) => !p.active));
	/** @type {{ kind: CatalogKind, title: string }[]} */
	const catalogMeta = $derived([{ kind: 'places', title: t('settings.places') }]);
</script>

{#if loadError}<div class="pd-alert pd-alert-error">{loadError}</div>{/if}

<div class="settings pd-stack">
	<!-- Group basics -->
	<div class="pd-card pd-stack">
		<h3>{t('settings.group')}</h3>
		<div class="field">
			<label for="s-name">{t('common.name')}</label>
			<input id="s-name" bind:value={name} />
		</div>
		<div class="field">
			<label for="s-desc">{t('common.description')}</label>
			<input id="s-desc" bind:value={description} />
		</div>
		<div class="field">
			<label for="s-vis">{t('group.visibility')}</label>
			<select id="s-vis" bind:value={visibility}>
				<option value="public">{t('group.public')}</option>
				<option value="private">{t('group.private')}</option>
			</select>
		</div>
		<div>
			<button class="pd-btn pd-btn-primary pd-btn-sm" disabled={savingGroup} onclick={saveGroup}>
				{savingGroup ? t('common.saving') : t('settings.saveChanges')}
			</button>
		</div>
	</div>

	<!-- Share link — always the saved state, never the draft above -->
	<div class="pd-card pd-stack">
		<h3>{t('settings.publicLink')}</h3>
		{#if savedPublic}
			<p class="muted small">{t('settings.publicLinkHint')}</p>
		{:else if hasToken}
			<p class="muted small">{t('settings.privateLinkHint')}</p>
		{:else}
			<p class="muted small">{t('settings.noLinkYet')}</p>
		{/if}

		{#if visibilityDirty}
			<p class="pd-alert pd-alert-warn small">{t('settings.linkUnsavedHint')}</p>
		{/if}

		{#if linkReady}
			<div class="share">
				<input readonly value={shareUrl} aria-label={t('settings.publicLink')} />
				<button class="pd-btn pd-btn-ghost pd-btn-sm" onclick={copyShare}>{t('common.copy')}</button>
			</div>
		{/if}

		{#if !savedPublic}
			<div>
				<button class="pd-btn pd-btn-ghost pd-btn-sm" disabled={rotating} onclick={rotateToken}>
					{hasToken ? t('settings.rotateToken') : t('settings.generateLink')}
				</button>
			</div>
		{/if}
	</div>

	<!-- Per-group options (device-local) -->
	<div class="pd-card pd-stack">
		<h3>{t('settings.options')}</h3>
		<label class="opt">
			<input
				type="checkbox"
				checked={showUnbalanced}
				onchange={(e) => setUnbalancedBadge(group.id, e.currentTarget.checked)}
			/>
			<span>
				<span class="opt-t">{t('settings.unbalancedOption')}</span>
				<span class="faint opt-d">{t('settings.unbalancedOptionHint')}</span>
			</span>
		</label>
	</div>

	<!-- Participants -->
	<div class="pd-card pd-stack">
		<h3>{t('common.players')}</h3>
		<div class="adder">
			<input
				placeholder={t('settings.playerPlaceholder')}
				bind:value={drafts.participant}
				onkeydown={(e) => e.key === 'Enter' && (e.preventDefault(), addParticipant())}
			/>
			<button class="pd-btn pd-btn-ghost pd-btn-sm" onclick={addParticipant}>{t('common.add')}</button>
		</div>
		<div class="tags">
			{#each participants as p (p.id)}
				<span class="chip" class:inactive={!p.active}>
					{p.name}
					{#if p.active}
						<button
							class="chip-x"
							aria-label={t('common.remove')}
							title={t('common.remove')}
							onclick={() => removeParticipant(p)}>✕</button
						>
					{:else}
						<button
							class="chip-x revive"
							aria-label={t('settings.reactivate', { name: p.name })}
							title={t('settings.reactivate', { name: p.name })}
							onclick={() => reactivateParticipant(p)}>↺</button
						>
					{/if}
				</span>
			{/each}
			{#if participants.length === 0}<span class="faint small">{t('settings.noPlayers')}</span>{/if}
		</div>
		{#if hasInactive}
			<p class="faint small">{t('settings.inactiveHint')}</p>
		{/if}
	</div>

	<!-- Catalogs -->
	<div class="catalogs pd-grid">
		{#each catalogMeta as meta (meta.kind)}
			<div class="pd-card pd-stack">
				<h3>{meta.title}</h3>
				<div class="adder">
					<input
						placeholder={t('settings.addPlaceholder')}
						bind:value={drafts[meta.kind]}
						onkeydown={(e) => e.key === 'Enter' && (e.preventDefault(), addItem(meta.kind))}
					/>
					<button class="pd-btn pd-btn-ghost pd-btn-sm" onclick={() => addItem(meta.kind)}>+</button>
				</div>
				<div class="tags">
					{#each lists[meta.kind] as item (item.id)}
						<span class="chip">
							{item.name}
							<button
								class="chip-x"
								aria-label={t('common.remove')}
								title={t('common.remove')}
								onclick={() => removeItem(meta.kind, item.id)}>✕</button
							>
						</span>
					{/each}
					{#if lists[meta.kind].length === 0}<span class="faint small">{t('common.emptyList')}</span>{/if}
				</div>
			</div>
		{/each}
	</div>

	<!-- Danger zone -->
	<div class="pd-card pd-stack danger">
		<h3>{t('settings.dangerZone')}</h3>
		<p class="muted small">
			{t('settings.deleteWarningPre')} <strong>{t('settings.deleteWarningStrong')}</strong>
			{t('settings.deleteWarningPost')}
		</p>
		<div>
			<button class="pd-btn pd-btn-danger pd-btn-sm" onclick={() => { showDelete = true; confirmName = ''; }}>
				{t('settings.deleteGroup')}
			</button>
		</div>
	</div>
</div>

{#if showDelete}
	<Modal title={t('settings.deleteGroup')} onclose={() => (showDelete = false)}>
		<div class="pd-stack">
			<p class="muted">
				{t('settings.deleteConfirmPre')} <strong>{group.name}</strong>
				{t('settings.deleteConfirmPost')}
			</p>
			<input
				placeholder={group.name}
				bind:value={confirmName}
				onkeydown={(e) => e.key === 'Enter' && confirmName === group.name && deleteGroup()}
			/>
			<div class="row mactions">
				<button class="pd-btn pd-btn-ghost" onclick={() => (showDelete = false)}>{t('common.cancel')}</button>
				<button
					class="pd-btn pd-btn-danger"
					disabled={confirmName !== group.name || deleting}
					onclick={deleteGroup}
				>
					{deleting ? t('settings.deleting') : t('settings.deletePermanently')}
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
	/* The whole label toggles, so the row *is* the hit area — negative margin keeps the extra
	   padding from re-spacing the card. */
	.opt {
		display: flex;
		align-items: flex-start;
		gap: 10px;
		cursor: pointer;
		padding: 8px;
		margin: -8px;
		border-radius: var(--radius-sm);
	}
	.opt:hover {
		background: rgba(124, 58, 237, 0.07);
	}
	.opt input {
		width: 22px;
		height: 22px;
		margin: 0;
		flex: 0 0 auto;
		accent-color: var(--felt-bright);
	}
	.opt-t {
		display: block;
		font-weight: 600;
		font-size: 0.92rem;
	}
	.opt-d {
		display: block;
		font-size: 0.8rem;
		line-height: 1.35;
	}
	.tags {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}
	/* The ✕/↺ used to be a ~13px target. Rather than float a 44px overlay that would spill into
	   the neighbouring chip (the gap is only 8px), the chip grows to 44px tall and the button
	   fills it: a full-height target with no overlap. */
	.tags .chip {
		gap: 2px;
		min-height: 44px;
		/* no right padding: the button itself is the right edge, so it can be a full 44px */
		padding: 0 0 0 12px;
	}
	.chip.inactive {
		opacity: 0.5;
	}
	.chip-x {
		display: inline-grid;
		place-items: center;
		min-width: 44px;
		min-height: 44px;
		background: none;
		border: none;
		border-radius: 999px;
		color: var(--text-faint);
		cursor: pointer;
		padding: 0;
		font-size: 0.85rem;
		line-height: 1;
	}
	.chip-x:hover {
		color: var(--text);
		background: rgba(255, 255, 255, 0.06);
	}
	.revive {
		color: var(--felt-bright);
		font-size: 1rem;
	}
	.revive:hover {
		color: var(--green-pos);
	}
	.catalogs {
		grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
	}
</style>
