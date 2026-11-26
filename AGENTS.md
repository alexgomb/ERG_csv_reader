# AGENTS.md — Project Scope & Engineering Instructions

## Project Overview

**nBio ERG-Trace** is a native desktop Python application (**PySide6 + PyQtGraph**) for reading, visualizing, and analyzing mouse electroretinography (ERG) recordings exported as CSV files from the **CSO Retimax** system.

- **Author:** Alejandro Gombau García
- **License:** MIT (`LICENSE`)
- **Repository:** `alexgomb/ERG_csv_reader` (private GitHub repository)
- **Primary Scientific Focus:** Exclusively **left-eye (`LEFT - OS`)** murine ERG recordings, maintaining strict **1:1 raw signal fidelity** with CSO Retimax CSV exports.

---

## Core Scope & Product Requirements

1. **CSO Retimax CSV Parsing & Eye Filtering**
   - Supports tab-delimited CSO Retimax CSV files using decimal commas (and dot-decimal fallbacks), CRLF/LF line endings, and UTF-8 / Windows-1252 encodings.
   - Reads metadata headers (`Exam start:` timestamp and eye line `LEFT - OS` / `RIGHT - OD`) and dynamically parses all exported signal columns (`GAV(uV)`, `AV1(uV)`, `AV2(uV)`, etc.), defaulting to `AV1(uV)`.
   - **Critical rule:** Always determine recorded eye from the internal CSV eye header line (line 2), **never** from filename substrings (some exams include `"RIGHT"` in the filename while recording `LEFT - OS`).
   - By default, `RIGHT - OD` CSVs are automatically skipped on load; users may opt in via *Settings* to inspect `RIGHT - OD` files when needed.

2. **Retimax-Inspired Left-Eye Desktop Interface**
   - Three-column desktop layout inspired by CSO Retimax (`Interfaz.png`), adapted specifically for left-eye CSV review without hardware acquisition controls (IR Camera, Start/Pause, Impedance).
   - **Left Sidebar:** Editable subject/exam metadata (`Strain / Lastname`, `Mouse ID / Name`, `Age`, `Exam`, read-only `Exam Start`, `Notes` — auto-inferred from parent folder and filename when applicable), interactive loaded-trace list with checkboxes to overlay reference curves (`GNS` style), and visible author credit.
   - **Center Workspace:** Interactive `LEFT - OS` PyQtGraph waveform canvas with Retimax grid, zero baseline, floating channel badge (`AV1`), reference overlays, draggable `A1`/`B1`/`C1` cursors snapped to real samples, and Retimax-format metrics table underneath (`Amplitude (µV)` and `Peak time (ms)` for `A1`, `B1`, `C1`, highlighted `A1-B1`, and `B1-C1`).
   - **Right Control Strip:** File loading (`Open CSV Files`, `Folder`, `Examples`), pure display controls (trace column selector, `±250 µV` preset, magnifier & `▲`/`▼` scale steps, `Auto-Scale`, `Reset View`, `Grid` toggle), marker actions (`Auto-Detect`, `Settings`), export buttons (`Copy Table`, `Save Plot`, `CSV`, `Excel`), quick `EN`/`ES` language toggle, `Light`/`Dark` theme toggle, and `About` dialog.

3. **Scientific Signal Integrity (No Filtering / No Baseline Alteration)**
   - **Never** apply low-pass smoothing, baseline offset subtraction, or amplitude resampling to the displayed or measured trace. All reported amplitudes and peak times must match the raw CSO Retimax CSV samples 1:1.

4. **Protocol-Aware Peak Detection & Flicker Analysis**
   - Automatically identifies murine protocols (`Dark-Adapted 3.0`, `Dark-Adapted 10.0`, `Light-Adapted 3.0`, `Light-Adapted 3.0 Flicker`, `Custom / Unknown`).
   - Places initial `A1`, `B1`, `C1` markers using user-configurable physiological time windows (ms) per protocol.
   - Dragging any marker updates table metrics live and marks the trace as `Manual`; `Auto-Detect` restores automatic placement.
   - For **30 Hz Flicker** protocols, displays an additional non-destructive analysis bar with cycle mean peak-to-trough amplitude (± SD), FFT fundamental amplitude (~30 Hz), FFT peak-to-peak amplitude, dominant frequency (Hz), and detected cycle count.

