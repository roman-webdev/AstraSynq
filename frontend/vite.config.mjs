import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import {createHash} from "node:crypto";
const securityHeaders={
  'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'",
  'X-Content-Type-Options':'nosniff', 'Referrer-Policy':'same-origin', 'X-Frame-Options':'DENY',
};


// Eligible landing visits start renderer/model transfers before the React app executes.
// This remains an external self-hosted script under the unchanged CSP.
function earlyCoreAssets(){return {name:'astra-early-core',enforce:'post',generateBundle(_options,bundle){
 const html=bundle['index.html'],scene=Object.values(bundle).find(item=>item.type==='chunk'&&item.name==='CoreScene');
 if(!html||html.type!=='asset'||!scene)return;
 const source=`(()=>{const n=navigator;if((location.hash.startsWith('#/')&&location.hash!=='#/')||matchMedia('(prefers-reduced-motion: reduce)').matches||n.connection?.saveData)return;const add=(url,rel,as)=>{const l=document.createElement('link');l.rel=rel;if(as)l.as=as;l.crossOrigin='anonymous';l.href=url;l.fetchPriority='high';document.head.appendChild(l);};add('/${scene.fileName}','modulepreload');for(const f of ['astra-core.model.bin','astra-studio.bin','astra-ceramic_normal.webp','astra-ceramic_roughness.webp','astra-pcb_normal.webp','astra-pcb_roughness.webp','astra-board-'+(matchMedia('(max-width: 767px), (pointer: coarse) and (max-height: 500px)').matches?'mobile':'desktop')+'.bin'])add('/visuals/'+f,'preload','fetch');})();`;
 const boot='assets/scene-start-'+createHash('sha256').update(source).digest('hex').slice(0,8)+'.js';
 this.emitFile({type:'asset',fileName:boot,source});
 html.source=String(html.source).replace('<script type="module"',`<script defer src="/${boot}"></script>\n    <script type="module"`);
}};}

export default defineConfig({
  build: {
    outDir: "dist/client",
    rollupOptions: {
      output: {
        manualChunks(id) {
          // Explicit shared React prevents the lazy chart chunk from owning it
          // and being pulled into every landing visit as a transitive dependency.
          if (['react','react-dom','scheduler','use-sync-external-store'].some(name=>id.includes('/node_modules/'+name+'/'))) return 'react';
          if (id.includes('/node_modules/recharts/')) return 'charts';
          if (['motion','motion-dom','motion-utils','framer-motion'].some(name=>id.includes('/node_modules/'+name+'/'))) return 'motion';
        },
      },
    },
  },
  optimizeDeps: {
    include: ["react", "react-dom/client"],
  },
  server: {
    headers: securityHeaders,
    host: "127.0.0.1",
    port: 4173,
    strictPort: true,
    proxy: {
      '/api': process.env.ASTRASYNQ_API_URL || 'http://127.0.0.1:8011',
      '/health': process.env.ASTRASYNQ_API_URL || 'http://127.0.0.1:8011',
      '/docs': process.env.ASTRASYNQ_API_URL || 'http://127.0.0.1:8011',
      '/openapi.json': process.env.ASTRASYNQ_API_URL || 'http://127.0.0.1:8011',
    },
    allowedHosts: [],
    warmup: {
      clientFiles: ["./src/main.jsx"],
    },
  },
  plugins: [react(),earlyCoreAssets()],
  preview: {headers:securityHeaders},
});


