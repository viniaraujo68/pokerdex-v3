<script>
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { get, post, put, errorMessage } from '$lib/api.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import NightForm from '$lib/components/NightForm.svelte';
	import { t } from '$lib/i18n.svelte.js';
	import { toast } from '$lib/toast.svelte.js';
	import { loginUrl } from '$lib/nav.js';

	// Guaranteed by the `[id]` route segment; `$page.params` just isn't typed per-route.
	const groupId = $derived(/** @type {string} */ ($page.params.id));
	const editId = $derived($page.url.searchParams.get('edit'));

	/** Everything the form needs to render its chips. */
	let catalogs = $state(
		/** @type {{ participants: import('$lib/types.js').Participant[], places: import('$lib/types.js').Named[] }|null} */ (null)
	);
	let night = $state(/** @type {import('$lib/types.js').Night|null} */ (null));
	/** Only for the document title — the form itself needs nothing from the group. */
	let group = $state(/** @type {import('$lib/types.js').Group|null} */ (null));
	/** Most recent night of the group — seeds place, standard buy-in and "same table". */
	let lastNight = $state(/** @type {import('$lib/types.js').Night|null} */ (null));
	let loading = $state(true);
	let saving = $state(false);
	/** An edit that failed to load must not render the form at all — hence a separate flag. */
	let loadError = $state('');

	$effect(() => {
		if (auth.ready && !auth.user) goto(loginUrl($page.url));
	});

	$effect(() => {
		if (groupId) load();
	});

	async function load() {
		loading = true;
		loadError = '';
		try {
			const [participants, places, nights, grp] = await Promise.all([
				get(`/groups/${groupId}/participants`),
				get(`/groups/${groupId}/places`),
				get(`/groups/${groupId}/nights`),
				get(`/groups/${groupId}`)
			]);
			group = grp;
			catalogs = { participants, places };
			// /nights comes back newest-first.
			lastNight = nights?.[0] ?? null;
			// The night being edited has to be in hand before the form renders — an empty form
			// here would PUT away every entry it never showed.
			if (editId) night = await get(`/groups/${groupId}/nights/${editId}`);
		} catch (e) {
			loadError = errorMessage(e);
		} finally {
			loading = false;
		}
	}

	/**
	 * @param {import('$lib/types.js').NightPayload} payload
	 * @returns {Promise<boolean>} true when saved — NightForm clears its draft on true only.
	 */
	async function save(payload) {
		saving = true;
		try {
			if (editId) await put(`/groups/${groupId}/nights/${editId}`, payload);
			else await post(`/groups/${groupId}/nights`, payload);
		} catch (e) {
			// A toast, not an inline banner: the Save button is at the bottom of a long form,
			// and a message pinned to the top of the page would land off-screen.
			toast.error(errorMessage(e));
			saving = false;
			return false;
		}
		await goto(`/groups/${groupId}?tab=nights`);
		// After the navigation on purpose — the overlay lives in the layout, so it survives.
		toast.success(t('toast.nightSaved'));
		return true;
	}

	const ready = $derived(!loading && !loadError && catalogs && (!editId || night));

	// The group name only shows up once it's loaded, so the title has a short form too.
	const title = $derived.by(() => {
		if (editId) return group ? t('title.editNightIn', { group: group.name }) : t('title.editNight');
		return group ? t('title.newNightIn', { group: group.name }) : t('title.newNight');
	});
</script>

<svelte:head>
	<title>{title}</title>
</svelte:head>

<div class="head">
	<a href={`/groups/${groupId}`} class="muted back">{t('night.backToGroup')}</a>
	<h1>{editId ? t('night.edit') : t('night.new')}</h1>
</div>

{#if loading}
	<div class="center"><div class="spinner"></div></div>
{:else if !ready}
	<div class="pd-stack">
		<div class="pd-toast pd-toast-error">
			{editId
				? t('night.loadFailed', { message: loadError || t('night.notLoaded') })
				: loadError || t('night.notLoaded')}
		</div>
		<div class="row">
			<button class="pd-btn pd-btn-primary" onclick={load}>{t('common.retry')}</button>
			<a href={`/groups/${groupId}`} class="pd-btn pd-btn-ghost">{t('group.back')}</a>
		</div>
	</div>
<!-- `catalogs` is what `ready` above is mostly about; re-testing it here is what narrows it. -->
{:else if catalogs}
	<NightForm
		{groupId}
		{catalogs}
		{night}
		{lastNight}
		editing={!!editId}
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
		min-height: 30dvh;
	}
</style>
