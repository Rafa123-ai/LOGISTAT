import os
from datetime import datetime
import streamlit as st
import pandas as pd

from ui_branding import render_header
from pdf_report import make_pdf_report

render_header("Reportes", show_home=True)

base_dir = os.getcwd()
out_dir = os.path.join(base_dir, "OUTPUT")
os.makedirs(out_dir, exist_ok=True)

result = st.session_state.get("result", None)
out_xlsx = st.session_state.get("out_xlsx", None)

if not isinstance(result, dict):
    st.info("Aún no hay resultado. Ve a Planeación y ejecuta primero.")
    st.stop()

resumen = result.get("resumen")
kpis_estado = {}

# Derivar KPIs simples desde el resumen (si está)
if isinstance(resumen, pd.DataFrame) and len(resumen):
    r = resumen.iloc[0].to_dict()
    kpis_estado = {
        "semaforo_general": r.get("semaforo_general"),
        "total_m3": r.get("total_m3"),
        "viajes": r.get("viajes"),
        "ollas_usadas": r.get("ollas_usadas"),
        "alertas": r.get("alertas"),
        "n_criticas": r.get("n_criticas"),
        "n_revisar": r.get("n_revisar"),
    }

st.subheader("Descargas")

c1, c2 = st.columns(2)

with c1:
    if isinstance(out_xlsx, str) and os.path.exists(out_xlsx):
        with open(out_xlsx, "rb") as f:
            st.download_button(
                " Descargar Excel (salida)",
                data=f,
                file_name=os.path.basename(out_xlsx),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="dl_xlsx",
            )
    else:
        st.info("Excel no disponible. Ejecuta Planeación.")

with c2:
    pdf_path = os.path.join(out_dir, f"REPORTE_LOGISTAT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
    if st.button("Generar PDF", use_container_width=True):
        try:
            make_pdf_report(pdf_path, resumen, kpis_estado, out_xlsx)
            st.session_state["last_pdf_path"] = pdf_path
            st.success("PDF generado.")
        except Exception as e:
            st.error(f"Error al generar PDF: {e}")
last_pdf = st.session_state.get("last_pdf_path")
if isinstance(last_pdf, str) and os.path.exists(last_pdf):
    with open(last_pdf, "rb") as f:
        st.download_button(
            "Descargar PDF (último)",
            data=f,
            file_name=os.path.basename(last_pdf),
            mime="application/pdf",
            use_container_width=True,
            key="dl_pdf",
        )

st.divider()
st.subheader("Vista previa")
if isinstance(resumen, pd.DataFrame):
    st.dataframe(resumen, use_container_width=True)










