import streamlit as st
from ui_branding import render_header
from wrap_core import render as render_core

render_header("Planeación", show_home=True)

render_core()





