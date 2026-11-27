"""Comprehensive edge-case unit tests for CSV/Excel exporters and JSON session persistence."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
from openpyxl import load_workbook

from erg_reader.exporters import (
    EXPORT_COLUMNS,
    export_summary_csv,
    export_summary_xlsx,
    load_session_json,
    save_session_json,
)
from erg_reader.models import DetectionConfig, ERGProtocol
from erg_reader.parser import load_csv_batch

EXAMPLE_DIR = Path(__file__).resolve().parents[1] / "example_files"


def test_export_empty_records_produces_valid_header_only_files(tmp_path: Path) -> None:
    csv_path = export_summary_csv([], tmp_path / "empty.csv")
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        rows = list(reader)
    assert header == EXPORT_COLUMNS
    assert rows == []

    xlsx_path = export_summary_xlsx([], tmp_path / "empty.xlsx")
    wb = load_workbook(xlsx_path)
    ws = wb["ERG Summary"]
    assert ws.max_row == 1
    assert [ws.cell(1, c).value for c in range(1, len(EXPORT_COLUMNS) + 1)] == EXPORT_COLUMNS


def test_export_special_characters_unicode_quotes_commas(tmp_path: Path) -> None:
    rec = load_csv_batch([EXAMPLE_DIR / "Dark-Adapted_3_ERG_RIGHT_LEFT - OS.csv"]).records[0]
    rec.metadata.strain_lastname = 'C57BL/6J, "WT"'
    rec.metadata.mouse_id_name = "Ratón #1 — Español"
    rec.metadata.notes = 'Amplitud normal; ojo izquierdo, "OS"'

    csv_path = export_summary_csv([rec], tmp_path / "unicode.csv")
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["Strain / Lastname"] == 'C57BL/6J, "WT"'
    assert rows[0]["Mouse ID / Name"] == "Ratón #1 — Español"
    assert rows[0]["Notes"] == 'Amplitud normal; ojo izquierdo, "OS"'

    xlsx_path = export_summary_xlsx([rec], tmp_path / "unicode.xlsx")
    wb = load_workbook(xlsx_path)
    ws = wb["ERG Summary"]
    assert ws.cell(2, EXPORT_COLUMNS.index("Mouse ID / Name") + 1).value == "Ratón #1 — Español"


def test_load_session_edge_cases_missing_csv_invalid_protocol_clamped_markers(tmp_path: Path) -> None:
    # 1. Invalid JSON structure
    bad_json = tmp_path / "bad.json"
    bad_json.write_text(json.dumps({"not_records": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid ERG session"):
        load_session_json(bad_json)

    # 2. Moved CSV next to session file (relative fallback) + missing CSV warning + invalid protocol + OOB markers
    local_copy = tmp_path / "Dark-Adapted_10_ERG_LEFT - OS.csv"
    local_copy.write_bytes((EXAMPLE_DIR / "Dark-Adapted_10_ERG_LEFT - OS.csv").read_bytes())

    session_file = tmp_path / "session.json"
    payload = {
        "schema_version": 1,
        "active_record_id": "rec_moved",
        "detection_config": DetectionConfig().to_dict(),
        "records": [
            {
                "record_id": "rec_moved",
                "file_path": "/nonexistent/original/path/Dark-Adapted_10_ERG_LEFT - OS.csv",
                "file_name": "Dark-Adapted_10_ERG_LEFT - OS.csv",
                "protocol": "not_a_real_protocol",
                "active_channel": "NON_EXISTENT_CH",
                "overlay_enabled": True,
                "metadata": {"strain_lastname": "C57", "mouse_id_name": "MovedMouse"},
                "markers": {"a1_idx": -50, "b1_idx": 100, "c1_idx": 99999, "is_manual": True},
            },
            {
                "record_id": "rec_missing",
                "file_path": "/completely/missing/file.csv",
                "file_name": "missing.csv",
                "markers": {"a1_idx": 1, "b1_idx": 2, "c1_idx": 3},
            },
        ],
    }
    session_file.write_text(json.dumps(payload), encoding="utf-8")

    records, _cfg, active_id, warnings = load_session_json(session_file)
    assert len(records) == 1
    assert len(warnings) == 1
    assert active_id == "rec_moved"

    rec = records[0]
    assert rec.protocol == ERGProtocol.DARK_ADAPTED_10  # fell back safely from invalid protocol
    assert rec.active_channel == "AV1(uV)"  # kept valid channel when saved channel didn't exist
    assert rec.markers.a1_idx == 0  # clamped from -50
    assert rec.markers.b1_idx == 100
    assert rec.markers.c1_idx == len(rec.time_ms) - 1  # clamped from 99999
    assert rec.overlay_enabled is True


def test_save_and_reload_empty_session(tmp_path: Path) -> None:
    session_file = save_session_json([], tmp_path / "empty_session.json")
    records, cfg, active_id, warnings = load_session_json(session_file)
    assert records == []
    assert active_id is None
    assert warnings == []
    assert cfg.include_right_od is False
