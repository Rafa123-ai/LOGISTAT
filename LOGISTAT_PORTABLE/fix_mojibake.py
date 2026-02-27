from pathlib import Path

REPL = {
    "PlaneaciÁƒ³n":"Planeación",
    "DiÁƒ©sel":"Diésel",
    "ExportaciÁƒ³n":"Exportación",
    "Á¢‚¬€œ":"€“",
    "Á¢‚¬€":"€”",
    "mÁ‚³":"m³",
    "Áƒ¡":"á","Áƒ©":"é","Áƒ­":"í","Áƒ³":"ó","Áƒº":"ú",
    "Áƒ":"Á","Áƒ€°":"Á‰","Áƒ":"Á","Áƒ€œ":"Á“","ÁƒÅ¡":"Áš",
    "Áƒ±":"ñ","Áƒ€˜":"Á‘",
    "Á¢‚¬Ëœ":"€˜","Á¢‚¬„¢":"€™","Á¢‚¬Å“":"€œ","Á¢‚¬ï¿½":"€","Á¢‚¬¦":"€¦",
    "Á‚":""
}

def fix_text(s: str) -> str:
    for a,b in REPL.items():
        s = s.replace(a,b)
    return s

root = Path(".")
files = list(root.rglob("*.py")) + list(root.rglob("*.txt")) + list(root.rglob("*.md"))

changed = 0
for p in files:
    try:
        txt = p.read_text(encoding="utf-8", errors="replace")
        new = fix_text(txt)
        if new != txt:
            p.write_text(new, encoding="utf-8", newline="\n")
            print("FIX:", p)
            changed += 1
    except Exception as e:
        print("SKIP:", p, e)

print(f"\nArchivos modificados: {changed}")




