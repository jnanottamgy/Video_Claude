/* motion.js: seek-order-proof keyframe tracks for HyperFrames (reveal slots).
   Every animated value is a pure function of time: a Track is a list of eased segments; a Rig is a set
   of tracks applied to one element by a style writer. ONE linear GSAP driver tween calls render(t),
   so any seek, in any order, paints identical pixels. Eases come from gsap.parseEase.
   Deterministic: no clocks, no Math.random (MO.rng is a seeded mulberry32, MO.hash an integer hash). */
(function (g) {
  "use strict";
  var MO = {};
  MO.FPS = 30;
  MO.EPS = 0.004;
  /* the start time of an event whose first visible frame is frame k */
  MO.hit = function (k) {
    return k / MO.FPS - MO.EPS;
  };

  MO.rng = function (seed) {
    var a = seed >>> 0;
    return function () {
      a = (a + 0x6d2b79f5) >>> 0;
      var t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  };
  MO.hash = function (a, b) {
    var h = Math.imul(a | 0, 374761393) ^ Math.imul((b | 0) + 1013, 668265263);
    h = Math.imul(h ^ (h >>> 13), 1274126177);
    h ^= h >>> 16;
    return (h >>> 0) / 4294967296;
  };
  MO.clamp01 = function (x) {
    return x < 0 ? 0 : x > 1 ? 1 : x;
  };
  MO.seg = function (t, t0, dur) {
    return MO.clamp01((t - t0) / dur);
  };
  var cache = {};
  MO.ease = function (e) {
    if (typeof e === "function") return e;
    if (!e || e === "none" || e === "linear") return function (p) { return p; };
    return cache[e] || (cache[e] = gsap.parseEase(e));
  };
  MO.lerp = function (a, b, p) {
    return a + (b - a) * p;
  };

  /* ---- Track: add segments in time order; `from` defaults to the value the track already has at t0 ---- */
  function Track(init) {
    this.init = init;
    this.segs = [];
  }
  Track.prototype.at = function (t) {
    var s = this.segs;
    var v = this.init;
    for (var i = 0; i < s.length; i++) {
      var q = s[i];
      if (t < q.t0) break;
      if (t >= q.t0 + q.dur) v = q.to;
      else v = q.f + (q.to - q.f) * q.e((t - q.t0) / q.dur);
    }
    return v;
  };
  Track.prototype.to = function (t0, dur, to, ease, from) {
    var f = from === undefined ? this.at(t0) : from;
    var q = { t0: t0, dur: Math.max(1e-4, dur), f: f, to: to, e: MO.ease(ease) };
    var i = this.segs.length;
    while (i > 0 && this.segs[i - 1].t0 > t0) i--;
    this.segs.splice(i, 0, q);
    return this;
  };
  Track.prototype.set = function (t0, v) {
    return this.to(t0, 1e-4, v, "none", v);
  };
  MO.Track = Track;

  /* ---- Rig: named tracks on one element ---- */
  function Rig(el, init, write) {
    this.el = typeof el === "string" ? document.querySelector(el) : el;
    this.tr = {};
    for (var k in init) this.tr[k] = new Track(init[k]);
    this.write = write || MO.std;
    this.last = {};
  }
  Rig.prototype.to = function (ch, t0, dur, v, ease, from) {
    this.tr[ch].to(t0, dur, v, ease, from);
    return this;
  };
  Rig.prototype.set = function (ch, t0, v) {
    this.tr[ch].set(t0, v);
    return this;
  };
  Rig.prototype.val = function (ch, t) {
    return this.tr[ch].at(t);
  };
  Rig.prototype.apply = function (t) {
    var v = {};
    for (var k in this.tr) v[k] = this.tr[k].at(t);
    this.write(this, v);
  };
  Rig.prototype.css = function (prop, s) {
    if (this.last[prop] !== s) {
      this.el.style[prop] = s;
      this.last[prop] = s;
    }
  };
  MO.Rig = Rig;
  MO.rig = function (el, init, write) {
    return new Rig(el, init, write);
  };

  /* standard writer. channels (all optional): o opacity · x y (px) · xp yp (percent) · r (deg) · s, sx, sy (scale)
     · b blur px · br brightness · sa saturate */
  MO.std = function (rig, v) {
    if ("o" in v) {
      var o = v.o;
      rig.css("opacity", o >= 0.999 ? "1" : o <= 0.001 ? "0" : o.toFixed(3));
      rig.css("visibility", o <= 0.001 ? "hidden" : "visible");
      if (o <= 0.001) return;
    }
    var tf = "";
    if ("xp" in v || "yp" in v) tf += "translate(" + (v.xp || 0).toFixed(2) + "%," + (v.yp || 0).toFixed(2) + "%) ";
    if ("x" in v || "y" in v) tf += "translate(" + (v.x || 0).toFixed(2) + "px," + (v.y || 0).toFixed(2) + "px) ";
    if ("r" in v) tf += "rotate(" + v.r.toFixed(3) + "deg) ";
    if ("s" in v) tf += "scale(" + v.s.toFixed(4) + ") ";
    if ("sx" in v || "sy" in v) tf += "scale(" + ("sx" in v ? v.sx : 1).toFixed(4) + "," + ("sy" in v ? v.sy : 1).toFixed(4) + ") ";
    if (tf) rig.css("transform", tf.trim());
    var fl = "";
    if ("b" in v && v.b > 0.05) fl += "blur(" + v.b.toFixed(2) + "px) ";
    if ("br" in v) fl += "brightness(" + v.br.toFixed(3) + ") ";
    if ("sa" in v) fl += "saturate(" + v.sa.toFixed(3) + ") ";
    if ("b" in v || "br" in v || "sa" in v) rig.css("filter", fl ? fl.trim() : "none");
  };

  /* an attack/decay pulse added to a track: up to `peak` in `att` s, back to `rest` in `dec` s */
  MO.pulse = function (track, t0, peak, att, dec, rest, easeUp, easeDown) {
    track.to(t0, att, peak, easeUp || "power2.out");
    track.to(t0 + att, dec, rest, easeDown || "power2.inOut");
    return track;
  };

  g.MO = MO;
})(window);
