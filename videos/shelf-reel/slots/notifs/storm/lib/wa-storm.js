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
    // banner edges (their shadow then ends before the caption band at 1290)
    this.safe = o.safe || { x0: 66, x1: 1014, y0: 274, y1: 1240, railX: 938, railY: 1100 };
    this.peak = o.peak || { s: 1, r: 0, dx: 0, dy: 0 };
    this.zones = []; // keep-clear rects (faces): {x0, y0, x1, y1, t0, t1}; no banner may rest on one
    this.ghostZones = []; // rects (the hook title) only ghost banners (opacity <= cap) may enter
    this.items = [];
    this.cell = 12;
    // world transform: drift x/y, rotation, scale, and a separate jolt multiplier for punches
    this.wt = { x: new WA.Track(0), y: new WA.Track(0), r: new WA.Track(0), s: new WA.Track(1), j: new WA.Track(1) };
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
  // what the compositor's detector sees as covered at t: every banner plus the reach of its drop
  // shadow (in a dense pile neighbouring shadows stack above 50 % alpha and fill the gaps)
  P.grid = function (t, skip) {
    var S = this.safe;
    var c = this.cell;
    var nx = Math.ceil((S.x1 - S.x0) / c);
    var ny = Math.ceil((S.y1 - S.y0) / c);
    var G = { g: new Uint8Array(nx * ny), nx: nx, ny: ny };
    for (var i = 0; i < this.items.length; i++) {
      var it = this.items[i];
      if (it === skip || it.ghost || it.born > t + 1e-6) continue;
      if (it.a.ch("o").at(t) < 0.6) continue;
      var p = it.a.pose(t);
      this.raster(G, p.x, p.y, p.s, p.r, it.h, true, this.shadowReach);
    }
    return G;
  };
  P.shadowReach = 14;
  P.raster = function (G, x, y, s, r, h, mark, pad) {
    var S = this.safe;
    var cl = this.cell;
    pad = pad || 0;
    var e = WA.ext(this.W, h, s, r);
    e = { hx: e.hx + pad, hy: e.hy + pad };
    var a = (-r * PI) / 180;
    var c = Math.cos(a);
    var sn = Math.sin(a);
    var hw = (this.W / 2) * s + pad;
    var hh = (h / 2) * s + pad;
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

  // keep-clear zones must also hold for the oversized hit frame and along a move's path
  P.clearPath = function (o, x, y, s, r, h, t) {
    var poses = [];
    if (o.entry) {
      var hp = this.hitPose({ x: x, y: y, s: s, r: r }, o.entry, h);
      poses.push([hp.x, hp.y, hp.s, r + 8]);
      poses.push([hp.x, hp.y, hp.s, r - 8]);
    }
    if (o.entry === "fly" && o.side) {
      // the visible part of a fly-in: from its first frame (~60 % along) to landing
      var side = o.side;
      var ef = WA.ext(this.W, h, s * 1.1, r + 30);
      if (side > 0 && y + ef.hy > this.safe.railY - 30) side = -1;
      var dist = o.dist || 820;
      for (var f = 0; f < 3; f++) {
        var u = 0.6 + 0.15 * f;
        for (var dy = -120; dy <= 120; dy += 240) {
          poses.push([x + side * dist * (1 - u), y + dy * (1 - u), s * (1 + 0.1 * (1 - u)), r + side * 24 * (1 - u)]);
        }
      }
    }
    if (o.from) {
      for (var k = 1; k <= 4; k++) {
        var u = k / 5;
        poses.push([o.from.x + (x - o.from.x) * u, o.from.y + (y - o.from.y) * u, o.from.s + (s - o.from.s) * u, o.from.r + (r - o.from.r) * u]);
      }
    }
    for (var i = 0; i < poses.length; i++) {
      var q = poses[i];
      for (var z = 0; z < this.zones.length; z++) {
        var Z = this.zones[z];
        if (Z.t1 > t && Z.t0 < t + 0.6 && this.overlaps(q[0], q[1], q[2], q[3], h, Z)) return false;
      }
    }
    return true;
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
    var tries = o.n || 140;
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
        if (!this.clearPath(o, x, y, s, r, h, t)) continue;
        var score;
        if (o.far) {
          var d = 1e9;
          for (var q = 0; q < o.far.length; q++) d = Math.min(d, Math.hypot((x - o.far[q][0]) / 1.3, y - o.far[q][1]));
          score = d;
        } else {
          // what the detector sees on the hit frame (entry overscale, lift, inward shift)
          var hp = o.entry ? this.hitPose({ x: x, y: y, s: s, r: r }, o.entry, h) : { x: x, y: y, s: s * (o.es || 1) };
          score = this.raster(G, hp.x, hp.y, hp.s * 0.97, r, h, false);
        }
        var nc = o.far ? undefined : score;
        if (o.bias) score *= o.bias(x, y, s, r);
        cands.push({ x: x, y: y, s: s, r: r, score: score, nc: nc });
      }
    }
    if (!cands.length) return null;
    cands.sort(function (a, b) {
      return b.score - a.score;
    });
    // coverage picks must add enough NEW visible area to register as an arrival (the compositor's
    // detector wants > 0.4 % of the frame: ~58 cells of 12 px); keep a margin
    var minNew = o.far ? 0 : o.minNew === undefined ? 100 : o.minNew;
    var good = cands.filter(function (c) {
      return c.nc === undefined || c.nc >= minNew;
    });
    var pool = good.length ? good : cands;
    var k = Math.min(pool.length, o.k || 3);
    return pool[Math.floor(this.rnd() * k)];
  };

  // the legal pose closest to a hand-placed one (spiral search, then smaller); null if none
  P.nearest = function (t, p, h, ghost, until) {
    var u = until === undefined ? t + 1 : until;
    for (var sc = 0; sc < 6; sc++) {
      var s = p.s * Math.pow(0.95, sc);
      for (var rad = 0; rad <= 260; rad += 8) {
        var n = rad === 0 ? 1 : Math.max(8, Math.round(rad / 6));
        for (var i = 0; i < n; i++) {
          var a = (2 * PI * i) / n;
          var x = p.x + rad * Math.cos(a);
          var y = p.y + rad * Math.sin(a);
          if (this.fits(x, y, s, p.r, h, t, u, !ghost)) return { x: x, y: y, s: s, r: p.r };
        }
      }
    }
    if (global.console) console.warn("wa-storm: no legal pose near", p);
    return null;
  };
  // add() for a hand-placed pose, corrected to the nearest legal pose
  P.place = function (key, tHit, pose, entry, opt) {
    var g = opt && opt.ghost;
    var q = this.nearest(tHit, pose, this.hOf(typeof key === "string" ? key : ""), g, opt && opt.until);
    return q ? this.add(key, tHit, q, entry, opt) : null;
  };

  // hit-frame overscale of each entry type (for pick({es}))
  WA.ENTRY_SCALE = { slam: 1.42, pop: 1.26, drop: 1.06, fly: 1.0, burst: 0.6, thru: 0.4 };

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
    cfg.tight = true;
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
    if (!opt.noAge && !it.ghost && (entry || {}).type !== "thru") {
      // older banners sink back into the pile: darker, softer, and a little further away (smaller),
      // which also keeps freeing visible area for the next arrival
      a.ch("d").add(it.born + 0.45, 2.6, opt.dim === undefined ? 0.42 : opt.dim, "sine.inOut", 0);
      a.ch("b").add(it.born + 0.9, 2.4, 1.2, "sine.inOut", 0);
      var age = this.ageScale === undefined ? 0.9 : this.ageScale;
      if (age < 1) a.ch("ag").add(it.born + 0.5, 2.5, age, "sine.inOut", 1);
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
        a.ch("s").add(t0, 0.22, p.s, "power3.out", p.s * 0.3);
        a.ch("r").add(t0, d, p.r, "expo.out", p.r * 0.25 + sg * RR(4, 12));
        a.ch("b").add(t0, 0.3, 0, "power2.out", 9);
        break;
      }
      case "slam": {
        var s0 = Math.min(p.s * 1.42, this.maxHitScale());
        var r0 = p.r + sg * RR(6, 11);
        // expo.out over 0.16 s: ~94 % of the overscale is gone within two frames, so the settle
        // never masks the next arrival (16ths are only three frames apart)
        var lift = { x: p.x, y: p.y - 24 };
        var g0 = this.inward(lift, s0, r0, it.h);
        a.ch("x").add(t0, 0.2, p.x, "expo.out", p.x + g0[0]);
        a.ch("y").add(t0, 0.2, p.y, "expo.out", lift.y + g0[1]);
        a.ch("s").add(t0, 0.16, p.s, "expo.out", s0);
        a.ch("r").add(t0, 0.3, p.r, "expo.out", r0);
        a.ch("b").add(t0, 0.2, 0, "power2.out", 9);
        break;
      }
      case "pop": {
        var s1 = Math.min(p.s * 1.26, this.maxHitScale());
        var r1 = p.r + sg * RR(3, 7);
        var g1 = this.inward(p, s1, r1, it.h);
        if (g1[0] || g1[1]) {
          a.ch("x").add(t0, 0.22, p.x, "expo.out", p.x + g1[0]);
          a.ch("y").add(t0, 0.22, p.y, "expo.out", p.y + g1[1]);
        }
        a.ch("s").add(t0, 0.15, p.s, "expo.out", s1);
        a.ch("r").add(t0, 0.26, p.r, "expo.out", r1);
        a.ch("b").add(t0, 0.17, 0, "power2.out", 6);
        break;
      }
      case "fly": {
        // from off-frame on one side; it starts two frames early so its first visible frame is
        // already mostly in-frame (and registers as an arrival on its beat)
        var t1 = t0 - 2 / WA.FPS;
        var dist = e.dist || 820;
        var ef = WA.ext(this.W, it.h, p.s * 1.1, p.r + 30);
        var fy = p.y + (e.dy || RR(-120, 120));
        fy = Math.max(this.safe.y0 + ef.hy, Math.min(this.safe.y1 - ef.hy, fy));
        var side = e.side;
        if (side > 0 && p.y + ef.hy > this.safe.railY - 30) side = -1; // the rail: come in from the left
        if (side > 0) fy = Math.min(fy, this.safe.railY - ef.hy); // enter above the rail
        a.ch("x").add(t1, 0.5, p.x, "expo.out", p.x + side * dist);
        a.ch("y").add(t1, 0.5, p.y, "expo.out", fy);
        a.ch("r").add(t1, 0.5, p.r, "expo.out", p.r + side * RR(18, 30));
        a.ch("s").add(t1, 0.5, p.s, "expo.out", p.s * 1.1);
        a.ch("b").add(t0, 0.28, 0, "power2.out", 14);
        break;
      }
      case "thru": {
        // blasted out of a point toward the camera and off-frame: it never lands
        var dt = e.dur || 0.36;
        a.ch("x").add(t0, dt, e.to[0], "power2.out", e.from[0]);
        a.ch("y").add(t0, dt, e.to[1], "power2.out", e.from[1]);
        a.ch("s").add(t0, dt, e.sEnd || p.s * 1.5, "power1.out", p.s * 0.35);
        a.ch("r").add(t0, dt, p.r + sg * RR(8, 16), "power1.out", p.r);
        a.ch("b").add(t0, 0.05, 6, "none", 6);
        a.ch("o").set(t0 + dt, 0);
        break;
      }
      case "drop": {
        var v0 = t0 - 0.046;
        var ed = WA.ext(this.W, it.h, p.s * 1.06, p.r);
        var fall = Math.max(40, Math.min(150, p.y - ed.hy - this.safe.y0)); // never starts above the safe top
        a.ch("y").add(v0, 0.7, p.y, WA.springEase(20, 0.66, 0.7), p.y - fall);
        a.ch("s").add(v0, 0.6, p.s, WA.springEase(17, 0.72, 0.6), p.s * 1.06);
        a.ch("b").add(t0, 0.26, 0, "power2.out", 11);
        break;
      }
    }
    a.ch("o").add(t0, 1e-4, it.op, "none", it.op);
    if (!it.ghost && e.type !== "thru") {
      // the unread pill pings as the banner lands
      a.ch("sh").set(t0 + 0.06, 0);
      a.ch("sh").add(t0 + 0.06, 0.7, 1, "power2.inOut", 0);
      a.ch("sh").set(t0 + 0.77, -1);
    }
  };

  // churn: the oldest live solid banner sinks back into the pile and vanishes just before t,
  // making room for the arrival on t (a real notification stack drops its oldest)
  P.recycle = function (t, n) {
    var tt = WA.hit(t);
    for (var c = 0; c < (n || 1); c++) {
      var elig = [];
      for (var i = 0; i < this.items.length; i++) {
        var it = this.items[i];
        if (it.ghost || it.recycled || it.keep || it.born > tt - 0.4) continue;
        if (it.a.ch("o").at(tt - 0.3) < 0.99) continue;
        elig.push(it);
      }
      if (!elig.length) return;
      elig.sort(function (p, q) {
        return p.born - q.born;
      });
      // of the six oldest, the one that frees the most visible area when it goes
      var old = null;
      var best = -1;
      for (var e = 0; e < Math.min(6, elig.length); e++) {
        var G = this.grid(tt + 0.3, elig[e]);
        var pp = elig[e].a.pose(tt + 0.3);
        var exp = this.raster(G, pp.x, pp.y, pp.s, pp.r, elig[e].h, false);
        if (exp > best) {
          best = exp;
          old = elig[e];
        }
      }
      old.recycled = true;
      var a = old.a;
      // it darkens into the pile first (no change in visible area), then sinks away in the two
      // frames right before the arrival, so the area it frees never masks a neighbouring beat
      // all of its change in visible area falls strictly between the previous arrival frame and
      // this one (frames k-2 -> k-1), never on an arrival frame
      var tv = WA.snap(t) - 2 / WA.FPS + 0.002;
      var dv = 1 / WA.FPS - 0.006;
      a.ch("d").add(tt - 0.3, 0.24, 0.8, "power1.out");
      a.ch("s").add(tv, dv, a.ch("s").at(tv) * 0.85, "power2.in");
      a.ch("o").add(tv, dv, 0, "power1.in");
    }
  };

  // the largest scale whose hit frame still fits the safe width under the peak world transform
  P.maxHitScale = function () {
    var w = ((this.safe.x1 - this.safe.x0) / this.peak.s - 24) / this.W;
    return Math.max(1, Math.min(1.32, w));
  };
  // where and how big a banner is on its first (hit) frame, per entry type: the planner scores
  // this footprint, so it matches what the compositor's detector actually sees
  P.hitPose = function (p, type, h) {
    if (type === "slam") {
      var s0 = Math.min(p.s * 1.42, this.maxHitScale());
      var lift = { x: p.x, y: p.y - 24 };
      var g0 = this.inward(lift, s0, p.r, h);
      return { x: p.x + g0[0], y: lift.y + g0[1], s: s0 };
    }
    if (type === "pop") {
      var s1 = Math.min(p.s * 1.26, this.maxHitScale());
      var g1 = this.inward(p, s1, p.r, h);
      return { x: p.x + g1[0], y: p.y + g1[1], s: s1 };
    }
    return { x: p.x, y: p.y, s: p.s * (WA.ENTRY_SCALE[type] || 1) };
  };

  // offset that keeps an oversized entry frame (scale s0, rotation r0) inside the safe rect: the
  // banner grows inward from the edge instead of spilling over it
  P.inward = function (p, s0, r0, h) {
    var S0 = this.safe;
    var k = this.peak.s;
    var m = (this.W / 2) * s0 * Math.sin((Math.abs(this.peak.r) * PI) / 180); // rotation margin
    var S = {
      x0: this.CX - (this.CX - S0.x0) / k + 8 + Math.abs(this.peak.dx || 0),
      x1: this.CX + (S0.x1 - this.CX) / k - 8 - Math.abs(this.peak.dx || 0),
      y0: this.CY - (this.CY - S0.y0) / k + m,
      y1: this.CY + (S0.y1 - this.CY) / k - m,
      railX: this.CX + (S0.railX - this.CX) / k - 8,
      railY: this.CY + (S0.railY - this.CY) / k - m,
    };
    var e = WA.ext(this.W, h, s0, r0);
    var dx = 0;
    var dy = 0;
    if (p.x - e.hx < S.x0) dx = S.x0 - (p.x - e.hx);
    else if (p.x + e.hx > S.x1) dx = S.x1 - (p.x + e.hx);
    if (p.y - e.hy < S.y0) dy = S.y0 - (p.y - e.hy);
    else if (p.y + e.hy > S.y1) dy = S.y1 - (p.y + e.hy);
    // the like/comment rail: nothing right of railX below railY
    if (p.y + dy + e.hy > S.railY && p.x + dx + e.hx > S.railX) dx = Math.min(dx, S.railX - (p.x + e.hx));
    return [dx, dy];
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
  // (dx, dy) is a SCREEN-space push; it is shortened until the pushed banner stays inside y 280-1240,
  // x 30-1050 and out of the keep-clear zones, then converted into the card's local (rotated, scaled) space
  P.shove = function (it, t, dx, dy, dr, out, back) {
    var a = it.a;
    out = out || 0.09;
    back = back || 0.42;
    var p = a.pose(t + out);
    // test the push over its whole life (the banner may still be travelling): peak, then decaying
    var samples = [[t + out * 0.6, 0.85], [t + out, 1], [t + out + back * 0.2, 0.9], [t + out + back * 0.4, 0.65], [t + out + back * 0.6, 0.35]];
    var k = 1;
    for (; k > 0.01; k -= 0.1) {
      var ok = true;
      for (var m = 0; m < samples.length && ok; m++) {
        var ps = a.pose(samples[m][0]);
        var amp = k * samples[m][1];
        var pts = this.points(ps.x + dx * amp, ps.y + dy * amp, ps.s, ps.r + (dr || 0) * samples[m][1], it.h, 6);
        for (var i = 0; i < pts.length && ok; i++) {
          var q = pts[i];
          if (q[1] < 280 || q[1] > 1240 || q[0] < 30 || q[0] > 1050) ok = false;
          for (var z = 0; z < this.zones.length && ok; z++) {
            var Z = this.zones[z];
            if (Z.t1 > t && Z.t0 <= t && inRect(q, Z)) ok = false;
          }
        }
      }
      if (ok) break;
    }
    k = Math.max(0, k);
    var ang = (-p.r * PI) / 180;
    var lx = ((dx * Math.cos(ang) - dy * Math.sin(ang)) * k) / p.s;
    var ly = ((dx * Math.sin(ang) + dy * Math.cos(ang)) * k) / p.s;
    a.ch("jx").add(t, out, lx, "power2.out");
    a.ch("jy").add(t, out, ly, "power2.out");
    a.ch("jr").add(t, out, dr || 0, "power2.out");
    a.ch("jx").add(t + out, back, 0, "power3.inOut");
    a.ch("jy").add(t + out, back, 0, "power3.inOut");
    a.ch("jr").add(t + out, back, 0, "power3.inOut");
  };
  // a whole-layer scale punch: peak on the hit frame, back to 1 over `frames` frames (default 2, so
  // the punch reads 1.0 -> peak -> mid -> 1.0 and never masks an arrival three frames later)
  P.jolt = function (t, peak, frames) {
    var t0 = WA.hit(t);
    this.wt.j.add(t0, 0.001, peak, "none", 1);
    this.wt.j.add(t0 + 0.004, (frames || 2) / WA.FPS - 0.002, 1, "power2.out", peak);
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
      a.ch("x").add(tc, du, cx, "power2.in");
      a.ch("y").add(tc, du, cy, "power2.in");
      a.ch("s").add(tc, du, 0.04, "power1.in");
      a.ch("r").add(tc, du, cur.r + (r() < 0.5 ? -1 : 1) * (40 + 30 * r()), "power3.in");
      a.ch("o").add(tGone - 0.12, 0.1, 0, "power1.in");
    }
  };

  /* ---------- per-frame ---------- */
  P.apply = function (t) {
    var wt = this.wt;
    var tf = "translate(" + wt.x.at(t).toFixed(2) + "px," + wt.y.at(t).toFixed(2) + "px) rotate(" + wt.r.at(t).toFixed(3) + "deg) scale(" + (wt.s.at(t) * wt.j.at(t)).toFixed(4) + ")";
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
