$ErrorActionPreference="Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if (-not (Test-Path ".\.venv")) {
  python -m venv .venv
}

. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel

if (Test-Path ".\requirements-lock.txt") {
  pip install -r .\requirements-lock.txt
} elseif (Test-Path ".\requirements.txt") {
  pip install -r .\requirements.txt
} else {
  throw "No encuentro requirements-lock.txt ni requirements.txt"
}

Write-Host "✅ Entorno listo. Ejecuta: .\run.ps1"
