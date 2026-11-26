"""Parser for CSO Retimax exported ERG CSV files."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

from erg_reader.analysis import auto_detect_markers
from erg_reader.models import (
    DetectionConfig,
    ERGProtocol,
    ERGSessionRecord,
    EyeSide,
    MouseMetadata,
)

GENERIC_PARENT_NAMES = {
    "",
    "example_files",
    "examples",
    "example",
    "csv",
    "csvs",
    "data",
    "erg",
    "erg_reader",
    "erg_csv_reader",
    "nbio_erg_trace",
    "nbio-erg-trace",
    "exports",
    "export",
    "retimax",
    "desktop",
    "documents",
    "downloads",
    "tmp",
    "temp",
}


class ERGParseError(ValueError):
    """Raised when a file cannot be parsed as a valid CSO Retimax CSV."""


@dataclass
class BatchLoadResult:
    """Outcome of loading one or more CSV files or directories."""

    records: list[ERGSessionRecord]
    skipped_right_od: list[Path]
    errors: list[tuple[Path, str]]


def _read_lines_with_fallback(path: Path) -> list[str]:
    """Read text lines supporting UTF-8-SIG, UTF-8, and CP1252/Latin-1 Windows exports."""
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = raw.decode(encoding)
            return [line.rstrip("\r\n") for line in text.splitlines() if line.strip()]
        except UnicodeDecodeError:
            continue
    raise ERGParseError(f"Unsupported text encoding in {path.name}")


def _parse_eye(line: str) -> EyeSide:
    """Detect recorded eye strictly from the internal CSV eye header line."""
    upper = line.strip().upper()
    if "LEFT" in upper or re.search(r"\bOS\b", upper):
        return EyeSide.LEFT_OS
    if "RIGHT" in upper or re.search(r"\bOD\b", upper):
        return EyeSide.RIGHT_OD
    return EyeSide.UNKNOWN


def _detect_delimiter(header_line: str) -> str:
    """Determine column separator from the column header line."""
    if "\t" in header_line:
        return "\t"
    if ";" in header_line:
        return ";"
    return ","


def _parse_float(token: str, decimal_comma: bool) -> float:
    cleaned = token.strip()
    if decimal_comma:
        cleaned = cleaned.replace(",", ".")
    return float(cleaned)


def infer_protocol(file_name: str, time_ms: np.ndarray) -> ERGProtocol:
    """Infer murine ERG protocol from filename conventions and recording duration."""
    low = file_name.lower()
    if "flicker" in low:
        return ERGProtocol.LIGHT_ADAPTED_3_FLICKER
    if "light" in low or "photopic" in low or re.search(r"\bla[\s_-]?3", low):
        return ERGProtocol.LIGHT_ADAPTED_3
    if "dark" in low or "scotopic" in low or re.search(r"\bda[\s_-]", low):
        if re.search(r"(?:^|[^0-9])10(?:\.0)?(?:[^0-9]|$)", low):
            return ERGProtocol.DARK_ADAPTED_10
        if re.search(r"(?:^|[^0-9])3(?:\.0)?(?:[^0-9]|$)", low):
            return ERGProtocol.DARK_ADAPTED_3
    if len(time_ms) > 10 and 140.0 <= float(time_ms[-1]) <= 185.0:
        return ERGProtocol.LIGHT_ADAPTED_3_FLICKER
    return ERGProtocol.UNKNOWN


def infer_metadata(path: Path, exam_start: str, protocol: ERGProtocol) -> MouseMetadata:
    """Auto-populate editable mouse/exam metadata from parent folder and filename."""
    exam_label = protocol.display_name
    if protocol == ERGProtocol.UNKNOWN:
        stem = re.sub(r"[\s_-]*(LEFT|RIGHT)\s*-\s*(OS|OD)\s*$", "", path.stem, flags=re.IGNORECASE)
        exam_label = stem.replace("_", " ").strip().upper() or protocol.display_name

    parent_name = path.parent.name.strip()
    strain = ""
    mouse_id = ""
    age = ""

    if parent_name and parent_name.lower() not in GENERIC_PARENT_NAMES:
        cleaned_parent = parent_name.replace("_", " ").strip()
        mouse_id = cleaned_parent
        tokens = cleaned_parent.split()
        if tokens:
            strain = tokens[0]
        age_match = re.search(r"\b(P\d+|\d+\s*(?:w|wk|wks|m|mo|mos|d|days?))\b", cleaned_parent, re.IGNORECASE)
        if age_match:
            age = age_match.group(1).upper()

    return MouseMetadata(
        strain_lastname=strain,
        mouse_id_name=mouse_id,
        age=age,
        exam=exam_label,
        exam_start=exam_start,
    )


def _select_default_channel(channel_names: list[str]) -> str:
    """Prefer AV1(uV) (Retimax primary average trace), falling back to GAV(uV) or first channel."""
    for preferred in ("AV1(uV)", "AV1", "GAV(uV)", "GAV"):
        for col in channel_names:
            if col.strip().upper() == preferred.upper():
                return col
    return channel_names[0]


def parse_retimax_csv(
    path: str | Path,
    config: DetectionConfig | None = None,
) -> ERGSessionRecord:
    """Parse a single CSO Retimax CSV file into an ERGSessionRecord."""
    file_path = Path(path)
    if not file_path.is_file():
        raise ERGParseError(f"File not found: {file_path}")

    lines = _read_lines_with_fallback(file_path)
    if len(lines) < 5:
        raise ERGParseError(f"File {file_path.name} has too few lines to be a Retimax ERG CSV.")

    # Locate the Time(ms) header row (standard Retimax puts it on line index 2).
    header_idx = -1
    for idx in range(min(8, len(lines))):
        if "time" in lines[idx].lower() and ("uv" in lines[idx].lower() or "µv" in lines[idx].lower()):
            header_idx = idx
            break
    if header_idx < 0:
        raise ERGParseError(
            f"Could not find Retimax column header (Time(ms) / uV) in {file_path.name}."
        )

    exam_start = ""
    eye = EyeSide.UNKNOWN
    for meta_line in lines[:header_idx]:
        lower = meta_line.lower()
        if "exam start" in lower:
            _, _, remainder = meta_line.partition(":")
            exam_start = remainder.strip()
        else:
            parsed_eye = _parse_eye(meta_line)
            if parsed_eye != EyeSide.UNKNOWN:
                eye = parsed_eye

    header_line = lines[header_idx]
    delimiter = _detect_delimiter(header_line)
    raw_headers = [col.strip() for col in header_line.split(delimiter) if col.strip()]
    if len(raw_headers) < 2:
        raise ERGParseError(f"Expected at least Time and 1 signal column in {file_path.name}.")

    channel_names = raw_headers[1:]
    decimal_comma = delimiter != ","

    time_values: list[float] = []
    channel_buffers: list[list[float]] = [[] for _ in channel_names]

    for row_idx, row in enumerate(lines[header_idx + 1 :], start=header_idx + 2):
        tokens = [tok.strip() for tok in row.split(delimiter)]
        # Drop trailing empty cells caused by trailing tab in Retimax exports.
        while tokens and tokens[-1] == "":
            tokens.pop()
        if not tokens:
            continue
        if len(tokens) < 1 + len(channel_names):
            raise ERGParseError(
                f"Malformed data row at line {row_idx} in {file_path.name}: expected "
                f"{1 + len(channel_names)} columns, got {len(tokens)}."
            )
        try:
            t_val = _parse_float(tokens[0], decimal_comma=decimal_comma)
            y_vals = [
                _parse_float(tokens[1 + c_idx], decimal_comma=decimal_comma)
                for c_idx in range(len(channel_names))
            ]
        except ValueError as exc:
            raise ERGParseError(
                f"Invalid numeric value at line {row_idx} in {file_path.name}: {exc}"
            ) from exc

        time_values.append(t_val)
        for c_idx, val in enumerate(y_vals):
            channel_buffers[c_idx].append(val)

    if len(time_values) < 4:
        raise ERGParseError(f"Insufficient waveform samples ({len(time_values)}) in {file_path.name}.")

    time_arr = np.asarray(time_values, dtype=np.float64)
    channels = {
        name: np.asarray(buf, dtype=np.float64)
        for name, buf in zip(channel_names, channel_buffers)
    }
    active_channel = _select_default_channel(channel_names)
    protocol = infer_protocol(file_path.name, time_arr)
    metadata = infer_metadata(file_path, exam_start=exam_start, protocol=protocol)

    cfg = config or DetectionConfig()
    markers = auto_detect_markers(
        time_ms=time_arr,
        signal_uv=channels[active_channel],
        protocol=protocol,
        config=cfg,
    )

    return ERGSessionRecord(
        record_id=uuid.uuid4().hex[:12],
        file_path=str(file_path.resolve()),
        file_name=file_path.name,
        eye=eye,
        protocol=protocol,
        time_ms=time_arr,
        channels=channels,
        active_channel=active_channel,
        metadata=metadata,
        markers=markers,
        overlay_enabled=False,
    )


def discover_csv_files(paths: Iterable[str | Path]) -> list[Path]:
    """Expand a mix of CSV files and folders (recursively) into sorted unique CSV paths."""
    found: list[Path] = []
    seen: set[Path] = set()
    for raw_path in paths:
        p = Path(raw_path)
        if p.is_file() and p.suffix.lower() == ".csv":
            resolved = p.resolve()
            if resolved not in seen:
                seen.add(resolved)
                found.append(resolved)
        elif p.is_dir():
            for child in sorted(p.rglob("*")):
                if child.is_file() and child.suffix.lower() == ".csv":
                    resolved = child.resolve()
                    if resolved not in seen:
                        seen.add(resolved)
                        found.append(resolved)
    return found


def load_csv_batch(
    paths: Iterable[str | Path],
    config: DetectionConfig | None = None,
) -> BatchLoadResult:
    """Parse multiple CSV files/folders, filtering RIGHT - OD according to configuration."""
    cfg = config or DetectionConfig()
    csv_files = discover_csv_files(paths)
    records: list[ERGSessionRecord] = []
    skipped_right_od: list[Path] = []
    errors: list[tuple[Path, str]] = []

    for csv_path in csv_files:
        try:
            record = parse_retimax_csv(csv_path, config=cfg)
        except ERGParseError as exc:
            errors.append((csv_path, str(exc)))
            continue

        if record.eye == EyeSide.RIGHT_OD and not cfg.include_right_od:
            skipped_right_od.append(csv_path)
            continue

        records.append(record)

    return BatchLoadResult(
        records=records,
        skipped_right_od=skipped_right_od,
        errors=errors,
    )
