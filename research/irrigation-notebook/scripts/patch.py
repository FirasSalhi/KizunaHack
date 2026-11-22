"""Apply the fixes to the FARMLINK notebook. Usage: python -I patch.py in.ipynb out.ipynb"""
import json, sys

src_path, dst_path = sys.argv[1], sys.argv[2]
nb = json.load(open(src_path, encoding="utf-8"))
cells = nb["cells"]
LOG = []


def get(i):
    return "".join(cells[i]["source"])


def put(i, text):
    cells[i]["source"] = text.splitlines(keepends=True)


def rep(i, old, new, count=1, tag=""):
    s = get(i)
    n = s.count(old)
    assert n >= 1, f"cell {i}: pattern not found: {old[:80]!r}"
    if count == 1:
        assert n == 1, f"cell {i}: pattern found {n} times: {old[:80]!r}"
    put(i, s.replace(old, new))
    LOG.append(f"cell {i}: {tag or old[:60]!r}")


# ---------------------------------------------------------------- FIX 1: TLS
# Cell 3: stop silencing certificate warnings.
rep(3, """    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
""", "", tag="FIX1 remove InsecureRequestWarning suppression")

# Cell 6: build a CA bundle that adds the intermediate certificate catalog.data.gov.tn forgets to send.
TLS_BLOCK = '''
# ---- FIX (TLS): catalog.data.gov.tn does not send its intermediate certificate, so a verified HTTPS
# request fails with CERTIFICATE_VERIFY_FAILED. Instead of disabling verification (verify=False), we fetch
# the missing intermediate from the URL published in the server certificate (AIA extension) and add it to
# certifi's roots. The chain is still fully verified against a trusted root: a forged intermediate would fail.
import ssl, certifi
def _build_ca_bundle(host='catalog.data.gov.tn'):
    aia_url = 'http://crt.sectigo.com/SectigoPublicServerAuthenticationCADVR36.crt'   # value read from the server certificate
    try:
        from cryptography import x509
        from cryptography.x509.oid import ExtensionOID, AuthorityInformationAccessOID
        leaf = x509.load_pem_x509_certificate(ssl.get_server_certificate((host, 443), timeout=15).encode())
        for d in leaf.extensions.get_extension_for_oid(ExtensionOID.AUTHORITY_INFORMATION_ACCESS).value:
            if d.access_method == AuthorityInformationAccessOID.CA_ISSUERS:
                aia_url = d.access_location.value
    except Exception as e:
        print(f"  (AIA lookup skipped: {type(e).__name__}; using known issuer URL)")
    der = requests.get(aia_url, timeout=20).content
    pem = ssl.DER_cert_to_PEM_cert(der) if not der.lstrip().startswith(b'-----') else der.decode()
    bundle = BASE_DIR / 'ca_bundle_with_intermediate.pem'
    bundle.write_text(Path(certifi.where()).read_text() + '\\n' + pem)
    return bundle
TLS_VERIFIED = False
try:
    _bundle = _build_ca_bundle()
    os.environ['REQUESTS_CA_BUNDLE'] = str(_bundle)      # used by every requests call with verify=True
    requests.get('https://catalog.data.gov.tn/api/3/action/status_show', timeout=20)
    TLS_VERIFIED = True
    print(f"🔒 TLS verification ON for catalog.data.gov.tn (bundle: {_bundle.name})")
except Exception as e:
    print(f"⚠️ Could not build a verified TLS chain for catalog.data.gov.tn: {type(e).__name__}: {str(e)[:160]}")
    print("   DGACTA downloads will fail (verification is never disabled). Attach cached CSVs to DATA_DIR instead.")

def _probe(url):'''
rep(6, "\ndef _probe(url):", TLS_BLOCK, tag="FIX1 verified TLS bundle for data.gov.tn")

# Cell 8 & 18: verification back on.
rep(8, "requests.get(url, timeout=25, verify=False)", "requests.get(url, timeout=25)", tag="FIX1 verify ON (package_show)")
rep(8, "requests.get(rurl, timeout=35, verify=False)", "requests.get(rurl, timeout=35)", tag="FIX1 verify ON (resources)")
rep(18, "requests.get(url, timeout=30, verify=False)", "requests.get(url, timeout=30)", tag="FIX1 verify ON (NASA POWER)")

