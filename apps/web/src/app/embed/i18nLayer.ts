/**
 * Translation layer for the research pages shown in the dashboard (Solar, Market, Irrigation 3D, Post-Harvest).
 *
 * Their files are not changed: the page route adds this script at the very start of the page. It translates the
 * page's text as it is drawn (text nodes, a few attributes, and text painted on canvases), using a dictionary
 * per page: source text -> { fr, en, ar, ja }. Numbers are matched as placeholders, so "Parcelle de 21,07 ha" is
 * found under "Parcelle de {0} ha". The brand is shown as Mdhalla (مظلّة in Arabic) everywhere.
 */

export type Lang = "fr" | "en" | "ar" | "ja";
export type Dictionary = Record<string, Partial<Record<Lang, string>>>;

export const LANGS: readonly Lang[] = ["fr", "en", "ar", "ja"];
export const isLang = (v: unknown): v is Lang => typeof v === "string" && (LANGS as readonly string[]).includes(v);

/** Source text -> text in `lang`, for one page (entries without that language are left out). */
export function pick(dict: Dictionary, lang: Lang): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [src, t] of Object.entries(dict)) {
    const v = t[lang];
    if (v != null && v !== src) out[src] = v;
  }
  return out;
}

/**
 * The script added to the page. `hideBilingual` hides the page's own Tunisian-Arabic subtitles (`.ar`) when the
 * dashboard language is not French, since the main text is then already in the chosen language.
 */
export function i18nLayer(lang: Lang, words: Record<string, string>, opts: { hideBilingual?: boolean } = {}): string {
  const brand = lang === "ar" ? "مظلّة" : "Mdhalla";
  const css = opts.hideBilingual && lang !== "fr" ? "<style>.ar{display:none!important}</style>" : "";
  const vars = `var LANG = ${JSON.stringify(lang)}, W = ${JSON.stringify(words)}, BRAND = ${JSON.stringify(brand)};`;
  return `${css}<script>/* Mdhalla: show this page in the dashboard's language */\n(function () {\n${vars}\n${CLIENT}\n})();\n</script>`;
}

// The page-side code, kept raw so its regular expressions keep their backslashes.
const CLIENT = String.raw`
  window.__FL_LANG = LANG;
  document.documentElement.lang = LANG;
  var NUM = /[-+−]?\d(?:[\d.,  ]*\d)?/g;
  var has = function (k) { return Object.prototype.hasOwnProperty.call(W, k); };
  // Keys may hold numbers ({0}, {1}...) and free text ({a}, {b}...); free text is translated on its own.
  var PATS = Object.keys(W).filter(function (k) { return /\{[a-z]\}/.test(k); }).map(function (k) {
    var names = [];
    var src = k.split(/(\{[a-z]\}|\{\d+\})/).map(function (part) {
      var m = /^\{([a-z]|\d+)\}$/.exec(part);
      if (!m) return part.replace(/[.*+?^(){}$|[\]\\]/g, "\\$&");
      if (/\d/.test(m[1])) return "\\{" + m[1] + "\\}";
      names.push(m[1]); return "(.+?)";
    }).join("");
    return { re: new RegExp("^" + src + "$"), names: names, key: k };
  }).sort(function (a, b) {
    // most specific first: "Z{0} · {a} · today" before "Z{0} · {a}"
    return b.key.replace(/\{\w+\}/g, "").length - a.key.replace(/\{\w+\}/g, "").length;
  });
  function lookup(t) {
    if (has(t)) return W[t];
    for (var i = 0; i < PATS.length; i++) {
      var m = PATS[i].re.exec(t); if (!m) continue;
      var out = W[PATS[i].key], names = PATS[i].names;
      for (var j = 0; j < names.length; j++) { var part = m[j + 1], v = lookupNum(part); out = out.split("{" + names[j] + "}").join(v == null ? part : v); }
      return out;
    }
    return null;
  }
  function lookupNum(t) {
    if (has(t)) return W[t];
    var nums = [], key = t.replace(NUM, function (m) { nums.push(m); return "{" + (nums.length - 1) + "}"; });
    var v = lookup(key);
    return v == null ? null : v.replace(/\{(\d+)\}/g, function (_, i) { return nums[+i] == null ? "" : nums[+i]; });
  }
  function tr(s) {
    if (s == null) return null;
    var raw = String(s), str = raw.replace(/FARMLINK|Farmlink/g, "Mdhalla"), t = str.trim();
    if (!t) return null;
    var v = lookupNum(t), out = v == null ? str : str.replace(t, function () { return v; });
    if (BRAND !== "Mdhalla") out = out.replace(/Mdhalla/g, BRAND);
    return out === raw ? null : out;
  }
  window.__flT = function (s) { var v = tr(s); return v == null ? s : v; };

  // Text painted on canvases (3D labels, chart axes).
  ["fillText", "strokeText"].forEach(function (fn) {
    var orig = CanvasRenderingContext2D.prototype[fn];
    CanvasRenderingContext2D.prototype[fn] = function (text) {
      var v = tr(text); if (v != null) arguments[0] = v;
      return orig.apply(this, arguments);
    };
  });

  var done = new WeakMap(), ATTRS = ["placeholder", "title", "aria-label", "alt"];
  function text(node) {
    var p = node.parentNode; if (!p || p.nodeName === "SCRIPT" || p.nodeName === "STYLE") return;
    var cur = node.nodeValue; if (done.get(node) === cur) return;
    var v = tr(cur); if (v != null && v !== cur) node.nodeValue = v;
    done.set(node, node.nodeValue);
  }
  function el(e) {
    for (var i = 0; i < ATTRS.length; i++) {
      var a = ATTRS[i], cur = e.getAttribute && e.getAttribute(a);
      if (cur) { var v = tr(cur); if (v != null && v !== cur) e.setAttribute(a, v); }
    }
  }
  function walk(root) {
    if (!root) return;
    if (root.nodeType === 3) return text(root);
    if (root.nodeType !== 1) return;
    el(root);
    var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT), n;
    while ((n = w.nextNode())) { if (n.nodeType === 3) text(n); else el(n); }
  }
  var queue = [], scheduled = false;
  function flush() { scheduled = false; var q = queue; queue = []; for (var i = 0; i < q.length; i++) walk(q[i]); }
  new MutationObserver(function (list) {
    for (var i = 0; i < list.length; i++) {
      var m = list[i];
      if (m.type === "childList") for (var j = 0; j < m.addedNodes.length; j++) queue.push(m.addedNodes[j]);
      else queue.push(m.target);
    }
    if (!scheduled) { scheduled = true; Promise.resolve().then(flush); }
  }).observe(document.documentElement, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATTRS });
  var t0 = tr(document.title); if (t0) document.title = t0;
  if (document.body) walk(document.body);
  document.addEventListener("DOMContentLoaded", function () { walk(document.body); var t = tr(document.title); if (t) document.title = t; });
`;
