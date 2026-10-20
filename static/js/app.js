/* WeliCoDev — umumiy frontend yordamchilari */
(function () {
  const root = document.documentElement;

  // ---------------------------------------------------------------- Mavzu
  window.wcdTheme = {
    get() {
      return root.dataset.theme || "dark";
    },
    set(theme) {
      root.dataset.theme = theme;
      try { localStorage.setItem("wcd-theme", theme); } catch (e) {}
      document.dispatchEvent(new CustomEvent("themechange", { detail: theme }));
    },
    toggle() {
      this.set(this.get() === "dark" ? "light" : "dark");
    },
  };

  // ---------------------------------------------------------------- Belgilar
  function renderIcons(scope) {
    if (window.lucide) window.lucide.createIcons({ attrs: { "stroke-width": 1.8 }, nameAttr: "data-lucide", root: scope || document });
  }

  // ---------------------------------------------------------------- Kod bloklari
  // highlight.js (125 KB) faqat sahifada kod bloki bo'lsa yuklanadi
  let hljsLoading = null;
  function loadHljs() {
    if (window.hljs) return Promise.resolve();
    if (hljsLoading) return hljsLoading;
    const b = document.body;
    const css = document.createElement("link");
    css.rel = "stylesheet"; css.href = b.dataset.hljsCss;
    document.head.appendChild(css);
    hljsLoading = new Promise((ok) => {
      const sc = document.createElement("script");
      sc.src = b.dataset.hljs; sc.onload = ok; sc.onerror = ok;
      document.head.appendChild(sc);
    });
    return hljsLoading;
  }

  function enhanceCode(scope) {
    const blocks = (scope || document).querySelectorAll(".richtext pre:not([data-enhanced])");
    if (!blocks.length) return;
    if (!window.hljs && document.body.dataset.hljs) {
      loadHljs().then(() => enhanceCode(scope));
      return;
    }
    blocks.forEach((pre) => {
      pre.dataset.enhanced = "1";
      const code = pre.querySelector("code") || pre;
      const lang = ([...code.classList].find((c) => c.startsWith("language-")) || "language-code").replace("language-", "");
      if (window.hljs && lang !== "plaintext") {
        try { window.hljs.highlightElement(code); } catch (e) {}
      }
      const head = document.createElement("div");
      head.className = "code-head";
      head.innerHTML = `<span>${lang}</span><button type="button"><i data-lucide="copy" class="w-3.5 h-3.5"></i><span>Copy</span></button>`;
      head.querySelector("button").addEventListener("click", async (ev) => {
        const label = ev.currentTarget.querySelector("span");
        try {
          await navigator.clipboard.writeText(code.innerText);
          label.textContent = "Copied";
        } catch (e) {
          label.textContent = "Ctrl+C";
        }
        setTimeout(() => (label.textContent = "Copy"), 1600);
      });
      pre.prepend(head);
    });
  }

  // ---------------------------------------------------------------- Toast
  window.wcdToast = function (message, kind) {
    const box = document.getElementById("toasts");
    if (!box) return;
    const el = document.createElement("div");
    el.className = `glass glass--sm px-4 py-3 text-sm flex items-center gap-2 animate-fade-up ${kind === "error" ? "text-danger" : "text-ink"}`;
    el.innerHTML = `<i data-lucide="${kind === "error" ? "circle-alert" : "circle-check"}" class="w-4 h-4"></i><span></span>`;
    el.querySelector("span").textContent = message;
    box.appendChild(el);
    renderIcons(el);
    setTimeout(() => el.remove(), 3800);
  };

  // ---------------------------------------------------------------- Nusxa olish
  window.wcdCopy = async function (text, okMessage) {
    try {
      await navigator.clipboard.writeText(text);
      window.wcdToast(okMessage || "Nusxa olindi");
    } catch (e) {
      window.prompt("Copy:", text);
    }
  };

  // ---------------------------------------------------------------- HTMX
  document.addEventListener("htmx:configRequest", (ev) => {
    const token = document.querySelector('meta[name="csrf-token"]');
    if (token) ev.detail.headers["X-CSRFToken"] = token.content;
  });
  document.addEventListener("htmx:afterSwap", (ev) => {
    renderIcons(ev.target);
    enhanceCode(ev.target);
  });
  document.addEventListener("htmx:responseError", (ev) => {
    if (ev.detail.xhr.status === 401 || ev.detail.xhr.status === 403) {
      window.wcdToast("Avval Telegram orqali kiring", "error");
    } else if (ev.detail.xhr.status === 429) {
      window.wcdToast("Juda tez. Biroz kutib qayta urinib ko'ring", "error");
    } else {
      window.wcdToast("Xatolik yuz berdi", "error");
    }
  });
  document.body.addEventListener("toast", (ev) => window.wcdToast(ev.detail.value || ev.detail.message, ev.detail.kind));

  // Skript `defer` bilan yuklanadi: DOM tayyor, Alpine esa hali ishga tushmagan.
  // Belgilar Alpine bog'lanishlaridan oldin chizilishi kerak, aks holda x-show kabi atributlar yo'qoladi.
  renderIcons();
  enhanceCode();
  window.wcdIcons = renderIcons;

  // ---------------------------------------------------------------- Alpine komponentlari
  document.addEventListener("alpine:init", () => {
    // Joylashuvdagi mahalliy vaqt (sayt egasining vaqt zonasi bo'yicha)
    window.Alpine.data("localClock", (tz) => ({
      time: "",
      init() {
        let f;
        try { f = new Intl.DateTimeFormat(document.documentElement.lang || "uz", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: tz || "Asia/Tashkent" }); }
        catch (e) { f = new Intl.DateTimeFormat("en", { hour: "2-digit", minute: "2-digit", hour12: false }); }
        const tick = () => (this.time = f.format(new Date()));
        tick();
        setInterval(tick, 15000);
      },
    }));

    // Bitta sahifada faqat bitta audio o'ynaydi
    window.Alpine.data("audioPlayer", (src) => {
      const audioEl = new Audio();  // reaktiv Proxy'dan tashqarida
      return {
      get audio() { return audioEl; },
      playing: false, pct: 0, current: "0:00", total: "0:00",
      list: [], idx: 0, title: "", artist: "", cover: "",
      init() {
        const data = this.$el.querySelector("script#tracks-data");
        if (data) { try { this.list = JSON.parse(data.textContent); } catch (e) {} }
        this.audio.preload = "none";
        this.audio.src = src;
        this.audio.addEventListener("timeupdate", () => {
          const d = this.audio.duration || 0;
          this.pct = d ? (this.audio.currentTime / d) * 100 : 0;
          this.current = fmt(this.audio.currentTime);
          this.total = fmt(d);
        });
        this.audio.addEventListener("ended", () => {
          this.playing = false;
          if (this.list.length > 1) this.next();
        });
        document.addEventListener("wcd-audio-play", (e) => {
          if (e.detail !== this.audio) { this.audio.pause(); this.playing = false; }
        });
      },
      toggle() {
        if (this.playing) { this.audio.pause(); this.playing = false; return; }
        document.dispatchEvent(new CustomEvent("wcd-audio-play", { detail: this.audio }));
        this.audio.play().then(() => (this.playing = true)).catch(() => (this.playing = false));
      },
      load(newSrc) {
        this.audio.pause();
        this.audio.src = newSrc;
        this.playing = false;
        this.toggle();
      },
      pick(i) {
        const t = this.list[i];
        if (!t) return;
        if (i === this.idx && this.audio.src.endsWith(t.src)) { this.toggle(); return; }
        this.idx = i;
        this.title = t.title; this.artist = t.artist; this.cover = t.cover;
        this.load(t.src);
      },
      next() { if (this.list.length) this.pick((this.idx + 1) % this.list.length); },
      prev() { if (this.list.length) this.pick((this.idx + this.list.length - 1) % this.list.length); },
      seek(ev) {
        const r = ev.currentTarget.getBoundingClientRect();
        if (this.audio.duration) this.audio.currentTime = ((ev.clientX - r.left) / r.width) * this.audio.duration;
      },
      };
    });
  });

  function fmt(sec) {
    if (!isFinite(sec)) return "0:00";
    const m = Math.floor(sec / 60), s = Math.floor(sec % 60);
    return `${m}:${String(s).padStart(2, "0")}`;
  }
})();
