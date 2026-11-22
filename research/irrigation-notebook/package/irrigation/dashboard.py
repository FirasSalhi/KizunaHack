"""Crop-specific irrigation dashboard (matplotlib, CPU only).

Colours: first three slots of a validated categorical palette (blue, orange, aqua) identify
crops; status colours are always paired with a text label.
"""
from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

CROP_COLORS = {"tomato": "#2a78d6", "olive": "#eb6834", "durum_wheat": "#1baf7a"}
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e3e2de", "#fcfcfb"
STATUS = {"NOW": ("#b3261e", "IRRIGATE NOW"), "WITHIN_HORIZON": ("#b26a00", "IRRIGATE WITHIN HORIZON"),
          "NOT_NEEDED": ("#1d6b3a", "NO IRRIGATION NEEDED")}


def _tile(ax, title, value, sub="", color=INK):
    ax.set_facecolor("#f3f2ee")
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.text(0.05, 0.84, title, transform=ax.transAxes, fontsize=9.5, color=MUTED, va="top")
    ax.text(0.05, 0.50, value, transform=ax.transAxes, fontsize=14, fontweight="bold", color=color, va="center")
    ax.text(0.05, 0.14, sub, transform=ax.transAxes, fontsize=8, color=MUTED, va="bottom")


def _clean(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#b9b8b2")
    ax.grid(axis="y", color=GRID, lw=0.8); ax.grid(axis="x", visible=False)
    ax.tick_params(colors=MUTED, labelsize=9)


def plot_dashboard(dec: dict, *, soil, profile_now: dict, theta_fc_by_depth: dict | None,
                   stage_etc_df, sim_df, path, title="Crop-specific irrigation intelligence", data_note=""):
    fig = plt.figure(figsize=(18, 11.5))
    fig.patch.set_facecolor(SURFACE)
    gs = GridSpec(3, 6, figure=fig, height_ratios=[2.2, 2.2, 1.1], hspace=0.5, wspace=0.55, top=0.82, bottom=0.04)
    gt = GridSpec(1, 6, figure=fig, top=0.925, bottom=0.845, wspace=0.07)
    fig.suptitle(title, fontsize=17, fontweight="bold", x=0.05, ha="left", y=0.985, color=INK)
    ok = dec.get("status") == "OK"

    # ---- KPI tiles -----------------------------------------------------------------
    f = lambda v, d=1: "n/a" if v is None else f"{v:.{d}f}"
    _tile(fig.add_subplot(gt[0, 0]), "Crop / stage", f"{dec['crop_fr']}", f"{dec['stage']} | Kc {dec['kc']:.2f}")
    _tile(fig.add_subplot(gt[0, 1]), "Crop water use (ETc)", f"{f(dec['etc_mm'],2)} mm/d", f"ETo {f(dec['eto_mm'],2)} mm/d ({dec['eto_method'].replace('FAO56_Penman_Monteith','Penman-Monteith').replace('Hargreaves_Samani(fallback)','Hargreaves*')})")
    th = dec.get("theta_rz_now")
    _tile(fig.add_subplot(gt[0, 2]), "Root-zone moisture now", "n/a" if th is None else f"{100*th:.1f} %",
          "forecast " + ("n/a" if dec.get("theta_rz_forecast") is None else f"{100*dec['theta_rz_forecast']:.1f} %"))
    frac = dec.get("dr_fraction_of_taw")
    _tile(fig.add_subplot(gt[0, 3]), "Depletion / RAW", "withheld" if not ok else f"{f(dec['dr_now_mm'])} / {f(dec['raw_mm'])} mm",
          "" if not ok else f"{100*frac:.0f} % of TAW {dec['taw_mm']:.0f} mm")
    col, label = STATUS.get(dec.get("timing"), ("#6b1f8a", "WITHHELD - " + dec.get("status", "")))
    _tile(fig.add_subplot(gt[0, 4]), "Recommendation", label, f"readiness: {dec['readiness']}", col)
    vol = "n/a" if dec.get("net_mm") is None else f"{dec['net_mm']:.1f} mm net"
    _tile(fig.add_subplot(gt[0, 5]), "Irrigation volume", vol, "" if dec.get("gross_mm") is None else f"{dec['gross_mm']:.1f} mm gross (Ea)")

    # ---- soil profile ------------------------------------------------------------------
    ax = fig.add_subplot(gs[0, 0:2]); _clean(ax)
    layers = profile_now["layers"] if profile_now else []
    for l in layers:
        d = l["sensor_cm"]
        ax.barh(d, 100 * l["theta"], height=min(14, l["thickness_cm"] * 0.8), color="#2a78d6", label="measured now" if d == layers[0]["sensor_cm"] else None)
        ax.text(100 * l["theta"] + 0.3, d, f"{100*l['theta']:.1f} %", va="center", fontsize=9, color=INK)
        if theta_fc_by_depth and d in theta_fc_by_depth:
            ax.plot(theta_fc_by_depth[d], d, "D", color="#eb6834", ms=8, mec=SURFACE, mew=1.5, label="forecast")
    if soil is not None:
        ax.axvline(100 * soil.fc, color="#1d6b3a", ls="--", lw=1.6); ax.text(100 * soil.fc, 0.02, " FC", transform=ax.get_xaxis_transform(), color="#1d6b3a", fontsize=9)
        ax.axvline(100 * soil.wp, color="#b3261e", ls="--", lw=1.6); ax.text(100 * soil.wp, 0.02, " WP", transform=ax.get_xaxis_transform(), color="#b3261e", fontsize=9)
    ax.set_xlim(0, 100 * max(soil.fc if soil else 0.2, max([l["theta"] for l in layers] + [0.1])) * 1.35)
    ax.invert_yaxis(); ax.set_xlabel("VWC (%)"); ax.set_ylabel("sensor depth (cm)")
    ax.set_title("Measured soil moisture vs declared FC / WP", loc="left", fontsize=11, fontweight="bold", color=INK)
    ax.grid(axis="y", visible=False); ax.legend(frameon=False, fontsize=9, loc="lower right")

    # ---- root-zone water bar ---------------------------------------------------------
    ax = fig.add_subplot(gs[0, 2:3]); _clean(ax)
    if ok:
        taw, raw, dr = dec["taw_mm"], dec["raw_mm"], dec["dr_now_mm"]
        ax.bar([0], [taw], color="#e3e2de", width=0.6)
        ax.bar([0], [dr], color="#2a78d6", width=0.6)
        ax.axhline(raw, color="#b3261e", ls="--", lw=1.6)
        ax.text(0.33, raw, f"RAW {raw:.0f}", color="#b3261e", va="bottom", fontsize=9)
        ax.text(0, dr / 2, f"Dr {dr:.0f}", ha="center", color="white", fontsize=10, fontweight="bold")
        ax.text(0, taw, f"TAW {taw:.0f}", ha="center", va="bottom", color=MUTED, fontsize=9)
        ax.set_ylim(0, taw * 1.12)
    else:
        ax.text(0.5, 0.5, "withheld\n(see warnings)", transform=ax.transAxes, ha="center", color=MUTED)
    ax.set_xlim(-0.6, 1.0); ax.set_xticks([]); ax.set_ylabel("mm"); ax.grid(False)
    ax.set_title("Root-zone depletion", loc="left", fontsize=11, fontweight="bold", color=INK)

    # ---- ETc by crop & stage ----------------------------------------------------------------
    ax = fig.add_subplot(gs[0, 3:6]); _clean(ax)
    stages = list(dict.fromkeys(stage_etc_df["stage"]))
    crops = list(dict.fromkeys(stage_etc_df["crop"]))
    w = 0.26
    for j, c in enumerate(crops):
        sub = stage_etc_df[stage_etc_df["crop"] == c].set_index("stage").loc[stages]
        xs = [i + (j - 1) * w for i in range(len(stages))]
        ax.bar(xs, sub["etc_mm"], width=w - 0.03, color=CROP_COLORS[c], label=c.replace("_", " "))
        ax.errorbar(xs, sub["etc_mm"], yerr=[sub["etc_mm"] - sub["etc_low_mm"], sub["etc_high_mm"] - sub["etc_mm"]],
                    fmt="none", ecolor=INK, lw=1, capsize=2)
    ax.set_xticks(range(len(stages))); ax.set_xticklabels([s.replace("_", "\n") for s in stages])
    ax.set_ylabel("ETc (mm/day)"); ax.set_ylim(0, ax.get_ylim()[1] * 1.3); ax.legend(frameon=False, fontsize=9, ncol=3, loc="upper left")
    ax.set_title("Same weather, different crops and stages (bars: FAO-56 Kc range)", loc="left", fontsize=11, fontweight="bold", color=INK)

    # ---- simulated depletion ------------------------------------------------------------------
    ax = fig.add_subplot(gs[1, 0:4]); _clean(ax)
    for c, g in sim_df.groupby("crop"):
        ax.plot(g["day"], g["dr_end_mm"], color=CROP_COLORS[c], lw=2, label=c.replace("_", " "))
        ax.plot(g["day"], g["RAW_mm"], color=CROP_COLORS[c], lw=1, ls=":")
        ev = g[g["irrigation_net_mm"] > 0]
        ax.plot(ev["day"], ev["dr_before_irrigation_mm"], "o", color=CROP_COLORS[c], ms=8, mec=SURFACE, mew=1.5)
    ax.set_xlabel("day of simulation"); ax.set_ylabel("depletion (mm)")
    ax.set_title("Scenario simulation (declared assumptions): depletion, RAW (dotted), irrigation events (dots)", loc="left", fontsize=11, fontweight="bold", color=INK)
    ax.set_ylim(0, ax.get_ylim()[1] * 1.25); ax.legend(frameon=False, fontsize=9, ncol=3, loc="upper left")

    # ---- reasoning & warnings --------------------------------------------------------------
    ax = fig.add_subplot(gs[1, 4:6]); ax.axis("off")
    txt = "WHY\n" + "\n".join("- " + e for e in dec["explanation"][:3])
    ax.text(0, 1, _wrap(txt, 52), va="top", fontsize=8.8, color=INK, transform=ax.transAxes)

    ax = fig.add_subplot(gs[2, :]); ax.axis("off")
    warns = dec["warnings"]
    box = "CONFIDENCE: " + dec["confidence"] + "   |   DATA-QUALITY WARNINGS\n" + "\n".join("! " + w_ for w_ in warns[:5])
    if data_note:
        box += "\n" + data_note
    ax.text(0, 1, _wrap(box, 215), va="top", fontsize=8.6, color="#7a1c14", transform=ax.transAxes,
            bbox=dict(boxstyle="round,pad=0.5", fc="#fff4ec", ec="#eb6834"))
    fig.savefig(path, dpi=130, bbox_inches="tight", facecolor=SURFACE)
    return fig


def _wrap(text, width):
    import textwrap
    out = []
    for line in text.split("\n"):
        out.extend(textwrap.wrap(line, width, subsequent_indent="  ") or [""])
    return "\n".join(out)
