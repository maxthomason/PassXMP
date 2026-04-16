#!/bin/bash
set -e

echo "Building PassXMP for macOS..."

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-build.txt

# Build with PyInstaller
pyinstaller \
    --windowed \
    --name PassXMP \
    --icon assets/icon.icns \
    --add-data "assets:assets" \
    src/main.py

echo "Build complete: dist/PassXMP.app"
