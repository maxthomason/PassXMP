# Changelog

All notable changes to PassXMP will be documented in this file.

## [2.0.0] — 2026-04-16

### Changed
- **Full UI redesign.** Replaced the single-window log-style layout with a two-tab native macOS interface (Presets / Settings).
- Presets tab now shows every `.xmp` file in a Finder-style table with per-file sync status (`✓` synced, `!` failed, blank pending, inline "syncing…" label).
- Multi-select checkboxes let you sync specific files instead of the whole folder.
- Progress footer shows the current filename, queue position, and bytes written during active syncs.
- Settings tab consolidates folder pickers, LUT precision, auto-start, and watcher control.
- Live pulsing green dot replaces the old coloured "● Syncing" / "● Paused" text status.
- All chrome now uses Qt palette roles so the UI adapts to light and dark mode.

### Added
- Search field in the Presets topbar filters the file list by filename.
- Right-click context menu on rows: **Reveal .xmp in Finder**, **Reveal .cube in Finder** (synced), **Resync this file** (synced), **Retry** (failed), **Copy error message** (failed).
- Selection persists across sessions.
- Empty states for "no folders configured" and "no .xmp files found" replace the blank-table condition.

### Removed
- In-app activity log (`Recent Activity` list). Logs continue to the file at `~/Library/Logs/PassXMP/passxmp.log`.
- Legacy `setup_window.py` and `settings_window.py` (consolidated into the Settings tab).

### Internal
- New `FileRegistry` (`src/core/file_registry.py`) owns the list of discovered presets and their derived sync status; emits Qt signals on change.
- New reusable widgets under `src/gui/widgets/`: `LiveDot`, `StatusCell`, `ProgressFooter`.
- `FolderWatcher` gained an `on_event(kind, path, new_path=None)` callback for raw filesystem events (in addition to the existing `on_sync`).
- `ConfigManager` persists the user's selection across sessions via `selected_relative_paths`.
- `setup_logging()` is now file-only (the GUI callback plumbing is gone).
- 107 tests cover the data model, widgets, and the full app-boot smoke path.

## [1.0.0] — 2026-04-15

- Initial MVP release: single-window config + Recent Activity + Start Syncing button.
