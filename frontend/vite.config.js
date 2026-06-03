import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
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
