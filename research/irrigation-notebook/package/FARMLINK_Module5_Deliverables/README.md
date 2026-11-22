# FARMLINK Module 5 — crop-aware irrigation intelligence package

Notebook-independent Python package (standard scientific stack only) that answers, per farm zone: **what** to irrigate, **when**, and **how much** (mm, m³, litres), ranks zones farm-wide, and splits a limited water budget. It is built from the Kaggle notebook `tunisian_crop_monitoring_final_v3.ipynb`.

> **Status in one paragraph.** All 81+ unit tests pass and the end-to-end farm example runs in a fresh process. **No real DGACTA or weather data could be downloaded in the build environment** (no outbound access), so the download clients are tested only against a local mock server, and every runnable example uses *labelled synthetic* data. Crop numbers are FAO-56 table values transcribed through a text-extraction service; none is locally validated. Treat all volumes as *candidate* values to be checked in the field.

## Layout
```
crop_knowledge/  crop_database.json (39 crops) · crop_parameters.csv · crop_sources.json
engine/          crop_retrieval · crop_water_requirements · eto · water_balance · soil · irrigation_engine
                 prioritization (ranking + allocation) · soil_moisture_predictor · data_sources · farm_registry · farm_runner
api/             api_schema.json · sample_farm.json · sample_crop_profile.json · sample_irrigation_response.json
models/          model_metadata.json   (no trained model shipped: persistence won; see file)
tests/           unittest suite (stdlib only) + fixtures/synthetic.py (SYNTHETIC, tests/demos only)
tools/           build_crop_knowledge.py · make_samples.py
AUDIT_REPORT.md
```

## Quick start
```python
import sys; sys.path.insert(0, "FARMLINK_Module5_Deliverables")
from engine.crop_retrieval import CropIndex
from engine.farm_runner import run_farm

ix = CropIndex(); ix.search("tomat"); ix.autocomplete("ol"); ix.get("blé dur")      # names, FR/AR, synonyms
resp = run_farm("api/sample_farm.json", weather_df, today="2026-05-30", forecast=forecast_df,
                weather_source="open_meteo_archive", available_water_m3=20)          # -> JSON-serialisable dict
```
Weather frame columns: `date,tmin,tmax,tmean,rh_mean,u2,rs,rain_mm` (u2: wind at 2 m in m/s; rs: MJ/m²/day). ETo is Penman-Monteith when complete, otherwise Hargreaves-Samani; the method is recorded per day (`eto_methods_in_window`).
Fetch real weather with `engine.data_sources.fetch_weather(lat, lon, start, end)` (Open-Meteo → NASA POWER, fallback recorded in the returned provenance) and DGACTA with `fetch_station_package` / `discover_resources` / `download_resource`.

Run the tests: `python -m unittest discover -s tests`.

## Rules the engine enforces
* No soil property is invented: without FC/WP the zone is `MISSING_SOIL_PARAMS`, volume withheld. Unknown irrigation efficiency ⇒ net requirement only. Missing planting date (annual) ⇒ no stage guess unless `stage_override`.
* Sensors count only if `calibrated: true` in VWC units; millivolts are never converted; depth comes from resource metadata; root-zone VWC is thickness-weighted with an extrapolation warning.
* TAW = 1000(FC−WP)Zr; RAW = p·TAW with p adjusted for ETc (0.1–0.8); Ks per FAO-56 Eq. 84; water balance closes exactly (tested); runoff = capillary rise = 0 and effective rain = P − 2 mm are *declared approximations*.
* m³ = gross mm × ha × 10; gross = net / Ea (typical Ea by method is labelled `typical_literature`, not measured).
* Root depth develops linearly from an assumed 0.30 m (FAO-56 Example 38, a single worked example) to the Table 22 scheduling depth over initial+development; perennials constant.
* Ranking weights and the allocation strategy (protect-then-refill) are documented design choices — neither calibrated nor optimal.

## Known limits
Kc_ini is often the FAO-56 *group default* (labelled); durum wheat = generic winter wheat; olive/citrus ignore actual canopy cover beyond named variants; ECOCROP/CROPWAT/WaPOR content, Ky (water sensitivity), Tunisian calendars and Arabic-name verification are **not** in the database (listed under each crop's `missing`); no yield model; no salinity; the Open-Meteo/NASA/CKAN HTTP contracts follow public documentation and were not exercised against the live services.
