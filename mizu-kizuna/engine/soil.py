"""Profil de sol : SoilGrids → texture USDA, groupe EcoCrop, réserve utile, alertes."""
from .i18n import t, texture as tr_texture
from .sources import SourceUnavailable, soilgrids

# Réserve utile (θFC − θWP) en mm d'eau par mètre de sol, milieu des plages FAO-56 tableau 19
TAW = {"sable": 80, "sable limoneux": 90, "limon sableux": 130, "limon": 155, "limon fin": 180,
       "silt": 170, "limon argilo-sableux": 150, "limon argileux": 160, "limon argilo-fin": 160,
       "argile sableuse": 170, "argile limoneuse": 185, "argile": 190}
ECO_GROUP = {"sable": "light", "sable limoneux": "light", "limon sableux": "light",
             "limon": "medium", "limon fin": "medium", "silt": "medium", "limon argilo-sableux": "medium",
             "limon argileux": "medium", "limon argilo-fin": "medium",
             "argile sableuse": "heavy", "argile limoneuse": "heavy", "argile": "heavy"}
GROUP_FR = {"light": "léger (sableux)", "medium": "moyen (limoneux)", "heavy": "lourd (argileux)"}

PRESETS = {  # choix manuel de l'agriculteur
    "sableux":  {"clay": 8, "sand": 82, "silt": 10, "ph": 7.9, "soc": 3},
    "limoneux": {"clay": 20, "sand": 40, "silt": 40, "ph": 7.6, "soc": 9},
    "argileux": {"clay": 45, "sand": 20, "silt": 35, "ph": 7.8, "soc": 12},
    "acide":    {"clay": 25, "sand": 35, "silt": 40, "ph": 5.4, "soc": 30},
}


def usda_texture(sand, silt, clay):
    """Triangle des textures USDA (noms français)."""
    if silt + 1.5 * clay < 15:
        return "sable"
    if silt + 1.5 * clay >= 15 and silt + 2 * clay < 30:
        return "sable limoneux"
    if (7 <= clay < 20 and sand > 52 and silt + 2 * clay >= 30) or (clay < 7 and silt < 50 and silt + 2 * clay >= 30):
        return "limon sableux"
    if 7 <= clay < 27 and 28 <= silt < 50 and sand <= 52:
        return "limon"
    if (silt >= 50 and 12 <= clay < 27) or (50 <= silt < 80 and clay < 12):
        return "limon fin"
    if silt >= 80 and clay < 12:
        return "silt"
    if 20 <= clay < 35 and silt < 28 and sand > 45:
        return "limon argilo-sableux"
    if 27 <= clay < 40 and 20 < sand <= 45:
        return "limon argileux"
    if 27 <= clay < 40 and sand <= 20:
        return "limon argilo-fin"
    if clay >= 35 and sand > 45:
        return "argile sableuse"
    if clay >= 40 and silt >= 40:
        return "argile limoneuse"
    return "argile"


def build_profile(clay, sand, silt, ph, soc, source, cec=None, extra=None):
    tex = usda_texture(sand, silt, clay)
    group = ECO_GROUP[tex]
    alerts = []
    if ph >= 8.3:
        alerts.append(t("s.a.alk", ph=round(ph, 1)))
    elif ph < 5.5:
        alerts.append(t("s.a.acid", ph=round(ph, 1)))
    if soc is not None and soc < 6:
        alerts.append(t("s.a.om", soc=round(soc, 1)))
    if group == "light":
        alerts.append(t("s.a.light"))
    if group == "heavy":
        alerts.append(t("s.a.heavy"))
    return {"texture": tr_texture(tex), "texture_code": tex, "group": group, "group_label": t("s.group." + group),
            "clay_pct": round(clay), "sand_pct": round(sand), "silt_pct": round(silt),
            "ph": round(ph, 1), "soc_g_kg": None if soc is None else round(soc, 1),
            "cec_cmol_kg": None if cec is None else round(cec, 1),
            "taw_mm_m": TAW[tex], "alerts": alerts, "source": source, **(extra or {})}


COUNTRY_DEFAULT = {"tunisie": "limoneux", "japon": "japon_andosol"}
PRESETS["japon_andosol"] = {"clay": 22, "sand": 38, "silt": 40, "ph": 5.9, "soc": 45}
PRESETS["limoneux"]["ph"] = 7.9


def get_soil(lat, lon, preset=None, online=True, country="tunisie"):
    if preset:
        p = PRESETS[preset]
        return build_profile(p["clay"], p["sand"], p["silt"], p["ph"], p["soc"], t("s.src.user"))
    if online:
        try:
            s = soilgrids(lat, lon)
            g = lambda k: s.get(k, {}).get("topsoil")
            clay, sand = g("clay"), g("sand")
            silt = g("silt") if g("silt") is not None else max(0, 100 - clay - sand)
            return build_profile(clay, sand, silt, g("phh2o"), g("soc"),
                                 t("s.src.sg"),
                                 cec=g("cec"), extra={"by_depth": {k: v["by_depth"] for k, v in s.items()}})
        except SourceUnavailable:
            pass
    p = PRESETS[COUNTRY_DEFAULT.get(country, "limoneux")]
    prof = build_profile(p["clay"], p["sand"], p["silt"], p["ph"], p["soc"],
                         t("s.src.default"))
    prof["default"] = True
    return prof
