/* WeliCoDev xaritalari (Leaflet + CARTO plitkalari).
   - data-map elementlari: saytdagi faqat ko'rish uchun xarita (bosh sahifa, aloqa)
   - Alpine "mapPicker": dashboardda joyni tanlash */
(function () {
  // OpenStreetMap plitkalari (kalitsiz). Qorong'i mavzuda CSS filtr bilan tungi ko'rinish beriladi.
  const tiles = () => "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
  const attribution = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

  const pin = () =>
    L.divIcon({ className: "wcd-pin", html: '<span class="wcd-pin__pulse"></span><span class="wcd-pin__dot"></span>', iconSize: [28, 28], iconAnchor: [14, 14] });

  function baseMap(el, lat, lng, zoom, opts) {
    const map = L.map(el, Object.assign({ zoomControl: false, attributionControl: true, scrollWheelZoom: false }, opts || {})).setView([lat, lng], zoom);
    // OSM qoidasi: plitka so'rovlarida Referer bo'lishi shart (saytning umumiy siyosati "same-origin")
    L.tileLayer(tiles(), { attribution, maxZoom: 19, referrerPolicy: "strict-origin-when-cross-origin" }).addTo(map);
    return map;
  }

  function initViewMaps(root) {
    if (!window.L) return;
    (root || document).querySelectorAll("[data-map]:not([data-map-ready])").forEach((el) => {
      el.dataset.mapReady = "1";
      const lat = parseFloat(el.dataset.lat), lng = parseFloat(el.dataset.lng), zoom = parseInt(el.dataset.zoom || "12", 10);
      const map = baseMap(el, lat, lng, zoom, { dragging: !L.Browser.mobile, tap: false });
      L.control.zoom({ position: "bottomright" }).addTo(map);
      L.marker([lat, lng], { icon: pin(), keyboard: false }).addTo(map);
      // Konteyner o'lchami keyin o'zgarsa (tablar, animatsiya)
      setTimeout(() => map.invalidateSize(), 300);
    });
  }

  // Xarita ko'rinadigan joyga yaqinlashganda yuklanadi
  function lazy() {
    const els = document.querySelectorAll("[data-map]");
    if (!els.length) return;
    if (!("IntersectionObserver" in window)) return initViewMaps();
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => { if (e.isIntersecting) { io.unobserve(e.target); initViewMaps(e.target.parentNode); } });
    }, { rootMargin: "200px" });
    els.forEach((el) => io.observe(el));
  }
  document.addEventListener("DOMContentLoaded", lazy);
  window.wcdInitMaps = initViewMaps;

  document.addEventListener("alpine:init", () => {
    Alpine.data("mapPicker", (lat, lng, zoom) => ({
      init() {
        const start = () => {
          if (!window.L) return setTimeout(start, 100);
          const map = baseMap(this.$refs.map, lat, lng, zoom, { scrollWheelZoom: true });
          L.control.zoom({ position: "bottomright" }).addTo(map);
          const marker = L.marker([lat, lng], { icon: pin(), draggable: true }).addTo(map);
          const form = this.$root.closest("form");
          const set = (ll) => {
            form.querySelector("[name=latitude]").value = ll.lat.toFixed(6);
            form.querySelector("[name=longitude]").value = ll.lng.toFixed(6);
          };
          marker.on("dragend", () => set(marker.getLatLng()));
          map.on("click", (e) => { marker.setLatLng(e.latlng); set(e.latlng); });
          map.on("zoomend", () => { form.querySelector("[name=map_zoom]").value = map.getZoom(); });
          ["latitude", "longitude"].forEach((n) => form.querySelector(`[name=${n}]`).addEventListener("change", () => {
            const ll = L.latLng(parseFloat(form.latitude.value), parseFloat(form.longitude.value));
            marker.setLatLng(ll); map.panTo(ll);
          }));
          this.map = map; this.marker = marker; this.set = set;
          // Tab ochilganda o'lchamni qayta hisoblash
          new IntersectionObserver(() => map.invalidateSize()).observe(this.$refs.map);
        };
        start();
      },
      locate() {
        if (!navigator.geolocation) return;
        navigator.geolocation.getCurrentPosition((p) => {
          const ll = L.latLng(p.coords.latitude, p.coords.longitude);
          this.marker.setLatLng(ll); this.map.setView(ll, 15); this.set(ll);
        });
      },
    }));
  });
})();
