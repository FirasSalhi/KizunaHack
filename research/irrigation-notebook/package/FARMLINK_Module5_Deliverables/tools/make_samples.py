"""Regenerate api/sample_crop_profile.json and api/sample_irrigation_response.json (deterministic, SYNTHETIC weather)."""
import json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tests"))
from engine.crop_retrieval import CropIndex
from engine.farm_runner import run_farm
from fixtures.synthetic import synthetic_weather

ix = CropIndex()
prof = {"_label": "Crop profile exactly as served from crop_knowledge/crop_database.json (FAO-56 transcription; not locally validated).",
        "profile": ix.get("tomato"), "completeness": ix.completeness("tomato")}
(ROOT / "api" / "sample_crop_profile.json").write_text(json.dumps(prof, ensure_ascii=False, indent=1), encoding="utf-8")

w = synthetic_weather("2026-04-01", 60); f = synthetic_weather("2026-05-31", 7, seed=1, rain_days=(3,))
resp = run_farm(str(ROOT / "api" / "sample_farm.json"), w[w.date <= "2026-05-30"], "2026-05-30", f, "SYNTHETIC_FIXTURE", available_water_m3=20)
out = {"_label": "ILLUSTRATIVE RESPONSE computed from SYNTHETIC weather (tests/fixtures/synthetic.py) and the demo farm. Not a real recommendation.", "response": resp}
(ROOT / "api" / "sample_irrigation_response.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("samples written")
