/** Money helpers. Values travel as integer cents; we only format/parse at the edges. */

import { i18n } from './i18n.svelte.js';

// pt-BR → "R$ 1.234,56"; en-US → "$1,234.56".
const FORMATS = {
	pt: {
		currency: new Intl.NumberFormat('pt-BR', {
			style: 'currency',
			currency: 'BRL',
			minimumFractionDigits: 2
		}),
		plain: new Intl.NumberFormat('pt-BR', {
			minimumFractionDigits: 2,
			maximumFractionDigits: 2
		}),
		axis: new Intl.NumberFormat('pt-BR', {
			style: 'currency',
			currency: 'BRL',
			minimumFractionDigits: 0,
			maximumFractionDigits: 0
		})
	},
	en: {
		currency: new Intl.NumberFormat('en-US', {
			style: 'currency',
			currency: 'USD',
			minimumFractionDigits: 2
		}),
		plain: new Intl.NumberFormat('en-US', {
			minimumFractionDigits: 2,
			maximumFractionDigits: 2
		}),
		axis: new Intl.NumberFormat('en-US', {
			style: 'currency',
			currency: 'USD',
			minimumFractionDigits: 0,
			maximumFractionDigits: 0
		})
	}
};

/** Reads the reactive locale, so callers inside templates/$derived re-run on switch. */
function fmt() {
	return FORMATS[i18n.locale] ?? FORMATS.pt;
}

/** `null`/`undefined` render as zero — see `centsToInput` for the field-level counterpart.
 * @param {number|null|undefined} cents */
export function formatMoney(cents) {
	return fmt().currency.format((cents ?? 0) / 100);
}

/** Signed money with +/- prefix, for profit columns. @param {number|null|undefined} cents */
export function formatSigned(cents) {
	const v = (cents ?? 0) / 100;
	const sign = v > 0 ? '+' : '';
	return sign + fmt().currency.format(v);
}

/** Money without decimals, for chart axes. @param {number|null|undefined} cents */
export function formatMoneyAxis(cents) {
	return fmt().axis.format((cents ?? 0) / 100);
}

/** Strips spaces and currency symbols. @param {string|number} value */
function stripCurrency(value) {
	return String(value)
		.trim()
		.replace(/\s|R\$|\$/g, '');
}

/**
 * Shapes we accept in a money field. Anything else is a typo, not a number —
 * `validateMoney` refuses it instead of silently saving 0.
 * Negatives are out: buy-in/cash-out are `ge=0` on the server.
 */
const MONEY_SHAPES = [
	/^\d+$/, // 50
	/^\d+[.,]\d{1,2}$/, // 50,5  50.50
	/^\d{1,3}(\.\d{3})+(,\d{1,2})?$/, // 1.234,56  (pt grouping)
	/^\d{1,3}(,\d{3})+(\.\d{1,2})?$/ // 1,234.56  (en grouping)
];

/**
 * Strict counterpart of `parseMoney`, for form fields: cents when the string is a
 * sane amount, 0 for empty (empty is not an error), `null` when it's garbage.
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

/** For text inputs: "12,50" / "12.50" / "1.234,56" -> 1250 cents. @param {string|number} value */
export function parseMoney(value) {
	if (value === null || value === undefined || value === '') return 0;
	let s = stripCurrency(value);
	// If both separators exist, the last one is the decimal separator.
	if (s.includes(',') && s.includes('.')) {
		if (s.lastIndexOf(',') > s.lastIndexOf('.')) s = s.replace(/\./g, '').replace(',', '.');
		else s = s.replace(/,/g, '');
	} else if (s.includes('.')) {
		// Only dots: in pt-BR the dot is the thousands separator ("1.500" = 1500),
		// so treat it as such when every group after the first has exactly 3 digits.
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

/**
 * cents -> editable string like "12,50" (no currency symbol).
 * A real 0 renders as "0", not "": a busted player's R$ 0 cash-out has to survive a
 * round-trip through the edit form instead of looking like an untouched field.
 * @param {number|null|undefined} cents
 */
export function centsToInput(cents) {
	if (cents === null || cents === undefined || Number.isNaN(cents)) return '';
	if (cents === 0) return '0';
	return fmt().plain.format(cents / 100);
}

/** @param {number|null|undefined} cents */
export function moneyClass(cents) {
	if (cents == null) return '';
	if (cents > 0) return 'pos';
	if (cents < 0) return 'neg';
	return '';
}
