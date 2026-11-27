import fs from 'node:fs'
import path from 'node:path'

import { readSheet } from 'read-excel-file/node'
import { describe, expect, it } from 'vitest'

import {
  buildSummaryCsvText,
  buildSummaryXlsxBlob,
  EXPORT_COLUMNS,
  formatRecordClipboardTsv,
  parseSessionJson,
  serializeSessionJson,
} from '../core/exporters'
import { defaultDetectionConfig } from '../core/models'
import { loadCsvFilesBatch } from '../core/parser'

const EXAMPLE_DIR = path.resolve(__dirname, '../../../example_files')

function loadLeftExamples() {
  const inputs = fs
    .readdirSync(EXAMPLE_DIR)
    .filter((f) => f.endsWith('.csv'))
    .map((name) => ({
      name,
      relativePath: `example_files/${name}`,
      content: new Uint8Array(fs.readFileSync(path.join(EXAMPLE_DIR, name))),
    }))
  return loadCsvFilesBatch(inputs).records
}

describe('Exporters & JSON Session Persistence (web)', () => {
  it('exports empty and Unicode/quoted batch CSV with exact 27 columns', () => {
    const emptyCsv = buildSummaryCsvText([])
    expect(emptyCsv.startsWith('\uFEFF')).toBe(true)
    const headerLine = emptyCsv.slice(1).trim().split('\r\n')[0]
    expect(headerLine.split(',')).toEqual([...EXPORT_COLUMNS])

    const records = loadLeftExamples()
    records[0].metadata.strain_lastname = 'C57BL/6J, "WT"'
    records[0].metadata.mouse_id_name = 'Ratón #1 — Español'
    records[0].metadata.notes = 'Nota con "comillas", y coma'

    const csvText = buildSummaryCsvText(records)
    expect(csvText).toContain('"C57BL/6J, ""WT"""')
    expect(csvText).toContain('Ratón #1 — Español')
    expect(csvText).toContain('"Nota con ""comillas"", y coma"')
  })

  it('generates valid multi-sheet Excel (.xlsx) readable back via read-excel-file', async () => {
    const records = loadLeftExamples()
    records[0].metadata.strain_lastname = 'C57'
    records[0].metadata.mouse_id_name = 'C57 P21'

    const blob = await buildSummaryXlsxBlob(records)
    expect(blob.size).toBeGreaterThan(2000)

    const buf = Buffer.from(await blob.arrayBuffer())
    const summaryRows = await readSheet(buf, 'ERG Summary')
    expect(summaryRows.length).toBe(5) // 1 header + 4 OS traces
    expect(summaryRows[0]).toEqual([...EXPORT_COLUMNS])
    expect(summaryRows[1][4]).toBe('C57')
    expect(summaryRows[1][5]).toBe('C57 P21')

    const infoRows = await readSheet(buf, 'Export Info')
    const flatInfo = infoRows.flat().map(String)
    expect(flatInfo).toContain('nBio ERG-Trace')
    expect(flatInfo).toContain('Alejandro Gombau García')
    expect(flatInfo.some((v) => v.includes('Grupo nBio'))).toBe(true)

    // Empty export still builds a valid workbook
    const emptyBlob = await buildSummaryXlsxBlob([])
    const emptyRows = await readSheet(Buffer.from(await emptyBlob.arrayBuffer()), 'ERG Summary')
    expect(emptyRows.length).toBe(1)
  })

  it('formats Retimax clipboard TSV with optional Flicker metrics section', () => {
    const records = loadLeftExamples()
    const da3 = records.find((r) => r.file_name.includes('Dark-Adapted_3'))!
    const flk = records.find((r) => r.file_name.includes('Flicker'))!

    const tsvDa3 = formatRecordClipboardTsv(da3)
    expect(tsvDa3).toContain('LEFT - OS\tA1\tB1\tC1\tA1-B1\tB1-C1')
    expect(tsvDa3).not.toContain('30 Hz Flicker')

    const tsvFlk = formatRecordClipboardTsv(flk)
    expect(tsvFlk).toContain('30 Hz Flicker')
    expect(tsvFlk).toContain('30.00')
  })

  it('round-trips JSON session preserving manual markers, manual protocol, overlays, and edge cases', () => {
    const records = loadLeftExamples()
    const target = records[1]
    target.protocol = 'light_adapted_3_flicker'
    target.metadata.strain_lastname = 'C57BL/6J'
    target.metadata.mouse_id_name = 'Mouse-04'
    target.markers = { a1_idx: 57, b1_idx: 100, c1_idx: 266, is_manual: true }
    records[0].overlay_enabled = true

    const cfg = { ...defaultDetectionConfig(), include_right_od: true }
    const json = serializeSessionJson(records, cfg, target.record_id)
    const loaded = parseSessionJson(json)

    expect(loaded.warnings).toEqual([])
    expect(loaded.records.length).toBe(4)
    expect(loaded.activeRecordId).toBe(target.record_id)
    expect(loaded.config.include_right_od).toBe(true)

    const restored = loaded.records.find((r) => r.record_id === target.record_id)!
    expect(restored.protocol).toBe('light_adapted_3_flicker')
    expect(restored.metadata.mouse_id_name).toBe('Mouse-04')
    expect(restored.markers).toEqual({ a1_idx: 57, b1_idx: 100, c1_idx: 266, is_manual: true })
    expect(loaded.records[0].overlay_enabled).toBe(true)

    // Corrupt JSON & invalid schema errors
    expect(() => parseSessionJson('{not valid json')).toThrow(/Invalid JSON/)
    expect(() => parseSessionJson(JSON.stringify({ foo: 'bar' }))).toThrow(/Invalid ERG session/)

    // Desktop session without embedded waveform matches already-loaded CSV and clamps OOB markers
    const desktopLike = JSON.stringify({
      schema_version: 1,
      active_record_id: 'desk1',
      records: [
        {
          record_id: 'desk1',
          file_path: '/win/path/Dark-Adapted_10_ERG_LEFT - OS.csv',
          file_name: 'Dark-Adapted_10_ERG_LEFT - OS.csv',
          protocol: 'bogus_protocol',
          active_channel: 'MISSING_CH',
          metadata: { strain_lastname: 'DesktopC57' },
          markers: { a1_idx: -20, b1_idx: 90, c1_idx: 99999, is_manual: true },
        },
        {
          record_id: 'unmatched',
          file_name: 'never_loaded.csv',
          markers: { a1_idx: 1, b1_idx: 2, c1_idx: 3 },
        },
      ],
    })
    const fromDesk = parseSessionJson(desktopLike, records)
    expect(fromDesk.records.length).toBe(1)
    expect(fromDesk.warnings.length).toBe(1)
    expect(fromDesk.records[0].markers.a1_idx).toBe(0)
    expect(fromDesk.records[0].markers.c1_idx).toBe(511)
    expect(fromDesk.records[0].protocol).toBe('dark_adapted_10')
    expect(fromDesk.records[0].metadata.strain_lastname).toBe('DesktopC57')
  })
})
