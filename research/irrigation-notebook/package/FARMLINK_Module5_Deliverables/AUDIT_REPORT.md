# Initial audit — `tunisian_crop_monitoring_final_v2.ipynb`

Method: the notebook JSON was inspected directly (cell counts, stored outputs, source patterns) and the notebook was executed from first to last cell in a sandbox **without internet**. Nothing from earlier reports was assumed.

## 1. Verified state (the stated figures are correct)
| Item | Verified value |
|---|---|
| Cells | 51 (29 code, 22 markdown) |
| Code cells with stored outputs / executed | 13 / 13 (16 output objects, 0 error outputs) |
| Code cells never executed | 16 — all are the v2 irrigation module (12A–12G, incl. unit-test cell) |
| Original notebook (before v2) | 25 cells, 13 code, all 13 executed, 16 output objects |

The 13 stored outputs come from a run on the notebook author's machine on **real DGACTA data** (a Windows path is printed). They are evidence of that run only; they were not reproduced here.

## 2. Functional vs. incomplete (offline execution, sandbox)
* Run OK offline: cells 2, 4, 12, 19, 24-32, 34, 36, 38, 40, 43, 45, 50 (setup, graceful download failure, old FAO-56 class, v2 package install and tests, demos that need no sensor table).
* **Fail offline, in cascade:** cell 6 `KeyError: 'domain'` (empty parser output) → cells 7, 9, 11 `NameError` → 14, 16, 17, 21, 42 `NameError` on `cm_piv`/`ml_dataset`. The notebook gives no explanation when data is absent; the first message is a pandas `KeyError`.
* The 16 unexecuted v2 cells were verified only by an out-of-notebook harness in the previous session (synthetic fixture); the notebook itself carried no outputs for them.

## 3. Download problems (cells 2, 4, 12)
1. `verify=False` in 3 requests and `urllib3.disable_warnings` — TLS verification disabled globally.
2. One attempt per request, no retry/backoff; fixed timeouts (25/35/30 s); redirects not checked.
3. No validation of the CKAN response beyond `success`, no check that a "CSV" is not an HTML error/login page, no checksum, no size check.
4. Resource discovery is a plain loop; cache fallback is partial and silent (message only).
5. Station coordinates are hard-coded, not read from CKAN metadata (unverified).
6. NASA POWER window hard-coded to 2026-11-01..21 (not tied to the sensor span); only `== -999` replaced after the fact; no Open-Meteo, no recorded fallback logic.

## 4. Scientific weaknesses
1. ML evidence is tiny: 154 aligned rows, 47 test samples over ≈ 5 days (1 h horizon); 6 h / 24 h tests have 42 / 40 samples. Persistence won at all horizons (MAE 0.0191 / 0.1095 / 0.5175 %), so no ML claim is supportable — the notebook handled this honestly.
2. The "winning" model saved to a pickle is the persistence baseline; the portability test printed a joblib/loky `wmic` traceback (Windows) as noise.
3. Original FAO-56 engine (cell 19): hard-coded Kc and Zr for 3 crops (tomato Zr 0.80 m, olive 1.20, wheat 1.00; wheat Kc end 0.25), stage chosen manually (no date-based stage, no Kc curve), Zr constant through the season, 85 % drip efficiency fixed. Superseded by v2 and now by `engine/`.
4. v2: Kc per stage = start/end means; Zr = lower bound of the Table 22 range; effective rain = P − 2 mm (declared approximation); elevation 10 m is a declared assumption for Chott Meriam.
5. Only Chott Meriam feeds the pipeline (`cm_sm`); the other four stations are parsed but unused downstream.
6. Measurement integrity (kept): parser separates VWC (%), voltage (mV) and temperature, depth comes from resource text, `None` when absent. Weak point: depth regex `(\d+)\s*cm` on name+filename, domain tests like `'sol' in resource_name` are broad substring rules and `iterrows` over all records is slow.

## 4b. Missing dependencies
`seaborn` (optional, guarded), `ipywidgets` (12E), `requests` (guarded). No `requirements.txt`; no packaging; paths are Kaggle-specific (`/kaggle/working`).

## 5. Integration problems for a web app
All logic lives in notebook globals; v2 embeds a 3-crop package via `%writefile` (not importable without running the notebook); no JSON contract; no multi-zone model; no farm-wide ranking, volumes in m³ or water allocation; no crop search.

## 6. What this audit could not check
Live behaviour of data.gov.tn, Open-Meteo and NASA POWER (unreachable from the sandbox), and whether the stored outputs correspond to the exact data currently on the portal.
