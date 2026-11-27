/**
 * Batch CSV & styled Excel (.xlsx) export, clipboard TSV, and JSON work session persistence.
 * Matches Python `erg_reader.exporters` 1:1 in column layout and schema.
 */

import writeXlsxFile, { type Row, type SheetData } from 'write-excel-file/browser'

import { computeFlickerMetrics, computePeakMetrics } from './analysis'
import {
  APP_AUTHOR,
  APP_NAME,
  APP_VERSION,
  defaultDetectionConfig,
  getActiveSignal,
  isValidProtocol,
  protocolDisplayName,
  sanitizeDetectionConfig,
  type DetectionConfig,
  type ERGProtocol,
  type ERGSessionRecord,
  type EyeSide,
  type MarkerIndices,
  type MouseMetadata,
} from './models'

export const SESSION_SCHEMA_VERSION = 1

export const EXPORT_COLUMNS = [
  'File Name',
  'Eye',
  'Protocol',
  'Channel',
  'Strain / Lastname',
  'Mouse ID / Name',
  'Age',
  'Exam',
  'Exam Start',
  'Markers Mode',
  'A1 Amplitude (uV)',
  'A1 Peak Time (ms)',
  'B1 Amplitude (uV)',
  'B1 Peak Time (ms)',
  'C1 Amplitude (uV)',
  'C1 Peak Time (ms)',
  'A1-B1 Amplitude (uV)',
  'A1-B1 Peak Time (ms)',
  'B1-C1 Amplitude (uV)',
  'B1-C1 Peak Time (ms)',
  'Flicker Mean P-T (uV)',
  'Flicker SD P-T (uV)',
  'Flicker FFT Amp (uV)',
  'Flicker FFT P-P (uV)',
  'Flicker Freq (Hz)',
  'Flicker Cycles',
  'Notes',
] as const

export type ExportColumn = (typeof EXPORT_COLUMNS)[number]
export type SummaryRow = Record<ExportColumn, string | number>

function round2(v: number): number {
  return Math.round(v * 100) / 100
}

export function buildSummaryRows(records: readonly ERGSessionRecord[]): SummaryRow[] {
  return records.map((rec) => {
    const signal = getActiveSignal(rec)
    const m = computePeakMetrics(rec.time_ms, signal, rec.markers)
    const fl =
      rec.protocol === 'light_adapted_3_flicker'
        ? computeFlickerMetrics(rec.time_ms, signal)
        : null

    return {
      'File Name': rec.file_name,
      Eye: rec.eye,
      Protocol: protocolDisplayName(rec.protocol),
      Channel: rec.active_channel,
      'Strain / Lastname': rec.metadata.strain_lastname,
      'Mouse ID / Name': rec.metadata.mouse_id_name,
      Age: rec.metadata.age,
      Exam: rec.metadata.exam,
      'Exam Start': rec.metadata.exam_start,
      'Markers Mode': rec.markers.is_manual ? 'Manual' : 'Auto',
      'A1 Amplitude (uV)': round2(m.a1_uv),
      'A1 Peak Time (ms)': round2(m.a1_ms),
      'B1 Amplitude (uV)': round2(m.b1_uv),
      'B1 Peak Time (ms)': round2(m.b1_ms),
      'C1 Amplitude (uV)': round2(m.c1_uv),
      'C1 Peak Time (ms)': round2(m.c1_ms),
      'A1-B1 Amplitude (uV)': round2(m.a1_b1_uv),
      'A1-B1 Peak Time (ms)': round2(m.a1_b1_ms),
      'B1-C1 Amplitude (uV)': round2(m.b1_c1_uv),
      'B1-C1 Peak Time (ms)': round2(m.b1_c1_ms),
      'Flicker Mean P-T (uV)': fl ? round2(fl.mean_peak_to_trough_uv) : '',
      'Flicker SD P-T (uV)': fl ? round2(fl.std_peak_to_trough_uv) : '',
      'Flicker FFT Amp (uV)': fl ? round2(fl.fft_fundamental_amp_uv) : '',
      'Flicker FFT P-P (uV)': fl ? round2(fl.fft_peak_to_peak_uv) : '',
      'Flicker Freq (Hz)': fl ? round2(fl.dominant_freq_hz) : '',
      'Flicker Cycles': fl ? fl.cycles_detected : '',
      Notes: rec.metadata.notes,
    }
  })
}

