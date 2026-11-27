/**
 * Retimax-inspired right vertical toolbar with file loading, pure display/scale controls,
 * marker actions, exports, EN/ES language toggle, Light/Dark theme toggle, and About button.
 */

import React from 'react'

import { translate, type Language, type Theme } from '../core/i18n'
import type { ERGSessionRecord } from '../core/models'

interface ControlsPanelProps {
  activeRecord: ERGSessionRecord | null
  hasRecords: boolean
  language: Language
  theme: Theme
  autoScale: boolean
  magnifier: number
  showGrid: boolean
  onOpenCsv: () => void
  onOpenFolder: () => void
  onLoadExamples: () => void
  onSaveSession: () => void
  onLoadSession: () => void
  onChangeChannel: (channel: string) => void
  onChangeMagnifier: (value: number) => void
  onToggleAutoScale: (enabled: boolean) => void
  onApplyRetimax250: () => void
  onResetView: () => void
  onToggleGrid: (enabled: boolean) => void
  onResetMarkers: () => void
  onOpenSettings: () => void
  onCopyTable: () => void
  onExportCsv: () => void
  onExportXlsx: () => void
  onExportPng: () => void
  onExportSvg: () => void
  onChangeLanguage: (lang: Language) => void
  onChangeTheme: (theme: Theme) => void
  onOpenAbout: () => void
}

