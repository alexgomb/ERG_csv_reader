import fs from 'node:fs'
import path from 'node:path'

import { describe, expect, it } from 'vitest'

import { defaultDetectionConfig } from '../core/models'
import {
  ERGParseError,
  inferMetadata,
  inferProtocol,
  loadCsvFilesBatch,
  parseRetimaxCsv,
} from '../core/parser'

const EXAMPLE_DIR = path.resolve(__dirname, '../../../example_files')

function loadExampleBytes(name: string): Uint8Array {
  return new Uint8Array(fs.readFileSync(path.join(EXAMPLE_DIR, name)))
}

describe('CSO Retimax CSV Parser (web)', () => {
  it('detects eye strictly from internal CSV header even when filename contains RIGHT', () => {
    const name = 'Dark-Adapted_3_ERG_RIGHT_LEFT - OS.csv'
    const rec = parseRetimaxCsv({ name, content: loadExampleBytes(name) })

    expect(rec.eye).toBe('LEFT - OS')
    expect(rec.protocol).toBe('dark_adapted_3')
    expect(rec.metadata.exam_start).toBe('23/10/2026 11:43:35')
    expect(rec.active_channel).toBe('AV1(uV)')
    expect(Object.keys(rec.channels).sort()).toEqual(['AV1(uV)', 'GAV(uV)'])
    expect(rec.time_ms.length).toBe(512)
    expect(rec.time_ms[0]).toBeCloseTo(0, 6)
    expect(rec.time_ms[511]).toBeCloseTo(249.511719, 4)
  })

  it('skips RIGHT - OD files by default and includes all 10 when enabled', () => {
    const allFiles = fs
      .readdirSync(EXAMPLE_DIR)
      .filter((f) => f.endsWith('.csv'))
      .map((name) => ({ name, relativePath: `example_files/${name}`, content: loadExampleBytes(name) }))

    const leftOnly = loadCsvFilesBatch(allFiles)
    expect(leftOnly.records.length).toBe(5)
    expect(leftOnly.skipped_right_od.length).toBe(5)
    expect(leftOnly.errors.length).toBe(0)
    expect(leftOnly.records.every((r) => r.eye === 'LEFT - OS')).toBe(true)

    const opsRec = leftOnly.records.find((r) => r.file_name.includes('OSCILLATORY'))!
    expect(opsRec.protocol).toBe('dark_adapted_3_ops')
    expect(inferProtocol('Potenciales_Oscilatorios_P21.csv', opsRec.time_ms)).toBe(
      'dark_adapted_3_ops',
    )

    const withOd = loadCsvFilesBatch(allFiles, {
      ...defaultDetectionConfig(),
      include_right_od: true,
    })
    expect(withOd.records.length).toBe(10)
    expect(withOd.skipped_right_od.length).toBe(0)
  })

  it('supports semicolon, comma, dot-decimal, UTF-8 BOM, Windows-1252, and multi-channel AV2', () => {
    const semi = parseRetimaxCsv({
      name: 'Dark-Adapted_3_semi.csv',
      content:
        'Exam start: 10/11/2026 08:15:00\r\n' +
        'LEFT - OS\r\n' +
        'Time(ms);GAV(uV);AV1(uV);AV2(uV)\r\n' +
        '0,0;0,0;1,5;2,0\r\n' +
        '10,0;-20,5;-25,5;-22,0\r\n' +
        '25,0;-100,25;-110,75;-108,0\r\n' +
        '55,0;180,5;190,0;185,5\r\n' +
        '130,0;10,0;5,25;6,0\r\n',
    })
    expect(Object.keys(semi.channels)).toEqual(['GAV(uV)', 'AV1(uV)', 'AV2(uV)'])
    expect(semi.channels['AV1(uV)'][2]).toBeCloseTo(-110.75, 5)
    expect(semi.channels['AV2(uV)'][3]).toBeCloseTo(185.5, 5)

    const comma = parseRetimaxCsv({
      name: 'Light-Adapted_3_comma.csv',
      content:
        '\uFEFFExam start: 10/11/2026 08:20:00\n' +
        'LEFT - OS\n' +
        'Time(ms),AV1(uV)\n' +
        '0.0,-3.0\n' +
        '15.0,-20.0\n' +
        '55.0,25.5\n' +
        '120.0,-2.0\n' +
        '249.5,-4.5\n',
    })
    expect(comma.protocol).toBe('light_adapted_3')
    expect(comma.channels['AV1(uV)'][2]).toBeCloseTo(25.5, 5)

    // Windows-1252 byte 0xB5 = 'µ'
    const latin =
      'Exam start: 01/01/2026 10:00:00\nleft - os\nTime(ms)\tAV1(\u00b5V)\n0,\t0,\n20,\t-100,\n50,\t180,\n120,\t10,\n'
    const cp1252Bytes = Uint8Array.from([...latin].map((ch) => ch.charCodeAt(0)))
    const rec1252 = parseRetimaxCsv({ name: 'DA_10_cp1252.csv', content: cp1252Bytes })
    expect(rec1252.eye).toBe('LEFT - OS')
    expect(rec1252.protocol).toBe('dark_adapted_10')
  })

  it('prioritizes 140-185ms flicker duration over light filename keyword', () => {
    const bytes = loadExampleBytes('Light-Adapted_3_Flicker_ERG_LEFT - OS.csv')
    const rec = parseRetimaxCsv({ name: 'Light_mouse01_OS.csv', content: bytes })
    expect(rec.protocol).toBe('light_adapted_3_flicker')

    const t250 = Array.from({ length: 512 }, (_, i) => (i * 250) / 512)
    expect(inferProtocol('DA_3_mouse.csv', t250)).toBe('dark_adapted_3')
    expect(inferProtocol('Scotopic_10.0_ERG.csv', t250)).toBe('dark_adapted_10')
    expect(inferProtocol('photopic_3.csv', t250)).toBe('light_adapted_3')
    expect(inferProtocol('generic_file.csv', t250)).toBe('unknown')
  })

  it('infers mouse metadata from non-generic parent folders only', () => {
    const generic = inferMetadata(
      'Dark-Adapted_3_LEFT - OS.csv',
      'example_files/Dark-Adapted_3_LEFT - OS.csv',
      '23/10/2026 11:00:00',
      'dark_adapted_3',
    )
    expect(generic.strain_lastname).toBe('')
    expect(generic.mouse_id_name).toBe('')

    const realMouse = inferMetadata(
      'Dark-Adapted_3_LEFT - OS.csv',
      'Cohort1/C57BL6_P21/Dark-Adapted_3_LEFT - OS.csv',
      '23/10/2026 11:00:00',
      'dark_adapted_3',
    )
    expect(realMouse.strain_lastname).toBe('C57BL6')
    expect(realMouse.mouse_id_name).toBe('C57BL6 P21')
    expect(realMouse.age).toBe('P21')
  })

  it('throws ERGParseError cleanly on malformed, truncated, or non-numeric CSVs', () => {
    expect(() =>
      parseRetimaxCsv({ name: 'short.csv', content: 'Exam start: x\nLEFT - OS\nTime(ms)\tAV1(uV)\n0,\t1,\n' }),
    ).toThrow(ERGParseError)

    expect(() =>
      parseRetimaxCsv({ name: 'no_hdr.csv', content: 'a\nb\nc\nd\ne\nf\n' }),
    ).toThrow(ERGParseError)

    expect(() =>
      parseRetimaxCsv({
        name: 'trunc.csv',
        content:
          'Exam start: x\nLEFT - OS\nTime(ms)\tGAV(uV)\tAV1(uV)\n0,\t1,0\t1,0\n1,\t2,0\n2,\t3,0\t3,0\n3,\t4,0\t4,0\n',
      }),
    ).toThrow(ERGParseError)

    expect(() =>
      parseRetimaxCsv({
        name: 'badnum.csv',
        content: 'Exam start: x\nLEFT - OS\nTime(ms)\tAV1(uV)\n0,\t1,0\n1,\tNaN_TEXT\n2,\t3,0\n3,\t4,0\n',
      }),
    ).toThrow(ERGParseError)

    expect(() =>
      parseRetimaxCsv({
        name: 'few.csv',
        content: 'Exam start: x\nLEFT - OS\nExtra\nTime(ms)\tAV1(uV)\n0,\t1,0\n1,\t2,0\n2,\t3,0\n',
      }),
    ).toThrow(ERGParseError)
  })

  it('handles mixed valid, OD, corrupt, and non-CSV inputs in batch load', () => {
    const res = loadCsvFilesBatch([
      { name: 'notes.txt', content: 'ignored' },
      { name: 'broken.csv', content: 'not\na\nvalid\nerg\nfile\n' },
      {
        name: 'Dark-Adapted_10_ERG_LEFT - OS.csv',
        content: loadExampleBytes('Dark-Adapted_10_ERG_LEFT - OS.csv'),
      },
      {
        name: 'Dark-Adapted_10_ERG_RIGHT - OD.csv',
        content: loadExampleBytes('Dark-Adapted_10_ERG_RIGHT - OD.csv'),
      },
    ])
    expect(res.records.length).toBe(1)
    expect(res.skipped_right_od.length).toBe(1)
    expect(res.errors.length).toBe(1)
  })
})
