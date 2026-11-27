/**
 * Protocol-aware peak detection, Retimax 1:1 amplitude math, and 30 Hz Flicker FFT analysis.
 * Designed for exact numerical parity with Python `erg_reader.analysis`.
 */

import {
  defaultDetectionConfig,
  type DetectionConfig,
  type ERGProtocol,
  type FlickerMetrics,
  type MarkerIndices,
  type OPMetrics,
  type PeakMetrics,
} from './models'

function clampIndex(idx: number, nSamples: number): number {
  if (nSamples <= 0) return 0
  return Math.max(0, Math.min(Math.trunc(idx), nSamples - 1))
}

function windowIndices(timeMs: readonly number[], tMin: number, tMax: number): number[] {
  const indices: number[] = []
  for (let i = 0; i < timeMs.length; i++) {
    if (timeMs[i] >= tMin && timeMs[i] <= tMax) {
      indices.push(i)
    }
  }
  if (indices.length > 0) {
    return indices
  }
  const target = 0.5 * (tMin + tMax)
  return [snapTimeToIndex(timeMs, target)]
}

/**
 * SciPy-compatible 1D local maxima finder supporting minimum peak distance and prominence.
 */
export function findPeaks1D(
  x: readonly number[],
  options: { distance?: number; prominence?: number } = {},
): number[] {
  const n = x.length
  if (n < 3) return []

  // 1. Detect all strict local maxima (handling flat plateaus identically to scipy.signal._local_maxima_1d)
  const rawPeaks: number[] = []
  let i = 1
  while (i < n - 1) {
    if (x[i - 1] < x[i]) {
      let iAhead = i + 1
      while (iAhead < n - 1 && x[iAhead] === x[i]) {
        iAhead++
      }
      if (x[iAhead] < x[i]) {
        // Midpoint of flat plateau (integer floor matches scipy)
        rawPeaks.push(Math.floor((i + iAhead - 1) / 2))
        i = iAhead
        continue
      }
    }
    i++
  }

  let peaks = rawPeaks

  // 2. Minimum distance filter: greedy selection by descending peak height (exact scipy algorithm)
  const distance = options.distance ?? 1
  if (distance > 1 && peaks.length > 1) {
    const order = [...peaks].sort((a, b) => {
      if (x[b] !== x[a]) return x[b] - x[a]
      return b - a
    })
    const keep = new Map<number, boolean>()
    for (const p of peaks) keep.set(p, true)

    const peakPos = new Map<number, number>()
    peaks.forEach((p, idx) => peakPos.set(p, idx))

    for (const p of order) {
      if (!keep.get(p)) continue
      const pos = peakPos.get(p)!
      // Suppress neighbors within distance on left
      for (let j = pos - 1; j >= 0 && p - peaks[j] < distance; j--) {
        keep.set(peaks[j], false)
      }
      // Suppress neighbors within distance on right
      for (let j = pos + 1; j < peaks.length && peaks[j] - p < distance; j++) {
        keep.set(peaks[j], false)
      }
    }
    peaks = peaks.filter((p) => keep.get(p))
  }

  // 3. Minimum prominence filter (exact scipy definition: peak height minus higher of left/right contour minimums)
  const minProm = options.prominence
  if (minProm !== undefined && minProm > 0 && peaks.length > 0) {
    peaks = peaks.filter((p) => {
      const h = x[p]
      let leftMin = h
      for (let j = p - 1; j >= 0; j--) {
        if (x[j] > h) break
        if (x[j] < leftMin) leftMin = x[j]
      }
      let rightMin = h
      for (let j = p + 1; j < n; j++) {
        if (x[j] > h) break
        if (x[j] < rightMin) rightMin = x[j]
      }
      const refBase = Math.max(leftMin, rightMin)
      return h - refBase >= minProm
    })
  }

  return peaks
}

