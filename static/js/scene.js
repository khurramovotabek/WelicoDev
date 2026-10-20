/* Protsedural tungi tog' manzarasi (rasm yuklanmagan sahifalar uchun fon).
   Bir marta chiziladi, faqat o'lcham yoki mavzu o'zgarganda qayta chiziladi. */
(function () {
  const canvas = document.getElementById("scene-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  const PALETTES = {
    dark: {
      sky: ["#070d24", "#13234f", "#2f4a86", "#7d86b3", "#e8a978"],
      glow: "rgba(255,186,140,0.38)",
      stars: true,
      far: ["#5d75ad", "#2b3f72"],
      snow: "rgba(220,232,255,0.55)",
      mid: ["#22335f", "#141f42"],
      near: ["#0e1733", "#080e22"],
      fog: "rgba(160,180,230,0.10)",
      lights: true,
      cloud: "rgba(190,205,240,0.10)",
    },
    light: {
      sky: ["#8fb2ea", "#a9c4f0", "#c9daf6", "#e8eefb", "#fbe2c8"],
      glow: "rgba(255,230,190,0.6)",
      stars: false,
      far: ["#a7bce4", "#8ea6d6"],
      snow: "rgba(255,255,255,0.85)",
      mid: ["#7d95c8", "#6a82b8"],
      near: ["#4d6399", "#3a4f83"],
      fog: "rgba(255,255,255,0.28)",
      lights: false,
      cloud: "rgba(255,255,255,0.45)",
    },
  };

  // Har safar bir xil manzara chiqishi uchun urug'li tasodifiy son generatori
  function rng(seed) {
    let s = seed >>> 0;
    return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
  }

  function ridge(rand, w, base, amp, rough, steps) {
    const pts = [];
    let y = base;
    for (let i = 0; i <= steps; i++) {
      const x = (i / steps) * w;
      y += (rand() - 0.5) * amp * rough;
      y = base + (y - base) * 0.82 + Math.sin(i * 0.35 + rand()) * amp * 0.18;
      pts.push([x, y]);
    }
    return pts;
  }

  function drawRange(pts, w, h, colors, snow) {
    const g = ctx.createLinearGradient(0, Math.min(...pts.map((p) => p[1])), 0, h);
    g.addColorStop(0, colors[0]);
    g.addColorStop(1, colors[1]);
    ctx.beginPath();
    ctx.moveTo(0, h);
    pts.forEach(([x, y]) => ctx.lineTo(x, y));
    ctx.lineTo(w, h);
    ctx.closePath();
    ctx.fillStyle = g;
    ctx.fill();
    if (snow) {
      ctx.save();
      ctx.clip();
      ctx.strokeStyle = snow;
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y + 1) : ctx.moveTo(x, y + 1)));
      ctx.stroke();
      // Cho'qqilardagi qor
      const top = Math.min(...pts.map((p) => p[1]));
      const sg = ctx.createLinearGradient(0, top, 0, top + 70);
      sg.addColorStop(0, snow);
      sg.addColorStop(1, "rgba(255,255,255,0)");
      ctx.fillStyle = sg;
      ctx.fillRect(0, top, w, 70);
      ctx.restore();
    }
  }

  function pine(x, y, s, color) {
    ctx.fillStyle = color;
    ctx.beginPath();
    for (let i = 0; i < 5; i++) {
      const ty = y - s * (0.25 + i * 0.19);
      const half = s * 0.23 * (1 - i * 0.17);
      ctx.moveTo(x, ty - s * 0.22);
      ctx.lineTo(x - half, ty + s * 0.08);
      ctx.lineTo(x + half, ty + s * 0.08);
    }
    ctx.fill();
    ctx.fillRect(x - s * 0.02, y - s * 0.25, s * 0.04, s * 0.25);
  }

  function draw() {
    const theme = document.documentElement.dataset.theme === "light" ? "light" : "dark";
    const P = PALETTES[theme];
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = window.innerWidth;
    const h = window.innerHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const rand = rng(20260819);

    // Osmon
    const sky = ctx.createLinearGradient(0, 0, 0, h);
    P.sky.forEach((c, i) => sky.addColorStop(i / (P.sky.length - 1) * 0.72, c));
    ctx.fillStyle = sky;
    ctx.fillRect(0, 0, w, h);

    // Ufqdagi quyosh botishi nuri (o'ng tomonda, dizayndagidek)
    const gx = w * 0.82, gy = h * 0.52;
    const glow = ctx.createRadialGradient(gx, gy, 0, gx, gy, Math.max(w, h) * 0.55);
    glow.addColorStop(0, P.glow);
    glow.addColorStop(1, "rgba(255,190,140,0)");
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, w, h);

    // Yulduzlar
    if (P.stars) {
      for (let i = 0; i < Math.round((w * h) / 5200); i++) {
        const x = rand() * w, y = rand() * h * 0.5;
        const r = rand() * 1.1 + 0.2;
        ctx.globalAlpha = 0.25 + rand() * 0.6 * (1 - y / (h * 0.5));
        ctx.fillStyle = "#fff";
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
    }

    // Bulutlar
    ctx.filter = "blur(28px)";
    for (let i = 0; i < 9; i++) {
      ctx.fillStyle = P.cloud;
      ctx.beginPath();
      ctx.ellipse(rand() * w, h * (0.28 + rand() * 0.22), 120 + rand() * 260, 26 + rand() * 40, 0, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.filter = "none";

    // Tog'lar: uzoq (qorli), o'rta, yaqin
    drawRange(ridge(rand, w, h * 0.58, 90, 1.5, 48), w, h, P.far, P.snow);
    ctx.fillStyle = P.fog;
    ctx.fillRect(0, h * 0.6, w, h * 0.1);
    const mid = ridge(rand, w, h * 0.7, 55, 1.2, 60);
    drawRange(mid, w, h, P.mid);

    // Vodiydagi shahar chiroqlari
    if (P.lights) {
      for (let i = 0; i < Math.round(w / 2.2); i++) {
        const x = w * 0.18 + rand() * w * 0.64;
        const y = h * 0.74 + rand() * h * 0.08;
        ctx.fillStyle = rand() > 0.3 ? "rgba(255,206,140,0.85)" : "rgba(170,205,255,0.8)";
        ctx.globalAlpha = 0.35 + rand() * 0.6;
        ctx.fillRect(x, y, 1.4, 1.4);
      }
      ctx.globalAlpha = 1;
      const city = ctx.createRadialGradient(w * 0.5, h * 0.78, 0, w * 0.5, h * 0.78, w * 0.4);
      city.addColorStop(0, "rgba(255,190,120,0.16)");
      city.addColorStop(1, "rgba(255,190,120,0)");
      ctx.fillStyle = city;
      ctx.fillRect(0, h * 0.6, w, h * 0.4);
    }

    drawRange(ridge(rand, w, h * 0.86, 30, 1, 40), w, h, P.near);

    // Chetlardagi archalar
    const treeColor = P.near[1];
    for (let i = 0; i < 26; i++) {
      const side = i % 2 === 0;
      const x = side ? rand() * w * 0.16 : w - rand() * w * 0.16;
      pine(x, h + 4, 80 + rand() * 170, treeColor);
    }

    // Pastki qism qorong'ilashadi, kontent o'qilishi uchun
    const shade = ctx.createLinearGradient(0, h * 0.55, 0, h);
    shade.addColorStop(0, "rgba(0,0,0,0)");
    shade.addColorStop(1, theme === "dark" ? "rgba(4,8,22,0.55)" : "rgba(220,230,250,0.35)");
    ctx.fillStyle = shade;
    ctx.fillRect(0, 0, w, h);
  }

  let t;
  window.addEventListener("resize", () => {
    clearTimeout(t);
    t = setTimeout(draw, 150);
  });
  document.addEventListener("themechange", draw);
  draw();
})();
