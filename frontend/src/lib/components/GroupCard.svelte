<script>
	import { t } from '$lib/i18n.svelte.js';

	/**
	 * One group in a card grid — the home dashboard and /explore render the same card, so it
	 * lives here. `visibility` is a prop because the public directory doesn't ship the field
	 * (everything it returns is public by definition) while the dashboard does.
	 * @type {{
	 *   group: { name: string, description?: string, night_count: number, participant_count: number },
	 *   href: string,
	 *   visibility?: 'public'|'private'
	 * }}
	 */
	let { group, href, visibility = 'public' } = $props();
</script>

<a {href} class="card group">
	<div class="spread">
		<h3>{group.name}</h3>
		<span class="chip {visibility === 'public' ? 'chip-felt' : ''}">
			{visibility === 'public' ? t('group.chipPublic') : t('group.chipPrivate')}
		</span>
	</div>
	{#if group.description}<p class="muted desc">{group.description}</p>{/if}
	<div class="row stats">
		<span class="chip">🃏 {t('group.nightCount', { count: group.night_count })}</span>
		<span class="chip">👥 {t('group.playerCount', { count: group.participant_count })}</span>
	</div>
</a>

<style>
	.group {
		display: flex;
		flex-direction: column;
		gap: 12px;
		transition:
			transform 0.12s ease,
			border-color 0.15s ease;
	}
	.group:hover {
		transform: translateY(-3px);
		border-color: var(--felt);
	}
	@media (prefers-reduced-motion: reduce) {
		/* the border colour still answers the hover; the lift is the part that has to go */
		.group:hover {
			transform: none;
		}
	}
	.desc {
		font-size: 0.9rem;
		margin: 0;
	}
	/* pushed to the bottom so the chips line up across cards of different description length */
	.stats {
		flex-wrap: wrap;
		margin-top: auto;
	}
</style>
