<script>
	import { onMount, tick } from 'svelte';
	import { t } from '$lib/i18n.svelte.js';

	/** @type {{ title: string, onclose: Function, children: any }} */
	let { title, onclose, children } = $props();

	/** @type {HTMLElement} */
	let dialogEl;
	/** @type {HTMLButtonElement} */
	let closeEl;

	const FOCUSABLE = [
		'a[href]',
		'button:not([disabled])',
		'input:not([disabled]):not([type="hidden"])',
		'select:not([disabled])',
		'textarea:not([disabled])',
		'[tabindex]:not([tabindex="-1"])'
	].join(',');

	/** Tab order of what's actually on screen — a hidden control would swallow the focus. */
	function focusables() {
		if (!dialogEl) return [];
		return /** @type {HTMLElement[]} */ ([...dialogEl.querySelectorAll(FOCUSABLE)]).filter(
			(el) => el.offsetWidth > 0 || el.offsetHeight > 0
		);
	}

	onMount(() => {
		// Who opened us, so Escape/✕ hands the focus back instead of dropping it on <body>.
		const opener = /** @type {HTMLElement|null} */ (document.activeElement);

		// Body scroll lock. Stored inline instead of a class so we can restore exactly what was there.
		const body = document.body;
		const prevOverflow = body.style.overflow;
		body.style.overflow = 'hidden';

		// `autofocus` inside the modal wins; otherwise the first real control, and the ✕ only as a
		// last resort — landing on "close" is a poor opening move.
		tick().then(() => {
			const auto = /** @type {HTMLElement|null} */ (dialogEl?.querySelector('[autofocus]'));
			const target = auto ?? focusables().find((el) => el !== closeEl) ?? closeEl ?? dialogEl;
			target?.focus();
		});

		return () => {
			body.style.overflow = prevOverflow;
			// Only if it's still in the document — a modal that navigated away has no opener left.
			if (opener?.isConnected) opener.focus?.();
		};
	});

	/** @param {KeyboardEvent} e */
	function onKeydown(e) {
		// Mid-IME-composition Escape/Enter belongs to the input method, not to us.
		if (e.isComposing || e.keyCode === 229) return;

		if (e.key === 'Escape') {
			e.stopPropagation();
			onclose();
			return;
		}

		if (e.key !== 'Tab') return;

		const items = focusables();
		if (items.length === 0) {
			// Nothing to cycle through: keep the focus on the dialog itself.
			e.preventDefault();
			dialogEl?.focus();
			return;
		}

		const first = items[0];
		const last = items[items.length - 1];
		const active = /** @type {HTMLElement} */ (document.activeElement);

		if (e.shiftKey && (active === first || !dialogEl.contains(active))) {
			e.preventDefault();
			last.focus();
		} else if (!e.shiftKey && (active === last || !dialogEl.contains(active))) {
			e.preventDefault();
			first.focus();
		}
	}
</script>

<!-- The keydown lives here (not on window) so Escape only closes for events raised inside. -->
<div
	class="backdrop"
	role="presentation"
	onkeydown={onKeydown}
	onclick={(e) => {
		if (e.target === e.currentTarget) onclose();
	}}
>
	<div
		class="modal"
		role="dialog"
		aria-modal="true"
		aria-label={title}
		tabindex="-1"
		bind:this={dialogEl}
	>
		<div class="mhead">
			<h2>{title}</h2>
			<button
				class="close"
				aria-label={t('common.close')}
				bind:this={closeEl}
				onclick={() => onclose()}>✕</button
			>
		</div>
		<div class="mbody">
			{@render children()}
		</div>
	</div>
</div>

<style>
	.backdrop {
		position: fixed;
		inset: 0;
		z-index: 100;
		background: rgba(6, 4, 12, 0.66);
		backdrop-filter: blur(4px);
		/* flex + `margin:auto` on the child centres without clipping when the dialog is tall */
		display: flex;
		padding: 20px;
		overflow: auto;
		overscroll-behavior: contain;
		animation: fade 0.15s ease;
	}
	.modal {
		margin: auto;
		width: 100%;
		max-width: 460px;
		/* dvh, not vh: the visible viewport shrinks when the on-screen keyboard opens */
		max-height: calc(100dvh - 40px);
		display: flex;
		flex-direction: column;
		background: linear-gradient(180deg, var(--surface), var(--bg-elev));
		border: 1px solid var(--border);
		border-radius: 16px;
		box-shadow: var(--shadow-lg);
		animation: pop 0.18s cubic-bezier(0.2, 0.9, 0.4, 1.1);
		overflow: hidden;
	}
	.modal:focus {
		outline: none;
	}
	.mhead {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
		padding: 18px 22px;
		border-bottom: 1px solid var(--border-soft);
		flex: 0 0 auto;
	}
	.mhead h2 {
		font-size: 1.2rem;
	}
	.close {
		display: grid;
		place-items: center;
		flex: 0 0 auto;
		min-width: 44px;
		min-height: 44px;
		background: none;
		border: none;
		color: var(--text-faint);
		font-size: 1rem;
		cursor: pointer;
		padding: 0;
		/* negative margin so the 44px target eats into the header padding instead of growing it */
		margin: -12px -14px -12px 0;
		border-radius: 8px;
		line-height: 1;
	}
	.close:hover {
		color: var(--text);
		background: var(--surface-2);
	}
	.mbody {
		padding: 22px;
		/* the pot of gold at the bottom of a long form must stay reachable */
		overflow-y: auto;
		-webkit-overflow-scrolling: touch;
		overscroll-behavior: contain;
		flex: 1 1 auto;
		min-height: 0;
	}
	@keyframes fade {
		from {
			opacity: 0;
		}
	}
	@keyframes pop {
		from {
			opacity: 0;
			transform: translateY(8px) scale(0.98);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.backdrop,
		.modal {
			animation: none;
		}
	}
</style>
