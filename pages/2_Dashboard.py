import streamlit as st
from ui_branding import render_header
import pandas as pd

render_header("Dashboard", show_home=True)

result = st.session_state.get("result")
if not isinstance(result, dict):
    st.info("Aún no hay resultado. Ve a Planeación y ejecuta primero.")
    st.stop()

resumen = result.get("resumen")
alertas = result.get("alertas_plan")
plan_calc = result.get("plan_calculado")
diesel = result.get("diesel")

# KPIs principales
if isinstance(resumen, pd.DataFrame) and len(resumen):
    r = resumen.iloc[0].to_dict()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Semáforo", r.get("semaforo_general", ""))
    c2.metric("Total m3", f"{float(r.get('total_m3', 0)):.1f}")
    c3.metric("Viajes", int(r.get("viajes", 0)))
    c4.metric("Ollas usadas", int(r.get("ollas_usadas", 0)))
else:
    st.warning("No hay RESUMEN disponible.")

st.divider()

# Mapa
st.subheader("Mapa de obras")
try:
    if isinstance(plan_calc, pd.DataFrame) and {"lat","lon"}.issubset(set(plan_calc.columns)):
        mdf = plan_calc.copy()
        mdf["lat"] = pd.to_numeric(mdf["lat"], errors="coerce")
        mdf["lon"] = pd.to_numeric(mdf["lon"], errors="coerce")
        mdf = mdf.dropna(subset=["lat","lon"])
        if len(mdf):
            st.map(mdf[["lat","lon"]].head(2000))
        else:
            st.info("Sin coordenadas válidas para mostrar en mapa.")
    else:
        st.info("El plan calculado no trae lat/lon.")
except Exception as e:
    st.info(f"No se pudo dibujar mapa: {e}")

st.divider()

# Gráficas rápidas (si existen columnas esperadas)
st.subheader("Distribuciones operativas")
if isinstance(plan_calc, pd.DataFrame) and len(plan_calc):
    cA, cB = st.columns(2)
    with cA:
        if "dist_km" in plan_calc.columns:
            st.write("Distancia (km)")
            st.bar_chart(plan_calc["dist_km"].clip(lower=0).head(200))
        elif "dist_km" in plan_calc.columns:
            st.write("Distancia (km)")
            st.line_chart(plan_calc["dist_km"].head(200))
        else:
            st.info("No hay dist_km en plan_calculado.")
    with cB:
        if "tardanza_min" in plan_calc.columns:
            st.write("Tardanza (min)")
            st.line_chart(plan_calc["tardanza_min"].head(200))
        else:
            st.info("No hay tardanza_min en plan_calculado.")

st.divider()
c1, c2 = st.columns(2)
with c1:
    st.subheader("Alertas")
    if isinstance(alertas, pd.DataFrame):
        st.dataframe(alertas, use_container_width=True, height=320)
    else:
        st.write(alertas)

with c2:
    st.subheader("Plan calculado (vista)")
    if isinstance(plan_calc, pd.DataFrame):
        st.dataframe(plan_calc.head(250), use_container_width=True, height=320)
    else:
        st.write(plan_calc)

st.divider()
st.subheader("Diésel (si se cargó template)")
if isinstance(diesel, dict) and diesel.get("ok") is True:
    st.success(f"Diesel OK €” fecha {diesel.get('fecha')}")
    t1, t2 = st.columns(2)
    with t1:
        st.write("Semáforo unidades")
        st.dataframe(diesel.get("semaforo"), use_container_width=True, height=260)
    with t2:
        st.write("Ranking (top/bottom)")
        st.dataframe(diesel.get("ranking"), use_container_width=True, height=260)

    with st.expander("Alertas diésel"):
        st.dataframe(diesel.get("alertas"), use_container_width=True)
    with st.expander("Detalle diésel"):
        st.dataframe(diesel.get("detalle"), use_container_width=True)
elif isinstance(diesel, dict) and diesel:
    st.warning(diesel.get("msg", "Diésel no disponible."))
else:
    st.info("No se cargó template de Diésel.")




