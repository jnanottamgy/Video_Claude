/* demo.js — SHELF CAMPUS demo scene (full, 32.100 -> 45.500 output s, 402 frames @30).
   Every pixel is a pure function of composition time t (= output s - 32.1): one paused GSAP timeline holds a
   single linear driver whose setter calls render(t). No clocks, no Math.random (seeded mulberry32), so frames
   seek in any order and render identically. Layout is authored in constants; nothing is measured at runtime. */
(function () {
  "use strict";

  var DUR = 13.4;
  var FPS = 30;
  var W0 = 32.1; // window start (output seconds)

  /* ================= math ================= */
  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
  function lerp(a, b, u) { return a + (b - a) * u; }
  function prog(t, t0, d) { return d <= 0 ? (t >= t0 ? 1 : 0) : clamp((t - t0) / d, 0, 1); }
  function sstep(a, b, x) { var u = clamp((x - a) / (b - a), 0, 1); return u * u * (3 - 2 * u); }
  var pe = function (s) { return gsap.parseEase(s); };
  var EO = pe("expo.out"), P2O = pe("power2.out"), P2I = pe("power2.in"), P2IO = pe("power2.inOut");
  var P3O = pe("power3.out"), P3I = pe("power3.in"), P3IO = pe("power3.inOut"), P4O = pe("power4.out");
  var BO = pe("back.out(1.7)"), BO2 = pe("back.out(2.4)"), BO1 = pe("back.out(1.2)");
  var TAU = Math.PI * 2;
  // closed-form underdamped spring displacement: 1 at d = 0, settles to 0 (native-notification-pop law)
  function spring(d, w, z) {
    if (d <= 0) return 1;
    var wd = w * Math.sqrt(1 - z * z);
    return Math.exp(-z * w * d) * (Math.cos(wd * d) + ((z * w) / wd) * Math.sin(wd * d));
  }
  // a decaying vibration (phone ring / banner shake)
  function buzz(d, hz, tau) { return d < 0 || d > 6 * tau ? 0 : Math.sin(TAU * hz * d) * Math.exp(-d / tau); }
  // deterministic three-frame impact shake (headline-slam): [dx, dy]
  function shake3(t, t0, amp) {
    var d = t - t0;
    if (d < 0 || d >= 3 / FPS) return null;
    var f = Math.floor(d * FPS + 1e-6);
    return f === 0 ? [amp, -amp * 0.55] : f === 1 ? [-amp * 0.7, amp * 0.4] : [amp * 0.25, -amp * 0.15];
  }
  function rng(seed) {
    var a = seed >>> 0;
    return function () {
      a = (a + 0x6d2b79f5) >>> 0;
      var r = a;
      r = Math.imul(r ^ (r >>> 15), r | 1);
      r ^= r + Math.imul(r ^ (r >>> 7), r | 61);
      return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
    };
  }

  /* ================= cue sheet (composition seconds; every cue is the time of the frame it lands on) ================= */
  // the renderer's frame time can land a hair under k/30, so every cue sits 1 ms early: it shows on frame k, never k+1
  function F(out) { return Math.round((out - W0) * FPS + 1e-9) / FPS - 0.001; }
  function Fr(k) { return k / FPS - 0.001; } // a cue on composition frame k (0-based)
  function fk(tc) { return Math.round((tc + 0.001) * FPS); } // the frame a cue lands on
  var T = {
    wa: F(32.68), land: F(33.263), kb: F(33.847),
    got: F(34.0), notes: F(34.39), m1: F(34.43),
    just: F(35.11), shelf: F(35.43), m2: F(35.596), it: F(35.83),
    type3: F(36.179), need: F(36.33), them: F(36.61), m3: F(36.762), back: F(36.85),
    ask: F(37.49), m4: F(37.929),
    m5: F(38.512), deadlines: F(38.66),
    m6: F(39.678), handled: F(39.76), cardBack: F(40.261),
    m7: F(40.844), reminders: F(41.0),
    m8: F(41.428), sorted: F(41.89),
    banner: F(42.011), ring2: F(42.594),
    hit1: F(43.177), hit2: F(43.76), hit3: F(44.343), hit4: F(44.926)
  };
  T.strike = Fr(3); T.dropNew = Fr(7);
  T.zoom0 = T.wa + 0.06; T.zoom1 = 1.12;
  T.push0 = 1.7; T.push1 = 2.28;
  T.exitWA = 1.8;
  T.fly0 = T.m1 - 0.34;
  // SHELF starts typing a few frames after reading (header "typing…" + the dots bubble)
  T.ty1 = Fr(fk(T.m1) + 12); T.ty2 = Fr(fk(T.m3) + 9); T.ty3 = Fr(fk(T.m5) + 10); T.ty4 = Fr(fk(T.m7) + 7);
  T.type5 = Fr(fk(T.m5) - 11); T.type7 = Fr(fk(T.m7) - 13);
  T.cardOut = Fr(fk(T.m6) + 2);
  T.skip0 = Fr(fk(T.m8) + 3); T.skip1 = Fr(fk(T.sorted) + 1);
  T.whip = Fr(324);
  var BEATS = [32.097, 32.68, 33.263, 33.847, 34.43, 35.013, 35.596, 36.179, 36.762, 37.345, 37.929, 38.512, 39.095, 39.678, 40.261, 40.844, 41.428, 42.011, 42.594, 43.177, 43.76, 44.343, 44.926].map(function (b) { return b - W0; });
  var DOWN = [32.68, 35.013, 37.345, 39.678, 42.011, 44.343].map(function (b) { return b - W0; });
  window.__demoCues = T;

  /* ================= DOM helpers ================= */
  function $(id) { return document.getElementById(id); }
  function div(cls, html) { var d = document.createElement("div"); if (cls) d.className = cls; if (html) d.innerHTML = html; return d; }
  // cached style writes (skip identical values; every value is recomputed from t each frame)
  function st(e, p, v) { var c = e.__c || (e.__c = {}); if (c[p] !== v) { e.style[p] = v; c[p] = v; } }
  function dsp(e, on) { st(e, "display", on ? "block" : "none"); return on; } // containers: children may set visibility themselves
  function op(e, o) { // opacity + visibility; returns whether visible
    if (o <= 0.002) { st(e, "visibility", "hidden"); return false; }
    st(e, "visibility", "visible");
    st(e, "opacity", o >= 0.998 ? "1" : o.toFixed(3));
    return true;
  }
  function fx(px) { return px > 0.25 ? "blur(" + px.toFixed(1) + "px)" : "none"; }
  function txt(e, s) { if (e.__t !== s) { e.textContent = s; e.__t = s; } }
  function cls(e, name, on) { var k = "__k" + name; if (e[k] !== on) { e.classList.toggle(name, on); e[k] = on; } }

  /* ================= glyphs (hand-drawn inline SVG; no logos, no emoji) ================= */
  var W = "#fff";
  function ic(body) { return '<svg viewBox="0 0 48 48" fill="none" stroke="' + W + '" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">' + body + "</svg>"; }
  var APPS = [
    ic('<rect x="8" y="11" width="32" height="29" rx="5"/><path d="M8 19h32M16 7v8M32 7v8"/><circle cx="17" cy="27" r="1.6" fill="#fff"/><circle cx="24" cy="27" r="1.6" fill="#fff"/><circle cx="31" cy="27" r="1.6" fill="#fff"/><circle cx="17" cy="34" r="1.6" fill="#fff"/><circle cx="24" cy="34" r="1.6" fill="#fff"/>'),
    ic('<rect x="11" y="7" width="26" height="34" rx="4"/><path d="M17 16h14M17 23h14M17 30h9"/>'),
    ic('<path d="M6 15a4 4 0 0 1 4-4h9l4 4.5h15a4 4 0 0 1 4 4V34a4 4 0 0 1-4 4H10a4 4 0 0 1-4-4z"/>'),
    ic('<rect x="7" y="12" width="34" height="25" rx="4"/><path d="M8.5 14.5 24 26l15.5-11.5"/>'),
    ic('<path d="M8 17a4 4 0 0 1 4-4h4l3-4h10l3 4h4a4 4 0 0 1 4 4v17a4 4 0 0 1-4 4H12a4 4 0 0 1-4-4z"/><circle cx="24" cy="25" r="6.5"/>'),
    ic('<circle cx="24" cy="24" r="16"/><path d="M24 14v10l7 5"/>'),
    ic('<rect x="11" y="6" width="26" height="36" rx="5"/><rect x="16" y="11" width="16" height="7" rx="1.5" fill="#fff" stroke="none"/><path d="M17.5 25h.01M24 25h.01M30.5 25h.01M17.5 31h.01M24 31h.01M30.5 31h.01M17.5 37h.01M24 37h.01" stroke-width="4"/>'),
    ic('<path d="M19 33V12l18-4v21"/><circle cx="15" cy="33" r="4.5" fill="#fff"/><circle cx="33" cy="29" r="4.5" fill="#fff"/>'),
    ic('<path d="M15 36h19a8 8 0 0 0 1-15.9A11 11 0 0 0 14 22a7 7 0 0 0 1 14z"/>'),
    ic('<path d="M24 42s13-12.5 13-22a13 13 0 0 0-26 0c0 9.5 13 22 13 22z"/><circle cx="24" cy="20" r="4.5" fill="#fff"/>'),
    ic('<path d="M10 16h28M10 32h28"/><circle cx="18" cy="16" r="4.5" fill="#fff"/><circle cx="31" cy="32" r="4.5" fill="#fff"/>'),
    ic('<path d="M24 13c-4-3-9-4-15-3v26c6-1 11 0 15 3 4-3 9-4 15-3V10c-6-1-11 0-15 3zM24 13v26"/>'),
    ic('<path d="M24 9.6 45 19.2 24 28.8 3 19.2z" fill="#fff" stroke="none"/><path d="M11.6 23.9v7.4c0 3.6 5.6 6.5 12.4 6.5s12.4-2.9 12.4-6.5v-7.4L24 29.6z" fill="#fff" stroke="none"/>'),
    ic('<path d="M10 38h28"/><rect x="13" y="24" width="5" height="11" rx="1.5" fill="#fff" stroke="none"/><rect x="21.5" y="15" width="5" height="20" rx="1.5" fill="#fff" stroke="none"/><rect x="30" y="20" width="5" height="15" rx="1.5" fill="#fff" stroke="none"/>'),
    ic('<rect x="7" y="11" width="34" height="26" rx="6"/><path d="M21 18v12l10-6z" fill="#fff"/>'),
    ic('<path d="M24 8l4.9 10 11 1.6-8 7.8 1.9 11L24 33.2l-9.8 5.2 1.9-11-8-7.8 11-1.6z"/>'),
    ic('<path d="M10 14l3 3 5-6M10 26l3 3 5-6M23 15h15M23 27h15M23 37h15"/><circle cx="13.5" cy="37" r="2.4" fill="#fff" stroke="none"/>'),
    ic('<path d="M12 36l2-8 18-18 6 6-18 18zM28 14l6 6"/>'),
    ic('<circle cx="24" cy="24" r="16"/><ellipse cx="24" cy="24" rx="7" ry="16"/><path d="M8.5 19h31M8.5 29h31"/>'),
    ic('<rect x="7" y="10" width="34" height="28" rx="5"/><path d="M10 34l9-10 6 6 4-4 9 8"/><circle cx="31" cy="18" r="3" fill="#fff" stroke="none"/>'),
    ic('<path d="M24 8c-6 0-10 4.5-10 10.5V26l-3.5 5h27L34 26v-7.5C34 12.5 30 8 24 8zM20 35a4 4 0 0 0 8 0"/>'),
    ic('<path d="M9 12a4 4 0 0 1 4-4h22a4 4 0 0 1 4 4v15a4 4 0 0 1-4 4H20l-7 6v-6a4 4 0 0 1-4-4zM16 16h16M16 23h10"/>'),
    ic('<circle cx="24" cy="17" r="7"/><path d="M10 40c1.5-8 7-12 14-12s12.5 4 14 12"/>')
  ];
  var APP_BG = [
    ["#5d6684", "#3a405a"], ["#6e5c92", "#463a63"], ["#3f7c84", "#275257"], ["#8b6553", "#5b3f33"], ["#5f7a5a", "#3c5039"],
    ["#8a5b72", "#5a3a4b"], ["#4b6e9b", "#2f4a6c"], ["#6f7581", "#484d57"], ["#977a4c", "#67502f"], ["#3e5f75", "#273e4e"],
    ["#7b5179", "#4d3150"], ["#557089", "#36495c"], ["#6b6a8e", "#43425f"], ["#866a5e", "#59443b"], ["#4f7470", "#32504c"],
    ["#5b5f86", "#3a3d5c"], ["#7f6a49", "#55452e"], ["#5d7d8f", "#3b5563"], ["#74587e", "#4a3753"], ["#62708a", "#3f4a5f"],
    ["#8d6060", "#5c3c3c"], ["#566b80", "#364556"], ["#6c7f61", "#45553d"]
  ];
  var TAIL_OUT = '<svg class="tail" viewBox="0 0 16 25"><path d="M0 0h12.5c2.8 0 4.2 3.3 2.4 5.4L0 23.6z" fill="#005c4b"/></svg>';
  var TAIL_IN = '<svg class="tail" viewBox="0 0 16 25"><path d="M16 0H3.5C.7 0-.7 3.3 1.1 5.4L16 23.6z" fill="#202c33"/></svg>';
  var PDF = '<svg class="pdf" viewBox="0 0 33 40"><path d="M4 1h17.5L31 10.5V36a3 3 0 0 1-3 3H4a3 3 0 0 1-3-3V4a3 3 0 0 1 3-3z" fill="#e5534b"/><path d="M21.5 1v7.2a2.3 2.3 0 0 0 2.3 2.3H31z" fill="#f4a29d"/><path d="M7.4 32.2v-7.6h3.1a2.3 2.3 0 0 1 0 4.6H7.4M14.6 24.6v7.6h1.9c2.3 0 3.6-1.6 3.6-3.8s-1.3-3.8-3.6-3.8zM22.6 32.2v-7.6h4.1M22.6 28.3h3.5" fill="none" stroke="#fff" stroke-width="1.85" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  var TICKS = '<svg class="tk" viewBox="0 0 18 11"><path class="t1" d="M1.1 5.9l3.1 3.1 6.2-7.2"/><path class="t2" d="M7.6 7.7l1.3 1.3 6.2-7.2"/></svg>';
  var CHECK = '<svg class="gl" viewBox="0 0 32 32"><circle cx="16" cy="16" r="15" fill="#25d366"/><path class="ckp" d="M9.5 16.5l4.4 4.4 8.6-9.2" fill="none" stroke="#fff" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="0"/></svg>';
  var SHELFG = '<svg class="gl" viewBox="0 0 32 32"><rect x="3.5" y="3.5" width="25" height="25" rx="4.5" fill="none" stroke="#53bdeb" stroke-width="2.4"/><path d="M3.5 16h25" stroke="#53bdeb" stroke-width="2.4"/><rect x="7.6" y="6.8" width="3.4" height="7.6" rx="1" fill="#53bdeb"/><rect x="12.4" y="8" width="3.4" height="6.4" rx="1" fill="#53bdeb"/><rect x="17.4" y="19.2" width="3.4" height="7.6" rx="1" fill="#53bdeb"/><rect x="21.6" y="20.4" width="3.4" height="6.4" rx="1" fill="#53bdeb" transform="rotate(14 23.3 23.6)"/></svg>';
  var BELL = '<svg class="gl" viewBox="0 0 32 32"><path d="M16 4.5c-4.6 0-7.6 3.4-7.6 8v5.2l-2.6 3.8h20.4l-2.6-3.8v-5.2c0-4.6-3-8-7.6-8z" fill="#ffb74d"/><path d="M12.6 24.5a3.4 3.4 0 0 0 6.8 0z" fill="#ffb74d"/></svg>';
  var LOCK = '<svg viewBox="0 0 20 22"><rect x="3" y="9.5" width="14" height="11" rx="2.5" fill="#ffd279"/><path d="M6.5 9.5V7a3.5 3.5 0 0 1 7 0v2.5" fill="none" stroke="#ffd279" stroke-width="2"/></svg>';
  var CLOCKS = '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" fill="none" stroke="#8696a0" stroke-width="2"/><path d="M12 7v5.2l3.4 2" fill="none" stroke="#8696a0" stroke-width="2" stroke-linecap="round"/></svg>';
  var CALGRID = (function () {
    var s = '<svg viewBox="0 0 96 70" style="display:block;width:96px;height:70px">';
    for (var r = 0; r < 4; r++) for (var c = 0; c < 5; c++) {
      var x = 12 + c * 16, y = 8 + r * 15;
      if (r === 1 && c === 4) s += '<circle cx="' + (x + 4) + '" cy="' + (y + 4) + '" r="8.5" fill="#e5534b"/><rect x="' + x + '" y="' + y + '" width="8" height="8" rx="2" fill="#fff"/>';
      else s += '<rect x="' + x + '" y="' + y + '" width="8" height="8" rx="2" fill="' + (r === 3 && c > 2 ? "#e3e7ee" : "#c3cad6") + '"/>';
    }
    return s + "</svg>";
  })();
  var PAGE = '<div class="pg-tag">UNIT 3</div><div class="pg-h">DBMS · Normalization</div><div class="pg-l" style="width:92%"></div><div class="pg-l" style="width:78%"></div><div class="pg-l" style="width:86%"></div><div class="pg-row"><div class="pg-box"></div><div class="pg-box"></div><div class="pg-box"></div></div><div class="pg-l" style="width:70%"></div><div class="pg-l" style="width:88%"></div><div class="pg-l" style="width:64%"></div>';
  var MARK = '<img src="./assets/shelf-mark.png" alt="" />';
  var SHIFT = '<svg viewBox="0 0 24 24"><path d="M12 4 4 12.5h4.5V20h7v-7.5H20z" fill="none" stroke="#fff" stroke-width="1.8" stroke-linejoin="round"/></svg>';
  var DEL = '<svg viewBox="0 0 24 24"><path d="M8.5 5H20a1.5 1.5 0 0 1 1.5 1.5v11A1.5 1.5 0 0 1 20 19H8.5L2.5 12z" fill="none" stroke="#fff" stroke-width="1.8" stroke-linejoin="round"/><path d="M11 9l6 6M17 9l-6 6" stroke="#fff" stroke-width="1.8" stroke-linecap="round"/></svg>';
  var HI = {
    doc: '<svg viewBox="0 0 120 120" fill="none" stroke="#fff" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"><path d="M34 12h36l22 22v66a8 8 0 0 1-8 8H34a8 8 0 0 1-8-8V20a8 8 0 0 1 8-8z"/><path d="M70 12v16a6 6 0 0 0 6 6h16"/><path d="M42 60h36M42 76h36M42 92h20"/></svg>',
    search: '<svg viewBox="0 0 120 120" fill="none" stroke="#fff" stroke-linecap="round"><circle cx="52" cy="52" r="30" stroke-width="8"/><path d="M75 75l25 25" stroke-width="11"/><path d="M38 44a16 16 0 0 1 14-10" stroke-width="5" opacity=".7"/></svg>',
    cal: '<svg viewBox="0 0 120 120" fill="none" stroke="#fff" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"><rect x="16" y="24" width="88" height="80" rx="14"/><path d="M16 46h88M40 14v20M80 14v20"/><rect class="hday" x="62" y="62" width="24" height="24" rx="6" fill="#fff" stroke="none"/><path d="M34 66h.01M34 82h.01M48 66h.01M48 82h.01" stroke-width="8"/></svg>',
    stamp: '<svg viewBox="0 0 200 200"><defs><path id="hsRing" d="M100 100m-74 0a74 74 0 1 1 148 0a74 74 0 1 1-148 0"/></defs><circle cx="100" cy="100" r="94" fill="none" stroke="#25d366" stroke-width="7"/><circle cx="100" cy="100" r="86" fill="none" stroke="#25d366" stroke-width="2.5" opacity=".8"/><text font-family="Sora" font-weight="700" font-size="17" fill="#25d366" letter-spacing="2"><textPath href="#hsRing" textLength="452" lengthAdjust="spacing">SUBMITTED · ON TIME · SUBMITTED · ON TIME ·</textPath></text><circle cx="100" cy="100" r="58" fill="#25d366"/><path d="M73 101l18 18 37-40" fill="none" stroke="#fff" stroke-width="13" stroke-linecap="round" stroke-linejoin="round"/></svg>'
  };

  /* ================= build: background bokeh ================= */
  var bokeh = [];
  (function () {
    var R = rng(20261024), host = $("bokeh");
    for (var i = 0; i < 18; i++) {
      var sz = 24 + R() * 110, blue = R() < 0.72;
      var e = div("bok");
      e.style.width = sz.toFixed(0) + "px";
      e.style.height = sz.toFixed(0) + "px";
      e.style.background = "radial-gradient(circle, " + (blue ? "rgba(120,180,255,0.55)" : "rgba(220,232,255,0.5)") + " 0%, rgba(120,180,255,0) 70%)";
      host.appendChild(e);
      bokeh.push({ e: e, x: R() * 1080, y: R() * 1920, sz: sz, z: 0.25 + R() * 0.75, o: 0.08 + R() * 0.16, ph: R() * TAU });
    }
  })();

  /* ================= build: the app grid (5 x 5 around the WhatsApp badge, which IS the phone) ================= */
  var GRID = { cx: 540, cy: 1050, pitch: 186 };
  var apps = [];
  var newApp = null;
  (function () {
    var host = $("grid"), R = rng(4242), k = 0;
    for (var r = 0; r < 5; r++) for (var c = 0; c < 5; c++) {
      if (r === 2 && c === 2) continue; // the WhatsApp badge: drawn by the phone's screen (it becomes the phone)
      var x = GRID.cx + (c - 2) * GRID.pitch, y = GRID.cy + (r - 2) * GRID.pitch;
      var e = div("app");
      var isNew = r === 1 && c === 2;
      if (isNew) {
        e.className = "app newapp";
        e.innerHTML =
          '<svg class="dl" viewBox="0 0 48 48" fill="none" stroke-linecap="round" stroke-linejoin="round"><circle cx="24" cy="24" r="17" stroke="rgba(255,255,255,0.22)" stroke-width="3"/><circle cx="24" cy="24" r="17" stroke="#9fd0ff" stroke-width="3" stroke-dasharray="106.8" stroke-dashoffset="40" transform="rotate(-90 24 24)"/><path class="arr" d="M24 14v16M17.5 23.5 24 30l6.5-6.5" stroke="#fff" stroke-width="3.4"/></svg>' +
          '<div class="lbl">NEW APP</div>' +
          '<svg class="strike" viewBox="0 0 168 168"><path class="sk" d="M22 22 146 146" stroke="#ff3b30" stroke-width="14" stroke-linecap="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/></svg>';
        e.setAttribute("data-layout-allow-overflow", "");
      } else {
        var g = APP_BG[k % APP_BG.length];
        e.style.background = "linear-gradient(160deg, " + g[0] + " 0%, " + g[1] + " 100%)";
        e.innerHTML = APPS[k % APPS.length];
        k++;
      }
      host.appendChild(e);
      var dx = x - GRID.cx, dy = y - GRID.cy, len = Math.hypot(dx, dy) || 1;
      var a = { e: e, x: x, y: y, ux: dx / len, uy: dy / len, ring: Math.max(Math.abs(c - 2), Math.abs(r - 2)), sp: 0.85 + R() * 0.3, rot: (R() - 0.5) * 50, ph: R() * TAU, isNew: isNew };
      apps.push(a);
      if (isNew) { newApp = a; a.sk = e.querySelector(".sk"); a.arr = e.querySelector(".arr"); }
    }
  })();

  /* ================= build: phone edges (thickness) + side buttons ================= */
  (function () {
    var host = $("phEdges");
    host.style.position = "absolute"; host.style.left = "0px"; host.style.top = "0px"; host.style.width = "660px"; host.style.height = "1430px";
    host.style.transformStyle = "preserve-3d";
    var btns = [[-7, 300, 62], [-7, 410, 112], [-7, 545, 112], [659, 440, 172]];
    btns.forEach(function (b) {
      var e = div("ph-btn");
      e.style.left = b[0] + "px"; e.style.top = b[1] + "px"; e.style.height = b[2] + "px";
      e.style.transform = "translateZ(-7px)";
      host.appendChild(e);
    });
    for (var i = 1; i <= 5; i++) {
      var e = div("ph-edge");
      e.style.transform = "translateZ(" + -i * 3 + "px)";
      e.style.filter = "brightness(" + (1 - i * 0.1).toFixed(2) + ")";
      host.appendChild(e);
    }
  })();

  /* ================= build: the WhatsApp chat ================= */
  // content coordinates: y = 0 is the top of the chat area (screen y 200)
  var MS = {};
  var ORDER = [
    ["m1", "out", 282], ["ty1", "in", 64], ["m2", "in", 160], ["m3", "out", 62], ["ty2", "in", 64], ["m4", "in", 304],
    ["m5", "out", 102], ["ty3", "in", 64], ["m6", "in", 268], ["m7", "out", 102], ["ty4", "in", 64], ["m8", "in", 62]
  ];
  (function () {
    var y = 150, prevReal = null;
    ORDER.forEach(function (o) {
      var id = o[0], isTyp = id.indexOf("ty") === 0;
      if (isTyp) { MS[id] = { id: id, side: o[1], top: y, h: o[2], typing: true }; return; } // its reply takes the same slot
      MS[id] = { id: id, side: o[1], top: y, h: o[2] };
      y += o[2] + 14;
      prevReal = id;
    });
  })();
  function bubbleHTML(id) {
    switch (id) {
      case "m1":
        return '<div class="bub out doc" style="width:440px;height:282px">' + TAIL_OUT + '<div class="dprev"><div class="page">' + PAGE + '</div></div><div class="drow">' + PDF + '<div class="dn"><div class="fn">DBMS Unit 3.pdf</div><div class="fm">24 pages · PDF · 3.1 MB</div></div></div><div class="dfoot"><span class="tm">9:41 PM' + TICKS + "</span></div></div>";
      case "m2":
        return '<div class="bub in txt" style="width:404px;height:160px">' + TAIL_IN + '<div class="halo"></div><div class="ln">' + CHECK + '<span class="tx b">Shelved.</span></div><div class="ln">' + SHELFG + '<span class="tx">DBMS <span class="sep">›</span> Unit 3</span></div><div class="ln" style="height:58px"><div class="chip">' + MARK + 'saved to your shelf</div><span class="sp"></span><span class="tm">9:41 PM</span></div></div>';
      case "m3":
        return '<div class="bub out txt" style="width:522px;height:62px">' + TAIL_OUT + '<div class="ln"><span class="tx">Send me the DBMS notes</span><span class="sp"></span><span class="tm">9:41 PM' + TICKS + "</span></div></div>";
      case "m4":
        return '<div class="bub in doc" style="width:440px;height:304px">' + TAIL_IN + '<div class="halo"></div><div class="dprev"><div class="page">' + PAGE + '</div></div><div class="drow">' + PDF + '<div class="dn"><div class="fn">DBMS Unit 3.pdf</div><div class="fm">24 pages · PDF · 3.1 MB</div></div></div><div class="dcap"><span class="tx">Here you go.</span><span class="sp"></span><span class="tm">9:41 PM</span></div></div>';
      case "m5":
        return '<div class="bub out txt" style="width:338px;height:102px">' + TAIL_OUT + '<div class="ln"><span class="tx">DAA assignment due</span></div><div class="ln"><span class="tx">Friday, 5 PM</span><span class="sp"></span><span class="tm">9:42 PM' + TICKS + "</span></div></div>";
      case "m6":
        return '<div class="bub in" style="width:476px;height:268px;padding:8px">' + TAIL_IN + '<div class="halo"></div><div class="dcard" id="m6card"><div class="cal"><div class="cal-h">FRI</div>' + CALGRID + '</div><div class="dct"><div class="dc-t">DAA Assignment</div><div class="dc-w">' + CLOCKS + 'Fri · 5:00 PM</div><div class="tag"><i></i>due in 3 days</div></div></div><div class="ln" style="padding:0 12px;margin-top:12px"><span class="tx">I\'ll remind you Thursday night.</span></div><div class="ln" style="height:30px;justify-content:flex-end;padding:0 12px"><span class="tm" style="transform:none">9:42 PM</span></div></div>';
      case "m7":
        return '<div class="bub out txt" style="width:498px;height:102px">' + TAIL_OUT + '<div class="ln"><span class="tx">Remind me Monday at 8 AM</span></div><div class="ln"><span class="tx">to submit the lab record</span><span class="sp"></span><span class="tm">9:42 PM' + TICKS + "</span></div></div>";
      case "m8":
        return '<div class="bub in txt" style="width:526px;height:62px">' + TAIL_IN + '<div class="halo"></div><div class="ln">' + BELL + '<span class="tx">Done. Monday, 8:00 AM.</span><span class="sp"></span><span class="tm">9:42 PM</span></div></div>';
    }
    return '<div class="bub in typ">' + TAIL_IN + "<i></i><i></i><i></i></div>";
  }
  (function () {
    var host = $("chatContent");
    host.appendChild(div("chipday", "Today"));
    host.appendChild(div("e2e", LOCK + "Messages are end-to-end encrypted."));
    Object.keys(MS).forEach(function (id) {
      var m = MS[id];
      var e = div("msg " + m.side, bubbleHTML(id));
      e.id = id;
      e.style.top = m.top + "px";
      e.setAttribute("data-layout-allow-occlusion", "");
      host.appendChild(e);
      m.e = e;
      m.tk = e.querySelector(".tk");
      m.halo = e.querySelector(".halo");
      if (m.typing) m.dots = e.querySelectorAll(".typ i");
    });
    // the chat scrolls under the header / input bar and is clipped by #chat: the audit reads boxes, not pixels
    host.querySelectorAll("*").forEach(function (n) { n.setAttribute("data-layout-allow-overlap", ""); n.setAttribute("data-layout-allow-occlusion", ""); });
    host.querySelectorAll(".page, .page *").forEach(function (n) { n.setAttribute("data-layout-ignore", ""); });
    MS.m2.chip = MS.m2.e.querySelector(".chip");
    MS.m2.ck = MS.m2.e.querySelector(".ckp");
    MS.m6.card = $("m6card");
  })();
  // message timing
  MS.m1.t = T.m1; MS.m2.t = T.m2; MS.m3.t = T.m3; MS.m4.t = T.m4; MS.m5.t = T.m5; MS.m6.t = T.m6; MS.m7.t = T.m7; MS.m8.t = T.m8;
  MS.ty1.t = T.ty1; MS.ty1.end = T.m2; MS.ty2.t = T.ty2; MS.ty2.end = T.m4; MS.ty3.t = T.ty3; MS.ty3.end = T.m6; MS.ty4.t = T.ty4; MS.ty4.end = T.m8;
  // read receipts on the user's messages: delivered at +0.12 s, read (blue) as SHELF starts typing
  MS.m1.read = T.ty1 - 3 / FPS; MS.m3.read = T.ty2 - 3 / FPS; MS.m5.read = T.ty3 - 3 / FPS; MS.m7.read = T.ty4 - 3 / FPS;
  var TYPWIN = [[T.ty1, T.m2], [T.ty2, T.m4], [T.ty3, T.m6], [T.ty4, T.m8]];
  // the chat's content bottom grows as items land (eased like WhatsApp's own list insert)
  var CB0 = 134;
  var CB_EV = ["m1", "ty1", "m2", "m3", "ty2", "m4", "m5", "ty3", "m6", "m7", "ty4", "m8"].map(function (id) { return [MS[id].t, MS[id].top + MS[id].h]; });
  function contentBottom(t) {
    var h = CB0;
    for (var i = 0; i < CB_EV.length; i++) {
      var t0 = CB_EV[i][0] - 0.03;
      if (t < t0) break;
      h = lerp(h, CB_EV[i][1], EO(prog(t, t0, 0.34)));
    }
    return h;
  }

  /* ================= build: keyboard ================= */
  var KEYS = {};
  var KB_Y = [84, 172, 260, 348];
  (function () {
    var host = $("kbKeys");
    function key(id, label, x, y, w, fn) {
      var e = div("key" + (fn ? " fn" : ""));
      e.style.left = x + "px"; e.style.top = y + "px"; e.style.width = w + "px";
      e.innerHTML = label;
      host.appendChild(e);
      KEYS[id] = { e: e, x: x, y: y, w: w };
    }
    var rows = ["qwertyuiop", "asdfghjkl", "zxcvbnm"];
    var x0 = [10, 41, 103];
    rows.forEach(function (r, ri) {
      for (var i = 0; i < r.length; i++) key(r[i], r[i], x0[ri] + i * 62, KB_Y[ri], 52, false);
    });
    key("shift", SHIFT, 10, KB_Y[2], 74, true);
    key("del", DEL, 546, KB_Y[2], 74, true);
    key("123", "123", 10, KB_Y[3], 124, true);
    key(" ", "space", 144, KB_Y[3], 342, false);
    key("ret", "return", 496, KB_Y[3], 124, true);
    KEYS[" "].e.style.fontSize = "24px";
  })();
  var kpop = $("kpop");
  $("kb").querySelectorAll("*").forEach(function (n) { n.setAttribute("data-layout-allow-occlusion", ""); n.setAttribute("data-layout-allow-overlap", ""); });

  // typed strings: prefix widths (Inter 400 @ 29 px, measured offline) let the field scroll to keep the caret in view
  var TYPED = [
    { s: "Send me the DBMS notes", t0: T.type3, t1: T.m3 - 0.06, send: T.m3,
      pw: [0, 18.6, 35.5, 52.6, 70.4, 78.6, 104, 120.9, 129, 138.5, 155.7, 172.6, 180.7, 201.7, 220.6, 246.8, 265.4, 273.6, 290.7, 308.1, 317.6, 334.2, 349.5] },
    { s: "DAA assignment due Friday, 5 PM", t0: T.type5, t1: T.m5 - 0.05, send: T.m5,
      pw: [0, 20.9, 39.9, 60.4, 68.5, 84.8, 100.1, 115.4, 122.5, 140.2, 157.4, 182.8, 199.7, 216.8, 226.3, 234.5, 252.2, 269.4, 286.3, 294.4, 311.6, 321.6, 328.9, 346.7, 363, 378.8, 385.9, 394.1, 411.3, 419.4, 438, 464.2] },
    { s: "Remind me Monday at 8 AM to submit the lab record", t0: T.type7, t1: T.m7 - 0.05, send: T.m7,
      pw: [0, 18.7, 35.1, 60.5, 67.6, 84.7, 102.5, 110.6, 136, 152.9, 161.1, 187.3, 204.7, 221.8, 239.6, 255.8, 271.7, 279.9, 296.2, 305.6, 313.8, 331.7, 339.9, 359.9, 386.1, 394.3, 403.7, 420.9, 429, 444.3, 461.5, 479.2, 504.6, 511.6, 521.1, 529.3, 538.8, 555.9, 572.8, 581, 588, 604.3, 622.1, 630.2, 641.1, 657.6, 674.1, 691.5, 702.4, 719.7] }
  ];

  /* ================= build: things that leave the screen ================= */
  var fly = $("fly");
  fly.innerHTML = PAGE + '<svg class="fbadge" viewBox="0 0 33 40">' + PDF.replace('<svg class="pdf" viewBox="0 0 33 40">', "").replace("</svg>", "") + "</svg>";
  fly.style.width = "384px"; fly.style.height = "497px"; fly.style.padding = "18px 22px"; fly.style.borderRadius = "6px";
  var popCard = $("popCard");
  popCard.innerHTML = MS.m6.card.outerHTML.replace('id="m6card"', "");
  var banner = $("banner");
  banner.innerHTML =
    '<div class="wa-card" style="--wa-w:860px;--wa-h:156px" data-layout-allow-overflow><div class="wa-fly"><div class="wa-banner">' +
    '<div class="wa-av shelfav">' + MARK + '<div class="wa-badge">' + WA.G.wa() + "</div></div>" +
    '<div class="wa-txt"><div class="wa-row"><div class="wa-title">SHELF Campus</div><div class="wa-time">now</div></div>' +
    '<div class="wa-row"><div class="wa-body">Reminder: submit the lab record</div></div></div>' +
    '<div class="wa-fx"><div class="wa-sheen" id="bsheen"></div></div></div><div class="wa-glow" id="bglow"></div></div></div>';
  var bsheen = $("bsheen"), bglow = $("bglow");
  var BAN_Y = 236; // banner centre, phone-local: just under the status bar, over the header
  var rings = [];
  (function () {
    var host = $("rings");
    host.style.position = "absolute"; host.style.left = "0px"; host.style.top = "0px";
    host.style.transformStyle = "preserve-3d";
    for (var i = 0; i < 4; i++) { var e = div("ring"); host.appendChild(e); rings.push(e); }
  })();
  $("badgeGlyph").innerHTML = WA.G.wa();

  /* ================= build: kinetic words ================= */
  var BIG_Y = 452, LEAD_Y = 322, LEAD_SIZE = 70;
  var LINES = [ // [text, onset frame time, entrance, style]; toLead / exit = the onset that displaces the line
    { size: 128, words: [["NO NEW APP.", -0.04, "slam"]], exit: T.wa, ex: "scale", shake: [0, 9] },
    { size: 150, words: [["JUST", T.wa, "drop"]], lead0: true, exit: T.exitWA },
    { size: 140, words: [["WHATSAPP.", T.wa, "slam", "green"]], exit: T.exitWA, shake: [T.wa, 10], sweep: T.wa + 0.08 },
    { size: 150, words: [["GOT", T.got, "rise"]], toLead: T.notes, exit: T.just },
    { size: 160, words: [["NOTES?", T.notes, "slam"]], exit: T.just, shake: [T.notes, 8] },
    { size: 150, words: [["JUST", T.just, "snapL"]], toLead: T.shelf, exit: T.need },
    { size: 160, words: [["SHELF", T.shelf, "slam", "blue"], ["IT.", T.it, "snapR"]], widths: [507.4, 725.6], exit: T.need, shake: [T.shelf, 8], sweep: T.shelf + 0.06 },
    { size: 150, words: [["NEED", T.need, "rise"], ["THEM", T.them, "rise"]], widths: [427.1, 908.3], toLead: T.back, exit: T.ask },
    { size: 170, words: [["BACK?", T.back, "slam"]], exit: T.ask, shake: [T.back, 8] },
    { size: 200, words: [["ASK.", T.ask, "punch", "blue"]], exit: T.deadlines, shake: [T.ask, 12], sweep: T.ask + 0.1 },
    { size: 140, words: [["DEADLINES.", T.deadlines, "snapR"]], toLead: T.handled, exit: T.reminders },
    { size: 150, words: [["HANDLED.", T.handled, "slam"]], exit: T.reminders, shake: [T.handled, 9] },
    { size: 136, words: [["REMINDERS.", T.reminders, "rise"]], toLead: T.sorted, exit: 99 },
    { size: 160, words: [["SORTED.", T.sorted, "slam"]], exit: 99, shake: [T.sorted, 9] }
  ];
  var ATK = 0.03, EXD = 0.067, LEADPRE = 0.12;
  (function () {
    var host = $("words");
    LINES.forEach(function (L) {
      var e = div("wl");
      e.setAttribute("data-layout-allow-occlusion", "");
      e.style.fontSize = L.size + "px";
      e.style.top = -L.size / 2 + "px";
      L.ws = [];
      L.words.forEach(function (w, i) {
        if (i > 0) e.appendChild(document.createTextNode(" "));
        var s = document.createElement("span");
        s.className = "ww" + (w[3] ? " " + w[3] : "");
        s.textContent = w[0];
        e.appendChild(s);
        L.ws.push(s);
      });
      L.e = e;
      L.green = L.words[0][3] === "green";
      L.t0 = L.words[0][1] - ATK;
      if (L.sweep !== undefined) L.ws.forEach(function (s) {
        var base = s.className.indexOf("green") >= 0 ? "linear-gradient(180deg, #c6ffda 0%, #52e384 44%, #1fbf5a 100%)" : "linear-gradient(180deg, #ffffff 0%, #cfe6ff 34%, #6cb0ff 100%)";
        if (s.className.indexOf("green") < 0 && s.className.indexOf("blue") < 0) base = "linear-gradient(180deg, #ffffff 0%, #eef3fa 42%, #b4c3d8 100%)";
        s.style.backgroundImage = "linear-gradient(100deg, rgba(255,255,255,0) 38%, rgba(255,255,255,0.95) 50%, rgba(255,255,255,0) 62%), " + base;
        s.style.backgroundSize = "260% 100%, 100% 100%";
        s.style.backgroundRepeat = "no-repeat";
        s.style.backgroundPosition = "130% 0, 0 0";
      });
      host.appendChild(e);
    });
  })();
  function wordPose(kind, t, onset) {
    var t0 = onset - ATK;
    var o = { x: 0, y: 0, s: 1, r: 0, b: 0, a: 0 };
    if (t < t0) return o;
    o.a = clamp((t - t0) / 0.03, 0, 1);
    var p, e;
    if (kind === "slam") { p = prog(t, t0, 0.32); e = EO(p); o.s = lerp(1.36, 1, e); o.b = 12 * (1 - e); }
    else if (kind === "rise") { p = prog(t, t0, 0.34); e = EO(p); o.y = lerp(95, 0, e); o.b = 10 * (1 - e); }
    else if (kind === "drop") { p = prog(t, t0, 0.3); e = EO(p); o.y = lerp(-85, 0, e); o.b = 9 * (1 - e); }
    else if (kind === "snapL") { p = prog(t, t0, 0.3); e = EO(p); o.x = lerp(-330, 0, e); o.b = 12 * (1 - e); }
    else if (kind === "snapR") { p = prog(t, t0, 0.3); e = EO(p); o.x = lerp(330, 0, e); o.b = 12 * (1 - e); }
    else if (kind === "punch") { p = prog(t, t0, 0.4); e = EO(p); o.s = lerp(2.3, 1, e); o.r = lerp(-10, 0, BO1(p)); o.b = 18 * (1 - e); }
    return o;
  }

  /* ================= build: the four hits ================= */
  // each hit: a hard cut to a new framing + colour pop, one icon, the word huge, and the matching piece of the
  // demo (blurred, tilted, behind) so the recap reads as SHELF, not as stock type
  var HITS = [
    { t: T.hit1, t1: T.hit2, icon: "doc", tile: true, ix: 540, iy: 645, isz: 330, glyph: 196, irot: 0, words: [["SAVE IT.", 190, 990]], rot: 0,
      bg: "radial-gradient(75% 46% at 50% 34%, #2f74ff 0%, #133d96 30%, #081d4f 60%, #030a1d 100%)", burst: "rgba(120,190,255,0.75)",
      frag: { id: "m1", w: 440, h: 282, x: 540, y: 1440, s: 1.8, rx: 42, rz: -7, blur: 2.4, o: 0.62 } },
    { t: T.hit2, t1: T.hit3, icon: "search", tile: false, ix: 560, iy: 1110, isz: 330, glyph: 280, irot: 0, words: [["FIND IT.", 192, 745]], rot: 2.5,
      bg: "radial-gradient(80% 52% at 50% 58%, #7cbcff 0%, #3483ff 24%, #1749bd 54%, #0a2368 100%)", burst: "rgba(255,255,255,0.55)",
      frag: { id: "m4", w: 440, h: 304, x: 520, y: 1150, s: 1.3, rx: 22, rz: -5, blur: 1.8, o: 0.62 } },
    { t: T.hit3, t1: T.hit4, icon: "cal", tile: true, ix: 350, iy: 675, isz: 320, glyph: 188, irot: -8, words: [["TRACK IT.", 176, 1000]], rot: -4,
      bg: "radial-gradient(70% 44% at 38% 36%, #3d8bff 0%, #16397f 30%, #0a1838 60%, #04091a 100%)", burst: "rgba(140,200,255,0.7)",
      frag: { id: "card", w: 458, h: 168, x: 620, y: 1420, s: 1.85, rx: 40, rz: -9, blur: 2.2, o: 0.66 } },
    { t: T.hit4, t1: 99, icon: "stamp", tile: false, ix: 540, iy: 620, isz: 390, glyph: 390, irot: -12, words: [["ACTUALLY", 126, 930], ["SUBMIT IT.", 166, 1090]], rot: 0,
      bg: "radial-gradient(72% 44% at 50% 32%, #2fe07a 0%, #138a4b 24%, #073a25 52%, #020d08 100%)", burst: "rgba(90,255,160,0.75)",
      frag: { id: "banner", w: 860, h: 156, x: 540, y: 1450, s: 1.0, rx: 44, rz: 0, blur: 2.2, o: 0.55 } }
  ];
  function fragHTML(id) {
    var h;
    if (id === "card") h = MS.m6.card.outerHTML;
    else if (id === "banner") h = banner.innerHTML;
    else h = bubbleHTML(id);
    return h.replace(/ id="[^"]*"/g, "").replace('class="tk"', 'class="tk dlv read"');
  }
  (function () {
    var host = $("hits"), R = rng(777);
    HITS.forEach(function (h, i) {
      var e = div("hit");
      var bg = div("hbg"); bg.style.background = h.bg; e.appendChild(bg);
      var grp = div("hgrp"); e.appendChild(grp);
      // the demo fragment, deep in the frame
      var pp = div("hpersp"), fr = div("hfrag", fragHTML(h.frag.id));
      fr.style.left = h.frag.x - h.frag.w / 2 + "px"; fr.style.top = h.frag.y - h.frag.h / 2 + "px";
      fr.style.width = h.frag.w + "px"; fr.style.height = h.frag.h + "px";
      fr.setAttribute("data-layout-ignore", "");
      fr.querySelectorAll("*").forEach(function (n) { n.setAttribute("data-layout-ignore", ""); });
      pp.appendChild(fr); grp.appendChild(pp);
      h.fragE = fr;
      h.streaks = [];
      for (var k = 0; k < 7; k++) {
        var s = div("streak");
        var ang = (R() - 0.5) * 30 + (i % 2 ? 160 : -20), len = 260 + R() * 420;
        s.style.width = len.toFixed(0) + "px";
        grp.appendChild(s);
        h.streaks.push({ e: s, ang: ang, y: 300 + R() * 1300, len: len, d: R() * 0.12, sp: 2600 + R() * 1800 });
      }
      var burst = div("hburst");
      burst.style.left = h.ix - 450 + "px"; burst.style.top = h.iy - 450 + "px"; burst.style.width = "900px"; burst.style.height = "900px";
      burst.style.background = "radial-gradient(circle, " + h.burst + " 0%, rgba(0,0,0,0) 62%)";
      grp.appendChild(burst);
      var ring = div("hring");
      ring.style.left = h.ix - 200 + "px"; ring.style.top = h.iy - 200 + "px"; ring.style.width = "400px"; ring.style.height = "400px";
      ring.style.boxShadow = "0 0 0 5px " + (h.icon === "stamp" ? "rgba(90,255,160,0.85)" : "rgba(190,225,255,0.85)") + ", 0 0 40px " + (h.icon === "stamp" ? "rgba(37,211,102,0.6)" : "rgba(79,157,255,0.6)");
      grp.appendChild(ring);
      var icon = div("hicon" + (h.tile ? " tile" : ""));
      icon.style.left = h.ix - h.isz / 2 + "px"; icon.style.top = h.iy - h.isz / 2 + "px";
      icon.style.width = h.isz + "px"; icon.style.height = h.isz + "px";
      icon.innerHTML = HI[h.icon];
      var sv = icon.querySelector("svg");
      sv.style.width = h.glyph + "px"; sv.style.height = h.glyph + "px"; sv.style.display = "block";
      if (h.icon === "search") sv.style.filter = "drop-shadow(0 10px 24px rgba(5,20,70,0.55)) drop-shadow(0 0 30px rgba(255,255,255,0.35))";
      if (h.icon === "stamp") sv.style.filter = "drop-shadow(0 0 26px rgba(37,211,102,0.75)) drop-shadow(0 14px 30px rgba(0,0,0,0.5))";
      grp.appendChild(icon);
      h.ws = [];
      h.words.forEach(function (w) {
        var we = div("hword");
        we.textContent = w[0];
        we.style.fontSize = w[1] + "px"; we.style.top = w[2] - w[1] / 2 + "px";
        we.style.transformOrigin = "540px " + w[1] / 2 + "px";
        if (h.icon === "search") we.style.textShadow = "0 0 30px rgba(190,225,255,0.9), 0 10px 30px rgba(4,18,70,0.65)";
        if (h.icon === "stamp") we.style.textShadow = "0 0 34px rgba(79,157,255,0.8), 0 0 90px rgba(37,211,102,0.35), 0 8px 24px rgba(0,0,0,0.5)";
        grp.appendChild(we);
        h.ws.push(we);
      });
      host.appendChild(e);
      h.e = e; h.grp = grp; h.burstE = burst; h.ringE = ring; h.iconE = icon;
      h.day = icon.querySelector(".hday");
    });
  })();

  /* ================= phone + camera model ================= */
  var PCY = 1315;          // phone centre (layout)
  var EST = 0.84;          // establishing camera scale (pivot x 540, y 600, + 40 px down)
  var BWL = 333;           // the badge window, in phone-local px
  var KP = { x: 540, y: 1250 }; // pivot of the per-message push-ins
  var MSG_T = [T.m1, T.m2, T.m3, T.m4, T.m5, T.m6, T.m7, T.m8];
  function gridScale(t) { return lerp(1.1, 1, EO(prog(t, 0, 0.42))) * (1 + 0.014 * prog(t, 0.42, 0.3)); }
  function badgeSize(t) {
    var s = 140 * gridScale(t);
    if (t >= T.wa - 0.01) s *= 1 + 0.22 * Math.sin(Math.PI * prog(t, T.wa - 0.01, 0.14));
    return s;
  }
  function camState(t) {
    var u = P3IO(prog(t, T.push0, T.push1 - T.push0));
    var s1 = lerp(EST, 1, u), oy = lerp(40, 0, u);
    var k = 1;
    for (var i = 0; i < MSG_T.length; i++) { var d = t - (MSG_T[i] - 0.02); if (d > 0) k += 0.0135 * BO(prog(d, 0, 0.42)); }
    var wz = 1 + 1.15 * P3I(prog(t, T.whip, T.hit1 - T.whip));
    return { s1: s1, oy: oy, k: k, wz: wz, blur: 18 * P3I(prog(t, T.whip, T.hit1 - T.whip)) };
  }
  // the camera maps a layout point to the screen: X = a*x + tx, Y = a*y + ty
  function camMatrix(C, bx, by) {
    var a = C.s1 * C.k * C.wz;
    var tx1 = 540 * (1 - C.s1), ty1 = 600 * (1 - C.s1) + C.oy;
    var tx2 = C.k * tx1 + KP.x * (1 - C.k), ty2 = C.k * ty1 + KP.y * (1 - C.k);
    return { a: a, tx: C.wz * tx2 + bx * (1 - C.wz), ty: C.wz * ty2 + by * (1 - C.wz) };
  }
  function phoneState(t) {
    var P = { dx: 0, dy: 0, s: 1, rx: 5, ry: -7, rz: 0, wl: 630, hl: 1400, rr: 77, ov: 0, glow: 0, bz: 1, blur: 0 };
    if (t < T.zoom0) {
      var bsz = badgeSize(t);
      P.s = bsz / (BWL * EST);
      P.dy = (GRID.cy - 640) / EST + 600 - PCY;
      P.rx = 0; P.ry = 0;
      P.wl = P.hl = BWL; P.rr = BWL * 0.235; P.ov = 1; P.bz = 0;
      P.glow = 0.55 + 0.45 * Math.exp(-Math.max(0, t - T.wa) / 0.25) * (t >= T.wa ? 1 : 0);
      return P;
    }
    var s0 = badgeSize(T.zoom0) / (BWL * EST), dy0 = (GRID.cy - 640) / EST + 600 - PCY;
    if (t < T.zoom1) {
      var z = prog(t, T.zoom0, T.zoom1 - T.zoom0), g = P3IO(z);
      P.s = lerp(s0, 1.3, g);
      P.dy = lerp(dy0, 0, g);
      P.rx = 13 * g; P.ry = -24 * g; P.rz = -3 * Math.sin(Math.PI * z);
      var gw = P3IO(prog(t, T.zoom0, 0.4));
      P.wl = lerp(BWL, 630, gw); P.hl = lerp(BWL, 1400, gw); P.rr = lerp(BWL * 0.235, 77, gw);
      P.ov = 1 - sstep(0.3, 0.8, gw); P.bz = sstep(0.5, 0.92, gw);
      P.glow = P.ov;
      P.blur = 6 * Math.pow(Math.sin(Math.PI * z), 2);
      return P;
    }
    var d = t - T.zoom1, sp = spring(d, 9, 0.6);
    P.s = 1 + 0.3 * sp;
    P.rx = 5 + 8 * sp; P.ry = -7 - 17 * sp;
    var sw = sstep(T.zoom1, T.zoom1 + 0.9, t), q = t - 1.1;
    P.ry += sw * 2.6 * Math.sin((TAU * q) / 6.4);
    P.rx += sw * 1.1 * Math.sin((TAU * q) / 5.1 + 1);
    P.rz = sw * 0.5 * Math.sin((TAU * q) / 7.3 + 0.5);
    P.dy = sw * 7 * Math.sin((TAU * q) / 3.3);
    // the deadline card pops out: the phone turns to show the depth, then back
    var pop = sstep(T.m6, T.m6 + 0.35, t) * (1 - sstep(T.cardBack, T.cardBack + 0.4, t));
    P.ry -= 6 * pop; P.rx += 2 * pop;
    // the reminder rings: the phone vibrates
    var v = buzz(t - (T.banner + 0.08), 23, 0.13) + buzz(t - T.ring2, 23, 0.13);
    P.dx += 5 * v; P.rz += 0.7 * v;
    return P;
  }

  /* ================= chat state helpers ================= */
  var KB_IN0 = 1274, KB_IN1 = 748; // the input bar's top, keyboard down / up (screen px)
  function kbState(t) { return P3O(prog(t, T.kb, 0.36)); }
  function inputTop(t) { return lerp(KB_IN0, KB_IN1, kbState(t)); }
  function scrollAt(t) { return Math.max(0, contentBottom(t) + 12 - (inputTop(t) - 200)); }
  var DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  function skipClock(t) { // Tue 9:41 PM -> Mon 8:00 AM, spun
    var v = P3IO(prog(t, T.skip0, T.skip1 - T.skip0));
    var mins = 2 * 1440 + 21 * 60 + 41 + Math.round(7819 * v); // minutes since Sunday 00:00
    var day = Math.floor(mins / 1440) % 7, mm = mins % 1440, h = Math.floor(mm / 60), m = mm % 60;
    var h12 = h % 12 === 0 ? 12 : h % 12;
    return { day: DAYS[day], short: DAYS[day].slice(0, 3), hm: h12 + ":" + (m < 10 ? "0" : "") + m, speed: Math.sin(Math.PI * v) };
  }

  /* ================= element refs ================= */
  var E = {
    bloom: $("bloom"), beam: $("beam"), greenGlow: $("greenGlow"), grid: $("grid"), cam: $("cam"), stage3d: $("stage3d"), phone: $("phone"),
    phEdges: $("phEdges"), phBody: $("phBody"), badgeGlow: $("badgeGlow"), screen: $("screen"), ui: $("ui"), badgeOv: $("badgeOv"),
    badgeGlyph: $("badgeGlyph"), island: $("island"), glare: $("glare"), chat: $("chat"), chatContent: $("chatContent"), hdr: $("hdr"),
    stOn: $("stOn"), stTy: $("stTy"), inp: $("inp"), kb: $("kb"), ftrack: $("ftrack"), ftx: $("ftx"), caret: $("caret"), send: $("send"),
    icam: $("icam"), imic: $("imic"), dim: $("dim"), lock: $("lock"), lkDay: $("lkDay"), lkTime: $("lkTime"), clkTx: $("clkTx"),
    words: $("words"), hits: $("hits"), flash: $("flash"), bgfx: $("bgfx"), vig: $("vig")
  };

  /* ================= render ================= */
  function beatPulse(t) {
    var v = 0;
    for (var i = 0; i < BEATS.length; i++) { var d = t - BEATS[i]; if (d >= 0 && d < 0.6) v += Math.exp(-d / 0.16) * (DOWN.indexOf(BEATS[i]) >= 0 ? 1 : 0.55); }
    return v;
  }

  function renderBackground(t, C, M, P) {
    var bp = beatPulse(t);
    // bloom sits behind the phone's screen centre
    var cy = M.a * (PCY + P.dy) + M.ty, cx = M.a * 540 + M.tx;
    if (t < T.zoom0) { cx = 540; cy = GRID.cy; }
    st(E.bloom, "transform", "translate(" + (cx - 540).toFixed(1) + "px," + (cy - 1220).toFixed(1) + "px) scale(" + (0.92 + 0.06 * bp).toFixed(3) + ")");
    st(E.bloom, "opacity", (0.72 + 0.22 * Math.min(1, bp)).toFixed(3));
    st(E.beam, "transform", "rotate(" + (2.5 * Math.sin((TAU * t) / 9)).toFixed(2) + "deg)");
    // green glow behind the WhatsApp badge (grid + zoom), gone once the phone has settled
    var gg = (t < T.zoom0 ? 0.55 + 0.6 * Math.exp(-Math.max(0, t - T.wa) / 0.3) * (t >= T.wa ? 1 : 0) : 0.9 * (1 - sstep(T.zoom0, T.zoom1 + 0.25, t)));
    if (op(E.greenGlow, gg)) st(E.greenGlow, "transform", "translate(" + (cx - 540).toFixed(1) + "px," + (cy - 1050).toFixed(1) + "px) scale(" + (t < T.zoom0 ? 0.55 * gridScale(t) * (1 + 0.25 * Math.exp(-Math.max(0, t - T.wa) / 0.2) * (t >= T.wa ? 1 : 0)) : lerp(0.6, 1.6, sstep(T.zoom0, T.zoom1, t))).toFixed(3) + ")");
    for (var i = 0; i < bokeh.length; i++) {
      var b = bokeh[i];
      var y = b.y - t * 18 * b.z - (M.ty - 0) * 0.05 * b.z;
      y = ((y % 2100) + 2100) % 2100 - 90;
      var x = b.x + 14 * Math.sin(t * 0.5 + b.ph) + (M.tx * 0.04 * b.z);
      st(b.e, "transform", "translate(" + (x - b.sz / 2).toFixed(1) + "px," + (y - b.sz / 2).toFixed(1) + "px)");
      st(b.e, "opacity", (b.o * (0.8 + 0.2 * Math.sin(t * 1.3 + b.ph))).toFixed(3));
    }
  }

  function renderGrid(t, imp) {
    if (!dsp(E.grid, t <= T.wa + 0.85)) return;
    st(E.grid, "transform", imp ? "translate(" + imp[0] + "px," + imp[1] + "px)" : "none");
    var gs = gridScale(t);
    for (var i = 0; i < apps.length; i++) {
      var a = apps[i];
      var x = GRID.cx + (a.x - GRID.cx) * gs, y = GRID.cy + (a.y - GRID.cy) * gs + 3 * Math.sin(t * 5.6 + a.ph);
      var s = gs, r = 0, blur = 0, o = 1;
      if (a.isNew) {
        // the download arrow bobs; struck through on "NO NEW APP.", then it drops away
        st(a.arr, "transform", "translateY(" + (2.2 * Math.sin(t * 15)).toFixed(2) + "px)");
        a.sk.setAttribute("stroke-dashoffset", (1 - P3O(prog(t, T.strike, 0.1))).toFixed(3));
        var dp = prog(t, T.dropNew, 0.34), de = P2I(dp);
        y += 250 * de; x -= 30 * de; r = 28 * de; s *= 1 - 0.42 * de; blur = 7 * de; o = 1 - sstep(0.55, 1, dp);
        st(a.e, "filter", t >= T.strike + 0.04 ? "saturate(0.25) brightness(0.72)" + (blur > 0.3 ? " blur(" + blur.toFixed(1) + "px)" : "") : "none");
      } else if (t >= T.wa) {
        var u = prog(t, T.wa + 0.015 * a.ring, 0.78), e = P2O(u);
        x += a.ux * 1150 * a.sp * e; y += a.uy * 1150 * a.sp * e;
        s *= 1 + 1.05 * e; r = a.rot * e;
        blur = u > 0 && u < 1 ? Math.min(14, 20 * (1 - u) * (1 - u)) : 0;
        o = 1 - sstep(0.5, 1, u);
        st(a.e, "filter", fx(blur));
      }
      if (!op(a.e, o)) continue;
      st(a.e, "transform", "translate(" + (x - 70).toFixed(1) + "px," + (y - 70).toFixed(1) + "px) rotate(" + r.toFixed(2) + "deg) scale(" + s.toFixed(4) + ")");
    }
  }

  function renderPhone(t, C, M, P, shk) {
    if (!dsp(E.cam, t < T.hit1)) return;
    var tx = M.tx + (shk ? shk[0] : 0), ty = M.ty + (shk ? shk[1] : 0);
    st(E.cam, "transform", "translate(" + tx.toFixed(2) + "px," + ty.toFixed(2) + "px) scale(" + M.a.toFixed(5) + ")");
    st(E.cam, "filter", fx(Math.max(P.blur, C.blur)));
    st(E.stage3d, "perspectiveOrigin", "540px " + (PCY + P.dy).toFixed(1) + "px");
    st(E.phone, "transform", "translate3d(" + P.dx.toFixed(2) + "px," + P.dy.toFixed(2) + "px,0) rotateX(" + P.rx.toFixed(3) + "deg) rotateY(" + P.ry.toFixed(3) + "deg) rotateZ(" + P.rz.toFixed(3) + "deg) scale(" + P.s.toFixed(5) + ")");
    // the badge -> screen morph
    var morphing = P.wl < 629.9 || P.hl < 1399.9;
    st(E.screen, "clipPath", morphing ? "inset(" + ((1400 - P.hl) / 2).toFixed(2) + "px " + ((630 - P.wl) / 2).toFixed(2) + "px round " + P.rr.toFixed(2) + "px)" : "none");
    if (op(E.badgeOv, P.ov)) {
      st(E.badgeOv, "backgroundSize", P.wl.toFixed(1) + "px " + P.hl.toFixed(1) + "px");
      st(E.badgeOv, "backgroundPosition", ((630 - P.wl) / 2).toFixed(1) + "px " + ((1400 - P.hl) / 2).toFixed(1) + "px");
    }
    if (op(E.badgeGlyph, P.ov)) st(E.badgeGlyph, "transform", "scale(" + ((Math.min(P.wl, P.hl) * 0.74) / 100).toFixed(4) + ")");
    if (op(E.badgeGlow, P.glow * 0.85)) st(E.badgeGlow, "transform", "scale(" + ((P.wl / BWL) * 0.95).toFixed(3) + ")");
    op(E.phBody, P.bz); op(E.phEdges, P.bz); op(E.island, P.bz); op(E.glare, P.bz);
    st(E.glare, "transform", "translateX(" + (-P.ry * 22 + 40 * Math.sin(t * 0.4)).toFixed(1) + "px)");
  }

  function renderChat(t) {
    if (t >= T.hit1) return;
    var kb = kbState(t), inTop = lerp(KB_IN0, KB_IN1, kb);
    st(E.inp, "transform", "translateY(" + inTop.toFixed(2) + "px)");
    st(E.kb, "transform", "translateY(" + lerp(1400, 840, kb).toFixed(2) + "px)");
    st(E.kb, "visibility", kb > 0.001 ? "visible" : "hidden");
    var sc = scrollAt(t);
    st(E.chatContent, "transform", "translateY(" + (-sc).toFixed(2) + "px)");

    // messages
    for (var id in MS) {
      var m = MS[id], e = m.e;
      if (m.typing) {
        if (t < m.t - 0.02 || t >= m.end - 0.02) { st(e, "visibility", "hidden"); continue; }
        var du = prog(t, m.t - 0.02, 0.1);
        op(e, lerp(0.4, 1, P2O(du)));
        st(e, "transform", "scale(" + lerp(0.6, 1, P2O(du)).toFixed(4) + ")");
        for (var i = 0; i < 3; i++) {
          var b = 0.5 + 0.5 * Math.sin(TAU * 1.8 * (t - m.t) - i * 0.9);
          st(m.dots[i], "opacity", (0.35 + 0.65 * b).toFixed(3));
          st(m.dots[i], "transform", "translateY(" + (-4 * b).toFixed(2) + "px)");
        }
        continue;
      }
      var t0 = m.t - 0.02;
      if (t < t0) { st(e, "visibility", "hidden"); continue; }
      var d = t - t0, u = prog(d, 0, 0.26), sc2, yo = 0, a;
      if (id === "m1") { sc2 = lerp(0.94, 1, BO1(prog(d, 0, 0.24))); a = 1; }
      else if (m.side === "out") { sc2 = lerp(0.76, 1, BO1(u)); yo = 46 * (1 - EO(prog(d, 0, 0.24))); a = 0.55 + 0.45 * prog(d, 0, 0.06); }
      else { sc2 = lerp(0.72, 1, BO1(u)); a = 0.55 + 0.45 * prog(d, 0, 0.06); }
      if (id === "m6") { // while the card is out of the phone, its slot in the bubble is empty
        var away = sstep(T.cardOut - 0.01, T.cardOut + 0.05, t) * (1 - sstep(T.cardBack + 0.27, T.cardBack + 0.34, t));
        st(m.card, "opacity", (1 - away).toFixed(3));
      }
      op(e, a);
      st(e, "transform", "translateY(" + yo.toFixed(2) + "px) scale(" + sc2.toFixed(4) + ")");
      if (m.halo) st(m.halo, "opacity", (0.95 * Math.exp(-d / 0.45)).toFixed(3));
      if (m.tk) {
        cls(m.tk, "dlv", t >= m.t + 0.12);
        cls(m.tk, "read", t >= m.read);
      }
    }
    // SHELF's "Shelved." details: the check draws, the chip pops
    MS.m2.ck.setAttribute("stroke-dashoffset", (1 - P3O(prog(t, T.m2 + 0.04, 0.2))).toFixed(3));
    var cu = prog(t, T.m2 + 0.12, 0.3);
    st(MS.m2.chip, "transform", "scale(" + lerp(0.55, 1, BO2(cu)).toFixed(4) + ")");
    st(MS.m2.chip, "opacity", prog(t, T.m2 + 0.12, 0.06).toFixed(3));

    // header status
    var typing = false;
    for (var w = 0; w < TYPWIN.length; w++) if (t >= TYPWIN[w][0] - 0.02 && t < TYPWIN[w][1] - 0.02) typing = true;
    st(E.stOn, "opacity", typing ? "0" : "1");
    st(E.stTy, "opacity", typing ? "1" : "0");

    // the input field: typing, caret, send
    var act = null, n = 0;
    for (var k = 0; k < TYPED.length; k++) if (t >= TYPED[k].t0 && t < TYPED[k].send) act = TYPED[k];
    var hl = null;
    if (act) {
      n = Math.round(act.s.length * P2IO(prog(t, act.t0, act.t1 - act.t0)));
      txt(E.ftx, act.s.slice(0, n));
      st(E.ftrack, "transform", "translateX(" + (-Math.max(0, act.pw[n] + 8 - 330)).toFixed(1) + "px)");
      if (t < act.t1 && n > 0) hl = act.s[n - 1].toLowerCase();
    } else {
      txt(E.ftx, "");
      st(E.ftrack, "transform", "translateX(0px)");
    }
    var focused = kb > 0.5;
    var blinkOn = act ? true : Math.floor((t - T.kb) * 2.2) % 2 === 0;
    st(E.caret, "opacity", focused && blinkOn ? "1" : "0");
    // send button: in while text is there, pressed on send
    var sendO = 0, sendS = 1;
    if (act && n > 0) { var su = prog(t, act.t0, 0.12); sendO = su; sendS = lerp(0.5, 1, BO2(su)); }
    for (var k2 = 0; k2 < TYPED.length; k2++) {
      var ds = t - TYPED[k2].send;
      if (ds >= 0 && ds < 0.16) { sendO = 1 - prog(ds, 0.08, 0.08); sendS = ds < 0.06 ? 0.84 : lerp(0.84, 1, P2O(prog(ds, 0.06, 0.1))); }
    }
    op(E.send, sendO);
    st(E.send, "transform", "scale(" + sendS.toFixed(3) + ")");
    st(E.icam, "opacity", (1 - sendO).toFixed(3));
    st(E.imic, "opacity", (1 - sendO).toFixed(3));
    // keyboard: the key under the finger lights up, with the iOS key popup for letters
    for (var kid in KEYS) cls(KEYS[kid].e, "hl", kid === hl);
    if (hl && hl !== " " && KEYS[hl]) {
      var K = KEYS[hl];
      st(kpop, "visibility", "visible");
      st(kpop, "transform", "translate(" + (K.x - 15) + "px," + (K.y - 106) + "px)");
      txt(kpop, hl);
    } else st(kpop, "visibility", "hidden");

    // status-bar clock + the time-skip lock clock
    if (t < T.skip0) { txt(E.clkTx, "9:41"); st(E.clkTx, "filter", "none"); }
    else {
      var c = skipClock(t);
      txt(E.clkTx, c.short + " " + c.hm);
      st(E.clkTx, "filter", c.speed > 0.15 ? "blur(" + (1.6 * c.speed).toFixed(2) + "px)" : "none");
    }
    var dimO = 0.66 * sstep(T.skip0, T.skip0 + 0.22, t);
    op(E.dim, dimO);
    st(E.chat, "filter", fx(7 * sstep(T.skip0, T.skip0 + 0.25, t)));
    st(E.kb, "filter", fx(7 * sstep(T.skip0, T.skip0 + 0.25, t)));
    var lo = sstep(T.skip0 + 0.02, T.skip0 + 0.16, t);
    if (op(E.lock, lo)) {
      var c2 = skipClock(t);
      txt(E.lkDay, c2.day);
      txt(E.lkTime, c2.hm);
      st(E.lock, "transform", "scale(" + lerp(0.9, 1, EO(prog(t, T.skip0, 0.4))).toFixed(4) + ")");
      st(E.lkTime, "filter", c2.speed > 0.12 ? "blur(" + (3.5 * c2.speed).toFixed(2) + "px)" : "none");
    }
  }

  // phone-local position of a chat-content point (x in screen px, y in chat-content px)
  function chatToLocal(x, y, t) { return { x: 15 + x, y: 15 + 200 + y - scrollAt(t) }; }

  function renderPopouts(t) {
    if (t >= T.hit1) return;
    // 1) the PDF flies into the chat (34.43)
    if (t >= T.fly0 && t < T.m1 + 0.08) {
      var u = prog(t, T.fly0, T.m1 - T.fly0), e = P3IO(u);
      var end = chatToLocal(168 + 6 + 22, MS.m1.top + 6 + 16, t); // the page inside the preview, top-left
      var ex = end.x + 192, ey = end.y + 248;
      var sx = -330, sy = 520, cx = -40, cy = 210; // start + bezier control (phone-local, outside the phone)
      var x = (1 - e) * (1 - e) * sx + 2 * (1 - e) * e * cx + e * e * ex;
      var y = (1 - e) * (1 - e) * sy + 2 * (1 - e) * e * cy + e * e * ey;
      var z = lerp(420, 0, e), s = lerp(0.52, 1, e);
      var after = prog(t, T.m1, 0.08);
      var o = (t < T.m1 ? prog(t, T.fly0, 0.05) : 1 - after) * 1;
      var speed = Math.sin(Math.PI * u);
      op(fly, o);
      st(fly, "transform", "translate3d(" + (x - 192).toFixed(1) + "px," + (y - 248.5).toFixed(1) + "px," + z.toFixed(1) + "px) rotateY(" + lerp(42, 0, e).toFixed(2) + "deg) rotateX(" + lerp(-12, 0, e).toFixed(2) + "deg) rotateZ(" + lerp(-20, 0, e).toFixed(2) + "deg) scale(" + s.toFixed(4) + ")");
      st(fly, "filter", fx(9 * speed));
      // crop the page to the preview window as it lands
      var crop = 497 - lerp(497, 134, sstep(0.72, 1, u));
      st(fly, "clipPath", crop > 0.5 ? "inset(0 0 " + crop.toFixed(1) + "px 0 round 6px)" : "none");
    } else st(fly, "visibility", "hidden");

    // 2) the deadline card lifts out of the phone in 3D for a beat, then settles back
    var out = prog(t, T.cardOut, 0.3), back = prog(t, T.cardBack, 0.34);
    var a = P3O(out) * (1 - P3IO(back));
    if (t >= T.cardOut && t < T.cardBack + 0.34) {
      var rest = chatToLocal(22 + 8, MS.m6.top + 8, t); // card top-left
      var rx0 = rest.x + 229, ry0 = rest.y + 84; // centre
      var cx2 = lerp(rx0, 330, a), cy2 = lerp(ry0, ry0 - 70, a);
      op(popCard, 1);
      st(popCard, "transform", "translate3d(" + (cx2 - 229).toFixed(1) + "px," + (cy2 - 84).toFixed(1) + "px," + (190 * a + 1).toFixed(1) + "px) rotateX(" + (-9 * a).toFixed(2) + "deg) rotateY(" + (13 * a).toFixed(2) + "deg) rotateZ(" + (-2.5 * a).toFixed(2) + "deg) scale(" + (1 + 0.3 * a).toFixed(4) + ")");
      var vel = Math.max(Math.sin(Math.PI * out) * (out < 1 ? 1 : 0), Math.sin(Math.PI * back) * (back > 0 ? 1 : 0));
      st(popCard, "filter", fx(4 * vel));
    } else st(popCard, "visibility", "hidden");

    // 3) the reminder banner drops onto the phone (and out of it, oversized), then rings
    var b0 = T.banner - 0.05;
    if (t >= b0) {
      var d = t - b0, sp = spring(d, 22, 0.6);
      var by = lerp(BAN_Y, 46, sp), bs = lerp(1, 0.3, sp);
      var shake = buzz(t - (T.banner + 0.1), 17, 0.15) + buzz(t - T.ring2, 17, 0.15);
      var shake2 = buzz(t - (T.banner + 0.1) - 0.012, 17, 0.15) + buzz(t - T.ring2 - 0.012, 17, 0.15);
      op(banner, prog(d, 0, 0.05));
      st(banner, "transform", "translate3d(" + (330 - 430 + 15 * shake).toFixed(1) + "px," + (by - 78).toFixed(1) + "px,110px) rotateZ(" + (1.3 * shake2).toFixed(3) + "deg) scale(" + bs.toFixed(4) + ")");
      var bv = Math.abs(spring(d + 1 / 60, 22, 0.6) - spring(d - 1 / 60, 22, 0.6)) * 30;
      st(banner, "filter", fx(Math.min(10, bv * 4)));
      // sheen sweep + edge glow on landing and on the second ring
      var sh = prog(t, T.banner + 0.06, 0.5);
      st(bsheen, "opacity", sh > 0 && sh < 1 ? "1" : "0");
      st(bsheen, "transform", "translateX(" + lerp(-260, 1000, P2IO(sh)).toFixed(1) + "px)");
      var gl = Math.exp(-Math.max(0, t - (T.banner + 0.1)) / 0.22) * (t >= T.banner + 0.1 ? 1 : 0) + Math.exp(-Math.max(0, t - T.ring2) / 0.22) * (t >= T.ring2 ? 0.8 : 0);
      st(bglow, "opacity", Math.min(1, gl).toFixed(3));
      // ring ripples from the avatar (the phone is ringing)
      var evs = [T.banner + 0.1, T.banner + 0.26, T.ring2, T.ring2 + 0.16];
      for (var i = 0; i < 4; i++) {
        var dr = t - evs[i];
        if (dr < 0 || dr > 0.62) { st(rings[i], "visibility", "hidden"); continue; }
        var ru = dr / 0.62;
        op(rings[i], 0.9 * (1 - ru) * (1 - ru));
        st(rings[i], "transform", "translate3d(" + (330 - 358 - 46 + 15 * shake).toFixed(1) + "px," + (BAN_Y - 46).toFixed(1) + "px,111px) scale(" + (1 + 2.3 * P2O(ru)).toFixed(4) + ")");
      }
    } else {
      st(banner, "visibility", "hidden");
      for (var j = 0; j < 4; j++) st(rings[j], "visibility", "hidden");
    }
  }

  function renderWords(t) {
    if (!dsp(E.words, t < T.hit1)) return;
    var wz = prog(t, T.whip, T.hit1 - T.whip);
    st(E.words, "transform", wz > 0 ? "scale(" + (1 + 0.25 * P3I(wz)).toFixed(4) + ")" : "none");
    st(E.words, "transformOrigin", "540px 420px");
    st(E.words, "opacity", (1 - P2I(wz)).toFixed(3));
    for (var i = 0; i < LINES.length; i++) {
      var L = LINES[i], e = L.e;
      if (t < L.t0 || t >= L.exit) { st(e, "visibility", "hidden"); continue; }
      // line pose: big line, or shrunk into the lead line above when the next word lands
      var y = BIG_Y, s = 1;
      if (L.lead0) { y = LEAD_Y; s = LEAD_SIZE / L.size; }
      else if (L.toLead !== undefined && t >= L.toLead - LEADPRE) { var u = EO(prog(t, L.toLead - LEADPRE, 0.22)); y = lerp(BIG_Y, LEAD_Y, u); s = lerp(1, LEAD_SIZE / L.size, u); }
      var x = 0;
      if (L.widths) {
        var full = L.widths[L.widths.length - 1];
        x = (full - L.widths[0]) / 2;
        for (var k = 1; k < L.words.length; k++) x = lerp(x, (full - L.widths[k]) / 2, EO(prog(t, L.words[k][1] - ATK, 0.26)));
      }
      var a = 1, blur = 0, ex = 0, es = 1;
      if (t >= L.exit - EXD) {
        var p = prog(t, L.exit - EXD, EXD);
        a = 1 - p; blur = 12 * p;
        if (L.ex === "scale") es = 1 + 0.22 * p; else ex = -50 * p;
      }
      var shk = L.shake ? shake3(t, L.shake[0], L.shake[1]) : null;
      if (!op(e, a)) continue;
      st(e, "transform", "translate(" + (x * s + (shk ? shk[0] : 0)).toFixed(2) + "px," + (y + ex + (shk ? shk[1] : 0)).toFixed(2) + "px) scale(" + (s * es).toFixed(4) + ")");
      var glow = L.green ? "drop-shadow(0 0 24px rgba(37,211,102,0.55))" : "drop-shadow(0 0 22px rgba(90,160,255,0.45))";
      st(e, "filter", glow + " drop-shadow(0 8px 18px rgba(0,0,0,0.5))" + (blur > 0.3 ? " blur(" + blur.toFixed(1) + "px)" : ""));
      for (var w = 0; w < L.ws.length; w++) {
        var W2 = L.words[w], o = wordPose(W2[2], t, W2[1]), we = L.ws[w];
        st(we, "opacity", o.a.toFixed(3));
        st(we, "transform", "translate(" + o.x.toFixed(1) + "px," + o.y.toFixed(1) + "px) rotate(" + o.r.toFixed(2) + "deg) scale(" + o.s.toFixed(4) + ")");
        st(we, "filter", fx(o.b));
        if (L.sweep !== undefined) st(we, "backgroundPosition", lerp(130, -30, P2IO(prog(t, L.sweep, 0.55))).toFixed(1) + "% 0, 0 0");
      }
    }
  }

  function renderHits(t) {
    if (!dsp(E.hits, t >= T.hit1)) return;
    for (var i = 0; i < HITS.length; i++) {
      var h = HITS[i];
      if (!dsp(h.e, t >= h.t && t < h.t1)) continue;
      var d = t - h.t;
      // cut-in punch then a slow push for the rest of the beat
      var gs = (1 + 0.04 * (1 - EO(prog(d, 0, 0.16)))) * (1 + 0.045 * P2O(prog(d, 0, 0.6)));
      var shk = shake3(t, h.t, i === 3 ? 12 : 8) || (i === 3 ? shake3(t, h.t + 0.1, 11) : null);
      st(h.grp, "transform", "translate(" + (shk ? shk[0] : 0) + "px," + (shk ? shk[1] : 0) + "px) rotate(" + h.rot + "deg) scale(" + gs.toFixed(4) + ")");
      for (var w = 0; w < h.ws.length; w++) {
        var we = EO(prog(d, -0.02, 0.16));
        st(h.ws[w], "opacity", "1");
        st(h.ws[w], "transform", "scale(" + lerp(1.08, 1, we).toFixed(4) + ")");
        st(h.ws[w], "filter", fx(2.5 * (1 - we)));
      }
      var F2 = h.frag, fu = prog(d, 0, 0.6);
      st(h.fragE, "opacity", F2.o.toFixed(3));
      st(h.fragE, "transform", "translateY(" + (-40 * P2O(fu)).toFixed(1) + "px) rotateX(" + F2.rx + "deg) rotateZ(" + F2.rz + "deg) scale(" + (F2.s * (1 + 0.05 * P2O(fu))).toFixed(4) + ")");
      st(h.fragE, "filter", fx(F2.blur));
      var ic = h.iconE;
      if (h.icon === "stamp") {
        var sd = d - 0.067, su = prog(sd, 0, 0.15);
        op(ic, sd >= 0 ? 1 : 0);
        st(ic, "transform", "rotate(" + lerp(-32, h.irot, P3O(su)).toFixed(2) + "deg) scale(" + lerp(2.5, 1, P3O(su)).toFixed(4) + ")");
        st(ic, "filter", fx(9 * (1 - su)));
      } else if (h.icon === "search") {
        var mu = prog(d, -0.02, 0.34);
        op(ic, 1);
        st(ic, "transform", "translateX(" + lerp(-320, 0, EO(mu)).toFixed(1) + "px) rotate(" + lerp(-28, 0, BO1(mu)).toFixed(2) + "deg) scale(" + lerp(0.75, 1, BO1(mu)).toFixed(4) + ")");
        st(ic, "filter", fx(8 * (1 - EO(mu))));
      } else {
        var pu = prog(d, -0.02, 0.3);
        op(ic, 1);
        st(ic, "transform", "rotate(" + h.irot + "deg) scale(" + lerp(0.62, 1, BO2(pu)).toFixed(4) + ")");
        if (h.day) h.day.setAttribute("fill", d > 0.22 ? "#7cc0ff" : "#fff");
      }
      var bu = prog(d, 0, 0.5);
      st(h.burstE, "opacity", (1 - 0.45 * P2O(bu)).toFixed(3));
      st(h.burstE, "transform", "scale(" + lerp(0.75, 1.12, P2O(bu)).toFixed(4) + ")");
      var ru = prog(d, 0, 0.42);
      if (op(h.ringE, ru > 0 && ru < 1 ? 0.85 * (1 - ru) : 0)) st(h.ringE, "transform", "scale(" + lerp(0.35, 2.3, P2O(ru)).toFixed(4) + ")");
      for (var k = 0; k < h.streaks.length; k++) {
        var S = h.streaks[k], sd2 = d - S.d;
        if (sd2 < 0 || sd2 > 0.3) { st(S.e, "visibility", "hidden"); continue; }
        var dir = (S.ang * Math.PI) / 180, dist = -S.len + S.sp * sd2;
        op(S.e, 0.9 * (1 - sd2 / 0.3));
        st(S.e, "transform", "translate(" + (540 + Math.cos(dir) * (dist - 700)).toFixed(1) + "px," + (S.y + Math.sin(dir) * (dist - 700)).toFixed(1) + "px) rotate(" + S.ang.toFixed(1) + "deg)");
      }
    }
  }

  function renderFx(t) {
    var ev = [[0, 0.14], [T.wa, 0.2], [T.banner, 0.12], [T.hit1, 0.3], [T.hit2, 0.26], [T.hit3, 0.26], [T.hit4, 0.36]];
    var f = 0;
    for (var i = 0; i < ev.length; i++) { var d = t - ev[i][0]; if (d >= 0 && d < 0.4) f = Math.max(f, ev[i][1] * Math.exp(-d / 0.065)); }
    op(E.flash, f);
    dsp(E.bgfx, t < T.hit1);
  }

  function render(t) {
    t = clamp(t, 0, DUR);
    var C = camState(t);
    var P = phoneState(t);
    // the whip zooms toward the banner's on-screen centre
    var M0 = camMatrix({ s1: C.s1, oy: C.oy, k: C.k, wz: 1 }, 0, 0);
    var bxS = M0.a * 540 + M0.tx, byS = M0.a * (600 + BAN_Y) + M0.ty;
    var M = camMatrix(C, bxS, byS);
    var imp = shake3(t, 0, 7) || shake3(t, T.wa, 8); // the two opening slams shake grid + badge together
    renderBackground(t, C, M, P);
    renderGrid(t, imp);
    renderPhone(t, C, M, P, imp);
    renderChat(t);
    renderPopouts(t);
    renderWords(t);
    renderHits(t);
    renderFx(t);
  }

  /* the paused timeline + its single linear driver are registered inline in index.html */
  window.__demo = { render: render, T: T, MS: MS, scrollAt: scrollAt, DUR: DUR, fk: fk };
})();
