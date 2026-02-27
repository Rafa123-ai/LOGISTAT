import os
import sys
import subprocess
from pathlib import Path

def main():
    # Carpeta donde está el exe / script
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)).resolve()
    # Cuando está empaquetado, sys.executable apunta al exe, pero queremos trabajar en la carpeta del exe
    exe_dir = Path(sys.executable).resolve().parent
    os.chdir(exe_dir)

    # Asegura OUTPUT
    (exe_dir / "OUTPUT").mkdir(exist_ok=True)

    cmd = [sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless=true"]
    subprocess.Popen(cmd, cwd=str(exe_dir))

if __name__ == "__main__":
    main()
