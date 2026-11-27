"""Export utilities (batch CSV, styled Excel .xlsx, clipboard TSV) and JSON session persistence."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from erg_reader import APP_NAME, __author__, __version__
from erg_reader.analysis import (
    compute_flicker_metrics,
    compute_op_metrics,
    compute_peak_metrics,
)
from erg_reader.models import (
    DetectionConfig,
    ERGProtocol,
    ERGSessionRecord,
    MarkerIndices,
    MouseMetadata,
)
from erg_reader.parser import ERGParseError, parse_retimax_csv

SESSION_SCHEMA_VERSION = 1

EXPORT_COLUMNS = [
    "File Name",
    "Eye",
    "Protocol",
    "Channel",
    "Strain / Lastname",
    "Mouse ID / Name",
    "Age",
    "Exam",
    "Exam Start",
    "Markers Mode",
    "A1 Amplitude (uV)",
    "A1 Peak Time (ms)",
    "B1 Amplitude (uV)",
    "B1 Peak Time (ms)",
    "C1 Amplitude (uV)",
    "C1 Peak Time (ms)",
    "A1-B1 Amplitude (uV)",
    "A1-B1 Peak Time (ms)",
    "B1-C1 Amplitude (uV)",
    "B1-C1 Peak Time (ms)",
    "Flicker Mean P-T (uV)",
    "Flicker SD P-T (uV)",
    "Flicker FFT Amp (uV)",
    "Flicker FFT P-P (uV)",
    "Flicker Freq (Hz)",
    "Flicker Cycles",
    "OP Sum Amplitude (uV)",
    "OP1 Amplitude (uV)",
    "OP2 Amplitude (uV)",
    "OP3 Amplitude (uV)",
    "OP4 Amplitude (uV)",
    "OP Dominant Freq (Hz)",
    "OP Wavelets",
    "Notes",
]


def _op_amp_at(amps: tuple[float, ...], idx: int) -> float | str:
    return round(amps[idx], 2) if idx < len(amps) else ""


def build_summary_rows(records: Sequence[ERGSessionRecord]) -> list[dict[str, Any]]:
    """Build flat tabular summary rows for all loaded ERG records."""
    rows: list[dict[str, Any]] = []
    for rec in records:
        metrics = compute_peak_metrics(rec.time_ms, rec.active_signal, rec.markers)
        flicker = (
            compute_flicker_metrics(rec.time_ms, rec.active_signal)
            if rec.protocol == ERGProtocol.LIGHT_ADAPTED_3_FLICKER
            else None
        )
        ops = (
            compute_op_metrics(rec.time_ms, rec.active_signal)
            if rec.protocol == ERGProtocol.DARK_ADAPTED_3_OPS
            else None
        )
        rows.append(
            {
                "File Name": rec.file_name,
                "Eye": rec.eye.value,
                "Protocol": rec.protocol.display_name,
                "Channel": rec.active_channel,
                "Strain / Lastname": rec.metadata.strain_lastname,
                "Mouse ID / Name": rec.metadata.mouse_id_name,
                "Age": rec.metadata.age,
                "Exam": rec.metadata.exam,
                "Exam Start": rec.metadata.exam_start,
                "Markers Mode": "Manual" if rec.markers.is_manual else "Auto",
                "A1 Amplitude (uV)": round(metrics.a1_uv, 2),
                "A1 Peak Time (ms)": round(metrics.a1_ms, 2),
                "B1 Amplitude (uV)": round(metrics.b1_uv, 2),
                "B1 Peak Time (ms)": round(metrics.b1_ms, 2),
                "C1 Amplitude (uV)": round(metrics.c1_uv, 2),
                "C1 Peak Time (ms)": round(metrics.c1_ms, 2),
                "A1-B1 Amplitude (uV)": round(metrics.a1_b1_uv, 2),
                "A1-B1 Peak Time (ms)": round(metrics.a1_b1_ms, 2),
                "B1-C1 Amplitude (uV)": round(metrics.b1_c1_uv, 2),
                "B1-C1 Peak Time (ms)": round(metrics.b1_c1_ms, 2),
                "Flicker Mean P-T (uV)": round(flicker.mean_peak_to_trough_uv, 2) if flicker else "",
                "Flicker SD P-T (uV)": round(flicker.std_peak_to_trough_uv, 2) if flicker else "",
                "Flicker FFT Amp (uV)": round(flicker.fft_fundamental_amp_uv, 2) if flicker else "",
                "Flicker FFT P-P (uV)": round(flicker.fft_peak_to_peak_uv, 2) if flicker else "",
                "Flicker Freq (Hz)": round(flicker.dominant_freq_hz, 2) if flicker else "",
                "Flicker Cycles": flicker.cycles_detected if flicker else "",
                "OP Sum Amplitude (uV)": round(ops.sum_op_amplitude_uv, 2) if ops else "",
                "OP1 Amplitude (uV)": _op_amp_at(ops.op_amplitudes_uv, 0) if ops else "",
                "OP2 Amplitude (uV)": _op_amp_at(ops.op_amplitudes_uv, 1) if ops else "",
                "OP3 Amplitude (uV)": _op_amp_at(ops.op_amplitudes_uv, 2) if ops else "",
                "OP4 Amplitude (uV)": _op_amp_at(ops.op_amplitudes_uv, 3) if ops else "",
                "OP Dominant Freq (Hz)": round(ops.dominant_freq_hz, 2) if ops else "",
                "OP Wavelets": ops.op_count if ops else "",
                "Notes": rec.metadata.notes,
            }
        )
    return rows


def export_summary_csv(records: Sequence[ERGSessionRecord], output_path: str | Path) -> Path:
    """Export summary metrics for all loaded ERG traces to a UTF-8 CSV file."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = build_summary_rows(records)
    with out.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return out


