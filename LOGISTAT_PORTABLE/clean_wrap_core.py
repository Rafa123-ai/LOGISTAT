from pathlib import Path
from datetime import datetime

p = Path("wrap_core.py")
lines = p.read_text(encoding="utf-8", errors="replace").splitlines()

# Backup
bak = Path(f"wrap_core.py.cleanbackup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
bak.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("Backup creado:", bak.name)

clean = []
skip = False

for line in lines:
    # Si encontramos un try que está fuera del bloque principal, lo eliminamos
    if line.strip() == "try:" and not line.startswith(" " * 12):
        skip = True
        continue
    if skip:
        # detener skip cuando encontramos except alineado
        if line.strip().startswith("except"):
            skip = False
        continue
    clean.append(line)

p.write_text("\n".join(clean) + "\n", encoding="utf-8")
print("Bloques try sueltos eliminados.")




