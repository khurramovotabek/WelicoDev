// Shablon va JS'lardagi Lucide belgilarini yig'ib, faqat shulardan iborat kichik to'plam yaratadi.
// Natija: static/vendor/lucide-subset.js (window.lucide.createIcons bilan bir xil API).
// Noma'lum belgi uchrasa (masalan dashboard'da kiritilgan nom), to'liq lucide.min.js keyinroq yuklanadi.
import { readFileSync, readdirSync, statSync, writeFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const ROOTS = ["templates", "apps", "static/js"];
const EXTRA = [ // ma'lumotlar bazasida ishlatiladigan va tez-tez kerak bo'ladigan belgilar
  "store", "package", "credit-card", "user-round", "layout-dashboard", "plug", "users", "activity", "star", "trending-up",
  "cpu", "briefcase", "book-open", "leaf", "hash", "check", "code", "globe", "shield", "zap", "rocket", "database",
  "server", "cloud", "smartphone", "monitor", "lock", "key", "bell", "mail", "phone", "map-pin", "calendar", "clock",
  "heart", "message-circle", "settings", "search", "image", "video", "music", "file-text", "folder", "terminal",
];
const found = new Set(EXTRA);
const re = /data-lucide="([a-z0-9-]+)"|data-lucide='([a-z0-9-]+)'|data-lucide=\\"([a-z0-9-]+)\\"|\|default:'([a-z0-9-]+)'|lucide="\$\{[^}]*"([a-z0-9-]+)"/g;
const walk = (dir) => {
  for (const f of readdirSync(dir)) {
    const p = join(dir, f);
    if (f === "migrations" || f === "node_modules" || f === "__pycache__") continue;
    const st = statSync(p);
    if (st.isDirectory()) walk(p);
    else if (/\.(html|js|py)$/.test(f)) {
      const src = readFileSync(p, "utf8");
      for (const m of src.matchAll(re)) found.add(m[1] || m[2] || m[3] || m[4] || m[5]);
      // {% if ... %}a{% else %}b{% endif %} kabi shartli nomlar
      for (const m of src.matchAll(/data-lucide="[^"]*\{%[^"]*"/g)) {
        for (const w of m[0].matchAll(/%\}([a-z0-9-]+)\{%/g)) found.add(w[1]);
      }
      // icon-name ko'rinishidagi Python satrlari: "user-plus", "message-circle" ...
      if (p.endsWith(".py")) for (const m of src.matchAll(/"([a-z]+(?:-[a-z0-9]+)+)"/g)) found.add(m[1]);
    }
  }
};
ROOTS.forEach((r) => existsSync(r) && walk(r));

const icons = {};
for (const name of [...found].sort()) {
  const file = `node_modules/lucide/dist/esm/icons/${name}.js`;
  if (!existsSync(file)) continue;
  const mod = await import(pathToFileURL(file).href);
  icons[name] = mod.default[2];
}

const runtime = `/* Lucide subset (${Object.keys(icons).length} icons) — scripts/build-icons.mjs bilan yaratilgan */
(function(){
var I=${JSON.stringify(icons)};
var NS="http://www.w3.org/2000/svg";
function el(t,a){var e=document.createElementNS(NS,t);for(var k in a)e.setAttribute(k,a[k]);return e;}
var missing=false;
function createIcons(o){o=o||{};var root=o.root||document,attrs=o.attrs||{};
 var nodes=root.querySelectorAll?root.querySelectorAll("[data-lucide]"):[];
 if(root.getAttribute&&root.getAttribute("data-lucide"))nodes=[root].concat([].slice.call(nodes));
 [].forEach.call(nodes,function(n){var name=n.getAttribute("data-lucide"),d=I[name];
  if(!d){missing=true;return;}
  var s=el("svg",{xmlns:NS,width:24,height:24,viewBox:"0 0 24 24",fill:"none",stroke:"currentColor","stroke-width":attrs["stroke-width"]||2,"stroke-linecap":"round","stroke-linejoin":"round"});
  d.forEach(function(c){s.appendChild(el(c[0],c[1]));});
  [].forEach.call(n.attributes,function(a){if(a.name!=="data-lucide")s.setAttribute(a.name,a.value);});
  s.setAttribute("class",("lucide lucide-"+name+" "+(n.getAttribute("class")||"")).trim());
  s.setAttribute("aria-hidden","true");
  n.parentNode&&n.parentNode.replaceChild(s,n);});
 if(missing&&!window.__lucideFull){window.__lucideFull=1;var sc=document.createElement("script");
  sc.src=(document.querySelector('script[src*="lucide-subset"]')||{}).src.replace("lucide-subset.js","lucide.min.js");
  sc.onload=function(){var full=window.lucide;window.lucide=Object.assign({},full,{createIcons:function(x){full.createIcons(x);}});full.createIcons(o);};
  document.head.appendChild(sc);}
}
window.lucide={createIcons:createIcons,icons:I};
})();`;
writeFileSync("static/vendor/lucide-subset.js", runtime);
console.log(`lucide-subset: ${Object.keys(icons).length} icons, ${(runtime.length / 1024).toFixed(1)} KB`);
