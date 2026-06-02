/** Money helpers. Values travel as integer cents; we only format/parse at the edges. */

const fmtBRL = new Intl.NumberFormat('pt-BR', {
	style: 'currency',
	currency: 'BRL',
	minimumFractionDigits: 2
});

const fmtPlain = new Intl.NumberFormat('pt-BR', {
	minimumFractionDigits: 2,
	maximumFractionDigits: 2
});

/** @param {number} cents */
export function formatMoney(cents) {
	return fmtBRL.format((cents ?? 0) / 100);
}

/** Signed money with +/- prefix, for profit columns. @param {number} cents */
export function formatSigned(cents) {
	const v = (cents ?? 0) / 100;
	const sign = cents > 0 ? '+' : '';
	return sign + fmtBRL.format(v);
}

/** For text inputs: "12,50" / "12.50" / "1.234,56" -> 1250 cents. @param {string|number} value */
export function parseMoney(value) {
	if (value === null || value === undefined || value === '') return 0;
	let s = String(value).trim().replace(/\s|R\$/g, '');
	// If both separators exist, the last one is the decimal separator.
	if (s.includes(',') && s.includes('.')) {
		if (s.lastIndexOf(',') > s.lastIndexOf('.')) s = s.replace(/\./g, '').replace(',', '.');
		else s = s.replace(/,/g, '');
	} else {
		s = s.replace(',', '.');
	}
	const n = Number(s);
	if (Number.isNaN(n)) return 0;
	return Math.round(n * 100);
}

/** cents -> editable string like "12,50" (no currency symbol). @param {number} cents */
export function centsToInput(cents) {
	if (!cents) return '';
	return fmtPlain.format(cents / 100);
}

/** @param {number} cents */
export function moneyClass(cents) {
	if (cents > 0) return 'pos';
	if (cents < 0) return 'neg';
	return '';
}
