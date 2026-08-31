<script>
	import { t } from '$lib/i18n.svelte.js';
	import Icon from './Icon.svelte';

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

<a {href} class="group card flex flex-col gap-3 bg-base-100 p-5">
	<div class="flex items-center justify-between gap-3">
		<h3 class="font-semibold">{group.name}</h3>
		<span class="badge badge-soft {visibility === 'public' ? 'badge-primary' : ''}">
			{visibility === 'public' ? t('group.chipPublic') : t('group.chipPrivate')}
		</span>
	</div>
	{#if group.description}
		<p class="text-sm text-base-content/80">{group.description}</p>
	{/if}
	<div class="mt-auto flex flex-wrap items-center gap-2">
		<span class="badge badge-soft">
			<Icon name="nights" />
			{t('group.nightCount', { count: group.night_count })}
		</span>
		<span class="badge badge-soft">
			<Icon name="players" />
			{t('group.playerCount', { count: group.participant_count })}
		</span>
	</div>
</a>

<style>
	.group {
		transition:
			transform 0.12s ease,
			border-color 0.15s ease;
	}
	.group:hover {
		transform: translateY(-3px);
		border-color: color-mix(in oklch, var(--color-primary) 55%, transparent);
	}
	@media (prefers-reduced-motion: reduce) {
		/* the border colour still answers the hover; the lift is the part that has to go */
		.group:hover {
			transform: none;
		}
	}
</style>
