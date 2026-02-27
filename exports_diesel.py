from __future__ import annotations
import os
from datetime import datetime
from typing import Dict
import pandas as pd
import streamlit as st

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "templates", "DIESEL_TEMPLATE.xlsx")

DIESEL_SHEETS = [
    "DIESEL_DETALLE",
    "DIESEL_RANKING",
    "DIESEL_ALERTAS",
    "DIESEL_SEMAFORO",
    "DIESEL_ROBO_ALERTAS",
    "DIESEL_MES_VS_MES",
    "DIESEL_EF_RUTA",
]

def _template_fact_cols() -> list[str]:
    try:
        df0 = pd.read_excel(TEMPLATE_PATH, sheet_name="fact_revolvedoras", nrows=0)
        return list(df0.columns)
    except Exception:
        return ["fecha","unidad_id","horas","km","litros","m3","viajes","tipo_equipo"]

def _empty_df(cols: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=cols)

def run_diesel_exports(base_dir: str, result: dict, out_xlsx: str | None, plan_date: str | None, diesel_uploaded: bool) -> None:
    if not os.path.exists(TEMPLATE_PATH):
        return
    out_dir = os.path.join(base_dir, "OUTPUT")
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plan_date_s = plan_date or datetime.now().strftime("%Y-%m-%d")

    fact_cols = _template_fact_cols()

    def ensure(df, cols):
        if df is None or not hasattr(df, "copy"):
            return _empty_df(cols)
        out = df.copy()
        for c in cols:
            if c not in out.columns:
                out[c] = None
        return out[cols]

    # engine frames (si existen)
    sheets: Dict[str, pd.DataFrame] = {
        "DIESEL_DETALLE": ensure(result.get("diesel_detalle"), fact_cols),
        "DIESEL_RANKING": result.get("diesel_ranking") if hasattr(result.get("diesel_ranking"),"copy") else _empty_df(["unidad_id","litros","km","m3","viajes","rend_km_l","rend_l_m3"]),
        "DIESEL_ALERTAS": result.get("diesel_alertas") if hasattr(result.get("diesel_alertas"),"copy") else _empty_df(["fecha","unidad_id","tipo_alerta","detalle","nivel"]),
        "DIESEL_SEMAFORO": result.get("diesel_semaforo") if hasattr(result.get("diesel_semaforo"),"copy") else _empty_df(["unidad_id","status","motivo"]),
        "DIESEL_ROBO_ALERTAS": result.get("diesel_robo_alertas") if hasattr(result.get("diesel_robo_alertas"),"copy") else _empty_df(["fecha","unidad_id","litros","delta_litros","motivo"]),
        "DIESEL_MES_VS_MES": result.get("diesel_mes_vs_mes") if hasattr(result.get("diesel_mes_vs_mes"),"copy") else _empty_df(["mes","litros","km","m3","viajes"]),
        "DIESEL_EF_RUTA": result.get("diesel_ef_ruta") if hasattr(result.get("diesel_ef_ruta"),"copy") else _empty_df(["localidad","km","litros","m3","viajes","eficiencia"]),
    }

    full_path = os.path.join(out_dir, f"DIESEL_REPORTE_{plan_date_s}_{stamp}.xlsx")
    with pd.ExcelWriter(full_path, engine="openpyxl") as w:
        for sh in DIESEL_SHEETS:
            sheets[sh].to_excel(w, sheet_name=sh[:31], index=False)
    st.session_state["out_diesel_full"] = full_path

    indiv = {}
    for sh in DIESEL_SHEETS:
        pth = os.path.join(out_dir, f"{sh}_{plan_date_s}_{stamp}.xlsx")
        with pd.ExcelWriter(pth, engine="openpyxl") as w:
            sheets[sh].to_excel(w, sheet_name=sh[:31], index=False)
        indiv[sh]=pth
    st.session_state["out_diesel_sheets"] = indiv

    st.session_state["diesel_frames"] = sheets
    st.session_state["diesel_uploaded"] = bool(diesel_uploaded)




