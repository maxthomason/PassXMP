# Contributing to PassXMP

Thanks for your interest. PassXMP is a small project — the bar for contributing is:

- **Issues first.** If you're planning more than a one-line fix, open an issue to talk through the approach before writing code.
- **Tests required.** New behavior ships with a test. Run `.venv/bin/python -m pytest` — 120+ tests should pass.
- **TDD encouraged.** Write the failing test first, then the implementation.
- **No style police.** There's no formatter or linter in CI. Match surrounding code.

## Development setup

```bash
git clone https://github.com/maxthomason/PassXMP.git
cd PassXMP
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python -m pytest        # should show 120 passing
.venv/bin/python -m src.main
```

## Architecture overview

- `src/core/` — XMP parser, Hald generator, color transforms, cube exporter, FileRegistry
- `src/watcher/` — folder-watcher + path-mirror logic (watchdog)
- `src/gui/` — PyQt6 UI: `MainWindow` (shell) → `PresetsView` + `SettingsView` → widgets
- `src/app.py` — top-level controller, wires everything
- `src/config/` — user config + Lightroom/DaVinci path detection

## Pull request checklist

- [ ] New tests for any new behavior
- [ ] `pytest` passes locally
- [ ] README / CHANGELOG updated if user-visible
- [ ] One commit per logical change (rebase before opening PR if needed)
