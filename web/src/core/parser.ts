/**
 * CSO Retimax CSV parser — 1:1 behavioral parity with Python `erg_reader.parser`.
 */

import { autoDetectMarkers } from './analysis'
import {
  defaultDetectionConfig,
  protocolDisplayName,
  type DetectionConfig,
  type ERGProtocol,
  type ERGSessionRecord,
  type EyeSide,
  type MouseMetadata,
} from './models'

const GENERIC_PARENT_NAMES = new Set([
  '',
  'example_files',
  'examples',
  'example',
  'csv',
  'csvs',
  'data',
  'erg',
  'erg_reader',
  'erg_csv_reader',
  'nbio_erg_trace',
  'nbio-erg-trace',
  'exports',
  'export',
  'retimax',
  'desktop',
  'documents',
  'downloads',
  'tmp',
  'temp',
])

export class ERGParseError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ERGParseError'
  }
}

export interface CsvInputFile {
  name: string
  relativePath?: string
  content: string | Uint8Array
}

export interface BatchLoadResult {
  records: ERGSessionRecord[]
  skipped_right_od: string[]
  errors: Array<{ fileName: string; message: string }>
}

function generateRecordId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID().replace(/-/g, '').slice(0, 12)
  }
  return Math.random().toString(36).slice(2, 14).padEnd(12, '0')
}

export function decodeCsvBytes(bytes: Uint8Array): string {
  // Strip UTF-8 BOM if present
  let view = bytes
  if (bytes.length >= 3 && bytes[0] === 0xef && bytes[1] === 0xbb && bytes[2] === 0xbf) {
    view = bytes.subarray(3)
  }
  try {
    return new TextDecoder('utf-8', { fatal: true }).decode(view)
  } catch {
    return new TextDecoder('windows-1252').decode(view)
  }
}

function parseEye(line: string): EyeSide {
  const upper = line.trim().toUpperCase()
  if (upper.includes('LEFT') || /\bOS\b/.test(upper)) {
    return 'LEFT - OS'
  }
  if (upper.includes('RIGHT') || /\bOD\b/.test(upper)) {
    return 'RIGHT - OD'
  }
  return 'UNKNOWN'
}

function detectDelimiter(headerLine: string): string {
  if (headerLine.includes('\t')) return '\t'
  if (headerLine.includes(';')) return ';'
  return ','
}

function parseNumberToken(token: string, decimalComma: boolean): number {
  let cleaned = token.trim()
  if (decimalComma) {
    cleaned = cleaned.replace(',', '.')
  }
  if (cleaned === '') {
    return Number.NaN
  }
  return Number(cleaned)
}

export function inferProtocol(fileName: string, timeMs: readonly number[]): ERGProtocol {
  const low = fileName.toLowerCase()
  if (low.includes('flicker')) {
    return 'light_adapted_3_flicker'
  }
  if (timeMs.length > 10) {
    const tEnd = timeMs[timeMs.length - 1]
    if (tEnd >= 140.0 && tEnd <= 185.0) {
      return 'light_adapted_3_flicker'
    }
  }
  if (low.includes('light') || low.includes('photopic') || /\bla[\s_-]?3/.test(low)) {
    return 'light_adapted_3'
  }
  if (low.includes('dark') || low.includes('scotopic') || /\bda[\s_-]/.test(low)) {
    if (/(?:^|[^0-9])10(?:\.0)?(?:[^0-9]|$)/.test(low)) {
      return 'dark_adapted_10'
    }
    if (/(?:^|[^0-9])3(?:\.0)?(?:[^0-9]|$)/.test(low)) {
      return 'dark_adapted_3'
    }
  }
  return 'unknown'
}

export function inferMetadata(
  fileName: string,
  relativePath: string | undefined,
  examStart: string,
  protocol: ERGProtocol,
): MouseMetadata {
  let examLabel = protocolDisplayName(protocol)
  if (protocol === 'unknown') {
    const stem = fileName.replace(/\.[^.]+$/, '')
    const stripped = stem.replace(/[\s_-]*(LEFT|RIGHT)\s*-\s*(OS|OD)\s*$/i, '')
    examLabel = stripped.replace(/_/g, ' ').trim().toUpperCase() || examLabel
  }

  let parentName = ''
  if (relativePath) {
    const normalized = relativePath.replace(/\\/g, '/')
    const parts = normalized.split('/').filter(Boolean)
    if (parts.length >= 2) {
      parentName = parts[parts.length - 2].trim()
    }
  }

  let strain = ''
  let mouseId = ''
  let age = ''

  if (parentName && !GENERIC_PARENT_NAMES.has(parentName.toLowerCase())) {
    const cleanedParent = parentName.replace(/_/g, ' ').trim()
    mouseId = cleanedParent
    const tokens = cleanedParent.split(/\s+/)
    if (tokens.length > 0) {
      strain = tokens[0]
    }
    const ageMatch = cleanedParent.match(/\b(P\d+|\d+\s*(?:w|wk|wks|m|mo|mos|d|days?))\b/i)
    if (ageMatch) {
      age = ageMatch[1].toUpperCase()
    }
  }

  return {
    strain_lastname: strain,
    mouse_id_name: mouseId,
    age,
    exam: examLabel,
    exam_start: examStart,
    notes: '',
  }
}

function selectDefaultChannel(channelNames: readonly string[]): string {
  const preferred = ['AV1(UV)', 'AV1', 'GAV(UV)', 'GAV']
  for (const target of preferred) {
    const match = channelNames.find((col) => col.trim().toUpperCase() === target)
    if (match) return match
  }
  return channelNames[0]
}

