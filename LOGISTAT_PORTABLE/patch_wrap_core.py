from pathlib import Path
import re
from datetime import datetime

p = Path("wrap_core.py")
if not p.exists():
    raise SystemExit("No encuentro wrap_core.py. Ejecuta esto dentro de la carpeta LOGISTAT_BACKUP.")

src = p.read_text(encoding="utf-8", errors="replace")

# Backup con timestamp
bak = Path(f"wrap_core.py.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
bak.write_text(src, encoding="utf-8")
print("✅ Backup creado:", bak.name)

lines = src.splitlines()

# --- 1) Eliminar bloque industrial roto (si existe) ---
# Borra desde un comentario "Exportación industrial" o "EXPORTACIÓN INDUSTRIAL" hasta antes del siguiente bloque de UI.
out = []
i = 0
removed = 0

def is_ui_boundary(s: str) -> bool:
    s2 = s.lstrip()
    return (
        s2.startswith("if st.") or s2.startswith("with st.") or s2.startswith("st.") or
        s2.startswith("def ") or s2.startswith("class ")
    )

while i < len(lines):
    line = lines[i]
    if ("Exportación industrial" in line) or ("EXPORTACIÓN INDUSTRIAL" in line) or ("EXPORTACION INDUSTRIAL" in line):
        removed += 1
        i += 1
        # saltar hasta encontrar frontera de UI o fin de archivo
        while i < len(lines) and not is_ui_boundary(lines[i]):
            i += 1
        continue
    out.append(line)
    i += 1

new = "\n".join(out) + "\n"

# --- 2) Asegurar imports necesarios (sin romper) ---
if "from datetime import datetime" not in new:
    new = new.replace("import pandas as pd\n", "import pandas as pd\nfrom datetime import datetime\n", 1)

if "from exports_industrial import" not in new:
    # intenta insertar solo si existe el módulo en la carpeta
    if Path("exports_industrial.py").exists():
        new = new.replace(
            "from logistat_engine import run_logistat_v11, RULES\n",
            "from logistat_engine import run_logistat_v11, RULES\n"
            "from exports_industrial import export_full_workbook, export_single_sheet, list_schema_sheets\n",
            1
        )

# --- 3) Insertar bloque correcto (SIN try) después de out_xlsx ---
anchor = 'st.session_state["out_xlsx"] = result.get("plan_excel")'
pos = new.find(anchor)
if pos == -1:
    raise SystemExit("No encontré la línea de out_xlsx en wrap_core.py. No pude insertar el bloque.")

# Detectar indentación del anchor
line_start = new.rfind("\n", 0, pos) + 1
indent = re.match(r"[ \t]*", new[line_start:pos]).group(0)

block = f"""
{indent}# Exportación industrial (workbook completo + descargas por hoja)
{indent}if Path("exports_industrial.py").exists() and isinstance(st.session_state.get("out_xlsx"), str) and os.path.exists(st.session_state["out_xlsx"]):
{indent}    from exports_industrial import export_full_workbook, export_single_sheet, list_schema_sheets
{indent}    out_dir = os.path.join(base_dir, "OUTPUT")
{indent}    os.makedirs(out_dir, exist_ok=True)
{indent}    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
{indent}
{indent}    full_path = os.path.join(out_dir, f"LOGISTAT_EXPORT_COMPLETO_{{stamp}}.xlsx")
{indent}    export_full_workbook(st.session_state["out_xlsx"], full_path)
{indent}    st.session_state["out_full_export"] = full_path
{indent}
{indent}    indiv = {{}}
{indent}    for sh in list_schema_sheets():
{indent}        pth = os.path.join(out_dir, f"{{sh}}_EXPORT_{{stamp}}.xlsx")
{indent}        export_single_sheet(st.session_state["out_xlsx"], sh, pth)
{indent}        indiv[sh] = pth
{indent}    st.session_state["out_sheet_exports"] = indiv
"""

# Solo insertar si aún no existe
if "out_sheet_exports" not in new:
    # también necesitamos Path import si vamos a usarlo
    if "from pathlib import Path" not in new:
        new = new.replace("from __future__ import annotations\n", "from __future__ import annotations\nfrom pathlib import Path\n", 1)
    new = new.replace(anchor, anchor + "\n" + block, 1)

p.write_text(new, encoding="utf-8")
print("✅ wrap_core.py corregido. Bloques removidos:", removed)




