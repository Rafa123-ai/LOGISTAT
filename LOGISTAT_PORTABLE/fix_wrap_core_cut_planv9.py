from pathlib import Path
from datetime import datetime

p = Path("wrap_core.py")
src = p.read_text(encoding="utf-8", errors="replace").splitlines()

# backup
bak = Path(f"wrap_core.py.bak_fixplanv9_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
bak.write_text("\n".join(src) + "\n", encoding="utf-8")
print("Backup:", bak.name)

out = []
cut = False
for line in src:
    if line.strip().startswith("# Exportación PLAN_V9"):
        cut = True
    if not cut:
        out.append(line)

p.write_text("\n".join(out) + "\n", encoding="utf-8")
print("✅ Eliminé el bloque PLAN_V9 mal indentado (desde '# Exportación PLAN_V9' hasta el final).")