def export_summary_xlsx(records: Sequence[ERGSessionRecord], output_path: str | Path) -> Path:
    """Export summary metrics to a formatted Excel workbook (.xlsx) ready for Prism/R/Excel."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = build_summary_rows(records)

    wb = Workbook()
    ws = wb.active
    ws.title = "ERG Summary"

    header_fill = PatternFill(start_color="1E3A5F", end_color="1E3A5F", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    highlight_fill = PatternFill(start_color="FFF59D", end_color="FFF59D", fill_type="solid")
    highlight_font = Font(name="Calibri", size=11, bold=True, color="111827")
    zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1"),
    )

    ws.append(EXPORT_COLUMNS)
    for col_idx in range(1, len(EXPORT_COLUMNS) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border
    ws.row_dimensions[1].height = 28

    a1_b1_amp_col = EXPORT_COLUMNS.index("A1-B1 Amplitude (uV)") + 1

    for row_idx, row_data in enumerate(rows, start=2):
        values = [row_data[col] for col in EXPORT_COLUMNS]
        ws.append(values)
        is_even = row_idx % 2 == 0
        for col_idx, val in enumerate(values, start=1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.border = thin_border
            if isinstance(val, float):
                cell.number_format = "0.00"
                cell.alignment = Alignment(horizontal="right", vertical="center")
            elif isinstance(val, int):
                cell.alignment = Alignment(horizontal="right", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

            if col_idx == a1_b1_amp_col:
                cell.fill = highlight_fill
                cell.font = highlight_font
            elif is_even:
                cell.fill = zebra_fill

    # Auto-fit column widths
    for col_idx, col_name in enumerate(EXPORT_COLUMNS, start=1):
        max_len = len(col_name)
        for row_idx in range(2, len(rows) + 2):
            val = ws.cell(row=row_idx, column=col_idx).value
            if val is not None:
                max_len = max(max_len, len(str(val)))
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 4, 34)

    ws.freeze_panes = "B2"

    # Second metadata sheet with tool & author attribution
    info_ws = wb.create_sheet(title="Export Info")
    info_ws.append(["Application", APP_NAME])
    info_ws.append(["Version", __version__])
    info_ws.append(["Author", __author__])
    info_ws.append(["Exported (UTC)", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")])
    info_ws.append(["Records Exported", len(records)])
    info_ws.column_dimensions["A"].width = 20
    info_ws.column_dimensions["B"].width = 36

    wb.save(out)
    return out


def format_record_clipboard_tsv(record: ERGSessionRecord) -> str:
    """Format the current record's Retimax-style metrics table as tab-separated text."""
    m = compute_peak_metrics(record.time_ms, record.active_signal, record.markers)
    lines = [
        f"{record.eye.value}\tA1\tB1\tC1\tA1-B1\tB1-C1",
        f"Amplitude (uV)\t{m.a1_uv:.2f}\t{m.b1_uv:.2f}\t{m.c1_uv:.2f}\t{m.a1_b1_uv:.2f}\t{m.b1_c1_uv:.2f}",
        f"Peak time (ms)\t{m.a1_ms:.2f}\t{m.b1_ms:.2f}\t{m.c1_ms:.2f}\t{m.a1_b1_ms:.2f}\t{m.b1_c1_ms:.2f}",
    ]
    if record.protocol == ERGProtocol.LIGHT_ADAPTED_3_FLICKER:
        fl = compute_flicker_metrics(record.time_ms, record.active_signal)
        lines.append("")
        lines.append("Flicker Metrics\tMean P-T (uV)\tSD P-T (uV)\tFFT Amp (uV)\tFFT P-P (uV)\tFreq (Hz)\tCycles")
        lines.append(
            f"30 Hz Flicker\t{fl.mean_peak_to_trough_uv:.2f}\t{fl.std_peak_to_trough_uv:.2f}\t"
            f"{fl.fft_fundamental_amp_uv:.2f}\t{fl.fft_peak_to_peak_uv:.2f}\t"
            f"{fl.dominant_freq_hz:.2f}\t{fl.cycles_detected}"
        )
    elif record.protocol == ERGProtocol.DARK_ADAPTED_3_OPS:
        ops = compute_op_metrics(record.time_ms, record.active_signal)
        op_vals = [f"{ops.op_amplitudes_uv[i]:.2f}" if i < len(ops.op_amplitudes_uv) else "—" for i in range(4)]
        lines.append("")
        lines.append("Oscillatory Potentials\tSum OPs (uV)\tOP1 (uV)\tOP2 (uV)\tOP3 (uV)\tOP4 (uV)\tFreq (Hz)\tWavelets")
        lines.append(
            f"DA 3.0 OPs\t{ops.sum_op_amplitude_uv:.2f}\t"
            + "\t".join(op_vals)
            + f"\t{ops.dominant_freq_hz:.2f}\t{ops.op_count}"
        )
    return "\n".join(lines)


