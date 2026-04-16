@echo off
echo Building PassXMP for Windows...

pip install -r requirements.txt
pip install -r requirements-build.txt

pyinstaller ^
    --windowed ^
    --name PassXMP ^
    --icon assets/icon.ico ^
    --add-data "assets;assets" ^
    src/main.py

echo Build complete: dist\PassXMP\PassXMP.exe
