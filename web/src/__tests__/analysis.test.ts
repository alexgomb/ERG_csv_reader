import fs from 'node:fs'
import path from 'node:path'

import { describe, expect, it } from 'vitest'

import {
  autoDetectMarkers,
  computeFlickerMetrics,
  computePeakMetrics,
  findPeaks1D,
  snapTimeToIndex,
} from '../core/analysis'
import {
  defaultDetectionConfig,
  getActiveSignal,
  PROTOCOL_ORDER,
  type ERGProtocol,
} from '../core/models'
import { parseRetimaxCsv } from '../core/parser'

const REPO_ROOT = path.resolve(__dirname, '../../..')
const EXAMPLE_DIR = path.join(REPO_ROOT, 'example_files')
const GOLDEN_PATH = path.join(REPO_ROOT, 'tests/golden_metrics.json')

interface GoldenEntry {
  eye: string
  protocol: ERGProtocol
  exam_start: string
  active_channel: string
  n_samples: number
  markers: { a1_idx: number; b1_idx: number; c1_idx: number; is_manual: boolean }
  peak_metrics: Record<string, number>
  flicker_metrics: Record<string, number> | null
}

describe('ERG Analysis & Python 1:1 Golden Parity (web)', () => {
  it('matches Python golden_metrics.json 1:1 across ALL 8 real CSO Retimax CSV files', () => {
    const golden = JSON.parse(fs.readFileSync(GOLDEN_PATH, 'utf-8')) as Record<string, GoldenEntry>
    const fileNames = Object.keys(golden)
    expect(fileNames.length).toBe(8)

    for (const fileName of fileNames) {
      const expected = golden[fileName]
      const bytes = new Uint8Array(fs.readFileSync(path.join(EXAMPLE_DIR, fileName)))
      const rec = parseRetimaxCsv({ name: fileName, content: bytes })

      expect(rec.eye).toBe(expected.eye)
      expect(rec.protocol).toBe(expected.protocol)
      expect(rec.metadata.exam_start).toBe(expected.exam_start)
      expect(rec.active_channel).toBe(expected.active_channel)
      expect(rec.time_ms.length).toBe(expected.n_samples)

      // Exact same sample indices as Python!
      expect(rec.markers).toEqual(expected.markers)

      const pm = computePeakMetrics(rec.time_ms, getActiveSignal(rec), rec.markers)
      expect(pm.a1_uv).toBeCloseTo(expected.peak_metrics.a1_uv, 4)
      expect(pm.a1_ms).toBeCloseTo(expected.peak_metrics.a1_ms, 4)
      expect(pm.b1_uv).toBeCloseTo(expected.peak_metrics.b1_uv, 4)
      expect(pm.b1_ms).toBeCloseTo(expected.peak_metrics.b1_ms, 4)
      expect(pm.c1_uv).toBeCloseTo(expected.peak_metrics.c1_uv, 4)
      expect(pm.c1_ms).toBeCloseTo(expected.peak_metrics.c1_ms, 4)
      expect(pm.a1_b1_uv).toBeCloseTo(expected.peak_metrics.a1_b1_uv, 4)
      expect(pm.a1_b1_ms).toBeCloseTo(expected.peak_metrics.a1_b1_ms, 4)
      expect(pm.b1_c1_uv).toBeCloseTo(expected.peak_metrics.b1_c1_uv, 4)
      expect(pm.b1_c1_ms).toBeCloseTo(expected.peak_metrics.b1_c1_ms, 4)

      if (expected.flicker_metrics) {
        const fl = computeFlickerMetrics(rec.time_ms, getActiveSignal(rec))
        expect(fl.cycles_detected).toBe(expected.flicker_metrics.cycles_detected)
        expect(fl.dominant_freq_hz).toBeCloseTo(expected.flicker_metrics.dominant_freq_hz, 4)
        expect(fl.fft_fundamental_amp_uv).toBeCloseTo(
          expected.flicker_metrics.fft_fundamental_amp_uv,
          4,
        )
        expect(fl.fft_peak_to_peak_uv).toBeCloseTo(expected.flicker_metrics.fft_peak_to_peak_uv, 4)
        expect(fl.mean_peak_to_trough_uv).toBeCloseTo(
          expected.flicker_metrics.mean_peak_to_trough_uv,
          4,
        )
        expect(fl.std_peak_to_trough_uv).toBeCloseTo(
          expected.flicker_metrics.std_peak_to_trough_uv,
          4,
        )
        expect(fl.first_peak_time_ms).toBeCloseTo(expected.flicker_metrics.first_peak_time_ms, 4)
      }
    }
  })

  it('reproduces Retimax Interfaz.png reference values to the second decimal place', () => {
    const bytes = new Uint8Array(
      fs.readFileSync(path.join(EXAMPLE_DIR, 'Dark-Adapted_3_ERG_RIGHT_LEFT - OS.csv')),
    )
    const rec = parseRetimaxCsv({ name: 'Dark-Adapted_3_ERG_RIGHT_LEFT - OS.csv', content: bytes })
    const aIdx = snapTimeToIndex(rec.time_ms, 27.83)
    const bIdx = snapTimeToIndex(rec.time_ms, 48.83)
    const cIdx = snapTimeToIndex(rec.time_ms, 129.88)

    const m = computePeakMetrics(rec.time_ms, getActiveSignal(rec), {
      a1_idx: aIdx,
      b1_idx: bIdx,
      c1_idx: cIdx,
      is_manual: true,
    })
    expect(m.a1_uv).toBeCloseTo(-135.34, 2)
    expect(m.b1_uv).toBeCloseTo(200.05, 2)
    expect(m.c1_uv).toBeCloseTo(12.58, 2)
    expect(m.a1_b1_uv).toBeCloseTo(335.39, 2)
    expect(m.a1_b1_ms).toBeCloseTo(21.0, 2)
    expect(m.b1_c1_uv).toBeCloseTo(187.48, 1)
    expect(m.b1_c1_ms).toBeCloseTo(81.05, 2)
  })

  it('handles degenerate short arrays (0, 1, 2 samples) and flat zero signals safely', () => {
    for (const n of [0, 1, 2]) {
      const t = Array.from({ length: n }, (_, i) => i)
      const y = new Array<number>(n).fill(0)
      const m = autoDetectMarkers(t, y, 'dark_adapted_3')
      expect(m.a1_idx).toBeGreaterThanOrEqual(0)
      expect(m.b1_idx).toBeGreaterThanOrEqual(0)
      expect(m.c1_idx).toBeGreaterThanOrEqual(0)
    }

    const t512 = Array.from({ length: 512 }, (_, i) => (i * 250) / 511)
    const yZero = new Array<number>(512).fill(0)
    for (const proto of PROTOCOL_ORDER) {
      const m = autoDetectMarkers(t512, yZero, proto)
      expect(m.a1_idx).toBeLessThan(m.b1_idx)
      expect(m.b1_idx).toBeLessThan(m.c1_idx)
      const pm = computePeakMetrics(t512, yZero, m)
      expect(pm.a1_b1_uv).toBe(0)
    }
  })

  it('clamps out-of-range windows, out-of-bounds marker indices, and handles zero-crossing C1', () => {
    const t = Array.from({ length: 100 }, (_, i) => (i * 50) / 99)
    const y = t.map((x) => -10 * Math.sin(x / 10))
    const cfg = defaultDetectionConfig()
    cfg.windows.dark_adapted_3 = {
      a_min_ms: 200,
      a_max_ms: 240,
      b_min_ms: 260,
      b_max_ms: 300,
      c_min_ms: 320,
      c_max_ms: 400,
    }
    const m = autoDetectMarkers(t, y, 'dark_adapted_3', cfg)
    expect(m.a1_idx).toBeGreaterThanOrEqual(0)
    expect(m.c1_idx).toBeLessThan(t.length)

    const pm = computePeakMetrics([0, 10, 20, 30], [1, -50, 100, 5], {
      a1_idx: -10,
      b1_idx: 2,
      c1_idx: 999,
      is_manual: true,
    })
    expect(pm.a1_uv).toBe(1)
    expect(pm.b1_uv).toBe(100)
    expect(pm.c1_uv).toBe(5)
    expect(snapTimeToIndex([], 10)).toBe(0)
  })

  it('handles Flicker edge cases: <8 samples, flat DC offset, synthetic 30 Hz + DC, and dt=0', () => {
    const flShort = computeFlickerMetrics([0, 1, 2], [1, -1, 1])
    expect(flShort.cycles_detected).toBe(0)
    expect(flShort.fft_fundamental_amp_uv).toBe(0)

    const n = 512
    const tMs = Array.from({ length: n }, (_, i) => (i * 166.666667) / n)
    const yFlat = new Array<number>(n).fill(-42.5)
    const flFlat = computeFlickerMetrics(tMs, yFlat)
    expect(flFlat.cycles_detected).toBe(0)
    expect(flFlat.fft_fundamental_amp_uv).toBeCloseTo(0, 6)

    const yDc = tMs.map((t) => -100 + 15 * Math.sin(2 * Math.PI * 30 * (t / 1000)))
    const flDc = computeFlickerMetrics(tMs, yDc)
    expect(flDc.dominant_freq_hz).toBeCloseTo(30, 0)
    expect(flDc.fft_fundamental_amp_uv).toBeCloseTo(15, 0)
    expect(flDc.mean_peak_to_trough_uv).toBeCloseTo(30, 0)

    const tZeroDt = new Array<number>(32).fill(0)
    const yWave = Array.from({ length: 32 }, (_, i) => Math.sin((i * 4 * Math.PI) / 32))
    const flDt0 = computeFlickerMetrics(tZeroDt, yWave)
    expect(Number.isFinite(flDt0.fft_fundamental_amp_uv)).toBe(true)
    expect(Number.isFinite(flDt0.mean_peak_to_trough_uv)).toBe(true)
  })

  it('finds flat plateau peaks accurately in findPeaks1D', () => {
    expect(findPeaks1D([0, 1, 5, 5, 5, 1, 0])).toEqual([3])
    expect(findPeaks1D([1, 2])).toEqual([])
  })
})
