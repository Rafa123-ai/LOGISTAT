"""
LOGISTAT Engine (V11.x) €” backend puro (sin código en top-level)

Este módulo está diseñado para:
- ser importado desde Streamlit (multipage) sin ejecutar nada al importar
- exponer `RULES` y `run_logistat_v11(...)` como API estable

IMPORTANTE:
- No debe haber cálculos usando variables como `plan` fuera de funciones.
"""

from __future__ import annotations

import os
import json
import math
import hashlib
from dataclasses import dataclass
from datetime import date, timedelta, datetime
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd


# =========================================================
# Reglas / parámetros (editable desde UI vía overrides)
# =========================================================
RULES: Dict[str, Any] = {
    # Planta
    "PLANTA_CAP_M3_TURNO": 230.0,   # m3 / turno
    "TURNO_HORAS": 12.0,

    # Tiempos planta (min)
    "T_ACOMODO_MIN": 5.0,
    "T_CARGA_MIN": 15.0,
    "T_MUESTREO_MIN": 7.0,

    # Obra
    "T_MAX_RETRASO_LLEGADA_MIN": 20.0,  # 15€“20 -> se usa 20
    "T_MAX_DESCARGA_MIN": 40.0,
    "T_MAX_FRAGUADO_MIN": 90.0,         # tiempo total permitido en olla (proxy)

    # Bombeo
    "T_BOMBA_MIN_MIN": 15.0,
    "T_BOMBA_MAX_MIN": 20.0,

    # Intervalo máximo entre ollas en obra
    "T_MAX_GAP_ENTRE_OLLAS_OBRA_MIN": 30.0,

    # Flota
    "N_OLLAS_DISPONIBLES": 11,
    "CAPACIDAD_OLLA_M3": 7.0,

    # Parámetros de velocidad (fallback si no hay históricos suficientes)
    "VEL_KMH_URBANA": 28.0,
    "VEL_KMH_CARRETERA": 45.0,

    # Distancia para clasificar obra como "lejana" (percentil)
    "DIST_LEJANA_PCTL": 0.70,

    # Coordenadas de planta (AJUSTA EN CONFIG/UI si aplica)
    "PLANTA_LAT": 0.0,
    "PLANTA_LON": 0.0,
}

# Catálogo / condición de unidades (revolvedoras)
UNIDAD_CONDICION: Dict[str, str] = {
    "R-03": "MENOR AL REGULAR",
    "R-06": "REGULAR",
    "R-08": "REGULAR",
    "R-11": "BUEN ESTADO",
    "R-12": "BUEN ESTADO",
    "R-13": "BUEN ESTADO",
    "R-14": "BUEN ESTADO",
    "R-15": "BUEN ESTADO",
    "R-16": "BUEN ESTADO",
    "R-17": "BUEN ESTADO",
    "R-18": "EXCELENTE ESTADO",
    "R-19": "EXCELENTE ESTADO",
    "R-20": "EXCELENTE ESTADO",
}
UNIDAD_FACTOR_REND: Dict[str, float] = {
    "R-03": 0.80,
    "R-06": 0.85,
    "R-08": 0.85,
    "R-11": 0.90,
    "R-12": 0.90,
    "R-13": 0.90,
    "R-14": 0.90,
    "R-15": 0.90,
    "R-16": 0.90,
    "R-17": 0.90,
    "R-18": 1.00,
    "R-19": 1.00,
    "R-20": 1.00,
}
COND_RANK: Dict[str, int] = {
    "MENOR AL REGULAR": 0,
    "REGULAR": 1,
    "BUEN ESTADO": 2,
    "EXCELENTE ESTADO": 3,
}


