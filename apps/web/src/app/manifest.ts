import type { MetadataRoute } from "next";

/** Web app manifest: lets phones install Mdhalla to the home screen and open it full-screen (FR-033). */
export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/",
    name: "Mdhalla",
    short_name: "Mdhalla",
    description: "Agriculture de précision : capteurs, IA et irrigation pour votre ferme.",
    lang: "fr",
    start_url: "/dashboard",
    scope: "/",
    display: "standalone",
    background_color: "#020302",
    theme_color: "#020302",
    categories: ["productivity", "utilities"],
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icons/icon-maskable-192.png", sizes: "192x192", type: "image/png", purpose: "maskable" },
      { src: "/icons/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
    shortcuts: [
      { name: "Scanner de plantes", url: "/dashboard/scanner", icons: [{ src: "/icons/icon-192.png", sizes: "192x192" }] },
      { name: "Planification des cultures", url: "/dashboard/planning", icons: [{ src: "/icons/icon-192.png", sizes: "192x192" }] },
      { name: "Irrigation 3D", url: "/dashboard/irrigation-3d", icons: [{ src: "/icons/icon-192.png", sizes: "192x192" }] },
    ],
  };
}
