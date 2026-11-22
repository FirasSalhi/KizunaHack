"""Plant identification from a photo, plant health check and full care sheet.

Ported from is9ini (github.com/RaziSnihaa/is9ini, backend/app/plant_id.py).
Same engines, thresholds and data.

Engines, tried in this order (PLANT_ENGINE=auto):
  1. Pl@ntNet API  ~50 000 species, needs internet + PLANTNET_API_KEY (free: 500 photos/day)
  2. BioCLIP 2     local, offline; zero-shot over the ~26 000-plant catalogue (see catalog.py)
  3. verdant       small local model, 110 houseplants only (last resort)

Care data: verdant-care-db (houseplants, CC BY-SA 4.0) + FAO EcoCrop (2 568 crops).
Health: Pl@ntNet diseases API online; offline, a PlantVillage leaf model for the 14 crops it knows.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import sqlite3
import ssl
import threading
import time
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageOps

from app.core.config import settings

log = logging.getLogger("farmlink.plants")

PLANTNET_URL = "https://my-api.plantnet.org/v2/identify/all"
PLANTNET_DISEASES_URL = "https://my-api.plantnet.org/v2/diseases/identify"


def _models() -> Path:
    return Path(settings.PLANT_MODELS_DIR)


def _verdant_dir() -> Path:
    return _models() / "verdant-plant-model"


def _care_db() -> Path:
    return _models() / "verdant-care-db" / "verdant_care.sqlite"


def _catalog_dir() -> Path:
    return _models() / "catalog"


def _bioclip_dir() -> Path:
    return _models() / "bioclip-2"


# --- human-readable labels -----------------------------------------------------------------
VERDANT_LIGHT = {
    "bright_some_direct": ("Bright, some direct sun", "≈ 10 000 – 30 000 lux"),
    "bright_indirect": ("Bright indirect light", "≈ 5 000 – 15 000 lux"),
    "medium": ("Medium light, no direct sun", "≈ 1 000 – 5 000 lux"),
}
VERDANT_HUMIDITY = {
    "low_ok": ("30 – 50 %", "low is fine"),
    "average": ("40 – 60 %", "average"),
    "high": ("60 – 80 %", "high"),
}
VERDANT_TOXICITY = {
    "non_toxic": "Non-toxic",
    "mildly_toxic": "Mildly toxic if eaten",
    "toxic_pets": "Toxic to pets",
}
VERDANT_TYPE = {
    "succulent": "Succulent",
    "cactus": "Cactus",
    "carnivorous": "Carnivorous",
    "tropical_foliage": "Tropical foliage",
    "flowering": "Flowering plant",
    "fern": "Fern",
    "bulb": "Bulb",
    "palm": "Palm",
    "prayer": "Prayer plant",
}
ECO_LIGHT = {
    "very bright": ("Full sun", "≈ 30 000 – 100 000 lux"),
    "clear skies": ("Sunny, open sky", "≈ 20 000 – 60 000 lux"),
    "cloudy skies": ("Bright, tolerates cloud", "≈ 5 000 – 20 000 lux"),
    "light shade": ("Light shade", "≈ 5 000 – 15 000 lux"),
    "heavy shade": ("Shade", "≈ 1 000 – 5 000 lux"),
}
# PlantVillage crops known by the leaf model: catalogue key prefix -> word used in its labels
LEAF_CROPS = {
    "malus": "Apple",
    "vaccinium": "Blueberry",
    "prunus avium": "Cherry",
    "prunus cerasus": "Cherry",
    "zea mays": "Corn",
    "vitis": "Grape",
    "citrus": "Orange",
    "prunus persica": "Peach",
    "capsicum": "Pepper",
    "solanum tuberosum": "Potato",
    "rubus": "Raspberry",
    "glycine max": "Soybean",
    "cucurbita": "Squash",
    "fragaria": "Strawberry",
    "solanum lycopersicum": "Tomato",
}

_lock = threading.Lock()
_db_lock = threading.RLock()
_pool = ThreadPoolExecutor(max_workers=4)
_state: dict[str, Any] = {}


class ScannerUnavailable(Exception):
    """The models are not installed (run: python -m app.plants.catalog)."""


def _num(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _fmt(v: Any) -> str:
    return f"{v:g}" if isinstance(v, float) else str(v)


def _binomial(name: str | None) -> str | None:
    # hybrids: "Fragaria × ananassa"
    words = [w for w in (name or "").replace("×", " ").split() if w.lower() != "x"]
    if len(words) >= 2 and words[0][:1].isupper():
        return f"{words[0]} {words[1]}".lower()
    return None


def _eco_index(rows: list[dict[str, str]]) -> dict[str, int]:
    """EcoCrop row by 'genus species', accepted names first, then synonyms."""
    index: dict[str, int] = {}
    for i, r in enumerate(rows):
        b = _binomial(r["ScientificName"])
        if b and b not in index:
            index[b] = i
    for i, r in enumerate(rows):
        for syn in (r["SYNO"] or "").split(","):
            b = _binomial(syn.strip())
            if b and b not in index:
                index[b] = i
    if "lycopersicon esculentum" in index:
        index.setdefault("solanum lycopersicum", index["lycopersicon esculentum"])
    return index


# --- loading -----------------------------------------------------------------
def _base() -> dict[str, Any]:
    """Care databases + verdant model + leaf model (small, always loaded)."""
    if not available():
        raise ScannerUnavailable("Plant scanner models are not installed.")
    with _lock:
        if "db" not in _state:
            import onnxruntime as ort

            verdant = _verdant_dir()
            cfg = json.loads((verdant / "config.json").read_text(encoding="utf-8"))
            opts = ort.SessionOptions()
            opts.log_severity_level = 3
            for head in ("species_head", "disease_head"):
                _state[head] = {
                    "cfg": cfg[head],
                    "session": ort.InferenceSession(
                        str(verdant / cfg[head]["file"]), opts, providers=["CPUExecutionProvider"]
                    ),
                }
            db = sqlite3.connect(_care_db(), check_same_thread=False)
            _state["db"] = db
            eco_csv = _models() / "ecocrop" / "EcoCrop_DB.csv"
            if eco_csv.exists():
                with open(eco_csv, encoding="latin-1") as f:
                    _state["eco"] = list(csv.DictReader(f))
            else:
                _state["eco"] = []
            _state["eco_index"] = _eco_index(_state["eco"])
            species = db.execute("SELECT id, scientific_name FROM species").fetchall()
            _state["verdant_by_name"] = {b: r[0] for r in species if (b := _binomial(r[1]))}
            # entries stored by genus only, e.g. "Spathiphyllum"
            _state["verdant_by_genus"] = {}
            for vid, sci in species:
                if sci and len(sci.split()) == 1:
                    _state["verdant_by_genus"].setdefault(sci.lower(), vid)
            _state["classes"], _state["by_key"], _state["by_verdant"] = [], {}, {}
        # The BioCLIP catalogue may be built while the API runs: pick it up as soon as it exists.
        classes_file = _catalog_dir() / "classes.json"
        if not _state["classes"] and classes_file.exists():
            cat = json.loads(classes_file.read_text(encoding="utf-8"))["classes"]
            _state["by_key"] = {c["key"]: c for c in cat}
            _state["by_verdant"] = {c["verdant"]: c for c in cat if c["verdant"]}
            _state["classes"] = cat
    return _state


def _bioclip() -> dict[str, Any] | None:
    bioclip_dir, catalog = _bioclip_dir(), _catalog_dir()
    if (
        not (bioclip_dir / "open_clip_config.json").exists()
        or not (catalog / "text_emb.npy").exists()
    ):
        return None
    if not _base()["classes"]:
        return None
    with _lock:
        if "bioclip" not in _state:
            try:
                import open_clip
                import torch
            except ImportError:  # optional extra: uv sync --extra bioclip
                log.info("BioCLIP 2 not installed (uv sync --extra bioclip); skipping it")
                _state["bioclip"] = None
                return None

            device = "cuda" if torch.cuda.is_available() else "cpu"
            model, _, preprocess = open_clip.create_model_and_transforms(f"local-dir:{bioclip_dir}")
            model = model.to(device).eval()
            if device == "cuda":
                model = model.half()
            emb = torch.from_numpy(np.load(catalog / "text_emb.npy")).to(device)
            emb = emb.half() if device == "cuda" else emb.float()
            _state["bioclip"] = {
                "model": model,
                "preprocess": preprocess,
                "emb": emb,
                "device": device,
                "scale": float(model.logit_scale.exp()),
            }
            log.info("BioCLIP 2 ready on %s (%d classes)", device, emb.shape[0])
    bioclip: dict[str, Any] | None = _state["bioclip"]
    return bioclip


def available() -> bool:
    return _care_db().exists() and (_verdant_dir() / "config.json").exists()


def engines() -> dict[str, bool]:
    """Which engines can answer right now (for the status line in the app)."""
    has_bioclip = (_bioclip_dir() / "open_clip_config.json").exists() and (
        _catalog_dir() / "text_emb.npy"
    ).exists()
    return {
        "plantnet": bool(settings.PLANTNET_API_KEY),
        "bioclip": has_bioclip,
        "verdant": available(),
    }


def warm_up() -> None:
    """Load the models in the background so the first scan is fast."""

    def run() -> None:
        try:
            _base()
            _bioclip()
        except Exception as exc:
            log.warning("Plant models not loaded: %s", exc)

    if available():
        threading.Thread(target=run, daemon=True).start()


# --- engines -----------------------------------------------------------------
def _open(image_bytes: bytes) -> Image.Image:
    return ImageOps.exif_transpose(Image.open(io.BytesIO(image_bytes))).convert("RGB")


def _engine_bioclip(img: Image.Image) -> dict[str, Any] | None:
    b = _bioclip()
    if b is None:
        return None
    import torch

    x = b["preprocess"](img).unsqueeze(0).to(b["device"])
    if b["device"] == "cuda":
        x = x.half()
    with torch.no_grad():
        f = torch.nn.functional.normalize(b["model"].encode_image(x).float(), dim=-1)
        logits = b["scale"] * f @ b["emb"].float().T
        probs = torch.softmax(logits, dim=-1)[0].cpu().numpy()
    classes = _state["classes"]
    top = np.argsort(-probs)[:5]
    # genus-level vote: species of the same genus share the probability mass
    genus = classes[top[0]]["taxonomy"][5]
    if genus:
        genus_p = float(
            sum(p for c, p in zip(classes, probs, strict=False) if c["taxonomy"][5] == genus)
        )
    else:
        genus_p = float(probs[top[0]])
    return {
        "engine": "BioCLIP 2 (local)",
        "candidates": [{"key": classes[i]["key"], "p": float(probs[i])} for i in top],
        "genus": genus,
        "genus_p": genus_p,
    }


def _ssl_context() -> ssl.SSLContext:
    """Use certifi's CA bundle when the system has none (still verifies the certificate)."""
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _multipart(image_bytes: bytes) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    body = (
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="organs"\r\n\r\nauto\r\n'
            f"--{boundary}\r\nContent-Disposition: form-data; "
            f'name="images"; filename="photo.jpg"\r\n'
            f"Content-Type: image/jpeg\r\n\r\n"
        ).encode()
        + image_bytes
        + f"\r\n--{boundary}--\r\n".encode()
    )
    return body, f"multipart/form-data; boundary={boundary}"


