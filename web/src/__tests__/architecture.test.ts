import { describe, expect, it } from 'vitest'

import { readDropDataTransfer, readFileListToCsvInputs } from '../core/fileDrop'
import { TRANSLATIONS, translate } from '../core/i18n'
import {
  defaultDetectionConfig,
  PROTOCOL_ORDER,
  sanitizeDetectionConfig,
} from '../core/models'

describe('Web Architecture Robustness (i18n, config sanitization, recursive drop)', () => {
  it('maintains 100% EN/ES translation key parity with no empty strings', () => {
    const enKeys = Object.keys(TRANSLATIONS.en).sort()
    const esKeys = Object.keys(TRANSLATIONS.es).sort()
    expect(esKeys).toEqual(enKeys)

    for (const key of enKeys) {
      expect(TRANSLATIONS.en[key].trim().length).toBeGreaterThan(0)
      expect(TRANSLATIONS.es[key].trim().length).toBeGreaterThan(0)
    }

    // Parameter substitution and fallback to key on unknown identifier
    expect(translate('en', 'status_loaded', { loaded: 4, skipped: 2 })).toBe(
      'Loaded 4 trace(s) (2 RIGHT - OD skipped).',
    )
    expect(translate('es', 'status_loaded', { loaded: 4, skipped: 2 })).toBe(
      'Cargadas 4 curva(s) (2 de RIGHT - OD omitidas).',
    )
    expect(translate('en', 'nonexistent_key_xyz')).toBe('nonexistent_key_xyz')
  })

  it('sanitizes corrupt, partial, NaN, and inverted detection configs safely', () => {
    const def = defaultDetectionConfig()
    expect(sanitizeDetectionConfig(null)).toEqual(def)
    expect(sanitizeDetectionConfig('invalid')).toEqual(def)
    expect(sanitizeDetectionConfig({})).toEqual(def)

    const messy = sanitizeDetectionConfig({
      include_right_od: 1,
      windows: {
        // Inverted min/max should be normalized
        dark_adapted_3: {
          a_min_ms: 40,
          a_max_ms: 10,
          b_min_ms: 120,
          b_max_ms: 35,
          c_min_ms: 210,
          c_max_ms: 105,
        },
        // NaN field should fall back cleanly to default for that protocol
        dark_adapted_10: {
          a_min_ms: 'not-a-number',
          a_max_ms: 35,
          b_min_ms: 25,
          b_max_ms: 105,
          c_min_ms: 95,
          c_max_ms: 205,
        },
      },
    })

    expect(messy.include_right_od).toBe(true)
    expect(messy.windows.dark_adapted_3).toEqual({
      a_min_ms: 10,
      a_max_ms: 40,
      b_min_ms: 35,
      b_max_ms: 120,
      c_min_ms: 105,
      c_max_ms: 210,
    })
    expect(messy.windows.dark_adapted_10).toEqual(def.windows.dark_adapted_10)
    for (const proto of PROTOCOL_ORDER) {
      expect(messy.windows[proto]).toBeDefined()
    }
  })

  it('recursively traverses nested dropped directories across multi-batch readEntries and falls back to FileList', async () => {
    const makeMockFile = (name: string, body: string, relPath?: string) => {
      const f = new File([body], name, { type: 'text/csv' })
      if (relPath) {
        Object.defineProperty(f, 'webkitRelativePath', { value: relPath })
      }
      return f
    }

    // 1. Plain FileList input preserving webkitRelativePath
    const fileA = makeMockFile('a.csv', 'data-a', 'Mouse01/a.csv')
    const fileB = makeMockFile('b.csv', 'data-b')
    const fromList = await readFileListToCsvInputs([fileA, fileB])
    expect(fromList.map((x) => x.relativePath)).toEqual(['Mouse01/a.csv', 'b.csv'])
    expect(fromList[0].content).toBeInstanceOf(Uint8Array)
    expect(new TextDecoder().decode(fromList[0].content as Uint8Array)).toBe('data-a')

    // 2. Recursive webkitGetAsEntry with multi-batch directory reader (simulates >100 entries)
    const entry1 = {
      isFile: true,
      isDirectory: false,
      name: 'da3.csv',
      fullPath: '/Mouse01/da3.csv',
      file: (cb: (f: File) => void) => cb(makeMockFile('da3.csv', 'csv1')),
    }
    const entry2 = {
      isFile: true,
      isDirectory: false,
      name: 'da10.csv',
      fullPath: '/Mouse01/sub/da10.csv',
      file: (cb: (f: File) => void) => cb(makeMockFile('da10.csv', 'csv2')),
    }
    const subDir = {
      isFile: false,
      isDirectory: true,
      name: 'sub',
      fullPath: '/Mouse01/sub',
      createReader: () => {
        let called = false
        return {
          readEntries: (cb: (entries: unknown[]) => void) => {
            if (!called) {
              called = true
              cb([entry2])
            } else {
              cb([])
            }
          },
        }
      },
    }
    const rootDir = {
      isFile: false,
      isDirectory: true,
      name: 'Mouse01',
      fullPath: '/Mouse01',
      createReader: () => {
        const batches = [[entry1], [subDir], []]
        let idx = 0
        return {
          readEntries: (cb: (entries: unknown[]) => void) => {
            cb(batches[idx++] ?? [])
          },
        }
      },
    }

    const mockDt = {
      items: [{ webkitGetAsEntry: () => rootDir }],
      files: [],
    } as unknown as DataTransfer

    const dropped = await readDropDataTransfer(mockDt)
    expect(dropped.map((x) => x.relativePath)).toEqual(['Mouse01/da3.csv', 'Mouse01/sub/da10.csv'])

    // 3. Fallback when webkitGetAsEntry is unavailable
    const fallbackDt = {
      items: [],
      files: [fileB],
    } as unknown as DataTransfer
    const fallbackRes = await readDropDataTransfer(fallbackDt)
    expect(fallbackRes.map((x) => x.name)).toEqual(['b.csv'])
  })
})
