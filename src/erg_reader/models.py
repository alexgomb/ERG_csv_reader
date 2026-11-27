"""Core data models for ERG traces, mouse metadata, markers, and metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


class EyeSide(str, Enum):
    """Recorded eye identifier parsed from CSO Retimax CSV header."""

    LEFT_OS = "LEFT - OS"
    RIGHT_OD = "RIGHT - OD"
    UNKNOWN = "UNKNOWN"


class ERGProtocol(str, Enum):
    """Supported mouse ERG recording protocols."""

    DARK_ADAPTED_3 = "dark_adapted_3"
    DARK_ADAPTED_10 = "dark_adapted_10"
    DARK_ADAPTED_3_OPS = "dark_adapted_3_ops"
    LIGHT_ADAPTED_3 = "light_adapted_3"
    LIGHT_ADAPTED_3_FLICKER = "light_adapted_3_flicker"
    UNKNOWN = "unknown"

    @property
    def display_name(self) -> str:
        """Retimax-style canonical display name for the protocol."""
        mapping = {
            ERGProtocol.DARK_ADAPTED_3: "DARK-ADAPTED 3.0 ERG",
            ERGProtocol.DARK_ADAPTED_10: "DARK-ADAPTED 10.0 ERG",
            ERGProtocol.DARK_ADAPTED_3_OPS: "DARK-ADAPTED 3.0 OSCILLATORY POTENTIALS",
            ERGProtocol.LIGHT_ADAPTED_3: "LIGHT-ADAPTED 3.0 ERG",
            ERGProtocol.LIGHT_ADAPTED_3_FLICKER: "LIGHT-ADAPTED 3.0 FLICKER ERG",
            ERGProtocol.UNKNOWN: "CUSTOM ERG",
        }
        return mapping[self]

    @property
    def short_label(self) -> str:
        """Compact protocol tag for lists and badges."""
        mapping = {
            ERGProtocol.DARK_ADAPTED_3: "DA 3.0",
            ERGProtocol.DARK_ADAPTED_10: "DA 10.0",
            ERGProtocol.DARK_ADAPTED_3_OPS: "OPs",
            ERGProtocol.LIGHT_ADAPTED_3: "LA 3.0",
            ERGProtocol.LIGHT_ADAPTED_3_FLICKER: "Flicker",
            ERGProtocol.UNKNOWN: "ERG",
        }
        return mapping[self]


@dataclass
class DetectionWindow:
    """Physiological search windows (in milliseconds) for A1, B1, and C1 markers."""

    a_min_ms: float
    a_max_ms: float
    b_min_ms: float
    b_max_ms: float
    c_min_ms: float
    c_max_ms: float

    def to_dict(self) -> dict[str, float]:
        return {
            "a_min_ms": float(self.a_min_ms),
            "a_max_ms": float(self.a_max_ms),
            "b_min_ms": float(self.b_min_ms),
            "b_max_ms": float(self.b_max_ms),
            "c_min_ms": float(self.c_min_ms),
            "c_max_ms": float(self.c_max_ms),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DetectionWindow:
        return cls(
            a_min_ms=float(data["a_min_ms"]),
            a_max_ms=float(data["a_max_ms"]),
            b_min_ms=float(data["b_min_ms"]),
            b_max_ms=float(data["b_max_ms"]),
            c_min_ms=float(data["c_min_ms"]),
            c_max_ms=float(data["c_max_ms"]),
        )


def default_detection_windows() -> dict[ERGProtocol, DetectionWindow]:
    """Default mouse ERG physiological search windows calibrated for CSO Retimax exports."""
    return {
        ERGProtocol.DARK_ADAPTED_3: DetectionWindow(
            a_min_ms=8.0,
            a_max_ms=40.0,
            b_min_ms=30.0,
            b_max_ms=110.0,
            c_min_ms=100.0,
            c_max_ms=190.0,
        ),
        ERGProtocol.DARK_ADAPTED_10: DetectionWindow(
            a_min_ms=6.0,
            a_max_ms=35.0,
            b_min_ms=25.0,
            b_max_ms=100.0,
            c_min_ms=95.0,
            c_max_ms=190.0,
        ),
        ERGProtocol.DARK_ADAPTED_3_OPS: DetectionWindow(
            a_min_ms=14.0,
            a_max_ms=32.0,
            b_min_ms=28.0,
            b_max_ms=48.0,
            c_min_ms=36.0,
            c_max_ms=60.0,
        ),
        ERGProtocol.LIGHT_ADAPTED_3: DetectionWindow(
            a_min_ms=8.0,
            a_max_ms=35.0,
            b_min_ms=30.0,
            b_max_ms=100.0,
            c_min_ms=95.0,
            c_max_ms=190.0,
        ),
        ERGProtocol.LIGHT_ADAPTED_3_FLICKER: DetectionWindow(
            a_min_ms=15.0,
            a_max_ms=45.0,
            b_min_ms=30.0,
            b_max_ms=65.0,
            c_min_ms=50.0,
            c_max_ms=85.0,
        ),
        ERGProtocol.UNKNOWN: DetectionWindow(
            a_min_ms=6.0,
            a_max_ms=45.0,
            b_min_ms=25.0,
            b_max_ms=120.0,
            c_min_ms=95.0,
            c_max_ms=210.0,
        ),
    }


@dataclass
class DetectionConfig:
    """User-configurable analysis and file-filtering preferences."""

    windows: dict[ERGProtocol, DetectionWindow] = field(default_factory=default_detection_windows)
    include_right_od: bool = False

    def get_window(self, protocol: ERGProtocol) -> DetectionWindow:
        return self.windows.get(protocol, default_detection_windows()[ERGProtocol.UNKNOWN])

    def to_dict(self) -> dict[str, Any]:
        return {
            "include_right_od": bool(self.include_right_od),
            "windows": {proto.value: win.to_dict() for proto, win in self.windows.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DetectionConfig:
        defaults = default_detection_windows()
        raw_windows = data.get("windows", {})
        windows: dict[ERGProtocol, DetectionWindow] = {}
        for proto, default_win in defaults.items():
            if proto.value in raw_windows:
                try:
                    windows[proto] = DetectionWindow.from_dict(raw_windows[proto.value])
                except (KeyError, TypeError, ValueError):
                    windows[proto] = default_win
            else:
                windows[proto] = default_win
        return cls(
            windows=windows,
            include_right_od=bool(data.get("include_right_od", False)),
        )


@dataclass
class MouseMetadata:
    """Editable subject and exam metadata matching Retimax's left sidebar."""

    strain_lastname: str = ""
    mouse_id_name: str = ""
    age: str = ""
    exam: str = ""
    exam_start: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "strain_lastname": self.strain_lastname,
            "mouse_id_name": self.mouse_id_name,
            "age": self.age,
            "exam": self.exam,
            "exam_start": self.exam_start,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MouseMetadata:
        return cls(
            strain_lastname=str(data.get("strain_lastname", "")),
            mouse_id_name=str(data.get("mouse_id_name", "")),
            age=str(data.get("age", "")),
            exam=str(data.get("exam", "")),
            exam_start=str(data.get("exam_start", "")),
            notes=str(data.get("notes", "")),
        )


