"use client";

/**
 * The farm's location, used by every dashboard page (weather, place name, irrigation, assistant).
 *
 * Order: the validated crop plan's parcel > the place chosen in Crop Planning (search, "Ma position" or a
 * quick button) > this device's position (browser geolocation, asked once) > unknown (pages say so).
 * Kept in this browser (localStorage), like the crop plan.
 */

import { useCallback, useEffect, useState } from "react";
import { PLAN_EVENT, loadPlan } from "@/lib/farmPlan";
import { nearestSeat } from "@/lib/seats";

export { nearestSeat };

export const PLACE_KEY = "fl_place";
export const PLACE_EVENT = "fl-place-change";

export interface Place {
  lat: number;
  lon: number;
  /** Name chosen in the planner (search result or quick button); empty for a device position. */
  name: string;
  source: "plan" | "selected" | "device";
}

const num = (v: unknown, lo: number, hi: number) => typeof v === "number" && Number.isFinite(v) && v >= lo && v <= hi;

export function parsePlace(input: unknown, source: Place["source"]): Place | null {
  if (!input || typeof input !== "object") return null;
  const p = input as Record<string, unknown>;
  if (!num(p.lat, -90, 90) || !num(p.lon, -180, 180)) return null;
  const name = typeof p.name === "string" ? p.name.slice(0, 80).trim() : "";
  return { lat: p.lat as number, lon: p.lon as number, name, source };
}

function readStored(): Place | null {
  try {
    const raw = localStorage.getItem(PLACE_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw) as { source?: unknown };
    return parsePlace(data, data.source === "device" ? "device" : "selected");
  } catch {
    return null;
  }
}

/** Remember a place chosen in Crop Planning, or this device's position. */
export function savePlace(place: Place): void {
  try {
    localStorage.setItem(PLACE_KEY, JSON.stringify(place));
  } catch {
    // storage blocked: the place lives for this page only
  }
  window.dispatchEvent(new Event(PLACE_EVENT));
}

/** Short label: the chosen name, else "near <governorate seat>", else the coordinates. */
export function placeLabel(place: Place, near: (town: string) => string): string {
  if (place.name) return place.name;
  const town = nearestSeat(place.lat, place.lon);
  return town ? near(town) : `${place.lat.toFixed(3)}, ${place.lon.toFixed(3)}`;
}

export type PlaceState = { place: Place | null; status: "ready" | "locating" | "unknown"; locate: () => void };

/** The farm's location for this page; asks the browser for its position once when nothing else is known. */
export function usePlace(): PlaceState {
  const [place, setPlace] = useState<Place | null>(null);
  const [status, setStatus] = useState<PlaceState["status"]>("locating");

  const resolve = useCallback(() => {
    const plan = loadPlan();
    const stored = readStored();
    if (plan) {
      // A place chosen near the parcel keeps its name (same farm).
      const sameFarm = stored && Math.abs(stored.lat - plan.location.lat) < 0.05 && Math.abs(stored.lon - plan.location.lon) < 0.05;
      setPlace({ lat: plan.location.lat, lon: plan.location.lon, name: sameFarm && stored ? stored.name : "", source: "plan" });
      setStatus("ready");
      return true;
    }
    if (stored) {
      setPlace(stored);
      setStatus("ready");
      return true;
    }
    return false;
  }, []);

  const locate = useCallback(() => {
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      setStatus("unknown");
      return;
    }
    setStatus("locating");
    navigator.geolocation.getCurrentPosition(
      (p) => savePlace({ lat: p.coords.latitude, lon: p.coords.longitude, name: "", source: "device" }),
      () => setStatus((s) => (s === "ready" ? s : "unknown")),
      { timeout: 10000, maximumAge: 10 * 60 * 1000 },
    );
  }, []);

  useEffect(() => {
    if (!resolve()) locate();
    const onChange = () => void resolve();
    window.addEventListener(PLACE_EVENT, onChange);
    window.addEventListener(PLAN_EVENT, onChange);
    window.addEventListener("storage", onChange);
    return () => {
      window.removeEventListener(PLACE_EVENT, onChange);
      window.removeEventListener(PLAN_EVENT, onChange);
      window.removeEventListener("storage", onChange);
    };
  }, [resolve, locate]);

  return { place, status, locate };
}