function escapeCsvCell(value: string | number): string {
  const str = String(value)
  if (str.includes(',') || str.includes('"') || str.includes('\n') || str.includes('\r')) {
    return `"${str.replaceAll('"', '""')}"`
  }
  return str
}

export function buildSummaryCsvText(records: readonly ERGSessionRecord[]): string {
  const rows = buildSummaryRows(records)
  const lines: string[] = [EXPORT_COLUMNS.map(escapeCsvCell).join(',')]
  for (const row of rows) {
    lines.push(EXPORT_COLUMNS.map((col) => escapeCsvCell(row[col])).join(','))
  }
  return '\uFEFF' + lines.join('\r\n') + '\r\n'
}

export async function buildSummaryXlsxBlob(records: readonly ERGSessionRecord[]): Promise<Blob> {
  const rows = buildSummaryRows(records)
  const a1b1Index = EXPORT_COLUMNS.indexOf('A1-B1 Amplitude (uV)')

  const headerRow: Row = EXPORT_COLUMNS.map((col) => ({
    value: col,
    type: String,
    fontWeight: 'bold',
    color: '#FFFFFF',
    backgroundColor: '#1E3A5F',
    align: 'center',
    alignVertical: 'center',
    wrap: true,
    borderColor: '#CBD5E1',
    borderStyle: 'thin',
  }))

  const dataRows: Row[] = rows.map((rowData, idx) => {
    const isEven = idx % 2 === 1
    return EXPORT_COLUMNS.map((col, colIdx) => {
      const val = rowData[col]
      const isHighlight = colIdx === a1b1Index
      const isNum = typeof val === 'number'
      const isCycles = col === 'Flicker Cycles' && isNum
      return {
        value: val,
        type: isNum ? Number : String,
        format: isNum ? (isCycles ? '0' : '0.00') : undefined,
        fontWeight: isHighlight ? 'bold' : undefined,
        color: isHighlight ? '#111827' : undefined,
        backgroundColor: isHighlight ? '#FFF59D' : isEven ? '#F8FAFC' : undefined,
        align: isNum ? 'right' : 'left',
        alignVertical: 'center',
        borderColor: '#CBD5E1',
        borderStyle: 'thin',
      }
    })
  })

  const summarySheet: SheetData = [headerRow, ...dataRows]
  const columnWidths = EXPORT_COLUMNS.map((col) => {
    let maxLen = col.length
    for (const r of rows) {
      maxLen = Math.max(maxLen, String(r[col]).length)
    }
    return { width: Math.min(maxLen + 4, 34) }
  })

  const utcStamp = new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC'
  const infoSheet: SheetData = [
    [
      { value: 'Application', type: String, fontWeight: 'bold' },
      { value: APP_NAME, type: String },
    ],
    [
      { value: 'Version', type: String, fontWeight: 'bold' },
      { value: APP_VERSION, type: String },
    ],
    [
      { value: 'Author', type: String, fontWeight: 'bold' },
      { value: APP_AUTHOR, type: String },
    ],
    [
      { value: 'Group', type: String, fontWeight: 'bold' },
      {
        value: 'Grupo nBio · Instituto de Bioingeniería · Universidad Miguel Hernández',
        type: String,
      },
    ],
    [
      { value: 'Exported (UTC)', type: String, fontWeight: 'bold' },
      { value: utcStamp, type: String },
    ],
    [
      { value: 'Records Exported', type: String, fontWeight: 'bold' },
      { value: records.length, type: Number },
    ],
  ]

  const blob = await writeXlsxFile(
    [
      {
        sheet: 'ERG Summary',
        data: summarySheet,
        columns: columnWidths,
        stickyRowsCount: 1,
        stickyColumnsCount: 1,
      },
      {
        sheet: 'Export Info',
        data: infoSheet,
        columns: [{ width: 20 }, { width: 58 }],
      },
    ],
    { fontFamily: 'Calibri', fontSize: 11 },
  ).toBlob()
  return blob
}

