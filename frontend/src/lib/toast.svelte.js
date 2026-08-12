/**
 * The app's single feedback channel. `items` is a runes `$state` array read by the one
 * `<Toasts />` mounted in `+layout.svelte`; because the layout outlives navigations, a
 * toast fired right before a `goto()` still shows up on the destination page.
 */

/** Never stack more than this — beyond it the oldest is dropped. */
const MAX = 3;
/** Auto-dismiss delay. */
const TTL = 4000;

/** @typedef {{ id: number, kind: 'success'|'error', message: string }} ToastItem */

/** @type {ToastItem[]} */
export const items = $state([]);

let nextId = 1;
/** @type {Map<number, ReturnType<typeof setTimeout>>} */
const timers = new Map();

/** @param {number} id */
export function dismiss(id) {
	const timer = timers.get(id);
	if (timer) {
		clearTimeout(timer);
		timers.delete(id);
	}
	const i = items.findIndex((x) => x.id === id);
	if (i !== -1) items.splice(i, 1);
}

/** @param {'success'|'error'} kind @param {string} message */
function push(kind, message) {
	const text = String(message ?? '').trim();
	if (!text) return 0; // nothing to say — don't flash an empty box
	const id = nextId++;
	items.push({ id, kind, message: text });
	while (items.length > MAX) dismiss(items[0].id);
	timers.set(
		id,
		setTimeout(() => dismiss(id), TTL)
	);
	return id;
}

export const toast = {
	/** @param {string} message */
	success: (message) => push('success', message),
	/** @param {string} message */
	error: (message) => push('error', message)
};

/**
 * Extra bottom offset for the mobile overlay, in px. The night form's sticky action bar owns
 * the bottom of the screen; it reserves space here so toasts land above it instead of on top
 * of the Save button.
 */
export const layout = $state({ bottomGap: 0 });

/**
 * Keep the bottom `px` of the viewport toast-free. Callers own the lifecycle: set it while
 * mounted, `setBottomGap(0)` on teardown.
 * @param {number} px
 */
export function setBottomGap(px) {
	layout.bottomGap = Math.max(0, Math.round(px) || 0);
}