@dataclass
class MarkerIndices:
    """Sample indices for A1, B1, and C1 waveform cursors."""

    a1_idx: int
    b1_idx: int
    c1_idx: int
    is_manual: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "a1_idx": int(self.a1_idx),
            "b1_idx": int(self.b1_idx),
            "c1_idx": int(self.c1_idx),
            "is_manual": bool(self.is_manual),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MarkerIndices:
        return cls(
            a1_idx=int(data["a1_idx"]),
            b1_idx=int(data["b1_idx"]),
            c1_idx=int(data["c1_idx"]),
            is_manual=bool(data.get("is_manual", False)),
        )


@dataclass(frozen=True)
class PeakMetrics:
    """Retimax-compatible ERG amplitude (µV) and peak time (ms) summary metrics."""

    a1_uv: float
    a1_ms: float
    b1_uv: float
    b1_ms: float
    c1_uv: float
    c1_ms: float
    a1_b1_uv: float
    a1_b1_ms: float
    b1_c1_uv: float
    b1_c1_ms: float


@dataclass(frozen=True)
class FlickerMetrics:
    """Dedicated 30 Hz Flicker ERG metrics (cycle peak-to-trough and FFT fundamental)."""

    mean_peak_to_trough_uv: float
    std_peak_to_trough_uv: float
    fft_fundamental_amp_uv: float
    fft_peak_to_peak_uv: float
    dominant_freq_hz: float
    cycles_detected: int
    first_peak_time_ms: float


@dataclass(frozen=True)
class OPMetrics:
    """Dedicated Oscillatory Potentials (OP1-OP4) metrics computed directly on raw Retimax OP trace."""

    op_amplitudes_uv: tuple[float, ...]
    op_peak_times_ms: tuple[float, ...]
    sum_op_amplitude_uv: float
    max_op_amplitude_uv: float
    dominant_freq_hz: float
    fft_band_amp_uv: float
    op_count: int


@dataclass
class ERGSessionRecord:
    """Complete loaded ERG CSV trace with metadata, markers, and overlay state."""

    record_id: str
    file_path: str
    file_name: str
    eye: EyeSide
    protocol: ERGProtocol
    time_ms: np.ndarray
    channels: dict[str, np.ndarray]
    active_channel: str
    metadata: MouseMetadata
    markers: MarkerIndices
    overlay_enabled: bool = False

    @property
    def active_signal(self) -> np.ndarray:
        """Voltage array (µV) for the currently selected trace channel."""
        if self.active_channel in self.channels:
            return self.channels[self.active_channel]
        first_key = next(iter(self.channels))
        return self.channels[first_key]

    @property
    def available_channels(self) -> list[str]:
        return list(self.channels.keys())

    @property
    def duration_ms(self) -> float:
        if len(self.time_ms) == 0:
            return 0.0
        return float(self.time_ms[-1])
