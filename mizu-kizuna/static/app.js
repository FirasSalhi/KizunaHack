/* MIZU KIZUNA — interface agriculteur (fr / tn / ja) */
(() => {
const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

/* ------------------------------------------------------------------ langue */
// Inside the FARMLINK dashboard the language comes from the page address (?lang=fr|tn|ja) and the
// dashboard hides our own language buttons (?embed=1); otherwise the visitor's last choice is used.
const PARAMS = new URLSearchParams(location.search);
const EMBEDDED = PARAMS.get("embed") === "1";
let LANG = PARAMS.get("lang") || (() => { try { return localStorage.getItem("mizu-lang") || "fr"; } catch { return "fr"; } })();
if (!I18N[LANG]) LANG = "fr";
if (EMBEDDED) {
  document.body.classList.add("embedded");
  // Same typeface as the FARMLINK dashboard around it.
  const font = document.createElement("link");
  font.rel = "stylesheet";
  font.href = "https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&display=swap";
  document.head.appendChild(font);
}
const LX = () => I18N[LANG];  // (L est réservé à Leaflet)
const T = (k, p = {}) => String(LX()[k] ?? I18N.fr[k] ?? k).replace(/\{(\w+)\}/g, (_, x) => p[x] ?? "");
const locale = () => ({fr: "fr-FR", tn: "fr-FR", ja: "ja-JP"}[LANG]);
const fmt = (n, d = 0) => n == null ? "—" : Number(n).toLocaleString(locale(), {maximumFractionDigits: d});

function applyLang() {
  document.documentElement.lang = LX().htmlLang;
  document.documentElement.dir = LX().dir;
  document.title = "MIZU KIZUNA — " + T("tagline").replace(/^水 絆 · /, "");
  $$("[data-i18n]").forEach(el => el.textContent = T(el.dataset.i18n));
  $$("[data-i18n-ph]").forEach(el => el.placeholder = T(el.dataset.i18nPh));
  $$(".langs button").forEach(b => b.classList.toggle("on", b.dataset.lang === LANG));
  if (farm) updateFarm(false);
  volumeHint();
  if (farm && $("#editBtn")) $("#editBtn").textContent = farm.pm.enabled() ? T("editDone") : T("edit");
  setTimeout(() => map.invalidateSize(), 50);
}
function switchLang(next) {
  if (next === LANG || !I18N[next]) return;
  LANG = next;
  try { localStorage.setItem("mizu-lang", LANG); } catch {}
  applyLang();
  if (DATA && !$("#results").hidden) runAnalysis();  // les textes du modèle viennent du serveur
}
$$(".langs button").forEach(b => b.onclick = () => switchLang(b.dataset.lang));
// The FARMLINK dashboard announces language changes; switching in place keeps the drawn parcel.
window.addEventListener("message", e => {
  if (e.data && e.data.type === "mizu:lang" && typeof e.data.lang === "string") switchLang(e.data.lang);
});

/* ------------------------------------------------------------------ carte */
const map = L_map();
function L_map() {
  const m = L.map("map", {zoomControl: true, maxZoom: 19}).setView([34.5, 9.6], 7);
  const imagery = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 19, maxNativeZoom: 18, attribution: "Imagerie © Esri, Maxar, Earthstar Geographics | © OpenStreetMap"}).addTo(m);
  L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 19, maxNativeZoom: 18, opacity: .9}).addTo(m);
  let warned = false;
  imagery.on("tileerror", () => { if (!warned) { warned = true; toast(T("tTiles"), 4000); } });
  m.pm.setGlobalOptions({pathOptions: {color: "#facc15", weight: 3, fillOpacity: .12}, snappable: false, allowSelfIntersection: false});
  return m;
}
let farm = null, resultLayer = null, zonesLayer = null, legend = null, layerCtl = null, DATA = null;

