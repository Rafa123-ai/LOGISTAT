from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, Optional

import pandas as pd
import numpy as np
import streamlit as st

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "templates", "PLAN_V9_TEMPLATE.xlsx")

def _template_schema() -> Dict[str, list[str]]:
    xls = pd.ExcelFile(TEMPLATE_PATH)
    schema: Dict[str, list[str]] = {}
    for sh in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sh, nrows=0)
        schema[sh] = list(df.columns)
    return schema

def _ensure_cols(df: pd.DataFrame | None, cols: list[str]) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame(columns=cols)
    out = df.copy()
    for c in cols:
        if c not in out.columns:
            out[c] = None
    return out[cols]

def _derive_plan_date(result: dict) -> str:
    # Prefer result['plan_date']
    if isinstance(result.get("plan_date"), str) and result.get("plan_date"):
        return result["plan_date"]
    # Try resumen columns containing 'fecha'
    try:
        res = result.get("resumen")
        if res is not None and hasattr(res, "columns") and len(res) > 0:
            for c in res.columns:
                if "fecha" in str(c).lower():
                    v = res.iloc[0][c]
                    if pd.notna(v):
                        return str(pd.to_datetime(v).date())
    except Exception:
        pass
    return datetime.now().strftime("%Y-%m-%d")

def _to_dt(series: pd.Series) -> pd.Series:
    try:
        return pd.to_datetime(series, errors="coerce")
    except Exception:
        return pd.to_datetime(pd.Series([None]*len(series)), errors="coerce")

def _operator_name() -> str:
    # If branding exists, use it; else blank
    try:
        from branding import AUTHOR_NAME
        return AUTHOR_NAME or ""
    except Exception:
        return ""

def _build_plan_operativo(result: dict, cols: list[str]) -> pd.DataFrame:
    pc = result.get("plan_calculado")
    if pc is None or not hasattr(pc, "copy"):
        return pd.DataFrame(columns=cols)
    df = pc.copy()

    # Normalizar columnas existentes a lower para detectar
    col_map = {str(c).lower(): c for c in df.columns}

    def get_any(*names):
        for n in names:
            if n in df.columns:
                return df[n]
            k = n.lower()
            if k in col_map:
                return df[col_map[k]]
        return None

    # Campos base
    id_pedido = get_any("id_pedido", "ID Pedido", "pedido_id")
    viaje = get_any("viaje", "Viaje", "trip_no")
    obra = get_any("obra", "Obra")
    cliente = get_any("cliente", "Cliente")
    m3 = get_any("m3", "Volumen (m3)", "volumen_m3")
    localidad = get_any("localidad", "Localidad")
    unidad = get_any("unidad", "Unidad")

    hora_req_llegada = get_any("hora_solicitada", "Hora requerida llegada", "req_arrival")
    hora_req_salida = get_any("hora_salida_req", "Hora requerida salida", "req_departure")

    t_ida = get_any("dist_min", "Tiempo ida (min)", "t_ida", "t_ida_min")
    t_desc = get_any("descarga_min", "Tiempo descarga (min)", "t_desc", "t_desc_min")
    t_reg = get_any("regreso_min", "Tiempo regreso (min)", "t_reg", "t_reg_min")

    metodo = get_any("metodo_estimacion", "Método estimación", "est_method")
    condicion = get_any("condicion", "Condición")
    ini_carga = get_any("t_carga_ini", "Inicio carga", "load_start")
    sal_planta = get_any("t_salida_planta", "Salida planta", "depart_planta")
    lleg_obra = get_any("t_llegada_obra", "Llegada a obra", "arrive_obra")
    fin_desc = get_any("t_fin_descarga", "Fin descarga", "unload_end")
    reg_planta = get_any("t_regreso_planta", "Regreso planta", "return_planta")

    late_min = get_any("tardanza_min", "Minutos de retraso", "late_min")
    frag_min = get_any("fraguado_min", "Minutos fraguado", "frag_min", "fraguado_proxy_min")
    alertas = get_any("alertas", "Alertas")
    hora_carga = get_any("hora_carga", "hora_carga")
    status_trip = get_any("status_trip", "status_trip")

    # Construir salida con columnas EXACTAS del template
    out = pd.DataFrame(index=df.index)

    fill = {
        "ID Pedido": id_pedido,
        "Viaje": viaje,
        "Obra": obra,
        "Cliente": cliente,
        "Volumen (m3)": m3,
        "Hora requerida llegada": hora_req_llegada,
        "Hora requerida salida": hora_req_salida,
        "Tiempo ida (min)": t_ida,
        "Tiempo descarga (min)": t_desc,
        "Tiempo regreso (min)": t_reg,
        "Método estimación": metodo,
        "Unidad": unidad,
        "Condición": condicion,
        "Inicio carga": ini_carga,
        "Salida planta": sal_planta,
        "Llegada a obra": lleg_obra,
        "Fin descarga": fin_desc,
        "Regreso planta": reg_planta,
        "Minutos de retraso": late_min,
        "Minutos fraguado": frag_min,
        "Alertas": alertas,
        "hora_carga": hora_carga,
        "status_trip": status_trip,
        "Operador": _operator_name(),
    }

    for c in cols:
        if c in fill and fill[c] is not None:
            out[c] = fill[c]
        elif c in df.columns:
            out[c] = df[c]
        else:
            out[c] = None

    return out[cols]

