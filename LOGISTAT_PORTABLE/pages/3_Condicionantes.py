import streamlit as st
from ui_branding import render_header
from logistat_engine import RULES

render_header("Condicionantes", show_home=True)

st.info("Este módulo ya puede usarse para ajustar RULES desde UI (si decides extenderlo).")
st.write("RULES actuales (solo lectura):")
st.json(RULES)




