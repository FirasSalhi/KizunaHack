import { describe, expect, it } from "vitest";
import { IRRIGATION_CROP, MARKET_CROP, parsePlan, POST_HARVEST_CROP, SOLAR_CROP, soilClass } from "@/lib/farmPlan";
import { nearestSeat } from "@/lib/seats";

// The message "Valider ce plan" sends from the crop planner (mizu-kizuna/static/app.js, sendPlan)
const fromPlanner = {
  version: 1,
  validated_at: "2026-11-22T10:00:00.000Z",
  area_ha: 31.77,
  location: { lat: 36.53, lon: 10.65 },
  country: "tunisie",
  water_source: "puits",
  irrigation_method: "goutte_a_goutte",
  soil: { texture: "limon argileux", clay_pct: 31, sand_pct: 36, silt_pct: 32 },
  crops: [
    { id: "onion", name: "Oignon", area_ha: 15.9, sowing_month: 11, perennial: false, irrigated: true, water_m3_typical: 46066 },
    { id: "strawberry", name: "Fraise", area_ha: 8.5, sowing_month: 10, perennial: false, irrigated: true, water_m3_typical: 33126 },
    { id: "grape", name: "Vigne", area_ha: 7.4, sowing_month: 1, perennial: true, irrigated: true, water_m3_typical: 75390 },
  ],
};

describe("Validated crop plan", () => {
  it("keeps a plan sent by the crop planner", () => {
    const plan = parsePlan(fromPlanner);
    expect(plan?.crops.map((c) => [c.id, c.area_ha])).toEqual([
      ["onion", 15.9],
      ["strawberry", 8.5],
      ["grape", 7.4],
    ]);
    expect(plan?.location).toEqual({ lat: 36.53, lon: 10.65 });
  });

  it("rejects malformed plans and bad crop entries", () => {
    expect(parsePlan(null)).toBeNull();
    expect(parsePlan({ ...fromPlanner, location: { lat: 999, lon: 0 } })).toBeNull();
    expect(parsePlan({ ...fromPlanner, crops: [] })).toBeNull();
    const plan = parsePlan({ ...fromPlanner, crops: [...fromPlanner.crops, { id: "<script>", area_ha: 1 }, { id: "tomato", area_ha: -2 }] });
    expect(plan?.crops).toHaveLength(3);
  });

  it("maps the planned crops onto Irrigation 3D and Post-Harvest crops", () => {
    expect(fromPlanner.crops.map((c) => IRRIGATION_CROP[c.id])).toEqual(["onion_dry", "strawberry", "grape_wine"]);
    expect(fromPlanner.crops.map((c) => POST_HARVEST_CROP[c.id]).filter(Boolean)).toEqual(["onion", "strawberry"]);
    expect(fromPlanner.crops.map((c) => MARKET_CROP[c.id]).filter(Boolean)).toEqual(["onion"]);
    expect(["tomato", "orange", "onion"].map((id) => SOLAR_CROP[id])).toEqual(["tomato", "citrus", undefined]);
    expect(nearestSeat(fromPlanner.location.lat, fromPlanner.location.lon)).toBe("Nabeul");
  });

  it("turns the SoilGrids texture into an Irrigation 3D soil class", () => {
    expect(soilClass(fromPlanner.soil)).toBe("clay_loam");
    expect(soilClass({ texture: null, clay_pct: 8, sand_pct: 80, silt_pct: 12 })).toBe("loamy_sand");
    expect(soilClass({ texture: null, clay_pct: null, sand_pct: null, silt_pct: null })).toBe("");
  });
});
