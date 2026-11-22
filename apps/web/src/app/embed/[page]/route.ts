import { readFile } from "node:fs/promises";
import path from "node:path";

/**
 * Serves the standalone research pages shown in dashboard sections, unchanged and from the same origin as
 * the app, so the dashboard can show them in a frame. Only the pages listed here can be served.
 */
const PAGES: Record<string, string[]> = {
  // Dashboard > Post-Harvest: HarvestGuard cold-storage digital twin (branch post-harvest-model)
  "post-harvest": ["post-harvest-model", "dashboard", "farmer_dashboard.html"],
  // Dashboard > 3D Irrigation: the farmer's 3D farm with per-field irrigation decisions (branch fatma)
  "irrigation-3d": ["irrigation-notebook", "html", "ferme_3d.html"],
};

export async function GET(_req: Request, { params }: { params: Promise<{ page: string }> }) {
  const { page } = await params;
  const parts = Object.hasOwn(PAGES, page) ? PAGES[page] : undefined;
  if (!parts) return new Response("Not found", { status: 404 });

  const file = path.join(process.cwd(), "..", "..", "research", ...parts);
  try {
    const html = await readFile(file, "utf8");
    return new Response(html, {
      headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-cache" },
    });
  } catch {
    return new Response(`Page not found (research/${parts.join("/")}).`, {
      status: 404,
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  }
}