# =========================================================
# Helpers generales
# =========================================================
def _norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def _attach_default_date(ts: pd.Timestamp, default_day: date) -> pd.Timestamp:
    # Si ya tiene fecha distinta a 1970-01-01, se respeta.
    if isinstance(ts, pd.Timestamp) and ts is not pd.NaT:
        try:
            if ts.date() != pd.Timestamp("1970-01-01").date():
                return ts
        except Exception:
            pass
        # sólo hora (o fecha inválida): anexar default_day
        return pd.Timestamp(datetime.combine(default_day, ts.to_pydatetime().time()))
    return pd.NaT


def _parse_hora_solicitada(plan: pd.DataFrame) -> pd.Series:
    s = pd.to_datetime(plan["hora_solicitada"], errors="coerce")
    # Si parece ser sólo HH:MM en texto
    if s.isna().mean() > 0.5:
        s2 = pd.to_datetime(plan["hora_solicitada"].astype(str), format="%H:%M", errors="coerce")
        s = s2

    default_day = date.today() + timedelta(days=1)
    s = s.apply(lambda t: _attach_default_date(t, default_day) if pd.notna(t) else pd.NaT)
    return s


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    return float(R * c)


def estimate_travel_min(dist_km: float, urbana: bool = True) -> float:
    vel = float(RULES["VEL_KMH_URBANA"] if urbana else RULES["VEL_KMH_CARRETERA"])
    if vel <= 0:
        vel = 30.0
    return float((dist_km / vel) * 60.0)


def unload_time_min(bombeable: bool) -> float:
    if bool(bombeable):
        return float(np.random.uniform(float(RULES["T_BOMBA_MIN_MIN"]), float(RULES["T_BOMBA_MAX_MIN"])))
    return float(min(25.0, float(RULES["T_MAX_DESCARGA_MIN"])))


def _safe_float(x, default=0.0) -> float:
    try:
        v = float(x)
        if math.isnan(v):
            return float(default)
        return v
    except Exception:
        return float(default)


# =========================================================
# Planeación (core)
# =========================================================
def expand_to_trips(plan_df: pd.DataFrame) -> pd.DataFrame:
    cap = float(RULES["CAPACIDAD_OLLA_M3"])
    rows = []
    for _, r in plan_df.iterrows():
        m3 = _safe_float(r.get("m3", 0.0), 0.0)
        if m3 <= 0:
            continue
        n = int(math.ceil(m3 / cap))
        for k in range(1, n + 1):
            trip = r.to_dict()
            trip["trip_idx"] = k
            trip["trip_m3"] = min(cap, m3 - (k - 1) * cap)
            trip["trip_id"] = f"{r.get('obra','OBRA')}_{k:02d}"
            rows.append(trip)
    return pd.DataFrame(rows)


def _build_fleet_catalog() -> pd.DataFrame:
    catalog = pd.DataFrame({
        "unidad_id": list(UNIDAD_CONDICION.keys()),
        "condicion": [UNIDAD_CONDICION[u] for u in UNIDAD_CONDICION.keys()],
        "factor_rend": [UNIDAD_FACTOR_REND.get(u, 0.9) for u in UNIDAD_CONDICION.keys()],
    })
    catalog["cond_rank"] = catalog["condicion"].map(COND_RANK).fillna(1).astype(int)
    # Selección de N ollas
    n = int(RULES["N_OLLAS_DISPONIBLES"])
    catalog = catalog.sort_values(["cond_rank", "unidad_id"], ascending=[False, True]).head(n).reset_index(drop=True)
    return catalog


