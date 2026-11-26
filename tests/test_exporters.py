"""Tests for batch CSV export, formatted Excel .xlsx export, clipboard TSV, and JSON session round-trip."""

from __future__ import annotations

import csv
from pathlib import Path

from openpyxl import load_workbook

from erg_reader.exporters import (
    export_summary_csv,
    export_summary_xlsx,
    format_record_clipboard_tsv,
    load_session_json,
    save_session_json,
)
from erg_reader.models import DetectionConfig
from erg_reader.parser import load_csv_batch

EXAMPLE_DIR = Path(__file__).resolve().parents[1] / "example_files"


def test_export_batch_csv_and_xlsx(tmp_path: Path) -> None:
    records = load_csv_batch([EXAMPLE_DIR]).records
    assert len(records) == 4
    records[0].metadata.strain_lastname = "C57"
    records[0].metadata.mouse_id_name = "C57 P21"
    records[0].metadata.age = "P21"

    csv_out = export_summary_csv(records, tmp_path / "summary.csv")
    assert csv_out.is_file()
    with csv_out.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 4
    assert rows[0]["Strain / Lastname"] == "C57"
    assert rows[0]["Mouse ID / Name"] == "C57 P21"
    flicker_row = next(r for r in rows if "Flicker" in r["File Name"])
    assert float(flicker_row["Flicker Freq (Hz)"]) == 30.0

    xlsx_out = export_summary_xlsx(records, tmp_path / "summary.xlsx")
    assert xlsx_out.is_file()
    wb = load_workbook(xlsx_out)
    assert "ERG Summary" in wb.sheetnames
    assert "Export Info" in wb.sheetnames
    ws = wb["ERG Summary"]
    assert ws.max_row == 5  # 1 header + 4 records
    info_ws = wb["Export Info"]
    info_values = [info_ws.cell(r, 2).value for r in range(1, info_ws.max_row + 1)]
    assert "Alejandro Gombau García" in info_values


def test_clipboard_tsv_format() -> None:
    records = load_csv_batch([EXAMPLE_DIR]).records
    flicker = next(r for r in records if "Flicker" in r.file_name)
    tsv = format_record_clipboard_tsv(flicker)
    assert "LEFT - OS\tA1\tB1\tC1\tA1-B1\tB1-C1" in tsv
    assert "Amplitude (uV)" in tsv
    assert "Peak time (ms)" in tsv
    assert "30 Hz Flicker" in tsv


def test_session_json_save_and_reload_preserves_manual_markers_and_metadata(tmp_path: Path) -> None:
    cfg = DetectionConfig(include_right_od=False)
    records = load_csv_batch([EXAMPLE_DIR], config=cfg).records

    target = records[1]
    target.metadata.strain_lastname = "C57BL/6J"
    target.metadata.mouse_id_name = "Mouse-04"
    target.metadata.age = "P21"
    target.metadata.notes = "Verified manually"
    target.markers.a1_idx = 57
    target.markers.b1_idx = 100
    target.markers.c1_idx = 266
    target.markers.is_manual = True
    records[0].overlay_enabled = True

    session_file = save_session_json(
        records,
        tmp_path / "work_session.json",
        config=cfg,
        active_record_id=target.record_id,
    )

    loaded_records, loaded_cfg, active_id, warnings = load_session_json(session_file)
    assert warnings == []
    assert len(loaded_records) == 4
    assert active_id == target.record_id
    assert loaded_cfg.include_right_od is False

    restored = next(r for r in loaded_records if r.record_id == target.record_id)
    assert restored.metadata.strain_lastname == "C57BL/6J"
    assert restored.metadata.mouse_id_name == "Mouse-04"
    assert restored.metadata.notes == "Verified manually"
    assert restored.markers.a1_idx == 57
    assert restored.markers.b1_idx == 100
    assert restored.markers.c1_idx == 266
    assert restored.markers.is_manual is True
    assert loaded_records[0].overlay_enabled is True
