from __future__ import annotations
import os
from datetime import datetime
import streamlit as st

def run_global_exports(base_dir: str, out_xlsx: str | None) -> None:
    if not out_xlsx or not isinstance(out_xlsx, str) or not os.path.exists(out_xlsx):
        return
    if not os.path.exists(os.path.join(base_dir, "exports_industrial.py")):
        return
    try:
        from exports_industrial import export_full_workbook, export_single_sheet, list_schema_sheets
        out_dir = os.path.join(base_dir, "OUTPUT")
        os.makedirs(out_dir, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        full_path = os.path.join(out_dir, f"LOGISTAT_EXPORT_GLOBAL_{stamp}.xlsx")
        export_full_workbook(out_xlsx, full_path)
        st.session_state["out_global_full"] = full_path

        indiv = {}
        for sh in list_schema_sheets():
            pth = os.path.join(out_dir, f"GLOBAL_{sh}_{stamp}.xlsx")
            export_single_sheet(out_xlsx, sh, pth)
            indiv[sh] = pth
        st.session_state["out_global_sheets"] = indiv
    except Exception as e:
        print("Global exports error:", e)




