/* WeliCoDev Telegram Mini App: navigatsiya, Telegram integratsiyasi, dars pleyeri. */
(function () {
  const tg = window.Telegram && window.Telegram.WebApp;
  const body = document.body;
  const view = document.getElementById("view");
  const debugUser = body.dataset.debugUser;
  const initData = tg && tg.initData;
  const haptic = (kind) => { try { tg && tg.HapticFeedback && tg.HapticFeedback.impactOccurred(kind || "light"); } catch (e) {} };

  // ------------------------------------------------------------ Telegram muhiti
  if (tg) {
    tg.ready();
    tg.expand();
    try { tg.disableVerticalSwipes && tg.disableVerticalSwipes(); } catch (e) {}
    try { tg.setHeaderColor("#0b1530"); tg.setBackgroundColor("#0b1530"); tg.setBottomBarColor && tg.setBottomBarColor("#0b1530"); } catch (e) {}
    const applyScheme = () => window.wcdTheme && window.wcdTheme.set(tg.colorScheme === "light" ? "light" : "dark");
    try { if (!localStorage.getItem("wcd-theme")) applyScheme(); } catch (e) { applyScheme(); }
    tg.onEvent("themeChanged", applyScheme);
  }
  if (!initData && !debugUser) {
    document.getElementById("tma-outside").hidden = false;
  }

  // ------------------------------------------------------------ Har bir so'rovga imzolangan initData
  const headers = () => (initData ? { "X-Telegram-Init-Data": initData } : debugUser ? { "X-TMA-Debug-User": debugUser } : {});
  document.addEventListener("htmx:configRequest", (ev) => Object.assign(ev.detail.headers, headers()));
  window.tmaFetch = (url, opts = {}) => fetch(url, { ...opts, headers: { ...(opts.headers || {}), ...headers() } });

  // ------------------------------------------------------------ Navigatsiya (stek + Telegram BackButton)
  const stack = [];
  let current = null;
  const backBtn = document.querySelector("[data-back]");

  function syncBack() {
    const canBack = stack.length > 0;
    backBtn.hidden = !canBack;
    document.querySelector("[data-brand]").hidden = canBack;
    if (tg && tg.BackButton) canBack ? tg.BackButton.show() : tg.BackButton.hide();
  }

  function load(url) {
    current = url;
    return htmx.ajax("GET", url, { target: "#view", swap: "innerHTML" }).then(() => window.scrollTo({ top: 0, behavior: "instant" }));
  }

  window.tmaGo = function (url) {
    if (current) stack.push(current);
    haptic("light");
    load(url);
    syncBack();
  };

  function goBack() {
    if (!stack.length) return;
    haptic("light");
    load(stack.pop());
    syncBack();
  }

  function setTab(url) {
    document.querySelectorAll("[data-tab]").forEach((t) => t.classList.toggle("is-active", t.dataset.tab === url));
  }

  backBtn.addEventListener("click", goBack);
  if (tg && tg.BackButton) tg.BackButton.onClick(goBack);

  document.addEventListener("click", (ev) => {
    const tab = ev.target.closest("[data-tab]");
    if (tab) {
      ev.preventDefault();
      stack.length = 0;
      setTab(tab.dataset.tab);
      haptic("soft");
      load(tab.dataset.tab);
      syncBack();
      return;
    }
    const go = ev.target.closest("[data-go]");
    if (go) {
      ev.preventDefault();
      tmaGo(go.dataset.go);
      return;
    }
    const ext = ev.target.closest("[data-external]");
    if (ext) {
      ev.preventDefault();
      const url = ext.dataset.external;
      if (tg && /^https:\/\/t\.me\//.test(url)) tg.openTelegramLink(url);
      else if (tg) tg.openLink(url, { try_instant_view: false });
      else window.open(url, "_blank");
    }
  });

  document.body.addEventListener("tma:screen", (ev) => {
    const d = ev.detail || {};
    document.querySelector("[data-title]").textContent = d.title || document.title;
    syncBack();
    if (window.wcdIcons) window.wcdIcons(view);
  });
  document.body.addEventListener("tma:toast", (ev) => {
    window.wcdToast && window.wcdToast(ev.detail.value || ev.detail);
    haptic("medium");
  });
  document.addEventListener("htmx:responseError", (ev) => {
    if (ev.detail.xhr.status === 401) document.getElementById("tma-outside").hidden = false;
  });

  // ------------------------------------------------------------ Ro'yxatdan o'tish (kontakt ulashish)
  window.tmaShareContact = function (btn) {
    if (!tg || !tg.requestContact) {
      tg ? tg.openTelegramLink(btn.dataset.bot) : window.open(btn.dataset.bot, "_blank");
      return;
    }
    tg.requestContact((ok) => {
      if (!ok) return;
      haptic("medium");
      btn.disabled = true;
      // Kontakt botga yuboriladi va bot foydalanuvchini ro'yxatdan o'tkazadi; tayyor bo'lguncha kutamiz
      let tries = 0;
      const timer = setInterval(async () => {
        tries += 1;
        const me = await tmaFetch(body.dataset.me).then((r) => r.json()).catch(() => ({}));
        if (me.registered || tries > 20) {
          clearInterval(timer);
          btn.disabled = false;
          if (me.registered) {
            try { tg.HapticFeedback.notificationOccurred("success"); } catch (e) {}
            load(body.dataset.home);
          }
        }
      }, 1500);
    });
  };

  // ------------------------------------------------------------ Dars pleyeri (haqiqiy ko'rilgan soniyalar)
  document.addEventListener("alpine:init", () => {
    Alpine.data("tmaPlayer", (cfg) => ({
      done: cfg.done, pending: 0, last: null, watched: 0, pct: 0, timer: null,
      init() {
        const v = this.$refs.video;
        if (!v) return;
        v.addEventListener("loadedmetadata", () => { if (cfg.start > 5 && cfg.start < v.duration - 5) v.currentTime = cfg.start; }, { once: true });
        v.addEventListener("timeupdate", () => {
          const t = v.currentTime;
          if (this.last !== null && !v.seeking) {
            const d = t - this.last;
            if (d > 0 && d < 1.5) { this.pending += d; this.watched += d; }
          }
          this.last = t;
          if (v.duration) this.pct = Math.min(100, Math.round((this.watched / v.duration) * 100));
        });
        v.addEventListener("seeking", () => (this.last = null));
        v.addEventListener("pause", () => this.flush());
        v.addEventListener("ended", () => this.flush());
        this.timer = setInterval(() => this.flush(), 10000);
        document.body.addEventListener("htmx:beforeSwap", () => { this.flush(); clearInterval(this.timer); }, { once: true });
      },
      flush() {
        if (this.pending < 1) return;
        const v = this.$refs.video;
        const payload = JSON.stringify({ position: v.currentTime, delta: this.pending });
        this.pending = 0;
        tmaFetch(cfg.heartbeat, { method: "POST", body: payload, headers: { "Content-Type": "application/json" } })
          .then((r) => (r.ok ? r.json() : null))
          .then((d) => {
            if (d && d.video_completed && !this.done) {
              this.done = true;
              try { tg.HapticFeedback.notificationOccurred("success"); } catch (e) {}
              if (d.completed) setTimeout(() => load(current), 900);
            }
          })
          .catch(() => {});
      },
    }));
  });

  // ------------------------------------------------------------ Boshlash
  document.addEventListener("DOMContentLoaded", () => {
    const start = (tg && tg.initDataUnsafe && tg.initDataUnsafe.start_param) || "";
    load(body.dataset.home).then(() => {
      // t.me/welicodevbot/app?startapp=course_<slug> kabi chuqur havolalar
      const m = start.match(/^(course|article|project)_(.+)$/);
      if (m) tmaGo(`/${body.dataset.lang}/app/${{ course: "courses", article: "blog", project: "projects" }[m[1]]}/${m[2]}/`);
    });
  });
})();
