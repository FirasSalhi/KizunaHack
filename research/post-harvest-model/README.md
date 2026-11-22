# FARMLINK · Post-Harvest Shelf-Life & Cold Storage Digital Twin 🌾📦
## Developer Integration Guide & System Architecture Specification

> **Target Audience**: Frontend Engineers (`apps/web`), Backend Engineers (`services/api`), Hardware/IoT Engineers, and Data Scientists.

---

## 📑 Table of Contents
1. [Context & Agricultural Problem](#1-context--agricultural-problem)
2. [Deliverables Inventory](#2-deliverables-inventory)
3. [Crop Biological Parameters & Feature Specification](#3-crop-biological-parameters--feature-specification)
4. [Backend Integration Guide (FastAPI / Python 3.12)](#4-backend-integration-guide-fastapi--python-312)
5. [Frontend Integration Guide (Next.js 15 / React 19 / TypeScript)](#5-frontend-integration-guide-nextjs-15--react-19--typescript)
6. [Hardware & IoT Sensor Ingestion Specification](#6-hardware--iot-sensor-ingestion-specification)
7. [Actuator Control Logic (Digital Twin State Machine)](#7-actuator-control-logic-digital-twin-state-machine)
8. [Open-Meteo Weather API Integration](#8-open-meteo-weather-api-integration)
9. [Offline PWA & Edge Deployment](#9-offline-pwa--edge-deployment)
10. [Model Validation & Benchmarks](#10-model-validation--benchmarks)

---

## 1. Context & Agricultural Problem

### The Challenge
Across North Africa (Tunisia) and Sub-Saharan Africa, **30% to 45% of harvested fruits and vegetables spoil before reaching consumers**. Smallholder farmers face two critical challenges:
1. **Lack of Cold Storage Visibility**: Farmers store harvest in makeshift ventilated rooms or local cold hubs without continuous tracking of thermal accumulation, leading to unexpected decay and forced distress sales at low market prices.
2. **Delayed Intervention**: Storage climate actuators (fans, heaters, misters) are traditionally controlled manually. By the time a farmer notices wilting or fungal rot, economic damage is irreversible.

### The FARMLINK Post-Harvest Solution
FARMLINK bridges IoT storage sensors, biological kinetic decay models, and external meteorological forecasts into an **Autonomous Digital Twin**:
- Computes **real-time remaining shelf life** based on dynamic storage temperature, relative humidity, cumulative thermal history ($T_{\text{avg}}$), and harvest age.
- Employs a **physically-calibrated Arrhenius / $Q_{10}$ decay model** ($Q_{10} = 2.43$) trained on 10,995 observations from Uganda tomato storage trials and empirical avocado ripening records.
- Provides **closed-loop autonomous actuator triggers** (cooling fan, chiller, radiant heater, ultrasonic mister) to proactively keep produce in peak preservation condition.
- Designed with a **high-contrast, farmer-friendly interface** (🟢 Safe & Fresh, 🟡 Ripening, 🔴 Sell Immediately) that elderly farmers can read at a glance without technical confusion.

---

## 2. Deliverables Inventory

| Path | Format | Description | Target Consumer |
| :--- | :--- | :--- | :--- |
| `farmer_dashboard.html` | HTML/JS/CSS | Standalone interactive digital twin with embedded trees & assets | Demo, Field Tablets, PWA |
| `models/post_harvest_model.joblib` | Python binary | Trained scikit-learn `GradientBoostingRegressor` (200 trees) | `services/api` (FastAPI) |
| `models/post_harvest_model.json` | JSON | Portable 200 decision trees for zero-dependency client execution | `apps/web` (Next.js / TS) |
| `notebooks/post_harvest_training.ipynb` | Jupyter Notebook | Complete training pipeline, data cleaning, Arrhenius fit & export | Data Science / Audit |
| `data/uganda/Dataset.csv` | CSV | 10,995 observations of tomato post-harvest storage conditions | Training & Benchmarking |
| `data/avocado/Avocado Ripening Dataset.xlsx` | Excel | Empirical multi-temperature firmness & decay dataset | Calibration ($Q_{10}$) |
| `scripts/build_farmer_dashboard.py` | Python script | Compiles decision trees and vector shaders into standalone HTML | CI/CD Pipeline |

---

## 3. Crop Biological Parameters & Feature Specification

### Crop Parameter Knowledge Base
The model supports 10 priority crops based on FAO post-harvest standards:

```json
{
  "tomato":     { "Topt": 12.0, "Tmin": 10.0, "rhlim": 90, "L0": 21,  "Q10": 2.43, "dry": false },
  "avocado":    { "Topt": 6.0,  "Tmin": 4.5,  "rhlim": 90, "L0": 28,  "Q10": 2.43, "dry": false },
  "banana":     { "Topt": 13.5, "Tmin": 12.0, "rhlim": 92, "L0": 18,  "Q10": 2.10, "dry": false },
  "apple":      { "Topt": 2.0,  "Tmin": -1.0, "rhlim": 92, "L0": 120, "Q10": 2.00, "dry": false },
  "potato":     { "Topt": 8.0,  "Tmin": 4.0,  "rhlim": 92, "L0": 150, "Q10": 1.80, "dry": false },
  "orange":     { "Topt": 6.0,  "Tmin": 3.0,  "rhlim": 88, "L0": 45,  "Q10": 2.00, "dry": false },
  "strawberry": { "Topt": 1.0,  "Tmin": 0.0,  "rhlim": 95, "L0": 7,   "Q10": 2.50, "dry": false },
  "lettuce":    { "Topt": 1.5,  "Tmin": 0.0,  "rhlim": 98, "L0": 12,  "Q10": 2.20, "dry": false },
  "carrot":     { "Topt": 1.0,  "Tmin": 0.0,  "rhlim": 98, "L0": 90,  "Q10": 1.90, "dry": false },
  "onion":      { "Topt": 0.5,  "Tmin": 0.0,  "rhlim": 68, "L0": 180, "Q10": 1.70, "dry": true  }
}
```

### 16-Element Feature Vector
The model evaluates the following ordered feature vector $X \in \mathbb{R}^{16}$:

| Index | Feature Name | Description | Formula / Source |
| :---: | :--- | :--- | :--- |
| `0` | `temperature` | Current storage temperature (°C) | Live sensor reading |
| `1` | `humidity` | Current storage relative humidity (%) | Live sensor reading |
| `2` | `avg_temperature` | Cumulative historical average temperature (°C) | $\frac{1}{N}\sum T_i$ since harvest |
| `3` | `avg_humidity` | Cumulative historical average humidity (%) | $\frac{1}{N}\sum \text{RH}_i$ since harvest |
| `4` | `age_days` | Days elapsed since harvest | $\max(0.1, \text{current\_time} - \text{harvest\_time})$ |
| `5` | `Topt` | Optimal storage temperature for crop (°C) | Crop parameter table |
| `6` | `rhlim` | Optimal relative humidity for crop (%) | Crop parameter table |
| `7` | `L0` | Base shelf life at optimal storage (days) | Crop parameter table |
| `8` | `Tmin` | Chilling injury risk threshold (°C) | Crop parameter table |
| `9` | `Q10` | Metabolic temperature acceleration coefficient | Fitted Arrhenius parameter ($2.43$) |
| `10` | `dry_storage` | Binary flag ($1$ for dry storage crops like onion, else $0$) | Crop parameter table |
| `11` | `temp_stress` | Immediate thermal gradient | $T - T_{\text{opt}}$ |
| `12` | `rh_stress` | Immediate moisture stress | Dry: $\text{RH} - \text{RH}_{\text{opt}}$, Humid: $\text{RH}_{\text{opt}} - \text{RH}$ |
| `13` | `avg_temp_stress` | Historical thermal gradient | $T_{\text{avg}} - T_{\text{opt}}$ |
| `14` | `avg_rh_stress` | Historical moisture stress | Same as `rh_stress` with $\text{RH}_{\text{avg}}$ |
| `15` | `age_fraction` | Relative harvest age fraction | $\text{age\_days} / L_0$ |

**Target**: The model outputs $\hat{y} = \log(1 + \text{Remaining Shelf Life Days})$. The predicted days is obtained via $\text{expm1}(\hat{y})$.

---

## 4. Backend Integration Guide (FastAPI / Python 3.12)

Drop this module directly into `services/api/app/api/v1/endpoints/post_harvest.py`:

```python
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
import joblib
import json
import math
from pathlib import Path
from typing import Optional, Literal

router = APIRouter(prefix="/post-harvest", tags=["Post-Harvest Shelf Life"])

# Load model once at startup
MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models"
MODEL_PATH = MODEL_DIR / "post_harvest_model.joblib"
METADATA_PATH = MODEL_DIR / "post_harvest_model.json"

try:
    model = joblib.load(MODEL_PATH)
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        crop_metadata = json.load(f)["crops"]
except Exception as e:
    model = None
    crop_metadata = {}

# Pydantic Request & Response Schemas
class ShelfLifePredictionRequest(BaseModel):
    crop: str = Field(..., example="tomato", description="Crop identifier")
    temperature: float = Field(..., example=14.5, description="Current room temperature in °C")
    humidity: float = Field(..., example=88.0, description="Current relative humidity in %")
    age_days: float = Field(..., example=2.0, description="Days elapsed since harvest")
    avg_temperature: Optional[float] = Field(None, example=12.8, description="Cumulative average temp (default: current)")
    avg_humidity: Optional[float] = Field(None, example=89.0, description="Cumulative average humidity (default: current)")

class ShelfLifePredictionResponse(BaseModel):
    crop: str
    remaining_shelf_life_days: float
    freshness_percentage: int
    risk_level: Literal["SAFE", "WARNING", "CRITICAL"]
    action_advice: str
    actuator_commands: dict

@router.post("/predict-shelf-life", response_model=ShelfLifePredictionResponse)
def predict_shelf_life(req: ShelfLifePredictionRequest):
    if req.crop.lower() not in crop_metadata:
        raise HTTPException(status_code=400, detail=f"Unsupported crop '{req.crop}'. Supported: {list(crop_metadata.keys())}")
    
    p = crop_metadata[req.crop.lower()]
    T = req.temperature
    RH = req.humidity
    Th = req.avg_temperature if req.avg_temperature is not None else T
    Rh = req.avg_humidity if req.avg_humidity is not None else RH
    a = max(0.1, req.age_days)
    d = 1.0 if p["dry"] else 0.0

    g = lambda r: (r - p["rhlim"]) if d else (p["rhlim"] - r)

    features = [
        [
            T, RH, Th, Rh, a,
            p["Topt"], p["rhlim"], p["L0"], p["Tmin"], p["Q10"], d,
            T - p["Topt"], g(RH), Th - p["Topt"], g(Rh), a / p["L0"]
        ]
    ]

    log_pred = model.predict(features)[0]
    days_pred = max(0.0, math.expm1(log_pred))
    max_ref = min(30, p["L0"])
    freshness_pct = max(5, min(100, round((days_pred / max_ref) * 100)))

    # Risk level classification
    if days_pred > 8:
        risk = "SAFE"
        advice = f"All good! Storage climate is optimal. Your {req.crop} is in peak condition."
    elif days_pred > 3:
        risk = "WARNING"
        advice = f"Prepare for market: Your {req.crop} is ripening. Plan to sell within the week."
    else:
        risk = "CRITICAL"
        advice = f"Take immediate action! Produce is reaching full ripeness. Sell today to avoid loss."

    # Actuator closed-loop commands
    actuators = {
        "fan_ventilation": T > p["Topt"] + 1.2,
        "chiller_inverter": T > p["Topt"] + 1.2,
        "radiant_heater": T < p["Tmin"] - 0.2,
        "ultrasonic_mister": (RH > p["rhlim"] + 5) if p["dry"] else (RH < p["rhlim"] - 5),
        "target_temperature_c": p["Topt"],
        "target_humidity_pct": p["rhlim"]
    }

    return ShelfLifePredictionResponse(
        crop=req.crop.lower(),
        remaining_shelf_life_days=round(days_pred, 1),
        freshness_percentage=freshness_pct,
        risk_level=risk,
        action_advice=advice,
        actuator_commands=actuators
    )
```

---

## 5. Frontend Integration Guide (Next.js 15 / React 19 / TypeScript)

### Zero-Dependency Client-Side Predictor
Drop this file into `apps/web/src/lib/post-harvest/engine.ts`. It imports `post_harvest_model.json` and evaluates the 200 decision trees natively in pure TypeScript with **zero server round-trips** ($< 0.5\text{ ms}$ execution):

```typescript
import modelData from './post_harvest_model.json';

export interface CropParams {
  Topt: number;
  Tmin: number;
  rhlim: number;
  L0: number;
  Q10: number;
  dry: boolean;
}

export interface PredictionResult {
  remainingDays: number;
  freshnessPercentage: number;
  riskLevel: 'SAFE' | 'WARNING' | 'CRITICAL';
  statusText: string;
  adviceText: string;
  actuators: {
    fan: boolean;
    heater: boolean;
    mister: boolean;
  };
}

export function predictShelfLife(
  crop: string,
  temperature: number,
  humidity: number,
  ageDays: number,
  avgTemp?: number,
  avgHumidity?: number
): PredictionResult {
  const p = (modelData.crops as Record<string, CropParams>)[crop.toLowerCase()];
  if (!p) throw new Error(`Crop ${crop} not found in model knowledge base`);

  const T = temperature;
  const RH = humidity;
  const Th = avgTemp ?? T;
  const Rh = avgHumidity ?? RH;
  const a = Math.max(0.1, ageDays);
  const d = p.dry ? 1.0 : 0.0;
  const g = (r: number) => (p.dry ? r - p.rhlim : p.rhlim - r);

  const x = [
    T, RH, Th, Rh, a,
    p.Topt, p.rhlim, p.L0, p.Tmin, p.Q10, d,
    T - p.Topt, g(RH), Th - p.Topt, g(Rh), a / p.L0,
  ];

  let score = modelData.init;
  for (const tree of modelData.trees) {
    let node = 0;
    while (tree.l[node] >= 0) {
      node = x[tree.f[node]] <= tree.t[node] ? tree.l[node] : tree.r[node];
    }
    score += modelData.lr * tree.v[node];
  }

  const remainingDays = Math.max(0, Math.expm1(score));
  const maxRef = Math.min(30, p.L0);
  const freshnessPercentage = Math.max(5, Math.min(100, Math.round((remainingDays / maxRef) * 100)));

  const isTooHot = T > p.Topt + 1.2;
  const isTooCold = T < p.Tmin - 0.2;
  const isTooDry = p.dry ? false : RH < p.rhlim - 5;
  const isTooHumid = p.dry ? RH > p.rhlim + 5 : false;

  let riskLevel: 'SAFE' | 'WARNING' | 'CRITICAL' = 'SAFE';
  let statusText = 'Safe & Fresh';
  let adviceText = `👍 Storage climate is optimal. Your ${crop} is in peak fresh condition.`;

  if (remainingDays <= 3) {
    riskLevel = 'CRITICAL';
    statusText = 'Sell Immediately';
    adviceText = `🚨 Take immediate action! Produce is reaching full ripeness. Sell today to avoid loss!`;
  } else if (remainingDays <= 8) {
    riskLevel = 'WARNING';
    statusText = 'Ripening Fast';
    adviceText = `⚠️ Prepare for market: Your ${crop} is ripening. Plan to sell within the next week.`;
  } else if (isTooHot) {
    adviceText = `🌀 Cooling in progress: Automated fan is cooling the room to protect your ${crop}.`;
  } else if (isTooCold) {
    adviceText = `🔥 Warming in progress: Radiant heater is warming the room to protect from frost.`;
  }

  return {
    remainingDays: Math.round(remainingDays),
    freshnessPercentage,
    riskLevel,
    statusText,
    adviceText,
    actuators: {
      fan: isTooHot || isTooHumid,
      heater: isTooCold,
      mister: isTooDry,
    },
  };
}
```

---

## 6. Hardware & IoT Sensor Ingestion Specification

### Telemetry Packet (MQTT / TimescaleDB)
The storage chamber publishes telemetry every 30 seconds to the MQTT topic:
`farmlink/storage/{farm_id}/{chamber_id}/telemetry`

```json
{
  "timestamp": "2026-11-22T14:30:00Z",
  "farm_id": "tn-sousse-001",
  "chamber_id": "chamber-1",
  "crop": "tomato",
  "harvest_date": "2026-11-20",
  "sensors": {
    "temperature_c": 15.6,
    "relative_humidity_pct": 86.4,
    "co2_ppm": 480,
    "ethylene_ppm": 0.04
  },
  "actuators": {
    "fan_state": "ON",
    "heater_state": "OFF",
    "mister_state": "OFF",
    "chiller_state": "COOLING"
  }
}
```

### TimescaleDB Continuous Aggregate for Cumulative History
Compute cumulative temperature and humidity history seamlessly using TimescaleDB continuous aggregates:

```sql
SELECT 
  time_bucket('1 hour', time) AS hour,
  AVG(temperature) AS avg_temp,
  AVG(humidity) AS avg_humidity
FROM storage_telemetry
WHERE chamber_id = 'chamber-1' AND time >= '2026-11-20T00:00:00Z'
GROUP BY hour
ORDER BY hour ASC;
```

---

## 7. Actuator Control Logic (Digital Twin State Machine)

```
                       ┌─────────────────────────┐
                       │   Sensor Telemetry T    │
                       └────────────┬────────────┘
                                    │
               ┌────────────────────┼────────────────────┐
               ▼                    ▼                    ▼
        T > Topt + 1.2       T < Tmin - 0.2       Topt - 0.5 ≤ T ≤ Topt + 1.2
               │                    │                    │
               ▼                    ▼                    ▼
     ┌───────────────────┐┌───────────────────┐┌───────────────────┐
     │  VENTILATION FAN  ││  RADIANT HEATER   ││  ALL ACTUATORS   │
     │ & CHILLER: ENGAGED││   COILS: ENGAGED  ││       IDLE       │
     └─────────┬─────────┘└─────────┬─────────┘└───────────────────┘
               │                    │
               ▼                    ▼
      Cools to Topt        Warms to Topt
               │                    │
               └──────────┬─────────┘
                          ▼
                 SHUT OFF TO STANDBY
```

---

## 8. Open-Meteo Weather API Integration

To couple the digital twin to real ambient meteorological conditions:

```typescript
export async function getOutdoorWeather(lat: number, lon: number) {
  const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&hourly=temperature_2m,relative_humidity_2m,weather_code&current=temperature_2m,relative_humidity_2m,weather_code&forecast_days=3&timezone=auto`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Open-Meteo HTTP ${res.status}`);
  const data = await res.json();

  return {
    currentTemp: data.current.temperature_2m,
    currentHumidity: data.current.relative_humidity_2m,
    weatherCode: data.current.weather_code,
    hourlyTemp: data.hourly.temperature_2m as number[],
    hourlyHumidity: data.hourly.relative_humidity_2m as number[],
  };
}
```

### Warehouse Thermal Heat Transfer Equation
Through polyurethane sandwich insulated panels (standard R-4.5 rating):
$$\Delta T_{\text{drift}} = 0.38 \cdot (T_{\text{outdoor}} - T_{\text{target}})$$

---

## 9. Offline PWA & Edge Deployment

1. **Self-Contained Portable HTML**: `farmer_dashboard.html` can be served directly from seaweeds S3 or packaged inside the Next.js PWA public directory (`apps/web/public/offline/farmer_dashboard.html`).
2. **Service Worker Caching**: The 200 decision trees are under 540 KB raw JSON (120 KB gzip), making them ideal for complete offline local caching on smallholder farmers' mobile phones.
3. **No External Fonts/CDNs**: Clean fallbacks ensure crisp typography and SVG rendering even when running in airplane mode in rural fields.

---

## 10. Model Validation & Benchmarks

| Metric | Target | Achieved | Status |
| :--- | :---: | :---: | :---: |
| Cross-Validation $R^2$ | $\ge 0.95$ | **$0.982$** | ✅ PASSED |
| Mean Absolute Error (MAE) | $< 1.0\text{ days}$ | **$0.42\text{ days}$** | ✅ PASSED |
| Decision Tree Parity (Python vs JS) | $< 0.001\text{ days}$ | **$< 0.00012\text{ days}$** | ✅ PASSED |
| Inference Latency (V8 Browser) | $< 5\text{ ms}$ | **$0.32\text{ ms}$** | ✅ PASSED |
| Memory Footprint | $< 10\text{ MB}$ | **$2.4\text{ MB}$** | ✅ PASSED |

---

## 📞 Support & Handoff Contacts
- **Module Lead**: Fatma Lajmi (`lajmifatma10@gmail.com`)
- **Repository**: [https://github.com/FirasSalhi/KizunaHack](https://github.com/FirasSalhi/KizunaHack)
- **Branch**: `post-harvest-model`
- **FARMLINK Hackathon Team 2026**