def _engine_plantnet(image_bytes: bytes) -> dict[str, Any] | None:
    key = settings.PLANTNET_API_KEY
    if not key:
        return None
    body, ctype = _multipart(image_bytes)
    url = (
        f"{PLANTNET_URL}?include-related-images=false&no-reject=true&nb-results=5&lang=en"
        f"&api-key={key}"
    )
    req = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": ctype})  # noqa: S310
    with urllib.request.urlopen(req, timeout=12, context=_ssl_context()) as resp:  # noqa: S310
        data = json.loads(resp.read())
    results = data.get("results") or []
    if not results:
        return None
    cands = []
    for r in results[:5]:
        sp = r["species"]
        cands.append(
            {
                "key": _binomial(sp["scientificNameWithoutAuthor"])
                or sp["scientificNameWithoutAuthor"].lower(),
                "p": float(r["score"]),
                "scientific": sp["scientificNameWithoutAuthor"],
                # "Apple" over "Paradise apple"
                "common": min((sp.get("commonNames") or [""])[:3], key=len).capitalize(),
                "family": sp.get("family", {}).get("scientificNameWithoutAuthor", ""),
                "genus": sp.get("genus", {}).get("scientificNameWithoutAuthor", ""),
            }
        )
    # if Pl@ntNet also knows our catalogue name ("Spider plant"), use it
    for c, r in zip(cands, results, strict=False):
        known = (_state.get("by_key", {}).get(c["key"]) or {}).get("common") or ""
        if known.lower() in [n.lower() for n in r["species"].get("commonNames") or []]:
            c["common"] = known[:1].upper() + known[1:]
    top_genus = cands[0]["genus"]
    return {
        "engine": "Pl@ntNet API",
        "candidates": cands,
        "genus": top_genus,
        "genus_p": sum(c["p"] for c in cands if c["genus"] == top_genus),
        "remaining": data.get("remainingIdentificationRequests"),
    }


