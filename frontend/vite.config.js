import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	build: {
		cssTarget: ['chrome123', 'edge123', 'firefox120', 'safari17.5']
	},
	server: {
		proxy: {
			// In dev, forward API calls to the FastAPI backend (cookies preserved).
			'/api': {
				target: process.env.API_PROXY || 'http://localhost:8000',
				changeOrigin: true
			}
		}
	}
});