def schedule_trips(trips: pd.DataFrame, fleet: pd.DataFrame) -> pd.DataFrame:
    if trips.empty:
        return pd.DataFrame()

    trips = trips.copy()
    # Orden de atención
    trips = trips.sort_values(["hora_solicitada_dt", "es_lejana", "dist_km"], ascending=[True, False, False]).reset_index(drop=True)

    planta_process = float(RULES["T_ACOMODO_MIN"]) + float(RULES["T_CARGA_MIN"]) + float(RULES["T_MUESTREO_MIN"])

    # Estado de flota: disponibilidad en planta
    t0 = pd.to_datetime(trips["hora_solicitada_dt"].min())
    fleet_state = {u: t0 for u in fleet["unidad_id"]}
    # Cola de planta (un solo punto)
    plant_available = t0

    out = []
    for _, t in trips.iterrows():
        is_far = bool(t.get("es_lejana", False))
        cand = fleet.copy()
        cand["available"] = cand["unidad_id"].map(fleet_state)

        if is_far:
            cand["score"] = cand["cond_rank"] * 10 + cand["factor_rend"] * 5
            cand = cand.sort_values(["score", "available"], ascending=[False, True])
        else:
            cand = cand.sort_values(["available", "cond_rank"], ascending=[True, False])

        chosen = cand.iloc[0]
        unidad = chosen["unidad_id"]
        unidad_ready = fleet_state[unidad]

        load_start = max(plant_available, unidad_ready)
        load_end = load_start + pd.Timedelta(minutes=planta_process)

        t_viaje = float(t.get("t_viaje_min_est", 0.0)) / float(chosen.get("factor_rend", 1.0))
        arrive = load_end + pd.Timedelta(minutes=t_viaje)

        dmin = unload_time_min(t.get("bombeable", False))
        dmin = float(min(dmin, float(RULES["T_MAX_DESCARGA_MIN"])))
        depart = arrive + pd.Timedelta(minutes=dmin)

        back = depart + pd.Timedelta(minutes=t_viaje)

        plant_available = load_end
        fleet_state[unidad] = back

        delay_min = (arrive - pd.Timestamp(t["hora_solicitada_dt"])).total_seconds() / 60.0
        frag_min = (depart - load_end).total_seconds() / 60.0  # proxy

        row = {k: t.get(k) for k in trips.columns}
        row.update({
            "unidad_id": unidad,
            "condicion": chosen.get("condicion", ""),
            "factor_rend": float(chosen.get("factor_rend", 1.0)),
            "t_planta_min": planta_process,
            "t_viaje_min": t_viaje,
            "t_descarga_min": dmin,
            "t_retorno_min": t_viaje,
            "t_total_ciclo_min": planta_process + 2 * t_viaje + dmin,
            "tardanza_min": float(delay_min),
            "fraguado_proxy_min": float(frag_min),
            "t_carga_ini": load_start,
            "t_carga_fin": load_end,
            "t_llegada_obra": arrive,
            "t_salida_obra": depart,
            "t_regreso_planta": back,
        })
        out.append(row)

    return pd.DataFrame(out)


