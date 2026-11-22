import { readFile } from "node:fs/promises";
import path from "node:path";

/**
 * Serves the HarvestGuard post-harvest digital twin (research/post-harvest-model) as-is, from the same
 * origin as the app, so the dashboard's Post-Harvest section can show it in a frame. The page is the
 * branch's own standalone HTML; nothing in it is changed here.
 */
const PAGE = path.join(process.cwd(), "..", "..", "research", "post-harvest-model", "dashboard", "farmer_dashboard.html");

export async function GET() {
  try {
    const html = await readFile(PAGE, "utf8");
    return new Response(html, {
      headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-cache" },
    });
  } catch {
    return new Response("Post-harvest dashboard not found (research/post-harvest-model/dashboard/farmer_dashboard.html).", {
      status: 404,
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  }
}
