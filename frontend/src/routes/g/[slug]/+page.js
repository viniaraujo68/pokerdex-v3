import { error } from '@sveltejs/kit';
import { fetchPublic } from '$lib/publicApi.js';

/**
 * The growth surface: this is the page people paste into WhatsApp/Discord, so it has to be
 * in the HTML (title, og tags, group name, nights) before any JS runs. Overrides the root
 * layout's `ssr = false` — the rest of the app stays a client-only SPA.
 */
export const ssr = true;

/** @type {import('./$types').PageLoad} */
export async function load({ fetch, params, url }) {
	// Private groups travel as `/g/<slug>?t=<share token>`; the token has to ride along to
	// the API or the SSR pass gets a 403 the client would then contradict.
	// Reading a single search param only makes *that* param a dependency, so switching tabs
	// (`?tab=`) does not re-run this load.
	const token = url.searchParams.get('t');
	const query = token ? `?t=${encodeURIComponent(token)}` : '';
	const { data, status } = await fetchPublic(fetch, `/public/${encodeURIComponent(params.slug)}${query}`);

	/*
	 * A slug that does not exist has to answer 404, not 200-with-a-message: this page is the
	 * one crawlers actually fetch, and a soft 404 gets the dead URL indexed. `error()` hands
	 * off to the root `+error.svelte`, which localizes the not-found copy itself.
	 *
	 * Only 404 escalates. 403 (a private group reached without its `?t=` token) deliberately
	 * stays a 200 rendered by `+page.svelte`: the visitor typically *has* a link and needs the
	 * inline "ask the owner for the share link" explanation, and a 403 page would throw away
	 * the fact that the group is real. The message below never reaches the screen — the
	 * error page renders `t('error.notFoundBody')` for 404s — so it is left unlocalized for
	 * server logs.
	 *
	 * Note the status arrives server-side but the error *page* paints on the client:
	 * SvelteKit builds the error response from the root layout alone
	 * (`respond_with_error.js` → `PageNodes([nodes[0]])`), so it honours the root
	 * `+layout.js`'s `ssr = false` and not this route's `ssr = true`. The 404 header is what
	 * crawlers key on, so that's fine — just don't expect the copy in `curl` output.
	 */
	if (status === 404) error(404, 'No public group with this slug.');

	return { group: data, status };
}
