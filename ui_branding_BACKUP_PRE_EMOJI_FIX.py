import os
import streamlit as st
from datetime import datetime
from branding import COMPANY_NAME, ADDRESS, MAPS_URL, LOGISTAT_VERSION, AUTHOR_NAME, AUTHOR_ROLE

def hide_sidebar():
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {display: none;}
        [data-testid="stSidebarNav"] {display: none;}
        </style>
        """,
        unsafe_allow_html=True,
    )

def render_brand_block(show_version: bool = True):
    logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo_cagsa.jpg")
    c1, c2 = st.columns([0.18, 0.82], vertical_alignment="center")
    with c1:
        if os.path.exists(logo_path):
            st.image(logo_path, use_container_width=True)
    with c2:
        st.markdown(f"### {COMPANY_NAME}")
        st.caption(ADDRESS)
        st.markdown(f"[ðŸ“ Ver ubicación en Google Maps]({MAPS_URL})")
        if show_version:
            st.caption(f"{LOGISTAT_VERSION} · Elaboró: {AUTHOR_NAME} · {AUTHOR_ROLE} · Fecha: {datetime.now().strftime('%Y-%m-%d')}")
    st.divider()

def render_header(title: str, show_home: bool = True):
    # Encabezado institucional + navegación
    render_brand_block(show_version=True)

    c1, c2 = st.columns([0.75, 0.25])
    with c1:
        st.markdown(f"## {title}")
    with c2:
        if show_home and st.button("ðŸ  Inicio", use_container_width=True):
            st.switch_page("app.py")




