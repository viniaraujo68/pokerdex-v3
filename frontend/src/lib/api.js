/** Thin fetch wrapper. Same-origin in prod (Caddy), proxied in dev (Vite). */

import { t } from './i18n.svelte.js';

export class ApiError extends Error {
	/** @param {number} status @param {string} message @param {string} [code] */
	constructor(status, message, code) {
		super(message);
		this.status = status;
		/** Machine-readable backend error code, when the API sent one. */
		this.code = code;
	}
}

/** @param {any} detail @returns {string|undefined} */
function detailCode(detail) {
	return detail && typeof detail === 'object' && typeof detail.code === 'string'
		? detail.code
		: undefined;
}

/** FastAPI 422 manda `detail` como lista de objetos; vira texto legível. @param {any} detail */
function detailMessage(detail) {
	if (Array.isArray(detail)) {
		return detail
			.map((d) => (d && typeof d === 'object' ? d.msg || JSON.stringify(d) : String(d)))
			.filter(Boolean)
			.join('; ');
	}
	const code = detailCode(detail);
	if (code) {
		// The backend sends `{code, message}` for user-facing errors: localize off the code
		// and keep its pt-BR `message` as the fallback for codes we don't know yet.
		const key = `apiError.${code}`;
		const localized = t(key);
		if (localized !== key) return localized;
		return detail.message || key;
	}
	if (detail && typeof detail === 'object') return detail.msg || JSON.stringify(detail);
	return detail;
}

/**
 * @param {string} path
 * @param {RequestInit} [options]
 */
export async function api(path, options = {}) {
	const res = await fetch(`/api${path}`, {
		credentials: 'include',
		...options,
		headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }
	});

	if (res.status === 204) return null;

	let body = null;
	const text = await res.text();
	if (text) {
		try {
			body = JSON.parse(text);
		} catch {
			body = text;
		}
	}

	if (!res.ok) {
		const detail = body && typeof body === 'object' ? body.detail : body;
		// Coded errors are localized; plain-string `detail`s pass through as the server wrote them.
		throw new ApiError(
			res.status,
			detailMessage(detail) || t('error.http', { status: res.status }),
			detailCode(detail)
		);
	}
	return body;
}

/** @param {string} p */
export const get = (p) => api(p);
/** @param {string} p @param {any} [data] */
export const post = (p, data) => api(p, { method: 'POST', body: JSON.stringify(data ?? {}) });
/** @param {string} p @param {any} [data] */
export const put = (p, data) => api(p, { method: 'PUT', body: JSON.stringify(data ?? {}) });
/** @param {string} p @param {any} [data] */
export const patch = (p, data) => api(p, { method: 'PATCH', body: JSON.stringify(data ?? {}) });
/** @param {string} p */
export const del = (p) => api(p, { method: 'DELETE' });

/**
 * Message of a caught value. A `catch` binding is `unknown`, and everything this app throws
 * is an `Error` (`ApiError` included) — narrowing it here beats repeating the check at every
 * `catch` site, and the `String(e)` fallback means a stray non-Error still reaches the user
 * as text instead of `undefined`.
 * @param {unknown} e
 * @returns {string}
 */
export function errorMessage(e) {
	return e instanceof Error ? e.message : String(e);
}

/**
 * HTTP status of a caught value, or 0 for anything that wasn't an API error — lets callers
 * special-case a status (403, 404) without an `instanceof` dance.
 * @param {unknown} e
 * @returns {number}
 */
export function errorStatus(e) {
	return e instanceof ApiError ? e.status : 0;
}
