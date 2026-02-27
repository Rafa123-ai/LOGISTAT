LOGISTAT (V11.x mejorado) — Streamlit multipage

Mejoras incluidas:
- Persistencia de parámetros en config.json (PLANTA_LAT/LON, capacidad, ollas).
- Botón para autodetectar planta como promedio de coordenadas del PLAN (temporal).
- Bloquea ejecución si PLANTA_LAT/LON están en 0,0 (evita distancias irreales).
- Dashboard con mapa y gráficas rápidas.

Ejecución:
  pip install streamlit pandas numpy reportlab openpyxl
  streamlit run app.py


Branding institucional:
- Logo en assets/logo_cagsa.jpg
- Datos en branding.py (empresa, dirección, maps, versión, autor)
- INFO se agrega al Excel de salida.
