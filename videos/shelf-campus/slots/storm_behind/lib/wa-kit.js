/* wa-kit.js — v2 (WhatsApp) kit shared by notifs/cards, notifs/storm and notifs/storm_hook.
   Master copy lives in slots/notifs/_shared/; each project carries its own copy in lib/
   (run _shared/sync.sh after edits).

   - WA.card(): the iOS dark-mode banner that shows a WhatsApp message (see wa-kit.css)
   - every icon is hand-drawn inline SVG (no logo files, no emoji, no other brands)
   - a tiny keyframe engine (WA.Track / WA.Actor): each frame is a pure function of time, sampled
     by ONE linear GSAP driver tween (the native-notification-pop pattern), so seeks in any order
     render identical pixels. Eases come from GSAP (gsap.parseEase) or the closed-form spring.
   Deterministic: no clocks, no Math.random (WA.rng is a seeded mulberry32). */
(function (global) {
  "use strict";

  var WA = {};
  WA.FPS = 30;

  /* ---------- seeded PRNG ---------- */
  WA.rng = function (seed) {
    var a = seed >>> 0;
    return function () {
      a = (a + 0x6d2b79f5) >>> 0;
      var t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  };

  /* ---------- frame helpers ----------
     A beat at time t lands on frame round(t * 30). hit(t) is the start time for an arrival whose
     FIRST visible frame must be that frame: 4 ms before it, so the frame shows the arrival pose. */
  WA.frame = function (t) {
    return Math.round(t * WA.FPS);
  };
  WA.snap = function (t) {
    return WA.frame(t) / WA.FPS;
  };
  WA.hit = function (t) {
    return WA.snap(t) - 0.004;
  };

  /* ---------- glyphs (inline SVG, drawn by hand) ---------- */
  // the WhatsApp glyph: a round speech-bubble outline with a small tail at the bottom-left and a
  // phone handset inside (white, on the green rounded square)
  var WA_BUBBLE = '<path d="M21 63.4A33 33 0 1 1 34.6 77L14.6 85.4Z" fill="none" stroke="#fff" stroke-width="7.4" stroke-linejoin="round"/>';
  var WA_HANDSET =
    '<path transform="translate(26.6 24.4) scale(1.95)" fill="#fff" d="M6.62 10.79c1.44 2.83 3.76 5.14 6.59 6.59l2.2-2.2c.27-.27.67-.36 1.02-.24 1.12.37 2.33.57 3.57.57.55 0 1 .45 1 1V20c0 .55-.45 1-1 1-9.39 0-17-7.61-17-17 0-.55.45-1 1-1h3.5c.55 0 1 .45 1 1 0 1.25.2 2.45.57 3.57.11.35.03.74-.25 1.02l-2.2 2.2z"/>';
  var G = {
    wa: function () {
      return '<svg viewBox="0 0 100 100" aria-hidden="true">' + WA_BUBBLE + WA_HANDSET + "</svg>";
    },
    // the full app icon (summary banners): gradient square + the same glyph, a touch smaller
    waIcon: function (id) {
      return (
        '<svg viewBox="0 0 100 100" aria-hidden="true"><defs><linearGradient id="' + id + '" x1="0" y1="0" x2="0" y2="1">' +
        '<stop offset="0" stop-color="#5df58a"/><stop offset=".55" stop-color="#25d366"/><stop offset="1" stop-color="#1cb653"/></linearGradient></defs>' +
        '<rect width="100" height="100" rx="24" fill="url(#' + id + ')"/>' +
        '<g transform="translate(13 13) scale(.74)">' + WA_BUBBLE + WA_HANDSET + "</g></svg>"
      );
    },
    group: function () {
      return (
        '<svg viewBox="0 0 48 48" aria-hidden="true">' +
        '<circle cx="17" cy="17.2" r="6.1" fill="#fff" fill-opacity=".7"/>' +
        '<path d="M4.6 36.4c.6-6.8 5.5-11 12.4-11 3 0 5.7.8 7.8 2.3-3.3 2.3-5.4 5.7-6 9.9z" fill="#fff" fill-opacity=".7"/>' +
        '<circle cx="30.2" cy="18.6" r="7.3" fill="#fff"/>' +
        '<path d="M17.2 40c.8-8 6.2-12.6 13-12.6s12.2 4.6 13 12.6z" fill="#fff"/>' +
        "</svg>"
      );
    },
    cap: function () {
      return (
        '<svg viewBox="0 0 48 48" aria-hidden="true">' +
        '<path d="M24 9.6 45 19.2 24 28.8 3 19.2z" fill="#fff"/>' +
        '<path d="M11.6 23.9v7.4c0 3.6 5.6 6.5 12.4 6.5s12.4-2.9 12.4-6.5v-7.4L24 29.6z" fill="#fff"/>' +
        '<path d="M40.6 21.2v10.6" stroke="#fff" stroke-width="2.4" stroke-linecap="round"/>' +
        '<circle cx="40.6" cy="33.4" r="2.6" fill="#fff"/>' +
        "</svg>"
      );
    },
    flask: function () {
      return (
        '<svg viewBox="0 0 48 48" aria-hidden="true">' +
        '<path d="M18.6 7.5h10.8M20.6 7.5v11.2l-9.8 17.6a3.2 3.2 0 0 0 2.8 4.7h20.8a3.2 3.2 0 0 0 2.8-4.7l-9.8-17.6V7.5" fill="none" stroke="#fff" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>' +
        '<path d="M14.9 30.6h18.2l3.1 5.6a1.6 1.6 0 0 1-1.4 2.4H13.2a1.6 1.6 0 0 1-1.4-2.4z" fill="#fff"/>' +
        "</svg>"
      );
    },
    megaphone: function () {
      return (
        '<svg viewBox="0 0 48 48" aria-hidden="true">' +
        '<path d="M7.5 20.6v6.8a2.6 2.6 0 0 0 2.6 2.6h3.6l14.3 8V10l-14.3 8h-3.6a2.6 2.6 0 0 0-2.6 2.6z" fill="#fff"/>' +
        '<path d="M14.6 30.4l2.5 8.5a2 2 0 0 0 1.9 1.5h1.7a1.6 1.6 0 0 0 1.5-2.1l-2.4-7.9z" fill="#fff"/>' +
        '<path d="M33.6 18.2a7.8 7.8 0 0 1 0 11.6" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round"/>' +
        "</svg>"
      );
    },
    folder: function () {
      return (
        '<svg viewBox="0 0 48 48" aria-hidden="true">' +
        '<path d="M5.6 14.6A3.6 3.6 0 0 1 9.2 11h9.6l3.7 4.1h16.3a3.6 3.6 0 0 1 3.6 3.6v15.7a3.6 3.6 0 0 1-3.6 3.6H9.2a3.6 3.6 0 0 1-3.6-3.6z" fill="#fff"/>' +
        '<path d="M5.6 20.4h36.8" stroke="#000" stroke-opacity=".14" stroke-width="2"/>' +
        "</svg>"
      );
    },
    building: function () {
      return (
        '<svg viewBox="0 0 48 48" aria-hidden="true">' +
        '<path d="M11 40.5V11.6A2.6 2.6 0 0 1 13.6 9h13.8A2.6 2.6 0 0 1 30 11.6v28.9M30 19.5h5.4A2.6 2.6 0 0 1 38 22.1v18.4M7 40.5h34" fill="none" stroke="#fff" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>' +
        '<path d="M16.4 15.5h2.6M22 15.5h2.6M16.4 21.8h2.6M22 21.8h2.6M16.4 28.1h2.6M22 28.1h2.6M33.5 27h.6M33.5 33h.6" stroke="#fff" stroke-width="3" stroke-linecap="round"/>' +
        "</svg>"
      );
    },
    // inline message glyphs (body line), 30 x 30
    pdf: function () {
      return (
        '<svg viewBox="0 0 30 30" aria-hidden="true">' +
        '<path d="M8 2.6h10.2l6.2 6.2v16.4a2.2 2.2 0 0 1-2.2 2.2H8a2.2 2.2 0 0 1-2.2-2.2V4.8A2.2 2.2 0 0 1 8 2.6z" fill="#e5534b"/>' +
        '<path d="M18.2 2.6v4.6a1.6 1.6 0 0 0 1.6 1.6h4.6z" fill="#f6aaa5"/>' +
        '<rect x="9.2" y="15.4" width="11.6" height="2.3" rx="1.15" fill="#fff" fill-opacity=".92"/>' +
        '<rect x="9.2" y="20" width="7.6" height="2.3" rx="1.15" fill="#fff" fill-opacity=".92"/>' +
        "</svg>"
      );
    },
    photo: function () {
      return (
        '<svg viewBox="0 0 30 30" aria-hidden="true">' +
        '<path d="M4.6 10.6A2.6 2.6 0 0 1 7.2 8h3l1.9-2.7h5.8L19.8 8h3a2.6 2.6 0 0 1 2.6 2.6v11.2a2.6 2.6 0 0 1-2.6 2.6H7.2a2.6 2.6 0 0 1-2.6-2.6z" fill="rgb(222,222,232)"/>' +
        '<circle cx="15" cy="16" r="4.9" fill="#2c2c30"/><circle cx="15" cy="16" r="3" fill="rgb(222,222,232)"/>' +
        "</svg>"
      );
    },
    mic: function () {
      return (
        '<svg viewBox="0 0 30 30" aria-hidden="true">' +
        '<rect x="10.8" y="3.4" width="8.4" height="14.6" rx="4.2" fill="#25d366"/>' +
        '<path d="M7.4 14.2a7.6 7.6 0 0 0 15.2 0M15 21.8v4.2M11 26h8" fill="none" stroke="#25d366" stroke-width="2.4" stroke-linecap="round"/>' +
        "</svg>"
      );
    },
    ban: function () {
      return (
        '<svg viewBox="0 0 30 30" aria-hidden="true">' +
        '<circle cx="15" cy="15.4" r="8.6" fill="none" stroke="rgb(170,170,180)" stroke-width="2.4"/>' +
        '<path d="M8.9 21.5 21.1 9.3" stroke="rgb(170,170,180)" stroke-width="2.4"/>' +
        "</svg>"
      );
    },
    fwd: function () {
      return (
        '<svg viewBox="0 0 30 30" aria-hidden="true">' +
        '<path d="M3.6 23.2c1-5.6 4.4-8.6 9.6-8.8V10.6l6.4 6-6.4 6v-3.7c-3.7 0-6.6 1.3-9.6 4.3z" fill="rgb(200,200,210)"/>' +
        '<path d="M11.6 23.2c1-5.6 4.4-8.6 9.6-8.8V10.6l6.4 6-6.4 6v-3.7c-3.7 0-6.6 1.3-9.6 4.3z" fill="rgb(200,200,210)"/>' +
        "</svg>"
      );
    },
  };
  WA.G = G;

  /* ---------- the chats (generic names only; avatars are drawn, never photos) ---------- */
  function grad(a, b) {
    return "linear-gradient(160deg, " + a + " 0%, " + b + " 100%)";
  }
  WA.CHATS = {
    unofficial: { name: "Unofficial Group", av: grad("#7d7bff", "#4f4dd8"), glyph: "group", group: true },
    official: { name: "Official Class Group", av: grad("#3fa0ff", "#0a6fe0"), glyph: "cap", group: true },
    boys: { name: "Boys Group", av: grad("#e87400", "#c75a00"), ini: "BG", group: true },
    ishaan: { name: "Ishaan", av: grad("#a35cf0", "#6a2fd6"), ini: "I" },
    cse: { name: "CSE 2nd Year", av: grad("#1f9fbd", "#137a94"), ini: "CSE", group: true },
    lab: { name: "Lab Batch B", av: grad("#52d97a", "#25a84d"), glyph: "flask", group: true },
    hostel: { name: "Hostel Wing C", av: grad("#c2a27a", "#94744f"), glyph: "building", group: true },
    project: { name: "Project Team", av: grad("#ff6b8a", "#e0365a"), glyph: "folder", group: true },
    reps: { name: "Class Reps", av: grad("#3ad6cc", "#12a49b"), glyph: "megaphone", group: true },
    zaid: { name: "Zaid", av: grad("#e8603f", "#c2412a"), ini: "Z" },
    mom: { name: "Mom", av: grad("#d94d8a", "#b0336c"), ini: "M" },
    wa: { name: "WhatsApp", app: true },
  };

  WA.pillText = function (n) {
    if (typeof n === "string") return n;
    n = Math.max(0, Math.round(n));
    return n > 999 ? "999+" : String(n);
  };

  function div(cls) {
    var d = document.createElement("div");
    if (cls) d.className = cls;
    return d;
  }
  var uid = 0;

  /* ---------- the banner ----------
     o = { chat, title?, sender?, msg, icon? ("pdf"|"photo"|"mic"|"ban"|"fwd"), del?, two?, time?,
           pill? (number|string|null), w?, h?, id?, decorative? }
     returns { el (.wa-card), fly, banner, pill, ping, timeEl, dim, sheen, glow, w, h, setPill(n), setTime(s) } */
  WA.card = function (o) {
    var chat = WA.CHATS[o.chat] || WA.CHATS.unofficial;
    var w = o.w || 940;
    var h = o.h || (o.two ? 196 : 156);

    var el = div("wa-card" + (o.tight ? " tight" : ""));
    if (o.id) el.id = o.id;
    el.setAttribute("data-layout-allow-overflow", "");
    // storm banners are deliberate, overlapping set dressing: skip the text-layout audit
    if (o.decorative) el.setAttribute("data-layout-ignore", "");
    el.style.setProperty("--wa-w", w + "px");
    el.style.setProperty("--wa-h", h + "px");

    var fly = div("wa-fly");
    var banner = div("wa-banner");

    // avatar + app badge
    var av = div("wa-av" + (chat.app ? " app" : ""));
    if (chat.app) {
      av.innerHTML = G.waIcon("wag" + uid++);
    } else {
      av.style.setProperty("--wa-av", chat.av);
      if (chat.glyph) av.innerHTML = G[chat.glyph]();
      else {
        var ini = document.createElement("span");
        ini.className = "wa-ini" + (chat.ini.length > 2 ? " s3" : "");
        ini.textContent = chat.ini;
        av.appendChild(ini);
      }
      var badge = div("wa-badge");
      badge.innerHTML = G.wa();
      av.appendChild(badge);
    }

    // text column
    var txt = div("wa-txt");
    var row1 = div("wa-row");
    var title = div("wa-title");
    title.textContent = o.title || chat.name;
    var time = div("wa-time");
    time.textContent = o.time || "now";
    row1.appendChild(title);
    row1.appendChild(time);

    var row2 = div("wa-row" + (o.two ? " two" : ""));
    var body = div("wa-body" + (o.del ? " del" : "") + (o.two ? " two" : ""));
    if (o.sender) body.appendChild(document.createTextNode(o.sender + ": "));
    if (o.icon && G[o.icon]) {
      var g = document.createElement("span");
      g.className = "g";
      g.innerHTML = G[o.icon]();
      body.appendChild(g);
    }
    body.appendChild(document.createTextNode(o.msg || ""));
    row2.appendChild(body);

    var pill = null;
    var pillNum = null;
    var ping = null;
    var shown = null;
    if (o.pill !== null && o.pill !== undefined) {
      pill = div("wa-pill");
      pillNum = document.createElement("span");
      pillNum.className = "wa-pn";
      shown = WA.pillText(o.pill);
      pillNum.textContent = shown;
      ping = document.createElement("span");
      ping.className = "wa-ping";
      pill.appendChild(ping);
      pill.appendChild(pillNum);
      row2.appendChild(pill);
    }
    txt.appendChild(row1);
    txt.appendChild(row2);

    var fx = div("wa-fx");
    var sheen = div("wa-sheen");
    sheen.setAttribute("data-layout-allow-overflow", "");
    var dim = div("wa-dim");
    fx.appendChild(sheen);
    fx.appendChild(dim);
    var glow = div("wa-glow");

    banner.appendChild(av);
    banner.appendChild(txt);
    banner.appendChild(fx);
    fly.appendChild(banner);
    fly.appendChild(glow);
    el.appendChild(fly);

    return {
      el: el,
      fly: fly,
      banner: banner,
      pill: pill,
      ping: ping,
      timeEl: time,
      dim: dim,
      sheen: sheen,
      glow: glow,
      w: w,
      h: h,
      setPill: function (n) {
        if (!pill) return;
        var s = WA.pillText(n);
        if (s !== shown) {
          shown = s;
          pillNum.textContent = s;
        }
      },
      setTime: function (s) {
        if (time.textContent !== s) time.textContent = s;
      },
    };
  };

  /* ---------- eases ---------- */
  // closed-form underdamped spring (the registry's native-notification-pop law):
  // x(t) = 1 - e^(-z w t) (cos(wd t) + (z w / wd) sin(wd t))
  WA.springEnv = function (omega, zeta) {
    var wd = omega * Math.sqrt(1 - zeta * zeta);
    return function (t) {
      return Math.exp(-zeta * omega * t) * (Math.cos(wd * t) + ((zeta * omega) / wd) * Math.sin(wd * t));
    };
  };
  // as an ease over a segment of `dur` seconds (the tail is pinned to 1 by the track afterwards)
  WA.springEase = function (omega, zeta, dur) {
    var env = WA.springEnv(omega, zeta);
    var endV = env(dur);
    return function (p) {
      // remove the residual so p = 1 lands exactly on 1 (residual < 0.5 % for the springs used)
      return 1 - env(p * dur) + endV * p;
    };
  };
  var easeCache = {};
  WA.ease = function (e) {
    if (typeof e === "function") return e;
    if (!e || e === "none" || e === "linear") return function (p) { return p; };
    if (!easeCache[e]) easeCache[e] = gsap.parseEase(e);
    return easeCache[e];
  };

  /* ---------- keyframe track ----------
     add(t0, dur, to, ease[, from]): from defaults to the track's own value at t0, so a segment that
     interrupts a running one continues from where it is (no jumps). Segments are added in time order. */
  function Track(init) {
    this.init = init;
    this.segs = [];
  }
  Track.prototype.at = function (t) {
    var s = this.segs;
    var v = this.init;
    for (var i = 0; i < s.length; i++) {
      var g = s[i];
      if (t < g.t0) break;
      if (t >= g.t0 + g.dur) v = g.to;
      else {
        var p = g.dur > 0 ? (t - g.t0) / g.dur : 1;
        v = g.f + (g.to - g.f) * g.e(p);
      }
    }
    return v;
  };
  Track.prototype.add = function (t0, dur, to, ease, from) {
    var f = from === undefined ? this.at(t0) : from;
    var seg = { t0: t0, dur: Math.max(1e-4, dur), f: f, to: to, e: WA.ease(ease) };
    var i = this.segs.length;
    while (i > 0 && this.segs[i - 1].t0 > t0) i--; // keep time order (stable for equal t0)
    this.segs.splice(i, 0, seg);
    return this;
  };
  Track.prototype.set = function (t0, v) {
    return this.add(t0, 1e-4, v, "none", v);
  };
  WA.Track = Track;

  /* ---------- actor: one banner driven by tracks ----------
     channels (centre x/y in px, scale, rotation deg, opacity, extra blur px, dim, glow,
     and an inner "fly" pose jx/jy/jr/js for trembles and blow-aparts) */
  // ag = a multiplicative "age" scale (older banners recede), always relative to s
  var CH = { x: 0, y: 0, s: 1, ag: 1, r: 0, o: 0, b: 0, d: 0, g: 0, jx: 0, jy: 0, jr: 0, js: 1, sh: -1 };
  function Actor(card, init) {
    this.k = card;
    this.tr = {};
    for (var c in CH) this.tr[c] = new Track(init && c in init ? init[c] : CH[c]);
    this.mb = 1; // motion-blur gain (0 disables the speed blur)
    this.mbMax = 18;
    this._last = {};
  }
  Actor.prototype.ch = function (c) {
    return this.tr[c];
  };
  Actor.prototype.pose = function (t) {
    var tr = this.tr;
    return { x: tr.x.at(t), y: tr.y.at(t), s: tr.s.at(t) * tr.ag.at(t), r: tr.r.at(t) };
  };
  // speed of the banner's outline in px per frame (translation + scale + rotation)
  Actor.prototype.speed = function (t) {
    var dt = 1 / (2 * WA.FPS);
    var a = this.pose(t - dt);
    var b = this.pose(t + dt);
    var half = (this.k.w + this.k.h) / 4;
    var tr = this.tr;
    var ja = { x: tr.jx.at(t - dt), y: tr.jy.at(t - dt), r: tr.jr.at(t - dt), s: tr.js.at(t - dt) };
    var jb = { x: tr.jx.at(t + dt), y: tr.jy.at(t + dt), r: tr.jr.at(t + dt), s: tr.js.at(t + dt) };
    var mv = Math.hypot(b.x - a.x + (jb.x - ja.x) * b.s, b.y - a.y + (jb.y - ja.y) * b.s);
    var sc = Math.abs(b.s * jb.s - a.s * ja.s) * half;
    var rot = (Math.abs(b.r + jb.r - a.r - ja.r) * Math.PI / 180) * half * b.s;
    return mv + sc + 0.6 * rot; // per 1/30 s
  };
  Actor.prototype.apply = function (t) {
    var tr = this.tr;
    var el = this.k.el;
    var o = tr.o.at(t);
    var L = this._last;
    if (o <= 0.001) {
      if (L.vis !== false) {
        el.style.visibility = "hidden";
        el.style.opacity = "0";
        L.vis = false;
      }
      return;
    }
    if (L.vis !== true) {
      el.style.visibility = "visible";
      L.vis = true;
    }
    var w = this.k.w;
    var h = this.k.h;
    var x = tr.x.at(t);
    var y = tr.y.at(t);
    var s = tr.s.at(t) * tr.ag.at(t);
    var r = tr.r.at(t);
    var tf = "translate(" + (x - w / 2).toFixed(2) + "px," + (y - h / 2).toFixed(2) + "px) rotate(" + r.toFixed(3) + "deg) scale(" + s.toFixed(4) + ")";
    if (tf !== L.tf) {
      el.style.transform = tf;
      L.tf = tf;
    }
    var os = o >= 0.999 ? "1" : o.toFixed(3);
    if (os !== L.o) {
      el.style.opacity = os;
      L.o = os;
    }
    var blur = tr.b.at(t);
    if (this.mb > 0) {
      var v = this.speed(t);
      blur = Math.max(blur, Math.min(this.mbMax, Math.max(0, (v - 7) * 0.12 * this.mb)));
    }
    var fs = blur > 0.35 ? "blur(" + blur.toFixed(1) + "px)" : "none";
    if (fs !== L.f) {
      el.style.filter = fs;
      L.f = fs;
    }
    var jx = tr.jx.at(t);
    var jy = tr.jy.at(t);
    var jr = tr.jr.at(t);
    var js = tr.js.at(t);
    var ftf = "translate(" + jx.toFixed(2) + "px," + jy.toFixed(2) + "px) rotate(" + jr.toFixed(3) + "deg) scale(" + js.toFixed(4) + ")";
    if (ftf !== L.ftf) {
      this.k.fly.style.transform = ftf;
      L.ftf = ftf;
    }
    var d = tr.d.at(t);
    var ds = d.toFixed(3);
    if (ds !== L.d) {
      this.k.dim.style.opacity = ds;
      L.d = ds;
    }
    var g = tr.g.at(t);
    var gs = g.toFixed(3);
    if (gs !== L.g) {
      this.k.glow.style.opacity = gs;
      L.g = gs;
    }
    var sh = tr.sh.at(t);
    var shs = sh < -0.5 || sh > 1.5 ? "0" : "1";
    if (shs !== L.sho) {
      this.k.sheen.style.opacity = shs;
      L.sho = shs;
    }
    if (shs === "1") {
      var sx = (-260 + (w + 300) * sh).toFixed(1);
      if (sx !== L.shx) {
        this.k.sheen.style.transform = "translateX(" + sx + "px)";
        L.shx = sx;
      }
    }
  };
  WA.Actor = Actor;

  /* ---------- geometry ---------- */
  // half extents of a w x h box at scale s, rotated rDeg
  WA.ext = function (w, h, s, rDeg) {
    var r = (Math.abs(rDeg) * Math.PI) / 180;
    var c = Math.cos(r);
    var sn = Math.sin(r);
    return { hx: s * ((w / 2) * c + (h / 2) * sn), hy: s * ((w / 2) * sn + (h / 2) * c) };
  };
  // corners of a w x h box centred on (x, y), scale s, rotation rDeg
  WA.corners = function (x, y, w, h, s, rDeg) {
    var a = (rDeg * Math.PI) / 180;
    var c = Math.cos(a);
    var sn = Math.sin(a);
    var hw = (w / 2) * s;
    var hh = (h / 2) * s;
    return [
      [-hw, -hh],
      [hw, -hh],
      [hw, hh],
      [-hw, hh],
    ].map(function (p) {
      return [x + p[0] * c - p[1] * sn, y + p[0] * sn + p[1] * c];
    });
  };

  // piecewise-linear lookup over [[t, v], ...] (sorted by t)
  WA.lerpKeys = function (keys, t) {
    if (t <= keys[0][0]) return keys[0][1];
    for (var i = 1; i < keys.length; i++) {
      if (t <= keys[i][0]) {
        var a = keys[i - 1];
        var b = keys[i];
        var u = (t - a[0]) / Math.max(1e-6, b[0] - a[0]);
        return a[1] + (b[1] - a[1]) * u;
      }
    }
    return keys[keys.length - 1][1];
  };
  // step lookup: the value of the last key at or before t
  WA.stepKeys = function (keys, t) {
    var v = keys[0][1];
    for (var i = 0; i < keys.length; i++) {
      if (t >= keys[i][0]) v = keys[i][1];
      else break;
    }
    return v;
  };

  global.WA = WA;
})(window);
