from __future__ import annotations

import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from branding import COMPANY_NAME, ADDRESS, MAPS_URL, LOGISTAT_VERSION, AUTHOR_NAME, AUTHOR_ROLE

def _register_font():
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                pdfmetrics.registerFont(TTFont("LOGISTAT_FONT", p))
                return "LOGISTAT_FONT"
            except Exception:
                pass
    return "Helvetica"

def make_pdf_report(pdf_path: str, resumen_df, kpis_estado: dict, out_xlsx: str | None):
    font_name = _register_font()
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter
    c.setFont(font_name, 11)

    y = height - 40

    def draw_line(text, x=40, dy=15, size=11):
        nonlocal y
        s = "" if text is None else str(text)
        c.setFont(font_name, size)
        c.drawString(x, y, s)
        y -= dy
        if y < 70:
            c.showPage()
            c.setFont(font_name, 11)
            y = height - 40

    # Logo + encabezado institucional
    logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo_cagsa.jpg")
    if os.path.exists(logo_path):
        try:
            img = ImageReader(logo_path)
            c.drawImage(img, 40, height - 110, width=70, height=70, mask='auto')
        except Exception:
            pass

    c.setFont(font_name, 14)
    c.drawString(120, height - 55, COMPANY_NAME)

    c.setFont(font_name, 10)
    c.drawString(120, height - 73, ADDRESS)

    c.setFont(font_name, 10)
    c.drawString(120, height - 90, f"{LOGISTAT_VERSION} · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    c.drawString(120, height - 105, f"Elaboró: {AUTHOR_NAME} · {AUTHOR_ROLE}")

    # Link
    c.setFont(font_name, 10)
    link_text = "Ubicación (Google Maps)"
    c.drawString(120, height - 120, link_text + f": {MAPS_URL}")
    try:
        c.linkURL(MAPS_URL, (120, height - 122, 520, height - 108), relative=0)
    except Exception:
        pass

    y = height - 150

    draw_line("REPORTE LOGISTAT", size=12, dy=18)
    draw_line("")

    draw_line("=== KPIs ===", size=11)
    if isinstance(kpis_estado, dict):
        for k, v in kpis_estado.items():
            draw_line(f"{k}: {v}")
    else:
        draw_line("No hay KPIs disponibles")

    draw_line("")
    draw_line("=== RESUMEN ===")

    try:
        if resumen_df is not None and len(resumen_df) > 0:
            cols = list(resumen_df.columns)
            max_rows = 20
            for _, row in resumen_df.head(max_rows).iterrows():
                s = " | ".join([f"{k}={row.get(k)}" for k in cols[:6]])
                draw_line(s, size=9, dy=12)
            if len(resumen_df) > max_rows:
                draw_line(f"... ({len(resumen_df) - max_rows} filas más)")
        else:
            draw_line("No hay datos en resumen.")
    except Exception as e:
        draw_line(f"(No se pudo renderizar resumen: {e})")

    draw_line("")
    draw_line(f"Excel asociado: {out_xlsx if out_xlsx else 'No disponible'}")
    c.save()




