from pathlib import Path
import re
from datetime import datetime

p = Path("wrap_core.py")
src = p.read_text(encoding="utf-8", errors="replace")

# Backup adicional por seguridad
bak = Path(f"wrap_core.py.bak_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
bak.write_text(src, encoding="utf-8")
print("Backup extra:", bak.name)

# 1) Quitar cualquier bloque previo de exportación industrial (si existiera)
#    Borra desde la línea que contenga "Exportación industrial" hasta antes de la siguiente línea que empiece con 'if st.' o 'with st.' o 'def '
lines = src.splitlines()
out = []
i = 0
removed = 0

def boundary(s: str) -> bool:
    s2 = s.lstrip()
    return s2.startswith("if st.") or s2.startswith("with st.") or s2.startswith("def ") or s2.startswith("class ")

while i < len(lines):
    if ("Exportación industrial" in lines[i]) or ("EXPORTACIÓN INDUSTRIAL" in lines[i]) or ("EXPORTACION INDUSTRIAL" in lines[i]):
        removed += 1
        i += 1
        while i < len(lines) and not boundary(lines[i]):
            i += 1
        continue
    out.append(lines[i])
    i += 1

new = "\n".join(out) + "\n"
print("Bloques removidos:", removed)

# 2) Insertar bloque correcto justo después de out_xlsx assignment
anchor = 'st.session_state["out_xlsx"] = result.get("plan_excel")'
pos = new.find(anchor)
if pos == -1:
    raise SystemExit("No encontré el anchor out_xlsx. No pude insertar bloque.")

# indentación exacta del anchor
line_start = new.rfind("\n", 0, pos) + 1
indent = re.match(r"[ \t]*", new[line_start:pos]).group(0)

# Evitar doble inserción
if "out_sheet_exports" not in new:
    block = (
        f'{indent}# Exportación industrial (workbook completo + descargas por hoja)\n'
        f'{indent}if isinstance(st.session_state.get("out_xlsx"), str) and os.path.exists(st.session_state["out_xlsx"]):\n'
        f'{indent}    if os.path.exists("exports_industrial.py"):\n'
        f'{indent}        from exports_industrial import export_full_workbook, export_single_sheet, list_schema_sheets\n'
        f'{indent}        out_dir = os.path.join(base_dir, "OUTPUT")\n'
        f'{indent}        os.makedirs(out_dir, exist_ok=True)\n'
        f'{indent}        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")\n'
        f'{indent}        full_path = os.path.join(out_dir, f"LOGISTAT_EXPORT_COMPLETO_{stamp}.xlsx")\n'
        f'{indent}        export_full_workbook(st.session_state["out_xlsx"], full_path)\n'
        f'{indent}        st.session_state["out_full_export"] = full_path\n'
        f'{indent}        indiv = {{}}\n'
        f'{indent}        for sh in list_schema_sheets():\n'
        f'{indent}            pth = os.path.join(out_dir, f"{sh}_EXPORT_{stamp}.xlsx")\n'
        f'{indent}            export_single_sheet(st.session_state["out_xlsx"], sh, pth)\n'
        f'{indent}            indiv[sh] = pth\n'
        f'{indent}        st.session_state["out_sheet_exports"] = indiv\n'
    )

    # asegurar imports necesarios arriba (sin romper)
    if "from datetime import datetime" not in new:
        new = new.replace("import pandas as pd\n", "import pandas as pd\nfrom datetime import datetime\n", 1)

    # insertar bloque después del anchor
    new = new.replace(anchor, anchor + "\n" + block, 1)

p.write_text(new, encoding="utf-8")
print("✅ wrap_core.py corregido (indentación OK).")




