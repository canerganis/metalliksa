import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import {defineConfig} from 'vite';

export default defineConfig(({mode}) => {
  // Static GitHub Pages demo (docs/DEMO_STATIC_DESIGN.md): only `vite build --mode demo` changes base and outDir.
  const demo = mode === 'demo';
  return {
    ...(demo ? {base: process.env.VITE_BASE_PATH || '/metalliksa/'} : {}),
    // Compile-time constant behind src/demo/flag.ts: false everywhere except the demo build, so Vite folds the demo branches away.
    define: {__STATIC_DEMO__: JSON.stringify(demo)},
    plugins: [react(), tailwindcss()],
    optimizeDeps: {
      // Only the SPA is an entry point; bundled scientific docs are not apps.
      entries: ['index.html'],
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    build: {
      ...(demo ? {outDir: 'dist-demo'} : {}),
      chunkSizeWarningLimit: 600,
      rollupOptions: {
        output: {
          manualChunks(id: string) {
            if (!id.includes('node_modules')) return undefined;
            if (/node_modules[\\/](three)[\\/]/.test(id)) return 'vendor-three';
            if (/node_modules[\\/](recharts|victory-vendor|d3-[^\\/]+)[\\/]/.test(id)) return 'vendor-charts';
            if (/node_modules[\\/](jspdf|jspdf-autotable|html2canvas|canvg|dompurify)[\\/]/.test(id)) return 'vendor-pdf';
            if (/node_modules[\\/][^\\/]*plotly[^\\/]*[\\/]/.test(id)) return 'vendor-plotly';
            if (/node_modules[\\/](react|react-dom|scheduler)[\\/]/.test(id)) return 'vendor-react';
            // Loaded only when a "How this is calculated" panel opens (src/utils/loadKatex.ts).
            if (/node_modules[\\/]katex[\\/]/.test(id)) return 'vendor-katex';
            return undefined;
          },
        },
      },
    },
    server: {
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      // Do not modifyâfile watching is disabled to prevent flickering during agent edits.
      hmr: process.env.DISABLE_HMR !== 'true',
      // Disable file watching when DISABLE_HMR is true to save CPU during agent edits.
      watch: process.env.DISABLE_HMR === 'true' ? null : {
        // Solver evidence and generated indexes must not reload an active UI job.
        ignored: [
          '**/graft/**',
          '**/.tmp-lpbf*/**',
          '**/.lpbf-*/**',
          '**/.warp-cache*/**',
          '**/docs/*.partial.json',
        ],
      },
    },
  };
});