export function autoDetectMarkers(
  timeMs: readonly number[],
  signalUv: readonly number[],
  protocol: ERGProtocol,
  config?: DetectionConfig,
): MarkerIndices {
  const n = timeMs.length
  if (n < 3) {
    return {
      a1_idx: 0,
      b1_idx: Math.max(0, Math.min(1, n - 1)),
      c1_idx: Math.max(0, n - 1),
      is_manual: false,
    }
  }

  const cfg = config ?? defaultDetectionConfig()
  const win = cfg.windows[protocol] ?? cfg.windows.unknown

  // 1. A1: a-wave trough (minimum voltage inside A1 window)
  const aCandidates = windowIndices(timeMs, win.a_min_ms, win.a_max_ms)
  let a1Idx = aCandidates[0]
  for (const idx of aCandidates) {
    if (signalUv[idx] < signalUv[a1Idx]) {
      a1Idx = idx
    }
  }

  // 2. B1: b-wave peak (maximum voltage after A1 inside B1 window)
  const bStart = Math.max(win.b_min_ms, timeMs[a1Idx] + 2.0)
  const bEnd = Math.max(win.b_max_ms, bStart + 5.0)
  const bCandidates = windowIndices(timeMs, bStart, bEnd)
  let b1Idx = bCandidates[0]
  for (const idx of bCandidates) {
    if (signalUv[idx] > signalUv[b1Idx]) {
      b1Idx = idx
    }
  }
  if (b1Idx <= a1Idx && a1Idx + 1 < n) {
    b1Idx = a1Idx + 1
  }

  // 3. C1: post-b-wave reference / trough inside C1 window
  const minGap =
    protocol === 'dark_adapted_3_ops' ? 4.0 : protocol === 'light_adapted_3_flicker' ? 6.0 : 15.0
  const cStart = Math.max(win.c_min_ms, timeMs[b1Idx] + minGap)
  const cEnd = Math.max(win.c_max_ms, cStart + 5.0)
  const cCandidates = windowIndices(timeMs, cStart, cEnd)

  let c1Idx = cCandidates[0]
  if (protocol === 'light_adapted_3_flicker' || protocol === 'dark_adapted_3_ops') {
    for (const idx of cCandidates) {
      if (signalUv[idx] < signalUv[c1Idx]) {
        c1Idx = idx
      }
    }
  } else {
    const seg = cCandidates.map((idx) => signalUv[idx])
    const negSeg = seg.map((v) => -v)
    const localTroughs = findPeaks1D(negSeg, {
      distance: Math.max(2, Math.floor(seg.length / 10)),
    })
    if (localTroughs.length > 0) {
      c1Idx = cCandidates[localTroughs[0]]
    } else {
      const hasNeg = seg.some((v) => v <= 0.0)
      const hasPos = seg.some((v) => v >= 0.0)
      if (hasNeg && hasPos) {
        let bestOffset = 0
        for (let k = 1; k < seg.length; k++) {
          if (Math.abs(seg[k]) < Math.abs(seg[bestOffset])) {
            bestOffset = k
          }
        }
        c1Idx = cCandidates[bestOffset]
      } else {
        for (const idx of cCandidates) {
          if (signalUv[idx] < signalUv[c1Idx]) {
            c1Idx = idx
          }
        }
      }
    }
  }

  if (c1Idx <= b1Idx && b1Idx + 1 < n) {
    c1Idx = b1Idx + 1
  }

  return {
    a1_idx: clampIndex(a1Idx, n),
    b1_idx: clampIndex(b1Idx, n),
    c1_idx: clampIndex(c1Idx, n),
    is_manual: false,
  }
}

export function computePeakMetrics(
  timeMs: readonly number[],
  signalUv: readonly number[],
  markers: MarkerIndices,
): PeakMetrics {
  const n = timeMs.length
  if (n === 0) {
    return {
      a1_uv: 0,
      a1_ms: 0,
      b1_uv: 0,
      b1_ms: 0,
      c1_uv: 0,
      c1_ms: 0,
      a1_b1_uv: 0,
      a1_b1_ms: 0,
      b1_c1_uv: 0,
      b1_c1_ms: 0,
    }
  }

  const aI = clampIndex(markers.a1_idx, n)
  const bI = clampIndex(markers.b1_idx, n)
  const cI = clampIndex(markers.c1_idx, n)

  const a1Uv = signalUv[aI]
  const a1Ms = timeMs[aI]
  const b1Uv = signalUv[bI]
  const b1Ms = timeMs[bI]
  const c1Uv = signalUv[cI]
  const c1Ms = timeMs[cI]

  return {
    a1_uv: a1Uv,
    a1_ms: a1Ms,
    b1_uv: b1Uv,
    b1_ms: b1Ms,
    c1_uv: c1Uv,
    c1_ms: c1Ms,
    a1_b1_uv: b1Uv - a1Uv,
    a1_b1_ms: b1Ms - a1Ms,
    b1_c1_uv: b1Uv - c1Uv,
    b1_c1_ms: c1Ms - b1Ms,
  }
}

function median(values: number[]): number {
  if (values.length === 0) return 0
  const sorted = [...values].sort((a, b) => a - b)
  const mid = Math.floor(sorted.length / 2)
  return sorted.length % 2 === 1 ? sorted[mid] : 0.5 * (sorted[mid - 1] + sorted[mid])
}

/**
 * Exact real DFT magnitude for bins k = 0..floor(N/2) (matches numpy.fft.rfft to machine precision).
 */
