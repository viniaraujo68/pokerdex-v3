<script>
	import { items, dismiss, layout } from '$lib/toast.svelte.js';
	import { t } from '$lib/i18n.svelte.js';

	/** Mounted once, from `+layout.svelte`. Everything else just calls `toast.*`. */
</script>

<!-- polite live region: announced without interrupting, and empty until something fires -->
<div
	class="toasts"
	role="status"
	aria-live="polite"
	style={`--toast-gap:${layout.bottomGap}px`}
>
	{#each items as item (item.id)}
		<div class="pd-toast pd-toast-{item.kind} item">
			<span class="msg">{item.message}</span>
			<button
				class="x"
				aria-label={t('common.close')}
				title={t('common.close')}
				onclick={() => dismiss(item.id)}
			>
				✕
			</button>
		</div>
	{/each}
</div>

<style>
	.toasts {
		position: fixed;
		z-index: 80; /* above the night form's sticky bar (20) and the header (50) */
		left: 12px;
		right: 12px;
		/* max(), not a sum: a reserved gap comes from measuring an element that already
		   includes the safe-area padding, so adding both would double-count it. */
		bottom: calc(12px + max(var(--toast-gap, 0px), env(safe-area-inset-bottom)));
		display: flex;
		flex-direction: column;
		gap: 8px;
		pointer-events: none; /* the empty region must never eat taps */
	}
	.item {
		pointer-events: auto;
		display: flex;
		align-items: flex-start;
		gap: 10px;
		box-shadow: var(--shadow);
		animation: toast-in 0.18s ease-out;
		/* own stacking context for the opaque base below */
		position: relative;
		isolation: isolate;
	}
	/* The shared `.pd-toast` palette is a ~10% tint, meant for use inside a card. Floating over
	   the page it would let buttons and text bleed through, so slide an opaque layer under it
	   instead of hardcoding a blended colour per kind. */
	.item::before {
		content: '';
		position: absolute;
		inset: 0;
		z-index: -1;
		border-radius: inherit;
		background: var(--bg-elev);
	}
	.msg {
		flex: 1;
		min-width: 0;
		overflow-wrap: anywhere;
	}
	.x {
		flex: 0 0 auto;
		display: grid;
		place-items: center;
		background: none;
		border: none;
		border-radius: var(--radius-sm);
		color: inherit;
		opacity: 0.65;
		cursor: pointer;
		font-size: 0.8rem;
		line-height: 1;
		/* 44×44 target; the negative margin eats back into the toast's own padding so the row
		   keeps its height instead of growing around the button. */
		min-width: 44px;
		min-height: 44px;
		margin: -12px -16px -12px 0;
	}
	.x:hover {
		opacity: 1;
	}

	@media (min-width: 700px) {
		.toasts {
			left: auto;
			right: 20px;
			bottom: auto;
			top: 76px; /* clear of the 64px sticky header */
			width: min(360px, calc(100vw - 40px));
		}
		.item {
			animation-name: toast-in-right;
		}
	}

	@keyframes toast-in {
		from {
			opacity: 0;
			transform: translateY(10px);
		}
	}
	@keyframes toast-in-right {
		from {
			opacity: 0;
			transform: translateX(14px);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.item {
			animation: none;
		}
	}
</style>
