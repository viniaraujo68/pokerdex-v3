// Authenticated, cookie-based app: render as a client SPA (no SSR).
// Avoids server-side module-state sharing and relative-fetch issues.
export const ssr = false;
export const prerender = false;
