"""Tests for peak detection, Retimax 1:1 amplitude math, and 30 Hz Flicker FFT analysis."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from erg_reader.analysis import (
    auto_detect_markers,
    compute_flicker_metrics,
    compute_peak_metrics,
    snap_time_to_index,
)
from erg_reader.models import MarkerIndices
from erg_reader.parser import parse_retimax_csv

EXAMPLE_DIR = Path(__file__).resolve().parents[1] / "example_files"


def test_retimax_exact_values_on_reference_da3_markers() -> None:
    """Verify exact 1:1 numerical match with Retimax Interfaz.png at its reference cursor timestamps."""
    rec = parse_retimax_csv(EXAMPLE_DIR / "Dark-Adapted_3_ERG_RIGHT_LEFT - OS.csv")
    a_idx = snap_time_to_index(rec.time_ms, 27.83)
    b_idx = snap_time_to_index(rec.time_ms, 48.83)
    c_idx = snap_time_to_index(rec.time_ms, 129.88)

    metrics = compute_peak_metrics(
        rec.time_ms,
        rec.active_signal,
        MarkerIndices(a1_idx=a_idx, b1_idx=b_idx, c1_idx=c_idx, is_manual=True),
    )

    assert metrics.a1_uv == pytest.approx(-135.34, abs=0.02)
    assert metrics.a1_ms == pytest.approx(27.83, abs=0.02)
    assert metrics.b1_uv == pytest.approx(200.05, abs=0.02)
    assert metrics.b1_ms == pytest.approx(48.83, abs=0.02)
    assert metrics.c1_uv == pytest.approx(12.58, abs=0.02)
    assert metrics.c1_ms == pytest.approx(129.88, abs=0.02)
    assert metrics.a1_b1_uv == pytest.approx(335.39, abs=0.02)
    assert metrics.a1_b1_ms == pytest.approx(21.00, abs=0.02)
    assert metrics.b1_c1_uv == pytest.approx(187.48, abs=0.02)
    assert metrics.b1_c1_ms == pytest.approx(81.05, abs=0.02)


def test_auto_detection_all_four_left_eye_protocols() -> None:
    expected = {
        "Dark-Adapted_3_ERG_RIGHT_LEFT - OS.csv": (28.32, 62.50, 353.91),
        "Dark-Adapted_10_ERG_LEFT - OS.csv": (21.00, 50.29, 366.53),
        "Light-Adapted_3_ERG_LEFT - OS.csv": (20.51, 56.15, 48.33),
        "Light-Adapted_3_Flicker_ERG_LEFT - OS.csv": (29.30, 44.92, 13.71),
    }
    for fname, (exp_a_ms, exp_b_ms, exp_ab_uv) in expected.items():
        rec = parse_retimax_csv(EXAMPLE_DIR / fname)
        markers = auto_detect_markers(rec.time_ms, rec.active_signal, rec.protocol)
        m = compute_peak_metrics(rec.time_ms, rec.active_signal, markers)

        assert markers.a1_idx < markers.b1_idx < markers.c1_idx
        assert m.a1_ms == pytest.approx(exp_a_ms, abs=0.5)
        assert m.b1_ms == pytest.approx(exp_b_ms, abs=0.5)
        assert m.a1_b1_uv == pytest.approx(exp_ab_uv, abs=0.1)


def test_flicker_metrics_on_real_and_synthetic_30hz_signal() -> None:
    rec = parse_retimax_csv(EXAMPLE_DIR / "Light-Adapted_3_Flicker_ERG_LEFT - OS.csv")
    fl = compute_flicker_metrics(rec.time_ms, rec.active_signal)

    assert fl.cycles_detected == 5
    assert fl.dominant_freq_hz == pytest.approx(30.0, abs=1.0)
    assert fl.mean_peak_to_trough_uv > 10.0
    assert fl.fft_peak_to_peak_uv == pytest.approx(2.0 * fl.fft_fundamental_amp_uv)

    # Synthetic exact 30 Hz sine wave with amplitude 10 uV (peak-to-peak 20 uV)
    t_ms = np.linspace(0.0, 1000.0 / 3.0, 1024, endpoint=False)  # exactly 10 cycles
    y_uv = 10.0 * np.sin(2.0 * np.pi * 30.0 * (t_ms / 1000.0))
    syn = compute_flicker_metrics(t_ms, y_uv)
    assert syn.dominant_freq_hz == pytest.approx(30.0, abs=0.5)
    assert syn.fft_fundamental_amp_uv == pytest.approx(10.0, abs=0.2)
    assert syn.mean_peak_to_trough_uv == pytest.approx(20.0, abs=0.2)
