from __future__ import annotations
import json, os
from typing import Any, Dict

DEFAULT_CONFIG = {
    "PLANTA_LAT": 0.0,
    "PLANTA_LON": 0.0,
    "PLANTA_CAP_M3_TURNO": 230.0,
    "N_OLLAS_DISPONIBLES": 11,
    "CAPACIDAD_OLLA_M3": 7.0,
}

def _config_path(base_dir: str) -> str:
    return os.path.join(base_dir, "config.json")

def load_config(base_dir: str) -> Dict[str, Any]:
    path = _config_path(base_dir)
    if not os.path.exists(path):
        return dict(DEFAULT_CONFIG)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        out = dict(DEFAULT_CONFIG)
        out.update({k: data.get(k, out[k]) for k in out.keys()})
        return out
    except Exception:
        return dict(DEFAULT_CONFIG)

def save_config(base_dir: str, cfg: Dict[str, Any]) -> None:
    path = _config_path(base_dir)
    safe = {k: cfg.get(k, DEFAULT_CONFIG[k]) for k in DEFAULT_CONFIG.keys()}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(safe, f, ensure_ascii=False, indent=2)




