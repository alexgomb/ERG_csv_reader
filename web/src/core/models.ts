/**
 * Core data models for nBio ERG-Trace Web — 1:1 parity with Python `erg_reader.models`.
 */

export const APP_NAME = 'nBio ERG-Trace'
export const APP_VERSION = '0.3.0'
export const APP_AUTHOR = 'Alejandro Gombau García'
export const APP_LICENSE = 'MIT'
export const REPO_URL = 'https://github.com/alexgomb/ERG_csv_reader'
export const NBIO_URL = 'http://nbio.umh.es'

export type EyeSide = 'LEFT - OS' | 'RIGHT - OD' | 'UNKNOWN'

export type ERGProtocol =
  | 'dark_adapted_3'
  | 'dark_adapted_10'
  | 'dark_adapted_3_ops'
  | 'light_adapted_3'
  | 'light_adapted_3_flicker'
  | 'unknown'

export const PROTOCOL_ORDER: readonly ERGProtocol[] = [
  'dark_adapted_3',
  'dark_adapted_10',
  'dark_adapted_3_ops',
  'light_adapted_3',
  'light_adapted_3_flicker',
  'unknown',
] as const

export function protocolDisplayName(protocol: ERGProtocol): string {
  switch (protocol) {
    case 'dark_adapted_3':
      return 'DARK-ADAPTED 3.0 ERG'
    case 'dark_adapted_10':
      return 'DARK-ADAPTED 10.0 ERG'
    case 'dark_adapted_3_ops':
      return 'DARK-ADAPTED 3.0 OSCILLATORY POTENTIALS'
    case 'light_adapted_3':
      return 'LIGHT-ADAPTED 3.0 ERG'
    case 'light_adapted_3_flicker':
      return 'LIGHT-ADAPTED 3.0 FLICKER ERG'
    default:
      return 'CUSTOM ERG'
  }
}

export function protocolShortLabel(protocol: ERGProtocol): string {
  switch (protocol) {
    case 'dark_adapted_3':
      return 'DA 3.0'
    case 'dark_adapted_10':
      return 'DA 10.0'
    case 'dark_adapted_3_ops':
      return 'OPs'
    case 'light_adapted_3':
      return 'LA 3.0'
    case 'light_adapted_3_flicker':
      return 'Flicker'
    default:
      return 'ERG'
  }
}

export function isValidProtocol(value: unknown): value is ERGProtocol {
  return (
    value === 'dark_adapted_3' ||
    value === 'dark_adapted_10' ||
    value === 'dark_adapted_3_ops' ||
    value === 'light_adapted_3' ||
    value === 'light_adapted_3_flicker' ||
    value === 'unknown'
  )
}

export interface DetectionWindow {
  a_min_ms: number
  a_max_ms: number
  b_min_ms: number
  b_max_ms: number
  c_min_ms: number
  c_max_ms: number
}

export interface DetectionConfig {
  windows: Record<ERGProtocol, DetectionWindow>
  include_right_od: boolean
}

export function defaultDetectionWindows(): Record<ERGProtocol, DetectionWindow> {
  return {
    dark_adapted_3: {
      a_min_ms: 8.0,
      a_max_ms: 40.0,
      b_min_ms: 30.0,
      b_max_ms: 110.0,
      c_min_ms: 100.0,
      c_max_ms: 190.0,
    },
    dark_adapted_10: {
      a_min_ms: 6.0,
      a_max_ms: 35.0,
      b_min_ms: 25.0,
      b_max_ms: 100.0,
      c_min_ms: 95.0,
      c_max_ms: 190.0,
    },
    dark_adapted_3_ops: {
      a_min_ms: 14.0,
      a_max_ms: 32.0,
      b_min_ms: 28.0,
      b_max_ms: 48.0,
      c_min_ms: 36.0,
      c_max_ms: 60.0,
    },
    light_adapted_3: {
      a_min_ms: 8.0,
      a_max_ms: 35.0,
      b_min_ms: 30.0,
      b_max_ms: 100.0,
      c_min_ms: 95.0,
      c_max_ms: 190.0,
    },
    light_adapted_3_flicker: {
      a_min_ms: 15.0,
      a_max_ms: 45.0,
      b_min_ms: 30.0,
      b_max_ms: 65.0,
      c_min_ms: 50.0,
      c_max_ms: 85.0,
    },
    unknown: {
      a_min_ms: 6.0,
      a_max_ms: 45.0,
      b_min_ms: 25.0,
      b_max_ms: 120.0,
      c_min_ms: 95.0,
      c_max_ms: 210.0,
    },
  }
}