function areaHa(latlngs) {
  const pts = latlngs.map(p => [p.lng, p.lat]);
  const k = Math.cos(pts.reduce((s, p) => s + p[1], 0) / pts.length * Math.PI / 180);
  let s = 0;
  for (let i = 0; i < pts.length; i++) {
    const [x1, y1] = pts[i], [x2, y2] = pts[(i + 1) % pts.length];
    s += (x1 * 111320 * k) * (y2 * 110540) - (x2 * 111320 * k) * (y1 * 110540);
  }
  return Math.abs(s) / 2 / 1e4;
}
const farmRing = () => farm.getLatLngs()[0];
const haTxt = ha => ha < 1 ? `${fmt(ha * 10000)} m²` : `${fmt(ha, 2)} ${LX().unitHa}`;
function updateFarm(advance = true) {
  if (!farm) return;
  const txt = haTxt(areaHa(farmRing()));
  farm.unbindTooltip();
  farm.bindTooltip(txt, {permanent: true, direction: "center", className: "area-label"}).openTooltip();
  $("#farmInfo").hidden = false;
  $("#farmInfo").textContent = T("farmInfo", {x: txt});
  $("#editBtn").hidden = $("#clearBtn").hidden = false;
  $("#drawBtn").hidden = true;
  $("#goBtn").disabled = false;
  $("#goHint").hidden = true;
  volumeHint();
  if (advance) setStep(3, [1, 2]);
}
$("#drawBtn").onclick = () => {
  if (map.getZoom() < 13) toast(T("tZoom"), 3500);
  map.pm.enableDraw("Polygon", {finishOn: null, tooltips: false});
  setStep(2, [1]);
};
map.on("pm:create", e => {
  if (farm) map.removeLayer(farm);
  farm = e.layer;
  farm.on("pm:edit", () => updateFarm(false));
  updateFarm();
});
$("#editBtn").onclick = () => {
  if (!farm) return;
  const on = farm.pm.enabled();
  on ? farm.pm.disable() : farm.pm.enable({allowSelfIntersection: false});
  $("#editBtn").textContent = on ? T("edit") : T("editDone");
};
$("#clearBtn").onclick = () => {
  if (farm) map.removeLayer(farm);
  farm = null;
  clearResultLayers();
  $("#farmInfo").hidden = $("#editBtn").hidden = $("#clearBtn").hidden = true;
  $("#drawBtn").hidden = false; $("#goBtn").disabled = true; $("#goHint").hidden = false;
  setStep(2, [1]);
};
function setStep(active, done = []) {
  $$(".step").forEach(li => {
    const n = +li.dataset.step;
    li.classList.toggle("active", n === active);
    li.classList.toggle("done", done.includes(n));
  });
}
$$(".step-head").forEach(h => h.onclick = () => {
  const n = +h.parentElement.dataset.step;
  if (n === 3 && !farm) return;
  setStep(n, $$(".step.done").map(x => +x.dataset.step));
});

/* ------------------------------------------------------------------ recherche */
let tSearch = null, suggestions = [], sel = -1;
$("#q").addEventListener("input", e => {
  clearTimeout(tSearch);
  const q = e.target.value.trim();
  if (q.length < 3) { $("#suggest").hidden = true; return; }
  tSearch = setTimeout(() => search(q), 450);
});
$("#q").addEventListener("keydown", e => {
  if ($("#suggest").hidden) return;
  if (e.key === "ArrowDown") { sel = Math.min(sel + 1, suggestions.length - 1); paintSuggest(); e.preventDefault(); }
  if (e.key === "ArrowUp") { sel = Math.max(sel - 1, 0); paintSuggest(); e.preventDefault(); }
  if (e.key === "Enter" && suggestions[Math.max(sel, 0)]) { pick(suggestions[Math.max(sel, 0)]); e.preventDefault(); }
  if (e.key === "Escape") $("#suggest").hidden = true;
});
document.addEventListener("click", e => { if (!e.target.closest(".search")) $("#suggest").hidden = true; });
async function search(q) {
  try {
    const r = await fetch(`/api/geocode?q=${encodeURIComponent(q)}&lang=${LANG}`);
    if (!r.ok) throw new Error();
    suggestions = await r.json();
  } catch { suggestions = []; $("#suggest").innerHTML = `<li class="empty">${esc(T("tSearchDown"))}</li>`; $("#suggest").hidden = false; return; }
  sel = -1; paintSuggest();
}
function paintSuggest() {
  const ul = $("#suggest");
  ul.innerHTML = suggestions.length ? suggestions.map((s, i) => `<li data-i="${i}" class="${i === sel ? "on" : ""}">${esc(s.name)}</li>`).join("")
    : `<li class="empty">${esc(T("tNoPlace"))}</li>`;
  ul.hidden = false;
  ul.querySelectorAll("li[data-i]").forEach(li => li.onclick = () => pick(suggestions[+li.dataset.i]));
}
function pick(s) {
  $("#suggest").hidden = true;
  $("#q").value = s.name.split(/[,،、]/).slice(0, 2).join(",");
  const [s1, n1, w1, e1] = s.bbox;
  map.fitBounds([[s1, w1], [n1, e1]], {maxZoom: 15});
  setStep(2, [1]);
}
$$("[data-fly]").forEach(b => b.onclick = () => {
  const [la, lo, z] = b.dataset.fly.split(",").map(Number);
  map.flyTo([la, lo], z, {duration: 1.2});
  setStep(2, [1]);
});
$("#locate").onclick = () => {
  if (!navigator.geolocation) return toast(T("tGeoNone"));
  navigator.geolocation.getCurrentPosition(
    p => { map.flyTo([p.coords.latitude, p.coords.longitude], 16); setStep(2, [1]); },
    () => toast(T("tGeoFail")), {timeout: 10000});
};

