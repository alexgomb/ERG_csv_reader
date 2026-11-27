<div align="center">

<a href="http://nbio.umh.es">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="src/erg_reader/assets/umh_nbio_dark.svg" />
    <source media="(prefers-color-scheme: light)" srcset="src/erg_reader/assets/umh_nbio_light.svg" />
    <img src="src/erg_reader/assets/umh_nbio_light.svg" alt="Universidad Miguel Hernández — Grupo nBio" width="380" />
  </picture>
</a>

<br />

<img src="web/public/favicon.svg" alt="nBio ERG-Trace Emblem" width="56" height="56" />

# nBio ERG-Trace

**Mouse electroretinography (ERG) viewer and amplitude analyzer for CSO Retimax CSV exports — available as a zero-install Web App and a native Desktop App.**

<p>
  <a href="https://alexgomb.github.io/ERG_csv_reader/"><img src="https://img.shields.io/badge/Live%20Web%20App-Open%20in%20Browser-1D4ED8?style=for-the-badge&logo=githubpages&logoColor=white" alt="Open Live Web App" /></a>
  <a href="https://github.com/alexgomb/ERG_csv_reader/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/alexgomb/ERG_csv_reader/ci.yml?branch=main&style=for-the-badge&logo=githubactions&logoColor=white&label=CI" alt="CI Status" /></a>
  <a href="https://github.com/alexgomb/ERG_csv_reader/actions/workflows/deploy-pages.yml"><img src="https://img.shields.io/github/actions/workflow/status/alexgomb/ERG_csv_reader/deploy-pages.yml?branch=main&style=for-the-badge&logo=githubpages&logoColor=white&label=Pages" alt="GitHub Pages Status" /></a>
  <a href="https://github.com/alexgomb/ERG_csv_reader/releases/latest"><img src="https://img.shields.io/github/v/release/alexgomb/ERG_csv_reader?style=for-the-badge&color=0F766E&label=Release" alt="Latest Release" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-334155?style=for-the-badge" alt="MIT License" /></a>
</p>

</div>

---

## Live Web App (No Installation Required)

