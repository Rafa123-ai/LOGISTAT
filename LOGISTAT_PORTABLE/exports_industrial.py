from __future__ import annotations
import os
from typing import Dict, Any, Tuple

import pandas as pd

from export_schema import SCHEMA

def _ensure_columns(df: pd.DataFrame | None, cols: list[str]) -> pd.DataFrame:
    if df is None:
        out = pd.DataFrame(columns=cols)
        return out
    out = df.copy()
    # agregar faltantes
    for c in cols:
        if c not in out.columns:
            out[c] = None
    # ordenar y dejar extras al final (si quieres estricto, quita extras)
    out = out[cols + [c for c in out.columns if c not in cols]]
    # si quieres SOLO columnas del esquema, usa:
    # out = out[cols]
    return out

def read_engine_output(plan_excel_path: str) -> Dict[str, pd.DataFrame]:
    """Lee el Excel principal generado por el motor y regresa dfs por hoja."""
    xls = pd.ExcelFile(plan_excel_path)
    out: Dict[str, pd.DataFrame] = {}
    for sh in xls.sheet_names:
        try:
            out[sh] = pd.read_excel(xls, sheet_name=sh)
        except Exception:
            continue
    return out

def export_full_workbook(plan_excel_path: str, out_path: str) -> str:
    """Genera un Excel con TODAS las hojas del esquema (aunque vacías)."""
    sheets = read_engine_output(plan_excel_path)
    with pd.ExcelWriter(out_path, engine="openpyxl") as w:
        for sh, cols in SCHEMA.items():
            df = _ensure_columns(sheets.get(sh), cols)
            df.to_excel(w, sheet_name=sh[:31], index=False)
    return out_path

def export_single_sheet(plan_excel_path: str, sheet_name: str, out_path: str) -> str:
    sheets = read_engine_output(plan_excel_path)
    cols = SCHEMA.get(sheet_name)
    if cols is None:
        # exportar lo que haya
        df = sheets.get(sheet_name, pd.DataFrame())
    else:
        df = _ensure_columns(sheets.get(sheet_name), cols)
    with pd.ExcelWriter(out_path, engine="openpyxl") as w:
        df.to_excel(w, sheet_name=sheet_name[:31], index=False)
    return out_path

def list_schema_sheets() -> list[str]:
    return list(SCHEMA.keys())




