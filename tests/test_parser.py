"""Tests for CSO Retimax CSV parsing, internal eye filtering, and metadata inference."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from erg_reader.models import DetectionConfig, ERGProtocol, EyeSide
from erg_reader.parser import ERGParseError, discover_csv_files, load_csv_batch, parse_retimax_csv

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = REPO_ROOT / "example_files"


def test_parse_dark_adapted_3_left_uses_internal_eye_not_filename() -> None:
    """Filename contains 'RIGHT' before '_LEFT - OS', so internal header must win."""
    csv_path = EXAMPLE_DIR / "Dark-Adapted_3_ERG_RIGHT_LEFT - OS.csv"
    rec = parse_retimax_csv(csv_path)

    assert rec.eye == EyeSide.LEFT_OS
    assert rec.protocol == ERGProtocol.DARK_ADAPTED_3
    assert rec.metadata.exam_start == "23/10/2026 11:43:35"
    assert rec.active_channel == "AV1(uV)"
    assert set(rec.available_channels) == {"GAV(uV)", "AV1(uV)"}
    assert len(rec.time_ms) == 512
    assert np.isclose(rec.time_ms[0], 0.0)
    assert np.isclose(rec.time_ms[-1], 249.511719, atol=1e-4)


def test_parse_flicker_duration_and_protocol() -> None:
    csv_path = EXAMPLE_DIR / "Light-Adapted_3_Flicker_ERG_LEFT - OS.csv"
    rec = parse_retimax_csv(csv_path)

    assert rec.eye == EyeSide.LEFT_OS
    assert rec.protocol == ERGProtocol.LIGHT_ADAPTED_3_FLICKER
    assert len(rec.time_ms) == 512
    assert 165.0 < rec.duration_ms < 168.0


def test_parse_oscillatory_potentials_protocol(tmp_path: Path) -> None:
    csv_path = EXAMPLE_DIR / "Dark-Adapted_3_OSCILLATORY_POTENTIAL_ERG_LEFT - OS.csv"
    rec = parse_retimax_csv(csv_path)

    assert rec.eye == EyeSide.LEFT_OS
    assert rec.protocol == ERGProtocol.DARK_ADAPTED_3_OPS
    assert rec.metadata.exam_start == "23/10/2026 11:27:00"
    assert len(rec.time_ms) == 512
    assert np.isclose(rec.time_ms[-1], 249.511719, atol=1e-4)

    # Spanish and shorthand OP filenames should also resolve to DARK_ADAPTED_3_OPS
    renamed = tmp_path / "Potenciales_Oscilatorios_P21_OS.csv"
    renamed.write_bytes(csv_path.read_bytes())
    assert parse_retimax_csv(renamed).protocol == ERGProtocol.DARK_ADAPTED_3_OPS


def test_batch_load_skips_right_od_by_default() -> None:
    result = load_csv_batch([EXAMPLE_DIR])

    assert len(result.records) == 5
    assert len(result.skipped_right_od) == 5
    assert len(result.errors) == 0
    assert all(r.eye == EyeSide.LEFT_OS for r in result.records)


def test_batch_load_includes_right_od_when_enabled() -> None:
    cfg = DetectionConfig(include_right_od=True)
    result = load_csv_batch([EXAMPLE_DIR], config=cfg)

    assert len(result.records) == 10
    assert len(result.skipped_right_od) == 0
    assert sum(1 for r in result.records if r.eye == EyeSide.LEFT_OS) == 5
    assert sum(1 for r in result.records if r.eye == EyeSide.RIGHT_OD) == 5


def test_recursive_folder_discovery_and_mouse_metadata_inference(tmp_path: Path) -> None:
    mouse_dir = tmp_path / "C57_P21"
    mouse_dir.mkdir()
    sample = (EXAMPLE_DIR / "Dark-Adapted_10_ERG_LEFT - OS.csv").read_bytes()
    target = mouse_dir / "Dark-Adapted_10_ERG_LEFT - OS.csv"
    target.write_bytes(sample)

    discovered = discover_csv_files([tmp_path])
    assert discovered == [target.resolve()]

    rec = parse_retimax_csv(target)
    assert rec.metadata.strain_lastname == "C57"
    assert rec.metadata.mouse_id_name == "C57 P21"
    assert rec.metadata.age == "P21"


def test_parse_multi_channel_av2_and_dot_decimals(tmp_path: Path) -> None:
    content = (
        "Exam start: 01/02/2026 09:00:00\r\n"
        "LEFT - OS\r\n"
        "Time(ms)\tGAV(uV)\tAV1(uV)\tAV2(uV)\t\r\n"
        "0.0\t0.0\t-1.0\t-2.0\t\r\n"
        "10.0\t-10.0\t-20.0\t-15.0\t\r\n"
        "25.0\t-50.0\t-60.0\t-55.0\t\r\n"
        "55.0\t120.0\t130.0\t125.0\t\r\n"
        "130.0\t10.0\t5.0\t8.0\t\r\n"
    )
    csv_path = tmp_path / "Dark-Adapted_3_test.csv"
    csv_path.write_text(content, encoding="utf-8")

    rec = parse_retimax_csv(csv_path)
    assert rec.available_channels == ["GAV(uV)", "AV1(uV)", "AV2(uV)"]
    assert rec.active_channel == "AV1(uV)"
    assert np.isclose(rec.channels["AV2(uV)"][3], 125.0)


def test_invalid_csv_raises_parse_error(tmp_path: Path) -> None:
    bad = tmp_path / "not_erg.csv"
    bad.write_text("col1,col2\n1,2\n3,4\n5,6\n7,8\n", encoding="utf-8")
    with pytest.raises(ERGParseError):
        parse_retimax_csv(bad)


def test_renamed_flicker_csv_detected_by_duration_over_light_keyword(tmp_path: Path) -> None:
    sample = (EXAMPLE_DIR / "Light-Adapted_3_Flicker_ERG_LEFT - OS.csv").read_bytes()
    renamed = tmp_path / "Light_mouse01_OS.csv"
    renamed.write_bytes(sample)

    rec = parse_retimax_csv(renamed)
    assert rec.protocol == ERGProtocol.LIGHT_ADAPTED_3_FLICKER

