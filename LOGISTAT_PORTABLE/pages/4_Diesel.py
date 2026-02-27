import streamlit as st
from ui_branding import render_header

render_header("Diésel", show_home=True)

frames = st.session_state.get("diesel_frames")
uploaded = st.session_state.get("diesel_uploaded", False)

if frames is None:
    st.info("Aún no hay reporte de diésel. Ejecuta Planeación (se generará aunque no cargues diésel).")
else:
    if not uploaded:
        st.warning("No se cargó archivo de diésel: se muestran plantillas vacías (estructura oficial).")

    for name, df in frames.items():
        st.subheader(name)
        st.dataframe(df, use_container_width=True)




