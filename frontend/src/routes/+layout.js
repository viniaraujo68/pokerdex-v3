// Authenticated, cookie-based app: render as a client SPA (no SSR).
// Avoids server-side module-state sharing and relative-fetch issues.
//
// The public surface opts back in per route (`src/routes/g/[slug]/+page.js` and
// `src/routes/explorar/+page.js` set `ssr = true`) — those pages get crawled and unfurled,
// so they have to arrive as HTML. A page's own option wins over the layout's.
export const ssr = false;
export const prerender = false;
