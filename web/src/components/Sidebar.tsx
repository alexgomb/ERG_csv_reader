/**
 * Retimax-inspired left sidebar: subject/exam metadata, manual Protocol selector,
 * checkable loaded ERG trace list (GNS overlays), UMH · nBio SVG logo, and author credit.
 */

import React from 'react'

import { translate, type Language, type Theme } from '../core/i18n'
import {
  APP_NAME,
  PROTOCOL_ORDER,
  protocolShortLabel,
  type ERGProtocol,
  type ERGSessionRecord,
  type MouseMetadata,
} from '../core/models'

interface SidebarProps {
  records: ERGSessionRecord[]
  activeRecord: ERGSessionRecord | null
  language: Language
  theme: Theme
  onSelectRecord: (recordId: string) => void
  onToggleOverlay: (recordId: string, checked: boolean) => void
  onUpdateMetadata: (patch: Partial<MouseMetadata>) => void
  onChangeProtocol: (protocol: ERGProtocol) => void
  onRemoveRecord: (recordId: string) => void
  onClearOverlays: () => void
  onClearAll: () => void
}

export const Sidebar: React.FC<SidebarProps> = ({
  records,
  activeRecord,
  language,
  theme,
  onSelectRecord,
  onToggleOverlay,
  onUpdateMetadata,
  onChangeProtocol,
  onRemoveRecord,
  onClearOverlays,
  onClearAll,
}) => {
  const tr = (key: string) => translate(language, key)
  const base = import.meta.env.BASE_URL
  const logoSrc = `${base}assets/${theme === 'dark' ? 'umh_nbio_dark.svg' : 'umh_nbio_light.svg'}`
  const hasOverlays = records.some((r) => r.overlay_enabled)

  const formatListLabel = (rec: ERGSessionRecord) => {
    const eyeTag = rec.eye === 'RIGHT - OD' ? ' [OD]' : ''
    const manualTag = rec.markers.is_manual ? ' · M' : ''
    const mousePrefix = rec.metadata.mouse_id_name.trim()
      ? `${rec.metadata.mouse_id_name.trim()} — `
      : ''
    return `[${protocolShortLabel(rec.protocol)}]${eyeTag} ${mousePrefix}${rec.file_name}${manualTag}`
  }

  return (
    <aside className="panel-card sidebar-card" aria-label="Subject Metadata and Loaded Traces">
      {/* Brand header */}
      <div className="brand-row">
        <img
          src={`${base}favicon.svg`}
          alt="nBio ERG-Trace emblem"
          className="brand-icon"
          width={38}
          height={38}
        />
        <div className="brand-text-col">
          <span className="brand-name">{APP_NAME}</span>
          <span className="brand-sub">{tr('subtitle_badge')}</span>
        </div>
      </div>

      {/* Subject & Exam Metadata */}
      <div className="group-box">
        <h2 className="group-title">{tr('sidebar_subject_group')}</h2>
        <div className="meta-form">
          <label className="meta-label" htmlFor="meta-strain">
            {tr('label_strain')}
          </label>
          <input
            id="meta-strain"
            type="text"
            className="input-field"
            disabled={!activeRecord}
            placeholder={tr('placeholder_strain')}
            value={activeRecord?.metadata.strain_lastname ?? ''}
            onChange={(e) => onUpdateMetadata({ strain_lastname: e.target.value })}
          />

          <label className="meta-label" htmlFor="meta-mouse-id">
            {tr('label_mouse_id')}
          </label>
          <input
            id="meta-mouse-id"
            type="text"
            className="input-field"
            disabled={!activeRecord}
            placeholder={tr('placeholder_mouse_id')}
            value={activeRecord?.metadata.mouse_id_name ?? ''}
            onChange={(e) => onUpdateMetadata({ mouse_id_name: e.target.value })}
          />

          <label className="meta-label" htmlFor="meta-age">
            {tr('label_age')}
          </label>
          <input
            id="meta-age"
            type="text"
            className="input-field"
            disabled={!activeRecord}
            placeholder={tr('placeholder_age')}
            value={activeRecord?.metadata.age ?? ''}
            onChange={(e) => onUpdateMetadata({ age: e.target.value })}
          />

          <label className="meta-label" htmlFor="meta-protocol">
            {tr('label_protocol')}
          </label>
          <select
            id="meta-protocol"
            className="select-field"
            disabled={!activeRecord}
            value={activeRecord?.protocol ?? 'dark_adapted_3'}
            onChange={(e) => onChangeProtocol(e.target.value as ERGProtocol)}
          >
            {PROTOCOL_ORDER.map((proto) => (
              <option key={proto} value={proto}>
                {tr(`protocol_${proto}`)}
              </option>
            ))}
          </select>

          <label className="meta-label" htmlFor="meta-exam">
            {tr('label_exam')}
          </label>
          <input
            id="meta-exam"
            type="text"
            className="input-field"
            disabled={!activeRecord}
            placeholder={tr('placeholder_exam')}
            value={activeRecord?.metadata.exam ?? ''}
            onChange={(e) => onUpdateMetadata({ exam: e.target.value })}
          />

          <label className="meta-label" htmlFor="meta-exam-start">
            {tr('label_exam_start')}
          </label>
          <input
            id="meta-exam-start"
            type="text"
            className="input-field"
            readOnly
            disabled={!activeRecord}
            value={activeRecord?.metadata.exam_start ?? ''}
          />

          <label className="meta-label" htmlFor="meta-notes">
            {tr('label_notes')}
          </label>
          <input
            id="meta-notes"
            type="text"
            className="input-field"
            disabled={!activeRecord}
            placeholder={tr('placeholder_notes')}
            value={activeRecord?.metadata.notes ?? ''}
            onChange={(e) => onUpdateMetadata({ notes: e.target.value })}
          />
        </div>
      </div>

      {/* Loaded ERG Traces */}
      <div className="group-box traces-box">
        <h2 className="group-title">{tr('sidebar_traces_group')}</h2>
        <p className="muted-hint">{tr('sidebar_overlay_hint')}</p>

        <ul className="trace-list" id="loaded-traces-list">
          {records.length === 0 ? (
            <li className="trace-empty">
              <strong>{tr('empty_traces_title')}</strong>
              <span>{tr('empty_traces_hint')}</span>
            </li>
          ) : (
            records.map((rec) => {
              const isActive = activeRecord?.record_id === rec.record_id
              return (
                <li
                  key={rec.record_id}
                  className={`trace-item ${isActive ? 'active' : ''}`}
                  title={rec.file_path}
                  onClick={() => onSelectRecord(rec.record_id)}
                >
                  <input
                    type="checkbox"
                    aria-label={`Overlay ${rec.file_name}`}
                    checked={rec.overlay_enabled}
                    onClick={(e) => e.stopPropagation()}
                    onChange={(e) => onToggleOverlay(rec.record_id, e.target.checked)}
                  />
                  <span className="trace-item-label">{formatListLabel(rec)}</span>
                </li>
              )
            })
          )}
        </ul>

        <div className="btn-row-3">
          <button
            type="button"
            id="btn-remove-trace"
            className="btn"
            disabled={!activeRecord}
            onClick={() => activeRecord && onRemoveRecord(activeRecord.record_id)}
          >
            {tr('btn_remove_selected')}
          </button>
          <button
            type="button"
            id="btn-clear-overlays"
            className="btn"
            disabled={!hasOverlays}
            onClick={onClearOverlays}
          >
            {tr('btn_clear_overlays')}
          </button>
          <button
            type="button"
            id="btn-clear-all"
            className="btn"
            disabled={records.length === 0}
            onClick={onClearAll}
          >
            {tr('btn_clear_all')}
          </button>
        </div>
      </div>

      {/* Institutional UMH · nBio vector SVG logo */}
      <div className="umh-nbio-banner">
        <img
          src={logoSrc}
          alt="Grupo nBio · Instituto de Bioingeniería · Universidad Miguel Hernández"
          title="Grupo nBio · Instituto de Bioingeniería · Universidad Miguel Hernández"
        />
      </div>

      <p className="author-footer">{tr('author_credit')}</p>
    </aside>
  )
}
