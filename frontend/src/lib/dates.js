import { localeTag } from './i18n.svelte.js';

/** @param {string} date */
export function formatNightDate(date) {
	return new Date(date + 'T00:00:00').toLocaleDateString(localeTag(), {
		day: '2-digit',
		month: 'long',
		year: 'numeric'
	});
}
