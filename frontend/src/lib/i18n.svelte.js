/**
 * Hand-rolled i18n. Flat dot-namespaced dictionaries, `{name}` interpolation and a
 * one/other plural convention. `i18n` is a runes $state object, so reading
 * `i18n.locale` inside a template/$derived (which `t()` does) re-renders on switch.
 */
import pt from './i18n/pt.js';
import en from './i18n/en.js';

/** @typedef {'pt'|'en'} Locale */
/** A dictionary value: plain text, or a one/other pair picked by `params.count`. */
/** @typedef {string | { one: string, other: string }} Phrase */

/**
 * Typed as an index so `t()` can look up a runtime string key. The annotation also makes the
 * dictionaries themselves checked: a malformed entry (a plural missing `other`, a nested
 * object) fails here rather than silently rendering as the key.
 * @type {Record<Locale, Record<string, Phrase>>}
 */
const dicts = { pt, en };
const STORAGE_KEY = 'pokerdex.locale';
const TAGS = { pt: 'pt-BR', en: 'en-US' };

/**
 * @returns {Locale}
 *
 * The public pages (`/g/[slug]`, `/explorar`) are server-rendered, and on the server there
 * is no storage and no `navigator` — nor a per-request place to put a locale, since this
 * module's state is shared by every request the node server handles. So SSR always renders
 * pt-BR (the app's primary audience, and what `app.html` declares as `lang`) and the client
 * corrects it during hydration: Svelte re-evaluates the dynamic text, so an English visitor
 * sees English from the first frame it can paint.
 */
function initialLocale() {
	if (typeof window === 'undefined') return 'pt';
	try {
		const saved = localStorage.getItem(STORAGE_KEY);
		if (saved === 'pt' || saved === 'en') return saved;
	} catch {
		// storage blocked (private mode) — fall through to the browser language
	}
	return typeof navigator !== 'undefined' && navigator.language?.toLowerCase().startsWith('pt')
		? 'pt'
		: 'en';
}

export const i18n = $state({ locale: /** @type {Locale} */ (initialLocale()) });

/** @param {Locale} l */
function applyLang(l) {
	if (typeof document !== 'undefined') document.documentElement.lang = TAGS[l] ?? TAGS.pt;
}

/** @param {Locale} l */
export function setLocale(l) {
	if (l !== 'pt' && l !== 'en') return;
	// Browser only: on the server this state is shared across requests, so switching it there
	// would leak one visitor's language into the next one's page.
	if (typeof window === 'undefined') return;
	i18n.locale = l;
	try {
		localStorage.setItem(STORAGE_KEY, l);
	} catch {
		// non-fatal: the language still applies for this session
	}
	applyLang(l);
}

applyLang(i18n.locale);

/** BCP-47 tag of the active locale, for Intl/toLocaleDateString. */
export function localeTag() {
	return TAGS[i18n.locale] ?? TAGS.pt;
}

/** @param {string} str @param {Record<string, any>} [params] */
function interpolate(str, params) {
	if (!params) return str;
	return str.replace(/\{(\w+)\}/g, (m, k) => (k in params ? String(params[k]) : m));
}

/**
 * Translate `key`. Missing keys render as the key itself (loud but harmless).
 * Plural values are `{ one, other }` and are picked with `params.count`.
 * @param {string} key
 * @param {Record<string, any>} [params]
 */
export function t(key, params) {
	const dict = dicts[i18n.locale] ?? dicts.pt;
	const entry = dict[key];
	const value =
		entry && typeof entry === 'object' ? (params?.count === 1 ? entry.one : entry.other) : entry;
	if (typeof value !== 'string') return key;
	return interpolate(value, params);
}