def save_session_json(
    records: Sequence[ERGSessionRecord],
    output_path: str | Path,
    config: DetectionConfig | None = None,
    active_record_id: str | None = None,
) -> Path:
    """Persist loaded CSV paths, manual cursor indices, overlays, and metadata to JSON."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "schema_version": SESSION_SCHEMA_VERSION,
        "app": APP_NAME,
        "version": __version__,
        "saved_utc": datetime.now(timezone.utc).isoformat(),
        "active_record_id": active_record_id,
        "detection_config": (config or DetectionConfig()).to_dict(),
        "records": [
            {
                "record_id": rec.record_id,
                "file_path": rec.file_path,
                "file_name": rec.file_name,
                "protocol": rec.protocol.value,
                "active_channel": rec.active_channel,
                "overlay_enabled": rec.overlay_enabled,
                "metadata": rec.metadata.to_dict(),
                "markers": rec.markers.to_dict(),
            }
            for rec in records
        ],
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def load_session_json(
    session_path: str | Path,
) -> tuple[list[ERGSessionRecord], DetectionConfig, str | None, list[str]]:
    """Reload a saved JSON work session, restoring metadata, protocol, active channels, and cursors."""
    path = Path(session_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "records" not in data:
        raise ValueError("Invalid ERG session file format.")

    config = DetectionConfig.from_dict(data.get("detection_config", {}))
    active_record_id = data.get("active_record_id")
    records: list[ERGSessionRecord] = []
    warnings: list[str] = []

    for entry in data.get("records", []):
        raw_fp = Path(entry["file_path"])
        # Support relative fallback next to the session file if moved
        if not raw_fp.is_file():
            alt = path.parent / entry.get("file_name", raw_fp.name)
            if alt.is_file():
                raw_fp = alt
        try:
            rec = parse_retimax_csv(raw_fp, config=config)
        except ERGParseError as exc:
            warnings.append(str(exc))
            continue

        rec.record_id = str(entry.get("record_id", rec.record_id))
        saved_proto = entry.get("protocol")
        if saved_proto:
            try:
                rec.protocol = ERGProtocol(saved_proto)
            except ValueError:
                pass
        saved_channel = entry.get("active_channel")
        if saved_channel in rec.channels:
            rec.active_channel = saved_channel
        rec.overlay_enabled = bool(entry.get("overlay_enabled", False))
        rec.metadata = MouseMetadata.from_dict(entry.get("metadata", {}))
        if "markers" in entry:
            saved_markers = MarkerIndices.from_dict(entry["markers"])
            n = len(rec.time_ms)
            rec.markers = MarkerIndices(
                a1_idx=max(0, min(saved_markers.a1_idx, n - 1)),
                b1_idx=max(0, min(saved_markers.b1_idx, n - 1)),
                c1_idx=max(0, min(saved_markers.c1_idx, n - 1)),
                is_manual=saved_markers.is_manual,
            )
        records.append(rec)

    return records, config, active_record_id, warnings