def _build_semaforo(df_plan: pd.DataFrame, by: str, cols: list[str]) -> pd.DataFrame:
    """Construye semáforo por pedido u obra sin duplicar columnas (bug fix: Obra ya existe)."""
    if df_plan is None or df_plan.empty:
        return pd.DataFrame(columns=cols)

    late = pd.to_numeric(df_plan.get("Minutos de retraso"), errors="coerce")
    frag = pd.to_numeric(df_plan.get("Minutos fraguado"), errors="coerce")

    base = df_plan.copy()
    base["__late"] = late.fillna(0)
    base["__frag"] = frag.fillna(0)
    base["__m3"] = pd.to_numeric(base.get("Volumen (m3)"), errors="coerce").fillna(0)
    base["__alerts"] = base.get("Alertas").astype(str).fillna("")

    # Armado de agregaciones evitando colisión con el índice (p.ej. by='Obra')
    agg = {
        "m3_total": ("__m3", "sum"),
        "atraso_max": ("__late", "max"),
        "frag_max": ("__frag", "max"),
        "tiene_alertas": ("__alerts", lambda s: int(any((str(x).strip() not in ["", "nan", "None"]) for x in s))),
    }

    # Solo agregar columnas descriptivas si NO son la llave de agrupación
    if by != "Obra" and "Obra" in base.columns:
        agg["Obra"] = ("Obra", lambda s: s.dropna().iloc[0] if len(s.dropna()) else None)
    if by != "Cliente" and "Cliente" in base.columns:
        agg["Cliente"] = ("Cliente", lambda s: s.dropna().iloc[0] if len(s.dropna()) else None)

    g = base.groupby(by, dropna=False).agg(**agg).reset_index()

    # Normalizar nombre de la llave
    if by == "ID Pedido":
        g = g.rename(columns={by: "ID Pedido"})
    elif by == "Obra":
        g = g.rename(columns={by: "Obra"})
    else:
        g = g.rename(columns={by: by})

    # Status semáforo (umbral inicial, ajustable luego)
    def status_row(r):
        if r.get("frag_max", 0) >= 30 or r.get("atraso_max", 0) >= 20:
            return "ROJO"
        if r.get("frag_max", 0) >= 15 or r.get("atraso_max", 0) >= 10 or r.get("tiene_alertas", 0) == 1:
            return "AMARILLO"
        return "VERDE"

    g["status"] = g.apply(status_row, axis=1)
    g["Operador"] = _operator_name()

    # Alinear columnas exactas
    out = pd.DataFrame()
    for c in cols:
        out[c] = g[c] if c in g.columns else None
    return out[cols]