function realDftMagnitudes(centered: readonly number[]): number[] {
  const n = centered.length
  const bins = Math.floor(n / 2) + 1
  const mags = new Array<number>(bins)
  const twoPiOverN = (2.0 * Math.PI) / n

  for (let k = 0; k < bins; k++) {
    let re = 0.0
    let im = 0.0
    const angleStep = twoPiOverN * k
    for (let j = 0; j < n; j++) {
      const ang = angleStep * j
      const val = centered[j]
      re += val * Math.cos(ang)
      im -= val * Math.sin(ang)
    }
    mags[k] = Math.hypot(re, im)
  }
  return mags
}

export function computeFlickerMetrics(
  timeMs: readonly number[],
  signalUv: readonly number[],
  targetFreqHz = 30.0,
): FlickerMetrics {
  const n = timeMs.length
  if (n < 8) {
    return {
      mean_peak_to_trough_uv: 0.0,
      std_peak_to_trough_uv: 0.0,
      fft_fundamental_amp_uv: 0.0,
      fft_peak_to_peak_uv: 0.0,
      dominant_freq_hz: 0.0,
      cycles_detected: 0,
      first_peak_time_ms: 0.0,
    }
  }

  const diffs: number[] = []
  for (let i = 1; i < n; i++) {
    diffs.push(timeMs[i] - timeMs[i - 1])
  }
  const dtMs = median(diffs)
  const fsHz = dtMs > 0 ? 1000.0 / dtMs : 1000.0

  // Mean and population standard deviation (ddof=0 matches numpy.std)
  let sum = 0.0
  for (let i = 0; i < n; i++) sum += signalUv[i]
  const meanVal = sum / n
  let varSum = 0.0
  for (let i = 0; i < n; i++) {
    const d = signalUv[i] - meanVal
    varSum += d * d
  }
  const stdVal = Math.sqrt(varSum / n)

  const minDist = Math.max(3, Math.round((0.65 * fsHz) / targetFreqHz))
  const prominence = Math.max(0.15 * stdVal, 0.5)

  const peaks = findPeaks1D(signalUv, { distance: minDist, prominence })
  const negSignal = signalUv.map((v) => -v)
  const troughs = findPeaks1D(negSignal, { distance: minDist, prominence })

  const amplitudes: number[] = []
  if (peaks.length > 0 && troughs.length > 0) {
    for (const pk of peaks) {
      let nearest = troughs[0]
      let bestDist = Math.abs(troughs[0] - pk)
      for (let j = 1; j < troughs.length; j++) {
        const d = Math.abs(troughs[j] - pk)
        if (d < bestDist) {
          bestDist = d
          nearest = troughs[j]
        }
      }
      amplitudes.push(signalUv[pk] - signalUv[nearest])
    }
  }

  let meanPtp = 0.0
  let stdPtp = 0.0
  let cycles = 0
  let firstPeakMs = 0.0

  if (amplitudes.length > 0) {
    meanPtp = amplitudes.reduce((acc, v) => acc + v, 0) / amplitudes.length
    const ptpVar =
      amplitudes.reduce((acc, v) => acc + (v - meanPtp) * (v - meanPtp), 0) / amplitudes.length
    stdPtp = Math.sqrt(ptpVar)
    cycles = amplitudes.length
    firstPeakMs = timeMs[peaks[0]]
  } else {
    let minV = signalUv[0]
    let maxV = signalUv[0]
    let maxIdx = 0
    for (let i = 1; i < n; i++) {
      if (signalUv[i] < minV) minV = signalUv[i]
      if (signalUv[i] > maxV) {
        maxV = signalUv[i]
        maxIdx = i
      }
    }
    meanPtp = maxV - minV
    stdPtp = 0.0
    cycles = 0
    firstPeakMs = timeMs[maxIdx]
  }

  // Exact single-sided FFT amplitude spectrum in 20-45 Hz band
  const centered = signalUv.map((v) => v - meanVal)
  const mags = realDftMagnitudes(centered)
  const spectrum = mags.map((m) => (2.0 / n) * m)
  const df = fsHz / n

  let bestIdx = spectrum.length > 1 ? 1 : 0
  let foundInBand = false
  for (let k = 0; k < spectrum.length; k++) {
    const f = k * df
    if (f >= 20.0 && f <= 45.0) {
      if (!foundInBand || spectrum[k] > spectrum[bestIdx]) {
        bestIdx = k
        foundInBand = true
      }
    }
  }
  if (!foundInBand && spectrum.length > 1) {
    bestIdx = 1
    for (let k = 2; k < spectrum.length; k++) {
      if (spectrum[k] > spectrum[bestIdx]) bestIdx = k
    }
  }

  const domFreq = bestIdx * df
  const fftAmp = spectrum[bestIdx] ?? 0.0

  return {
    mean_peak_to_trough_uv: meanPtp,
    std_peak_to_trough_uv: stdPtp,
    fft_fundamental_amp_uv: fftAmp,
    fft_peak_to_peak_uv: 2.0 * fftAmp,
    dominant_freq_hz: domFreq,
    cycles_detected: cycles,
    first_peak_time_ms: firstPeakMs,
  }
}

