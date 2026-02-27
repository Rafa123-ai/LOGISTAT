import streamlit as st
from ui_branding import render_header
import os

render_header("Exportación", show_home=True)

st.subheader("Descargas")

tabs = st.tabs(["Global", "Producción (PlanV9)", "Diésel"])

def dl_button(label, path, key):
    if isinstance(path, str) and os.path.exists(path):
        with open(path, "rb") as f:
            st.download_button(
                label,
                data=f,
                file_name=os.path.basename(path),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key=key,
            )
        return True
    return False

with tabs[0]:
    st.caption("Reporte global (estructura industrial).")
    dl_button("¬‡ï¸ Descargar Global COMPLETO", st.session_state.get("out_global_full"), "dl_global_full")

    sheets = st.session_state.get("out_global_sheets", {})
    if sheets:
        sh = st.selectbox("Hoja global", options=list(sheets.keys()), key="sel_global")
        dl_button(f"¬‡ï¸ Descargar {sh}", sheets.get(sh), f"dl_global_{sh}")
    else:
        st.info("Ejecuta Planeación para generar el global.")

with tabs[1]:
    st.caption("Reporte Producción con estructura PlanV9 (Excel completo y por hoja).")
    dl_button("¬‡ï¸ Descargar PlanV9 COMPLETO", st.session_state.get("out_planv9_full"), "dl_planv9_full")

    sheets = st.session_state.get("out_planv9_sheets", {})
    if sheets:
        sh = st.selectbox("Hoja PlanV9", options=list(sheets.keys()), key="sel_planv9")
        dl_button(f"¬‡ï¸ Descargar {sh}", sheets.get(sh), f"dl_planv9_{sh}")
    else:
        st.info("Ejecuta Planeación para generar PlanV9.")

with tabs[2]:
    st.caption("Reporte Diésel. Se genera aunque no cargues archivo (saldrá vacío si no hay datos).")
    dl_button("¬‡ï¸ Descargar Diésel COMPLETO", st.session_state.get("out_diesel_full"), "dl_diesel_full")

    sheets = st.session_state.get("out_diesel_sheets", {})
    if sheets:
        sh = st.selectbox("Hoja Diésel", options=list(sheets.keys()), key="sel_diesel")
        dl_button(f"¬‡ï¸ Descargar {sh}", sheets.get(sh), f"dl_diesel_{sh}")
    else:
        st.info("Ejecuta Planeación para generar Diésel.")




