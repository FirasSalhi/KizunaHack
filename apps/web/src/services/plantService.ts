import { apiClient, getStoredToken } from "./apiClient";
import type { PlantSearchHit, ScanResult, ScanSummary, ScannerStatus, SpeciesSheet } from "@/types/plants";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001/api/v1";

/** Phone photos can be 5–10 MB: send at most 1600 px (JPEG), which is plenty for identification. */
async function shrink(file: File, maxSide = 1600): Promise<Blob> {
  if (typeof createImageBitmap !== "function") return file;
  try {
    const bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
    const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height));
    if (scale === 1 && file.type === "image/jpeg" && file.size < 4 * 1024 * 1024) return file;
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    canvas.getContext("2d")?.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    bitmap.close();
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.9));
    return blob ?? file;
  } catch {
    return file; // unusual formats: let the server try
  }
}

export const plantService = {
  status(): Promise<ScannerStatus> {
    return apiClient<ScannerStatus>("/plants/status");
  },

  async identify(file: File): Promise<ScanResult> {
    const body = await shrink(file);
    return apiClient<ScanResult>("/plants/identify", {
      method: "POST",
      headers: { "Content-Type": body.type || "application/octet-stream" },
      body,
    });
  },

  search(q: string): Promise<PlantSearchHit[]> {
    return apiClient<PlantSearchHit[]>(`/plants/search?q=${encodeURIComponent(q)}`);
  },

  care(speciesId: string): Promise<SpeciesSheet> {
    return apiClient<SpeciesSheet>(`/plants/care/${encodeURIComponent(speciesId)}`);
  },

  listScans(): Promise<ScanSummary[]> {
    return apiClient<ScanSummary[]>("/plants/scans");
  },

  getScan(id: string): Promise<ScanSummary & { result: ScanResult }> {
    return apiClient(`/plants/scans/${id}`);
  },

  fixScan(id: string, speciesId: string): Promise<ScanSummary & { result: ScanResult }> {
    return apiClient(`/plants/scans/${id}`, { method: "PATCH", body: JSON.stringify({ species_id: speciesId }) });
  },

  deleteScan(id: string): Promise<{ deleted: string }> {
    return apiClient(`/plants/scans/${id}`, { method: "DELETE" });
  },

  /** Scan photos need the sign-in token, so they are fetched and shown as object URLs. */
  async photoUrl(id: string, size: "thumb" | "full" = "thumb"): Promise<string | null> {
    const token = getStoredToken();
    const res = await fetch(`${API_BASE_URL}/plants/scans/${id}/image?size=${size}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      credentials: "include",
    });
    return res.ok ? URL.createObjectURL(await res.blob()) : null;
  },
};
