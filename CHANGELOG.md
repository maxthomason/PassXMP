# Changelog

All notable changes to PassXMP will be documented in this file.

## [2.0.1] — 2026-04-16

**Security release. Users on 2.0.0 should upgrade.**

### Security
- Switch XMP parser to `defusedxml`. A crafted `.xmp` file with nested entity definitions (billion-laughs) could previously exhaust memory on older expat versions. External entity references are also rejected, blocking local-file exfiltration via a malicious preset pack.
- Normalise path separators in `_cleanup_empty_dirs` so a trailing slash on `dv_root` cannot make the empty-dir walk delete the DaVinci LUT folder itself when all presets are removed.

### Fixed
- `.cube` writes are now atomic (temp file + `os.replace`). A crash mid-write used to leave a truncated LUT whose newer mtime fooled the freshness check into skipping re-conversion.
- `config.json` saves use the same atomic pattern. A crash mid-save no longer resets all user settings.
- `os.getlogin()` in Linux path detection is guarded with a `$USER` fallback — the app no longer crashes at launch on hosts without a controlling terminal (Docker, `systemd --user`, double-forked daemons).
- `mark_done` returns early for rows that were already removed by the watcher. Prevents `_failed` set leaks when a file is deleted mid-sync.
- `passxmp.log` now rotates at 5 MB with 3 backups. Long-running installs no longer accumulate an unbounded log file.
- Rescan distinguishes "folder not found", "folder not readable", and "empty folder" in the Presets empty state so unreachable LR paths surface instead of silently showing "no presets."
- `.cube` `TITLE` header strips double-quotes, newlines, and non-printable characters. Presets with unusual filenames no longer produce malformed LUT headers.

### Polish
- Main window briefly shows `PassXMP — Stopping…` before the blocking joins in `_on_quit`, so a slow shutdown doesn't look like a hang.
- Presets summary line uses the registry's live status instead of a stale derivation, so in-flight files no longer briefly show as "synced" during re-sync.
- Watcher completion callback uses the watcher's frozen `lr_root` instead of the live config value, so the UI stays consistent if folders are changed while a sync is running.
- "Large sync" size warning threshold updated to measured per-file byte counts (~1.28 MB at 33³, ~11 MB at 65³) instead of the earlier underestimate.
- `rescan` and `initial_sync` docstrings document that symlinks inside `lr_root` are not followed.

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