# Cell 18: NASA window follows the sensor period instead of hard-coded dates.
rep(18, "    datetime(2026, 11, 1), datetime(2026, 11, 21),",
    "    (cm_piv.index.min().normalize() - pd.Timedelta(days=12)).to_pydatetime(), cm_piv.index.max().normalize().to_pydatetime(),",
    tag="FIX dynamic NASA date window")

# Cell 10: provenance must reflect what this run actually did.
rep(10, """    DATA_PROVENANCE = 'REAL_DGACTA'
elif ALLOW_FIXTURE:""", """    DATA_PROVENANCE = 'REAL_DGACTA'
    _n_fail = int((ACQ_DF['status'] == 'PACKAGE_FAILED').sum()) if len(ACQ_DF) else 0
    if _n_fail:
        DATA_PROVENANCE = 'REAL_DGACTA_FROM_EARLIER_DOWNLOAD'
        print(f"\\n⚠️ {_n_fail} station package(s) could not be read in this run; the CSVs used were downloaded earlier "
              f"(section 3 loop or cache). Errors:")
        print(ACQ_DF.loc[ACQ_DF['status'] == 'PACKAGE_FAILED', ['station', 'error']].to_string(index=False))
    print(f"TLS verified for DGACTA: {TLS_VERIFIED}")
elif ALLOW_FIXTURE:""", tag="FIX1 honest DATA_PROVENANCE")

# ---------------------------------------------------------------- FIX 2: duplicates in the parser
rep(12, """    csv_files = sorted(list(data_dir.glob("*.csv")))
""", """    csv_files = sorted(list(data_dir.glob("*.csv")))
    # FIX: only parse files listed in the manifest (stale copies with other names in /kaggle/working were parsed twice)
    if manifest_df is not None and len(manifest_df) > 0 and 'local_file' in manifest_df.columns:
        listed = set(manifest_df['local_file'].dropna().astype(str))
        skipped = [f.name for f in csv_files if f.name not in listed]
        csv_files = [f for f in csv_files if f.name in listed]
        if skipped:
            print(f"ℹ️ {len(skipped)} CSV file(s) in DATA_DIR are not in the manifest and are ignored (stale/duplicate copies).")
""", tag="FIX2 parse manifest-listed files only")
rep(12, "df_sm_corrected = df_classified[df_classified['domain'] == 'soil_moisture_probe'].copy()",
    """_n0 = len(df_classified)
df_classified = df_classified.drop_duplicates(subset=[c for c in ['station', 'sensor_depth_cm', 'measurement_type', 'timestamp', 'valeur'] if c in df_classified.columns])
if len(df_classified) < _n0:
    print(f"ℹ️ Removed {_n0 - len(df_classified):,} exact duplicate records (same station/depth/channel/time/value).")
df_sm_corrected = df_classified[df_classified['domain'] == 'soil_moisture_probe'].copy()""",
    tag="FIX2 drop exact duplicate records")

# ---------------------------------------------------------------- FIX 3: fresh weather for ETo
rep(46, """    wx = standardize_nasa_power(nasa_weather_df)
""", """    # FIX: prefer the engine weather (Open-Meteo, complete up to the sensor date -> Penman-Monteith every day) over
    # NASA POWER, whose last 2-3 days are -999 (latency) and forced a stale Hargreaves ETo onto the recommendations.
    if WEATHER_SOURCE in ('open_meteo', 'nasa_power') and len(WEATHER_FARM):
        _m = {'tmean': 'nasa_tmean_C', 'tmax': 'nasa_tmax_C', 'tmin': 'nasa_tmin_C', 'rh_mean': 'nasa_rh2m_pct', 'u2': 'nasa_wind_ms', 'rs': 'nasa_solar_MJ', 'rain_mm': 'nasa_precip_mm'}
        _w0 = cm_piv.index.min().normalize() - pd.Timedelta(days=12)
        _wf = WEATHER_FARM[pd.to_datetime(WEATHER_FARM['date']) >= _w0]
        weather_input = _wf[['date'] + list(_m)].rename(columns=_m).assign(provenance=f'{WEATHER_SOURCE}_daily')
        print(f"Weather for ETo: engine source '{WEATHER_SOURCE}' ({len(weather_input)} days, up to {pd.to_datetime(weather_input['date']).max().date()})")
    else:
        weather_input = nasa_weather_df
        print("Weather for ETo: NASA POWER (cell 6.2)")
    wx = standardize_nasa_power(weather_input)
""", tag="FIX3 use Open-Meteo weather for ETo")
for i in range(len(cells)):
    if cells[i]["cell_type"] == "code" and "A_real_NASA_POWER_weather" in get(i):
        rep(i, "A_real_NASA_POWER_weather", "A_real_weather", count=0, tag="FIX3 rename scenario A")
