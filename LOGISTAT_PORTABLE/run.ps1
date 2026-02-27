$ErrorActionPreference="Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

# Activa venv local
. .\.venv\Scripts\Activate.ps1

# Limpia cache Python
Get-ChildItem -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
  Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

python -m streamlit run app.py
