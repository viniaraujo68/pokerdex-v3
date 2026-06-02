/** Thin fetch wrapper. Same-origin in prod (Caddy), proxied in dev (Vite). */

export class ApiError extends Error {
	/** @param {number} status @param {string} message */
	constructor(status, message) {
		super(message);
		this.status = status;
	}
}

/**
 * @param {string} path
 * @param {RequestInit} [options]
 */
export async function api(path, options = {}) {
	const res = await fetch(`/api${path}`, {
		credentials: 'include',
		headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
		...options
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
		throw new ApiError(res.status, detail || `Erro ${res.status}`);
	}
	return body;
}

export const get = (p) => api(p);
export const post = (p, data) => api(p, { method: 'POST', body: JSON.stringify(data ?? {}) });
export const put = (p, data) => api(p, { method: 'PUT', body: JSON.stringify(data ?? {}) });
export const patch = (p, data) => api(p, { method: 'PATCH', body: JSON.stringify(data ?? {}) });
export const del = (p) => api(p, { method: 'DELETE' });
