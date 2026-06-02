<script>
	/** @type {{ title: string, onclose: Function, children: any }} */
	let { title, onclose, children } = $props();

	function onKey(e) {
		if (e.key === 'Escape') onclose();
	}
</script>

<svelte:window onkeydown={onKey} />

<div
	class="backdrop"
	role="presentation"
	onclick={(e) => {
		if (e.target === e.currentTarget) onclose();
	}}
>
	<div class="modal" role="dialog" aria-modal="true" aria-label={title}>
		<div class="mhead">
			<h2>{title}</h2>
			<button class="close" aria-label="Fechar" onclick={() => onclose()}>✕</button>
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
		display: grid;
		place-items: center;
		padding: 20px;
		animation: fade 0.15s ease;
	}
	.modal {
		width: 100%;
		max-width: 460px;
		background: linear-gradient(180deg, var(--surface), var(--bg-elev));
		border: 1px solid var(--border);
		border-radius: 16px;
		box-shadow: var(--shadow-lg);
		animation: pop 0.18s cubic-bezier(0.2, 0.9, 0.4, 1.1);
		overflow: hidden;
	}
	.mhead {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 18px 22px;
		border-bottom: 1px solid var(--border-soft);
	}
	.mhead h2 {
		font-size: 1.2rem;
	}
	.close {
		background: none;
		border: none;
		color: var(--text-faint);
		font-size: 1rem;
		cursor: pointer;
		padding: 4px 8px;
		border-radius: 8px;
	}
	.close:hover {
		color: var(--text);
		background: var(--surface-2);
	}
	.mbody {
		padding: 22px;
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
</style>
