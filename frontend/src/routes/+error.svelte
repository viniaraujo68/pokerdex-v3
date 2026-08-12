<script>
	import { page } from '$app/stores';
	import { t } from '$lib/i18n.svelte.js';

	// 404 is the one status worth its own copy — "not found" and "we broke" call for different
	// next steps. Everything else shares the generic wording plus the status chip.
	const notFound = $derived($page.status === 404);
	const title = $derived(notFound ? t('error.notFoundTitle') : t('error.title'));
	const body = $derived(notFound ? t('error.notFoundBody') : t('error.body'));
</script>

<svelte:head>
	<title>{notFound ? t('title.notFound') : t('title.error')}</title>
</svelte:head>

<div class="card empty stack errbox">
	<span class="glyph" aria-hidden="true">♠</span>
	<span class="chip">{t('error.http', { status: $page.status })}</span>
	<h1>{title}</h1>
	<p class="muted">{body}</p>
	{#if $page.error?.message && !notFound}
		<p class="faint detail">{$page.error.message}</p>
	{/if}
	<a href="/" class="btn btn-ghost">{t('error.home')}</a>
</div>

<style>
	.errbox {
		align-items: center;
		gap: 12px;
		max-width: 520px;
		margin: 8vh auto 0;
		/* .empty ships 48px of vertical padding; the card supplies the horizontal side */
		padding: 40px 22px;
	}
	.glyph {
		display: grid;
		place-items: center;
		width: 56px;
		height: 56px;
		border-radius: 16px;
		background: linear-gradient(180deg, var(--felt-bright), var(--felt-deep));
		color: #fff;
		font-size: 1.8rem;
	}
	.errbox h1 {
		font-size: 1.5rem;
		color: var(--text);
	}
	.errbox p {
		margin: 0;
	}
	.detail {
		font-size: 0.82rem;
		overflow-wrap: anywhere;
	}
</style>
