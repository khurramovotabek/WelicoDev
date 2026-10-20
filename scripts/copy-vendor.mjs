// node_modules'dagi brauzer kutubxonalarini static/vendor ga ko'chiradi (CDN'ga bog'liq bo'lmaslik uchun)
import { copyFileSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";

const files = {
  "node_modules/alpinejs/dist/cdn.min.js": "static/vendor/alpine.min.js",
  "node_modules/@alpinejs/collapse/dist/cdn.min.js": "static/vendor/alpine-collapse.min.js",
  "node_modules/htmx.org/dist/htmx.min.js": "static/vendor/htmx.min.js",
  "node_modules/lucide/dist/umd/lucide.min.js": "static/vendor/lucide.min.js",
  "node_modules/@highlightjs/cdn-assets/highlight.min.js": "static/vendor/highlight.min.js",
  "node_modules/@highlightjs/cdn-assets/languages/dockerfile.min.js": "static/vendor/hljs-dockerfile.min.js",
  "node_modules/@highlightjs/cdn-assets/languages/nginx.min.js": "static/vendor/hljs-nginx.min.js",
  "node_modules/@highlightjs/cdn-assets/styles/tokyo-night-dark.min.css": "static/vendor/hljs-tokyo-night.min.css",
  "node_modules/qrcode-generator/qrcode.js": "static/vendor/qrcode.js",
  "node_modules/chart.js/dist/chart.umd.js": "static/vendor/chart.umd.js",
};

for (const [src, dst] of Object.entries(files)) {
  mkdirSync(dirname(dst), { recursive: true });
  copyFileSync(src, dst);
}
console.log(`vendor: ${Object.keys(files).length} files copied`);
