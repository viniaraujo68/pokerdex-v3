import { fetchPublic } from '$lib/publicApi.js';

/**
 * The public directory is indexable, so the unfiltered listing is server-rendered. Searching
 * from here on is client-side (debounced, see `+page.svelte`) — the query never enters the
 * URL, so this load runs once per visit.
 */
export const ssr = true;

/** @type {import('./$types').PageLoad} */
export async function load({ fetch }) {
	const { data, status } = await fetchPublic(fetch, '/public?q=');
	return { groups: data ?? [], status };
}