def _verdant_run(head: dict[str, Any], img: Image.Image) -> Any:
    h = head["cfg"]
    w, ht = img.size
    s = h["resize_shortest_edge"] / min(w, ht)
    im = img.resize((max(1, round(w * s)), max(1, round(ht * s))), Image.Resampling.BICUBIC)
    w, ht = im.size
    c = h["center_crop"]
    im = im.crop(((w - c) // 2, (ht - c) // 2, (w - c) // 2 + c, (ht - c) // 2 + c))
    x = np.asarray(im, dtype=np.float32) * h["rescale"]
    if h.get("channel_order") == "BGR":
        x = x[..., ::-1]
    x = (x - np.array(h["mean"], dtype=np.float32)) / np.array(h["std"], dtype=np.float32)
    inputs = {h["input_name"]: x.transpose(2, 0, 1)[None].astype(np.float32)}
    return head["session"].run([h["output_name"]], inputs)[0][0]


def _engine_verdant(img: Image.Image) -> dict[str, Any]:
    head = _state["species_head"]
    logits = _verdant_run(head, img)
    p = np.exp(logits - logits.max())
    p /= p.sum()
    top = np.argsort(-p)[:5]
    labels = head["cfg"]["labels"]
    cands = []
    for i in top:
        c = _state["by_verdant"].get(labels[i])
        cands.append(
            {
                "key": c["key"] if c else f"verdant:{labels[i]}",
                "p": float(p[i]),
                "verdant": labels[i],
            }
        )
    return {
        "engine": "verdant (110 houseplants)",
        "candidates": cands,
        "genus": None,
        "genus_p": float(p[top[0]]),
    }


# --- care sheets -----------------------------------------------------------------
def _item(key: str, title: str, value: str, detail: str = "") -> dict[str, str]:
    return {"key": key, "title": title, "value": value, "detail": detail}


def _verdant_row(vid: str) -> sqlite3.Row | None:
    cur = _state["db"].cursor()
    cur.row_factory = sqlite3.Row
    row: sqlite3.Row | None = cur.execute("SELECT * FROM species WHERE id = ?", (vid,)).fetchone()
    return row


def _disease(disease_id: str) -> dict[str, Any] | None:
    r = (
        _state["db"]
        .execute(
            "SELECT disease_id, name, symptoms, prevention, treatment_steps FROM disease_text "
            "WHERE disease_id = ? AND lang = 'en'",
            (disease_id,),
        )
        .fetchone()
    )
    if not r:
        return None
    return {
        "id": r[0],
        "name": r[1],
        "symptoms": r[2],
        "prevention": r[3],
        "treatment": json.loads(r[4] or "[]"),
    }


def _leaf_crop(key: str) -> str | None:
    for prefix, crop in LEAF_CROPS.items():
        if key == prefix or key.startswith(prefix + " "):
            return crop
    return None


def _crop_diseases(crop: str) -> list[dict[str, Any]]:
    rows = (
        _state["db"]
        .execute(
            "SELECT DISTINCT disease_id FROM model_disease_map "
            "WHERE is_healthy = 0 AND model_label LIKE ?",
            (f"%{crop}%",),
        )
        .fetchall()
    )
    return [d for d in (_disease(r[0]) for r in rows) if d]


def care_sheet(key: str, override: dict[str, Any] | None = None) -> dict[str, Any]:  # noqa: C901
    """Full care sheet for a catalogue key (e.g. 'malus domestica'), merging verdant + EcoCrop."""
    with _db_lock:
        st = _base()
        c = st["by_key"].get(key)
        if c is None and key.startswith("verdant:"):
            c = {
                "key": key,
                "taxonomy": ["Plantae"],
                "common": "",
                "ecocrop": None,
                "verdant": key.split(":", 1)[1],
                "family": "",
            }
        elif (
            c is None
        ):  # species not in the BioCLIP catalogue (e.g. from Pl@ntNet): look it up by name
            c = {
                "key": key,
                "taxonomy": ["Plantae"],
                "common": "",
                "family": "",
                "ecocrop": st["eco_index"].get(key),
                "verdant": st["verdant_by_name"].get(key),
            }
        o = override or {}
        sheet: dict[str, Any] = {
            "id": key,
            "common_name": o.get("common") or c.get("common") or "",
            "scientific_name": o.get("scientific") or c.get("scientific") or key.capitalize(),
            "family": o.get("family") or c.get("family") or "",
            "type": "Plant",
            "care": [],
            "possible_diseases": [],
            "recommended_settings": None,
            "sources": [],
        }
        v = _verdant_row(c["verdant"]) if c.get("verdant") else None
        e = st["eco"][c["ecocrop"]] if c.get("ecocrop") is not None else None
        if not v and not e:  # no data for this exact species: borrow a close relative (same genus)
            genus = key.split()[0] + " " if " " in key else None
            if genus:
                vid = next(
                    (vid for b, vid in st["verdant_by_name"].items() if b.startswith(genus)), None
                ) or st["verdant_by_genus"].get(genus.strip())
                eid = next((i for b, i in st["eco_index"].items() if b.startswith(genus)), None)
                v = _verdant_row(vid) if vid else None
                e = st["eco"][eid] if eid is not None and not v else None
                if v or e:
                    relative = v["scientific_name"] if v else e["ScientificName"]  # type: ignore[index]
                    sheet["note"] = (
                        f"Care data from a close relative of the same genus ({relative})."
                    )
        care: dict[str, dict[str, str]] = {}
        dry: float | None = None
        wet: float | None = None
        tmin: float | None = None
        tmax: float | None = None

        if e:
            sheet["sources"].append("FAO EcoCrop")
            lifo, lispa = (e["LIFO"] or "").split(",")[0], (e["LISPA"] or "").split(",")[0]
            sheet["type"] = " ".join(x for x in (lispa.capitalize(), lifo) if x) or "Plant"
            if e["CAT"]:
                sheet["category"] = e["CAT"]
            r_lo, r_hi = _num(e["ROPMN"]), _num(e["ROPMX"])
            if r_lo and r_hi:
                mean = (r_lo + r_hi) / 2
                if mean < 600:
                    need, dry, wet = "Low", 20, 70
                elif mean <= 1200:
                    need, dry, wet = "Medium", 35, 80
                else:
                    need, dry, wet = "High", 45, 85
                care["watering"] = _item(
                    "watering",
                    "Water need",
                    need,
                    f"{_fmt(r_lo)} – {_fmt(r_hi)} mm of rain per year",
                )
            light = ECO_LIGHT.get((e["LIOPMN"] or "").strip()) or ECO_LIGHT.get(
                (e["LIOPMX"] or "").strip()
            )
            if light:
                care["light"] = _item("light", "Light", light[0], light[1])
            t_lo, t_hi = _num(e["TOPMN"]), _num(e["TOPMX"])
            a_lo, a_hi = _num(e["TMIN"]), _num(e["TMAX"])
            if t_lo is not None and t_hi is not None:
                tmin, tmax = t_lo, t_hi
                detail = (
                    f"survives {_fmt(a_lo)} – {_fmt(a_hi)} °C"
                    if a_lo is not None and a_hi is not None
                    else "optimal range"
                )
                care["temperature"] = _item(
                    "temperature", "Temperature", f"{_fmt(t_lo)} – {_fmt(t_hi)} °C", detail
                )
            kill = _num(e["KTMP"])
            if kill is not None:
                care["frost"] = _item(
                    "frost", "Frost", f"Killed at {_fmt(kill)} °C", "protect below this"
                )
            ph_lo, ph_hi = _num(e["PHOPMN"]), _num(e["PHOPMX"])
            if ph_lo and ph_hi:
                drained = (e["DRA"] or "").split("(")[0].strip() + " drained"
                care["soil"] = _item("soil", "Soil pH", f"{_fmt(ph_lo)} – {_fmt(ph_hi)}", drained)
            g_lo, g_hi = _num(e["GMIN"]), _num(e["GMAX"])
            if g_lo and g_hi:
                care["cycle"] = _item(
                    "cycle", "Growing cycle", f"{_fmt(g_lo)} – {_fmt(g_hi)} days", lispa or ""
                )

        if v:  # houseplant data is more precise for indoor care: it wins
            sheet["sources"].insert(0, "verdant-care-db")
            if not sheet["common_name"]:
                n = (
                    _state["db"]
                    .execute(
                        "SELECT common_name FROM species_name WHERE species_id = ? AND lang = 'en'",
                        (v["id"],),
                    )
                    .fetchone()
                )
                sheet["common_name"] = n[0] if n else v["id"].replace("-", " ").capitalize()
            if sheet["scientific_name"].lower().startswith("verdant:"):
                sheet["scientific_name"] = v["scientific_name"]
            sheet["type"] = VERDANT_TYPE.get(v["care_archetype"], sheet["type"])
            days = v["watering_interval_days"]
            care["watering"] = _item(
                "watering", "Watering", f"Every {days} days", "when the topsoil is dry"
            )
            vlight = VERDANT_LIGHT.get(v["light_code"], (v["light_code"], ""))
            care["light"] = _item("light", "Light", vlight[0], vlight[1])
            hum = VERDANT_HUMIDITY.get(v["humidity_code"], (v["humidity_code"], ""))
            care["humidity"] = _item("humidity", "Humidity", hum[0], hum[1])
            care["temperature"] = _item(
                "temperature",
                "Temperature",
                f"{v['temp_min']} – {v['temp_max']} °C",
                "comfort range",
            )
            care["toxicity"] = _item(
                "toxicity",
                "Pets & kids",
                VERDANT_TOXICITY.get(v["toxicity_code"], v["toxicity_code"]),
            )
            if days <= 3:
                dry, wet = 45, 85
            elif days <= 7:
                dry, wet = 35, 80
            elif days <= 14:
                dry, wet = 25, 75
            else:
                dry, wet = 15, 65
            tmin, tmax = v["temp_min"], v["temp_max"]
            rows = (
                _state["db"]
                .execute("SELECT disease_id FROM susceptibility WHERE species_id = ?", (v["id"],))
                .fetchall()
            )
            sheet["possible_diseases"] = [d for d in (_disease(r[0]) for r in rows) if d]

        crop = _leaf_crop(key)
        if crop and not sheet["possible_diseases"]:
            sheet["possible_diseases"] = _crop_diseases(crop)
        sheet["leaf_crop"] = crop

        order = [
            "watering",
            "light",
            "humidity",
            "temperature",
            "frost",
            "soil",
            "cycle",
            "toxicity",
        ]
        sheet["care"] = [care[k] for k in order if k in care]
        sheet["care"].append(
            _item("type", "Type", sheet["type"], sheet.get("category", "").split(",")[0])
        )
        if dry is not None and tmin is not None and tmax is not None:
            sheet["recommended_settings"] = {
                "plant_profile": key,
                "soil_dry_pct": dry,
                "soil_wet_pct": wet,
                "temp_min_c": max(0.0, min(30.0, float(tmin))),
                "temp_max_c": max(15.0, min(50.0, float(tmax))),
            }
        if not sheet["common_name"]:
            sheet["common_name"] = sheet["scientific_name"]
        if not v and not e:
            sheet["note"] = "No growing data in our databases for this plant yet."
        return sheet


# --- health check: is the plant sick? ------------------------------------------------------------
SICK_SCORE = 0.30  # measured: real diseases 0.46-0.64, healthy plants <= 0.11
HEALTHY_SCORE = 0.15
# words in a Pl@ntNet disease name -> treatment sheet in verdant-care-db (first match wins)
DISEASE_SHEETS = [
    ("late blight", "late_blight"),
    ("phytophthora", "late_blight"),
    ("early blight", "early_blight"),
    ("alternaria", "early_blight"),
    ("powdery mildew", "powdery_mildew"),
    ("oidium", "powdery_mildew"),
    ("erysiphe", "powdery_mildew"),
    ("botrytis", "leaf_mold"),
    ("mould", "leaf_mold"),
    ("mold", "leaf_mold"),
    ("blight", "blight"),
    ("rust", "rust"),
    ("puccinia", "rust"),
    ("scab", "scab"),
    ("venturia", "scab"),
    ("black rot", "black_rot"),
    ("rot", "root_rot"),
    ("pythium", "root_rot"),
    ("scorch", "leaf_scorch"),
    ("bacterial", "bacterial_spot"),
    ("xanthomonas", "bacterial_spot"),
    ("pseudomonas", "bacterial_spot"),
    ("leaf spot", "leaf_spot"),
    ("septoria", "leaf_spot"),
    ("cercospora", "leaf_spot"),
    ("spot", "leaf_spot"),
    ("mite", "spider_mite"),
    ("tetranychus", "spider_mite"),
    ("greening", "citrus_greening"),
    ("esca", "esca"),
    ("virus", "viral"),
    ("mosaic", "viral"),
    ("tobamovirus", "viral"),
]


def _plantnet_diseases(image_bytes: bytes) -> list[dict[str, Any]] | None:
    key = settings.PLANTNET_API_KEY
    if not key:
        return None
    body, ctype = _multipart(image_bytes)
    url = f"{PLANTNET_DISEASES_URL}?include-related-images=false&nb-results=5&lang=en&api-key={key}"
    req = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": ctype})  # noqa: S310
    try:
        with urllib.request.urlopen(req, timeout=15, context=_ssl_context()) as resp:  # noqa: S310
            results: list[dict[str, Any]] = json.loads(resp.read()).get("results") or []
            return results
    except urllib.error.HTTPError as exc:
        if exc.code == 404:  # "not found": nothing recognised on the photo
            return []
        raise


def _disease_entry(r: dict[str, Any]) -> dict[str, Any]:
    desc = r.get("description") or r["name"]
    scientific, _, common = desc.partition(" - ")
    text = desc.lower()
    sheet_id = next((sid for word, sid in DISEASE_SHEETS if word in text), None)
    sheet = _disease(sheet_id) if sheet_id else None
    name = common.strip() or (sheet["name"] if sheet else scientific.strip())
    # "Late blight of potato" on a tomato -> "Late blight"
    if sheet and sheet["name"].lower() in name.lower():
        name = sheet["name"]
    return {
        "code": r["name"],
        "name": name[:1].upper() + name[1:],
        "scientific": scientific.strip(),
        "score": round(float(r["score"]), 3),
        "sheet": sheet,
    }


def _health_from_plantnet(results: list[dict[str, Any]]) -> dict[str, Any]:
    entries = [_disease_entry(r) for r in results]
    if not entries:
        return {
            "engine": "Pl@ntNet diseases",
            "status": "healthy_looking",
            "confidence": None,
            "top": None,
            "others": [],
            "message": "No disease or pest recognised on this photo.",
        }
    # close pathogens of the same genus (e.g. several Puccinia rusts) share the score: add them up
    genus = entries[0]["scientific"].split()[0] if entries[0]["scientific"] else ""
    group = sum(e["score"] for e in entries if genus and e["scientific"].split()[:1] == [genus])
    top = max(entries[0]["score"], group)
    if top >= SICK_SCORE:
        status, message = "possible_disease", f"Signs of {entries[0]['name'].lower()} detected."
    elif entries[0]["score"] < HEALTHY_SCORE:
        status, message = "healthy_looking", "No clear disease detected on this photo."
    else:
        status = "uncertain"
        message = (
            "Something may be wrong, but the AI is not sure. "
            "Take a close photo of the damaged leaf."
        )
    return {
        "engine": "Pl@ntNet diseases",
        "status": status,
        "confidence": round(top, 3),
        "top": entries[0],
        "others": entries[1:4],
        "message": message,
    }


def _health_from_leaf(leaf: dict[str, Any]) -> dict[str, Any]:
    """Offline fallback: PlantVillage leaf model, only for the crops it knows."""
    if not leaf.get("applicable"):
        return {
            "engine": None,
            "status": "unavailable",
            "confidence": None,
            "top": None,
            "others": [],
            "message": "Health check needs internet (Pl@ntNet), except for apple, tomato, grape, "
            "potato, pepper, strawberry and a few other crops.",
        }
    if not leaf["sure"]:
        status, message = "uncertain", "Leaf check uncertain. Take a close photo of one leaf."
    elif leaf["healthy"]:
        status, message = "healthy_looking", "The leaf looks healthy."
    else:
        name = (leaf["disease"] or {}).get("name", leaf["label"]).lower()
        status, message = "possible_disease", f"Possible {name}."
    top = {
        "code": leaf["label"],
        "name": (leaf["disease"] or {}).get("name") or leaf["label"],
        "scientific": "",
        "score": leaf["confidence"],
        "sheet": leaf["disease"],
    }
    return {
        "engine": "PlantVillage leaf model (offline, beta)",
        "status": status,
        "confidence": leaf["confidence"],
        "top": None if leaf["healthy"] else top,
        "others": [],
        "message": message,
    }


# --- leaf check -----------------------------------------------------------------
def _leaf_check(img: Image.Image, crop: str) -> dict[str, Any]:
    head = _state["disease_head"]
    labels = head["cfg"]["labels"]
    idx = [i for i, lab in enumerate(labels) if crop.lower() in lab.lower()]
    logits = _verdant_run(head, img)[idx]
    p = np.exp(logits - logits.max())
    p /= p.sum()
    best = int(np.argmax(p))
    label, conf = labels[idx[best]], float(p[best])
    mapped = (
        _state["db"]
        .execute(
            "SELECT disease_id, is_healthy FROM model_disease_map WHERE model_label = ?", (label,)
        )
        .fetchone()
    )
    return {
        "beta": True,
        "applicable": True,
        "crop": crop,
        # trained on single-leaf lab photos: only trust very confident answers
        "sure": conf >= 0.9,
        "healthy": bool(mapped[1]) if mapped else None,
        "label": label,
        "confidence": round(conf, 3),
        "disease": _disease(mapped[0]) if mapped and mapped[0] else None,
        "note": f"Compared only with {crop.lower()} leaf conditions (PlantVillage, lab photos). "
        "For a real check, photograph one leaf up close. Indicative only.",
    }


# --- main entry point -----------------------------------------------------------------
SURE_SPECIES = 0.35
SURE_GENUS = 0.55
ENGINE_ORDER = {
    "auto": ["plantnet", "bioclip", "verdant"],
    "plantnet": ["plantnet", "verdant"],
    "bioclip": ["bioclip", "verdant"],
    "verdant": ["verdant"],
}


def identify(image_bytes: bytes) -> dict[str, Any]:
    t0 = time.time()
    _base()
    img = _open(image_bytes)
    engine_errors: list[str] = []
    res: dict[str, Any] | None = None
    # the disease check runs in parallel with the species identification (online only)
    online = settings.PLANT_ENGINE in ("auto", "plantnet") and bool(settings.PLANTNET_API_KEY)
    disease_future = _pool.submit(_plantnet_diseases, image_bytes) if online else None
    order = ENGINE_ORDER.get(settings.PLANT_ENGINE, ENGINE_ORDER["auto"])
    for name in order:
        try:
            if name == "plantnet":
                res = _engine_plantnet(image_bytes)
            elif name == "bioclip":
                res = _engine_bioclip(img)
            else:
                res = _engine_verdant(img)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError) as exc:
            engine_errors.append(f"{name}: {exc}")
            res = None
        if res:
            break
    if res is None:  # verdant always answers; only reached if it failed too
        raise ScannerUnavailable("No plant engine could read this photo.")

    disease_results = None
    if disease_future is not None:
        try:
            disease_results = disease_future.result(timeout=20)
        except Exception as exc:  # offline, quota, timeout: fall back to the leaf model
            engine_errors.append(f"plantnet diseases: {exc}")

    with _db_lock:
        cands = res["candidates"]
        best = cands[0]
        override = {k: best.get(k) for k in ("scientific", "common", "family") if best.get(k)}
        species = care_sheet(best["key"], override)
        genus_sure = bool(res.get("genus")) and res["genus_p"] >= SURE_GENUS
        # Pl@ntNet splits its score between close species of the same genus:
        # a clear genus + a leading species is enough
        second = cands[1]["p"] if len(cands) > 1 else 0.0
        clear_lead = best["p"] >= 0.10 and best["p"] >= 2.5 * second
        sure = best["p"] >= SURE_SPECIES or (
            res["engine"].startswith("Pl@ntNet")
            and ((genus_sure and best["p"] >= 0.12) or clear_lead)
        )
        crop = species.get("leaf_crop")
        result: dict[str, Any] = {
            "engine": res["engine"],
            "sure": sure,
            "confidence": round(best["p"], 3),
            "genus": {
                "name": res.get("genus"),
                "confidence": round(res["genus_p"], 3),
                "sure": genus_sure,
            },
            "species": species,
            "alternatives": [
                {
                    "id": c["key"],
                    "common_name": c.get("common") or care_sheet(c["key"]).get("common_name"),
                    "scientific_name": c.get("scientific")
                    or care_sheet(c["key"]).get("scientific_name"),
                    "confidence": round(c["p"], 3),
                }
                for c in cands[1:4]
            ],
            "leaf_health": _leaf_check(img, crop)
            if crop and (sure or genus_sure)
            else {"applicable": False},
            "engine_errors": engine_errors,
        }
        result["health"] = (
            _health_from_plantnet(disease_results)
            if disease_results is not None
            else _health_from_leaf(result["leaf_health"])
        )
        result["ms"] = round((time.time() - t0) * 1000)
        if res.get("remaining") is not None:
            result["plantnet_remaining_today"] = res["remaining"]
        return result


def search(q: str, limit: int = 20) -> list[dict[str, Any]]:
    """Search the catalogue by common or scientific name (for picking the right plant by hand)."""
    st = _base()
    q = q.lower().strip()
    if st["classes"]:
        hits = [c for c in st["classes"] if q in c["key"] or q in (c["common"] or "").lower()]
        hits.sort(key=lambda c: (c["ecocrop"] is None and c["verdant"] is None, len(c["key"])))
        return [
            {
                "id": c["key"],
                "common_name": c["common"] or c["scientific"],
                "scientific_name": c["scientific"],
            }
            for c in hits[:limit]
        ]
    # no BioCLIP catalogue yet: search the care databases directly
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    with _db_lock:
        for vid, sci, common in (
            st["db"]
            .execute(
                "SELECT s.id, s.scientific_name, n.common_name FROM species s "
                "LEFT JOIN species_name n ON n.species_id = s.id AND n.lang = 'en'"
            )
            .fetchall()
        ):
            if q in (common or "").lower() or q in (sci or "").lower():
                key = _binomial(sci) or f"verdant:{vid}"
                seen.add(key)
                out.append({"id": key, "common_name": common or sci, "scientific_name": sci})
    seen_rows: set[int] = set()
    for b, i in st["eco_index"].items():
        row = st["eco"][i]
        names = [n.strip() for n in (row["COMNAME"] or "").split(",")]
        match = next((n for n in names if q in n.lower() and n.isascii()), None)
        if b not in seen and i not in seen_rows and (q in b or match):
            seen.add(b)
            seen_rows.add(i)
            out.append(
                {
                    "id": b,
                    "common_name": (match or b).capitalize(),
                    "scientific_name": row["ScientificName"],
                }
            )
    out.sort(key=lambda h: (not h["common_name"].lower().startswith(q), len(h["common_name"])))
    return out[:limit]