export function defaultDetectionConfig(): DetectionConfig {
  return {
    windows: defaultDetectionWindows(),
    include_right_od: false,
  }
}

export function sanitizeDetectionConfig(raw: unknown): DetectionConfig {
  const defaults = defaultDetectionWindows()
  if (!raw || typeof raw !== 'object') {
    return defaultDetectionConfig()
  }
  const obj = raw as Record<string, unknown>
  const rawWindows =
    obj.windows && typeof obj.windows === 'object'
      ? (obj.windows as Record<string, unknown>)
      : {}
  const windows = { ...defaults }

  for (const proto of PROTOCOL_ORDER) {
    const entry = rawWindows[proto]
    if (entry && typeof entry === 'object') {
      const w = entry as Record<string, unknown>
      const nums = [
        Number(w.a_min_ms),
        Number(w.a_max_ms),
        Number(w.b_min_ms),
        Number(w.b_max_ms),
        Number(w.c_min_ms),
        Number(w.c_max_ms),
      ]
      if (nums.every((n) => Number.isFinite(n))) {
        windows[proto] = {
          a_min_ms: Math.min(nums[0], nums[1]),
          a_max_ms: Math.max(nums[0], nums[1]),
          b_min_ms: Math.min(nums[2], nums[3]),
          b_max_ms: Math.max(nums[2], nums[3]),
          c_min_ms: Math.min(nums[4], nums[5]),
          c_max_ms: Math.max(nums[4], nums[5]),
        }
      }
    }
  }

  return {
    windows,
    include_right_od: Boolean(obj.include_right_od ?? false),
  }
}

export interface MouseMetadata {
  strain_lastname: string
  mouse_id_name: string
  age: string
  exam: string
  exam_start: string
  notes: string
}

export interface MarkerIndices {
  a1_idx: number
  b1_idx: number
  c1_idx: number
  is_manual: boolean
}

export interface PeakMetrics {
  a1_uv: number
  a1_ms: number
  b1_uv: number
  b1_ms: number
  c1_uv: number
  c1_ms: number
  a1_b1_uv: number
  a1_b1_ms: number
  b1_c1_uv: number
  b1_c1_ms: number
}

export interface FlickerMetrics {
  mean_peak_to_trough_uv: number
  std_peak_to_trough_uv: number
  fft_fundamental_amp_uv: number
  fft_peak_to_peak_uv: number
  dominant_freq_hz: number
  cycles_detected: number
  first_peak_time_ms: number
}

export interface OPMetrics {
  op_amplitudes_uv: number[]
  op_peak_times_ms: number[]
  sum_op_amplitude_uv: number
  max_op_amplitude_uv: number
  dominant_freq_hz: number
  fft_band_amp_uv: number
  op_count: number
}

export interface ERGSessionRecord {
  record_id: string
  file_path: string
  file_name: string
  eye: EyeSide
  protocol: ERGProtocol
  time_ms: number[]
  channels: Record<string, number[]>
  active_channel: string
  metadata: MouseMetadata
  markers: MarkerIndices
  overlay_enabled: boolean
}

export function getActiveSignal(rec: ERGSessionRecord): number[] {
  if (rec.active_channel in rec.channels) {
    return rec.channels[rec.active_channel]
  }
  const keys = Object.keys(rec.channels)
  return keys.length > 0 ? rec.channels[keys[0]] : []
}