export function parseRetimaxCsv(
  input: CsvInputFile,
  config?: DetectionConfig,
): ERGSessionRecord {
  const rawText =
    typeof input.content === 'string'
      ? input.content.replace(/^\uFEFF/, '')
      : decodeCsvBytes(input.content)

  const lines = rawText
    .split(/\r?\n/)
    .map((l) => l.trimEnd())
    .filter((l) => l.trim().length > 0)

  if (lines.length < 5) {
    throw new ERGParseError(`File ${input.name} has too few lines to be a Retimax ERG CSV.`)
  }

  // Locate column header row containing Time and uV/µV
  let headerIdx = -1
  for (let i = 0; i < Math.min(8, lines.length); i++) {
    const low = lines[i].toLowerCase()
    if (low.includes('time') && (low.includes('uv') || low.includes('µv') || low.includes('μv'))) {
      headerIdx = i
      break
    }
  }
  if (headerIdx < 0) {
    throw new ERGParseError(
      `Could not find Retimax column header (Time(ms) / uV) in ${input.name}.`,
    )
  }

  let examStart = ''
  let eye: EyeSide = 'UNKNOWN'
  for (let i = 0; i < headerIdx; i++) {
    const metaLine = lines[i]
    if (metaLine.toLowerCase().includes('exam start')) {
      const colonIdx = metaLine.indexOf(':')
      if (colonIdx >= 0) {
        examStart = metaLine.slice(colonIdx + 1).trim()
      }
    } else {
      const parsedEye = parseEye(metaLine)
      if (parsedEye !== 'UNKNOWN') {
        eye = parsedEye
      }
    }
  }

  const headerLine = lines[headerIdx]
  const delimiter = detectDelimiter(headerLine)
  const rawHeaders = headerLine
    .split(delimiter)
    .map((c) => c.trim())
    .filter((c) => c.length > 0)

  if (rawHeaders.length < 2) {
    throw new ERGParseError(`Expected at least Time and 1 signal column in ${input.name}.`)
  }

  const channelNames = rawHeaders.slice(1)
  const decimalComma = delimiter !== ','

  const timeValues: number[] = []
  const channelBuffers: number[][] = channelNames.map(() => [])

  for (let rowOffset = headerIdx + 1; rowOffset < lines.length; rowOffset++) {
    const row = lines[rowOffset]
    const tokens = row.split(delimiter).map((tok) => tok.trim())
    while (tokens.length > 0 && tokens[tokens.length - 1] === '') {
      tokens.pop()
    }
    if (tokens.length === 0) continue

    if (tokens.length < 1 + channelNames.length) {
      throw new ERGParseError(
        `Malformed data row at line ${rowOffset + 1} in ${input.name}: expected ${1 + channelNames.length} columns, got ${tokens.length}.`,
      )
    }

    const tVal = parseNumberToken(tokens[0], decimalComma)
    if (!Number.isFinite(tVal)) {
      throw new ERGParseError(
        `Invalid numeric value at line ${rowOffset + 1} in ${input.name}: "${tokens[0]}"`,
      )
    }

    const yVals: number[] = []
    for (let c = 0; c < channelNames.length; c++) {
      const yv = parseNumberToken(tokens[1 + c], decimalComma)
      if (!Number.isFinite(yv)) {
        throw new ERGParseError(
          `Invalid numeric value at line ${rowOffset + 1} in ${input.name}: "${tokens[1 + c]}"`,
        )
      }
      yVals.push(yv)
    }

    timeValues.push(tVal)
    for (let c = 0; c < channelNames.length; c++) {
      channelBuffers[c].push(yVals[c])
    }
  }

  if (timeValues.length < 4) {
    throw new ERGParseError(
      `Insufficient waveform samples (${timeValues.length}) in ${input.name}.`,
    )
  }

  const channels: Record<string, number[]> = {}
  channelNames.forEach((name, idx) => {
    channels[name] = channelBuffers[idx]
  })

  const activeChannel = selectDefaultChannel(channelNames)
  const protocol = inferProtocol(input.name, timeValues)
  const metadata = inferMetadata(input.name, input.relativePath, examStart, protocol)
  const cfg = config ?? defaultDetectionConfig()
  const markers = autoDetectMarkers(timeValues, channels[activeChannel], protocol, cfg)

  return {
    record_id: generateRecordId(),
    file_path: input.relativePath || input.name,
    file_name: input.name,
    eye,
    protocol,
    time_ms: timeValues,
    channels,
    active_channel: activeChannel,
    metadata,
    markers,
    overlay_enabled: false,
  }
}

export function loadCsvFilesBatch(
  inputs: readonly CsvInputFile[],
  config?: DetectionConfig,
): BatchLoadResult {
  const cfg = config ?? defaultDetectionConfig()
  const records: ERGSessionRecord[] = []
  const skippedRightOd: string[] = []
  const errors: Array<{ fileName: string; message: string }> = []

  const sorted = [...inputs].sort((a, b) =>
    (a.relativePath || a.name).localeCompare(b.relativePath || b.name),
  )

  for (const item of sorted) {
    if (!item.name.toLowerCase().endsWith('.csv')) {
      continue
    }
    try {
      const rec = parseRetimaxCsv(item, cfg)
      if (rec.eye === 'RIGHT - OD' && !cfg.include_right_od) {
        skippedRightOd.push(item.relativePath || item.name)
        continue
      }
      records.push(rec)
    } catch (err) {
      errors.push({
        fileName: item.name,
        message: err instanceof Error ? err.message : String(err),
      })
    }
  }

  return {
    records,
    skipped_right_od: skippedRightOd,
    errors,
  }
}