> **Launch directly in your browser:** **[https://alexgomb.github.io/ERG_csv_reader/](https://alexgomb.github.io/ERG_csv_reader/)**

- **100% Local & Private:** All CSV parsing, waveform rendering, FFT analysis, and CSV/Excel exports run **exclusively inside your browser**. Your research CSV files never leave your device and are never uploaded to any server.
- **1:1 Numerical Parity with Desktop:** Shares the exact same raw-signal formulas, Retimax peak detection windows, Oscillatory Potentials (`OP1–OP4`) extraction, and 30 Hz Flicker FFT math as the Python desktop engine, continuously verified against [`tests/golden_metrics.json`](tests/golden_metrics.json) across all **10** real CSO Retimax recordings (C57BL/6 mouse at postnatal day 21 · P21).
- **Works on Any Computer:** Share the link with lab colleagues on Windows, macOS, or Linux — click **Examples** to test immediately with the bundled C57BL/6 P21 dataset or drag and drop your CSO Retimax CSVs/folders.

---

## Overview

**nBio ERG-Trace** is built for vision-science laboratories recording murine ERGs with the **CSO Retimax** system. It is available both as a **zero-install Web App** (React + TypeScript + Vite on GitHub Pages) and a **native desktop application** (Python + PySide6 + PyQtGraph). Both share the same Retimax-inspired interface focused on the **left eye (`LEFT - OS`)**, preserving **1:1 raw signal fidelity** (no artificial smoothing or baseline alteration) while adding modern batch loading, interactive cursor adjustment, reference overlays, manual protocol selection, dedicated **Oscillatory Potentials (`OP1–OP4`)** and **30 Hz Flicker** analysis, bilingual EN/ES support, dark/light themes, and direct CSV/Excel export.

### Key Features

- **Left-Eye (`LEFT - OS`) Workflow:** Automatically identifies recorded eye from the internal CSO Retimax CSV header (not filename text) and filters out `RIGHT - OD` exports by default (configurable in *Settings*).
- **1:1 Raw Signal Fidelity:** Pure display controls (`±250 µV` Retimax scale, magnifier `0.25x–25x`, `▲`/`▼` scale steps, `Auto-Scale`, free zoom/pan, grid toggle, dynamic channel selector `AV1(uV)` / `GAV(uV)` / `AV2(uV)...`) without filtering or modifying underlying microvolt values.
- **Protocol-Aware Auto-Detection, Manual Protocol Override & Draggable Cursors:** Automatically detects all five standard murine CSO Retimax protocols (`Dark-Adapted 3.0`, `Dark-Adapted 10.0`, `Dark-Adapted 3.0 Oscillatory Potentials`, `Light-Adapted 3.0`, and `Light-Adapted 3.0 Flicker`) — or override manually via the sidebar dropdown — placing `A1`, `B1`, and `C1` within configurable physiological windows (ms) and allowing interactive dragging along raw samples with live recalculation of `A1-B1` (highlighted yellow) and `B1-C1`.
- **Dedicated Oscillatory Potentials (`OP1–OP4`) Analysis:** Automatically extracts `OP1–OP4` trough-to-peak wavelets within the physiological ascending-b-wave window (`15–65 ms`), computing total summed amplitude (**∑OPs**), individual `OP1–OP4` amplitudes & implicit peak times, dominant OP-band FFT frequency (`60–200 Hz`), and wavelet count directly from raw Retimax OP traces.
- **Dedicated 30 Hz Flicker Metrics:** Automatically computes raw-signal mean peak-to-trough amplitude (± SD), FFT fundamental amplitude (~30 Hz), FFT peak-to-peak amplitude, dominant frequency, and cycle count for Flicker traces.
- **Multi-File / Folder Loading & Reference Overlays:** Drag and drop individual CSVs, multiple files, or mouse subfolders recursively. Check any trace in the sidebar to overlay it in muted gray (`GNS` reference style) behind the active waveform.
- **Batch Export & Work Sessions:** Export all loaded and manually verified records to **CSV** or formatted **Excel (`.xlsx`)** (34 columns including `A1`/`B1`/`C1`, Flicker, and `OP1–OP4` / `∑OPs`), copy the active metrics table to the clipboard, save high-resolution **PNG** or vector **SVG** plots, and save/reopen **JSON** work sessions preserving cursor adjustments, protocol overrides, and mouse metadata.
- **Bilingual (EN / ES) & Light / Dark Themes:** Switch language and theme live at any time; preferences and detection windows persist automatically across launches.

---

## Technology Stack

### Native Desktop (`src/erg_reader/`)

<p>
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/PySide6-Qt%206-41CD52?style=for-the-badge&logo=qt&logoColor=white" alt="PySide6 Qt 6" />
  <img src="https://img.shields.io/badge/PyQtGraph-Waveform%20Canvas-0C4A6E?style=for-the-badge&logo=python&logoColor=white" alt="PyQtGraph" />
  <img src="https://img.shields.io/badge/NumPy-Signal%20Arrays-013243?style=for-the-badge&logo=numpy&logoColor=white" alt="NumPy" />
  <img src="https://img.shields.io/badge/SciPy-Peak%20%26%20OP%20FFT-8CAAE6?style=for-the-badge&logo=scipy&logoColor=white" alt="SciPy" />
  <img src="https://img.shields.io/badge/OpenPyXL-Excel%20.xlsx-1D6F42?style=for-the-badge" alt="OpenPyXL" />
  <img src="https://img.shields.io/badge/PyInstaller-Windows%20.exe-1E293B?style=for-the-badge&logo=python&logoColor=white" alt="PyInstaller" />
  <img src="https://img.shields.io/badge/pytest-51%20Tests-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white" alt="pytest" />
  <img src="https://img.shields.io/badge/Ruff-Linter-D7FF64?style=for-the-badge&logo=ruff&logoColor=1E293B" alt="Ruff" />
</p>

### Zero-Install Web App (`web/`) & CI/CD

<p>
  <img src="https://img.shields.io/badge/React-19-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React 19" />
  <img src="https://img.shields.io/badge/TypeScript-Strict-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/Vite-Bundler-646CFF?style=for-the-badge&logo=vite&logoColor=white" alt="Vite" />
  <img src="https://img.shields.io/badge/HTML5-Semantic-E34F26?style=for-the-badge&logo=html5&logoColor=white" alt="HTML5" />
  <img src="https://img.shields.io/badge/CSS3-Vanilla%20Themes-1572B6?style=for-the-badge&logo=css&logoColor=white" alt="CSS3" />
  <img src="https://img.shields.io/badge/SVG-Interactive%20Plot-FFB13B?style=for-the-badge&logo=svg&logoColor=1E293B" alt="SVG" />
  <img src="https://img.shields.io/badge/Vitest-26%20Tests-6E9F18?style=for-the-badge&logo=vitest&logoColor=white" alt="Vitest" />
  <img src="https://img.shields.io/badge/Testing%20Library-UI%20Tests-E33332?style=for-the-badge&logo=testinglibrary&logoColor=white" alt="Testing Library" />
  <img src="https://img.shields.io/badge/Oxlint-Linter-0F172A?style=for-the-badge&logo=oxc&logoColor=white" alt="Oxlint" />
  <img src="https://img.shields.io/badge/GitHub%20Pages-Static%20Deploy-222222?style=for-the-badge&logo=githubpages&logoColor=white" alt="GitHub Pages" />
  <img src="https://img.shields.io/badge/GitHub%20Actions-CI%2FCD-2088FF?style=for-the-badge&logo=githubactions&logoColor=white" alt="GitHub Actions" />
</p>

---

## Dual-Platform Architecture

Both the **Native Desktop App** and the **Zero-Install Web App** implement the exact same layered data pipeline with zero server-side processing, locked together by a shared golden-reference contract (`tests/golden_metrics.json`) verified on every commit.

```mermaid
flowchart TB
    CSV["CSO Retimax CSV Exports — DA 3.0, DA 10.0, OPs, LA 3.0, 30 Hz Flicker (1:1 Raw Microvolts)"]

    subgraph DESKTOP["Native Desktop Architecture — src/erg_reader/ (Python)"]
        direction TB
        DP["parser.py — UTF-8/CP1252, Internal Eye Header, Recursive Folders"]
        DA["analysis.py — NumPy & SciPy find_peaks, A1/B1/C1, OP1-OP4 & 30 Hz rfft"]
        DU["PySide6 + PyQtGraph UI — Draggable Cursors, OP & Flicker Bars, Overlays, EN/ES"]
        DE["exporters.py — 34-Col CSV, OpenPyXL Excel, PNG/SVG, JSON Session & QSettings"]
        DB["PyInstaller — Standalone nBio_ERG_Trace.exe (GitHub Releases)"]
        DP --> DA --> DU --> DE --> DB
    end

    subgraph WEB["Zero-Install Web Architecture — web/ (100% Local in Browser)"]
        direction TB
        WP["fileDrop.ts + parser.ts — Recursive Folder Drop & Internal Eye Header"]
        WA["analysis.ts — SciPy-Exact findPeaks1D, A1/B1/C1, OP1-OP4 & Real DFT"]
        WU["React 19 + Interactive SVG UI — Pointer Cursors, OP & Flicker Bars, Overlays, EN/ES"]
        WE["exporters.ts — 34-Col CSV, write-excel-file Excel, PNG/SVG, Self-Contained JSON"]
        WB["Vite Static Bundle — GitHub Pages (alexgomb.github.io/ERG_csv_reader)"]
        WP --> WA --> WU --> WE --> WB
    end

    subgraph QA["Shared Verification & CI/CD — .github/workflows/"]
        direction LR
        GM["tests/golden_metrics.json — 10 Real C57BL/6 P21 CSO Retimax CSVs"]
        PT["pytest + pytest-qt + Ruff (51 Tests — Ubuntu & Windows)"]
        WT["Vitest + Testing Library + tsc + Oxlint (26 Tests — Ubuntu)"]
        GM -.->|"1:1 Parity"| PT
        GM -.->|"1:1 Parity"| WT
    end

    CSV --> DP
    CSV --> WP
    DA -.->|"Generates & Validates"| GM
    WA -.->|"Matches Bit-for-Bit"| GM

    classDef input fill:#1E3A8A,stroke:#1D4ED8,color:#FFFFFF
    classDef py fill:#0F4C81,stroke:#38BDF8,color:#F8FAFC
    classDef web fill:#065F46,stroke:#34D399,color:#ECFDF5
    classDef qa fill:#78350F,stroke:#F59E0B,color:#FFFBEB

    class CSV input
    class DP,DA,DU,DE,DB py
    class WP,WA,WU,WE,WB web
    class GM,PT,WT qa
```

| Layer | Native Desktop (`src/erg_reader/`) | Zero-Install Web App (`web/`) |
| --- | --- | --- |
| **Runtime & Privacy** | Local Python / standalone Windows `.exe` | 100% local in-browser SPA (zero uploads) |
| **CSV & Folder Input** | `parser.py` (`Path.rglob`, drag & drop) | `parser.ts` + `fileDrop.ts` (recursive `webkitGetAsEntry`) |
| **Analysis Engine** | `NumPy` + `SciPy` (`A1/B1/C1`, `OP1–OP4`, `30 Hz Flicker`) | Pure TypeScript (`findPeaks1D`, `OP1–OP4`, exact real DFT) |
| **Interactive Plot** | `PySide6` + `PyQtGraph` + `QSvgGenerator` | `React 19` + Interactive `SVG` + Canvas PNG export |
| **Batch Export** | 34-col UTF-8 CSV, `OpenPyXL` `.xlsx`, JSON session | 34-col UTF-8 CSV, `write-excel-file` `.xlsx`, self-contained JSON |
| **Preferences Storage** | `QSettings` | `localStorage` (with corrupt-JSON fallback) |
| **Distribution** | `pip install -e .` & GitHub Release `.exe` | Automatic GitHub Pages deploy on push to `main` |
| **Automated Tests** | `ruff` + `pytest` + `pytest-qt` (**51 tests**) | `tsc` + `oxlint` + `Vitest` + Testing Library (**26 tests**) |

---

## Screenshots

### Light Mode (English) — Dark-Adapted 3.0 ERG with Dark-Adapted 10.0 Reference Overlay
![Light Mode EN - Dark-Adapted 3.0 ERG with Reference Overlay](docs/screenshots/01_light_en_da3_overlay.png)

### Dark Mode (English) — Dark-Adapted 3.0 ERG
![Dark Mode EN - Dark-Adapted 3.0 ERG](docs/screenshots/02_dark_en_da3.png)

### Light Mode (Spanish) — Light-Adapted 3.0 Flicker ERG (Auto-Scale & 30 Hz FFT Bar)
![Light Mode ES - 30 Hz Flicker ERG](docs/screenshots/03_light_es_flicker.png)

### Dark Mode (Spanish) — Dark-Adapted 10.0 ERG
![Dark Mode ES - Dark-Adapted 10.0 ERG](docs/screenshots/04_dark_es_da10.png)

---

## Installation & Quick Start

### Option 1: Run from Python (Windows / macOS / Linux)

Requires **Python 3.10+**.

```bash
git clone git@github.com:alexgomb/ERG_csv_reader.git
cd ERG_csv_reader

python -m venv .venv
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On macOS / Linux:
source .venv/bin/activate

pip install -e .
```

Launch the desktop app:

```bash
# Start empty (or pass CSV files / folders as arguments)
nbio-erg-trace

# Or start directly with the bundled CSO Retimax example files
nbio-erg-trace --examples

# Optional startup overrides
nbio-erg-trace --examples --lang es --theme dark
```

You can also launch via `erg-reader` or `python -m erg_reader`.

### Option 2: Standalone Windows Executable (`.exe`)

Tagged releases (`v*`) automatically trigger the GitHub Actions workflow (`.github/workflows/release-windows.yml`) to compile and attach a self-contained `nBio_ERG_Trace.exe` with bundled `example_files/`.

To build `nBio_ERG_Trace.exe` locally on Windows:

```powershell
pip install -e ".[dev]"
pyinstaller --clean --noconfirm packaging/erg_reader.spec
# Output: dist\nBio_ERG_Trace.exe
```

---

## CSO Retimax CSV Format Supported

The parser natively reads CSO Retimax tab-delimited exports with comma decimals (and dot-decimal fallbacks):

```text
Exam start: 23/10/2026 11:43:35
LEFT - OS
Time(ms)	GAV(uV)	AV1(uV)
0,	-3,881836	-3,881836
0,488281	-3,973389	-3,973389
...
```

### Bundled Example Dataset (`example_files/`)

Sample CSO Retimax recordings from a **C57BL/6 mouse at postnatal day 21 (P21)** covering all **five** standard murine ERG protocols (`Dark-Adapted 3.0`, `Dark-Adapted 10.0`, `Dark-Adapted 3.0 Oscillatory Potentials`, `Light-Adapted 3.0`, and `Light-Adapted 3.0 Flicker`, both `LEFT - OS` and `RIGHT - OD`) are included in [`example_files/`](example_files/) and can be loaded inside either app via **File → Load Example Files** or the **Examples** button.

---

## Keyboard Shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl+O` | Open CSV files |
| `Ctrl+Shift+O` | Open folder (recursive) |
| `Ctrl+S` | Save work session (`.json`) |
| `Ctrl+Shift+C` | Copy current Retimax metrics table to clipboard |
| `Ctrl+R` | Reset active trace markers (`A1`, `B1`, `C1`) to auto-detection |
| `Ctrl+0` | Reset waveform view |
| `G` | Toggle plot grid |
| `Ctrl+Q` | Exit |

---

## Development & Testing

Both the **Python desktop engine** (`src/erg_reader/`) and the **TypeScript web engine** (`web/src/`) are covered by automated unit, edge-case, and UI test suites, tied together by a shared cross-platform golden reference ([`tests/golden_metrics.json`](tests/golden_metrics.json)).

### Python Desktop Suite

```bash
pip install -e ".[dev]"

# Lint
ruff check src tests

# Automated unit, edge-case & headless Qt UI tests
QT_QPA_PLATFORM=offscreen pytest -v
```

### Web App (`web/`)

Requires **Node.js 22+**.

```bash
npm --prefix web ci

# Start local development server
npm --prefix web run dev

# Strict TypeScript check, oxlint, and Vitest unit + edge-case + Python golden parity tests
npm --prefix web run typecheck
npm --prefix web run lint
npm --prefix web test

# Production build for GitHub Pages
VITE_BASE=/ERG_csv_reader/ npm --prefix web run build
```

---

## Changelog

### [0.3.0] — 2026-11-27

#### Added
- **Oscillatory Potentials (`OP1–OP4`) Full Support (Desktop + Web):**
  - Added the `Dark-Adapted 3.0 Oscillatory Potentials` (`dark_adapted_3_ops`) protocol across automatic filename classification (English & Spanish), sidebar manual protocol selector, and configurable Settings detection windows.
  - Implemented non-destructive `compute_op_metrics` / `computeOpMetrics` extracting `OP1–OP4` trough-to-peak wavelets within the physiological ascending-b-wave window (`15–65 ms`), summed OP amplitude (**∑OPs**), individual implicit peak times, dominant `60–200 Hz` OP-band FFT frequency, and wavelet count with 1:1 Python ↔ Web numerical parity.
  - Added a dedicated conditional **Oscillatory Potentials Analysis** bar below the Retimax metrics table in both the PySide6 desktop app and React web app, 7 new OP columns in batch CSV/Excel exports (34 columns total), and OP clipboard TSV output.
- **Bundled C57BL/6 P21 Oscillatory Potentials Examples & Golden Parity:** Added `Dark-Adapted_3_OSCILLATORY_POTENTIAL_ERG_LEFT - OS.csv` and `RIGHT - OD.csv` to `example_files/` and `web/public/example_files/`, documented that the bundled dataset is from a **C57BL/6 mouse at postnatal day 21 (P21)**, and expanded `tests/golden_metrics.json` and both test suites (77 tests total: 51 Python + 26 Web).
- **Enhanced README:** Added adaptive Light/Dark UMH · nBio SVG logos, verified Technology Stack badges, and a Dual-Platform Architecture Mermaid diagram.

### [0.2.0] — 2026-11-27

#### Added
- **Zero-Install Web App (`web/`):** Complete 100% client-side React + TypeScript + Vite single-page application deployed automatically to GitHub Pages at **[https://alexgomb.github.io/ERG_csv_reader/](https://alexgomb.github.io/ERG_csv_reader/)** with 1:1 visual, functional, and numerical parity with the desktop app (raw CSO Retimax CSV/folder drag-and-drop, interactive SVG waveform canvas with draggable `A1`/`B1`/`C1` cursors, reference overlays, manual protocol selector, 30 Hz Flicker FFT analysis, CSV/Excel/PNG/SVG/JSON export, Light/Dark themes, and EN/ES i18n).
- **Automated GitHub Pages Deployment & Dual-Platform CI:** Added `.github/workflows/deploy-pages.yml` and expanded `.github/workflows/ci.yml` to run both Python (`ruff` + `pytest` on Ubuntu & Windows) and Web (`tsc` + `oxlint` + `vitest` + `vite build`) on every push and pull request.
- **Comprehensive Unit, Edge-Case & Cross-Platform Golden Parity Tests:**
  - Expanded Python test suite (`test_parser_edge_cases.py`, `test_analysis_edge_cases.py`, `test_exporters_edge_cases.py`, `test_ui.py`) covering BOM/CP1252/dot-decimal/malformed CSVs, short/flat/degenerate signals, zero-crossing `C1`, out-of-bounds markers, Unicode CSV/Excel/JSON round-trips, EN/ES i18n parity, and pure-vector SVG asset checks.
  - Added Vitest + Testing Library web test suite (`parser.test.ts`, `analysis.test.ts`, `exporters.test.ts`, `architecture.test.ts`, `app.test.tsx`) validating 1:1 numerical parity against `tests/golden_metrics.json` across all 8 real CSO Retimax CSVs, SciPy-identical peak tie-breaking, multi-sheet `.xlsx` round-trips, recursive directory drag-and-drop, and corrupt `localStorage` recovery.

#### Fixed
- Fixed edge cases in `src/erg_reader/analysis.py` for empty arrays (`n = 0` previously yielded `b1_idx = -1`) and zero-timestep inputs (`dt_ms = 0` previously raised `ZeroDivisionError` in `rfftfreq`).

### [0.1.2] — 2026-11-26

#### Added
- Manual **Protocol** selector dropdown in the left sidebar (`Dark-Adapted 3.0`, `Dark-Adapted 10.0`, `Light-Adapted 3.0`, `Light-Adapted 3.0 Flicker`, `Custom / Unknown`) to override automatic protocol classification at any time, immediately toggling the 30 Hz Flicker analysis bar and recalculating automatic markers while preserving manual cursor edits.
- Manual protocol overrides are now saved and restored inside `.json` work sessions.

#### Improved
- Prioritized the 140–185 ms recording duration check in `infer_protocol` so renamed 30 Hz Flicker CSVs without `"flicker"` in their filename are still auto-detected accurately.

### [0.1.1] — 2026-11-26

#### Added
- Pure vector SVG **UMH · nBio** institutional logo (`umh_nbio_light.svg` / `umh_nbio_dark.svg`) rendered at 2× HiDPI in the left sidebar and About dialog, adapting cleanly to Light and Dark modes.
- Added institutional affiliation in the About dialog: **Grupo nBio · Instituto de Bioingeniería · Universidad Miguel Hernández** (`http://nbio.umh.es`).
- Bundled SVG assets in both `pyproject.toml` package data and the PyInstaller `nBio_ERG_Trace.exe` Windows release build.

### [0.1.0] — 2026-11-26

#### Added
- Initial release of **nBio ERG-Trace** desktop application (`PySide6` + `PyQtGraph` + `NumPy` + `SciPy` + `OpenPyXL`).
- CSO Retimax CSV parser supporting comma/dot decimals, CRLF/UTF-8/CP1252 encodings, dynamic average columns (`AV1`, `GAV`, `AV2`...), and strict internal eye-header detection (`LEFT - OS` vs `RIGHT - OD`).
- Retimax-inspired left-eye (`LEFT - OS`) desktop interface with editable subject/exam metadata, recursive drag-and-drop CSV/folder loading, and checkable reference waveform overlays (`GNS` style).
- Protocol-aware automatic detection (`Dark-Adapted 3.0`, `Dark-Adapted 10.0`, `Light-Adapted 3.0`, `Light-Adapted 3.0 Flicker`) with configurable mouse physiological time windows (ms) and draggable `A1`/`B1`/`C1` cursors snapped 1:1 to raw samples.
- Retimax-style metrics table (`Amplitude (µV)` and `Peak time (ms)` for `A1`, `B1`, `C1`, highlighted `A1-B1`, `B1-C1`) plus dedicated 30 Hz Flicker analysis bar (mean peak-to-trough ± SD, FFT fundamental & peak-to-peak, dominant frequency, cycles).
- Pure display controls (`±250 µV`, magnifier `0.25x–25x`, `▲`/`▼` scale steps, `Auto-Scale`, zoom/pan, grid toggle, trace column selector).
- Batch export to UTF-8 CSV and formatted Excel (`.xlsx`), clipboard TSV copy, high-resolution PNG and native SVG plot export, and `.json` work session save/load.
- Live English / Spanish (`EN`/`ES`) localization and Light / Dark themes with `QSettings` persistence.
- Bundled CSO Retimax `example_files/`, automated `pytest` + `pytest-qt` test suite, PyInstaller Windows `.spec`, and GitHub Actions CI & Windows `.exe` release workflows.
- MIT License and in-app attribution.

---

## Contributors & License

- **Author:** Alejandro Gombau García ([GitHub](https://github.com/alexgomb) · [LinkedIn](https://www.linkedin.com/in/alejandro-gombau/)) · Grupo nBio, Instituto de Bioingeniería, Universidad Miguel Hernández
- **Contributors:** [Gemini](https://github.com/gemini-code-assist) (`@gemini-code-assist`) & [Antigravity](https://github.com/apps/antigravity-for-github)
- **License:** [MIT License](LICENSE)
