/* notif-storm.js — the notification STORM engine shared by notifs/storm and notifs/storm_hook.
   Master copy lives in slots/notifs/_shared/; each project carries its own copy in lib/.

   The cold open (storm_hook, output 0.000-3.467) plays the SAME footage as the storm's
   44.400-47.867, so both are built from one deterministic plan: the hook is the storm's
   first beats shifted +0.2 s, stopped full (no pileup, no collapse).

   Times below are STORM-local seconds (= output time - 44.600). Word cues (words.json):
     What 0.053 · the 0.32 · f*ck 0.60 · why 0.983 · are 1.10 · my 1.34 · notes 1.46
     scattered 1.763 · in 2.17 · so 2.30 · many 2.603 · groups? 3.05 (ends 3.267)
     48.033 cut to head-in-hand (3.433) · pileup accelerates to 6.80 · collapse 6.85-7.20

   Built on NK (notif-kit.js). Deterministic: seeded PRNG only. */
(function (global) {
  "use strict";
  var NK = global.NK;

  var W = 700; // storm banner width (same card design, narrower than the 940 lock-screen card)
  var H = 150;
  var CX = 540; // storm centre = world transform origin (vertigo / collapse pivot)
  var CY = 760;
  // safe area, pulled in so the vertigo (rotate 3deg, scale 1.045 about CX,CY) stays inside
  // the reel's safe zones and never touches the caption band (1290-1460) or the right rail.
  var B = { x0: 84, x1: 996, y0: 292, y1: 1212, railY: 1100, railX: 932 };
  // laptop shot (44.40-48.03 and the cold open): his eyes / nose / mouth / hand stay clear
  var FACE = { x0: 690, x1: 950, y0: 806, y1: 1088 };

  var C = {
    cr: { app: "unofficial", sender: "CR:", msg: "all the notes, units 1-5", badge: 12 },
    teacher: { app: "official", sender: "Teacher:", msg: "syllabus copy attached", badge: 48 },
    zaid: { app: "boys", sender: "Zaid:", msg: "solved PYQs", badge: 99 },
    notes: { app: "pdf", msg: "Notes_FINAL_v3.pdf", mono: true, time: "2m" },
    bro: { app: "ishaan", msg: "bro check the group", badge: 3 },
    unit3: { app: "boys", msg: "who has unit 3??", badge: 23 },
    u47: { app: "unofficial", msg: "47 new messages", badge: 47 },
    exam: { app: "reminder", sender: "EXAM", msg: "in 8 hours", time: "now" },
    img4: { app: "img", msg: "notes_unit4 (1).jpg", mono: true, time: "1m" },
    o128: { app: "official", msg: "128 new messages", badge: 99 },
    fwd: { app: "mail", msg: "Fwd: Fwd: notes", badge: 7, time: "5m" },
    pyq: { app: "boys", sender: "Zaid:", msg: "PYQ_2022 (blurry).jpg", badge: 31 },
    due: { app: "calendar", msg: "Assignment due 11:59 PM", time: "now" },
    voice: { app: "ishaan", msg: "voice message (0:42)", badge: 4, time: "1m" },
    syl: { app: "pdf", msg: "Syllabus copy.pdf", mono: true, time: "now" },
    study: { app: "reminder", msg: "did you study??", time: "now" },
  };
  var GROUPS = [C.u47, C.o128, C.unit3, C.cr, C.teacher, C.zaid, C.pyq, C.u47, C.o128, C.unit3, C.zaid, C.teacher];

  var POOL = [
    { app: "unofficial", sender: "CR:", msg: "all the notes, units 1-5", badge: 12 },
    { app: "official", sender: "Teacher:", msg: "syllabus copy attached", badge: 48 },
    { app: "boys", sender: "Zaid:", msg: "solved PYQs", badge: 99 },
    { app: "pdf", msg: "Notes_FINAL_v3.pdf", mono: true, time: "2m" },
    { app: "ishaan", msg: "bro check the group", badge: 3 },
    { app: "boys", msg: "who has unit 3??", badge: 23 },
    { app: "unofficial", msg: "47 new messages", badge: 47 },
    { app: "reminder", sender: "EXAM", msg: "in 8 hours", time: "now" },
    { app: "img", msg: "notes_unit4 (1).jpg", mono: true, time: "1m" },
    { app: "official", msg: "128 new messages", badge: 99 },
    { app: "mail", msg: "Fwd: Fwd: notes", badge: 7, time: "5m" },
    { app: "boys", sender: "Zaid:", msg: "PYQ_2022 (blurry).jpg", badge: 31 },
    { app: "calendar", msg: "Assignment due 11:59 PM", time: "now" },
    { app: "ishaan", msg: "voice message (0:42)", badge: 4, time: "1m" },
    { app: "pdf", msg: "Syllabus copy.pdf", mono: true, time: "now" },
    { app: "reminder", msg: "did you study??", time: "now" },
  ];

  /* opt = { off: seconds added to every storm-local time (hook: 0.2),
             full: true -> pileup + vertigo + collapse (storm), false -> stop full at 3.267 (hook),
             seed } */
  NK.buildStorm = function (tl, world, opt) {
    var OFF = opt.off || 0;
    var FULL = !!opt.full;
    var rnd = NK.rng(opt.seed || 4465);
    function R(a, b) {
      return a + (b - a) * rnd();
    }
    function sgn() {
      return rnd() < 0.5 ? -1 : 1;
    }

    function fits(cx, cy, s, r, face) {
      var e = NK.ext(W, H, s, r);
      var x0 = cx - e.hx;
      var x1 = cx + e.hx;
      var y0 = cy - e.hy;
      var y1 = cy + e.hy;
      if (x0 < B.x0 || x1 > B.x1 || y0 < B.y0 || y1 > B.y1) return false;
      if (y1 > B.railY && x1 > B.railX) return false;
      if (face && x1 > FACE.x0 && x0 < FACE.x1 && y1 > FACE.y0 && y0 < FACE.y1) return false;
      return true;
    }

    var cards = [];
    var poolIdx = 0;
    var order = [];
    function nextContent() {
      // seeded shuffles of the whole pool
      while (order.length <= poolIdx) {
        var idx = POOL.map(function (_, i) {
          return i;
        });
        for (var i = idx.length - 1; i > 0; i--) {
          var j = Math.floor(rnd() * (i + 1));
          var tmp = idx[i];
          idx[i] = idx[j];
          idx[j] = tmp;
        }
        if (order.length && idx[0] === order[order.length - 1]) idx.push(idx.shift());
        order = order.concat(idx);
      }
      return POOL[order[poolIdx++]];
    }

    // candidate grid points (feasibility is checked per card size / rotation)
    function candidates(s, r, face, step) {
      var out = [];
      var e = NK.ext(W, H, s, r);
      step = step || 18;
      for (var y = B.y0 + e.hy; y <= B.y1 - e.hy; y += step) {
        for (var x = B.x0 + e.hx; x <= B.x1 - e.hx; x += step) {
          if (fits(x, y, s, r, face)) out.push([x, y]);
        }
      }
      return out;
    }
    function minDist(x, y, pts, ax) {
      var d = 1e9;
      for (var q = 0; q < pts.length; q++) {
        var dd = Math.hypot((x - pts[q][0]) / ax, y - pts[q][1]);
        if (dd < d) d = dd;
      }
      return d;
    }

    // one card: content + landing pose; c.cur tracks the pose for later moves
    function newCard(t, x, y, s, r, entry, content) {
      content = content || nextContent();
      var c = {
        t: t,
        cx: x,
        cy: y,
        s: s,
        r: r,
        entry: entry,
        spec: {
          app: content.app,
          sender: content.sender,
          msg: content.msg,
          mono: content.mono,
          time: content.time || (rnd() < 0.7 ? "now" : "1m"),
          badge: content.badge === undefined ? null : content.badge,
          w: W,
          h: H,
        },
        px: x,
        py: y,
        cur: { x: 0, y: 0, s: s, r: r },
        moves: [],
      };
      cards.push(c);
      return c;
    }

    // farthest-point pick among candidates (optionally inside a ring around the centre)
    function pickFar(s, r, face, seeds, ring) {
      var cs = candidates(s, r, face);
      var best = null;
      var bestD = -1;
      for (var i = 0; i < cs.length; i++) {
        var x = cs[i][0] + R(-6, 6);
        var y = cs[i][1] + R(-6, 6);
        if (!fits(x, y, s, r, face)) continue;
        if (ring) {
          var dc = Math.hypot(x - CX, y - CY);
          if (dc < ring[0] || dc > ring[1]) continue;
        }
        var d = minDist(x, y, seeds, 1.25);
        if (d > bestD) {
          bestD = d;
          best = [x, y];
        }
      }
      return best;
    }
    // best-candidate pick for pileups: random candidates, far from the most recent cards
    function pickRecent(s, r, face, recentN, k, centreBias) {
      var cs = candidates(s, r, face, 16);
      if (!cs.length) return null;
      var recent = cards.slice(-recentN).map(function (c) {
        return [c.px, c.py];
      });
      var best = null;
      var bestD = -1;
      for (var i = 0; i < k; i++) {
        var p = cs[Math.floor(rnd() * cs.length)];
        var x = p[0] + R(-7, 7);
        var y = p[1] + R(-7, 7);
        if (!fits(x, y, s, r, face)) continue;
        var d = recent.length ? minDist(x, y, recent, 1.35) : 1e9;
        if (centreBias) {
          // denser middle, ragged edge: discount spots near the border of the safe area
          var ex = Math.abs(x - CX) / ((B.x1 - B.x0) / 2);
          var ey = Math.abs(y - CY) / ((B.y1 - B.y0) / 2);
          d *= 1 - centreBias * Math.min(1, Math.max(ex, ey));
        }
        if (d > bestD) {
          bestD = d;
          best = [x, y];
        }
      }
      return best;
    }
    function addFar(t, s, r, entry, face, seeds, ring, content) {
      var p = null;
      for (var tries = 0; tries < 4 && !p; tries++) {
        p = pickFar(s, r, face, seeds, ring);
        if (!p) s *= 0.92;
      }
      if (!p) p = [CX - 200, 420];
      seeds.push(p);
      return newCard(t, p[0], p[1], s, r, entry, content);
    }
    function addPile(t, s, r, entry, face, recentN, content, centreBias) {
      var p = null;
      for (var tries = 0; tries < 4 && !p; tries++) {
        p = pickRecent(s, r, face, recentN || 12, 22, centreBias);
        if (!p) s *= 0.92;
      }
      if (!p) p = [CX - 200, 420];
      return newCard(t, p[0], p[1], s, r, entry, content);
    }
    // hero card: the legal spot nearest to a designed target
    function addHero(t, s, r, entry, face, target, content) {
      var best = null;
      for (var tries = 0; tries < 5 && !best; tries++) {
        var cs = candidates(s, r, face, 10);
        var bd = 1e9;
        for (var i = 0; i < cs.length; i++) {
          var dd = Math.hypot(cs[i][0] - target[0], cs[i][1] - target[1]);
          if (dd < bd) {
            bd = dd;
            best = cs[i];
          }
        }
        if (!best) s *= 0.93;
      }
      if (!best) best = target;
      return newCard(t, best[0], best[1], s, r, entry, content);
    }

    /* ---------------- the plan (storm-local times) ---------------- */
    var T_WHAT = 0.053;
    var T_FCK = 0.6;
    var T_WHY = 0.983;
    var T_SCAT = 1.763;
    var T_MANY = 2.603;
    var T_CUT2 = 3.433; // head-in-hand shot
    var T_PEAK = 6.8;
    var T_SUCK = 6.85;
    var T_GONE = 7.2;

    // 1) "What": burst of 7 from the centre to a balanced ring around it
    var seeds1 = [[CX, CY]];
    var burst = [C.cr, C.teacher, C.zaid, C.bro, C.img4, C.u47, C.fwd];
    for (var i = 0; i < 7; i++) {
      var s1 = i < 3 ? R(0.84, 0.94) : R(0.68, 0.82);
      addFar(T_WHAT + i * 0.016, s1, sgn() * R(2, 9), "burst", true, seeds1, [170, 410], burst[i]);
    }
    // 2) "f*ck": the EXAM reminder slams in big, near the camera; a smaller one follows
    addHero(T_FCK, 1.0, -4, "slam", true, [430, 640], C.exam);
    addHero(T_FCK + 0.07, 0.66, 7, "slam", true, [800, 430], C.study);
    // 3) "why are my notes" -> the notes file lands on "notes"
    addPile(T_WHY, R(0.66, 0.8), sgn() * R(3, 12), "slam", true, 11, C.voice);
    addPile(1.34, R(0.64, 0.78), sgn() * R(3, 12), "slam", true, 11, C.o128);
    addHero(1.46, 0.78, 5, "slam", true, [380, 930], C.notes);
    // 4) "scattered": everything is flung out to every corner (rot -14..14, scale 0.55-1.0)
    var existing = cards.slice();
    var seeds4 = [[CX, CY]];
    // biggest first: they have the fewest legal spots
    existing
      .map(function (c, k) {
        return { c: c, k: k, s2: R(0.55, 1.0), r2: sgn() * R(5, 14) };
      })
      .sort(function (a, b) {
        return b.s2 - a.s2;
      })
      .forEach(function (o) {
        var c = o.c;
        var dx = c.px - CX;
        var dy = c.py - CY;
        var len = Math.hypot(dx, dy) || 1;
        dx /= len;
        dy /= len;
        var s2 = o.s2;
        var cs = [];
        for (var tries = 0; tries < 5 && !cs.length; tries++) {
          cs = candidates(s2, o.r2, true, 16);
          if (!cs.length) s2 = Math.max(0.55, s2 * 0.9);
        }
        var best = null;
        var bestS = -1e9;
        for (var q = 0; q < cs.length; q++) {
          var x = cs[q][0];
          var y = cs[q][1];
          var out = (x - c.px) * dx + (y - c.py) * dy; // keep the motion outward
          var score = minDist(x, y, seeds4, 1.2) + 0.55 * out;
          if (score > bestS) {
            bestS = score;
            best = [x, y];
          }
        }
        if (!best) return;
        seeds4.push(best);
        c.moves.push({ t: T_SCAT + o.k * 0.012, x: best[0] - c.cx, y: best[1] - c.cy, s: s2, r: o.r2 });
        c.px = best[0];
        c.py = best[1];
      });
    // the files themselves fly out with them
    [C.syl, C.pyq, C.due, C.unit3].forEach(function (ct, j) {
      addFar(T_SCAT + 0.03 + j * 0.03, R(0.58, 0.76), sgn() * R(4, 14), "burst", true, seeds4, null, ct);
    });
    // 5) "in so"
    addPile(2.17, R(0.6, 0.74), sgn() * R(3, 14), "slam", true, 14);
    addPile(2.3, R(0.58, 0.7), sgn() * R(3, 14), "slam", true, 14);
    // 6) "many groups?": fast pileup of small group-chat cards
    var t6 = T_MANY;
    var g6 = 0.075;
    for (i = 0; i < 12; i++) {
      addPile(t6, R(0.55, 0.66), sgn() * R(0, 14), "pop", true, 16, GROUPS[i]);
      t6 += g6;
      g6 = Math.max(0.034, g6 * 0.88);
    }

    if (FULL) {
      // 7) head in hand: arrivals keep ACCELERATING (to two per frame); his head may be covered
      var t7 = T_CUT2 + 0.02;
      var g7 = 0.21;
      var n7 = 0;
      while (t7 < T_PEAK) {
        var late = (t7 - T_CUT2) / (T_PEAK - T_CUT2);
        var big = n7 % 4 === 1;
        var s7 = big ? R(0.84, 1.0) : R(0.55, 0.76);
        var kind = n7 % 5 === 3 ? "fly" : big ? "slam" : "pop";
        addPile(t7, s7, sgn() * R(0, 14), kind, false, 14, null, 0.25 + 0.5 * late);
        n7++;
        t7 += g7;
        g7 = Math.max(1 / 30, g7 * 0.915);
        if (t7 > 6.2 && g7 <= 1 / 30 && t7 < T_PEAK) {
          addPile(t7 - 1 / 60, R(0.55, 0.8), sgn() * R(0, 14), "pop", false, 14, null, 0.75);
        }
      }
    }

    /* ---------------- tweens ---------------- */
    cards.forEach(function (c, idx) {
      // per-card PRNG: entry flourishes never shift the shared plan (hook == storm, beat for beat)
      var cr = NK.rng(7919 * (idx + 1));
      function RR(a, b) {
        return a + (b - a) * cr();
      }
      function SG() {
        return cr() < 0.5 ? -1 : 1;
      }
      var k = NK.card(c.spec);
      c.k = k;
      k.el.style.left = (c.cx - W / 2).toFixed(1) + "px";
      k.el.style.top = (c.cy - H / 2).toFixed(1) + "px";
      world.appendChild(k.el);

      var t0 = c.t + OFF;
      var s = c.s;
      var r = c.r;

      // ---- entry ---- (late arrivals are shortened so nothing overlaps the collapse)
      var cap = FULL ? Math.max(0.03, T_SUCK + OFF - t0 - 0.004) : 9;
      function d(v) {
        return Math.min(v, cap);
      }
      if (c.entry === "burst") {
        tl.fromTo(k.el, { x: CX - c.cx, y: CY - c.cy }, { x: 0, y: 0, duration: d(0.62), ease: "expo.out" }, t0);
        tl.fromTo(k.el, { scale: s * 0.3, rotation: 0 }, { scale: s, rotation: r, duration: d(0.55), ease: "back.out(1.5)" }, t0);
        tl.fromTo(k.el, { opacity: 0 }, { opacity: 1, duration: d(0.09), ease: "power1.out" }, t0);
        tl.fromTo(k.el, { filter: "blur(14px)" }, { filter: "blur(0px)", duration: d(0.34), ease: "power2.out" }, t0);
      } else if (c.entry === "slam") {
        tl.fromTo(k.el, { x: 0, y: -26 }, { x: 0, y: 0, duration: d(0.32), ease: "power4.out" }, t0);
        tl.fromTo(k.el, { scale: s * 1.55, rotation: r + SG() * RR(6, 12) }, { scale: s, rotation: r, duration: d(0.32), ease: "power4.out" }, t0);
        tl.fromTo(k.el, { opacity: 0 }, { opacity: 1, duration: d(0.07), ease: "power1.out" }, t0);
        tl.fromTo(k.el, { filter: "blur(12px)" }, { filter: "blur(0px)", duration: d(0.22), ease: "power2.out" }, t0);
      } else if (c.entry === "fly") {
        var side = c.cx < CX ? -1 : 1;
        tl.fromTo(k.el, { x: side * RR(760, 900), y: RR(-160, 160) }, { x: 0, y: 0, duration: d(0.42), ease: "expo.out" }, t0);
        tl.fromTo(k.el, { scale: s * 1.1, rotation: r + side * RR(18, 30) }, { scale: s, rotation: r, duration: d(0.42), ease: "expo.out" }, t0);
        tl.fromTo(k.el, { opacity: 0 }, { opacity: 1, duration: d(0.06), ease: "power1.out" }, t0);
        tl.fromTo(k.el, { filter: "blur(16px)" }, { filter: "blur(0px)", duration: d(0.26), ease: "power2.out" }, t0);
      } else {
        // pop: small fast slam onto the pile
        tl.fromTo(k.el, { scale: s * 1.4, rotation: r + SG() * RR(4, 10) }, { scale: s, rotation: r, duration: d(0.24), ease: "back.out(1.6)" }, t0);
        tl.fromTo(k.el, { opacity: 0 }, { opacity: 1, duration: d(0.06), ease: "power1.out" }, t0);
        tl.fromTo(k.el, { filter: "blur(9px)" }, { filter: "blur(0px)", duration: d(0.17), ease: "power2.out" }, t0);
      }
      // older cards sink into the pile as new ones land on top: darker and softer with age
      tl.fromTo(k.dim, { opacity: 0 }, { opacity: 0.46, duration: 2.4, ease: "sine.inOut" }, t0 + 0.45);
      tl.fromTo(k.fly, { filter: "blur(0px)" }, { filter: "blur(1.6px)", duration: 2.2, ease: "sine.inOut", immediateRender: false }, t0 + 0.8);

      // ---- later moves ("scattered") ----
      c.moves.forEach(function (m) {
        var tm = m.t + OFF;
        tl.fromTo(k.el, { x: c.cur.x, y: c.cur.y }, { x: m.x, y: m.y, duration: 0.62, ease: "expo.out", immediateRender: false }, tm);
        tl.fromTo(
          k.el,
          { scale: c.cur.s, rotation: c.cur.r },
          { scale: m.s, rotation: m.r, duration: 0.62, ease: "expo.out", immediateRender: false },
          tm
        );
        tl.fromTo(k.el, { filter: "blur(10px)" }, { filter: "blur(0px)", duration: 0.3, ease: "power2.out", immediateRender: false }, tm);
        c.cur = { x: m.x, y: m.y, s: m.s, r: m.r };
      });

      // ---- collapse: sucked into the centre ----
      if (FULL) {
        var tc = T_SUCK + OFF + RR(0, 0.05);
        var dur = 0.29;
        tl.fromTo(
          k.el,
          { x: c.cur.x, y: c.cur.y },
          { x: CX - c.cx, y: CY - c.cy, duration: dur, ease: "power3.in", immediateRender: false },
          tc
        );
        tl.fromTo(
          k.el,
          { scale: c.cur.s, rotation: c.cur.r },
          { scale: 0.04, rotation: c.cur.r + SG() * RR(50, 120), duration: dur, ease: "power2.in", immediateRender: false },
          tc
        );
        tl.fromTo(k.el, { filter: "blur(0px)" }, { filter: "blur(10px)", duration: dur, ease: "power2.in", immediateRender: false }, tc);
        tl.fromTo(
          k.el,
          { opacity: 1 },
          { opacity: 0, duration: 0.12, ease: "power1.in", immediateRender: false },
          Math.min(T_GONE + OFF - 0.13, tc + dur - 0.12)
        );
      }
    });

    /* ---------------- whole-storm moves ---------------- */
    // tiny punch on "f*ck" and on "scattered"
    tl.fromTo(world, { scale: 1.035 }, { scale: 1, duration: 0.35, ease: "expo.out", immediateRender: false }, T_FCK + OFF);
    tl.fromTo(world, { scale: 1.03 }, { scale: 1, duration: 0.4, ease: "expo.out", immediateRender: false }, T_SCAT + OFF);
    if (FULL) {
      // vertigo: the whole storm slowly drifts / rotates while the pile grows
      tl.fromTo(
        world,
        { rotation: 0, scale: 1, x: 0 },
        { rotation: 3, scale: 1.045, x: -8, duration: T_SUCK - T_CUT2, ease: "sine.in", immediateRender: false },
        T_CUT2 + OFF
      );
      // collapse: a breath out, then everything spirals into the centre
      tl.fromTo(world, { rotation: 3, scale: 1.045 }, { rotation: 3.6, scale: 1.065, duration: 0.08, ease: "power2.out", immediateRender: false }, T_SUCK + OFF);
      tl.fromTo(world, { rotation: 3.6, scale: 1.065 }, { rotation: 11, scale: 0.88, duration: 0.27, ease: "power3.in", immediateRender: false }, T_SUCK + OFF + 0.08);
    }

    /* ---------------- badges count up (text driven by time) ---------------- */
    var counters = [];
    cards.forEach(function (c, idx) {
      if (typeof c.spec.badge !== "number") return;
      var br = NK.rng(104729 * (idx + 1));
      counters.push({
        k: c.k,
        b0: c.spec.badge,
        t0: c.t + OFF,
        r1: 0.8 + 1.4 * br(), // a few new messages per second while it sits there
        r2: 6 + 8 * br(), // pileup: accelerating count
      });
    });
    function applyState(t) {
      for (var q = 0; q < counters.length; q++) {
        var cn = counters[q];
        var n = cn.b0;
        var dt = t - cn.t0 - 0.45;
        if (dt > 0) n += Math.floor(dt * cn.r1);
        if (FULL) {
          var dp = t - (T_CUT2 + OFF);
          if (dp > 0) n += Math.floor(cn.r2 * dp * dp);
        }
        cn.k.setBadge(n);
      }
    }
    return { cards: cards, applyState: applyState, W: W, H: H, CX: CX, CY: CY };
  };
})(window);