def validate_business_rules(plan_df: pd.DataFrame, sched_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    alerts = []

    total_m3 = float(plan_df["m3"].sum()) if len(plan_df) else 0.0

    # 1) Capacidad planta turno
    if total_m3 > float(RULES["PLANTA_CAP_M3_TURNO"]):
        alerts.append((
            "PLANTA_CAPACIDAD",
            f"Volumen total {total_m3:.1f} m3 excede capacidad {RULES['PLANTA_CAP_M3_TURNO']} m3/turno",
            "CRITICO",
        ))

    if sched_df.empty:
        alerts_df = pd.DataFrame(alerts, columns=["codigo", "descripcion", "nivel"])
        resumen = pd.DataFrame([{
            "fecha_plan": (date.today() + timedelta(days=1)),
            "total_m3": total_m3,
            "viajes": 0,
            "ollas_usadas": 0,
            "alertas": int(len(alerts_df)),
            "n_criticas": int((alerts_df["nivel"] == "CRITICO").sum()) if len(alerts_df) else 0,
            "n_revisar": int((alerts_df["nivel"] == "REVISAR").sum()) if len(alerts_df) else 0,
            "semaforo_general": "CRITICO" if len(alerts_df) else "OK",
            "engine_version": "engine_v11_streamlit",
        }])
        return alerts_df, resumen

    # 2) Retraso máximo llegada
    bad_delay = sched_df[sched_df["tardanza_min"] > float(RULES["T_MAX_RETRASO_LLEGADA_MIN"])]
    for _, r in bad_delay.iterrows():
        alerts.append((
            "RETRASO_OBRA",
            f"{r['trip_id']} unidad {r['unidad_id']} tardanza {float(r['tardanza_min']):.1f} min (> {RULES['T_MAX_RETRASO_LLEGADA_MIN']})",
            "CRITICO",
        ))

    # 3) Descarga máxima
    bad_unload = sched_df[sched_df["t_descarga_min"] > float(RULES["T_MAX_DESCARGA_MIN"])]
    for _, r in bad_unload.iterrows():
        alerts.append((
            "DESCARGA_MAX",
            f"{r['trip_id']} descarga {float(r['t_descarga_min']):.1f} min (> {RULES['T_MAX_DESCARGA_MIN']})",
            "CRITICO",
        ))

    # 4) Fraguado máximo (proxy)
    bad_frag = sched_df[sched_df["fraguado_proxy_min"] > float(RULES["T_MAX_FRAGUADO_MIN"])]
    for _, r in bad_frag.iterrows():
        alerts.append((
            "FRAGUADO_MAX",
            f"{r['trip_id']} fraguado proxy {float(r['fraguado_proxy_min']):.1f} min (> {RULES['T_MAX_FRAGUADO_MIN']})",
            "CRITICO",
        ))

    # 5) Gap entre ollas por obra
    tmp = sched_df.sort_values(["obra", "t_llegada_obra"]).copy()
    tmp["gap_min"] = tmp.groupby("obra")["t_llegada_obra"].diff().dt.total_seconds() / 60.0
    bad_gap = tmp[tmp["gap_min"] > float(RULES["T_MAX_GAP_ENTRE_OLLAS_OBRA_MIN"])]
    for _, r in bad_gap.iterrows():
        alerts.append((
            "GAP_OBRA",
            f"Obra {r['obra']} gap {float(r['gap_min']):.1f} min (> {RULES['T_MAX_GAP_ENTRE_OLLAS_OBRA_MIN']})",
            "CRITICO",
        ))

    # 6) Planta idle
    s = sched_df.sort_values("t_carga_ini")[["t_carga_ini", "t_carga_fin"]].copy()
    s["idle_min"] = (s["t_carga_ini"] - s["t_carga_fin"].shift(1)).dt.total_seconds() / 60.0
    idle = s[s["idle_min"] > 0].copy()
    for _, r in idle.iterrows():
        alerts.append(("PLANTA_IDLE", f"Planta sin cargar ~{float(r['idle_min']):.1f} min", "REVISAR"))

    alerts_df = pd.DataFrame(alerts, columns=["codigo", "descripcion", "nivel"])

    # Semáforo general
    sem = "OK"
    if (alerts_df["nivel"] == "CRITICO").any():
        sem = "CRITICO"
    elif len(alerts_df) > 0:
        sem = "REVISAR"

    fecha_plan = pd.to_datetime(sched_df["hora_solicitada_dt"].min()).date()
    resumen = pd.DataFrame([{
        "fecha_plan": fecha_plan,
        "total_m3": total_m3,
        "viajes": int(len(sched_df)),
        "ollas_usadas": int(sched_df["unidad_id"].nunique()),
        "alertas": int(len(alerts_df)),
        "n_criticas": int((alerts_df["nivel"] == "CRITICO").sum()),
        "n_revisar": int((alerts_df["nivel"] == "REVISAR").sum()),
        "semaforo_general": sem,
        "engine_version": "engine_v11_streamlit",
    }])
    return alerts_df, resumen


# =========================================================
# Diesel (opcional) €” ingestion + KPIs
# =========================================================
def _safe_div(a, b):
    a = np.asarray(a, dtype="float64")
    b = np.asarray(b, dtype="float64")
    return np.where(b == 0, np.nan, a / b)


def build_kpis_day(fact_day: pd.DataFrame) -> pd.DataFrame:
    df = fact_day.copy()
    df["unidad_id"] = df["unidad_id"].astype(str).str.strip()
    for c in ["litros", "viajes", "horas", "km", "m3"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    df["km_por_m3"] = _safe_div(df["km"], df["m3"])
    df["lts_por_km"] = _safe_div(df["litros"], df["km"])
    df["m3_por_km"] = _safe_div(df["m3"], df["km"])
    df["km_por_lt"] = _safe_div(df["km"], df["litros"])
    df["m3_por_lt"] = _safe_div(df["m3"], df["litros"])
    return df.sort_values(["unidad_id"]).reset_index(drop=True)


def build_ranking(det: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    d = det[(det["km"] > 0) & (det["litros"] > 0)].copy()
    if d.empty:
        return pd.DataFrame(columns=[
            "segmento", "unidad_id", "lts_por_km", "km_por_lt", "m3_por_lt",
            "km_por_m3", "litros", "km", "m3", "viajes", "horas"
        ])
    best = d.sort_values("lts_por_km").head(top_n).copy()
    best["segmento"] = f"TOP {top_n} (mejor: menor L/km)"
    worst = d.sort_values("lts_por_km", ascending=False).head(top_n).copy()
    worst["segmento"] = f"BOTTOM {top_n} (peor: mayor L/km)"
    cols = ["segmento", "unidad_id", "lts_por_km", "km_por_lt", "m3_por_lt", "km_por_m3", "litros", "km", "m3", "viajes", "horas"]
    return pd.concat([best[cols], worst[cols]], ignore_index=True)


def build_alerts_day(det: pd.DataFrame) -> pd.DataFrame:
    d = det.copy()
    d["flag_litros_sin_km"] = (d["litros"] > 0) & (d["km"] == 0)
    d["flag_km_sin_litros"] = (d["km"] > 0) & (d["litros"] == 0)
    d["flag_m3_sin_viajes"] = (d["m3"] > 0) & (d["viajes"] == 0)
    d["flag_viajes_sin_m3"] = (d["viajes"] > 0) & (d["m3"] == 0)

    def iqr_flags(x: pd.Series):
        x = x.replace([np.inf, -np.inf], np.nan).dropna()
        if len(x) < 4:
            return None, None
        q1, q3 = x.quantile(0.25), x.quantile(0.75)
        iqr = q3 - q1
        return q1 - 1.5 * iqr, q3 + 1.5 * iqr

    lo, hi = iqr_flags(d["lts_por_km"])
    d["flag_outlier_lts_por_km"] = False
    if lo is not None:
        d["flag_outlier_lts_por_km"] = (d["lts_por_km"] < lo) | (d["lts_por_km"] > hi)

    lo2, hi2 = iqr_flags(d["km_por_lt"])
    d["flag_outlier_km_por_lt"] = False
    if lo2 is not None:
        d["flag_outlier_km_por_lt"] = (d["km_por_lt"] < lo2) | (d["km_por_lt"] > hi2)

    rule_map = {
        "flag_litros_sin_km": "Litros > 0 pero Km = 0",
        "flag_km_sin_litros": "Km > 0 pero Litros = 0",
        "flag_m3_sin_viajes": "m3 > 0 pero Viajes = 0",
        "flag_viajes_sin_m3": "Viajes > 0 pero m3 = 0",
        "flag_outlier_lts_por_km": "Outlier estadístico en L/km (IQR)",
        "flag_outlier_km_por_lt": "Outlier estadístico en Km/L (IQR)",
    }

    rows = []
    base_cols = ["unidad_id", "litros", "km", "m3", "viajes", "horas", "lts_por_km", "km_por_lt", "m3_por_lt", "km_por_m3"]
    for flag, desc in rule_map.items():
        sub = d[d[flag] == True]
        if len(sub):
            tmp = sub[base_cols].copy()
            tmp["alerta"] = desc
            tmp["regla"] = flag
            rows.append(tmp)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=base_cols + ["alerta", "regla"])


def build_semaforo(det: pd.DataFrame, alerts: pd.DataFrame) -> pd.DataFrame:
    crit_rules = {"flag_litros_sin_km", "flag_km_sin_litros", "flag_m3_sin_viajes", "flag_viajes_sin_m3"}
    out_rules = {"flag_outlier_lts_por_km", "flag_outlier_km_por_lt"}

    if alerts.empty:
        out = det[["unidad_id"]].drop_duplicates().copy()
        out["semaforo"] = "OK"
        out["num_alertas"] = 0
        out["num_criticas"] = 0
        out["num_outliers"] = 0
        out["motivos"] = ""
        return out

    a = alerts.copy()
    a["is_critica"] = a["regla"].isin(crit_rules)
    a["is_outlier"] = a["regla"].isin(out_rules)

    g = (
        a.groupby("unidad_id", as_index=False)
         .agg(
            num_alertas=("regla", "count"),
            num_criticas=("is_critica", "sum"),
            num_outliers=("is_outlier", "sum"),
            motivos=("alerta", lambda s: " | ".join(sorted(set(map(str, s))))),
         )
    )
    g["semaforo"] = "REVISAR"
    g.loc[g["num_criticas"] > 0, "semaforo"] = "CRITICO"

    all_units = det[["unidad_id"]].drop_duplicates()
    out = all_units.merge(g, on="unidad_id", how="left")
    out["semaforo"] = out["semaforo"].fillna("OK")
    out["num_alertas"] = out["num_alertas"].fillna(0).astype(int)
    out["num_criticas"] = out["num_criticas"].fillna(0).astype(int)
    out["num_outliers"] = out["num_outliers"].fillna(0).astype(int)
    out["motivos"] = out["motivos"].fillna("")
    order = {"CRITICO": 0, "REVISAR": 1, "OK": 2}
    out["__o"] = out["semaforo"].map(order)
    out = out.sort_values(["__o", "num_alertas", "unidad_id"], ascending=[True, False, True]).drop(columns="__o")
    return out


def _file_md5(path: str, chunk_size: int = 2**20) -> str:
    md5 = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            md5.update(chunk)
    return md5.hexdigest()


def _read_daily_template(path: str):
    fact = pd.read_excel(path, sheet_name="fact_revolvedoras")
    dim = pd.read_excel(path, sheet_name="dim_revolvedora")

    fact["unidad_id"] = fact["unidad_id"].astype(str).str.strip()
    fact["fecha"] = pd.to_datetime(fact["fecha"]).dt.date

    for c in ["litros", "viajes", "horas", "km", "m3"]:
        fact[c] = pd.to_numeric(fact[c], errors="coerce").fillna(0)
    fact["viajes"] = fact["viajes"].astype(int)

    # Quita filas sin actividad
    fact = fact[(fact[["litros", "viajes", "horas", "km", "m3"]].sum(axis=1) > 0)].copy()

    dim["unidad_id"] = dim["unidad_id"].astype(str).str.strip()
    if "alias_unidad" not in dim.columns:
        dim["alias_unidad"] = ""
    if "activo" not in dim.columns:
        dim["activo"] = True
    dim = dim[["unidad_id", "alias_unidad", "activo"]].drop_duplicates()

    return fact, dim


def _load_parquet_or_empty(path: str, cols):
    if os.path.exists(path):
        return pd.read_parquet(path)
    return pd.DataFrame(columns=cols)


def _load_hash_log(path: str):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_hash_log(path: str, log_dict: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(log_dict, f, ensure_ascii=False, indent=2)


def run_diesel_ingestion_app(diesel_template_path: str, base_dir: str, verbose: bool = False):
    """Ingiere un Excel diario (dim_revolvedora + fact_revolvedoras) con control por hash."""
    diesel_db_dir = os.path.join(base_dir, "DB", "DIESEL")
    os.makedirs(diesel_db_dir, exist_ok=True)
    fact_pq = os.path.join(diesel_db_dir, "fact_consumo_revolvedora_diario.parquet")
    dim_pq = os.path.join(diesel_db_dir, "dim_revolvedora.parquet")
    log_json = os.path.join(diesel_db_dir, "ingestion_log_hash.json")

    hist_fact = _load_parquet_or_empty(fact_pq, ["fecha", "unidad_id", "litros", "viajes", "horas", "km", "m3"])
    hist_dim = _load_parquet_or_empty(dim_pq, ["unidad_id", "alias_unidad", "activo"])
    log_hash = _load_hash_log(log_json)

    name = os.path.basename(diesel_template_path)
    h = _file_md5(diesel_template_path)
    if name in log_hash and log_hash[name] == h:
        return hist_fact, hist_dim, {"ingested": False, "file": name}

    fact_new, dim_new = _read_daily_template(diesel_template_path)

    dim_final = pd.concat([hist_dim, dim_new], ignore_index=True)
    dim_final["unidad_id"] = dim_final["unidad_id"].astype(str).str.strip()
    dim_final = dim_final.drop_duplicates(subset=["unidad_id"], keep="last").reset_index(drop=True)

    fact_final = pd.concat([hist_fact, fact_new], ignore_index=True)
    fact_final["unidad_id"] = fact_final["unidad_id"].astype(str).str.strip()
    fact_final["fecha"] = pd.to_datetime(fact_final["fecha"]).dt.date
    fact_final = (
        fact_final.sort_values(["fecha", "unidad_id"])
        .drop_duplicates(subset=["fecha", "unidad_id"], keep="last")
        .reset_index(drop=True)
    )

    dim_final.to_parquet(dim_pq, index=False)
    fact_final.to_parquet(fact_pq, index=False)

    log_hash[name] = h
    _save_hash_log(log_json, log_hash)

    if verbose:
        print("Diesel: ingestado:", name)

    return fact_final, dim_final, {"ingested": True, "file": name}


# =========================================================
# API principal para la app
# =========================================================
def run_logistat_v11(
    plan_path: str,
    diesel_template_path: Optional[str],
    base_dir: str,
    rules_overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Ejecuta planeación + validación de reglas + (opcional) diesel KPIs.

    Retorna dict con llaves:
      - resumen: DataFrame
      - plan_calculado: DataFrame
      - alertas_plan: DataFrame
      - plan_excel: str (ruta)
      - diesel: dict|None
    """
    # Copia local de reglas (evita que una corrida deje RULES mutadas permanentemente)
    rules_local = dict(RULES)
    if rules_overrides:
        for k, v in rules_overrides.items():
            rules_local[k] = v

    # Aplicar a RULES global durante esta ejecución (para usar helpers que consultan RULES)
    RULES.update(rules_local)

    out_dir = os.path.join(base_dir, "OUTPUT")
    os.makedirs(out_dir, exist_ok=True)

    # ---- Carga plan
    plan_raw = pd.read_excel(plan_path)
    plan = _norm_cols(plan_raw)

    required = ["cliente", "obra", "hora_solicitada", "lat", "lon", "localidad", "m3"]
    missing = [c for c in required if c not in plan.columns]
    if missing:
        raise ValueError(f"Faltan columnas obligatorias en el plan: {missing}")

    if "bombeable" not in plan.columns:
        plan["bombeable"] = False

    plan["hora_solicitada_dt"] = _parse_hora_solicitada(plan)
    if plan["hora_solicitada_dt"].isna().any():
        raise ValueError("No pude interpretar 'hora_solicitada'. Usa HH:MM o fecha-hora.")

    plan["m3"] = pd.to_numeric(plan["m3"], errors="coerce").fillna(0.0)
    plan = plan[plan["m3"] > 0].copy()

    # ---- Distancias + tiempos estimados
    planta_lat = float(RULES.get("PLANTA_LAT", 0.0))
    planta_lon = float(RULES.get("PLANTA_LON", 0.0))

    plan["lat"] = pd.to_numeric(plan["lat"], errors="coerce")
    plan["lon"] = pd.to_numeric(plan["lon"], errors="coerce")
    if plan["lat"].isna().any() or plan["lon"].isna().any():
        raise ValueError("Hay coordenadas inválidas (lat/lon). Revisa el PLAN.")

    plan["dist_km"] = plan.apply(lambda r: haversine_km(planta_lat, planta_lon, float(r["lat"]), float(r["lon"])), axis=1)

    thr = float(plan["dist_km"].quantile(float(RULES["DIST_LEJANA_PCTL"]))) if len(plan) else 0.0
    plan["es_lejana"] = plan["dist_km"] >= thr
    plan["t_viaje_min_est"] = plan["dist_km"].apply(lambda d: estimate_travel_min(float(d), urbana=True))

    # ---- Expandir a viajes + programar
    trips = expand_to_trips(plan)
    if trips.empty:
        raise ValueError("El PLAN no generó viajes (revisa m3).")

    fleet = _build_fleet_catalog()
    sched = schedule_trips(trips, fleet)

    # ---- Validar reglas
    alerts_df, resumen_df = validate_business_rules(plan, sched)

    # ---- Sugerencias (retardante)
    thr_frag = 0.8 * float(RULES["T_MAX_FRAGUADO_MIN"])
    if not sched.empty and "fraguado_proxy_min" in sched.columns:
        sched["sugerir_retardante"] = sched["fraguado_proxy_min"] > thr_frag

    # ---- Export Excel principal
    fecha_plan = pd.to_datetime(sched["hora_solicitada_dt"].min()).date()
    out_xlsx = os.path.join(out_dir, f"PLAN_V11_{fecha_plan}.xlsx")
    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as writer:
        plan.to_excel(writer, index=False, sheet_name="PLAN_INPUT")
        sched.to_excel(writer, index=False, sheet_name="PLAN_CALCULADO")
        alerts_df.to_excel(writer, index=False, sheet_name="ALERTAS")
        resumen_df.to_excel(writer, index=False, sheet_name="RESUMEN")

    diesel_obj = None
    if diesel_template_path:
        try:
            fact_hist, dim_hist, info = run_diesel_ingestion_app(diesel_template_path, base_dir, verbose=False)
            _fecha = fecha_plan
            diesel_day = fact_hist.copy()
            if len(diesel_day):
                diesel_day = diesel_day[pd.to_datetime(diesel_day["fecha"]).dt.date == _fecha].copy()

            if diesel_day.empty:
                diesel_obj = {"ok": False, "msg": f"No hay datos diesel para el día {_fecha}", "ingestion": info}
            else:
                det = build_kpis_day(diesel_day)
                als = build_alerts_day(det)
                sem = build_semaforo(det, als)
                rnk = build_ranking(det, top_n=5)
                diesel_obj = {
                    "ok": True,
                    "fecha": _fecha,
                    "detalle": det,
                    "alertas": als,
                    "semaforo": sem,
                    "ranking": rnk,
                    "ingestion": info,
                }

                # Anexa al Excel del plan
                with pd.ExcelWriter(out_xlsx, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
                    det.to_excel(writer, index=False, sheet_name="DIESEL_DETALLE")
                    rnk.to_excel(writer, index=False, sheet_name="DIESEL_RANKING")
                    als.to_excel(writer, index=False, sheet_name="DIESEL_ALERTAS")
                    sem.to_excel(writer, index=False, sheet_name="DIESEL_SEMAFORO")
        except Exception as e:
            diesel_obj = {"ok": False, "msg": f"Error Diesel: {e}"}

    return {
        "resumen": resumen_df,
        "plan_calculado": sched,
        "alertas_plan": alerts_df,
        "plan_excel": out_xlsx,
        "diesel": diesel_obj,
        "rules_used": dict(RULES),
    }




