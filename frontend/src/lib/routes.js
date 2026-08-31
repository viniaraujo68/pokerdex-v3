import { t } from '$lib/i18n.svelte.js';

/** @type {import('@viniaraujo68/plinth/routing').RoutingConfig<import('$app/types').RouteId>} */
export const routes = {
	meta: {
		'/': { title: () => t('nav.home'), icon: 'home' },
		'/explore': { title: () => t('nav.explore'), icon: 'explore' },
		'/account': { title: () => t('nav.account'), icon: 'account', requiredRoles: ['user'] },
		'/login': { title: () => t('nav.login'), icon: 'login', requiredRoles: ['guest'] },
		'/register': { title: () => t('nav.register'), icon: 'register', requiredRoles: ['guest'] },

		'/groups/[id]': {},
		'/groups/[id]/nights/new': {},
		'/g/[slug]': {}
	},

	pages: import.meta.glob('/src/routes/**/+page.svelte')
};
