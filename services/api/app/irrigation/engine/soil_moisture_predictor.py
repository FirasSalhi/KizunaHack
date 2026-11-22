"""Soil-moisture forecasting at 1 h / 6 h / 24 h versus persistence.

* Chronological split (no shuffling); the test block is strictly later than train/validation.
* Gaps: the series is put on a regular hourly grid; any lag/target window touching a missing hour is dropped (no interpolation across gaps).
* Models: persistence (y_hat = y_t), and ridge regression on lagged VWC + hour-of-day, solved with numpy (coefficients exportable as JSON).
* Selection rule: the ridge model is kept for a horizon only if it beats persistence on the held-out test MAE by `min_improvement`
  (default 5 %). Otherwise persistence is retained and reported as the winner. Nothing is claimed beyond that test block.
"""
from __future__ import annotations

import json
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

HORIZONS = (1, 6, 24)
LAGS = (0, 1, 2, 3, 6, 12, 24)


def to_hourly(df: pd.DataFrame, time_col: str, value_col: str) -> pd.Series:
    s = df[[time_col, value_col]].dropna().copy()
    s[time_col] = pd.to_datetime(s[time_col], utc=True)
    s = s.sort_values(time_col).drop_duplicates(time_col)
    h = s.set_index(time_col)[value_col].astype(float).resample("1h").mean()
    return h


def make_supervised(h: pd.Series, horizon: int) -> pd.DataFrame:
    X = pd.DataFrame({f"lag{l}": h.shift(l) for l in LAGS})
    X["hour_sin"] = np.sin(2 * np.pi * h.index.hour / 24); X["hour_cos"] = np.cos(2 * np.pi * h.index.hour / 24)
    X["y"] = h.shift(-horizon); X["persistence"] = h
    return X.dropna()


def chronological_split(n: int, train=0.6, val=0.2):
    a, b = int(n * train), int(n * (train + val))
    return slice(0, a), slice(a, b), slice(b, n)


def _fit_ridge(X: np.ndarray, y: np.ndarray, alpha: float):
    mu, sd = X.mean(0), X.std(0); sd[sd == 0] = 1
    Z = (X - mu) / sd; ym = y.mean()
    w = np.linalg.solve(Z.T @ Z + alpha * np.eye(Z.shape[1]), Z.T @ (y - ym))
    return {"mu": mu, "sd": sd, "w": w, "b": ym}


def _pred(m, X): return ((X - m["mu"]) / m["sd"]) @ m["w"] + m["b"]


def evaluate(h: pd.Series, horizons=HORIZONS, min_improvement: float = 0.05, min_rows: int = 200,
             alphas=(0.1, 1.0, 10.0, 100.0)) -> Dict:
    """Train/validate/test per horizon. Returns metrics, the selected model per horizon and export-ready parameters."""
    out = {"horizons": {}, "n_hours_total": int(len(h)), "n_missing_hours": int(h.isna().sum()), "selection_rule": f"ridge kept only if test MAE improves on persistence by >= {min_improvement:.0%}"}
    for H in horizons:
        D = make_supervised(h, H)
        if len(D) < min_rows:
            out["horizons"][f"{H}h"] = {"status": "INSUFFICIENT_DATA", "rows": int(len(D)), "winner": "persistence", "note": f"need >= {min_rows} gap-free rows"}; continue
        feats = [c for c in D.columns if c not in ("y", "persistence")]
        tr, va, te = chronological_split(len(D))
        Xtr, ytr, Xva, yva, Xte, yte = D[feats].values[tr], D["y"].values[tr], D[feats].values[va], D["y"].values[va], D[feats].values[te], D["y"].values[te]
        best = None
        for a in alphas:
            m = _fit_ridge(Xtr, ytr, a); mae = np.mean(np.abs(_pred(m, Xva) - yva))
            if best is None or mae < best[0]: best = (mae, a, m)
        _, alpha, m = best
        m = _fit_ridge(np.vstack([Xtr, Xva]), np.concatenate([ytr, yva]), alpha)   # refit on train+val, test untouched
        ml, pers = _pred(m, Xte), D["persistence"].values[te]
        mae_ml, mae_p = float(np.mean(np.abs(ml - yte))), float(np.mean(np.abs(pers - yte)))
        rmse_ml, rmse_p = float(np.sqrt(np.mean((ml - yte) ** 2))), float(np.sqrt(np.mean((pers - yte) ** 2)))
        win = "ridge" if mae_ml <= mae_p * (1 - min_improvement) else "persistence"
        out["horizons"][f"{H}h"] = {"status": "OK", "rows": int(len(D)), "test_rows": int(te.stop - te.start), "test_start": str(D.index[te][0]),
                                      "alpha": alpha, "mae_ridge": mae_ml, "mae_persistence": mae_p, "rmse_ridge": rmse_ml, "rmse_persistence": rmse_p,
                                      "improvement_vs_persistence": 1 - mae_ml / mae_p if mae_p > 0 else None, "winner": win,
                                      "model": {"features": feats, "mu": m["mu"].tolist(), "sd": m["sd"].tolist(), "w": m["w"].tolist(), "b": float(m["b"])} if win == "ridge" else None}
    return out


def predict(model_json: Dict, horizon_key: str, recent_hourly: pd.Series) -> float:
    """Predict using exported metadata; falls back to persistence when persistence is the stored winner."""
    spec = model_json["horizons"][horizon_key]
    last = float(recent_hourly.dropna().iloc[-1])
    if spec.get("winner") != "ridge" or not spec.get("model"):
        return last
    m = spec["model"]
    if recent_hourly.iloc[-25:].isna().any() or len(recent_hourly) < 25:
        raise ValueError("need 25 gap-free recent hours for the ridge model; use persistence")
    h = recent_hourly
    row = [float(h.shift(l).iloc[-1]) for l in LAGS] + [np.sin(2*np.pi*h.index[-1].hour/24), np.cos(2*np.pi*h.index[-1].hour/24)]
    z = (np.array(row) - np.array(m["mu"])) / np.array(m["sd"])
    return float(z @ np.array(m["w"]) + m["b"])


def save_metadata(result: Dict, path: str, extra: Optional[Dict] = None):
    meta = {"model_type": "per-horizon ridge (numpy) vs persistence", "data_provenance": "set by caller", **(extra or {}), **result}
    with open(path, "w", encoding="utf-8") as f: json.dump(meta, f, indent=1, default=float)