rep(53, "f\"Weather: NASA POWER reanalysis, last valid day {last_valid_date.date()}.",
    "f\"Weather: {weather_source}, last valid day {last_valid_date.date()}.", tag="FIX3 dashboard note")

# ---------------------------------------------------------------- FIX 4: sensor below WP lowers confidence
rep(38, """        for lay in prof["layers"]:
            if lay["theta"] < soil.wp:
                warnings.append(""", """        for lay in prof["layers"]:
            if lay["theta"] < soil.wp:
                layers_below_wp.append(lay["sensor_cm"])
                warnings.append(""", tag="FIX4 record layers below WP")
rep(38, """    if depletion_mm_override is not None:
        if not (0 <= depletion_mm_override <= taw):""", """    layers_below_wp = []
    if depletion_mm_override is not None:
        if not (0 <= depletion_mm_override <= taw):""", tag="FIX4 init list")
rep(38, """    if reasons:
        readiness, conf = "ILLUSTRATIVE", "LOW\"""", """    if layers_below_wp:
        reasons.append(f"sensor layer(s) at {layers_below_wp} cm read below the declared WP (sensor/soil conflict)")
    if reasons:
        readiness, conf = "ILLUSTRATIVE", ("VERY_LOW" if layers_below_wp else "LOW")""", tag="FIX4 VERY_LOW confidence")
rep(38, """    res.update(status="OK", readiness=readiness, confidence=conf,""",
    """    if layers_below_wp:
        expl.append(f"CAUTION: sensor layer(s) at {layers_below_wp} cm read below the declared wilting point; "
                    "the volume above depends on a soil description the sensors contradict. Verify FC/WP on site before irrigating.")
    res["sensor_soil_conflict_layers_cm"] = layers_below_wp
    res.update(status="OK", readiness=readiness, confidence=conf,""", tag="FIX4 explanation")

# ---------------------------------------------------------------- FIX 5: meaningful water-allocation example
rep(58, "available_water_m3=20.0)", "available_water_m3=AVAILABLE_WATER_M3)", tag="FIX5 allocation volume variable")
rep(58, "_fc = FORECAST_FARM\n", "_fc = FORECAST_FARM\nAVAILABLE_WATER_M3 = 1500.0   # DEMO: roughly half of the farm's gross need, so the allocation rule is visible\n",
    tag="FIX5 1500 m3")
rep(62, """print(f"Available {A['available_m3']} m3""", """_need = sum(p['full_need_gross_m3'] for p in A['plan'])
print(f"Total gross need of computable zones: {_need:,.0f} m3 -> available water covers {100*A['available_m3']/_need:.0f} %" if _need else "No zone needs water.")
print(f"Available {A['available_m3']} m3""", tag="FIX5 print coverage")
put(61, get(61).replace("## 12K. 💧 Limited-water example: 20 m³ for the zones that have complete inputs",
                        "## 12K. 💧 Limited-water example: 1 500 m³ (≈ half of the need) for the zones that have complete inputs"))
LOG.append("cell 61: FIX5 title")

# ---------------------------------------------------------------- FIX 6: predictor explanation
rep(64, """print("\\nRule:", next(iter(PRED_RESULTS.values()))['selection_rule'])""",
    """print("\\nRule:", next(iter(PRED_RESULTS.values()))['selection_rule'])
_h = next(iter(PRED_RESULTS.values()))
print(f"Why fewer rows than section 7 ({len(ml_dataset)} rows): this predictor uses lags up to 24 h (needs 24 previous gap-free hours) "
      f"and the hourly grid has {_h['n_missing_hours']} missing hour(s) out of {_h['n_hours_total']}; it requires >= 200 rows, "
      "i.e. about 10 days of continuous data. With the current series persistence remains the answer.")""",
    tag="FIX6 explain INSUFFICIENT_DATA")

# ---------------------------------------------------------------- FIX 7: stale numbers in markdown
rep(14, "with **170 continuous hourly readings per depth** ($10\\text{ cm}, 30\\text{ cm}, 60\\text{ cm}$) from November 13 to November 21, 2026.",
    "with **continuous hourly readings per depth** ($10\\text{ cm}, 30\\text{ cm}, 60\\text{ cm}$); the exact count and period are printed in section 6.1 (they grow with every new download).",
    tag="FIX7 EDA text")