def _build_riesgo(df_plan: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    if df_plan is None or df_plan.empty:
        return pd.DataFrame(columns=cols)

    df = df_plan.copy()

    # Convertir tiempos
    dt_depart = _to_dt(df.get("Salida planta"))
    dt_return = _to_dt(df.get("Regreso planta"))
    df["__depart"] = dt_depart
    df["__return"] = dt_return

    # gap_sig_min: diferencia entre siguiente salida y regreso actual por Unidad
    df["gap_sig_min"] = np.nan
    if "Unidad" in df.columns:
        df = df.sort_values(["Unidad","__depart"], kind="mergesort")
        for unidad, g in df.groupby("Unidad", dropna=False):
            idx = g.index.to_list()
            dep = g["__depart"]
            ret = g["__return"]
            # next departure - current return
            nxt = dep.shift(-1)
            gap = (nxt - ret).dt.total_seconds() / 60.0
            df.loc[idx, "gap_sig_min"] = gap.values

    # m3_hora: volumen en la hora de salida
    df["__m3"] = pd.to_numeric(df.get("Volumen (m3)"), errors="coerce").fillna(0)
    if "__depart" in df.columns:
        hour = df["__depart"].dt.floor("H")
        df["__hour"] = hour
        m3_h = df.groupby("__hour")["__m3"].transform("sum")
        df["m3_hora"] = m3_h
    else:
        df["m3_hora"] = np.nan

    late = pd.to_numeric(df.get("Minutos de retraso"), errors="coerce").fillna(0)
    frag = pd.to_numeric(df.get("Minutos fraguado"), errors="coerce").fillna(0)
    gap = pd.to_numeric(df.get("gap_sig_min"), errors="coerce")

    # Score simple (ajustable): retraso + frag + penalización por gap negativo o muy corto
    score = late*1.0 + frag*0.8
    score = score + np.where(gap.notna() & (gap < 0), 25, 0)
    score = score + np.where(gap.notna() & (gap < 10) & (gap >= 0), 10, 0)

    df["Score Riesgo"] = score.round(2)

    def nivel(s):
        if s >= 40: return "ALTO"
        if s >= 20: return "MEDIO"
        return "BAJO"
    df["Nivel Riesgo"] = df["Score Riesgo"].apply(nivel)

    # Causa (principal)
    causas=[]
    for i in df.index:
        c=[]
        if float(late.loc[i])>=20: c.append("RETRASO")
        if float(frag.loc[i])>=30: c.append("FRAGUADO")
        gi = gap.loc[i]
        if pd.notna(gi) and gi < 0: c.append("SOLAPAMIENTO")
        elif pd.notna(gi) and gi < 10: c.append("GAP_CORTO")
        causas.append(";".join(c) if c else "NORMAL")
    df["Causa"] = causas
    df["Operador"] = _operator_name()

    # Alinear columnas
    out = pd.DataFrame()
    for c in cols:
        if c in df.columns:
            out[c] = df[c]
        else:
            out[c] = None
    return out[cols]

def _build_recomendaciones(df_plan: pd.DataFrame, df_alertas: pd.DataFrame | None, cols: list[str]) -> pd.DataFrame:
    recs=[]
    op=_operator_name()
    # Reglas sencillas (ingeniería v1)
    if df_plan is None or df_plan.empty:
        recs.append(("SISTEMA", "Cargar PLAN válido", "No hay datos de planeación para analizar.", op))
    else:
        late = pd.to_numeric(df_plan.get("Minutos de retraso"), errors="coerce").fillna(0)
        frag = pd.to_numeric(df_plan.get("Minutos fraguado"), errors="coerce").fillna(0)
        n_late = int((late>10).sum())
        n_frag = int((frag>15).sum())
        if n_late>0:
            recs.append(("OPERACIÁ“N", "Ajustar secuencia de carga", f"Hay {n_late} viajes con retraso > 10 min. Revisar ventanas por obra y disponibilidad de unidades.", op))
        if n_frag>0:
            recs.append(("CALIDAD", "Revisar riesgo de fraguado", f"Hay {n_frag} viajes con fraguado > 15 min. Considerar priorizar obras lejanas o aumentar colchón de tiempos.", op))
        if df_alertas is not None and not df_alertas.empty:
            recs.append(("CONTROL", "Atender alertas críticas", f"Se generaron {len(df_alertas)} alertas. Priorizar ROJAS y revisar semáforos.", op))
        recs.append(("SISTEMA", "Guardar evidencia", "Descargar Excel PlanV9 completo y por hoja para trazabilidad.", op))

    out=pd.DataFrame(recs, columns=["tipo","recomendacion","detalle","Operador"])
    return _ensure_cols(out, cols)

def _build_incidencias(cols: list[str]) -> pd.DataFrame:
    # Se deja vacío pero con columnas
    return pd.DataFrame(columns=cols)

def _build_impacto(plan_oper: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    if plan_oper is None or plan_oper.empty:
        return pd.DataFrame(columns=cols)
    # crear base minimal
    df=plan_oper.copy()
    # columnas base disponibles
    def col(name): return df[name] if name in df.columns else None

    base=pd.DataFrame()
    base["pedido_id"] = col("ID Pedido")
    base["trip_no"] = col("Viaje")

    # Map to REPLAN fields
    map_replan = {
        "obra_REPLAN":"Obra",
        "cliente_REPLAN":"Cliente",
        "m3_REPLAN":"Volumen (m3)",
        "req_arrival_REPLAN":"Hora requerida llegada",
        "req_departure_REPLAN":"Hora requerida salida",
        "t_ida_REPLAN":"Tiempo ida (min)",
        "t_desc_REPLAN":"Tiempo descarga (min)",
        "t_reg_REPLAN":"Tiempo regreso (min)",
        "est_method_REPLAN":"Método estimación",
        "unidad_REPLAN":"Unidad",
        "condicion_REPLAN":"Condición",
        "load_start_REPLAN":"Inicio carga",
        "depart_planta_REPLAN":"Salida planta",
        "arrive_obra_REPLAN":"Llegada a obra",
        "unload_end_REPLAN":"Fin descarga",
        "return_planta_REPLAN":"Regreso planta",
        "late_min_REPLAN":"Minutos de retraso",
        "frag_min_REPLAN":"Minutos fraguado",
        "alerts_REPLAN":"Alertas",
        "hora_carga_REPLAN":"hora_carga",
        "status_trip_REPLAN":"status_trip",
    }
    map_orig = {k.replace("_REPLAN","_ORIG"): v for k,v in map_replan.items()}

    for dest, src in map_replan.items():
        base[dest]=col(src)
    for dest, src in map_orig.items():
        base[dest]=col(src)

    base["Operador"]=_operator_name()

    out=pd.DataFrame()
    for c in cols:
        out[c]=base[c] if c in base.columns else None
    return out[cols]

def run_planv9_exports(base_dir: str, result: dict, out_xlsx: str | None, plan_date: Optional[str] = None) -> None:
    if not os.path.exists(TEMPLATE_PATH):
        return

    schema = _template_schema()
    out_dir = os.path.join(base_dir, "OUTPUT")
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plan_date_s = plan_date or _derive_plan_date(result)

    # Build sheets
    sheets: Dict[str, pd.DataFrame] = {}

    # Core
    plan_oper = _build_plan_operativo(result, schema["PLAN_OPERATIVO"])
    sheets["PLAN_OPERATIVO"] = plan_oper
    sheets["ALERTAS"] = _ensure_cols(result.get("alertas_plan") if hasattr(result.get("alertas_plan"), "copy") else None, schema["ALERTAS"])
    sheets["RESUMEN_EJECUTIVO"] = _ensure_cols(result.get("resumen") if hasattr(result.get("resumen"), "copy") else None, schema["RESUMEN_EJECUTIVO"])

    # Engineering layers
    sheets["RECOMENDACIONES"] = _build_recomendaciones(plan_oper, sheets["ALERTAS"], schema["RECOMENDACIONES"])
    sheets["SEMAFORO_PEDIDOS"] = _build_semaforo(plan_oper, by="ID Pedido", cols=schema["SEMAFORO_PEDIDOS"])
    sheets["SEMAFORO_OBRAS"] = _build_semaforo(plan_oper, by="Obra", cols=schema["SEMAFORO_OBRAS"])
    sheets["RIESGO_OPERATIVO"] = _build_riesgo(plan_oper, schema["RIESGO_OPERATIVO"])
    sheets["INCIDENCIAS"] = _build_incidencias(schema["INCIDENCIAS"])

    # REPLAN v1: por ahora espejo del operativo (base para siguiente fase)
    sheets["PLAN_REPLAN"] = plan_oper.copy() if not plan_oper.empty else pd.DataFrame(columns=schema["PLAN_REPLAN"])
    sheets["PLAN_REPLAN"] = _ensure_cols(sheets["PLAN_REPLAN"], schema["PLAN_REPLAN"])

    sheets["IMPACTO_REPLAN"] = _build_impacto(plan_oper, schema["IMPACTO_REPLAN"])
    # Riesgo replan = recalcular sobre plan_replan
    sheets["RIESGO_REPLAN"] = _build_riesgo(sheets["PLAN_REPLAN"], schema["RIESGO_REPLAN"])

    # Full workbook
    full_path = os.path.join(out_dir, f"PLAN_V9_COMPLETO_{plan_date_s}_{stamp}.xlsx")
    with pd.ExcelWriter(full_path, engine="openpyxl") as w:
        for sh in schema.keys():
            sheets.get(sh, pd.DataFrame(columns=schema[sh])).to_excel(w, sheet_name=sh[:31], index=False)
    st.session_state["out_planv9_full"] = full_path

    # Per-sheet
    indiv = {}
    for sh in schema.keys():
        pth = os.path.join(out_dir, f"PLANV9_{sh}_{plan_date_s}_{stamp}.xlsx")
        with pd.ExcelWriter(pth, engine="openpyxl") as w:
            sheets.get(sh, pd.DataFrame(columns=schema[sh])).to_excel(w, sheet_name=sh[:31], index=False)
        indiv[sh] = pth
    st.session_state["out_planv9_sheets"] = indiv




