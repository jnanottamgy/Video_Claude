/* wa-storm.js — the WhatsApp notification STORM engine, shared by notifs/storm and notifs/storm_hook.
   Master copy lives in slots/notifs/_shared/; each project carries its own copy in lib/.
   Built on wa-kit.js (WA.card, WA.Actor, WA.Track). Deterministic: seeded PRNG only.

   A Storm owns a "world" layer (vertigo / jolts / collapse) and its banners. Each project's
   index.html writes the plan: which banner lands on which beat frame, where, and how.
   Placement is planned in world space and must stay inside the reel's safe zones both at rest and
   under the most extreme world transform the plan uses (opt.peak), and out of any keep-clear zones
   (faces, the hook title) while those apply. New banners are placed where they add the most
   VISIBLE area (a coverage grid), because the compositor hears an arrival as an alpha jump. */
(function (global) {
  "use strict";
  var WA = global.WA;
  var PI = Math.PI;

  /* ---------- message copy (slots/notifs/SPEC.md) ---------- */
  WA.MSG = {
    u_pdf: { chat: "unofficial", sender: "CR", icon: "pdf", msg: "Notes_unit1-5.pdf", pill: 47 },
    u_all: { chat: "unofficial", sender: "CR", msg: "all the notes, units 1-5", pill: 52 },
    u_47: { chat: "unofficial", msg: "47 new messages", pill: 47 },
    o_syl: { chat: "official", sender: "Prof. Mehta", msg: "Syllabus copy attached", pill: 128 },
    o_128: { chat: "official", msg: "128 new messages", pill: 128 },
    b_pyq: { chat: "boys", sender: "Zaid", icon: "photo", msg: "Solved PYQs (12 photos)", pill: "99+" },
    b_u3: { chat: "boys", sender: "Rahul", msg: "who has unit 3??", pill: 31 },
    b_blur: { chat: "boys", sender: "Zaid", icon: "photo", msg: "PYQ_2022 (blurry).jpg", pill: 34 },
    i_bro: { chat: "ishaan", msg: "bro check the group", pill: 3 },
    i_mic: { chat: "ishaan", icon: "mic", msg: "Voice message (0:42)", pill: 4 },
    c_exam: { chat: "cse", sender: "CR", msg: "@everyone exam is at 9 sharp", pill: 56 },
    c_del: { chat: "cse", sender: "Aman", icon: "ban", msg: "This message was deleted", del: true, pill: 57 },
    l_rec: { chat: "lab", sender: "Neha", msg: "anyone has the record??", pill: 9 },
    h_chg: { chat: "hostel", sender: "Kabir", msg: "who took my charger", pill: 5 },
    p_fwd: { chat: "project", sender: "Arjun", icon: "fwd", msg: "Forwarded many times: unit 4 notes.pdf", pill: 7, two: true },
    r_13: { chat: "reps", sender: "Priya", msg: "sir said only units 1-3", pill: 14 },
    z_pls: { chat: "zaid", msg: "send notes pls", pill: 2 },
    m_eat: { chat: "mom", msg: "Beta, did you eat?", pill: 1 },
    s_9: { chat: "wa", msg: "47 messages from 9 chats" },
    s_14: { chat: "wa", msg: "128 messages from 14 chats" },
    s_999: { chat: "wa", msg: "999+ unread", pill: "999+" },
  };
  // the pileup draws from this mix (summaries are placed by hand on the big hits)
  WA.POOL = ["u_47", "o_128", "b_u3", "i_bro", "c_exam", "l_rec", "h_chg", "p_fwd", "r_13", "z_pls", "m_eat",
    "b_blur", "u_all", "o_syl", "c_del", "i_mic", "b_pyq", "u_pdf"];

  function Storm(world, o) {
    this.world = world;
    this.W = o.W || 780;
    this.CX = o.cx;
    this.CY = o.cy;
    this.rnd = WA.rng(o.seed || 7);
    this.safe = o.safe || { x0: 66, x1: 1014, y0: 274, y1: 1284, railX: 938, railY: 1100 };
    this.peak = o.peak || { s: 1, r: 0, dx: 0, dy: 0 };
    this.zones = []; // keep-clear rects (faces): {x0, y0, x1, y1, t0, t1}; no banner may rest on one
    this.ghostZones = []; // rects (the hook title) only ghost banners (opacity <= cap) may enter
    this.items = [];
    this.cell = 12;
    this.wt = { x: new WA.Track(0), y: new WA.Track(0), r: new WA.Track(0), s: new WA.Track(1) };
    world.style.transformOrigin = this.CX + "px " + this.CY + "px";
    this.order = [];
    this.poolIdx = 0;
    this.pool = o.pool || WA.POOL;
  }
  var P = Storm.prototype;

  P.R = function (a, b) {
    return a + (b - a) * this.rnd();
  };
  P.sgn = function () {
    return this.rnd() < 0.5 ? -1 : 1;
  };
  // next message from seeded shuffles of the pool (no immediate repeats)
  P.next = function () {
    while (this.order.length <= this.poolIdx) {
      var idx = this.pool.slice();
      for (var i = idx.length - 1; i > 0; i--) {
        var j = Math.floor(this.rnd() * (i + 1));
        var tmp = idx[i];
        idx[i] = idx[j];
        idx[j] = tmp;
      }
      if (this.order.length && idx[0] === this.order[this.order.length - 1]) idx.push(idx.shift());
      this.order = this.order.concat(idx);
    }
    return this.order[this.poolIdx++];
  };

  /* ---------- geometry ---------- */
  P.hOf = function (key) {
    return WA.MSG[key] && WA.MSG[key].two ? 196 : 156;
  };
  // points over a banner (outline + interior), world space
  P.points = function (x, y, s, r, h, n) {
    var a = (r * PI) / 180;
    var c = Math.cos(a);
    var sn = Math.sin(a);
    var hw = (this.W / 2) * s;
    var hh = (h / 2) * s;
    var out = [];
    n = n || 8;
    for (var i = 0; i <= n; i++) {
      var u = -1 + (2 * i) / n;
      for (var j = 0; j <= 4; j++) {
        var v = -1 + (2 * j) / 4;
        out.push([x + u * hw * c - v * hh * sn, y + u * hw * sn + v * hh * c]);
      }
    }
    return out;
  };
  P.toScreen = function (px, py, T) {
    var dx = px - this.CX;
    var dy = py - this.CY;
    var a = (T.r * PI) / 180;
    return [this.CX + T.s * (dx * Math.cos(a) - dy * Math.sin(a)) + T.dx, this.CY + T.s * (dx * Math.sin(a) + dy * Math.cos(a)) + T.dy];
  };
  P.safePt = function (p) {
    var S = this.safe;
    if (p[0] < S.x0 || p[0] > S.x1 || p[1] < S.y0 || p[1] > S.y1) return false;
    if (p[1] > S.railY && p[0] > S.railX) return false;
    return true;
  };
  function inRect(p, z) {
    return p[0] > z.x0 && p[0] < z.x1 && p[1] > z.y0 && p[1] < z.y1;
  }
  // does a banner overlap rect z? (sampled banner points in z, or z's corners inside the banner)
  P.overlaps = function (x, y, s, r, h, z) {
    var pts = this.points(x, y, s, r, h, 10);
    for (var i = 0; i < pts.length; i++) if (inRect(pts[i], z)) return true;
    var a = (-r * PI) / 180;
    var c = Math.cos(a);
    var sn = Math.sin(a);
    var hw = (this.W / 2) * s;
    var hh = (h / 2) * s;
    var cs = [[z.x0, z.y0], [z.x1, z.y0], [z.x1, z.y1], [z.x0, z.y1], [(z.x0 + z.x1) / 2, (z.y0 + z.y1) / 2]];
    for (var k = 0; k < cs.length; k++) {
      var dx = cs[k][0] - x;
      var dy = cs[k][1] - y;
      var lx = dx * c - dy * sn;
      var ly = dx * sn + dy * c;
      if (Math.abs(lx) < hw && Math.abs(ly) < hh) return true;
    }
    return false;
  };
  // inside the safe area at rest AND under the peak world transform; solid banners also stay out of
  // every keep-clear zone active during [t0, t1)
  P.fits = function (x, y, s, r, h, t0, t1, solid) {
    var pts = this.points(x, y, s, r, h, 8);
    for (var i = 0; i < pts.length; i++) {
      if (!this.safePt(pts[i])) return false;
      if (!this.safePt(this.toScreen(pts[i][0], pts[i][1], this.peak))) return false;
    }
    for (var z = 0; z < this.zones.length; z++) {
      var Z = this.zones[z];
      if (Z.t1 > t0 && Z.t0 < t1 && this.overlaps(x, y, s, r, h, Z)) return false;
    }
    if (solid) {
      for (var g = 0; g < this.ghostZones.length; g++) {
        var GZ = this.ghostZones[g];
        if (GZ.t1 > t0 && GZ.t0 < t1 && this.overlaps(x, y, s, r, h, GZ)) return false;
      }
    }
    return true;
  };

  /* ---------- coverage grid (what the compositor's pop detector sees) ---------- */
  P.grid = function (t) {
    var S = this.safe;
    var c = this.cell;
    var nx = Math.ceil((S.x1 - S.x0) / c);
    var ny = Math.ceil((S.y1 - S.y0) / c);
    var G = { g: new Uint8Array(nx * ny), nx: nx, ny: ny };
    for (var i = 0; i < this.items.length; i++) {
      var it = this.items[i];
      if (it.ghost || it.born > t + 1e-6) continue;
      if (it.a.ch("o").at(t) < 0.6) continue;
      var p = it.a.pose(t);
      this.raster(G, p.x, p.y, p.s, p.r, it.h, true);
    }
    return G;
  };
  P.raster = function (G, x, y, s, r, h, mark) {
    var S = this.safe;
    var cl = this.cell;
    var e = WA.ext(this.W, h, s, r);
    var a = (-r * PI) / 180;
    var c = Math.cos(a);
    var sn = Math.sin(a);
    var hw = (this.W / 2) * s;
    var hh = (h / 2) * s;
    var i0 = Math.max(0, Math.floor((x - e.hx - S.x0) / cl));
    var i1 = Math.min(G.nx - 1, Math.floor((x + e.hx - S.x0) / cl));
    var j0 = Math.max(0, Math.floor((y - e.hy - S.y0) / cl));
    var j1 = Math.min(G.ny - 1, Math.floor((y + e.hy - S.y0) / cl));
    var n = 0;
    for (var j = j0; j <= j1; j++) {
      var py = S.y0 + (j + 0.5) * cl - y;
      for (var i = i0; i <= i1; i++) {
        var px = S.x0 + (i + 0.5) * cl - x;
        var lx = px * c - py * sn;
        var ly = px * sn + py * c;
        if (Math.abs(lx) <= hw && Math.abs(ly) <= hh) {
          var k = j * G.nx + i;
          if (mark) G.g[k] = 1;
          else if (!G.g[k]) n++;
        }
      }
    }
    return n;
  };
  P.coverage = function (t) {
    var G = this.grid(t);
    var n = 0;
    for (var i = 0; i < G.g.length; i++) n += G.g[i];
    return n / G.g.length;
  };

  /* ---------- placement ----------
     o = { s: [lo, hi], r: [lo, hi] (abs deg), h, n (candidates), k (choose among the best k),
           until (keep-clear window end), ghost (bool), region {x0,y0,x1,y1} (centre limits),
           bias(x, y) -> weight, far: [[x, y], ...] (spread away from these instead of coverage) } */
  P.pick = function (t, o) {
    var S = this.safe;
    var h = o.h || 156;
    var G = o.far ? null : this.grid(t + 0.3);
    var cands = [];
    var tries = o.n || 70;
    for (var pass = 0; pass < 4 && !cands.length; pass++) {
      var shrink = Math.pow(0.9, pass);
      for (var i = 0; i < tries; i++) {
        var s = this.R(o.s[0], o.s[1]) * shrink;
        var r = this.sgn() * this.R(o.r[0], o.r[1]);
        var e = WA.ext(this.W, h, s, r);
        var R0 = o.region || S;
        var xa = Math.max(S.x0 + e.hx, R0.x0);
        var xb = Math.min(S.x1 - e.hx, R0.x1);
        var ya = Math.max(S.y0 + e.hy, R0.y0);
        var yb = Math.min(S.y1 - e.hy, R0.y1);
        if (xa > xb || ya > yb) continue;
        var x = this.R(xa, xb);
        var y = this.R(ya, yb);
        if (!this.fits(x, y, s, r, h, t, o.until === undefined ? t + 1 : o.until, !o.ghost)) continue;
        var score;
        if (o.far) {
          var d = 1e9;
          for (var q = 0; q < o.far.length; q++) d = Math.min(d, Math.hypot((x - o.far[q][0]) / 1.3, y - o.far[q][1]));
          score = d;
        } else {
          score = this.raster(G, x, y, s, r, h, false);
        }
        if (o.bias) score *= o.bias(x, y, s, r);
        cands.push({ x: x, y: y, s: s, r: r, score: score });
      }
    }
    if (!cands.length) return null;
    cands.sort(function (a, b) {
      return b.score - a.score;
    });
    var k = Math.min(cands.length, o.k || 3);
    return cands[Math.floor(this.rnd() * k)];
  };

  /* ---------- banners ---------- */
  // spec: a WA.MSG key or a spec object. pose {x, y, s, r} (world, centre). entry {type, ...}.
  // opt: { ghost (opacity cap, e.g. 0.5), dim (aging max), noAge, mb (motion-blur gain) }
  P.add = function (key, tHit, pose, entry, opt) {
    opt = opt || {};
    var spec = typeof key === "string" ? WA.MSG[key] : key;
    var cfg = {};
    for (var f in spec) cfg[f] = spec[f];
    cfg.w = this.W;
    cfg.decorative = true;
    var card = WA.card(cfg);
    var a = new WA.Actor(card, { x: pose.x, y: pose.y, s: pose.s, r: pose.r, o: 0 });
    if (opt.mb !== undefined) a.mb = opt.mb;
    this.world.appendChild(card.el);
    var it = {
      a: a,
      k: card,
      h: card.h,
      key: typeof key === "string" ? key : "custom",
      born: WA.snap(tHit),
      ghost: !!opt.ghost,
      op: opt.ghost ? opt.ghost : 1,
      pill: typeof spec.pill === "number" ? spec.pill : null,
      rate: 0.6 + 1.6 * this.rnd(),
      idx: this.items.length,
    };
    this.items.push(it);
    this.enter(it, tHit, pose, entry || { type: "slam" });
    if (!opt.noAge && !it.ghost) {
      a.ch("d").add(it.born + 0.45, 2.6, opt.dim === undefined ? 0.42 : opt.dim, "sine.inOut", 0);
      a.ch("b").add(it.born + 0.9, 2.4, 1.2, "sine.inOut", 0);
    }
    return it;
  };

  P.enter = function (it, tHit, p, e) {
    var a = it.a;
    var t0 = WA.hit(tHit);
    var fr = WA.rng(7919 * (it.idx + 1)); // per-banner flourish: never shifts the shared plan
    function RR(lo, hi) {
      return lo + (hi - lo) * fr();
    }
    var sg = fr() < 0.5 ? -1 : 1;
    switch (e.type) {
      case "burst": {
        // flung out of a point (the laptop, the centre): tiny at the origin, overshoots into place
        var d = e.dur || 0.6;
        a.ch("x").add(t0, d, p.x, "expo.out", e.from[0]);
        a.ch("y").add(t0, d, p.y, "expo.out", e.from[1]);
        a.ch("s").add(t0, d * 0.85, p.s, "back.out(1.45)", p.s * 0.3);
        a.ch("r").add(t0, d, p.r, "expo.out", p.r * 0.25 + sg * RR(4, 12));
        a.ch("b").add(t0, 0.3, 0, "power2.out", 9);
        break;
      }
      case "slam": {
        a.ch("y").add(t0, 0.3, p.y, "power4.out", p.y - 24);
        a.ch("s").add(t0, 0.3, p.s, "power4.out", Math.min(p.s * 1.42, 1.32));
        a.ch("r").add(t0, 0.3, p.r, "power4.out", p.r + sg * RR(6, 11));
        a.ch("b").add(t0, 0.22, 0, "power2.out", 12);
        break;
      }
      case "pop": {
        a.ch("s").add(t0, 0.24, p.s, "back.out(1.8)", Math.min(p.s * 1.26, 1.22));
        a.ch("r").add(t0, 0.24, p.r, "power3.out", p.r + sg * RR(3, 7));
        a.ch("b").add(t0, 0.17, 0, "power2.out", 8);
        break;
      }
      case "fly": {
        // from off-frame on one side; it starts a frame early so its first visible frame is in-frame
        var t1 = t0 - 1 / WA.FPS;
        var dist = e.dist || 820;
        a.ch("x").add(t1, 0.5, p.x, "expo.out", p.x + e.side * dist);
        a.ch("y").add(t1, 0.5, p.y, "expo.out", p.y + (e.dy || RR(-120, 120)));
        a.ch("r").add(t1, 0.5, p.r, "expo.out", p.r + e.side * RR(18, 30));
        a.ch("s").add(t1, 0.5, p.s, "expo.out", p.s * 1.1);
        a.ch("b").add(t0, 0.28, 0, "power2.out", 14);
        break;
      }
      case "drop": {
        var v0 = t0 - 0.046;
        a.ch("y").add(v0, 0.7, p.y, WA.springEase(20, 0.66, 0.7), p.y - 150);
        a.ch("s").add(v0, 0.6, p.s, WA.springEase(17, 0.72, 0.6), p.s * 1.06);
        a.ch("b").add(t0, 0.26, 0, "power2.out", 11);
        break;
      }
    }
    a.ch("o").set(t0, it.op);
    if (!it.ghost) {
      // the unread pill pings as the banner lands
      a.ch("sh").set(t0 + 0.06, 0);
      a.ch("sh").add(t0 + 0.06, 0.7, 1, "power2.inOut", 0);
      a.ch("sh").set(t0 + 0.77, -1);
    }
  };

  // move a banner to a new pose (scatter / fling)
  P.moveTo = function (it, t, p, dur, ease) {
    var a = it.a;
    a.ch("x").add(t, dur, p.x, ease || "expo.out");
    a.ch("y").add(t, dur, p.y, ease || "expo.out");
    a.ch("s").add(t, dur, p.s, ease || "expo.out");
    a.ch("r").add(t, dur, p.r, ease || "expo.out");
  };
  // temporary shove on the inner channel (a shockwave), back to rest
  P.shove = function (it, t, dx, dy, dr) {
    var a = it.a;
    a.ch("jx").add(t, 0.09, dx, "power2.out");
    a.ch("jy").add(t, 0.09, dy, "power2.out");
    a.ch("jr").add(t, 0.09, dr || 0, "power2.out");
    a.ch("jx").add(t + 0.09, 0.42, 0, "power3.inOut");
    a.ch("jy").add(t + 0.09, 0.42, 0, "power3.inOut");
    a.ch("jr").add(t + 0.09, 0.42, 0, "power3.inOut");
  };
  // white edge-glow flash on every banner that is up at t
  P.flash = function (t) {
    var t0 = WA.hit(t);
    for (var i = 0; i < this.items.length; i++) {
      var a = this.items[i].a;
      if (this.items[i].born > t + 0.01) continue;
      a.ch("g").add(t0, 0.001, this.items[i].ghost ? 0.5 : 1, "none", 0);
      a.ch("g").add(t0 + 0.034, 0.24, 0, "power2.out");
    }
  };
  // everything is sucked into (cx, cy) and gone by tGone
  P.collapse = function (t0, tGone, cx, cy) {
    for (var i = 0; i < this.items.length; i++) {
      var it = this.items[i];
      var a = it.a;
      var r = WA.rng(9973 * (i + 1));
      var tc = t0 + 0.05 * r();
      var du = tGone - 0.03 - tc;
      var cur = a.pose(tc);
      a.mbMax = 20;
      a.ch("x").add(tc, du, cx, "power3.in");
      a.ch("y").add(tc, du, cy, "power3.in");
      a.ch("s").add(tc, du, 0.04, "power2.in");
      a.ch("r").add(tc, du, cur.r + (r() < 0.5 ? -1 : 1) * (70 + 90 * r()), "power2.in");
      a.ch("o").add(tGone - 0.12, 0.1, 0, "power1.in");
    }
  };

  /* ---------- per-frame ---------- */
  P.apply = function (t) {
    var wt = this.wt;
    var tf = "translate(" + wt.x.at(t).toFixed(2) + "px," + wt.y.at(t).toFixed(2) + "px) rotate(" + wt.r.at(t).toFixed(3) + "deg) scale(" + wt.s.at(t).toFixed(4) + ")";
    if (tf !== this._wtf) {
      this.world.style.transform = tf;
      this._wtf = tf;
    }
    for (var i = 0; i < this.items.length; i++) {
      var it = this.items[i];
      it.a.apply(t);
      if (it.pill !== null && t >= it.born) {
        var n = it.pill + Math.floor(Math.max(0, t - it.born - 0.4) * it.rate);
        if (this.countUp) n += this.countUp(t, it);
        it.k.setPill(n);
      }
    }
  };

  WA.Storm = Storm;
})(window);
