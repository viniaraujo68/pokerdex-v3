/**
 * `?next=` handling for the login/register bounce. Kept in one place because the value is
 * attacker-controllable: a raw `goto(next)` would happily send the freshly-logged-in user
 * to another origin (open redirect / credential phishing).
 */

/**
 * Accept only same-origin relative paths. `//evil.com` and `/\evil.com` are
 * protocol-relative in browsers, so a leading-slash check alone is not enough.
 * @param {string|null|undefined} value
 * @returns {string|null} the safe path, or null
 */
export function safeNext(value) {
	if (typeof value !== 'string') return null;
	if (!value.startsWith('/')) return null;
	if (value.startsWith('//') || value.startsWith('/\\')) return null;
	return value;
}

/**
 * `/login?next=<current path>` — where a page sends a visitor who isn't signed in.
 * The query string is dropped on purpose: tokens and filters aren't worth round-tripping.
 * @param {URL} url current page URL
 */
export function loginUrl(url) {
	const path = url?.pathname ?? '/';
	return path === '/' ? '/login' : `/login?next=${encodeURIComponent(path)}`;
}

/**
 * Carry the same `next` across the login ↔ register links.
 * @param {string} base '/login' or '/register'
 * @param {string|null} next already-sanitized path
 */
export function withNext(base, next) {
	return next ? `${base}?next=${encodeURIComponent(next)}` : base;
}
