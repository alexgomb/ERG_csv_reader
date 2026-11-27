/**
 * Main application component for nBio ERG-Trace Web.
 * 100% client-side mouse ERG CSV analyzer with full parity to the desktop PySide6 app.
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { ControlsPanel } from './components/ControlsPanel'
import { MetricsTable } from './components/MetricsTable'
import { AboutModal, SettingsModal } from './components/Modals'
import { Sidebar } from './components/Sidebar'
import { WaveformPlot, type WaveformPlotHandle } from './components/WaveformPlot'
import { autoDetectMarkers } from './core/analysis'
import {
  buildSummaryCsvText,
  buildSummaryXlsxBlob,
  formatRecordClipboardTsv,
  parseSessionJson,
  serializeSessionJson,
  triggerBlobDownload,
} from './core/exporters'
import { readDropDataTransfer, readFileListToCsvInputs } from './core/fileDrop'
import { translate, type Language, type Theme } from './core/i18n'
import {
  APP_NAME,
  defaultDetectionConfig,
  getActiveSignal,
  protocolDisplayName,
  sanitizeDetectionConfig,
  type DetectionConfig,
  type ERGProtocol,
  type ERGSessionRecord,
  type MouseMetadata,
} from './core/models'
import { loadCsvFilesBatch, type CsvInputFile } from './core/parser'

const BUNDLED_EXAMPLES = [
  'Dark-Adapted_10_ERG_LEFT - OS.csv',
  'Dark-Adapted_10_ERG_RIGHT - OD.csv',
  'Dark-Adapted_3_ERG_RIGHT_LEFT - OS.csv',
  'Dark-Adapted_3_ERG_RIGHT_RIGHT - OD.csv',
  'Light-Adapted_3_ERG_LEFT - OS.csv',
  'Light-Adapted_3_ERG_RIGHT - OD.csv',
  'Light-Adapted_3_Flicker_ERG_LEFT - OS.csv',
  'Light-Adapted_3_Flicker_ERG_RIGHT - OD.csv',
]

const STORAGE_KEYS = {
  lang: 'nbio_erg_lang',
  theme: 'nbio_erg_theme',
  grid: 'nbio_erg_grid',
  config: 'nbio_erg_config',
}

function loadStoredLanguage(): Language {
  try {
    const val = localStorage.getItem(STORAGE_KEYS.lang)
    if (val === 'en' || val === 'es') return val
  } catch {
    // ignore storage restrictions
  }
  return 'en'
}

function loadStoredTheme(): Theme {
  try {
    const val = localStorage.getItem(STORAGE_KEYS.theme)
    if (val === 'light' || val === 'dark') return val
  } catch {
    // ignore
  }
  return 'light'
}

function loadStoredGrid(): boolean {
  try {
    const val = localStorage.getItem(STORAGE_KEYS.grid)
    if (val !== null) return val !== 'false'
  } catch {
    // ignore
  }
  return true
}

function loadStoredConfig(): DetectionConfig {
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.config)
    if (raw) {
      return sanitizeDetectionConfig(JSON.parse(raw))
    }
  } catch {
    // ignore
  }
  return defaultDetectionConfig()
}

interface StatusState {
  key: string
  params?: Record<string, string | number>
}

export const App: React.FC = () => {
  const [language, setLanguage] = useState<Language>(loadStoredLanguage)
  const [theme, setTheme] = useState<Theme>(loadStoredTheme)
  const [showGrid, setShowGrid] = useState<boolean>(loadStoredGrid)
  const [config, setConfig] = useState<DetectionConfig>(loadStoredConfig)

  const [records, setRecords] = useState<ERGSessionRecord[]>([])
  const [activeRecordId, setActiveRecordId] = useState<string | null>(null)
  const [autoScale, setAutoScale] = useState<boolean>(false)
  const [magnifier, setMagnifier] = useState<number>(1.0)
  const [status, setStatus] = useState<StatusState>({ key: 'status_ready' })

  const [isDragOver, setIsDragOver] = useState<boolean>(false)
  const [showSettings, setShowSettings] = useState<boolean>(false)
  const [showAbout, setShowAbout] = useState<boolean>(false)

  const plotRef = useRef<WaveformPlotHandle>(null)
  const csvInputRef = useRef<HTMLInputElement>(null)
  const folderInputRef = useRef<HTMLInputElement>(null)
  const sessionInputRef = useRef<HTMLInputElement>(null)
  const dragDepthRef = useRef(0)

  const tr = useCallback(
    (key: string, params?: Record<string, string | number>) => translate(language, key, params),
    [language],
  )

  // Apply theme attribute to document root & persist preferences
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    try {
      localStorage.setItem(STORAGE_KEYS.theme, theme)
    } catch {
      // ignore
    }
  }, [theme])

  useEffect(() => {
    document.documentElement.lang = language
    document.title = `${APP_NAME} — ${language === 'es' ? 'Analizador de ERG Murino' : 'Mouse ERG Analyzer'}`
    try {
      localStorage.setItem(STORAGE_KEYS.lang, language)
    } catch {
      // ignore
    }
  }, [language])

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEYS.grid, String(showGrid))
    } catch {
      // ignore
    }
  }, [showGrid])

  const activeRecord = useMemo(
    () => records.find((r) => r.record_id === activeRecordId) ?? null,
    [records, activeRecordId],
  )

  const overlayRecords = useMemo(
    () => records.filter((r) => r.overlay_enabled && r.record_id !== activeRecordId),
    [records, activeRecordId],
  )

  const ingestCsvInputs = useCallback(
    (inputs: CsvInputFile[]) => {
      const result = loadCsvFilesBatch(inputs, config)
      if (result.records.length > 0) {
        setRecords((prev) => {
          const existing = new Set(prev.map((r) => r.file_path))
          const fresh = result.records.filter((r) => !existing.has(r.file_path))
          if (fresh.length === 0) return prev
          setActiveRecordId(fresh[0].record_id)
          return [...prev, ...fresh]
        })
      }

      if (result.errors.length > 0) {
        const detail = result.errors
          .slice(0, 3)
          .map((e) => `${e.fileName}: ${e.message}`)
          .join(' | ')
        setStatus({
          key: 'status_parse_errors',
          params: { count: result.errors.length, detail },
        })
      } else if (result.records.length > 0 && result.skipped_right_od.length > 0) {
        setStatus({
          key: 'status_loaded',
          params: { loaded: result.records.length, skipped: result.skipped_right_od.length },
        })
      } else if (result.records.length > 0) {
        setStatus({ key: 'status_loaded_no_skip', params: { loaded: result.records.length } })
      } else if (result.skipped_right_od.length > 0) {
        setStatus({
          key: 'status_all_skipped_od',
          params: { skipped: result.skipped_right_od.length },
        })
      }
    },
    [config],
  )

  const handleLoadExamples = useCallback(async () => {
    const base = import.meta.env.BASE_URL
    try {
      const inputs: CsvInputFile[] = await Promise.all(
        BUNDLED_EXAMPLES.map(async (name) => {
          const resp = await fetch(`${base}example_files/${encodeURIComponent(name)}`)
          if (!resp.ok) throw new Error(`HTTP ${resp.status} for ${name}`)
          const bytes = new Uint8Array(await resp.arrayBuffer())
          return { name, relativePath: `example_files/${name}`, content: bytes }
        }),
      )
      ingestCsvInputs(inputs)
    } catch (err) {
      setStatus({
        key: 'status_parse_errors',
        params: { count: 1, detail: err instanceof Error ? err.message : String(err) },
      })
    }
  }, [ingestCsvInputs])

  const handleSessionFileText = useCallback(
    (rawText: string) => {
      try {
        const loaded = parseSessionJson(rawText, records)
        setConfig(loaded.config)
        try {
          localStorage.setItem(STORAGE_KEYS.config, JSON.stringify(loaded.config))
        } catch {
          // ignore
        }
        setRecords(loaded.records)
        const nextActive =
          loaded.activeRecordId && loaded.records.some((r) => r.record_id === loaded.activeRecordId)
            ? loaded.activeRecordId
            : loaded.records[0]?.record_id ?? null
        setActiveRecordId(nextActive)
        if (loaded.warnings.length > 0) {
          setStatus({
            key: 'status_parse_errors',
            params: { count: loaded.warnings.length, detail: loaded.warnings[0] },
          })
        } else {
          setStatus({ key: 'status_session_loaded', params: { count: loaded.records.length } })
        }
      } catch (err) {
        setStatus({
          key: 'status_session_error',
          params: { detail: err instanceof Error ? err.message : String(err) },
        })
      }
    },
    [records],
  )

  // Drag & Drop handlers on the full app window
  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault()
    dragDepthRef.current++
    setIsDragOver(true)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    dragDepthRef.current = Math.max(0, dragDepthRef.current - 1)
    if (dragDepthRef.current === 0) {
      setIsDragOver(false)
    }
  }

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault()
    dragDepthRef.current = 0
    setIsDragOver(false)
    const droppedFiles = Array.from(e.dataTransfer.files ?? [])
    if (droppedFiles.length === 1 && droppedFiles[0].name.toLowerCase().endsWith('.json')) {
      const text = await droppedFiles[0].text()
      handleSessionFileText(text)
      return
    }
    const inputs = await readDropDataTransfer(e.dataTransfer)
    if (inputs.length > 0) {
      ingestCsvInputs(inputs)
    }
  }

  // Record mutation handlers
  const updateActiveRecord = useCallback(
    (updater: (rec: ERGSessionRecord) => ERGSessionRecord) => {
      if (!activeRecordId) return
      setRecords((prev) =>
        prev.map((rec) => (rec.record_id === activeRecordId ? updater(rec) : rec)),
      )
    },
    [activeRecordId],
  )

  const handleMarkerMove = useCallback(
    (marker: 'a1' | 'b1' | 'c1', sampleIdx: number) => {
      updateActiveRecord((rec) => ({
        ...rec,
        markers: {
          ...rec.markers,
          a1_idx: marker === 'a1' ? sampleIdx : rec.markers.a1_idx,
          b1_idx: marker === 'b1' ? sampleIdx : rec.markers.b1_idx,
          c1_idx: marker === 'c1' ? sampleIdx : rec.markers.c1_idx,
          is_manual: true,
        },
      }))
    },
    [updateActiveRecord],
  )

  const handleUpdateMetadata = useCallback(
    (patch: Partial<MouseMetadata>) => {
      updateActiveRecord((rec) => ({
        ...rec,
        metadata: { ...rec.metadata, ...patch },
      }))
    },
    [updateActiveRecord],
  )

  const handleChangeProtocol = useCallback(
    (protocol: ERGProtocol) => {
      updateActiveRecord((rec) => {
        if (rec.protocol === protocol) return rec
        const oldDefaultExam = protocolDisplayName(rec.protocol)
        const nextExam =
          !rec.metadata.exam.trim() || rec.metadata.exam.trim().toUpperCase() === oldDefaultExam
            ? protocolDisplayName(protocol)
            : rec.metadata.exam
        const nextMarkers = rec.markers.is_manual
          ? rec.markers
          : autoDetectMarkers(rec.time_ms, getActiveSignal(rec), protocol, config)
        return {
          ...rec,
          protocol,
          metadata: { ...rec.metadata, exam: nextExam },
          markers: nextMarkers,
        }
      })
    },
    [config, updateActiveRecord],
  )

  const handleChangeChannel = useCallback(
    (channel: string) => {
      updateActiveRecord((rec) => {
        if (!(channel in rec.channels)) return rec
        const nextMarkers = rec.markers.is_manual
          ? rec.markers
          : autoDetectMarkers(rec.time_ms, rec.channels[channel], rec.protocol, config)
        return { ...rec, active_channel: channel, markers: nextMarkers }
      })
    },
    [config, updateActiveRecord],
  )

  const handleResetMarkers = useCallback(() => {
    if (!activeRecord) return
    updateActiveRecord((rec) => ({
      ...rec,
      markers: autoDetectMarkers(rec.time_ms, getActiveSignal(rec), rec.protocol, config),
    }))
    setStatus({ key: 'status_markers_reset' })
  }, [activeRecord, config, updateActiveRecord])

  const handleApplySettings = (newCfg: DetectionConfig) => {
    setConfig(newCfg)
    try {
      localStorage.setItem(STORAGE_KEYS.config, JSON.stringify(newCfg))
    } catch {
      // ignore
    }
    setRecords((prev) =>
      prev.map((rec) =>
        rec.markers.is_manual
          ? rec
          : {
              ...rec,
              markers: autoDetectMarkers(rec.time_ms, getActiveSignal(rec), rec.protocol, newCfg),
            },
      ),
    )
    setShowSettings(false)
    setStatus({ key: 'status_settings_updated' })
  }

  const handleToggleOverlay = (recordId: string, checked: boolean) => {
    setRecords((prev) =>
      prev.map((r) => (r.record_id === recordId ? { ...r, overlay_enabled: checked } : r)),
    )
  }

  const handleClearOverlays = () => {
    setRecords((prev) => prev.map((r) => ({ ...r, overlay_enabled: false })))
  }

  const handleRemoveRecord = (recordId: string) => {
    setRecords((prev) => {
      const idx = prev.findIndex((r) => r.record_id === recordId)
      if (idx < 0) return prev
      const next = prev.filter((r) => r.record_id !== recordId)
      if (activeRecordId === recordId) {
        const nextRec = next[Math.min(idx, next.length - 1)] ?? null
        setActiveRecordId(nextRec ? nextRec.record_id : null)
      }
      return next
    })
  }

  const handleClearAll = () => {
    setRecords([])
    setActiveRecordId(null)
    setStatus({ key: 'status_ready' })
  }

  // Export handlers
  const handleCopyTable = async () => {
    if (!activeRecord) return
    const tsv = formatRecordClipboardTsv(activeRecord)
    try {
      await navigator.clipboard.writeText(tsv)
      setStatus({ key: 'status_copied' })
    } catch {
      setStatus({ key: 'status_copied' })
    }
  }

  const handleExportCsv = () => {
    if (records.length === 0) return
    const csv = buildSummaryCsvText(records)
    triggerBlobDownload(new Blob([csv], { type: 'text/csv;charset=utf-8' }), 'erg_summary.csv')
    setStatus({ key: 'status_exported', params: { file: 'erg_summary.csv' } })
  }

  const handleExportXlsx = async () => {
    if (records.length === 0) return
    const blob = await buildSummaryXlsxBlob(records)
    triggerBlobDownload(blob, 'erg_summary.xlsx')
    setStatus({ key: 'status_exported', params: { file: 'erg_summary.xlsx' } })
  }

  const handleSaveSession = () => {
    if (records.length === 0) return
    const json = serializeSessionJson(records, config, activeRecordId)
    triggerBlobDownload(
      new Blob([json], { type: 'application/json;charset=utf-8' }),
      'nbio_erg_session.json',
    )
    setStatus({ key: 'status_session_saved', params: { count: records.length } })
  }

  const handleExportPng = async () => {
    if (!activeRecord || !plotRef.current) return
    const stem = activeRecord.file_name.replace(/\.csv$/i, '').replace(/\s+/g, '_')
    await plotRef.current.exportPng(`${stem}.png`)
    setStatus({ key: 'status_exported', params: { file: `${stem}.png` } })
  }

  const handleExportSvg = () => {
    if (!activeRecord || !plotRef.current) return
    const stem = activeRecord.file_name.replace(/\.csv$/i, '').replace(/\s+/g, '_')
    plotRef.current.exportSvg(`${stem}.svg`)
    setStatus({ key: 'status_exported', params: { file: `${stem}.svg` } })
  }

  // Keyboard shortcuts (non-conflicting with standard browser bindings)
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null
      const inInput =
        target &&
        (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT')
      if (!inInput && !e.ctrlKey && !e.metaKey && !e.altKey && e.key.toLowerCase() === 'g') {
        setShowGrid((g) => !g)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  return (
    <div
      className="app-shell"
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Hidden native file inputs */}
      <input
        ref={csvInputRef}
        type="file"
        accept=".csv,text/csv"
        multiple
        hidden
        onChange={async (e) => {
          if (e.target.files && e.target.files.length > 0) {
            const inputs = await readFileListToCsvInputs(e.target.files)
            ingestCsvInputs(inputs)
            e.target.value = ''
          }
        }}
      />
      <input
        ref={folderInputRef}
        type="file"
        multiple
        hidden
        {...({ webkitdirectory: '', directory: '' } as Record<string, string>)}
        onChange={async (e) => {
          if (e.target.files && e.target.files.length > 0) {
            const inputs = await readFileListToCsvInputs(e.target.files)
            ingestCsvInputs(inputs)
            e.target.value = ''
          }
        }}
      />
      <input
        ref={sessionInputRef}
        type="file"
        accept=".json,application/json"
        hidden
        onChange={async (e) => {
          const file = e.target.files?.[0]
          if (file) {
            const text = await file.text()
            handleSessionFileText(text)
            e.target.value = ''
          }
        }}
      />

      {/* Compact top header bar */}
      <header className="top-bar">
        <div className="top-bar-left">
          <h1 className="top-bar-title">{APP_NAME}</h1>
          <span className="privacy-pill">{tr('privacy_badge')}</span>
        </div>
        <div className="top-bar-right">
          <a
            className="about-link"
            style={{ fontSize: '11.5px' }}
            href="https://github.com/alexgomb/ERG_csv_reader/releases/latest"
            target="_blank"
            rel="noreferrer"
          >
            Windows .exe
          </a>
        </div>
      </header>

      {/* Main Retimax-inspired 3-column workstation */}
      <main className="workspace-grid">
        <Sidebar
          records={records}
          activeRecord={activeRecord}
          language={language}
          theme={theme}
          onSelectRecord={setActiveRecordId}
          onToggleOverlay={handleToggleOverlay}
          onUpdateMetadata={handleUpdateMetadata}
          onChangeProtocol={handleChangeProtocol}
          onRemoveRecord={handleRemoveRecord}
          onClearOverlays={handleClearOverlays}
          onClearAll={handleClearAll}
        />

        <div className="center-column">
          <WaveformPlot
            ref={plotRef}
            record={activeRecord}
            overlays={overlayRecords}
            language={language}
            theme={theme}
            showGrid={showGrid}
            autoScale={autoScale}
            magnifier={magnifier}
            onMarkerMove={handleMarkerMove}
            onLoadExamples={handleLoadExamples}
            onOpenCsv={() => csvInputRef.current?.click()}
          />
          <MetricsTable record={activeRecord} language={language} />
        </div>

        <ControlsPanel
          activeRecord={activeRecord}
          hasRecords={records.length > 0}
          language={language}
          theme={theme}
          autoScale={autoScale}
          magnifier={magnifier}
          showGrid={showGrid}
          onOpenCsv={() => csvInputRef.current?.click()}
          onOpenFolder={() => folderInputRef.current?.click()}
          onLoadExamples={handleLoadExamples}
          onSaveSession={handleSaveSession}
          onLoadSession={() => sessionInputRef.current?.click()}
          onChangeChannel={handleChangeChannel}
          onChangeMagnifier={(v) => {
            setAutoScale(false)
            setMagnifier(v)
          }}
          onToggleAutoScale={setAutoScale}
          onApplyRetimax250={() => {
            setAutoScale(false)
            setMagnifier(1.0)
          }}
          onResetView={() => plotRef.current?.resetView()}
          onToggleGrid={setShowGrid}
          onResetMarkers={handleResetMarkers}
          onOpenSettings={() => setShowSettings(true)}
          onCopyTable={handleCopyTable}
          onExportCsv={handleExportCsv}
          onExportXlsx={handleExportXlsx}
          onExportPng={handleExportPng}
          onExportSvg={handleExportSvg}
          onChangeLanguage={setLanguage}
          onChangeTheme={setTheme}
          onOpenAbout={() => setShowAbout(true)}
        />
      </main>

      <footer className="status-bar" role="status" aria-live="polite" data-testid="status-bar">
        <span>{tr(status.key, status.params)}</span>
        <span>Grupo nBio · Instituto de Bioingeniería · UMH</span>
      </footer>

      {isDragOver && (
        <div className="drop-overlay">
          <div className="drop-overlay-box">{tr('drop_overlay_text')}</div>
        </div>
      )}

      {showSettings && (
        <SettingsModal
          config={config}
          language={language}
          onApply={handleApplySettings}
          onClose={() => setShowSettings(false)}
        />
      )}

      {showAbout && (
        <AboutModal language={language} theme={theme} onClose={() => setShowAbout(false)} />
      )}
    </div>
  )
}

export default App
