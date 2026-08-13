# Rebuilds dist\KovaaksPracticeMode.exe — a single standalone .exe that
# users can run without installing Python or any dependencies.
#
# Usage: powershell -ExecutionPolicy Bypass -File build.ps1

pip install -r requirements.txt
pip install pyinstaller

python build_icon.py
pyinstaller --noconfirm KovaaksPracticeMode.spec

Write-Host ""
Write-Host "Built: dist\KovaaksPracticeMode.exe"
