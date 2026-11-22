import { readFile } from "node:fs/promises";
import path from "node:path";
import { IRRIGATION_CROP, IRRIGATION_METHOD, PLAN_KEY, POST_HARVEST_CROP } from "@/lib/farmPlan";

/**
 * Serves the standalone research pages shown in dashboard sections, from the same origin as the app, so
 * the dashboard can show them in a frame. Only the pages listed here can be served.
 *
 * Their layout and code are not changed. A short script is added at the end of the page that reads the
 * farmer's validated crop plan (lib/farmPlan.ts, saved by Crop Planning) and pre-fills the page with it,
 * so the farmer never picks the same crops twice.
 */
const PAGES: Record<string, string[]> = {
  // Dashboard > Post-Harvest: HarvestGuard cold-storage digital twin (branch post-harvest-model)
  "post-harvest": ["post-harvest-model", "dashboard", "farmer_dashboard.html"],
  // Dashboard > 3D Irrigation: the farmer's 3D farm with per-field irrigation decisions (branch fatma)
  "irrigation-3d": ["irrigation-notebook", "html", "ferme_3d.html"],
};

// The 3D farm sends a fixed demo location to the irrigation engine; use the plan's parcel instead.
const DEMO_LOCATION = "location: {lat: 35.918, lon: 10.558, elevation_m: 10}";

// Its code runs inside a closure, so a hook is added at the end of it (next to the page's own
// window.__farmCheck) that replaces the demo plots, like its "add a plot" form does.
const IRRIGATION_CLOSURE_END = "\n})();\n</script>";
const IRRIGATION_HOOK = `
window.__flSetPlots = (zones) => {
  FZ = zones.map(z => ({...z, soil: SOILS[z.soilKey] ? {fc: SOILS[z.soilKey].fc, wp: SOILS[z.soilKey].wp} : {fc: '', wp: ''}}));
  nextId = FZ.length + 1; R = null; refresh(); select(0, true);
};`;

const readPlan = `var plan = null; try { plan = JSON.parse(localStorage.getItem(${JSON.stringify(PLAN_KEY)}) || "null"); } catch (e) {}
  if (!plan || !Array.isArray(plan.crops) || !plan.crops.length) return;`;

/** Irrigation 3D: one plot per planned crop (max 6), with its hectares, the parcel's soil and method. */
const IRRIGATION_BRIDGE = `(function () {
  ${readPlan}
  var CROPS = ${JSON.stringify(IRRIGATION_CROP)}, METHODS = ${JSON.stringify(IRRIGATION_METHOD)};
  if (plan.location) window.__FL_LOC = {lat: plan.location.lat, lon: plan.location.lon, elevation_m: 0};
  function soilClass(s) {
    s = s || {}; var c = s.clay_pct, sa = s.sand_pct, si = s.silt_pct;
    if (c == null || sa == null) return "";
    if (c >= 40) return "silty_clay"; if (c >= 27) return "clay_loam"; if (sa >= 70 && c < 15) return "loamy_sand";
    if (si != null && si >= 50) return "silt"; if (sa >= 52) return "sandy_loam"; return "loam";
  }
  function stage(c, now) {
    if (c.perennial || !c.sowing_month) return "mid_season";
    var months = (now - c.sowing_month + 12) % 12;
    return months <= 1 ? "initial" : months <= 2 ? "development" : months <= 4 ? "mid_season" : months <= 6 ? "late_season" : "initial";
  }
  function apply() {
    try {
      var soilKey = soilClass(plan.soil), method = METHODS[plan.irrigation_method] || "drip", now = new Date().getMonth() + 1;
      var zones = plan.crops.filter(function (c) { return CROPS[c.id]; }).slice(0, 6).map(function (c, i) {
        return {id: "P" + (i + 1), crop: CROPS[c.id], stage: stage(c, now), area: Math.max(0.1, Math.round(c.area_ha * 100) / 100),
          dr: 0, lastDays: 3, soilKey: soilKey, method: method, z: null};
      });
      if (!zones.length || typeof window.__flSetPlots !== "function") return;
      var title = document.querySelector("#title p");
      if (title && title.firstChild) title.firstChild.textContent = "Votre ferme (plan validé) · météo du ";
      window.__flSetPlots(zones);
    } catch (e) { console.warn("FARMLINK: plan not applied", e); }
  }
  if (document.readyState === "complete") setTimeout(apply, 0); else window.addEventListener("load", function () { setTimeout(apply, 0); });
})();`;

/**
 * Post-Harvest: select the first planned crop that HarvestGuard can store. HarvestGuard shows buttons for
 * its first 10 crops only, so planned crops beyond those get a button too (same markup as its own).
 */
const POST_HARVEST_BRIDGE = `(function () {
  ${readPlan}
  var CROPS = ${JSON.stringify(POST_HARVEST_CROP)};
  var planned = plan.crops.map(function (c) { return CROPS[c.id]; }).filter(function (k, i, a) { return k && a.indexOf(k) === i; });
  if (!planned.length) return;
  function apply() {
    try {
      if (typeof selectCrop !== "function" || typeof initCropButtons !== "function") return;
      planned = planned.filter(function (k) { return M.crops[k]; });
      if (!planned.length) return;
      var draw = initCropButtons;
      initCropButtons = function () {
        draw();
        var box = document.getElementById("cropButtons"), shown = Object.keys(M.crops).slice(0, 10);
        planned.forEach(function (k) {
          if (shown.indexOf(k) !== -1 || !box) return;
          var b = document.createElement("button");
          b.className = "crop-btn " + (k === currentCrop ? "active" : "");
          b.innerHTML = '<span class="icon">' + ((typeof CROP_ICONS !== "undefined" && CROP_ICONS[k]) || "🌱") + "</span><span>" + k[0].toUpperCase() + k.slice(1) + "</span>";
          b.onclick = function () { selectCrop(k); };
          box.appendChild(b);
        });
      };
      selectCrop(planned[0]);
    } catch (e) { console.warn("FARMLINK: plan not applied", e); }
  }
  if (document.readyState === "complete") setTimeout(apply, 0); else window.addEventListener("load", function () { setTimeout(apply, 0); });
})();`;

const BRIDGES: Record<string, string> = { "irrigation-3d": IRRIGATION_BRIDGE, "post-harvest": POST_HARVEST_BRIDGE };

export async function GET(_req: Request, { params }: { params: Promise<{ page: string }> }) {
  const { page } = await params;
  const parts = Object.hasOwn(PAGES, page) ? PAGES[page] : undefined;
  if (!parts) return new Response("Not found", { status: 404 });

  const file = path.join(process.cwd(), "..", "..", "research", ...parts);
  let html: string;
  try {
    html = await readFile(file, "utf8");
  } catch {
    return new Response(`Page not found (research/${parts.join("/")}).`, {
      status: 404,
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  }

  if (page === "irrigation-3d") {
    html = html.replace(DEMO_LOCATION, `location: (window.__FL_LOC || {lat: 35.918, lon: 10.558, elevation_m: 10})`);
    const end = html.lastIndexOf(IRRIGATION_CLOSURE_END);
    if (end !== -1) html = html.slice(0, end) + IRRIGATION_HOOK + html.slice(end);
  }
  const bridge = `<script>/* FARMLINK: pre-fill with the validated crop plan */\n${BRIDGES[page]}\n</script>`;
  html = html.includes("</body>") ? html.replace(/<\/body>(?![\s\S]*<\/body>)/, `${bridge}\n</body>`) : html + bridge;

  return new Response(html, {
    headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-cache" },
  });
}
