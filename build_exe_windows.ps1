$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Write-Host ""
Write-Host "============================================================"
Write-Host " FH6 Live Map v0.8.9 UI Follow + QR - Windows EXE builder"
Write-Host "============================================================"
Write-Host ""
$python = Get-Command py -ErrorAction SilentlyContinue
if (-not $python) { throw 'Python launcher "py" was not found. Install Python 3.11+ on this builder PC.' }
py --version
py -m pip install --upgrade pip pyinstaller qrcode
py -m PyInstaller --noconfirm --clean FH6LiveMap.spec
Write-Host ""
Write-Host "Build complete:"
Write-Host "  $PSScriptRoot\dist\FH6LiveMap.exe"
Write-Host ""