export function formatRecordClipboardTsv(record: ERGSessionRecord): string {
  const signal = getActiveSignal(record)
  const m = computePeakMetrics(record.time_ms, signal, record.markers)
  const lines = [
    `${record.eye}\tA1\tB1\tC1\tA1-B1\tB1-C1`,
    `Amplitude (uV)\t${m.a1_uv.toFixed(2)}\t${m.b1_uv.toFixed(2)}\t${m.c1_uv.toFixed(2)}\t${m.a1_b1_uv.toFixed(2)}\t${m.b1_c1_uv.toFixed(2)}`,
    `Peak time (ms)\t${m.a1_ms.toFixed(2)}\t${m.b1_ms.toFixed(2)}\t${m.c1_ms.toFixed(2)}\t${m.a1_b1_ms.toFixed(2)}\t${m.b1_c1_ms.toFixed(2)}`,
  ]
  if (record.protocol === 'light_adapted_3_flicker') {
    const fl = computeFlickerMetrics(record.time_ms, signal)
    lines.push('')
    lines.push(
      'Flicker Metrics\tMean P-T (uV)\tSD P-T (uV)\tFFT Amp (uV)\tFFT P-P (uV)\tFreq (Hz)\tCycles',
    )
    lines.push(
      `30 Hz Flicker\t${fl.mean_peak_to_trough_uv.toFixed(2)}\t${fl.std_peak_to_trough_uv.toFixed(2)}\t${fl.fft_fundamental_amp_uv.toFixed(2)}\t${fl.fft_peak_to_peak_uv.toFixed(2)}\t${fl.dominant_freq_hz.toFixed(2)}\t${fl.cycles_detected}`,
    )
  }
  return lines.join('\n')
}

export interface SerializedSessionRecord {
  record_id: string
  file_path: string
  file_name: string
  eye?: EyeSide
  protocol: ERGProtocol
  active_channel: string
  overlay_enabled: boolean
  metadata: MouseMetadata
  markers: MarkerIndices
  // Embedded waveform payload for 100% self-contained browser reload
  time_ms?: number[]
  channels?: Record<string, number[]>
}

export interface SerializedSessionPayload {
  schema_version: number
  app: string
  version: string
  saved_utc: string
  active_record_id: string | null
  detection_config: DetectionConfig
  records: SerializedSessionRecord[]
}

export function serializeSessionJson(
  records: readonly ERGSessionRecord[],
  config: DetectionConfig,
  activeRecordId: string | null,
): string {
  const payload: SerializedSessionPayload = {
    schema_version: SESSION_SCHEMA_VERSION,
    app: APP_NAME,
    version: APP_VERSION,
    saved_utc: new Date().toISOString(),
    active_record_id: activeRecordId,
    detection_config: config,
    records: records.map((rec) => ({
      record_id: rec.record_id,
      file_path: rec.file_path,
      file_name: rec.file_name,
      eye: rec.eye,
      protocol: rec.protocol,
      active_channel: rec.active_channel,
      overlay_enabled: rec.overlay_enabled,
      metadata: { ...rec.metadata },
      markers: { ...rec.markers },
      time_ms: rec.time_ms,
      channels: rec.channels,
    })),
  }
  return JSON.stringify(payload, null, 2)
}

export interface SessionLoadResult {
  records: ERGSessionRecord[]
  config: DetectionConfig
  activeRecordId: string | null
  warnings: string[]
}

