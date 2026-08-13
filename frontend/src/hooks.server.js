/**
 * Server-side `/api` routing for the pages that are rendered on the server
 * (`/g/[slug]` and `/explore` — see their `+page.js`).
 *
 * In the browser `/api/*` is same-origin: the edge proxy (prod) or the Vite dev proxy sends
 * it to FastAPI. During SSR a relative fetch resolves against the SvelteKit node server,
 * which serves no `/api` at all — so the request has to be re-pointed at the backend
 * container. Doing it in `handleFetch` keeps the loads themselves origin-agnostic: they
 * fetch `/api/...` and it works on both sides.
 */
import { dev } from '$app/environment';
import { env } from '$env/dynamic/private';

/** Compose puts the API on the internal network; `vite dev` runs it on localhost:8000. */
const FALLBACK_BASE = dev ? 'http://localhost:8000' : 'http://backend:8000';

function apiBase() {
	return (env.POKERDEX_API_INTERNAL_URL || FALLBACK_BASE).replace(/\/+$/, '');
}

/** @type {import('@sveltejs/kit').HandleFetch} */
export async function handleFetch({ request, fetch, event }) {
	const url = new URL(request.url);
	if (url.pathname === '/api' || url.pathname.startsWith('/api/')) {
		// Same method/body/path, different host. No credentials are added: the public
		// endpoints need none, and forwarding the visitor's cookies to another origin is
		// exactly the leak SvelteKit warns about in the handleFetch docs.
		const proxied = new Request(apiBase() + url.pathname + url.search, request);

		/*
		 * The one header worth adding. This request leaves the *frontend container*, so
		 * without it FastAPI sees a single source IP for every visitor and slowapi's per-IP
		 * buckets collapse into one shared allowance — the first few SSR'd views of
		 * /g/<slug> or /explore would 429 the whole world.
		 *
		 * `event.getClientAddress()` is the real visitor: adapter-node resolves it from
		 * ADDRESS_HEADER/XFF_DEPTH (set in docker-compose.yml), so the value we pass on is
		 * already the client the edge proxy vouched for, not a hop. Overwriting rather than
		 * appending is deliberate — a single-entry chain is what the backend's
		 * --forwarded-allow-ips=* + get_remote_address() reads, and it keeps a
		 * visitor-supplied X-Forwarded-For from riding through to the limiter's key.
		 *
		 * Guarded because adapter-node *throws* from getClientAddress() when ADDRESS_HEADER
		 * names a header the request doesn't carry (or XFF_DEPTH outruns the chain). Behind
		 * the edge proxy that can't happen, but a direct hit on the container — health check,
		 * `docker exec curl`, a proxy misconfigured tomorrow — would otherwise blank the
		 * scoreboard silently: publicApi.js catches everything and renders the generic
		 * failure card, so the page would come back 200 with no data at all. When there's no
		 * resolvable address the header is simply left off and that caller falls back to the
		 * container's shared bucket, which is the behaviour this whole block replaced.
		 */
		let clientAddress = '';
		try {
			clientAddress = event.getClientAddress();
		} catch {
			// No client address to be had — see above; degrade to the shared bucket.
		}
		if (clientAddress) proxied.headers.set('X-Forwarded-For', clientAddress);

		return fetch(proxied);
	}
	return fetch(request);
}