export function computeOpMetrics(
  timeMs: readonly number[],
  signalUv: readonly number[],
  windowStartMs = 15.0,
  windowEndMs = 65.0,
  maxWavelets = 4,
): OPMetrics {
  const n = timeMs.length
  if (n < 8) {
    return {
      op_amplitudes_uv: [],
      op_peak_times_ms: [],
      sum_op_amplitude_uv: 0.0,
      max_op_amplitude_uv: 0.0,
      dominant_freq_hz: 0.0,
      fft_band_amp_uv: 0.0,
      op_count: 0,
    }
  }

  const diffs: number[] = []
  for (let i = 1; i < n; i++) {
    diffs.push(timeMs[i] - timeMs[i - 1])
  }
  const dtMs = median(diffs)
  const fsHz = dtMs > 0 ? 1000.0 / dtMs : 1000.0

  const winIndices: number[] = []
  for (let i = 0; i < n; i++) {
    if (timeMs[i] >= windowStartMs && timeMs[i] <= windowEndMs) {
      winIndices.push(i)
    }
  }

  const opAmps: number[] = []
  const opTimes: number[] = []

  if (winIndices.length >= 3) {
    const seg = winIndices.map((idx) => signalUv[idx])
    let segSum = 0.0
    for (const v of seg) segSum += v
    const segMean = segSum / seg.length
    let segVar = 0.0
    for (const v of seg) {
      const d = v - segMean
      segVar += d * d
    }
    const segStd = Math.sqrt(segVar / seg.length)
    const minDist = Math.max(3, Math.round(0.006 * fsHz))
    const prominence = Math.max(0.35 * segStd, 1.5)
    const relPeaks = findPeaks1D(seg, { distance: minDist, prominence })
    const peaks = relPeaks.slice(0, maxWavelets).map((p) => winIndices[p])

    const winStartIdx = winIndices[0]
    for (let i = 0; i < peaks.length; i++) {
      const pk = peaks[i]
      const searchStart = i > 0 ? peaks[i - 1] : winStartIdx
      let troughIdx = searchStart
      for (let j = searchStart + 1; j <= pk; j++) {
        if (signalUv[j] < signalUv[troughIdx]) {
          troughIdx = j
        }
      }
      opAmps.push(signalUv[pk] - signalUv[troughIdx])
      opTimes.push(timeMs[pk])
    }
  }

  // Exact single-sided FFT dominant component in 60-200 Hz ISCEV OP band
  let sum = 0.0
  for (let i = 0; i < n; i++) sum += signalUv[i]
  const meanVal = sum / n
  const centered = signalUv.map((v) => v - meanVal)
  const mags = realDftMagnitudes(centered)
  const spectrum = mags.map((m) => (2.0 / n) * m)
  const df = fsHz / n

  let bestIdx = spectrum.length > 1 ? 1 : 0
  let foundInBand = false
  for (let k = 0; k < spectrum.length; k++) {
    const f = k * df
    if (f >= 60.0 && f <= 200.0) {
      if (!foundInBand || spectrum[k] > spectrum[bestIdx]) {
        bestIdx = k
        foundInBand = true
      }
    }
  }
  if (!foundInBand && spectrum.length > 1) {
    bestIdx = 1
    for (let k = 2; k < spectrum.length; k++) {
      if (spectrum[k] > spectrum[bestIdx]) bestIdx = k
    }
  }

  let sumOp = 0.0
  let maxOp = 0.0
  for (const a of opAmps) {
    sumOp += a
    if (a > maxOp) maxOp = a
  }

  return {
    op_amplitudes_uv: opAmps,
    op_peak_times_ms: opTimes,
    sum_op_amplitude_uv: sumOp,
    max_op_amplitude_uv: maxOp,
    dominant_freq_hz: bestIdx * df,
    fft_band_amp_uv: spectrum[bestIdx] ?? 0.0,
    op_count: opAmps.length,
  }
}

export function snapTimeToIndex(timeMs: readonly number[], targetTimeMs: number): number {
  if (timeMs.length === 0) return 0
  let bestIdx = 0
  let bestDiff = Math.abs(timeMs[0] - targetTimeMs)
  for (let i = 1; i < timeMs.length; i++) {
    const d = Math.abs(timeMs[i] - targetTimeMs)
    if (d < bestDiff) {
      bestDiff = d
      bestIdx = i
    }
  }
  return bestIdx
}