export const ControlsPanel: React.FC<ControlsPanelProps> = ({
  activeRecord,
  hasRecords,
  language,
  theme,
  autoScale,
  magnifier,
  showGrid,
  onOpenCsv,
  onOpenFolder,
  onLoadExamples,
  onSaveSession,
  onLoadSession,
  onChangeChannel,
  onChangeMagnifier,
  onToggleAutoScale,
  onApplyRetimax250,
  onResetView,
  onToggleGrid,
  onResetMarkers,
  onOpenSettings,
  onCopyTable,
  onExportCsv,
  onExportXlsx,
  onExportPng,
  onExportSvg,
  onChangeLanguage,
  onChangeTheme,
  onOpenAbout,
}) => {
  const tr = (key: string) => translate(language, key)
  const channels = activeRecord ? Object.keys(activeRecord.channels) : []

  const stepMagnifier = (factor: number) => {
    const next = Math.max(0.25, Math.min(25, Math.round(magnifier * factor * 100) / 100))
    onChangeMagnifier(next)
  }

  return (
    <aside className="panel-card controls-card" aria-label="Waveform Controls and Export">
      {/* 1. Files & Sessions */}
      <div className="group-box">
        <h2 className="group-title">{tr('ctrl_files_group')}</h2>
        <button
          type="button"
          id="ctrl-open-csv-btn"
          className="btn btn-primary"
          onClick={onOpenCsv}
        >
          {tr('btn_open_csv')}
        </button>
        <div className="btn-row-2">
          <button type="button" id="ctrl-open-folder-btn" className="btn" onClick={onOpenFolder}>
            {tr('btn_open_folder')}
          </button>
          <button
            type="button"
            id="ctrl-load-examples-btn"
            className="btn"
            onClick={onLoadExamples}
          >
            {tr('btn_load_examples')}
          </button>
        </div>
        <div className="btn-row-2">
          <button
            type="button"
            id="ctrl-save-session-btn"
            className="btn"
            disabled={!hasRecords}
            onClick={onSaveSession}
          >
            {tr('btn_save_session')}
          </button>
          <button type="button" id="ctrl-load-session-btn" className="btn" onClick={onLoadSession}>
            {tr('btn_load_session')}
          </button>
        </div>
      </div>

      {/* 2. Pure Display & Scale */}
      <div className="group-box">
        <h2 className="group-title">{tr('ctrl_display_group')}</h2>
        <label className="field-caption" htmlFor="ctrl-channel-select">
          {tr('label_channel')}
        </label>
        <select
          id="ctrl-channel-select"
          className="select-field"
          disabled={!activeRecord}
          value={activeRecord?.active_channel ?? ''}
          onChange={(e) => onChangeChannel(e.target.value)}
        >
          {channels.map((ch) => (
            <option key={ch} value={ch}>
              {ch}
            </option>
          ))}
        </select>

        <label className="field-caption" htmlFor="ctrl-magnifier-input">
          {tr('label_magnifier')}
        </label>
        <div className="mag-row">
          <button
            type="button"
            className="btn"
            disabled={!activeRecord}
            title={tr('btn_scale_down')}
            onClick={() => stepMagnifier(0.5)}
          >
            ▼
          </button>
          <input
            id="ctrl-magnifier-input"
            type="number"
            className="input-field"
            style={{ textAlign: 'center', fontFamily: 'JetBrains Mono, monospace' }}
            min={0.25}
            max={25}
            step={0.25}
            disabled={!activeRecord}
            value={magnifier}
            onChange={(e) => {
              const v = Number(e.target.value)
              if (Number.isFinite(v) && v >= 0.25 && v <= 25) {
                onChangeMagnifier(v)
              }
            }}
          />
          <button
            type="button"
            className="btn"
            disabled={!activeRecord}
            title={tr('btn_scale_up')}
            onClick={() => stepMagnifier(2)}
          >
            ▲
          </button>
        </div>

        <div className="btn-row-2">
          <button
            type="button"
            id="ctrl-autoscale-btn"
            className={`btn ${autoScale ? 'btn-active' : ''}`}
            disabled={!activeRecord}
            onClick={() => onToggleAutoScale(!autoScale)}
          >
            {tr('btn_autoscale')}
          </button>
          <button
            type="button"
            id="ctrl-retimax250-btn"
            className="btn"
            disabled={!activeRecord}
            onClick={onApplyRetimax250}
          >
            {tr('btn_retimax_250')}
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '6px' }}>
          <button
            type="button"
            id="ctrl-reset-view-btn"
            className="btn"
            style={{ flex: 1 }}
            disabled={!activeRecord}
            onClick={onResetView}
          >
            {tr('btn_reset_view')}
          </button>
          <label className="checkbox-row">
            <input
              id="ctrl-grid-checkbox"
              type="checkbox"
              checked={showGrid}
              onChange={(e) => onToggleGrid(e.target.checked)}
            />
            <span>{tr('chk_grid')}</span>
          </label>
        </div>
      </div>

      {/* 3. Markers */}
      <div className="group-box">
        <h2 className="group-title">{tr('ctrl_markers_group')}</h2>
        <div className="btn-row-2">
          <button
            type="button"
            id="ctrl-reset-markers-btn"
            className="btn"
            disabled={!activeRecord}
            onClick={onResetMarkers}
          >
            {tr('btn_reset_markers')}
          </button>
          <button type="button" id="ctrl-settings-btn" className="btn" onClick={onOpenSettings}>
            {tr('btn_settings')}
          </button>
        </div>
      </div>

      {/* 4. Export */}
      <div className="group-box">
        <h2 className="group-title">{tr('ctrl_export_group')}</h2>
        <button
          type="button"
          id="ctrl-copy-table-btn"
          className="btn"
          disabled={!activeRecord}
          onClick={onCopyTable}
        >
          {tr('btn_copy_table')}
        </button>
        <div className="btn-row-2">
          <button
            type="button"
            id="ctrl-export-csv-btn"
            className="btn"
            disabled={!hasRecords}
            onClick={onExportCsv}
          >
            {tr('btn_export_csv')}
          </button>
          <button
            type="button"
            id="ctrl-export-xlsx-btn"
            className="btn"
            disabled={!hasRecords}
            onClick={onExportXlsx}
          >
            {tr('btn_export_xlsx')}
          </button>
        </div>
        <div className="btn-row-2">
          <button
            type="button"
            id="ctrl-export-png-btn"
            className="btn"
            disabled={!activeRecord}
            onClick={onExportPng}
          >
            {tr('btn_export_png')}
          </button>
          <button
            type="button"
            id="ctrl-export-svg-btn"
            className="btn"
            disabled={!activeRecord}
            onClick={onExportSvg}
          >
            {tr('btn_export_svg')}
          </button>
        </div>
      </div>

      {/* 5. Appearance */}
      <div className="group-box">
        <h2 className="group-title">{tr('ctrl_appearance_group')}</h2>
        <span className="field-caption">{tr('label_language')}</span>
        <div className="btn-row-2">
          <button
            type="button"
            id="ctrl-lang-en-btn"
            className={`btn ${language === 'en' ? 'btn-active' : ''}`}
            onClick={() => onChangeLanguage('en')}
          >
            EN
          </button>
          <button
            type="button"
            id="ctrl-lang-es-btn"
            className={`btn ${language === 'es' ? 'btn-active' : ''}`}
            onClick={() => onChangeLanguage('es')}
          >
            ES
          </button>
        </div>

        <span className="field-caption">{tr('label_theme')}</span>
        <div className="btn-row-2">
          <button
            type="button"
            id="ctrl-theme-light-btn"
            className={`btn ${theme === 'light' ? 'btn-active' : ''}`}
            onClick={() => onChangeTheme('light')}
          >
            {tr('theme_light_short')}
          </button>
          <button
            type="button"
            id="ctrl-theme-dark-btn"
            className={`btn ${theme === 'dark' ? 'btn-active' : ''}`}
            onClick={() => onChangeTheme('dark')}
          >
            {tr('theme_dark_short')}
          </button>
        </div>
      </div>

      <button type="button" id="ctrl-about-btn" className="btn" onClick={onOpenAbout}>
        {tr('btn_about')}
      </button>
    </aside>
  )
}