5. **Batch Loading, Export & Session Persistence**
   - Supports drag-and-drop and dialogs for single CSVs, multiple CSVs, recursive folders/subfolders, and bundled `example_files/`.
   - Batch export of all loaded records to UTF-8 **CSV** and styled **Excel (`.xlsx`)** (highlighting `A1-B1` amplitude and including an `Export Info` sheet).
   - Clipboard TSV copy for the active table, high-resolution **PNG** and native **SVG** plot export, and **JSON** work sessions preserving cursor indices, metadata, active channels, overlays, and detection windows.

6. **Bilingual UI, Themes & Packaging**
   - Live switchable **English (`en`)** and **Spanish (`es`)** UI, defaulting to English on first launch.
   - Live switchable **Light** (Retimax clinical default) and **Dark** themes, persisted alongside language, grid toggle, and detection settings via `QSettings`.
   - Standard installable Python package (`pyproject.toml`, `requirements.txt`, `nbio-erg-trace` / `erg-reader` entry points), PyInstaller `.spec` (`packaging/erg_reader.spec` → `nBio_ERG_Trace.exe`), and GitHub Actions CI + automated Windows `.exe` release builds.

---

## Architecture Map

| Path | Responsibility |
| --- | --- |
| `src/erg_reader/models.py` | Core dataclasses (`ERGSessionRecord`, `MouseMetadata`, `MarkerIndices`, `PeakMetrics`, `FlickerMetrics`, `DetectionConfig`) |
| `src/erg_reader/parser.py` | CSO Retimax CSV parser, internal eye detection, protocol/metadata inference, recursive batch discovery |
| `src/erg_reader/analysis.py` | Protocol-aware `A1`/`B1`/`C1` detection, Retimax exact metric formulas, 30 Hz Flicker peak-to-trough & FFT |
| `src/erg_reader/exporters.py` | Batch CSV & formatted Excel `.xlsx` exporters, clipboard TSV formatter, JSON session save/load |
| `src/erg_reader/i18n.py` | Complete English & Spanish translation catalog and `Translator` class |
| `src/erg_reader/themes.py` | Light & Dark QSS stylesheets and PyQtGraph color palettes |
| `src/erg_reader/ui/plot_widget.py` | Interactive PyQtGraph canvas, draggable `A1`/`B1`/`C1` cursors, reference overlays, PNG/SVG export |
| `src/erg_reader/ui/metrics_table.py` | Retimax-format 2×6 metrics table with highlighted `A1-B1` cell and conditional 30 Hz Flicker bar |
| `src/erg_reader/ui/sidebar.py` | Editable metadata form, checkable trace list for overlays, branding header, author footer |
| `src/erg_reader/ui/controls_panel.py` | Scroll-safe Retimax-style right toolbar with pure display controls, exports, language & theme switchers |
| `src/erg_reader/ui/dialogs.py` | `SettingsDialog` (physiological windows & `RIGHT - OD` toggle) and `AboutDialog` |
| `src/erg_reader/ui/main_window.py` | Top-level `MainWindow`, menus, shortcuts, drag-and-drop, and `QSettings` persistence |

---

## Development & Verification Guidelines

- **Run linter:** `ruff check src tests`
- **Run tests (headless):** `QT_QPA_PLATFORM=offscreen pytest -v`
- **Run application:** `nbio-erg-trace` (or `python -m erg_reader --examples`)
- **Build Windows executable:** `pyinstaller --clean --noconfirm packaging/erg_reader.spec`
- Keep `README.md` (including its **Changelog** and screenshots) and `AGENTS.md` updated whenever user-facing features, protocols, or packaging workflows change.
- Never alter raw CSV sample amplitudes in display or metric computations.
