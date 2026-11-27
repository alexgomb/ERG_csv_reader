# AGENTS.md — Project Scope & Engineering Instructions

## Project Overview

**nBio ERG-Trace** is a dual-platform electroretinography (ERG) viewer and amplitude analyzer for murine recordings exported as CSV files from the **CSO Retimax** system, shipping both:
- **Native Desktop App (`src/erg_reader/`):** Python + PySide6 + PyQtGraph + NumPy + SciPy + OpenPyXL (packaged as standalone `nBio_ERG_Trace.exe` on Windows Releases).
- **Zero-Install Web App (`web/`):** 100% client-side React + TypeScript + Vite SPA deployed automatically to **GitHub Pages** at `https://alexgomb.github.io/ERG_csv_reader/` (CSVs never leave the user's browser).

- **Author:** Alejandro Gombau García
- **Research Group:** Grupo nBio · Instituto de Bioingeniería · Universidad Miguel Hernández (`http://nbio.umh.es`)
- **License:** MIT (`LICENSE`)
- **Repository:** `alexgomb/ERG_csv_reader` (public GitHub repository)
- **Primary Scientific Focus:** Exclusively **left-eye (`LEFT - OS`)** murine ERG recordings, maintaining strict **1:1 raw signal fidelity** with CSO Retimax CSV exports across both desktop and web engines.

---

## Core Scope & Product Requirements

1. **CSO Retimax CSV Parsing & Eye Filtering**
   - Supports tab-delimited CSO Retimax CSV files using decimal commas (and dot-decimal fallbacks), CRLF/LF line endings, UTF-8 (with or without BOM) and Windows-1252 encodings.
   - Reads metadata headers (`Exam start:` timestamp and eye line `LEFT - OS` / `RIGHT - OD`) and dynamically parses all exported signal columns (`GAV(uV)`, `AV1(uV)`, `AV2(uV)`, etc.), defaulting to `AV1(uV)`.
   - **Critical rule:** Always determine recorded eye from the internal CSV eye header line (line 2), **never** from filename substrings (some exams include `"RIGHT"` in the filename while recording `LEFT - OS`).
   - By default, `RIGHT - OD` CSVs are automatically skipped on load; users may opt in via *Settings* to inspect `RIGHT - OD` files when needed.

2. **Retimax-Inspired Left-Eye Interface (Desktop & Web Parity)**
   - Three-column layout inspired by CSO Retimax (`Interfaz.png`), adapted specifically for left-eye CSV review without hardware acquisition controls (IR Camera, Start/Pause, Impedance).
   - **Left Sidebar:** Editable subject/exam metadata (`Strain / Lastname`, `Mouse ID / Name`, `Age`, manual `Protocol` selector, `Exam`, read-only `Exam Start`, `Notes` — auto-inferred from parent folder and filename when applicable), interactive loaded-trace list with checkboxes to overlay reference curves (`GNS` style), institutional UMH · nBio vector SVG logo (`umh_nbio_light.svg` / `umh_nbio_dark.svg`), and visible author credit.
   - **Center Workspace:** Interactive `LEFT - OS` waveform canvas (PyQtGraph on desktop, interactive SVG + pointer-capture on web) with Retimax grid, zero baseline, floating channel badge (`AV1`), reference overlays, draggable `A1`/`B1`/`C1` cursors snapped 1:1 to real samples, and Retimax-format metrics table underneath (`Amplitude (µV)` and `Peak time (ms)` for `A1`, `B1`, `C1`, highlighted `A1-B1`, and `B1-C1`).
   - **Right Control Strip:** File loading (`Open CSV Files`, `Folder`, `Examples`), pure display controls (trace column selector, `±250 µV` preset, magnifier & `▲`/`▼` scale steps, `Auto-Scale`, `Reset View`, `Grid` toggle), marker actions (`Auto-Detect`, `Settings`), export buttons (`Copy Table`, `Save Plot` PNG/SVG, `CSV`, `Excel`), session `Save`/`Load` JSON, quick `EN`/`ES` language toggle, `Light`/`Dark` theme toggle, and `About` dialog.

3. **Scientific Signal Integrity (No Filtering / No Baseline Alteration)**
   - **Never** apply low-pass smoothing, baseline offset subtraction, or amplitude resampling to the displayed or measured trace. All reported amplitudes and peak times must match the raw CSO Retimax CSV samples 1:1.

4. **Protocol-Aware Peak Detection, Manual Override & Flicker Analysis**
   - Automatically identifies murine protocols (`Dark-Adapted 3.0`, `Dark-Adapted 10.0`, `Light-Adapted 3.0`, `Light-Adapted 3.0 Flicker`, `Custom / Unknown`), prioritizing the 140–185 ms recording duration for 30 Hz Flicker so renamed Flicker CSVs are still recognized.
   - Users can override the protocol at any time via the sidebar `Protocol` dropdown, which immediately toggles the 30 Hz Flicker analysis bar and recalculates automatic markers (while preserving manual cursor edits).
   - Dragging any marker updates table metrics live and marks the trace as `Manual`; `Auto-Detect` restores automatic placement.
   - For **30 Hz Flicker** protocols, displays an additional non-destructive analysis bar with cycle mean peak-to-trough amplitude (± SD), FFT fundamental amplitude (~30 Hz), FFT peak-to-peak amplitude, dominant frequency (Hz), and detected cycle count.
   - **Cross-Platform Golden Parity Contract:** `tests/golden_metrics.json` captures exact Python-computed markers, `peak_metrics`, and `flicker_metrics` across all 8 bundled CSO Retimax CSVs. The TypeScript web engine (`web/src/core/analysis.ts`, including SciPy-compatible `findPeaks1D` and exact real DFT) MUST pass 1:1 numerical parity against `tests/golden_metrics.json` in CI.

5. **Batch Loading, Export & Session Persistence**
   - Supports drag-and-drop and dialogs for single CSVs, multiple CSVs, recursive folders/subfolders, and bundled `example_files/`.
   - Batch export of all loaded records to UTF-8 CSV (27 columns) and styled Excel (`.xlsx`, highlighting `A1-B1` amplitude and including an `Export Info` sheet).
   - Clipboard TSV copy for the active table, high-resolution **PNG** and native **SVG** plot export, and **JSON** work sessions preserving cursor indices, protocol overrides, metadata, active channels, overlays, and detection windows (the web app embeds waveforms inside exported JSON so sessions reload offline without re-selecting CSVs, and can also match desktop-exported JSON sessions to currently loaded CSVs).

6. **Bilingual UI, Themes, Packaging & Deployment**
   - Live switchable **English (`en`)** and **Spanish (`es`)** UI (default English) with automated 100% EN/ES key parity checks on both platforms.
   - Live switchable **Light** (Retimax clinical default) and **Dark** themes, persisted via `QSettings` (desktop) and `localStorage` (web).
   - Desktop packaging: `pyproject.toml`, `packaging/erg_reader.spec` → `nBio_ERG_Trace.exe` via `.github/workflows/release-windows.yml`.
   - Web deployment: `web/` built with `VITE_BASE=/ERG_csv_reader/` and published automatically via `.github/workflows/deploy-pages.yml` on push to `main`.

---

## Architecture Map

| Path | Responsibility |
| --- | --- |
| `src/erg_reader/models.py` | Python dataclasses (`ERGSessionRecord`, `MouseMetadata`, `MarkerIndices`, `PeakMetrics`, `FlickerMetrics`, `DetectionConfig`) |
| `src/erg_reader/parser.py` | Python CSO Retimax CSV parser, internal eye detection, protocol/metadata inference, recursive batch discovery |
| `src/erg_reader/analysis.py` | Python protocol-aware `A1`/`B1`/`C1` detection, Retimax exact metric formulas, 30 Hz Flicker peak-to-trough & FFT |
| `src/erg_reader/exporters.py` | Python batch CSV & OpenPyXL `.xlsx` exporters, clipboard TSV formatter, JSON session save/load |
| `src/erg_reader/i18n.py` | Python English & Spanish translation catalog and `Translator` class |
| `src/erg_reader/themes.py` | Light & Dark QSS stylesheets and PyQtGraph color palettes |
| `src/erg_reader/assets/` | Pure vector UMH · nBio institutional SVGs (`umh_nbio_light.svg`, `umh_nbio_dark.svg`) without `<clipPath>` |
| `src/erg_reader/ui/` | PySide6 UI modules (`plot_widget.py`, `metrics_table.py`, `sidebar.py`, `controls_panel.py`, `dialogs.py`, `main_window.py`) |
| `tests/` | Python `pytest` + `pytest-qt` unit, edge-case, and UI tests + shared cross-platform reference `tests/golden_metrics.json` |
| `web/src/core/` | TypeScript core engine (`models.ts`, `parser.ts`, `analysis.ts`, `exporters.ts`, `fileDrop.ts`, `i18n.ts`) with 1:1 Python parity |
| `web/src/components/` | React UI components (`WaveformPlot.tsx`, `MetricsTable.tsx`, `Sidebar.tsx`, `ControlsPanel.tsx`, `Modals.tsx`) |
| `web/src/__tests__/` | Vitest + Testing Library unit, edge-case, architecture, UI integration, and golden parity tests |
| `web/public/` | Static web assets (`favicon.svg`, `assets/umh_nbio_*.svg`, `example_files/*.csv`) |
| `.github/workflows/` | `ci.yml` (Python Ubuntu/Windows + Web TS/Vitest), `deploy-pages.yml` (GitHub Pages), `release-windows.yml` (PyInstaller `.exe`) |

---

## Development & Verification Guidelines

- **Python Desktop:**
  - Lint: `ruff check src tests`
  - Tests (headless): `QT_QPA_PLATFORM=offscreen pytest -v`
  - Run app: `nbio-erg-trace --examples`
  - Build Windows `.exe`: `pyinstaller --clean --noconfirm packaging/erg_reader.spec`
- **Web App (`web/`):**
  - Typecheck: `npm --prefix web run typecheck`
  - Lint: `npm --prefix web run lint`
  - Tests (including Python golden parity): `npm --prefix web test`
  - Local dev server: `npm --prefix web run dev`
  - Production GitHub Pages build: `VITE_BASE=/ERG_csv_reader/ npm --prefix web run build`
- Keep `README.md` (including its **Changelog**), `AGENTS.md`, `web/public/example_files/`, `web/public/assets/`, and `tests/golden_metrics.json` synchronized whenever protocols, assets, or features change.
- Never alter raw CSV sample amplitudes in display or metric computations.
