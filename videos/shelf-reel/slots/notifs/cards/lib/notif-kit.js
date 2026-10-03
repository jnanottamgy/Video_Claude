/* notif-kit.js — shared notification-card factory + helpers for the notifs slot
   (cards / storm / storm_hook). Master copy lives in slots/notifs/_shared/;
   each project carries its own copy in lib/ (run _shared/sync.sh after edits).
   Deterministic: no clocks, no Math.random (use NK.rng, a seeded mulberry32). */
(function (global) {
  "use strict";

  var NK = {};

  /* ---------- seeded PRNG ---------- */
  NK.rng = function (seed) {
    var a = seed >>> 0;
    return function () {
      a = (a + 0x6d2b79f5) >>> 0;
      var t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  };

  /* ---------- generic glyphs (inline SVG, no real brands) ---------- */
  var G = {
    group: function (c) {
      return (
        '<svg viewBox="0 0 48 48" aria-hidden="true">' +
        '<path d="M26 6h10a7 7 0 0 1 7 7v6a7 7 0 0 1-4 6.3l1.6 4.7-5.6-4H26a7 7 0 0 1-7-7v-6a7 7 0 0 1 7-7z" fill="#fff" fill-opacity=".55"/>' +
        '<path d="M12 15h15a8 8 0 0 1 8 8v7a8 8 0 0 1-8 8h-8.5l-7.2 5.6c-.7.5-1.6 0-1.6-.8v-5.2A8 8 0 0 1 4 30v-7a8 8 0 0 1 8-8z" fill="#fff"/>' +
        '<circle cx="12.5" cy="26.5" r="2.4" fill="' + c + '"/>' +
        '<circle cx="19.5" cy="26.5" r="2.4" fill="' + c + '"/>' +
        '<circle cx="26.5" cy="26.5" r="2.4" fill="' + c + '"/>' +
        "</svg>"
      );
    },
    person: function () {
      return (
        '<svg viewBox="0 0 48 48" aria-hidden="true">' +
        '<circle cx="24" cy="18" r="8.6" fill="#fff"/>' +
        '<path d="M8.5 41.5c1.4-8.4 8-13 15.5-13s14.1 4.6 15.5 13z" fill="#fff"/>' +
        "</svg>"
      );
    },
    pdf: function (c) {
      return (
        '<svg viewBox="0 0 48 48" aria-hidden="true">' +
        '<path d="M14 4.5h14.5L38 14v27.5a3 3 0 0 1-3 3H14a3 3 0 0 1-3-3v-34a3 3 0 0 1 3-3z" fill="#fff"/>' +
        '<path d="M28.5 4.5V12a2 2 0 0 0 2 2H38z" fill="#ffc9c4"/>' +
        '<rect x="15" y="19" width="14" height="2.6" rx="1.3" fill="#ffc9c4"/>' +
        '<rect x="15" y="24" width="18" height="2.6" rx="1.3" fill="#ffc9c4"/>' +
        '<text x="24.5" y="39.5" text-anchor="middle" font-family="Inter, sans-serif" font-weight="800" font-size="10.5" fill="' + c + '">PDF</text>' +
        "</svg>"
      );
    },
    img: function (c) {
      return (
        '<svg viewBox="0 0 48 48" aria-hidden="true">' +
        '<path d="M14 4.5h14.5L38 14v27.5a3 3 0 0 1-3 3H14a3 3 0 0 1-3-3v-34a3 3 0 0 1 3-3z" fill="#fff"/>' +
        '<path d="M28.5 4.5V12a2 2 0 0 0 2 2H38z" fill="#c7dcff"/>' +
        '<circle cx="19.5" cy="23" r="3.3" fill="' + c + '"/>' +
        '<path d="M14 40l7.4-9.4 5 5.8 3.5-4 6.1 7.6z" fill="' + c + '"/>' +
        "</svg>"
      );
    },
    bell: function () {
      return (
        '<svg viewBox="0 0 48 48" aria-hidden="true">' +
        '<path d="M24 5.5a2.6 2.6 0 0 1 2.6 2.6v1.3c5.4 1.2 8.9 5.7 8.9 11.3v7.6l3.4 4.6v2.4H9.1v-2.4l3.4-4.6v-7.6c0-5.6 3.5-10.1 8.9-11.3V8.1A2.6 2.6 0 0 1 24 5.5z" fill="#1c1c1e"/>' +
        '<path d="M19.4 37.6h9.2a4.6 4.6 0 0 1-9.2 0z" fill="#1c1c1e"/>' +
        "</svg>"
      );
    },
    mail: function (c) {
      return (
        '<svg viewBox="0 0 48 48" aria-hidden="true">' +
        '<rect x="6" y="11" width="36" height="26" rx="5" fill="#fff"/>' +
        '<path d="M9 15l15 11.5L39 15" fill="none" stroke="' + c + '" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>' +
        "</svg>"
      );
    },
    cal: function (c) {
      return (
        '<svg viewBox="0 0 48 48" aria-hidden="true">' +
        '<rect x="7" y="9" width="34" height="32" rx="6" fill="#fff"/>' +
        '<path d="M13 9h22a6 6 0 0 1 6 6v4H7v-4a6 6 0 0 1 6-6z" fill="#e9d0fb"/>' +
        '<rect x="14" y="5" width="4.2" height="9" rx="2.1" fill="#fff" stroke="' + c + '" stroke-width="1.4"/>' +
        '<rect x="29.8" y="5" width="4.2" height="9" rx="2.1" fill="#fff" stroke="' + c + '" stroke-width="1.4"/>' +
        '<rect x="12" y="23" width="6.5" height="5.5" rx="1.6" fill="' + c + '"/>' +
        '<rect x="20.75" y="23" width="6.5" height="5.5" rx="1.6" fill="' + c + '"/>' +
        '<rect x="29.5" y="23" width="6.5" height="5.5" rx="1.6" fill="' + c + '"/>' +
        '<rect x="12" y="31" width="6.5" height="5.5" rx="1.6" fill="' + c + '"/>' +
        '<rect x="20.75" y="31" width="6.5" height="5.5" rx="1.6" fill="' + c + '"/>' +
        '<rect x="29.5" y="31" width="6.5" height="5.5" rx="1.6" fill="#ff3b30"/>' +
        "</svg>"
      );
    },
  };

  /* ---------- the "apps" (generic names only) ---------- */
  NK.APPS = {
    unofficial: { name: "Unofficial Group", tile: "#5E5CE6", glyph: "group" },
    official: { name: "Official Class Group", tile: "#0A84FF", glyph: "group" },
    boys: { name: "Boys Group", tile: "#FF9F0A", glyph: "group" },
    ishaan: { name: "Ishaan", tile: "#8B919B", glyph: "person", round: true },
    pdf: { name: "Downloads", tile: "#FF453A", glyph: "pdf" },
    img: { name: "Downloads", tile: "#2D7FF9", glyph: "img" },
    reminder: { name: "Reminder", tile: "#FFB21E", glyph: "bell" },
    mail: { name: "Inbox", tile: "#30B0C7", glyph: "mail" },
    calendar: { name: "Calendar", tile: "#BF5AF2", glyph: "cal" },
  };

  NK.badgeText = function (n) {
    if (typeof n === "string") return n;
    n = Math.max(0, Math.round(n));
    return n > 99 ? "99+" : String(n);
  };

  function div(cls) {
    var d = document.createElement("div");
    if (cls) d.className = cls;
    return d;
  }

  /* ---------- card factory ----------
     o = { app, title?, sender?, msg, mono?, time?, badge? (number|"99+"|null), w?, h?, id? }
     returns { el (.nk-card), fly, notif, badge, dim, sheen, alarm, setBadge(n) } */
  NK.card = function (o) {
    var app = NK.APPS[o.app] || NK.APPS.unofficial;
    var w = o.w || 940;
    var h = o.h || 150;

    var el = div("nk-card");
    if (o.id) el.id = o.id;
    el.setAttribute("data-layout-allow-overflow", "");
    el.style.setProperty("--nk-w", w + "px");
    el.style.setProperty("--nk-h", h + "px");

    var fly = div("nk-fly");
    var notif = div("notif nk");

    var icon = div("icon" + (app.round ? " round" : ""));
    icon.style.setProperty("--nk-c", app.tile);
    if (app.glyph === "person") {
      icon.style.backgroundImage = "linear-gradient(180deg, #b4b9c2 0%, #7c828c 100%)";
    }
    icon.innerHTML = G[app.glyph](app.tile);

    var body = div("body");
    var row = div("row");
    var title = div("title");
    title.textContent = o.title || app.name;
    var time = div("time");
    time.textContent = o.time || "now";
    row.appendChild(title);
    row.appendChild(time);
    var msg = div("msg" + (o.mono ? " mono" : ""));
    if (o.sender) {
      var b = document.createElement("b");
      b.textContent = o.sender + " ";
      msg.appendChild(b);
    }
    msg.appendChild(document.createTextNode(o.msg || ""));
    body.appendChild(row);
    body.appendChild(msg);

    var fx = div("nk-fx");
    var sheen = div("nk-sheen");
    sheen.setAttribute("data-layout-allow-overflow", "");
    var dim = div("nk-dim");
    var alarm = div("nk-alarm");
    fx.appendChild(sheen);
    fx.appendChild(dim);
    fx.appendChild(alarm);

    notif.appendChild(icon);
    notif.appendChild(body);
    notif.appendChild(fx);

    var badge = null;
    var shown = null;
    if (o.badge !== null && o.badge !== undefined) {
      badge = div("badge");
      shown = NK.badgeText(o.badge);
      badge.textContent = shown;
      notif.appendChild(badge);
    }

    fly.appendChild(notif);
    el.appendChild(fly);

    return {
      el: el,
      fly: fly,
      notif: notif,
      badge: badge,
      dim: dim,
      sheen: sheen,
      alarm: alarm,
      timeEl: time,
      w: w,
      h: h,
      setBadge: function (n) {
        if (!badge) return;
        var s = NK.badgeText(n);
        if (s !== shown) {
          shown = s;
          badge.textContent = s;
        }
      },
    };
  };

  /* ---------- geometry for scattered cards ---------- */
  // half extents of a w x h card at scale s, rotated rDeg
  NK.ext = function (w, h, s, rDeg) {
    var r = (Math.abs(rDeg) * Math.PI) / 180;
    var c = Math.cos(r);
    var sn = Math.sin(r);
    return { hx: s * ((w / 2) * c + (h / 2) * sn), hy: s * ((w / 2) * sn + (h / 2) * c) };
  };

  // piecewise-linear lookup over [[t, v], ...] (sorted by t)
  NK.lerpKeys = function (keys, t) {
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

  global.NK = NK;
})(window);
