/* WeliCoDev — butun sayt bo'ylab ishlaydigan musiqa pleyeri (Alpine store "player").

   - Bitta <audio> elementi (Alpine Proxy'dan tashqarida, aks holda play() ishlamaydi)
   - Navbat, shuffle, repeat (off/all/one), tezlik, ovoz va mute
   - Ekvalayzer: Web Audio API (bass / o'rta / treble) va tayyor presetlar
   - Uyqu taymeri, Media Session (qulf ekrani, klaviatura media tugmalari)
   - Sozlamalar localStorage'da; navbat va joy sahifa almashganda tiklanadi
   - YouTube treklar (src "yt:<id>") rasmiy IFrame API orqali — <audio> bilan bir xil interfeysdagi dvigatel;
     YouTube qoidasiga ko'ra video oynasi ko'rinib turadi (#wcd-yt), ekvalayzer/vizualizator faqat audio faylga
   Fayl sifati o'zgartirilmaydi: audio asl faylidan oqim bilan beriladi. */
(function () {
  const SETTINGS_KEY = "wcd-player";
  const SESSION_KEY = "wcd-player-session";
  const html = new Audio();
  html.preload = "metadata";
  const yt = createYouTubeEngine();
  // Joriy dvigatel: oddiy audio yoki YouTube (trekka qarab almashadi)
  let audio = html;

  const EQ_PRESETS = {
    flat: [0, 0, 0],
    bass: [6, 0, -1],
    vocal: [-2, 4, 2],
    treble: [-1, 0, 5],
    night: [3, -1, -4],
  };

  let ctx = null, nodes = null, sleepTimer = null, saveTick = 0;

  const read = (key, fallback) => {
    try { return JSON.parse(localStorage.getItem(key)) || fallback; } catch (e) { return fallback; }
  };
  const write = (key, value) => {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) {}
  };
  const fmt = (s) => (isFinite(s) && s >= 0 ? `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}` : "0:00");

  // Web Audio grafi faqat birinchi ijroda yaratiladi (brauzer foydalanuvchi harakatini talab qiladi)
  function ensureGraph(store) {
    if (nodes || !(window.AudioContext || window.webkitAudioContext)) return;
    try {
      ctx = new (window.AudioContext || window.webkitAudioContext)();
      const src = ctx.createMediaElementSource(html);
      const bass = ctx.createBiquadFilter(); bass.type = "lowshelf"; bass.frequency.value = 200;
      const mid = ctx.createBiquadFilter(); mid.type = "peaking"; mid.frequency.value = 1500; mid.Q.value = 0.9;
      const treble = ctx.createBiquadFilter(); treble.type = "highshelf"; treble.frequency.value = 4500;
      const analyser = ctx.createAnalyser(); analyser.fftSize = 512; analyser.smoothingTimeConstant = 0.82;
      src.connect(bass).connect(mid).connect(treble).connect(analyser).connect(ctx.destination);
      nodes = { bass, mid, treble, analyser };
      // Vizualizatorlar (musiqa sahifasi) shu analizatordan chastota ma'lumotini o'qiydi
      window.wcdAnalyser = analyser;
      store.applyEq();
    } catch (e) {
      nodes = null;
    }
  }

  document.addEventListener("alpine:init", () => {
    const saved = read(SETTINGS_KEY, {});
    Alpine.store("player", {
      queue: [], idx: -1, playing: false, loading: false,
      pct: 0, buffered: 0, current: "0:00", total: "0:00", duration: 0,
      volume: saved.volume ?? 0.85, muted: !!saved.muted, rate: saved.rate || 1,
      shuffle: !!saved.shuffle, repeat: saved.repeat || "off",
      eq: saved.eq || [0, 0, 0], eqPreset: saved.eqPreset || "flat",
      sleepAt: 0, sleepLeft: "", panel: "", expanded: false, dismissed: false,

      get audio() { return audio; },
      get track() { return this.queue[this.idx] || null; },
      get active() { return !!this.track && !this.dismissed; },
      get presets() { return Object.keys(EQ_PRESETS); },

      init() {
        for (const el of [html, yt]) {
          el.volume = this.volume;
          el.muted = this.muted;
          // Faqat joriy dvigatel hodisalari hisobga olinadi (almashtirishdagi eski "pause" holatni buzmasin)
          const on = (type, fn) => el.addEventListener(type, () => { if (el === audio) fn(); });
          on("timeupdate", () => this.tick());
          on("progress", () => this.tickBuffer());
          on("loadedmetadata", () => { this.duration = audio.duration; this.total = fmt(audio.duration); audio.playbackRate = this.rate; });
          on("play", () => { this.playing = true; this.saveSession(); });
          on("pause", () => { this.playing = false; this.saveSession(); });
          on("waiting", () => (this.loading = true));
          on("playing", () => (this.loading = false));
          on("ended", () => this.onEnded());
          on("error", () => { this.loading = false; this.playing = false; });
        }
        this.mediaSession();
        this.keyboard();
        this.restore();
        window.addEventListener("pagehide", () => this.saveSession());
      },

      // ------------------------------------------------------------ Navbat
      /** Navbatni almashtiradi va i-trekni ijro etadi. Bir xil trek bosilsa pauza/davom. */
      playList(list, i = 0) {
        if (!list || !list.length) return;
        const same = this.track && list[i] && this.track.id === list[i].id && this.track.src === list[i].src;
        if (same) return this.toggle();
        this.queue = list.filter((t) => t && t.src);
        const target = list[i];
        this.play(Math.max(0, this.queue.findIndex((t) => t.id === target.id)));
      },
      /** JSON ro'yxat (script#id) ichidan trekni id bo'yicha ijro etadi. */
      playFrom(elementId, id) {
        const list = window.wcdTracks(elementId);
        const i = id == null ? 0 : list.findIndex((t) => t.id === id);
        if (i >= 0) this.playList(list, i);
      },
      /** Trekka mos dvigatelni tanlaydi (YouTube yoki audio fayl). */
      use(t) {
        const engine = t && t.yt ? yt : html;
        if (engine !== audio) { audio.pause(); audio = engine; }
        if (engine !== yt) yt.hide();
        engine.volume = this.volume; engine.muted = this.muted;
      },
      get isVideo() { return !!(this.track && this.track.yt); },
      play(i) {
        if (!this.queue.length) return;
        this.idx = (i + this.queue.length) % this.queue.length;
        this.dismissed = false;
        this.use(this.track);
        audio.src = this.track.src;
        audio.playbackRate = this.rate;
        this.pct = 0; this.buffered = 0; this.current = "0:00"; this.total = this.track.duration || "0:00";
        this.start();
        this.meta();
      },
      start() {
        if (audio === html) {
          ensureGraph(this);
          if (ctx && ctx.state === "suspended") ctx.resume();
        }
        document.dispatchEvent(new CustomEvent("wcd-audio-play", { detail: audio }));
        this.loading = true;
        return audio.play().catch(() => { this.loading = false; this.playing = false; });
      },
      toggle() {
        if (!this.track) return;
        if (audio.paused) { if (!audio.src) audio.src = this.track.src; this.start(); } else audio.pause();
      },
      next() {
        if (!this.queue.length) return;
        if (this.shuffle && this.queue.length > 1) {
          let j; do { j = Math.floor(Math.random() * this.queue.length); } while (j === this.idx);
          return this.play(j);
        }
        this.play(this.idx + 1);
      },
      prev() {
        if (audio.currentTime > 3) { audio.currentTime = 0; return; }
        this.play(this.idx - 1);
      },
      onEnded() {
        if (this.repeat === "one") { audio.currentTime = 0; return this.start(); }
        if (this.repeat === "off" && !this.shuffle && this.idx === this.queue.length - 1) { this.playing = false; return; }
        this.next();
      },
      close() {
        audio.pause();
        yt.hide();
        this.dismissed = true; this.panel = ""; this.expanded = false;
        try { sessionStorage.removeItem(SESSION_KEY); localStorage.removeItem(SESSION_KEY); } catch (e) {}
      },
      isCurrent(id) { return !!this.track && this.track.id === id; },

      // ------------------------------------------------------------ Vaqt
      tick() {
        const d = audio.duration || 0;
        this.pct = d ? (audio.currentTime / d) * 100 : 0;
        this.current = fmt(audio.currentTime);
        if (d) this.total = fmt(d);
        if (++saveTick % 16 === 0) this.saveSession();
        if (this.sleepAt) this.tickSleep();
        if ("mediaSession" in navigator && d && navigator.mediaSession.setPositionState) {
          try { navigator.mediaSession.setPositionState({ duration: d, playbackRate: audio.playbackRate, position: audio.currentTime }); } catch (e) {}
        }
      },
      tickBuffer() {
        const d = audio.duration || 0;
        if (d && audio.buffered.length) this.buffered = (audio.buffered.end(audio.buffered.length - 1) / d) * 100;
      },
      seekTo(ev) {
        const r = ev.currentTarget.getBoundingClientRect();
        const x = (ev.touches ? ev.touches[0].clientX : ev.clientX) - r.left;
        if (audio.duration) audio.currentTime = Math.max(0, Math.min(1, x / r.width)) * audio.duration;
      },
      seekBy(sec) { if (audio.duration) audio.currentTime = Math.max(0, Math.min(audio.duration, audio.currentTime + sec)); },

      // ------------------------------------------------------------ Ovoz va sozlamalar
      setVolume(v) { this.volume = Math.max(0, Math.min(1, +v)); html.volume = yt.volume = this.volume; if (this.volume > 0 && this.muted) this.toggleMute(); this.saveSettings(); },
      toggleMute() { this.muted = !this.muted; html.muted = yt.muted = this.muted; this.saveSettings(); },
      get volumeIcon() { return this.muted || this.volume === 0 ? "off" : this.volume < 0.5 ? "low" : "high"; },
      setRate(r) { this.rate = r; audio.playbackRate = r; this.saveSettings(); },
      cycleRepeat() { this.repeat = { off: "all", all: "one", one: "off" }[this.repeat]; this.saveSettings(); },
      toggleShuffle() { this.shuffle = !this.shuffle; this.saveSettings(); },
      setPreset(name) { this.eqPreset = name; this.eq = [...EQ_PRESETS[name]]; this.applyEq(); this.saveSettings(); },
      setBand(i, v) { this.eq[i] = +v; this.eqPreset = "custom"; this.applyEq(); this.saveSettings(); },
      applyEq() {
        if (!nodes) return;
        nodes.bass.gain.value = this.eq[0]; nodes.mid.gain.value = this.eq[1]; nodes.treble.gain.value = this.eq[2];
      },
      setSleep(minutes) {
        this.sleepAt = minutes ? Date.now() + minutes * 60000 : 0;
        this.sleepLeft = minutes ? `${minutes}:00` : "";
        clearInterval(sleepTimer);
        if (minutes) sleepTimer = setInterval(() => this.tickSleep(), 1000);
      },
      tickSleep() {
        const left = Math.round((this.sleepAt - Date.now()) / 1000);
        if (left <= 0) { audio.pause(); this.setSleep(0); return; }
        this.sleepLeft = fmt(left);
      },
      togglePanel(name) { this.panel = this.panel === name ? "" : name; },
      saveSettings() {
        write(SETTINGS_KEY, { volume: this.volume, muted: this.muted, rate: this.rate, shuffle: this.shuffle, repeat: this.repeat, eq: this.eq, eqPreset: this.eqPreset });
      },

      // ------------------------------------------------------------ Sahifalar orasida davom ettirish
      saveSession() {
        if (!this.track || this.dismissed) return;
        write(SESSION_KEY, { queue: this.queue, idx: this.idx, time: audio.currentTime || 0, playing: !audio.paused, at: Date.now() });
      },
      restore() {
        const s = read(SESSION_KEY, null);
        // 6 soatdan eski sessiya tiklanmaydi
        if (!s || !s.queue || !s.queue.length || Date.now() - (s.at || 0) > 6 * 3600 * 1000) return;
        this.queue = s.queue; this.idx = Math.min(s.idx, s.queue.length - 1);
        this.use(this.track);
        audio.src = this.track.src;
        const resumeAt = s.time || 0;
        audio.addEventListener("loadedmetadata", () => { if (resumeAt < audio.duration - 1) audio.currentTime = resumeAt; }, { once: true });
        this.current = fmt(resumeAt);
        this.meta();
        // Avvalgi sahifada o'ynayotgan bo'lsa, davom ettirishga harakat (brauzer ruxsat bermasa — pauza holatida qoladi).
        // YouTube videosi foydalanuvchi bosmaguncha o'zi boshlanmaydi.
        if (s.playing && audio === html) audio.play().catch(() => {});
      },

      // ------------------------------------------------------------ Tizim integratsiyasi
      meta() {
        if (!("mediaSession" in navigator) || !this.track) return;
        const t = this.track;
        navigator.mediaSession.metadata = new MediaMetadata({
          title: t.title, artist: t.artist, album: t.album || "WeliCoDev",
          artwork: t.cover ? [{ src: t.cover, sizes: "512x512" }] : [],
        });
      },
      mediaSession() {
        if (!("mediaSession" in navigator)) return;
        const ms = navigator.mediaSession;
        const on = (action, fn) => { try { ms.setActionHandler(action, fn); } catch (e) {} };
        on("play", () => this.toggle());
        on("pause", () => this.toggle());
        on("previoustrack", () => this.prev());
        on("nexttrack", () => this.next());
        on("seekbackward", (d) => this.seekBy(-(d.seekOffset || 10)));
        on("seekforward", (d) => this.seekBy(d.seekOffset || 10));
        on("seekto", (d) => { if (d.seekTime != null) audio.currentTime = d.seekTime; });
      },
      keyboard() {
        document.addEventListener("keydown", (e) => {
          if (!this.active || e.ctrlKey || e.metaKey || e.altKey) return;
          const tag = (document.activeElement && document.activeElement.tagName) || "";
          if (/INPUT|TEXTAREA|SELECT|BUTTON/.test(tag) || document.activeElement.isContentEditable) return;
          if (e.code === "Space" || e.key === "k") { e.preventDefault(); this.toggle(); }
          else if (e.key === "m") this.toggleMute();
          else if (e.key === "ArrowRight" && e.shiftKey) this.next();
          else if (e.key === "ArrowLeft" && e.shiftKey) this.prev();
          else if (e.key === "ArrowRight") this.seekBy(10);
          else if (e.key === "ArrowLeft") this.seekBy(-10);
          else if (e.key === "Escape") this.panel = "";
        });
      },
    });
  });

  /** YouTube IFrame API ustidagi dvigatel: HTMLAudioElement'ning pleyer ishlatadigan qismini takrorlaydi. */
  function createYouTubeEngine() {
    const listeners = {};
    let player = null, apiReady = null, loadedId = "", id = "", state = -1, timer = null, metaSent = false;
    let vol = 1, mute = false, rate = 1;
    const emit = (type) => (listeners[type] || []).slice().forEach((fn) => fn());
    const box = () => {
      let el = document.getElementById("wcd-yt");
      if (!el) {
        el = document.createElement("div");
        el.id = "wcd-yt";
        el.innerHTML = '<div id="wcd-yt-frame"></div>';
        document.body.appendChild(el);
      }
      return el;
    };
    const api = () => apiReady || (apiReady = new Promise((resolve, reject) => {
      if (window.YT && window.YT.Player) return resolve();
      const prev = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = () => { if (prev) prev(); resolve(); };
      const s = document.createElement("script");
      s.src = "https://www.youtube.com/iframe_api";
      s.onerror = () => reject(new Error("YouTube API"));
      document.head.appendChild(s);
      // Sekin tarmoq yoki bloklovchi kengaytma: 15 soniyada yuklanmasa, keyingi bosishda qayta urinadi
      setTimeout(() => reject(new Error("YouTube API timeout")), 15000);
    }).catch((e) => { apiReady = null; box().classList.remove("is-on"); emit("error"); throw e; }));
    const startTimer = () => { clearInterval(timer); timer = setInterval(() => emit("timeupdate"), 250); };
    const stopTimer = () => { clearInterval(timer); emit("timeupdate"); };
    function onState(s) {
      state = s;
      if (s === 1) {
        if (!metaSent) { metaSent = true; emit("loadedmetadata"); }
        emit("play"); emit("playing"); startTimer();
      } else if (s === 2) { stopTimer(); emit("pause"); }
      else if (s === 0) { stopTimer(); emit("ended"); }
      else if (s === 3) emit("waiting");
    }
    function apply() {
      if (!player || !player.setVolume) return;
      player.setVolume(Math.round(vol * 100));
      mute ? player.mute() : player.unMute();
      if (player.setPlaybackRate) player.setPlaybackRate(rate);
    }
    function load() {
      box().classList.add("is-on");
      return api().then(() => new Promise((resolve) => {
        if (player) {
          if (loadedId !== id) { loadedId = id; metaSent = false; player.loadVideoById(id); } else player.playVideo();
          apply();
          return resolve();
        }
        loadedId = id;
        player = new YT.Player("wcd-yt-frame", {
          width: "100%", height: "100%", videoId: id,
          playerVars: { autoplay: 1, playsinline: 1, rel: 0, modestbranding: 1 },
          events: {
            onReady: () => { apply(); player.playVideo(); resolve(); },
            onStateChange: (e) => onState(e.data),
            onError: () => { stopTimer(); emit("error"); },
          },
        });
      }));
    }
    return {
      addEventListener(type, fn, opts) {
        const list = (listeners[type] = listeners[type] || []);
        const wrapped = opts && opts.once ? () => { list.splice(list.indexOf(wrapped), 1); fn(); } : fn;
        list.push(wrapped);
      },
      get src() { return id ? `yt:${id}` : ""; },
      set src(v) { id = String(v || "").replace(/^yt:/, ""); },
      play() { return id ? load() : Promise.reject(new Error("no video")); },
      pause() { if (player && player.pauseVideo) player.pauseVideo(); },
      hide() { this.pause(); const el = document.getElementById("wcd-yt"); if (el) el.classList.remove("is-on"); },
      get paused() { return state !== 1 && state !== 3; },
      get currentTime() { return player && player.getCurrentTime ? player.getCurrentTime() || 0 : 0; },
      set currentTime(t) { if (player && player.seekTo) player.seekTo(t, true); },
      get duration() { const d = player && player.getDuration ? player.getDuration() : 0; return d || NaN; },
      get buffered() { return { length: 0 }; },
      get volume() { return vol; }, set volume(v) { vol = v; apply(); },
      get muted() { return mute; }, set muted(v) { mute = !!v; apply(); },
      get playbackRate() { return rate; }, set playbackRate(v) { rate = v || 1; apply(); },
    };
  }

  // Boshqa (eski) audio elementlari o'ynasa, global pleyer to'xtaydi
  document.addEventListener("wcd-audio-play", (e) => { if (e.detail !== audio) audio.pause(); });

  /** Sahifadagi JSON'dan treklar ro'yxati: <script type="application/json" id="..."> */
  window.wcdTracks = function (id) {
    const el = document.getElementById(id);
    try { return el ? JSON.parse(el.textContent) : []; } catch (e) { return []; }
  };
})();
