import streamlit as st

st.set_page_config(
    page_title="LOGISTAT",
    page_icon="static/logo-192.png",
    layout="wide"
)

st.markdown(
    '''
    <link rel="manifest" href="/static/manifest.json">
    ''',
    unsafe_allow_html=True,
)
import streamlit as st

st.set_page_config(
    page_title="LOGISTAT",
    page_icon="static/logo-192.png",
    layout="wide"
)

st.markdown(
    '''
    <link rel="manifest" href="/static/manifest.json">
    ''',
    unsafe_allow_html=True,
)











import streamlit as st

st.set_page_config(
    page_title="LOGISTAT",
    page_icon="static/logo-192.png",
    layout="wide"
)

st.markdown(
    """
    <link rel="manifest" href="/static/manifest.json">
    """,
    unsafe_allow_html=True,
)


APP_BUILD = 'BRANDED-1.0'
import streamlit as st
from branding import COMPANY_NAME, LOGISTAT_VERSION, AUTHOR_NAME, AUTHOR_ROLE
from datetime import datetime
from ui_branding import render_header, hide_sidebar

st.set_page_config(
    page_title="LOGISTAT - V11.x",
    layout="wide",
    initial_sidebar_state="collapsed",
)
hide_sidebar()
render_header("Inicio", show_home=False)

st.caption(f"Build: {APP_BUILD}")
st.caption(f"{LOGISTAT_VERSION} · {COMPANY_NAME} · Elaboró: {AUTHOR_NAME} · {AUTHOR_ROLE} · {datetime.now().strftime('%Y-%m-%d')}")


st.subheader("Menú principal")

r1c1, r1c2, r1c3 = st.columns(3)
with r1c1:
    if st.button("🚚 Planeación", use_container_width=True):
        st.switch_page("pages/1_Planeacion.py")
with r1c2:
    if st.button("Dashboard", use_container_width=True):
        st.switch_page("pages/2_Dashboard.py")
with r1c3:
    if st.button("Condicionantes", use_container_width=True):
        st.switch_page("pages/3_Condicionantes.py")

r2c1, r2c2, r2c3 = st.columns(3)
with r2c1:
    if st.button("Diésel", use_container_width=True):
        st.switch_page("pages/4_Diesel.py")
with r2c2:
    if st.button("Exportación", use_container_width=True):
        st.switch_page("pages/5_Exportacion.py")
with r2c3:
    if st.button("Reportes", use_container_width=True):
        st.switch_page("pages/6_Reportes.py")

st.info("Este build usa tu motor logistat_engine.py (V11.x).")