export function parseSessionJson(
  rawJson: string,
  existingRecords: readonly ERGSessionRecord[] = [],
): SessionLoadResult {
  let parsed: unknown
  try {
    parsed = JSON.parse(rawJson)
  } catch (err) {
    throw new Error(`Invalid JSON syntax: ${err instanceof Error ? err.message : String(err)}`)
  }
  if (!parsed || typeof parsed !== 'object' || !Array.isArray((parsed as Record<string, unknown>).records)) {
    throw new Error('Invalid ERG session file format (missing "records" array).')
  }

  const data = parsed as Record<string, unknown>
  const config = sanitizeDetectionConfig(data.detection_config ?? defaultDetectionConfig())
  const activeRecordId =
    typeof data.active_record_id === 'string' ? data.active_record_id : null
  const records: ERGSessionRecord[] = []
  const warnings: string[] = []

  const existingByName = new Map<string, ERGSessionRecord>()
  for (const r of existingRecords) {
    existingByName.set(r.file_name, r)
  }

  for (const rawEntry of data.records as unknown[]) {
    if (!rawEntry || typeof rawEntry !== 'object') {
      warnings.push('Skipped malformed record entry in session JSON.')
      continue
    }
    const entry = rawEntry as Record<string, unknown>
    const fileName = String(entry.file_name ?? 'unknown.csv')
    const matched = existingByName.get(fileName)

    const timeMs = Array.isArray(entry.time_ms)
      ? (entry.time_ms as unknown[]).map(Number).filter((v) => Number.isFinite(v))
      : matched?.time_ms
    const channels =
      entry.channels && typeof entry.channels === 'object'
        ? (entry.channels as Record<string, number[]>)
        : matched?.channels

    if (!timeMs || timeMs.length < 4 || !channels || Object.keys(channels).length === 0) {
      warnings.push(
        `Trace "${fileName}" has no embedded waveform data. Load the CSV first to apply this desktop session.`,
      )
      continue
    }

    const n = timeMs.length
    const availChannels = Object.keys(channels)
    const savedCh = typeof entry.active_channel === 'string' ? entry.active_channel : ''
    const activeChannel = availChannels.includes(savedCh) ? savedCh : availChannels[0]

    const proto: ERGProtocol = isValidProtocol(entry.protocol)
      ? entry.protocol
      : matched?.protocol ?? 'unknown'

    const eye: EyeSide =
      entry.eye === 'LEFT - OS' || entry.eye === 'RIGHT - OD' || entry.eye === 'UNKNOWN'
        ? entry.eye
        : matched?.eye ?? 'LEFT - OS'

    const rawMeta =
      entry.metadata && typeof entry.metadata === 'object'
        ? (entry.metadata as Record<string, unknown>)
        : {}
    const metadata: MouseMetadata = {
      strain_lastname: String(rawMeta.strain_lastname ?? ''),
      mouse_id_name: String(rawMeta.mouse_id_name ?? ''),
      age: String(rawMeta.age ?? ''),
      exam: String(rawMeta.exam ?? protocolDisplayName(proto)),
      exam_start: String(rawMeta.exam_start ?? ''),
      notes: String(rawMeta.notes ?? ''),
    }

    const rawMarkers =
      entry.markers && typeof entry.markers === 'object'
        ? (entry.markers as Record<string, unknown>)
        : {}
    const clamp = (v: unknown, fallback: number) => {
      const num = Number(v)
      if (!Number.isFinite(num)) return fallback
      return Math.max(0, Math.min(Math.trunc(num), n - 1))
    }
    const markers: MarkerIndices = {
      a1_idx: clamp(rawMarkers.a1_idx, 0),
      b1_idx: clamp(rawMarkers.b1_idx, Math.min(1, n - 1)),
      c1_idx: clamp(rawMarkers.c1_idx, Math.min(2, n - 1)),
      is_manual: Boolean(rawMarkers.is_manual ?? false),
    }

    records.push({
      record_id: typeof entry.record_id === 'string' ? entry.record_id : `${fileName}_${records.length}`,
      file_path: typeof entry.file_path === 'string' ? entry.file_path : fileName,
      file_name: fileName,
      eye,
      protocol: proto,
      time_ms: timeMs,
      channels,
      active_channel: activeChannel,
      metadata,
      markers,
      overlay_enabled: Boolean(entry.overlay_enabled ?? false),
    })
  }

  return { records, config, activeRecordId, warnings }
}

export function triggerBlobDownload(blob: Blob, fileName: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
