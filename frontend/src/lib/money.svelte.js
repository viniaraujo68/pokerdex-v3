import { createFormatters } from '@viniaraujo68/plinth/formatters';
import { i18n } from './i18n.svelte.js';

/** @type {Record<string, { tag: string, currency: string }>} */
const LOCALES = {
	pt: { tag: 'pt-BR', currency: 'BRL' },
	en: { tag: 'en-US', currency: 'USD' }
};

/** @type {Map<string, { format: import('@viniaraujo68/plinth/formatters').Formatters, currency: string }>} */
const cache = new Map();

/** @param {string} locale */
function formattersFor(locale) {
	const cached = cache.get(locale);
	if (cached) return cached;
	const { tag, currency } = LOCALES[locale] ?? LOCALES.pt;
	const built = { format: createFormatters(tag), currency };
	cache.set(locale, built);
	return built;
}

const active = $derived(formattersFor(i18n.locale));

/** @param {number|null|undefined} cents */
export function formatMoney(cents) {
	return active.format.currency((cents ?? 0) / 100, active.currency);
}

/** @param {number|null|undefined} cents */
export function formatSigned(cents) {
	const v = (cents ?? 0) / 100;
	const sign = v > 0 ? '+' : '';
	return sign + active.format.currency(v, active.currency);
}

/** @param {number|null|undefined} cents */
export function formatMoneyAxis(cents) {
	return active.format.currency((cents ?? 0) / 100, active.currency, 'axis');
}

/** @param {string|number} value */
function stripCurrency(value) {
	return String(value)
		.trim()
		.replace(/\s|R\$|\$/g, '');
}

const MONEY_SHAPES = [
	/^\d+$/,
	/^\d+[.,]\d{1,2}$/,
	/^\d{1,3}(\.\d{3})+(,\d{1,2})?$/,
	/^\d{1,3}(,\d{3})+(\.\d{1,2})?$/
];

/**
 * @param {string|number|null|undefined} value
 * @returns {number|null}
 */
export function validateMoney(value) {
	if (value === null || value === undefined) return 0;
	const s = stripCurrency(value);
	if (s === '') return 0;
	if (!MONEY_SHAPES.some((re) => re.test(s))) return null;
	return parseMoney(s);
}

/** @param {string|number} value */
export function parseMoney(value) {
	if (value === null || value === undefined || value === '') return 0;
	let s = stripCurrency(value);
	if (s.includes(',') && s.includes('.')) {
		if (s.lastIndexOf(',') > s.lastIndexOf('.')) s = s.replace(/\./g, '').replace(',', '.');
		else s = s.replace(/,/g, '');
	} else if (s.includes('.')) {
		const parts = s.split('.');
		const thousands = parts.slice(1).every((p) => /^\d{3}$/.test(p));
		if (thousands) s = parts.join('');
	} else {
		s = s.replace(',', '.');
	}
	const n = Number(s);
	if (Number.isNaN(n)) return 0;
	return Math.round(n * 100);
}

/** @param {number|null|undefined} cents */
export function centsToInput(cents) {
	if (cents === null || cents === undefined || Number.isNaN(cents)) return '';
	if (cents === 0) return '0';
	return active.format.currency(cents / 100, active.currency, 'plain');
}

/** @param {number|null|undefined} cents */
export function moneyClass(cents) {
	if (cents == null) return '';
	if (cents > 0) return 'money-pos';
	if (cents < 0) return 'money-neg';
	return '';
}
