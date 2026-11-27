"""Comprehensive edge-case unit tests for ERG peak detection, metrics, and Flicker FFT."""

from __future__ import annotations

import numpy as np
import pytest

from erg_reader.analysis import (
    auto_detect_markers,
    compute_flicker_metrics,
    compute_peak_metrics,
    snap_time_to_index,
)
from erg_reader.models import (
    DetectionConfig,
    DetectionWindow,
    ERGProtocol,
    MarkerIndices,
)


def test_auto_detect_degenerate_short_arrays() -> None:
    for n in (0, 1, 2):
        t = np.arange(n, dtype=np.float64)
        y = np.zeros(n, dtype=np.float64)
        markers = auto_detect_markers(t, y, ERGProtocol.DARK_ADAPTED_3)
        assert markers.is_manual is False
        assert markers.a1_idx >= 0
        assert markers.b1_idx >= 0
        assert markers.c1_idx >= 0


def test_auto_detect_flat_zero_waveform_maintains_strict_order() -> None:
    t = np.linspace(0.0, 250.0, 512)
    y = np.zeros_like(t)
    for proto in ERGProtocol:
        m = auto_detect_markers(t, y, proto)
        assert 0 <= m.a1_idx < m.b1_idx < m.c1_idx < len(t)
        pm = compute_peak_metrics(t, y, m)
        assert pm.a1_b1_uv == 0.0
        assert pm.b1_c1_uv == 0.0
        assert pm.a1_b1_ms > 0.0
        assert pm.b1_c1_ms > 0.0


def test_auto_detect_all_negative_and_monotonic_c1_fallbacks() -> None:
    t = np.linspace(0.0, 250.0, 512)
    # Strictly negative waveform with a peak at 55ms and smooth negative monotonic drop
    y = -50.0 - 100.0 * np.exp(-((t - 20.0) / 6.0) ** 2) + 40.0 * np.exp(-((t - 55.0) / 10.0) ** 2) - 0.1 * t
    m = auto_detect_markers(t, y, ERGProtocol.DARK_ADAPTED_3)
    assert m.a1_idx < m.b1_idx < m.c1_idx
    assert 15.0 <= t[m.a1_idx] <= 25.0
    assert 50.0 <= t[m.b1_idx] <= 60.0

    # Smooth zero crossing in C1 window without local minima (descending straight line past 0)
    y_zero = np.where(t < 30.0, -80.0, np.where(t < 60.0, 150.0, 150.0 - (t - 60.0) * 2.0))
    m_zero = auto_detect_markers(t, y_zero, ERGProtocol.DARK_ADAPTED_3)
    # Zero crossing happens around t = 135 ms
    assert abs(t[m_zero.c1_idx] - 135.0) < 2.0


def test_auto_detect_windows_outside_signal_range() -> None:
    t = np.linspace(0.0, 50.0, 100)
    y = -10.0 * np.sin(t / 10.0)
    cfg = DetectionConfig(
        windows={
            ERGProtocol.DARK_ADAPTED_3: DetectionWindow(
                a_min_ms=200.0,
                a_max_ms=240.0,
                b_min_ms=260.0,
                b_max_ms=300.0,
                c_min_ms=320.0,
                c_max_ms=400.0,
            )
        }
    )
    m = auto_detect_markers(t, y, ERGProtocol.DARK_ADAPTED_3, config=cfg)
    assert 0 <= m.a1_idx < len(t)
    assert 0 <= m.b1_idx < len(t)
    assert 0 <= m.c1_idx < len(t)


def test_compute_peak_metrics_clamps_out_of_bounds_indices() -> None:
    t = np.array([0.0, 10.0, 20.0, 30.0])
    y = np.array([1.0, -50.0, 100.0, 5.0])
    pm = compute_peak_metrics(t, y, MarkerIndices(a1_idx=-10, b1_idx=2, c1_idx=999))
    assert pm.a1_ms == 0.0 and pm.a1_uv == 1.0
    assert pm.b1_ms == 20.0 and pm.b1_uv == 100.0
    assert pm.c1_ms == 30.0 and pm.c1_uv == 5.0
    assert pm.a1_b1_uv == 99.0
    assert pm.b1_c1_uv == 95.0


def test_snap_time_to_index_edge_cases() -> None:
    assert snap_time_to_index(np.array([], dtype=np.float64), 10.0) == 0
    t = np.array([0.0, 5.0, 10.0, 15.0])
    assert snap_time_to_index(t, -100.0) == 0
    assert snap_time_to_index(t, 100.0) == 3
    assert snap_time_to_index(t, 7.4) == 1
    assert snap_time_to_index(t, 7.6) == 2


def test_flicker_metrics_edge_cases() -> None:
    # Too short (< 8 samples)
    fl_short = compute_flicker_metrics(np.array([0.0, 1.0, 2.0]), np.array([1.0, -1.0, 1.0]))
    assert fl_short.cycles_detected == 0
    assert fl_short.mean_peak_to_trough_uv == 0.0
    assert fl_short.fft_fundamental_amp_uv == 0.0

    # Flat constant signal with large DC offset -> zero amplitude, zero cycles
    t_ms = np.linspace(0.0, 166.66, 512, endpoint=False)
    y_flat = np.full_like(t_ms, -42.5)
    fl_flat = compute_flicker_metrics(t_ms, y_flat)
    assert fl_flat.cycles_detected == 0
    assert fl_flat.mean_peak_to_trough_uv == 0.0
    assert fl_flat.fft_fundamental_amp_uv == pytest.approx(0.0, abs=1e-9)

    # 30 Hz sine wave + large DC offset (-100 uV) -> DC must NOT distort FFT or peak-to-trough
    y_dc = -100.0 + 15.0 * np.sin(2.0 * np.pi * 30.0 * (t_ms / 1000.0))
    fl_dc = compute_flicker_metrics(t_ms, y_dc)
    assert fl_dc.dominant_freq_hz == pytest.approx(30.0, abs=0.5)
    assert fl_dc.fft_fundamental_amp_uv == pytest.approx(15.0, abs=0.2)
    assert fl_dc.fft_peak_to_peak_uv == pytest.approx(30.0, abs=0.4)
    assert fl_dc.mean_peak_to_trough_uv == pytest.approx(30.0, abs=0.2)

    # Degenerate zero time step guard (all timestamps identical)
    t_zero_dt = np.zeros(32, dtype=np.float64)
    y_wave = np.sin(np.linspace(0.0, 4.0 * np.pi, 32))
    fl_dt0 = compute_flicker_metrics(t_zero_dt, y_wave)
    assert np.isfinite(fl_dt0.mean_peak_to_trough_uv)
    assert np.isfinite(fl_dt0.fft_fundamental_amp_uv)
