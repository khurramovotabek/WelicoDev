// Browser kutubxonalarini static/vendor ichiga ko'chiradi.
import {
  copyFileSync,
  readFileSync,
  writeFileSync,
  cpSync,
  mkdirSync,
} from "node:fs";
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
  "node_modules/leaflet/dist/leaflet.js": "static/vendor/leaflet/leaflet.js",
  "node_modules/leaflet/dist/leaflet.css": "static/vendor/leaflet/leaflet.css",
};

for (const [src, dst] of Object.entries(files)) {
  mkdirSync(dirname(dst), { recursive: true });
  copyFileSync(src, dst);

  // Remove source-map references from copied JS files.
  if (dst.endsWith(".js")) {
    const content = readFileSync(dst, "utf8")
      .replace(/\/\/[#@]\s*sourceMappingURL=.*$/gm, "")
      .replace(/\/\*[#@]\s*sourceMappingURL=.*?\*\//gs, "");
    writeFileSync(dst, content);
  }
}

cpSync(
  "node_modules/leaflet/dist/images",
  "static/vendor/leaflet/images",
  { recursive: true },
);

console.log(`vendor: ${Object.keys(files).length} files copied; Leaflet images copied`);
