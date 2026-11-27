"""Protocol-aware peak detection, Retimax-compatible ERG metrics, and Flicker FFT analysis."""

from __future__ import annotations

import numpy as np
from scipy.signal import find_peaks

from erg_reader.models import (
    DetectionConfig,
    ERGProtocol,
    FlickerMetrics,
    MarkerIndices,
    PeakMetrics,
)


def _window_indices(time_ms: np.ndarray, t_min: float, t_max: float) -> np.ndarray:
    """Return sample indices inside [t_min, t_max], or nearest single index if empty."""
    mask = (time_ms >= t_min) & (time_ms <= t_max)
    indices = np.flatnonzero(mask)
    if len(indices) > 0:
        return indices
    target = 0.5 * (t_min + t_max)
    nearest = int(np.argmin(np.abs(time_ms - target)))
    return np.asarray([nearest], dtype=int)


def _clamp_index(idx: int, n_samples: int) -> int:
    return max(0, min(int(idx), n_samples - 1))


def auto_detect_markers(
    time_ms: np.ndarray,
    signal_uv: np.ndarray,
    protocol: ERGProtocol,
    config: DetectionConfig | None = None,
) -> MarkerIndices:
    """Automatically place A1, B1, and C1 markers on raw ERG waveform samples.

    Uses configurable physiological time windows per protocol without modifying
    the underlying raw voltage signal.
    """
    n = len(time_ms)
    if n < 3:
        return MarkerIndices(
            a1_idx=0,
            b1_idx=max(0, min(1, n - 1)),
            c1_idx=max(0, n - 1),
            is_manual=False,
        )

    cfg = config or DetectionConfig()
    win = cfg.get_window(protocol)

    # 1. A1: a-wave trough (minimum voltage inside A1 physiological window)
    a_candidates = _window_indices(time_ms, win.a_min_ms, win.a_max_ms)
    a1_idx = int(a_candidates[int(np.argmin(signal_uv[a_candidates]))])

    # 2. B1: b-wave peak (maximum voltage after A1 inside B1 physiological window)
    b_start = max(win.b_min_ms, float(time_ms[a1_idx]) + 2.0)
    b_end = max(win.b_max_ms, b_start + 5.0)
    b_candidates = _window_indices(time_ms, b_start, b_end)
    b1_idx = int(b_candidates[int(np.argmax(signal_uv[b_candidates]))])
    if b1_idx <= a1_idx and a1_idx + 1 < n:
        b1_idx = a1_idx + 1

    # 3. C1: post-b-wave reference / trough inside C1 physiological window
    min_gap = 6.0 if protocol == ERGProtocol.LIGHT_ADAPTED_3_FLICKER else 15.0
    c_start = max(win.c_min_ms, float(time_ms[b1_idx]) + min_gap)
    c_end = max(win.c_max_ms, c_start + 5.0)
    c_candidates = _window_indices(time_ms, c_start, c_end)

    if protocol == ERGProtocol.LIGHT_ADAPTED_3_FLICKER:
        # Next trough following B1 peak
        c1_idx = int(c_candidates[int(np.argmin(signal_uv[c_candidates]))])
    else:
        # For flash ERGs, locate the post-b-wave baseline return (closest to 0 uV
        # on the descending limb or first local minimum within the C1 window).
        seg = signal_uv[c_candidates]
        local_troughs, _ = find_peaks(-seg, distance=max(2, len(seg) // 10))
        if len(local_troughs) > 0:
            # Choose the earliest notable return trough (mirrors Retimax C1 placement)
            c1_idx = int(c_candidates[int(local_troughs[0])])
        else:
            # Fallback: point closest to 0 uV if descending past baseline, else minimum
            if np.any(seg <= 0.0) and np.any(seg >= 0.0):
                c1_idx = int(c_candidates[int(np.argmin(np.abs(seg)))])
            else:
                c1_idx = int(c_candidates[int(np.argmin(seg))])

    if c1_idx <= b1_idx and b1_idx + 1 < n:
        c1_idx = b1_idx + 1

    return MarkerIndices(
        a1_idx=_clamp_index(a1_idx, n),
        b1_idx=_clamp_index(b1_idx, n),
        c1_idx=_clamp_index(c1_idx, n),
        is_manual=False,
    )


def compute_peak_metrics(
    time_ms: np.ndarray,
    signal_uv: np.ndarray,
    markers: MarkerIndices,
) -> PeakMetrics:
    """Compute Retimax-exact amplitudes (µV) and implicit/peak times (ms) from raw samples."""
    n = len(time_ms)
    a_i = _clamp_index(markers.a1_idx, n)
    b_i = _clamp_index(markers.b1_idx, n)
    c_i = _clamp_index(markers.c1_idx, n)

    a1_uv = float(signal_uv[a_i])
    a1_ms = float(time_ms[a_i])
    b1_uv = float(signal_uv[b_i])
    b1_ms = float(time_ms[b_i])
    c1_uv = float(signal_uv[c_i])
    c1_ms = float(time_ms[c_i])

    return PeakMetrics(
        a1_uv=a1_uv,
        a1_ms=a1_ms,
        b1_uv=b1_uv,
        b1_ms=b1_ms,
        c1_uv=c1_uv,
        c1_ms=c1_ms,
        a1_b1_uv=b1_uv - a1_uv,
        a1_b1_ms=b1_ms - a1_ms,
        b1_c1_uv=b1_uv - c1_uv,
        b1_c1_ms=c1_ms - b1_ms,
    )


def compute_flicker_metrics(
    time_ms: np.ndarray,
    signal_uv: np.ndarray,
    target_freq_hz: float = 30.0,
) -> FlickerMetrics:
    """Compute 30 Hz Flicker ERG cycle peak-to-trough amplitude and FFT fundamental metrics.

    Non-destructive: computed directly from the raw waveform without altering trace values.
    """
    n = len(time_ms)
    if n < 8:
        return FlickerMetrics(
            mean_peak_to_trough_uv=0.0,
            std_peak_to_trough_uv=0.0,
            fft_fundamental_amp_uv=0.0,
            fft_peak_to_peak_uv=0.0,
            dominant_freq_hz=0.0,
            cycles_detected=0,
            first_peak_time_ms=0.0,
        )

    dt_ms = float(np.median(np.diff(time_ms)))
    fs_hz = 1000.0 / dt_ms if dt_ms > 0 else 1000.0

    # Expected cycle spacing in samples (~33.3 ms at 30 Hz)
    min_dist = max(3, int(round(0.65 * fs_hz / target_freq_hz)))
    prominence = max(0.15 * float(np.std(signal_uv)), 0.5)

    peaks, _ = find_peaks(signal_uv, distance=min_dist, prominence=prominence)
    troughs, _ = find_peaks(-signal_uv, distance=min_dist, prominence=prominence)

    # Pair each peak with the nearest adjacent trough (preceding or following)
    amplitudes: list[float] = []
    if len(peaks) > 0 and len(troughs) > 0:
        for pk in peaks:
            nearest_trough = troughs[int(np.argmin(np.abs(troughs - pk)))]
            amplitudes.append(float(signal_uv[pk] - signal_uv[nearest_trough]))

    if amplitudes:
        mean_ptp = float(np.mean(amplitudes))
        std_ptp = float(np.std(amplitudes, ddof=0))
        cycles = len(amplitudes)
        first_peak_ms = float(time_ms[peaks[0]])
    else:
        mean_ptp = float(np.max(signal_uv) - np.min(signal_uv))
        std_ptp = 0.0
        cycles = 0
        first_peak_ms = float(time_ms[int(np.argmax(signal_uv))])

    # Single-sided FFT fundamental component around ~30 Hz (20–45 Hz band)
    centered = signal_uv - float(np.mean(signal_uv))
    freqs = np.fft.rfftfreq(n, d=1.0 / fs_hz)
    spectrum = (2.0 / n) * np.abs(np.fft.rfft(centered))

    band_mask = (freqs >= 20.0) & (freqs <= 45.0)
    if np.any(band_mask):
        band_indices = np.flatnonzero(band_mask)
        best_idx = int(band_indices[int(np.argmax(spectrum[band_indices]))])
    else:
        best_idx = int(np.argmax(spectrum[1:])) + 1 if len(spectrum) > 1 else 0

    dom_freq = float(freqs[best_idx])
    fft_amp = float(spectrum[best_idx])

    return FlickerMetrics(
        mean_peak_to_trough_uv=mean_ptp,
        std_peak_to_trough_uv=std_ptp,
        fft_fundamental_amp_uv=fft_amp,
        fft_peak_to_peak_uv=2.0 * fft_amp,
        dominant_freq_hz=dom_freq,
        cycles_detected=cycles,
        first_peak_time_ms=first_peak_ms,
    )


def snap_time_to_index(time_ms: np.ndarray, target_time_ms: float) -> int:
    """Snap an arbitrary cursor X position (ms) to the closest real sample index."""
    if len(time_ms) == 0:
        return 0
    return int(np.argmin(np.abs(time_ms - target_time_ms)))
