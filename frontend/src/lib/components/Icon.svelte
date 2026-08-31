<script>
	/**
	 * @typedef {'spade'|'place'|'players'|'nights'|'pot'|'globe'|'lock'
	 *   |'search'|'warning'|'edit'|'restore'|'close'|'chevron'} IconName
	 */

	/** @type {{ name: IconName, class?: string, label?: string }} */
	let { name, class: className = 'size-[1em]', label } = $props();

	const filled = $derived(name === 'spade');
</script>

<svg
	class={className}
	viewBox="0 0 24 24"
	fill={filled ? 'currentColor' : 'none'}
	stroke={filled ? 'none' : 'currentColor'}
	stroke-width="2"
	stroke-linecap="round"
	stroke-linejoin="round"
	role={label ? 'img' : undefined}
	aria-label={label}
	aria-hidden={label ? undefined : 'true'}
>
	{#if name === 'spade'}
		<path
			d="M12 2.2c-.4 0-1.7 1.1-3.9 3.3C5.4 8.3 4 10.9 4 13c0 1.5.5 2.7 1.4 3.6.9.9 2 1.4 3.3 1.4 1 0 1.9-.3 2.6-.9.1 2.4-.9 4.1-3 5.2h7.4c-2.1-1.1-3.1-2.8-3-5.2.7.6 1.6.9 2.6.9 1.3 0 2.4-.5 3.3-1.4.9-.9 1.4-2.1 1.4-3.6 0-2.1-1.4-4.7-4.1-7.5C13.7 3.3 12.4 2.2 12 2.2Z"
		/>
	{:else if name === 'place'}
		<path d="M12 21.2c4.4-4.3 6.6-7.7 6.6-10.3a6.6 6.6 0 1 0-13.2 0c0 2.6 2.2 6 6.6 10.3Z" />
		<circle cx="12" cy="10.4" r="2.4" />
	{:else if name === 'players'}
		<circle cx="8.8" cy="8" r="3.2" />
		<circle cx="17.4" cy="8.8" r="2.4" />
		<path d="M2.8 19.8a6 6 0 0 1 12 0" />
		<path d="M17 19.8a5.4 5.4 0 0 1 4.2-5.3" />
	{:else if name === 'nights'}
		<rect x="3.4" y="5.2" width="17.2" height="15.4" rx="2.6" />
		<path d="M3.4 10.2h17.2M8 2.8v3.2M16 2.8v3.2" />
	{:else if name === 'pot'}
		<rect x="2.4" y="6" width="19.2" height="12" rx="2.6" />
		<circle cx="12" cy="12" r="2.7" />
		<path d="M6.2 9.6v4.8M17.8 9.6v4.8" />
	{:else if name === 'globe'}
		<circle cx="12" cy="12" r="8.8" />
		<path d="M3.2 12h17.6" />
		<path d="M12 3.2c2.5 2.4 3.8 5.4 3.8 8.8s-1.3 6.4-3.8 8.8c-2.5-2.4-3.8-5.4-3.8-8.8S9.5 5.6 12 3.2Z" />
	{:else if name === 'lock'}
		<rect x="4.4" y="10.4" width="15.2" height="10.2" rx="2.6" />
		<path d="M8 10.4V7.6a4 4 0 0 1 8 0v2.8" />
	{:else if name === 'search'}
		<circle cx="10.6" cy="10.6" r="6.2" />
		<path d="m15.2 15.2 5 5" />
	{:else if name === 'warning'}
		<path d="M10.3 3.9a2 2 0 0 1 3.4 0l7.4 13a2 2 0 0 1-1.7 3H4.6a2 2 0 0 1-1.7-3l7.4-13Z" />
		<path d="M12 9.4v4.2M12 17.2h.01" />
	{:else if name === 'edit'}
		<path d="M12.5 20.5H21" />
		<path d="M16.6 3.6a2.2 2.2 0 0 1 3.1 3.1L7.4 19 3 20.2l1.2-4.4L16.6 3.6Z" />
	{:else if name === 'restore'}
		<path d="M3.2 12a8.8 8.8 0 1 0 8.8-8.8 9.5 9.5 0 0 0-6.6 2.7L3.2 8" />
		<path d="M3.2 3.2v4.9h4.9" />
	{:else if name === 'close'}
		<path d="m6.4 6.4 11.2 11.2M17.6 6.4 6.4 17.6" />
	{:else if name === 'chevron'}
		<path d="m5.5 9.5 6.5 6 6.5-6" />
	{/if}
</svg>
