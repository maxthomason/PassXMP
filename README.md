# PassXMP

**Your Lightroom presets, instantly in DaVinci.**

PassXMP watches your Lightroom Classic presets folder and automatically mirrors it as `.cube` LUT files in DaVinci Resolve's LUT directory — preserving full folder hierarchy, naming, and organization.

After a one-time setup, the workflow is zero-touch:

1. Create or modify a preset in Lightroom
2. PassXMP detects the change, converts the color data to a `.cube` LUT
3. DaVinci Resolve reflects the preset on next refresh

No Lightroom engine dependency. No manual export steps. No technical knowledge required.

---

## Download

> **Releases coming soon** — Mac (`.dmg`) and Windows (`.exe`) builds will be available on the [Releases](https://github.com/maxthomason/PassXMP/releases) page.

---

## Quick Start

### One-Time Setup

1. Launch PassXMP
2. Confirm or browse to your **Lightroom Presets folder** and **DaVinci LUT folder** (auto-detected on most systems)
3. Click **Start Syncing**

That's it. PassXMP runs in your system tray and keeps everything in sync.

### Default Paths (Auto-Detected)

| App | Mac | Windows |
|-----|-----|---------|
| Lightroom Presets | `~/Library/Application Support/Adobe/Lightroom/Develop Presets/` | `%APPDATA%\Adobe\Lightroom\Develop Presets\` |
| DaVinci LUT | `/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT/` | `%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\LUT\` |

---

## How It Works

PassXMP uses a **Hald CLUT** approach — a mathematical identity image where every possible RGB input value is represented. The Lightroom preset's color adjustments are applied to this identity, and the resulting values are written as a standard 3D LUT.

```
.xmp file changed
       |
   XMP Parser ── extracts crs: namespace parameters
       |
   Sanitizer ─── zeros non-color params (exposure, clarity, etc.)
       |
   Hald CLUT ─── generates 33³ RGB identity array
       |
   Color Pipeline ── applies transforms in Lightroom's order
       |
   .cube Export ── writes standard 3D LUT file
       |
   Mirror ──────── places file in matching DaVinci subfolder
```

### Color Transform Pipeline

Transforms are applied in the same order as Lightroom's internal processing:

1. **White Balance** — Temperature and Tint via daylight locus approximation
2. **Saturation / Vibrance** — Global adjustments with vibrance protecting saturated colors
3. **HSL** — Per-channel hue rotation, saturation, and luminance across 8 color ranges with smooth blending
4. **Tone Curve** — Parametric (zone-based) and point curves (master + per-channel RGB) via cubic spline interpolation
5. **Color Grading** — Shadow/midtone/highlight wheels with luminance-based masking
6. **Split Toning** — Legacy shadow/highlight tinting with balance control

---

## What Translates

These parameters map cleanly to a 3D LUT and are reproduced with high fidelity:

| Category | Parameters |
|----------|-----------|
| White Balance | Temperature, Tint |
| Tone Curve | Parametric zones, point curves (master + RGB channels) |
| HSL / Color Mixer | Hue, Saturation, Luminance for all 8 color ranges |
| Color Grading | Shadow/Midtone/Highlight/Global wheels (Hue, Sat, Lum) |
| Split Toning | Shadow/Highlight Hue and Saturation, Balance |
| Vibrance / Saturation | Global Vibrance, Saturation |

## What Gets Zeroed Out

These parameters **cannot** be accurately encoded in a 3D LUT. PassXMP automatically zeros them before conversion — no manual cleanup needed.

| Category | Parameters |
|----------|-----------|
| Tone / Exposure | Exposure, Contrast, Highlights, Shadows, Whites, Blacks |
| Detail | Clarity, Texture, Dehaze, Sharpness |
| Noise Reduction | Luminance Smoothing, Color Noise Reduction |
| Lens Corrections | Vignette, Chromatic Aberration |
| Transform | Upright, Lens Profile corrections |
| Effects | Grain |

> This is a limitation of the LUT format, not PassXMP. For best results, build **color-focused presets** — the tone curve, HSL, and color grading adjustments all translate accurately.

---

## Running from Source

Requires **Python 3.11+**.

```bash
# Clone
git clone https://github.com/maxthomason/PassXMP.git
cd passxmp

# Install dependencies
pip install -r requirements.txt

# Run
python -m src.main
```

### Running Tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

### Building Distributables

```bash
# Mac
pip install -r requirements-build.txt
bash scripts/build_mac.sh

# Windows
pip install -r requirements-build.txt
scripts\build_windows.bat
```

---

## Project Structure

```
passxmp/
├── src/
│   ├── main.py                  # Entry point
│   ├── app.py                   # App lifecycle, window management
│   ├── core/
│   │   ├── xmp_parser.py        # XML parsing + sanitization
│   │   ├── hald_generator.py    # Hald CLUT identity generation
│   │   ├── color_transforms.py  # Full color transform pipeline
│   │   ├── cube_exporter.py     # .cube file writer
│   │   └── sync_engine.py       # Per-file conversion orchestrator
│   ├── watcher/
│   │   ├── folder_watcher.py    # watchdog file observer
│   │   └── mirror.py            # Path mirroring + initial sync
│   ├── gui/
│   │   ├── setup_window.py      # First-launch setup
│   │   ├── main_window.py       # Sync status + activity log
│   │   ├── settings_window.py   # Path/option editor
│   │   └── tray_icon.py         # System tray menu
│   ├── config/
│   │   ├── config_manager.py    # JSON config read/write
│   │   └── path_detector.py     # Auto-detect LR + DV paths
│   └── utils/
│       └── logger.py            # File + GUI logging
├── tests/
│   ├── test_xmp_parser.py
│   ├── test_color_transforms.py
│   ├── test_cube_exporter.py
│   ├── test_mirror.py
│   └── fixtures/sample_presets/
├── scripts/
│   ├── build_mac.sh
│   └── build_windows.bat
├── requirements.txt
├── requirements-dev.txt
├── requirements-build.txt
└── pyproject.toml
```

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.11+ |
| GUI | PyQt6 |
| File Watching | watchdog |
| Color Math | NumPy, SciPy |
| XML Parsing | xml.etree.ElementTree (stdlib) |
| Packaging | PyInstaller |
| Testing | pytest |

---

## Contributing

Contributions are welcome. To get started:

1. Fork the repo and create a feature branch
2. Run the test suite: `python -m pytest tests/ -v`
3. Ensure all tests pass before submitting a PR

Areas where help is especially appreciated:

- **Color accuracy** — comparing PassXMP output against Lightroom's actual rendering
- **Platform testing** — verifying path detection and builds on different OS versions
- **New input formats** — Capture One, ACR, etc.

---

## License

MIT — see [LICENSE](LICENSE).

Built by [Maxwell Thomason](https://github.com/maxthomason) for the photo editing community.
