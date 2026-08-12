/**
 * Per-group UI options. They live in localStorage (device-local, no server round-trip) and
 * are mirrored in a `$state` map so a toggle in the Config tab updates the group header in
 * the same paint, without a reload.
 */

const PREFIX = 'pokerdex.opt.unbalancedBadge';

/**
 * Values set this session. A missing key falls through to storage; reading an absent key on
 * a `$state` proxy still registers the dependency, so the later write re-renders readers.
 * @type {Record<string, boolean>}
 */
const overrides = $state({});

/** @param {string|number} groupId */
function key(groupId) {
	return `${PREFIX}.${groupId}`;
}

/** @param {string|number} groupId */
function readStored(groupId) {
	try {
		// Default ON: the warning is opt-out, since a pot that doesn't close is usually a typo.
		return localStorage.getItem(key(groupId)) !== '0';
	} catch {
		return true; // storage blocked — behave like the default
	}
}

/** Is the unbalanced-nights warning enabled for this group? @param {string|number} groupId */
export function unbalancedBadgeEnabled(groupId) {
	return overrides[String(groupId)] ?? readStored(groupId);
}

/** @param {string|number} groupId @param {boolean} on */
export function setUnbalancedBadge(groupId, on) {
	overrides[String(groupId)] = on;
	try {
		localStorage.setItem(key(groupId), on ? '1' : '0');
	} catch {
		// non-fatal: the choice holds for this session only
	}
}
