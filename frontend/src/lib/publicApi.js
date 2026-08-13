/**
 * Fetch helper for the *universal* loads of the public pages (`/g/[slug]`, `/explore`).
 *
 * Separate from `$lib/api.js` on purpose:
 *  - it takes the load event's `fetch`, so SSR responses are inlined into the HTML and the
 *    browser doesn't refetch them during hydration (and `handleFetch` can re-point `/api`
 *    at the backend on the server side);
 *  - it never throws and never localizes. A load runs on the server, where the locale is
 *    still the pt-BR default, so it returns the raw status and lets the page turn that into
 *    a message with `t()` — which re-renders when the visitor switches language.
 */

/**
 * @param {typeof globalThis.fetch} fetch the load event's fetch
 * @param {string} path API path *without* the `/api` prefix, e.g. `/public/my-group`
 * @returns {Promise<{ data: any, status: number }>} `status` is 200 on success, the HTTP
 *   status on an API error, or 0 when the request never got an answer.
 */
export async function fetchPublic(fetch, path) {
	try {
		const res = await fetch(`/api${path}`);
		if (!res.ok) return { data: null, status: res.status };
		return { data: await res.json(), status: 200 };
	} catch {
		// backend down / DNS / aborted — the page renders its generic failure copy
		return { data: null, status: 0 };
	}
}
