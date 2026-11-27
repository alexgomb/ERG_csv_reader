"""Comprehensive edge-case unit tests for the CSO Retimax CSV parser."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from erg_reader.models import DetectionConfig, ERGProtocol, EyeSide
from erg_reader.parser import (
    ERGParseError,
    discover_csv_files,
    infer_metadata,
    infer_protocol,
    load_csv_batch,
    parse_retimax_csv,
)


def _write_csv(path: Path, text: str, encoding: str = "utf-8") -> Path:
    path.write_bytes(text.encode(encoding))
    return path


def test_parse_semicolon_and_comma_delimited_variants(tmp_path: Path) -> None:
    semi = _write_csv(
        tmp_path / "Dark-Adapted_3_semi.csv",
        "Exam start: 10/11/2026 08:15:00\r\n"
        "LEFT - OS\r\n"
        "Time(ms);GAV(uV);AV1(uV)\r\n"
        "0,0;0,0;1,5\r\n"
        "10,0;-20,5;-25,5\r\n"
        "25,0;-100,25;-110,75\r\n"
        "55,0;180,5;190,0\r\n"
        "130,0;10,0;5,25\r\n",
    )
    rec_semi = parse_retimax_csv(semi)
    assert rec_semi.eye == EyeSide.LEFT_OS
    assert rec_semi.protocol == ERGProtocol.DARK_ADAPTED_3
    assert np.isclose(rec_semi.channels["AV1(uV)"][2], -110.75)

    comma = _write_csv(
        tmp_path / "Light-Adapted_3_comma.csv",
        "Exam start: 10/11/2026 08:20:00\n"
        "LEFT - OS\n"
        "Time(ms),GAV(uV),AV1(uV)\n"
        "0.0,-2.5,-3.0\n"
        "15.0,-18.0,-20.0\n"
        "55.0,22.0,25.5\n"
        "120.0,-1.0,-2.0\n"
        "249.5,-5.0,-4.5\n",
    )
    rec_comma = parse_retimax_csv(comma)
    assert rec_comma.protocol == ERGProtocol.LIGHT_ADAPTED_3
    assert np.isclose(rec_comma.channels["AV1(uV)"][2], 25.5)


def test_parse_cp1252_micro_symbol_and_utf8_bom_and_blank_lines(tmp_path: Path) -> None:
    cp1252_file = _write_csv(
        tmp_path / "DA_10_cp1252.csv",
        "Exam start: 12/12/2026 14:00:00\r\n"
        "\r\n"
        "left - os\r\n"
        "Time(ms)\tGAV(µV)\tAV1(µV)\t\r\n"
        "\r\n"
        "0,\t1,0\t2,0\t\r\n"
        "20,\t-120,5\t-130,25\t\r\n"
        "50,\t200,0\t210,75\t\r\n"
        "130,\t15,0\t12,5\t\r\n"
        "249,5\t-5,0\t-4,0\t\r\n",
        encoding="cp1252",
    )
    rec = parse_retimax_csv(cp1252_file)
    assert rec.eye == EyeSide.LEFT_OS
    assert rec.protocol == ERGProtocol.DARK_ADAPTED_10
    assert rec.active_channel == "GAV(µV)" or "AV1" in rec.active_channel
    assert len(rec.time_ms) == 5

    bom_file = _write_csv(
        tmp_path / "Dark-Adapted_3_bom.csv",
        "Exam start: 01/01/2026 00:00:00\n"
        "RIGHT - OD\n"
        "Time(ms)\tAV1(uV)\n"
        "0,\t0,\n"
        "10,\t-5,\n"
        "20,\t5,\n"
        "30,\t0,\n",
        encoding="utf-8-sig",
    )
    rec_bom = parse_retimax_csv(bom_file)
    assert rec_bom.eye == EyeSide.RIGHT_OD
    assert rec_bom.metadata.exam_start == "01/01/2026 00:00:00"


def test_parse_missing_exam_start_and_unknown_eye(tmp_path: Path) -> None:
    minimal = _write_csv(
        tmp_path / "mystery_trace.csv",
        "Unknown Eye Header\n"
        "Time(ms)\tCustomCh(uV)\n"
        "0,\t1,0\n"
        "10,\t-10,0\n"
        "50,\t30,0\n"
        "120,\t2,0\n"
        "249,\t0,0\n",
    )
    rec = parse_retimax_csv(minimal)
    assert rec.eye == EyeSide.UNKNOWN
    assert rec.metadata.exam_start == ""
    assert rec.active_channel == "CustomCh(uV)"
    assert rec.protocol == ERGProtocol.UNKNOWN


@pytest.mark.parametrize(
    ("name", "t_end", "expected"),
    [
        ("DA_3_mouse.csv", 249.5, ERGProtocol.DARK_ADAPTED_3),
        ("Scotopic_10.0_ERG.csv", 249.5, ERGProtocol.DARK_ADAPTED_10),
        ("photopic_3_test.csv", 249.5, ERGProtocol.LIGHT_ADAPTED_3),
        ("LA-3_OS.csv", 249.5, ERGProtocol.LIGHT_ADAPTED_3),
        ("custom_flicker_trace.csv", 249.5, ERGProtocol.LIGHT_ADAPTED_3_FLICKER),
        ("renamed_file_without_keywords.csv", 166.33, ERGProtocol.LIGHT_ADAPTED_3_FLICKER),
        ("completely_generic.csv", 249.5, ERGProtocol.UNKNOWN),
    ],
)
def test_infer_protocol_matrix(name: str, t_end: float, expected: ERGProtocol) -> None:
    t = np.linspace(0.0, t_end, 512)
    assert infer_protocol(name, t) == expected


@pytest.mark.parametrize(
    ("folder_name", "exp_strain", "exp_mouse", "exp_age"),
    [
        ("example_files", "", "", ""),
        ("nbio_erg_trace", "", "", ""),
        ("Desktop", "", "", ""),
        ("C57BL6_P21", "C57BL6", "C57BL6 P21", "P21"),
        ("rd10_4wks", "rd10", "rd10 4wks", "4WKS"),
        ("WT_Mouse7_3m", "WT", "WT Mouse7 3m", "3M"),
    ],
)
def test_infer_metadata_parent_folder_rules(
    tmp_path: Path, folder_name: str, exp_strain: str, exp_mouse: str, exp_age: str
) -> None:
    folder = tmp_path / folder_name
    folder.mkdir(exist_ok=True)
    csv_path = folder / "Dark-Adapted_3_LEFT - OS.csv"
    meta = infer_metadata(csv_path, "23/10/2026 11:00:00", ERGProtocol.DARK_ADAPTED_3)
    assert meta.strain_lastname == exp_strain
    assert meta.mouse_id_name == exp_mouse
    assert meta.age == exp_age
    assert meta.exam == "DARK-ADAPTED 3.0 ERG"


def test_parse_error_cases(tmp_path: Path) -> None:
    # 1. Missing file
    with pytest.raises(ERGParseError, match="File not found"):
        parse_retimax_csv(tmp_path / "does_not_exist.csv")

    # 2. Too few lines
    short = _write_csv(tmp_path / "short.csv", "Exam start: x\nLEFT - OS\nTime(ms)\tAV1(uV)\n0,\t1,\n")
    with pytest.raises(ERGParseError, match="too few lines"):
        parse_retimax_csv(short)

    # 3. Missing column header
    no_hdr = _write_csv(tmp_path / "no_hdr.csv", "a\nb\nc\nd\ne\nf\n")
    with pytest.raises(ERGParseError, match="column header"):
        parse_retimax_csv(no_hdr)

    # 4. Single column only
    one_col = _write_csv(
        tmp_path / "one_col.csv",
        "Exam start: x\nLEFT - OS\nTime(ms) uV\n0,\n1,\n2,\n3,\n4,\n",
    )
    with pytest.raises(ERGParseError, match="at least Time and 1 signal"):
        parse_retimax_csv(one_col)

    # 5. Truncated data row
    trunc = _write_csv(
        tmp_path / "trunc.csv",
        "Exam start: x\nLEFT - OS\nTime(ms)\tGAV(uV)\tAV1(uV)\n"
        "0,\t1,0\t1,0\n"
        "1,\t2,0\n"
        "2,\t3,0\t3,0\n"
        "3,\t4,0\t4,0\n",
    )
    with pytest.raises(ERGParseError, match="Malformed data row"):
        parse_retimax_csv(trunc)

    # 6. Non-numeric cell
    bad_num = _write_csv(
        tmp_path / "bad_num.csv",
        "Exam start: x\nLEFT - OS\nTime(ms)\tAV1(uV)\n"
        "0,\t1,0\n"
        "1,\tNOT_A_NUMBER\n"
        "2,\t3,0\n"
        "3,\t4,0\n",
    )
    with pytest.raises(ERGParseError, match="Invalid numeric value"):
        parse_retimax_csv(bad_num)

    # 7. Insufficient samples (< 4)
    few_samples = _write_csv(
        tmp_path / "few_samples.csv",
        "Exam start: x\nLEFT - OS\nExtra line\nTime(ms)\tAV1(uV)\n0,\t1,0\n1,\t2,0\n2,\t3,0\n",
    )
    with pytest.raises(ERGParseError, match="Insufficient waveform samples"):
        parse_retimax_csv(few_samples)


def test_discover_and_batch_load_mixed_valid_od_corrupt_and_duplicates(tmp_path: Path) -> None:
    sub = tmp_path / "MouseA" / "Day1"
    sub.mkdir(parents=True)
    valid_os = _write_csv(
        sub / "Dark-Adapted_3_OS.CSV",
        "Exam start: 01/01/2026 10:00:00\nLEFT - OS\nTime(ms)\tAV1(uV)\n"
        "0,\t0,\n20,\t-100,\n50,\t180,\n120,\t10,\n249,\t-5,\n",
    )
    valid_od = _write_csv(
        sub / "Dark-Adapted_3_OD.csv",
        "Exam start: 01/01/2026 10:00:00\nRIGHT - OD\nTime(ms)\tAV1(uV)\n"
        "0,\t0,\n20,\t-1,\n50,\t1,\n120,\t0,\n249,\t0,\n",
    )
    corrupt = _write_csv(sub / "broken.csv", "bad\nfile\ncontents\nonly\nhere\n")
    (sub / "readme.txt").write_text("ignore me", encoding="utf-8")

    # Passing both the file and parent folder should deduplicate cleanly
    discovered = discover_csv_files([valid_os, tmp_path, valid_od])
    assert len(discovered) == 3

    res = load_csv_batch([valid_os, tmp_path], config=DetectionConfig(include_right_od=False))
    assert len(res.records) == 1
    assert res.records[0].file_path == str(valid_os.resolve())
    assert res.skipped_right_od == [valid_od.resolve()]
    assert len(res.errors) == 1
    assert res.errors[0][0] == corrupt.resolve()
