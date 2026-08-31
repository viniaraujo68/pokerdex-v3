<script>
	/** @type {{ class?: string, detail?: string, label?: string }} */
	let { class: className = 'size-[1em]', detail = 'var(--color-primary)', label } = $props();
</script>

<svg
	class={className}
	viewBox="5.6 2.4 20.8 27.2"
	fill="currentColor"
	role={label ? 'img' : undefined}
	aria-label={label}
	aria-hidden={label ? undefined : 'true'}
>
	<rect x="5.6" y="2.4" width="20.8" height="27.2" rx="3.4" />
	<circle cx="9.9" cy="6.1" r="2.4" fill={detail} />
	<circle cx="14.8" cy="5.9" r="0.75" fill={detail} />
	<circle cx="17.3" cy="5.9" r="0.75" fill={detail} />
	<circle cx="19.8" cy="5.9" r="0.75" fill={detail} />
	<rect x="8.2" y="9.6" width="15.6" height="13" rx="1.7" fill={detail} />
	<circle cx="16" cy="16.1" r="5.3" />
	<circle
		cx="16"
		cy="16.1"
		r="4.1"
		fill="none"
		stroke={detail}
		stroke-width="1.5"
		stroke-dasharray="1.7 1.52"
		stroke-linecap="butt"
	/>
	<circle cx="16" cy="16.1" r="1.5" fill={detail} />
	<rect x="8.6" y="24.4" width="5.6" height="2.4" rx="1.2" fill={detail} />
	<circle cx="20.4" cy="25.6" r="1.9" fill={detail} />
</svg>
