"""FARMLINK - Agricultural Market Intelligence & Investment Advisor (Streamlit dashboard).

Run from research/market-advisor:   streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from farmlink_market import advisor as A  # noqa: E402
from farmlink_market import crops as C  # noqa: E402
from farmlink_market import kpis as K  # noqa: E402

GREEN, DARK, BG = "#2E7D32", "#1B4332", "#F7F9F7"
PALETTE = [GREEN, "#66BB6A", "#A5D6A7", "#1B4332", "#C8E6C9", "#81C784", "#388E3C", "#43A047"]
st.set_page_config(page_title="FARMLINK – Market Intelligence", page_icon="🌱", layout="wide")
st.markdown(f"""
<style>
.stApp {{ background: {BG}; }}
[data-testid="stSidebar"] {{ background: {DARK}; }}
[data-testid="stSidebar"] * {{ color: #E8F5E9 !important; }}
h1, h2, h3 {{ color: {DARK}; }}
.card {{ background: white; border: 1px solid #E3E8E3; border-radius: 12px; padding: 14px 16px; height: 100%; }}
.card .label {{ color: #5f6b5f; font-size: 0.82rem; }}
.card .value {{ color: {DARK}; font-size: 1.55rem; font-weight: 700; line-height: 1.2; }}
.card .sub {{ color: #6b776b; font-size: 0.78rem; }}
.src {{ color: #6b776b; font-size: 0.78rem; margin-top: -6px; }}
.badge {{ display:inline-block; padding: 1px 8px; border-radius: 999px; font-size: 0.75rem; background:#E8F5E9; color:{DARK}; }}
</style>""", unsafe_allow_html=True)


@st.cache_data
def data() -> K.Data:
    return K.load()


@st.cache_data
def sources() -> dict:
    return json.loads((ROOT / "data" / "metadata" / "sources.json").read_text(encoding="utf-8"))


@st.cache_data
def quality() -> dict:
    return json.loads((ROOT / "data" / "metadata" / "data_quality_report.json").read_text(encoding="utf-8"))


def card(col, label: str, value: str, sub: str = "") -> None:
    col.markdown(f'<div class="card"><div class="label">{label}</div><div class="value">{value}</div>'
                 f'<div class="sub">{sub}</div></div>', unsafe_allow_html=True)


def src(text: str) -> None:
    st.markdown(f'<div class="src">Source : {text}</div>', unsafe_allow_html=True)


def fmt_t(x: float) -> str:
    return f"{x:,.0f} t".replace(",", " ")


def fmt_pct(x: float) -> str:
    return "n.d." if pd.isna(x) else f"{x:+.1f} %"


def month_label(d) -> str:
    return "–" if pd.isna(d) else f"{K.MONTHS_FR[d.month - 1]} {d.year}"


def style(fig, h: int = 340):
    fig.update_layout(height=h, margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor="white", plot_bgcolor="white",
                      font=dict(color="#263326"), legend_title_text="", colorway=PALETTE)
    fig.update_xaxes(gridcolor="#EEF2EE")
    fig.update_yaxes(gridcolor="#EEF2EE")
    return fig


ARR_SRC = "INS, Bulletin mensuel (tableau 9.5) – Marché de gros de Tunis. Apports au marché de gros de Tunis uniquement."
RET_SRC = "INS, Bulletin mensuel (tableau 9.1) – prix moyens de détail à Tunis."
MOA_SRC = "Ministère de l'Agriculture (catalog.data.gov.tn) – séries nationales des cultures maraîchères."


# ================================================================== Page 1
def page_market() -> None:
    d = data()
    st.title("Vue du marché")
    st.caption("Agricultural Market Intelligence & Investment Advisor · Marché de gros de Tunis et production nationale")
    cov = K.season_coverage(d.arrivals)
    seasons = cov[cov.months_reported >= 10].season.tolist()
    default = K.latest_complete_season(d.arrivals)
    c1, c2 = st.columns([1, 3])
    season = c1.selectbox("Campagne agricole (sept. → août)", seasons[::-1],
                          index=seasons[::-1].index(default) if default in seasons else 0)
    row = cov[cov.season == season].iloc[0]
    if not row.complete:
        c2.warning(f"Campagne incomplète : {row.months_reported}/12 mois publiés (manquants : "
                   f"{', '.join(row.missing_months)}). Les totaux portent sur les mois disponibles.")
    else:
        c2.success(f"Campagne {season} complète : 12 mois publiés par l'INS. C'est la dernière campagne complète.")
    k = K.arrivals_kpis(d.arrivals, season)
    tv, tf = k[k.crop_id == "total_vegetables"], k[k.crop_id == "total_fruits"]
    cols = st.columns(4)
    if len(tv):
        card(cols[0], "Apports de légumes · Tunis", fmt_t(tv.total_t.iloc[0]), f"vs campagne précédente : {fmt_pct(tv.yoy_pct.iloc[0])}")
    if len(tf):
        card(cols[1], "Apports de fruits · Tunis", fmt_t(tf.total_t.iloc[0]), f"vs campagne précédente : {fmt_pct(tf.yoy_pct.iloc[0])}")
    pk = K.producer_price_kpis(d.veg, d.cpi)
    pr = K.production_kpis(d.veg)
    tom = pr[pr.crop_id == "tomato"]
    if len(tom):
        card(cols[2], f"Production nationale de tomate {tom.last_year.iloc[0]}", fmt_t(tom.production_t.iloc[0]),
             f"vs année précédente : {fmt_pct(tom.production_yoy_pct.iloc[0])}")
    tot = pr[~pr.crop_id.isin(["other_vegetables"])].production_t.sum() + pr[pr.crop_id == "other_vegetables"].production_t.sum()
    card(cols[3], f"Production maraîchère nationale {int(pr.last_year.max())}", fmt_t(tot), "toutes cultures maraîchères")
    st.write("")
    a, b = st.columns(2)
    for col, cat, title in ((a, "vegetable", "Top 5 des légumes"), (b, "fruit", "Top 5 des fruits")):
        top = K.top_by_arrivals(k, cat)
        fig = px.bar(top.sort_values("total_t"), x="total_t", y="crop", orientation="h", text="total_t",
                     labels={"total_t": "tonnes", "crop": ""}, color_discrete_sequence=[GREEN if cat == "vegetable" else "#66BB6A"])
        fig.update_traces(texttemplate="%{text:,.0f} t", textposition="outside", cliponaxis=False)
        fig.update_xaxes(range=[0, top.total_t.max() * 1.25])
        col.subheader(title)
        col.plotly_chart(style(fig, 300), use_container_width=True)
        with col:
            src(f"{ARR_SRC} Campagne {season}, mois disponibles.")
            st.dataframe(top.assign(**{"Pic": top.peak_month.map(month_label), "Creux": top.low_month.map(month_label),
                                       "Évolution": top.yoy_pct.map(fmt_pct)})[["crop", "total_t", "Pic", "Creux", "Évolution"]]
                         .rename(columns={"crop": "Produit", "total_t": "Tonnes"}), hide_index=True,
                         column_config={"Tonnes": st.column_config.NumberColumn(format="%.0f")}, use_container_width=True)
    st.subheader("Plus fortes hausses et baisses des apports")
    up, down = K.arrival_movers(k)
    u, dn = st.columns(2)
    for col, df, label in ((u, up, "Hausse"), (dn, down, "Baisse")):
        col.markdown(f"**{label}** · campagne {season} vs {k.previous_season.iloc[0]}, mêmes mois, produits ≥ 2 000 t")
        col.dataframe(df.assign(**{"Évolution": df.yoy_pct.map(fmt_pct)})[["crop", "total_t", "Évolution", "yoy_months_compared"]]
                      .rename(columns={"crop": "Produit", "total_t": "Tonnes", "yoy_months_compared": "Mois comparés"}),
                      hide_index=True, use_container_width=True,
                      column_config={"Tonnes": st.column_config.NumberColumn(format="%.0f")})
    src(ARR_SRC + " Seuls les mois publiés dans les deux campagnes sont comparés.")

    st.subheader("Apports mensuels au marché de gros de Tunis")
    arr = d.arrivals[~d.arrivals.crop_id.isin(K.AGGREGATES)].dropna(subset=["crop_id"])
    names = {c: K.name_fr(c) for c in arr.crop_id.unique()}
    f1, f2 = st.columns([3, 2])
    sel = f1.multiselect("Produits", sorted(names, key=names.get), default=["tomato", "potato", "onion", "hot_pepper"],
                         format_func=names.get, key="arr_sel")
    years = sorted(d.arrivals.date.dt.year.unique())
    yr = f2.select_slider("Années", years, value=(years[max(0, len(years) - 3)], years[-1]), key="arr_years")
    m = arr[arr.crop_id.isin(sel) & arr.date.dt.year.between(*yr)].copy()
    m["tonnes"] = m.arrivals_t.where(m.status != "no_arrivals", 0)
    m["Produit"] = m.crop_id.map(names)
    fig = px.line(m, x="date", y="tonnes", color="Produit", markers=True, labels={"date": "", "tonnes": "tonnes / mois"})
    st.plotly_chart(style(fig, 360), use_container_width=True)
    src(ARR_SRC + " Les mois non publiés (« … ») apparaissent comme des trous ; « /// » (pas d'apport) = 0 t.")

    st.subheader("Prix de détail à Tunis")
    ret = d.retail
    rn = {c: K.name_fr(c) for c in ret.crop_id.unique()}
    r1, r2 = st.columns([3, 2])
    rsel = r1.multiselect("Produits", sorted(rn, key=rn.get), default=["tomato", "potato", "onion", "sweet_pepper"],
                          format_func=rn.get, key="ret_sel")
    ryr = r2.select_slider("Années", sorted(ret.date.dt.year.unique()),
                           value=(int(ret.date.dt.year.min()), int(ret.date.dt.year.max())), key="ret_years")
    rr = ret[ret.crop_id.isin(rsel) & ret.date.dt.year.between(*ryr)].assign(Produit=lambda x: x.crop_id.map(rn))
    fig = px.line(rr, x="date", y="retail_price_dt_kg", color="Produit", markers=True,
                  labels={"date": "", "retail_price_dt_kg": "DT / kg"})
    st.plotly_chart(style(fig, 340), use_container_width=True)
    src(RET_SRC)
    rk = K.retail_kpis(d.retail, season)
    if len(rk):
        st.markdown(f"**Prix de détail moyens, campagne {season}** – les prix les plus stables ont la plus faible variation mensuelle.")
        st.dataframe(rk.sort_values("cv_pct")[["crop", "avg_dt_kg", "min_dt_kg", "max_dt_kg", "cv_pct", "yoy_pct", "months"]]
                     .rename(columns={"crop": "Produit", "avg_dt_kg": "Moyenne DT/kg", "min_dt_kg": "Min", "max_dt_kg": "Max",
                                      "cv_pct": "Variation mensuelle (%)", "yoy_pct": "vs campagne préc. (%)", "months": "Mois"}),
                     hide_index=True, use_container_width=True,
                     column_config={c: st.column_config.NumberColumn(format="%.2f") for c in
                                    ["Moyenne DT/kg", "Min", "Max"]} | {
                         "Variation mensuelle (%)": st.column_config.NumberColumn(format="%.0f"),
                         "vs campagne préc. (%)": st.column_config.NumberColumn(format="%+.1f")})

    st.subheader("Production nationale et prix à la production")
    p1, p2 = st.columns(2)
    v = d.veg[d.veg.crop_id != "other_vegetables"].assign(Culture=lambda x: x.crop_id.map(K.name_fr))
    fig = px.line(v, x="year", y="production_t", color="Culture", labels={"year": "", "production_t": "tonnes"})
    p1.plotly_chart(style(fig, 320), use_container_width=True)
    fig = px.line(v, x="year", y=v.producer_price_dt_t / 1000, color="Culture", labels={"year": "", "y": "DT / kg (courants)"})
    p2.plotly_chart(style(fig, 320), use_container_width=True)
    src(MOA_SRC + " Prix à la production en dinars courants (non corrigés de l'inflation).")
    st.dataframe(pk[pk.crop_id != "other_vegetables"][["crop", "last_year", "price_dt_kg", "yoy_pct", "nominal_trend_pct_yr",
                                                     "real_trend_pct_yr", "volatility_pct", "years"]]
                 .rename(columns={"crop": "Culture", "last_year": "Année", "price_dt_kg": "Prix production DT/kg",
                                  "yoy_pct": "Sur un an (%)", "nominal_trend_pct_yr": "Tendance courante (%/an)",
                                  "real_trend_pct_yr": "Tendance réelle (%/an)", "volatility_pct": "Instabilité (%)",
                                  "years": "Période"}),
                 hide_index=True, use_container_width=True,
                 column_config={c: st.column_config.NumberColumn(format="%.1f") for c in
                                ["Sur un an (%)", "Tendance courante (%/an)", "Tendance réelle (%/an)", "Instabilité (%)"]}
                 | {"Prix production DT/kg": st.column_config.NumberColumn(format="%.2f")})
    st.caption("Tendance réelle : prix corrigé de l'inflation (indice des prix à la consommation). Instabilité : écart type des variations annuelles.")


# ================================================================== Page 2
def page_crop() -> None:
    d = data()
    st.title("Fiche culture")
    have = set(d.arrivals.crop_id.dropna()) | set(d.veg.crop_id) | set(d.retail.crop_id) | set(d.faostat.crop_id)
    ids = [c.id for c in C.CROPS if c.id in have]
    cid = st.selectbox("Culture", ids, format_func=lambda c: f"{C.BY_ID[c].fr} · {C.BY_ID[c].ar} · {C.BY_ID[c].en}")
    crop = C.BY_ID[cid]
    st.markdown(f"### {crop.fr} <span class='badge'>{'légume' if crop.category == 'vegetable' else 'fruit'}</span> "
                f"<span class='badge'>{'pérenne' if crop.perennial else 'annuelle'}</span>", unsafe_allow_html=True)
    st.caption(f"{crop.ar} · {crop.en} · *{crop.scientific}*")
    for n in crop.notes:
        st.info(n)
    nat_id = cid if cid in set(d.veg.crop_id) else (crop.group if crop.group in set(d.veg.crop_id) else None)
    st.subheader("Production nationale")
    if nat_id:
        if nat_id != cid:
            st.info(f"Le ministère publie seulement le groupe « {K.name_fr(nat_id)} ».")
        v = d.veg[d.veg.crop_id == nat_id]
        c1, c2, c3 = st.columns(3)
        for col, y, lab in ((c1, "production_t", "Production (t)"), (c2, "area_ha", "Superficie (ha)"), (c3, "yield_t_ha", "Rendement (t/ha)")):
            fig = px.bar(v, x="year", y=y, labels={"year": "", y: lab}, color_discrete_sequence=[GREEN])
            col.plotly_chart(style(fig, 260), use_container_width=True)
        src(MOA_SRC + " Superficie publiée en milliers d'ha (étiquetée « ha » dans le fichier source).")
        pp = v.dropna(subset=["producer_price_dt_t"]).copy()
        pp["Courant"] = pp.producer_price_dt_t / 1000
        pp[f"Constant {int(d.cpi.year.max())}"] = K.deflate(pp.producer_price_dt_t, pp.year, d.cpi) / 1000
        fig = px.line(pp.melt("year", ["Courant", f"Constant {int(d.cpi.year.max())}"]), x="year", y="value", color="variable",
                      markers=True, labels={"year": "", "value": "DT / kg"}, title="Prix à la production")
        st.plotly_chart(style(fig, 320), use_container_width=True)
        src(MOA_SRC + " Dinars constants : corrigé avec l'indice des prix à la consommation (Banque mondiale).")
    else:
        f = d.faostat[d.faostat.crop_id == cid]
        if len(f):
            st.warning("Pas de série nationale du ministère pour cette culture : données FAOSTAT, avec leur statut "
                       "(officielle, estimée par la FAO, imputée).")
            fig = px.scatter(f[f.element.isin(["production_t", "yield_t_ha", "producer_price_dt_t"])], x="year", y="value",
                             color="flag_meaning", facet_row="element", height=600,
                             labels={"year": "", "value": "", "flag_meaning": "Statut"})
            fig.update_yaxes(matches=None)
            st.plotly_chart(style(fig, 600), use_container_width=True)
            src("FAOSTAT (QCL, PP), Tunisie. Unités : t, t/ha, DT/t.")
        nf = d.fruits[d.fruits.crop_id == cid]
        if len(nf):
            fig = px.bar(nf, x="year", y="production_t", labels={"year": "", "production_t": "tonnes"},
                         color_discrete_sequence=[GREEN], title="Production nationale (ministère)")
            st.plotly_chart(style(fig, 280), use_container_width=True)
            src("Ministère de l'Agriculture (data.gov.tn), séries fruitières nationales, milliers de tonnes convertis en tonnes.")
        if not len(f) and not len(nf):
            st.info("Aucune donnée de production nationale disponible pour cette culture.")

    arr = d.arrivals[d.arrivals.crop_id == cid].copy()
    if len(arr):
        st.subheader("Marché de gros de Tunis")
        arr["tonnes"] = arr.arrivals_t.where(arr.status != "no_arrivals", 0)
        a1, a2 = st.columns([2, 1])
        fig = px.bar(arr, x="date", y="tonnes", labels={"date": "", "tonnes": "tonnes / mois"}, color_discrete_sequence=[GREEN],
                     title="Apports mensuels")
        a1.plotly_chart(style(fig, 300), use_container_width=True)
        sea = K.seasonality(d.arrivals, cid)
        fig = px.bar(sea, x="month_name", y="avg_t", labels={"month_name": "", "avg_t": "t / mois (moyenne)"},
                     color_discrete_sequence=["#66BB6A"], title="Saisonnalité")
        a2.plotly_chart(style(fig, 300), use_container_width=True)
        src(ARR_SRC)
    ret = d.retail[d.retail.crop_id == cid]
    sb = d.sidi_bouzid[d.sidi_bouzid.crop_id == cid]
    if len(ret) or len(sb):
        st.subheader("Prix sur les marchés")
        fig = go.Figure()
        if len(ret):
            fig.add_scatter(x=ret.date, y=ret.retail_price_dt_kg, name="Détail, Tunis (INS, mensuel)", line=dict(color=DARK))
        if len(sb):
            m = sb.set_index("date").resample("MS")[["wholesale_min_dt_kg", "wholesale_max_dt_kg", "retail_min_dt_kg",
                                                       "retail_max_dt_kg"]].mean().dropna(how="all")
            fig.add_scatter(x=m.index, y=(m.wholesale_min_dt_kg + m.wholesale_max_dt_kg) / 2,
                            name="Gros, Sidi Bouzid (moyenne min-max)", line=dict(color="#66BB6A"))
            fig.add_scatter(x=m.index, y=(m.retail_min_dt_kg + m.retail_max_dt_kg) / 2,
                            name="Détail, Sidi Bouzid (moyenne min-max)", line=dict(color="#A5D6A7", dash="dot"))
        fig.update_layout(yaxis_title="DT / kg")
        st.plotly_chart(style(fig, 340), use_container_width=True)
        src("INS (détail Tunis) ; CRDA Sidi Bouzid via data.gov.tn (gros et détail, 2018-2022, millimes/kg déduits des valeurs). "
            "Prix de gros et de détail affichés séparément, jamais additionnés.")
    if nat_id and len(ret):
        gap = K.price_gap(d.veg, d.retail, nat_id, cid)
        if len(gap):
            st.markdown("**Écart entre prix de détail à Tunis et prix national à la production**")
            fig = px.bar(gap.melt("year", ["producer_dt_kg", "retail_dt_kg"]), x="year", y="value", color="variable", barmode="group",
                         labels={"year": "", "value": "DT / kg"})
            fig.for_each_trace(lambda t: t.update(name={"producer_dt_kg": "Production (national)", "retail_dt_kg": "Détail (Tunis)"}[t.name]))
            st.plotly_chart(style(fig, 280), use_container_width=True)
            st.caption("Différence entre deux niveaux de prix mesurés à des endroits différents : ce n'est ni le bénéfice "
                       "de l'agriculteur ni la marge des commerçants (transport, pertes, gros et détail inclus).")
    if crop.fao56:
        st.subheader("Besoin en eau selon la région")
        pm = st.select_slider("Mois de semis / plantation", list(range(1, 13)), value=A.default_planting_month(crop.fao56) or 3,
                              format_func=lambda m: K.MONTHS_FR[m - 1])
        rows = []
        for gov, g in d.climate.groupby("governorate"):
            w = A.water_need(crop.fao56, g, pm, A.IRRIGATION_EFFICIENCY["drip"])
            if w:
                rows.append({"Gouvernorat": gov, "m³/ha": w.gross_m3_ha, "mm": w.net_irrigation_mm})
        if rows:
            wdf = pd.DataFrame(rows).sort_values("m³/ha")
            fig = px.bar(wdf, x="Gouvernorat", y="m³/ha", color_discrete_sequence=[GREEN])
            st.plotly_chart(style(fig, 320), use_container_width=True)
            src("Calcul FAO-56 (coefficients culturaux) avec le climat moyen NASA POWER de chaque chef-lieu, "
                "pluie efficace USDA-SCS, goutte-à-goutte (efficience 90 %). Ordre de grandeur, pas une mesure.")
        else:
            st.info("Durées de cycle FAO-56 non disponibles pour cette culture : besoin en eau non calculé.")


# ================================================================== Page 3
def page_advisor() -> None:
    d = data()
    st.title("Conseiller d'investissement")
    st.caption("Comparer des cultures avec les données officielles disponibles. Ce n'est pas une prédiction de bénéfice.")
    govs = sorted(d.climate.governorate.unique())
    with st.form("farm"):
        st.subheader("Votre exploitation")
        c1, c2, c3 = st.columns(3)
        gov = c1.selectbox("Gouvernorat", govs, index=govs.index("Nabeul") if "Nabeul" in govs else 0)
        area = c2.number_input("Surface cultivée (ha)", 0.1, 500.0, 2.0, 0.1)
        budget = c3.number_input("Budget disponible (DT)", 0.0, 10_000_000.0, 50_000.0, 1000.0)
        c4, c5, c6 = st.columns(3)
        water = c4.radio("Disponibilité en eau", ["limited", "moderate", "abundant"], index=1, horizontal=True,
                         format_func={"limited": "Limitée", "moderate": "Moyenne", "abundant": "Abondante"}.get)
        m3 = c5.number_input("Eau disponible pour la saison (m³, facultatif)", 0.0, 10_000_000.0, 0.0, 500.0)
        irr = c6.selectbox("Irrigation", ["drip", "sprinkler", "surface"],
                           format_func={"drip": "Goutte-à-goutte", "sprinkler": "Aspersion", "surface": "Gravitaire"}.get)
        c7, c8 = st.columns([1, 3])
        cat = c7.selectbox("Catégorie", [None, "vegetable", "fruit"], format_func={None: "Toutes", "vegetable": "Légumes",
                                                                                     "fruit": "Fruits"}.get)
        cands = c8.multiselect("Cultures à comparer (vide = toutes)", A.ADVISABLE, format_func=K.name_fr)
        with st.expander("Coûts de production par hectare (vos chiffres)"):
            st.caption("Aucune source officielle ne publie ces coûts par culture : ils viennent de vous. "
                       "Le coût de l'eau est calculé automatiquement. Laissez 0 si vous ne savez pas.")
            tariff_def, tariff_note = A.default_tariff(d)
            t1, t2 = st.columns(2)
            tariff = t1.number_input("Prix de l'eau (DT/m³)", 0.0, 5.0, round(tariff_def, 3), 0.005, format="%.3f",
                                     help=f"Par défaut : {tariff_note}.")
            smag = float(d.smag.sort_values("year").smag_dt_day.iloc[-1])
            t2.markdown(f"SMAG officiel (salaire minimum agricole) : **{smag:.3f} DT/jour** (INS). "
                        "Main-d'œuvre = jours/ha × salaire.")
            base = [c for c in (cands or A.ADVISABLE) if A.evidence(d, c).level != "insufficient"
                    and (cat is None or C.BY_ID[c].category == cat)]
            cost_df = pd.DataFrame({"Culture": [K.name_fr(c) for c in base], "crop_id": base,
                                    **{k: 0.0 for k in ["Semences", "Engrais", "Traitements", "Jours de travail/ha", "Énergie",
                                                        "Matériel", "Autres"]}})
            edited = st.data_editor(cost_df, hide_index=True, disabled=["Culture"], column_config={"crop_id": None},
                                    use_container_width=True, key="costs")
        with st.expander("Mois de semis et pondérations"):
            pms = {}
            cols = st.columns(4)
            for i, c in enumerate(base):
                f = C.BY_ID[c].fao56
                if f and A.default_planting_month(f):
                    pms[c] = cols[i % 4].selectbox(K.name_fr(c), list(range(1, 13)), index=A.default_planting_month(f) - 1,
                                                    format_func=lambda m: K.MONTHS_FR[m - 1], key=f"pm_{c}")
            st.caption("Mois par défaut : exemple méditerranéen de la FAO-56, pas un calendrier tunisien. Adaptez-le.")
            w1, w2, w3, w4 = st.columns(4)
            wm = w1.slider("Marché", 0, 100, 30)
            wp = w2.slider("Productivité", 0, 100, 25)
            wr = w3.slider("Rentabilité", 0, 100, 25)
            ww = w4.slider("Eau", 0, 100, 20)
            st.caption("Pondérations initiales = choix de conception (30/25/25/20), non validées scientifiquement.")
        go_ = st.form_submit_button("Comparer les cultures", type="primary")
    if not go_ and "advice" not in st.session_state:
        st.info("Remplissez le formulaire puis cliquez sur « Comparer les cultures ».")
        return
    costs = {}
    for _, r in edited.iterrows():
        costs[r.crop_id] = {"seeds": r["Semences"], "fertilisers": r["Engrais"], "pesticides": r["Traitements"],
                            "labour": r["Jours de travail/ha"] * smag, "energy": r["Énergie"], "equipment": r["Matériel"],
                            "other": r["Autres"]}
    total_w = max(wm + wp + wr + ww, 1)
    fi = A.FarmerInput(governorate=gov, area_ha=area, budget_dt=budget or None, water=water,
                       water_available_m3=m3 or None, irrigation=irr, category=cat, candidates=cands or None,
                       costs_per_ha=costs, planting_month=pms, water_tariff_dt_m3=tariff,
                       weights={"market": wm / total_w, "productivity": wp / total_w, "profitability": wr / total_w,
                                "water": ww / total_w})
    table, results = A.recommend(d, fi)
    st.session_state["advice"] = True
    if table.empty:
        st.error("Preuves insuffisantes pour toutes les cultures choisies : aucune recommandation n'est produite.")
    else:
        st.subheader("Classement")
        st.caption("Scores relatifs (0 = la plus faible de la liste, 100 = la plus forte). Ajouter ou retirer une culture change les scores.")
        sc = table.melt(["Culture"], ["Marché", "Productivité", "Rentabilité", "Eau"], var_name="Critère", value_name="Score critère")
        weights = fi.weights | {"water": fi.weights["water"] * A.WATER_WEIGHT_FACTOR[water]}
        wmap = {"Marché": weights["market"], "Productivité": weights["productivity"], "Rentabilité": weights["profitability"],
                "Eau": weights["water"]}
        sc["Contribution"] = sc.apply(lambda r: r["Score critère"] * wmap[r["Critère"]] / sum(wmap.values()), axis=1)
        fig = px.bar(sc, y="Culture", x="Contribution", color="Critère", orientation="h",
                     category_orders={"Culture": table.Culture.tolist()},
                     color_discrete_sequence=[DARK, GREEN, "#66BB6A", "#A5D6A7"], labels={"Contribution": "Score global"})
        st.plotly_chart(style(fig, 80 + 45 * len(table)), use_container_width=True)
        show = table.drop(columns=["crop_id"])
        st.dataframe(show, use_container_width=True, column_config={
            c: st.column_config.NumberColumn(format="%.0f") for c in ["Score", "Marché", "Productivité", "Rentabilité", "Eau",
                                                                      "Revenu attendu (DT/ha)", "Eau (m³/ha)"]})
        st.caption("Preuves A = séries officielles nationales du ministère de l'Agriculture (rendement et prix à la production).")
        st.subheader("Détail par culture")
        for r in sorted([x for x in results if x["status"] == "OK"], key=lambda x: x["rank"]):
            with st.expander(f"{r['rank']}. {r['crop']} – score {r['score']:.0f}/100", expanded=r["rank"] == 1):
                st.markdown(r["why"])
                k1, k2, k3, k4 = st.columns(4)
                card(k1, "Rendement attendu", f"{r['yield_t_ha']:.1f} t/ha", "médiane nationale, 5 dernières années")
                card(k2, "Prix attendu", f"{r['price_dt_kg']:.2f} DT/kg", f"prix à la production, DT constants {int(d.cpi.year.max())}")
                card(k3, "Besoin en eau", f"{r['water']['gross_m3_ha']:,.0f} m³/ha".replace(",", " ") if r["water"] else "n.d.",
                     f"{r['water']['season_days']} jours de culture" if r["water"] else "données FAO-56 manquantes")
                card(k4, "Coût saisi + eau", f"{r['cost_ha']:,.0f} DT/ha".replace(",", " "),
                     "vos coûts + eau calculée" if r["costs_entered"] else "eau seulement (coûts non saisis)")
                sc_rows = []
                for s, lab in (("pessimistic", "Pessimiste"), ("expected", "Attendu"), ("optimistic", "Optimiste")):
                    v = r["scenarios"][s]
                    sc_rows.append({"Scénario": lab, "Revenu (DT)": v["revenue"], "Coûts (DT)": v["cost"],
                                    "Bénéfice (DT)": v["profit"], "Bénéfice / ha (DT)": v["profit_ha"]})
                sdf = pd.DataFrame(sc_rows)
                fig = px.bar(sdf.melt("Scénario", ["Revenu (DT)", "Coûts (DT)"] + (["Bénéfice (DT)"] if r["costs_entered"] else [])),
                             x="Scénario", y="value", color="variable", barmode="group",
                             color_discrete_sequence=[GREEN, "#B0BEC5", DARK], labels={"value": f"DT pour {area:g} ha", "Scénario": ""})
                st.plotly_chart(style(fig, 280), use_container_width=True)
                st.dataframe(sdf, hide_index=True, use_container_width=True,
                             column_config={c: st.column_config.NumberColumn(format="%.0f") for c in sdf.columns[1:]})
                if not r["costs_entered"]:
                    st.warning("Bénéfice non calculé : saisissez vos coûts de production. Le revenu affiché est un revenu brut.")
                a, b = st.columns(2)
                a.markdown("**Risques**\n" + ("\n".join(f"- {x}" for x in r["risks"]) or "- Aucun risque particulier détecté dans les données."))
                a.markdown("**Données utilisées**\n" + "\n".join(f"- {x}" for x in r["sources"]) + f"\n- Période : {r['years']} ({r['n_years']} ans)")
                b.markdown("**Hypothèses**\n" + "\n".join(f"- {x}" for x in r["assumptions"]))
                b.markdown("**Informations manquantes**\n" + ("\n".join(f"- {x}" for x in r["missing"]) or "- aucune"))
        st.markdown("**La recommandation peut changer si :**\n" + "\n".join(f"- {x}" for x in A.CHANGE_CONDITIONS))
    ins = [r for r in results if r["status"] != "OK"]
    if ins:
        st.subheader("Preuves insuffisantes")
        st.dataframe(pd.DataFrame([{"Culture": r["crop"], "Raison": r["reason"]} for r in ins]), hide_index=True,
                     use_container_width=True)


# ================================================================== Page 4
def page_sources() -> None:
    d = data()
    st.title("Sources et fiabilité")
    s = sources()
    rows = [{"Jeu de données": v.get("title"), "Éditeur": v.get("publisher"), "Couverture": v.get("geography"),
             "Unités": v.get("units"), "Niveau": v.get("level"), "Téléchargé le": str(v.get("retrieved_at", ""))[:10],
             "Mis à jour (source)": str(v.get("resource_modified", ""))[:10], "Lien": v.get("landing_page") or v.get("url")}
            for k, v in s.items()]
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True,
                 column_config={"Lien": st.column_config.LinkColumn()})
    q = quality()
    st.subheader("Couverture des données")
    cov = []
    for name, t in q["tables"].items():
        cov.append({"Table": name, "Lignes": t["records"], "Années": "–".join(map(str, t.get("years", []))) or
                    "–".join(t.get("dates", [])), "Cultures": len(t.get("crops", [])), "Doublons": t["duplicates"],
                    "Valeurs manquantes": ", ".join(f"{k} {v}%" for k, v in t["missing_pct"].items()) or "aucune"})
    st.dataframe(pd.DataFrame(cov), hide_index=True, use_container_width=True)
    st.subheader("Fraîcheur des apports au marché de gros de Tunis")
    sc = K.season_coverage(d.arrivals)
    st.dataframe(sc.assign(missing_months=sc.missing_months.map(", ".join)).rename(columns={
        "season": "Campagne", "months_reported": "Mois publiés", "months_in_data": "Mois dans les bulletins",
        "missing_months": "Mois manquants", "complete": "Complète"}), hide_index=True, use_container_width=True)
    st.subheader("Contrôles de qualité")
    iss = pd.DataFrame(q["issues"])
    sev = st.multiselect("Niveau", ["error", "warning", "info"], default=["error", "warning", "info"])
    st.dataframe(iss[iss.severity.isin(sev)].rename(columns={"dataset": "Source", "severity": "Niveau", "message": "Constat"}),
                 hide_index=True, use_container_width=True)
    st.subheader("Méthode")
    st.markdown((ROOT / "reports" / "methodology_fr.md").read_text(encoding="utf-8"))


pg = st.navigation([st.Page(page_market, title="Vue du marché", icon="📊", default=True),
                    st.Page(page_crop, title="Fiche culture", icon="🌿", url_path="culture"),
                    st.Page(page_advisor, title="Conseiller d'investissement", icon="💡", url_path="conseiller"),
                    st.Page(page_sources, title="Sources et fiabilité", icon="📚", url_path="sources")])
with st.sidebar:
    st.markdown("## 🌱 FARMLINK")
    st.markdown("Agricultural Market Intelligence & Investment Advisor")
    st.caption("Données officielles tunisiennes · aucune valeur inventée")
pg.run()