/* ------------------------------------------------------------------ formulaire */
const form = {source: "puits", method: "goutte_a_goutte", salinity: "non", soil: "", kinds: "all"};
$$(".choices").forEach(group => group.querySelectorAll("button").forEach(b => b.onclick = () => {
  group.querySelectorAll("button").forEach(x => x.classList.toggle("on", x === b));
  form[group.dataset.name] = b.dataset.v;
  if (group.dataset.name === "source") $("#irrigBlock").hidden = b.dataset.v === "pluie";
}));
function volumeHint() {
  const v = +$("#volume").value;
  $("#volumeHint").textContent = (!farm || !v) ? T("volEmpty") : T("volPerHa", {x: fmt(v / areaHa(farmRing()))});
}
$("#volume").addEventListener("input", volumeHint);

/* ------------------------------------------------------------------ analyse */
$("#goBtn").onclick = () => runAnalysis();
async function runAnalysis() {
  if (!farm) return;
  if (farm.pm.enabled()) { farm.pm.disable(); $("#editBtn").textContent = T("edit"); }
  const ring = farmRing().map(p => [p.lng, p.lat]);
  const body = {
    farm: {type: "Polygon", coordinates: [[...ring, ring[0]]]},
    water: {source: form.source, method: form.method, volume_m3: form.source === "pluie" ? null : (+$("#volume").value || null)},
    salinity: form.salinity, soil_type: form.soil || null, kinds: form.kinds, lang: LANG
  };
  showLoading(true);
  try {
    const r = await fetch("/api/analyze", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
    const d = await r.json();
    if (!r.ok) throw new Error(typeof d.detail === "string" ? d.detail : T("tFail"));
    DATA = d;
    renderResults(d);
  } catch (e) {
    toast(e.message || T("tFail"), 5000);
  } finally { showLoading(false); }
}
let loadTimer = null;
function showLoading(on) {
  $("#loading").hidden = !on;
  const items = $$("#loadSteps li");
  clearInterval(loadTimer);
  if (!on) return;
  let i = 0;
  const tick = () => { items.forEach((li, k) => { li.className = k < i ? "ok" : k === i ? "now" : ""; }); i = Math.min(i + 1, items.length - 1); };
  tick(); loadTimer = setInterval(tick, 2200);
}
function toast(msg, ms = 3000) {
  const t = $("#toast"); t.textContent = msg; t.hidden = false;
  clearTimeout(t._h); t._h = setTimeout(() => t.hidden = true, ms);
}

/* ------------------------------------------------------------------ résultats */
function clearResultLayers() {
  [resultLayer, zonesLayer].forEach(l => l && map.removeLayer(l));
  resultLayer = zonesLayer = null;
  if (legend) { map.removeControl(legend); legend = null; }
  if (layerCtl) { map.removeControl(layerCtl); layerCtl = null; }
  if (farm) farm.setStyle({fillOpacity: .12});
}
const badgeClass = lv => ({tres: "b-tres", adapte: "b-ad", possible: "b-pos"}[lv] || "b-dec");
const monthName = m => LX().months[m - 1];
const whenTxt = (perennial, m, kind = "meta") => T(perennial ? (kind === "meta" ? "metaPlant" : "planting") : (kind === "meta" ? "metaSow" : "sowing"), {m: monthName(m)});

/** Send the validated plan to FARMLINK (the page around this one) so its other sections reuse it. */
function sendPlan(d) {
  const soil = (d.land && d.land.soil) || {};
  const plan = {
    version: 1,
    validated_at: new Date().toISOString(),
    area_ha: d.farm.area_ha,
    location: {lat: d.farm.lat, lon: d.farm.lon},
    country: d.farm.country,
    water_source: d.farm.water_source,
    irrigation_method: d.farm.irrigation_method,
    soil: {texture: soil.texture || null, clay_pct: soil.clay_pct ?? null, sand_pct: soil.sand_pct ?? null, silt_pct: soil.silt_pct ?? null},
    crops: d.plan.allocation.map(a => ({id: a.crop, name: a.name, area_ha: a.area_ha, sowing_month: a.sowing_month,
      perennial: !!a.perennial, irrigated: !!a.irrigated, water_m3_typical: a.water_m3_typical})),
  };
  let target = "*";
  try { if (document.referrer) target = new URL(document.referrer).origin; } catch {}
  window.parent.postMessage({type: "mizu:plan", plan}, target);
}

function renderResults(d) {
  clearResultLayers();
  const plan = d.plan, cur = d.farm, rainfedMode = cur.water_source === "pluie";
  // carte : un bloc par culture, avec son nom et sa surface
  resultLayer = L.geoJSON(plan.map, {
    style: f => ({fillColor: f.properties.fill, fillOpacity: .55, color: "#ffffff", weight: 2}),
    onEachFeature: (f, l) => l.bindTooltip(`<b>${esc(f.properties.name)}</b><br>${fmt(f.properties.area_ha, 1)} ${LX().unitHa}`,
      {permanent: true, direction: "center", className: "block-label"})
  }).addTo(map);
  farm.setStyle({fillOpacity: 0}); farm.closeTooltip(); farm.unbindTooltip(); farm.bringToFront();
  const sat = d.land.satellite;
  const overlays = {[T("layerPlan")]: resultLayer};
  if (sat.available && sat.vigor_zones) {
    const zc = ["", "#e76f51", "#e9c46a", "#2a9d8f"];
    zonesLayer = L.geoJSON(sat.vigor_zones, {style: f => ({fillColor: zc[f.properties.zone], fillOpacity: .55, color: "#fff", weight: 1}),
      onEachFeature: (f, l) => l.bindTooltip(T("vigorTip", {v: LX().vigor[f.properties.zone], n: f.properties.ndvi_mean, a: fmt(f.properties.area_ha, 2)}), {sticky: true})});
    overlays[T("layerZones")] = zonesLayer;
  }
  layerCtl = L.control.layers(null, overlays, {collapsed: true, position: "topright"}).addTo(map);
  map.fitBounds(farm.getBounds(), {padding: [40, 40], maxZoom: 17});
  const colors = Object.fromEntries(plan.map.legend.filter(x => x.crop).map(x => [x.crop, x.color]));

  /* ---------- VUE SIMPLE ---------- */
  const h = [];
  h.push(`<div class="res-head"><div><h2>${T("yourPlan")}</h2>
    <p>${haTxt(cur.area_ha)} · ${T(cur.country)} · ${rainfedMode ? T("rainfedMode") : T("irrigation") + " " + (LX().methods[cur.irrigation_method] || "")}</p></div>
    <button class="back" id="backBtn">${T("back")}</button></div>`);
  d.warnings.filter(w => !/satellite|ساتليت|衛星/i.test(w) || /été|الصيف|夏/.test(w)).forEach(w => h.push(`<div class="alert">${esc(w)}</div>`));

  if (!plan.allocation.length) {
    h.push(`<div class="alert">${T("planNone")} ${rainfedMode ? T("planNoneRain") : T("planNoneIrr")}</div>`);
  } else {
    h.push(`<div class="simple-plan">${plan.allocation.map(a => {
      const when = T(a.perennial ? "plantIn" : "sowIn", {m: monthName(a.sowing_month)});
      const water = a.irrigated && !rainfedMode ? T("waterYear", {w: fmt(a.water_m3_typical)}) : T("noIrr");
      const inter = a.intercrops && a.intercrops.length ? `<div class="sp-inter">🌱 ${T("between")} <b>${a.intercrops.map(i => esc(i.name)).join(", ")}</b></div>` : "";
      return `<div class="sp-item" style="border-inline-start-color:${colors[a.crop]}">
        <div class="sp-top"><b>${esc(a.name)}</b><span class="sp-ha">${fmt(a.area_ha, 1)} ${LX().unitHa}</span></div>
        <div class="sp-meta"><span>📅 ${esc(when)}</span><span>💧 ${esc(water)}</span></div>${inter}</div>`; }).join("")}</div>`);
    if (!rainfedMode && d.summary.water_typical_m3 > 0)
      h.push(`<p class="sp-total">${T("waterTotal", {a: fmt(d.summary.water_typical_m3), b: fmt(d.summary.water_dry_year_m3)})}</p>`);
    if (d.summary.area_unplanted_ha > 0.05 * cur.area_ha) h.push(`<div class="alert">${T("unplanted", {x: fmt(d.summary.area_unplanted_ha, 1)})}</div>`);
    // Inside FARMLINK: the farmer validates the plan once; the other sections reuse these crops.
    if (EMBEDDED) h.push(`<div class="validate-box"><button class="primary big" id="validateBtn">${T("validatePlan")}</button>
      <p class="hint" id="validateHint" hidden>${T("planValidatedHint")}</p></div>`);
  }
  // à planter ensemble : 2 meilleures combinaisons possibles qui touchent le plan
  const planIds = new Set(plan.allocation.map(a => a.crop));
  const together = d.combinations.filter(c => c.feasible && c.members.some(m => planIds.has(m.crop))).slice(0, 2);
  if (together.length) h.push(`<div class="block"><h3>${T("togetherTitle")}</h3>${together.map(c => `<div class="sp-combo">
      <b>${esc(c.title)}</b><span>${esc(c.causes[0].text)}</span>${c.cautions[0] ? `<small>⚠ ${esc(c.cautions[0])}</small>` : ""}</div>`).join("")}</div>`);
  const fc = d.forecast.advice.slice(1);
  if (fc.length) h.push(`<div class="block"><h3>${T("fcTitle")}</h3><ul class="notes">${fc.map(a => `<li>${esc(a)}</li>`).join("")}</ul></div>`);
  h.push(`<div class="actions"><button class="primary" id="detailsBtn">${T("showDetails")}</button><button class="ghost" id="printBtn">${T("print")}</button></div>`);

  /* ---------- DÉTAILS (repliés) ---------- */
  h.push(`<div id="details" hidden>`);
  if (plan.associations.length) h.push(`<div class="block"><h3>${T("planTitle")}</h3><div class="pairs">${plan.associations.map(p => `<div class="pair ${p.relation === "with" ? "good" : p.relation === "avoid" ? "bad" : ""}">
      <b>${esc(p.crops.join(" + "))}</b> : ${p.relation === "with" ? T("pairWith") : p.relation === "avoid" ? T("pairAvoid") : T("pairNeutral")}${p.reasons[0] ? " — " + esc(p.reasons[0]) : ""}</div>`).join("")}</div>
      <p class="src">${esc(T("placement", {x: plan.map.placement}))}</p></div>`);
  const ok = d.combinations.filter(c => c.feasible), ko = d.combinations.filter(c => !c.feasible);
  h.push(`<div class="block"><h3>${T("comboTitle")} <small>${T("comboSmall")}</small></h3>
    <div id="combos">${ok.map(comboCard).join("")}</div>
    ${ko.length ? `<button class="ghost small" id="comboToggle">${T("comboMore", {n: ko.length})}</button><div id="combosKo" hidden>${ko.map(comboCard).join("")}</div>` : ""}</div>`);
  h.push(`<div class="block"><h3>${T("rankTitle")} <small>${T("rankSmall")}</small></h3>
    <div class="tabs">${[["legumes", "tabVeg"], ["grandes_cultures", "tabField"], ["arbres", "tabTrees"], ["aromatiques", "tabArom"]].map(([k, t]) => `<button data-cat="${k}">${T(t)}</button>`).join("")}</div>
    <div id="cropList"></div></div>`);
  const s = d.land.soil;
  h.push(`<div class="block"><h3>${T("landTitle")}</h3><div class="land">
    <div><span>${T("texture")}</span><b>${esc(s.texture)}</b><span>${T("clayFmt", {c: s.clay_pct, s: s.sand_pct})}</span></div>
    <div><span>pH</span><b>${s.ph}</b><span>${s.ph >= 7.5 ? T("phAlk") : s.ph < 6 ? T("phAcid") : T("phNeutral")}</span></div>
    <div><span>${T("om")}</span><b>${s.soc_g_kg ?? "—"} g/kg</b><span>${T("omSub")}</span></div>
    <div><span>${T("taw")}</span><b>${s.taw_mm_m} mm/m</b><span>${T("tawSub")}</span></div></div>
    ${s.alerts.length ? `<ul class="notes">${s.alerts.map(a => `<li>${esc(a)}</li>`).join("")}</ul>` : ""}
    <p class="src">${T("source")} ${esc(s.source)}</p>`);
  if (sat.available) h.push(`<h3 style="margin-top:16px;font-size:14px">${T("satTitle", {n: sat.scenes_used, a: sat.period[0], b: sat.period[1]})}</h3>
      ${ndviChart(sat.ndvi_series)}<ul class="notes">${sat.interpretation.map(x => `<li>${esc(x)}</li>`).join("")}</ul>
      <p class="src">${T("source")} ${esc(sat.source)}</p>`);
  else h.push(`<p class="src">${esc(T("satNa", {x: sat.reason || T("na")}))}</p>`);
  h.push(`</div>`);
  const c = d.climate;
  h.push(`<div class="block"><h3>${T("climTitle")} <small>· ${c.years[0]}–${c.years[1]}</small></h3>${climateChart(c.normals)}
    <p class="src">${esc(c.source)} · ${T("etoM")} ${esc(c.eto_method)} · ${T("alt", {x: fmt(c.elevation_m)})}</p></div>`);
  if (d.calendar.length) h.push(`<div class="block"><h3>${T("calTitle")}</h3>${calendarTable(d.calendar, colors)}</div>`);
  h.push(`<div class="actions"><button class="ghost" id="jsonBtn">${T("copyJson")}</button></div><p class="method">${esc(d.method)}</p></div>`);

  $("#wizard").hidden = true;
  const res = $("#results"); res.hidden = false; res.innerHTML = h.join("");
  $("#panel").scrollTop = 0;
  $("#detailsBtn").onclick = () => { const box = $("#details"); box.hidden = !box.hidden; $("#detailsBtn").textContent = box.hidden ? T("showDetails") : T("hideDetails"); };
  const tg = $("#comboToggle");
  if (tg) tg.onclick = () => { const box = $("#combosKo"); box.hidden = !box.hidden; tg.textContent = box.hidden ? T("comboMore", {n: ko.length}) : T("comboLess"); };
  $$(".combo-head").forEach(el => el.onclick = () => el.parentElement.classList.toggle("open"));
  $("#backBtn").onclick = () => { res.hidden = true; $("#wizard").hidden = false; clearResultLayers(); updateFarm(false); setStep(3, [1, 2]); };
  $("#printBtn").onclick = () => window.print();
  const vb = $("#validateBtn");
  if (vb) vb.onclick = () => {
    sendPlan(d);
    vb.textContent = T("planValidated");
    vb.classList.add("done");
    $("#validateHint").hidden = false;
  };
  $("#jsonBtn").onclick = async () => { try { await navigator.clipboard.writeText(JSON.stringify(d, null, 2)); toast(T("tCopied")); } catch { toast(T("tCopyFail")); } };
  res.querySelectorAll(".tabs button").forEach(b => b.onclick = () => {
    res.querySelectorAll(".tabs button").forEach(x => x.classList.toggle("on", x === b)); renderCrops(b.dataset.cat); });
  const planCats = d.ranking.filter(r => planIds.has(r.crop)).map(r => r.category);
  const firstCat = planCats[0] || ["legumes", "grandes_cultures", "arbres", "aromatiques"].find(k => d.ranking.some(r => r.category === k)) || "legumes";
  res.querySelector(`.tabs button[data-cat="${firstCat}"]`).click();
}

function renderCrops(cat) {
  const list = DATA.ranking.filter(r => r.category === cat);
  const rainfedMode = DATA.farm.water_source === "pluie";
  $("#cropList").innerHTML = list.length ? list.map(r => {
    const comp = DATA.companions[r.crop];
    const per = r.type === "perennial";
    return `<div class="crop" data-c="${r.crop}">
      <div class="crop-top"><span class="nm">${esc(r.name)}</span><span class="badge ${badgeClass(r.level)}">${esc(r.label)}</span></div>
      <div class="score"><div style="width:${r.score}%"></div></div>
      <div class="meta"><span>${T("metaScore", {s: r.score})}</span><span>${whenTxt(per, r.best_sowing_month)}</span>
        ${rainfedMode ? "" : `<span>${T("metaWater", {a: fmt(r.water_m3_ha_typical), b: fmt(r.water_m3_ha_dry_year)})}</span>`}</div>
      <div class="crop-detail">
        <div class="factors">${[["fClimat", r.factors.climat], ["fSol", r.factors.sol], ["fSel", r.factors.sel], ["fEau", r.factors.eau]].map(([k, v]) => `<div><b>${v}</b>${T(k)}</div>`).join("")}
          <div><b>${r.factors.risque}%</b>${T("fRisque")}</div></div>
        ${r.pros.length ? `<h4>${T("pros")}</h4><ul>${r.pros.map(x => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}
        ${r.cons.length ? `<h4>${T("cons")}</h4><ul>${r.cons.map(x => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}
        <p class="src">${T("analyzed", {n: r.years_analyzed, f: r.risk.frost_pct, h: r.risk.heat_pct, r: fmt(r.rain_season_mm)})}</p>
        ${(() => { const cs = DATA.combinations.filter(x => x.feasible && x.members.some(m => m.crop === r.crop));
          return cs.length ? `<h4>${T("comboInCrop")}</h4><ul>${cs.map(x => `<li>${esc(x.title)} — ${esc(x.causes[0].text)}</li>`).join("")}</ul>` : ""; })()}
        <h4>${T("plantWith")}</h4>
        <div class="comp" data-comp="${r.crop}">${comp ? compHtml(comp) : `<span class="src">${T("loadingTxt")}</span>`}</div>
      </div></div>`;
  }).join("") : `<p class="hint">${T("noneCat")}</p>`;
  $$("#cropList .crop").forEach(el => el.onclick = async e => {
    if (e.target.closest(".crop-detail")) return;
    el.classList.toggle("open");
    const id = el.dataset.c, box = el.querySelector("[data-comp]");
    if (el.classList.contains("open") && !DATA.companions[id]) {
      try { const r = await fetch(`/api/crops/${id}/companions?country=${DATA.farm.country}&lang=${LANG}`); DATA.companions[id] = await r.json(); box.innerHTML = compHtml(DATA.companions[id]); }
      catch { box.innerHTML = `<span class="src">${T("na")}</span>`; }
    }
  });
}
const ROLE_ICON = {top: "🌳", middle: "🌿", low: "🌱", first: "①", then: "②"};
const CAUSE_ICON = {etages: "⬍", racines: "⤓", azote: "N", ravageurs: "🐞", eau: "💧", sol: "▤", revenu: "＄", calendrier: "🗓", microclimat: "☁"};
function comboCard(c) {
  return `<div class="combo ${c.feasible ? "" : "ko"}">
    <div class="combo-head">
      <div class="combo-members">${c.members.map(m => `<span class="member" title="${esc(m.role_label)}"><i>${ROLE_ICON[m.role] || "•"}</i>${esc(m.name)}<small>${esc(m.role_label)}</small></span>`).join('<span class="plus">+</span>')}</div>
      <div class="combo-side"><span class="badge ${c.feasible ? "b-ad" : "b-dec"}">${c.feasible ? T("comboOk") : T("comboNo")}</span>
        <span class="src">${T("comboScore", {s: c.fit})} · ${esc(c.water_label)}</span></div>
    </div>
    ${c.why_not ? `<p class="combo-why-not">${esc(c.why_not)}</p>` : ""}
    ${c.water_note ? `<p class="combo-water">💧 ${esc(c.water_note)}</p>` : ""}
    <div class="combo-body">
      <h4>${T("comboWhy")}</h4>
      <ul class="causes">${c.causes.map(x => `<li><span class="cause-chip">${CAUSE_ICON[x.type] || "•"} ${esc(x.type_label)}</span>${esc(x.text)}</li>`).join("")}</ul>
      ${c.cautions.length ? `<h4>${T("comboCaution")}</h4><ul class="cautions">${c.cautions.map(x => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}
      <h4>${T("comboLayout")}</h4><p class="layout-txt">${esc(c.layout)}</p>
      <p class="src">${T("comboConf", {c: esc(c.confidence_label)})} · ${T("comboSources")} : ${c.sources.map(esc).join(" ; ")}</p>
    </div></div>`;
}
function compHtml(c) {
  const line = x => `<span title="${esc(x.reasons.join(" · "))}">${esc(x.name)}</span>`;
  return `<div class="with"><b>${T("together")}</b>${c.with.slice(0, 6).map(line).join("") || "<span>—</span>"}</div>
    <div class="avoid"><b>${T("avoid")}</b>${c.avoid.slice(0, 6).map(line).join("") || "<span>—</span>"}</div>`;
}

/* ------------------------------------------------------------------ graphiques SVG (toujours de gauche à droite) */
function climateChart(n) {
  const W = 400, H = 150, Lm = 30, B = 20, Tm = 8, w = (W - Lm - 8) / 12, ms = LX().monthsShort;
  const rmax = Math.max(50, ...n.rain, ...n.eto), tmax = Math.max(...n.tmax) + 2, tmin = Math.min(0, ...n.tmin) - 2;
  const y = v => Tm + (H - Tm - B) * (1 - v / rmax), yt = v => Tm + (H - Tm - B) * (1 - (v - tmin) / (tmax - tmin));
  let s = `<svg class="chart" dir="ltr" viewBox="0 0 ${W} ${H}" role="img">`;
  n.rain.forEach((v, i) => { s += `<rect x="${Lm + i * w + 3}" y="${y(v)}" width="${w - 6}" height="${H - B - y(v)}" rx="2" fill="#7cc4d6"><title>${LX().months[i]} : ${v} mm / ETo ${n.eto[i]} mm</title></rect>`; });
  const line = (arr, f, col, dash) => `<polyline fill="none" stroke="${col}" stroke-width="2" ${dash ? 'stroke-dasharray="4 3"' : ""} points="${arr.map((v, i) => `${Lm + i * w + w / 2},${f(v)}`).join(" ")}"/>`;
  s += line(n.eto, y, "#0e7490", true) + line(n.tmax, yt, "#d9480f") + line(n.tmin, yt, "#4c6ef5");
  ms.forEach((m, i) => s += `<text x="${Lm + i * w + w / 2}" y="${H - 5}" font-size="10" text-anchor="middle" fill="#6b7280">${m}</text>`);
  s += `<text x="2" y="12" font-size="10" fill="#6b7280">mm</text></svg>`;
  return s + `<p class="src"><span style="color:#7cc4d6">■</span> ${T("rainL")} · <span style="color:#0e7490">- -</span> ${T("etoL")} · <span style="color:#d9480f">—</span> ${T("tmaxL")} · <span style="color:#4c6ef5">—</span> ${T("tminL")}</p>`;
}
function ndviChart(series) {
  if (!series || series.length < 2) return "";
  const W = 400, H = 110, Lm = 28, B = 18, Tm = 6;
  const x = i => Lm + i * (W - Lm - 8) / (series.length - 1), y = v => Tm + (H - Tm - B) * (1 - Math.max(0, Math.min(1, v)));
  let s = `<svg class="chart" dir="ltr" viewBox="0 0 ${W} ${H}" role="img">`;
  s += `<rect x="${Lm}" y="${y(1)}" width="${W - Lm - 8}" height="${y(.35) - y(1)}" fill="#e3f4ea"/>`;
  s += `<polyline fill="none" stroke="#1f8a55" stroke-width="2.2" points="${series.map((p, i) => `${x(i)},${y(p.ndvi)}`).join(" ")}"/>`;
  series.forEach((p, i) => s += `<circle cx="${x(i)}" cy="${y(p.ndvi)}" r="2.5" fill="#1f8a55"><title>${p.date} : NDVI ${p.ndvi}</title></circle>`);
  [0, .5, 1].forEach(v => s += `<text x="2" y="${y(v) + 3}" font-size="10" fill="#6b7280">${v}</text>`);
  s += `<text x="${Lm}" y="${H - 4}" font-size="10" fill="#6b7280">${series[0].date.slice(0, 7)}</text><text x="${W - 8}" y="${H - 4}" font-size="10" text-anchor="end" fill="#6b7280">${series.at(-1).date.slice(0, 7)}</text></svg>`;
  return s + `<p class="src">${T("ndviCap")}</p>`;
}
function calendarTable(cal, colors) {
  const ms = LX().monthsShort;
  return `<table class="cal"><tr><th></th>${ms.map(m => `<th>${m}</th>`).join("")}</tr>${cal.map(c => {
    const months = new Set();
    const n = c.perennial ? 365 : c.season_days;
    for (let d = 0; d < n; d += 15) months.add(((c.sowing_month - 1 + Math.floor(d / 30)) % 12) + 1);
    return `<tr><td><i class="swatch" style="display:inline-block;background:${colors[c.crop] || "#cbd5e0"};margin-inline-end:6px"></i>${esc(c.name)}</td>${ms.map((_, i) => {
      const m = i + 1; return `<td><div class="${m === c.sowing_month ? "sow" : months.has(m) ? "on" : ""}">&nbsp;</div></td>`; }).join("")}</tr>`;
  }).join("")}</table><p class="src">${T("calCap")}</p>`;
}

applyLang();
volumeHint();
const APP_VERSION = "2.4";
fetch("/api/health").then(r => r.json()).then(h => { if (h.version !== APP_VERSION) toast(T("oldServer"), 15000); }).catch(() => {});
})();
