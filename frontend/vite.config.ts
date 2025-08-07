import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		port: 3000,
		proxy: {
			// Proxy API requests to backend
			'/api': {
				target: 'http://localhost:8000',
				changeOrigin: true
			}
		}
	}
});