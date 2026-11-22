/**
 * The farmer's validated crop plan: drawn and chosen once in Crop Planning (MIZU KIZUNA), then reused by
 * Irrigation 3D and Post-Harvest so the farmer never picks the same crops twice.
 *
 * Kept in this browser (localStorage), like the demo session, so it works with or without an account.
 */

export const PLAN_KEY = "fl_farm_plan";
export const PLAN_EVENT = "fl-plan-change";

export interface PlanCrop {
  /** MIZU KIZUNA crop id, e.g. "tomato", "olive" */
  id: string;
  name: string;
  area_ha: number;
  sowing_month: number | null;
  perennial: boolean;
  irrigated: boolean;
  water_m3_typical: number | null;
}

export interface FarmPlan {
  version: 1;
  validated_at: string;
  area_ha: number;
  location: { lat: number; lon: number };
  country: string | null;
  water_source: string | null;
  irrigation_method: string | null;
  soil: { texture: string | null; clay_pct: number | null; sand_pct: number | null; silt_pct: number | null };
  crops: PlanCrop[];
}

const num = (v: unknown, lo: number, hi: number): number | null =>
  typeof v === "number" && Number.isFinite(v) && v >= lo && v <= hi ? v : null;
const str = (v: unknown, max = 80): string | null => (typeof v === "string" && v.length > 0 ? v.slice(0, max) : null);

/** Accept only a well-formed plan (it arrives from another page, and is read back from storage). */
export function parsePlan(input: unknown): FarmPlan | null {
  if (!input || typeof input !== "object") return null;
  const p = input as Record<string, unknown>;
  const loc = (p.location ?? {}) as Record<string, unknown>;
  const lat = num(loc.lat, -90, 90);
  const lon = num(loc.lon, -180, 180);
  const area = num(p.area_ha, 0, 100_000);
  if (lat == null || lon == null || area == null || !Array.isArray(p.crops)) return null;
  const crops: PlanCrop[] = [];
  for (const raw of p.crops.slice(0, 8)) {
    if (!raw || typeof raw !== "object") continue;
    const c = raw as Record<string, unknown>;
    const id = str(c.id, 40);
    const cropArea = num(c.area_ha, 0, 100_000);
    if (!id || !/^[a-z_]+$/.test(id) || cropArea == null) continue;
    crops.push({
      id,
      name: str(c.name) ?? id,
      area_ha: cropArea,
      sowing_month: num(c.sowing_month, 1, 12),
      perennial: c.perennial === true,
      irrigated: c.irrigated === true,
      water_m3_typical: num(c.water_m3_typical, 0, 1e9),
    });
  }
  if (!crops.length) return null;
  const soil = (p.soil ?? {}) as Record<string, unknown>;
  return {
    version: 1,
    validated_at: str(p.validated_at, 40) ?? new Date().toISOString(),
    area_ha: area,
    location: { lat, lon },
    country: str(p.country, 20),
    water_source: str(p.water_source, 20),
    irrigation_method: str(p.irrigation_method, 30),
    soil: {
      texture: str(soil.texture, 40),
      clay_pct: num(soil.clay_pct, 0, 100),
      sand_pct: num(soil.sand_pct, 0, 100),
      silt_pct: num(soil.silt_pct, 0, 100),
    },
    crops,
  };
}

export function loadPlan(): FarmPlan | null {
  try {
    const raw = localStorage.getItem(PLAN_KEY);
    return raw ? parsePlan(JSON.parse(raw)) : null;
  } catch {
    return null;
  }
}

export function savePlan(plan: FarmPlan): void {
  try {
    localStorage.setItem(PLAN_KEY, JSON.stringify(plan));
  } catch {
    // storage blocked (private mode): the plan lives for this page only
  }
  window.dispatchEvent(new Event(PLAN_EVENT));
}

export function clearPlan(): void {
  try {
    localStorage.removeItem(PLAN_KEY);
  } catch {
    // nothing stored
  }
  window.dispatchEvent(new Event(PLAN_EVENT));
}

/** MIZU KIZUNA crop -> Irrigation 3D crop (research/irrigation-notebook crop database). */
export const IRRIGATION_CROP: Record<string, string> = {
  alfalfa: "alfalfa", almond: "almond", apricot: "stone_fruit", barley: "barley", cabbage: "cabbage",
  carrot: "carrot", chickpea: "chickpea", cucumber: "cucumber", date_palm: "date_palm", durum_wheat: "durum_wheat",
  eggplant: "eggplant", faba_bean: "faba_bean", fig: "fig", garlic: "garlic", grape: "grape_wine", lettuce: "lettuce",
  mandarin_jp: "citrus", melon: "melon", olive: "olive", onion: "onion_dry", orange: "citrus", pea: "green_bean",
  pepper: "sweet_pepper", pistachio: "pistachio", pomegranate: "pomegranate", potato: "potato",
  strawberry: "strawberry", tomato: "tomato", watermelon: "watermelon", wheat: "durum_wheat",
};

/** MIZU KIZUNA crop -> Post-Harvest (HarvestGuard) crop, for the crops it can store. */
export const POST_HARVEST_CROP: Record<string, string> = {
  tomato: "tomato", potato: "potato", orange: "orange", mandarin_jp: "orange", strawberry: "strawberry",
  lettuce: "lettuce", carrot: "carrot", onion: "onion", cabbage: "cabbage", pepper: "pepper", olive: "olive",
  garlic: "garlic", wheat: "wheat", durum_wheat: "wheat", date_palm: "dates",
};

/** MIZU KIZUNA crop -> Market "best month to sell" crop (research/market-advisor, Tunis retail prices). */
export const MARKET_CROP: Record<string, string> = {
  tomato: "tomato", potato: "potato", onion: "onion", pepper: "sweet_pepper", carrot: "carrot",
  cabbage: "cabbage", garlic: "garlic", date_palm: "date",
};

/** MIZU KIZUNA crop -> Solar pump simulation crop (research/solar-pump, FAO-56 Kc). */
export const SOLAR_CROP: Record<string, string> = {
  tomato: "tomato", pepper: "pepper", potato: "potato", watermelon: "watermelon", olive: "olive",
  orange: "citrus", mandarin_jp: "citrus", date_palm: "date_palm",
};

/** MIZU KIZUNA irrigation method -> Irrigation 3D method. */
export const IRRIGATION_METHOD: Record<string, string> = {
  goutte_a_goutte: "drip", aspersion: "sprinkler", gravitaire: "surface",
};

/** SoilGrids texture (clay / sand / silt %) -> the Irrigation 3D soil classes. */
export function soilClass(soil: FarmPlan["soil"]): string {
  const { clay_pct: clay, sand_pct: sand, silt_pct: silt } = soil;
  if (clay == null || sand == null) return "";
  if (clay >= 40) return "silty_clay";
  if (clay >= 27) return "clay_loam";
  if (sand >= 70 && clay < 15) return "loamy_sand";
  if (silt != null && silt >= 50) return "silt";
  if (sand >= 52) return "sandy_loam";
  return "loam";
}
