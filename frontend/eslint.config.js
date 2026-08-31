/**
 * Flat config. Two layers only: `@eslint/js` recommended for the JS, `eslint-plugin-svelte`
 * recommended for the components (its own parser reads the runes and the template).
 *
 * No formatting rules and no Prettier here on purpose — `npm run check` (svelte-check with
 * `checkJs`) is what actually catches bugs in this codebase, and a formatter would rewrite
 * every file it touches. Style stays a review conversation.
 */
import js from '@eslint/js';
import svelte from 'eslint-plugin-svelte';
import globals from 'globals';

export default [
	{
		// Build output and the generated SvelteKit types — nothing here is hand-written.
		ignores: ['build/', '.svelte-kit/', 'node_modules/']
	},

	js.configs.recommended,
	...svelte.configs.recommended,

	{
		// App code runs in the browser; the SSR'd pages also touch node globals through
		// `$env`/`handleFetch`, so both sets are in scope.
		languageOptions: {
			ecmaVersion: 2023,
			sourceType: 'module',
			globals: { ...globals.browser, ...globals.node }
		},
		rules: {
			// `catch {}` blocks that deliberately swallow (storage blocked, clipboard missing) are
			// a pattern here, and every one carries a comment saying why.
			'no-empty': ['error', { allowEmptyCatch: true }],

			/*
			 * Off: the rule wants every `href`/`goto()` wrapped in `resolve()` from `$app/paths`,
			 * which only matters for an app mounted under a `base` path or built with
			 * `paths.relative`. Pokerdex is served from the root of its own domain and sets
			 * neither (see svelte.config.js), so `resolve()` would be 30 no-op wrappers.
			 * Revisit if the app ever gains a `base`.
			 */
			'svelte/no-navigation-without-resolve': 'off',

			/*
			 * Off: the rule flags any `new Map()`/`new Set()` in a `.svelte`/`.svelte.js` file and
			 * can't see how it's used. All five sites it caught are deliberately *not* reactive
			 * containers: two are built fresh inside a `$derived` (the derived re-runs, the map
			 * never mutates), one is a local tally inside `NightForm`'s `standardBuyIn`, one is the
			 * copy-on-write `selectedPlayers` filter (a new Set is assigned, never mutated in
			 * place), and one is `money.svelte.js`'s per-locale formatter cache, which nothing
			 * renders. `SvelteMap`/`SvelteSet` would add per-key subscription overhead for no
			 * behaviour change.
			 */
			'svelte/prefer-svelte-reactivity': 'off',
			// Leading `_` marks "required by the signature, unused by us".
			'no-unused-vars': [
				'error',
				{ argsIgnorePattern: '^_', varsIgnorePattern: '^_', caughtErrors: 'none' }
			]
		}
	},

	{
		// Node-only files: config and the server hooks.
		files: ['*.config.js', 'src/hooks.server.js'],
		languageOptions: { globals: globals.node }
	}
];