rep(14, "- The vertical soil profile reveals consistent physical stratification:",
    "- The vertical soil profile reveals consistent physical stratification (ranges below are from the first analysed download):", tag="FIX7 EDA ranges")
rep(23, "First 70% train ($107\\text{ hours}$), last 30% holdout test ($47\\text{ hours} \\approx 2.0\\text{ days}$).",
    "First 70% train, last 30% holdout test (sample counts and dates are printed by the cell below).", tag="FIX7 split text")
rep(45, "NASA POWER provides", "The engine weather (Open-Meteo, NASA POWER as fallback) provides", tag="FIX7 12C text")
rep(47, "real NASA POWER weather of the notebook period", "real weather (engine source: Open-Meteo or NASA POWER) of the notebook period", tag="FIX7 12D text")
rep(69, "Our parser successfully decoupled 2,302 physical observations across the 5 DGACTA stations,",
    "Our parser decoupled the physical observations of the 5 DGACTA stations (count printed in section 4.1, duplicates removed),", tag="FIX7 conclusions count")
rep(69, "On the continuous 170-hour series at Chott Meriam, **Persistence Baseline is the clear winner** ($\\text{MAE} = 0.0191\\%$, $R^2 = 0.9902$).",
    "On the continuous hourly series at Chott Meriam, **Persistence Baseline is the clear winner** (MAE and $R^2$ printed in section 8; Random Forest and HistGradientBoosting have negative $R^2$ on the holdout).",
    tag="FIX7 conclusions metrics")


# ---------------------------------------------------------------- FIX 8: weather must not hang on HTTP 429
rep(20, "WEATHER_PROV, WEATHER_SOURCE, FORECAST_FARM = None, None, None\n", """WEATHER_PROV, WEATHER_SOURCE, FORECAST_FARM = None, None, None
# FIX: the engine session retries HTTP 429 and honours Retry-After; Open-Meteo answers 429 'daily limit exceeded'
# with a Retry-After of hours, which froze this cell. This session does not retry 429, so the NASA POWER
# fallback is used immediately (and recorded in WEATHER_PROV).
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
wsess = requests.Session()
_wr = Retry(total=2, connect=2, read=2, status=2, backoff_factor=1.0, allowed_methods=("GET",), status_forcelist=(500, 502, 503, 504), respect_retry_after_header=False)
wsess.mount("https://", HTTPAdapter(max_retries=_wr)); wsess.mount("http://", HTTPAdapter(max_retries=_wr))
wsess.headers["User-Agent"] = "FARMLINK-Module5/2.0"
""", tag="FIX8 weather session without 429 retry")
rep(20, "str(_end), sess, order=", "str(_end), wsess, order=", tag="FIX8 use wsess (archive)")
rep(20, "str(_end), str(_end), sess, forecast=True)", "str(_end), str(_end), wsess, forecast=True)", tag="FIX8 use wsess (forecast)")

# header note
cells.insert(1, {"cell_type": "markdown", "metadata": {}, "source": [
    "> ### 🛠️ v3.1 – corrections\n",
    "> 1. **TLS**: `verify=False` removed. The missing intermediate certificate of `catalog.data.gov.tn` is added to a CA bundle, so downloads are verified.\n",
    "> 2. **Duplicates**: the parser reads only files listed in the manifest and drops exact duplicate records.\n",
    "> 3. **Weather**: ETo uses the up-to-date engine weather (Open-Meteo, Penman–Monteith) instead of 3-day-old NASA POWER + Hargreaves.\n",
    "> 4. **Sensor/soil conflict**: a sensor layer below the declared wilting point lowers confidence to `VERY_LOW` with an explicit caution.\n",
    "> 5. **Water allocation**: realistic example (1 500 m³ ≈ half of the need) instead of 20 m³.\n",
    "> 6. **Provenance & texts**: honest `DATA_PROVENANCE`, explanation of `INSUFFICIENT_DATA`, stale numbers removed from the markdown.\n",
    "> 7. **Weather timeout**: an HTTP 429 (Open-Meteo daily quota) no longer freezes the notebook for hours; the NASA POWER fallback is used and recorded.\n"]})

json.dump(nb, open(dst_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
sys.stdout.reconfigure(encoding="utf-8")
print("\n".join(LOG)); print(f"OK -> {dst_path} ({len(LOG)} edits)")
