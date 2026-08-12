<script>
	import { tick } from 'svelte';

	/**
	 * The tab strip shared by the owner's group page and the public scoreboard: a real
	 * `tablist` (roving tabindex + arrow keys) that scrolls horizontally when the labels
	 * don't fit, with a fade telling you there's more to the right.
	 *
	 * The selection itself is the parent's business — both callers keep it in the URL, so
	 * `active` comes in as a prop and `onChange` navigates.
	 *
	 * @type {{
	 *   tabs: Array<{ id: string, label: string }>,
	 *   active: string,
	 *   onChange: (id: string) => void,
	 *   label: string,
	 *   controls: string,
	 *   idPrefix?: string,
	 *   center?: boolean
	 * }}
	 */
	let { tabs, active, onChange, label, controls, idPrefix = 'tab', center = false } = $props();

	/** @param {string} id */
	const tabId = (id) => `${idPrefix}-${id}`;

	/** @param {KeyboardEvent} e */
	function onKey(e) {
		const ids = tabs.map((x) => x.id);
		const from = ids.indexOf(active);
		let to = null;
		if (e.key === 'ArrowRight') to = (from + 1) % ids.length;
		else if (e.key === 'ArrowLeft') to = (from - 1 + ids.length) % ids.length;
		else if (e.key === 'Home') to = 0;
		else if (e.key === 'End') to = ids.length - 1;
		if (to === null) return;
		e.preventDefault();
		const id = ids[to];
		onChange(id);
		// The callers navigate, and a navigation keeps focus where it was — so walk focus
		// over to the tab that is now selected.
		tick().then(() => document.getElementById(tabId(id))?.focus());
	}

	/** @type {HTMLElement|undefined} */
	let tabsEl = $state();
	/** True while there are tabs scrolled off the right edge — drives the fade mask. */
	let fadeRight = $state(false);

	function updateFade() {
		if (!tabsEl) return;
		fadeRight = tabsEl.scrollWidth - tabsEl.clientWidth - tabsEl.scrollLeft > 4;
	}

	$effect(() => {
		// re-measure when the labels change (locale switch) or the element first appears
		tabs;
		tabsEl;
		updateFade();
	});
</script>

<!-- The bar is the fade host; the inner strip is what actually scrolls. -->
<div class="tabsbar" class:fade={fadeRight}>
	<div
		class="tabs"
		class:center
		role="tablist"
		aria-label={label}
		bind:this={tabsEl}
		onscroll={updateFade}
	>
		{#each tabs as item (item.id)}
			<button
				class="tab"
				class:active={active === item.id}
				role="tab"
				id={tabId(item.id)}
				aria-selected={active === item.id}
				aria-controls={controls}
				tabindex={active === item.id ? 0 : -1}
				onclick={() => onChange(item.id)}
				onkeydown={onKey}
			>
				{item.label}
			</button>
		{/each}
	</div>
</div>

<style>
	.tabsbar {
		position: relative;
		margin-bottom: 24px;
	}
	.tabs {
		display: flex;
		gap: 4px;
		border-bottom: 1px solid var(--border);
		overflow-x: auto;
		-webkit-overflow-scrolling: touch;
		scrollbar-width: none; /* Firefox */
		-ms-overflow-style: none;
	}
	/* centred while they fit, scrollable (from the left) once they don't — the `safe`
	   keyword is what keeps the first tab reachable; plain `center` is the fallback */
	.tabs.center {
		justify-content: center;
		justify-content: safe center;
	}
	.tabs::-webkit-scrollbar {
		display: none;
	}
	/* Right-edge fade: the only hint that a 4th tab exists at 390px. A mask, not a gradient
	   overlay — the page background is itself a gradient, so a painted "fade to --bg" would
	   show as a smudge. Applied only while there's something scrolled off. */
	.tabsbar.fade .tabs {
		-webkit-mask-image: linear-gradient(to right, #000 calc(100% - 44px), transparent);
		mask-image: linear-gradient(to right, #000 calc(100% - 44px), transparent);
	}
	.tab {
		background: none;
		border: none;
		border-bottom: 2px solid transparent;
		color: var(--text-muted);
		min-height: 44px;
		padding: 10px 16px;
		font-family: inherit;
		font-size: 0.95rem;
		font-weight: 600;
		cursor: pointer;
		white-space: nowrap;
		flex: 0 0 auto;
	}
	.tab:focus-visible {
		/* inside a horizontal scroller an outset ring gets clipped — tuck it in */
		outline-offset: -2px;
	}
	.tab.active {
		color: var(--felt-bright);
		border-bottom-color: var(--felt-bright);
	}
	.tab:hover {
		color: var(--text);
	}
</style>
