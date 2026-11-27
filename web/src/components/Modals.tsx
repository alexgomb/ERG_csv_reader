/**
 * Settings (physiological detection windows & RIGHT - OD filter) and About modals.
 */

import React, { useState } from 'react'

import { translate, type Language, type Theme } from '../core/i18n'
import {
  APP_AUTHOR,
  APP_LICENSE,
  APP_NAME,
  APP_VERSION,
  defaultDetectionConfig,
  NBIO_URL,
  PROTOCOL_ORDER,
  REPO_URL,
  sanitizeDetectionConfig,
  type DetectionConfig,
  type DetectionWindow,
  type ERGProtocol,
} from '../core/models'

interface SettingsModalProps {
  config: DetectionConfig
  language: Language
  onApply: (config: DetectionConfig) => void
  onClose: () => void
}

const WINDOW_FIELDS: Array<keyof DetectionWindow> = [
  'a_min_ms',
  'a_max_ms',
  'b_min_ms',
  'b_max_ms',
  'c_min_ms',
  'c_max_ms',
]

export const SettingsModal: React.FC<SettingsModalProps> = ({
  config,
  language,
  onApply,
  onClose,
}) => {
  const tr = (key: string) => translate(language, key)
  const [draft, setDraft] = useState<DetectionConfig>(() => sanitizeDetectionConfig(config))

  const updateWindowField = (
    proto: ERGProtocol,
    field: keyof DetectionWindow,
    rawVal: string,
  ) => {
    const val = Number(rawVal)
    if (!Number.isFinite(val)) return
    setDraft((prev) => ({
      ...prev,
      windows: {
        ...prev.windows,
        [proto]: {
          ...prev.windows[proto],
          [field]: Math.max(0, Math.min(500, val)),
        },
      },
    }))
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="settings-title">
      <div className="modal-card">
        <div className="modal-header">
          <h2 id="settings-title" className="modal-title">
            {tr('settings_title')}
          </h2>
          <button type="button" className="btn" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        <p className="muted-hint" style={{ fontSize: '12px' }}>
          {tr('settings_intro')}
        </p>

        <div className="group-box">
          <h3 className="group-title">{tr('settings_eye_group')}</h3>
          <label className="checkbox-row">
            <input
              id="settings-include-od"
              type="checkbox"
              checked={draft.include_right_od}
              onChange={(e) =>
                setDraft((prev) => ({ ...prev, include_right_od: e.target.checked }))
              }
            />
            <span>{tr('settings_include_od')}</span>
          </label>
        </div>

        <div className="group-box">
          <h3 className="group-title">{tr('settings_windows_group')}</h3>
          <div style={{ overflowX: 'auto' }}>
            <table className="settings-table">
              <thead>
                <tr>
                  <th>{tr('settings_col_protocol')}</th>
                  <th>A1 Min</th>
                  <th>A1 Max</th>
                  <th>B1 Min</th>
                  <th>B1 Max</th>
                  <th>C1 Min</th>
                  <th>C1 Max</th>
                </tr>
              </thead>
              <tbody>
                {PROTOCOL_ORDER.map((proto) => (
                  <tr key={proto}>
                    <td>{tr(`protocol_${proto}`)}</td>
                    {WINDOW_FIELDS.map((field) => (
                      <td key={field}>
                        <input
                          type="number"
                          className="input-field settings-num-input"
                          min={0}
                          max={500}
                          step={1}
                          value={draft.windows[proto][field]}
                          onChange={(e) => updateWindowField(proto, field, e.target.value)}
                        />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="modal-footer">
          <button
            type="button"
            id="settings-restore-btn"
            className="btn"
            onClick={() => setDraft(defaultDetectionConfig())}
          >
            {tr('settings_btn_restore')}
          </button>
          <div className="modal-footer-right">
            <button type="button" className="btn" onClick={onClose}>
              {tr('settings_btn_cancel')}
            </button>
            <button
              type="button"
              id="settings-apply-btn"
              className="btn btn-primary"
              onClick={() => onApply(sanitizeDetectionConfig(draft))}
            >
              {tr('settings_btn_apply')}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

interface AboutModalProps {
  language: Language
  theme: Theme
  onClose: () => void
}

export const AboutModal: React.FC<AboutModalProps> = ({ language, theme, onClose }) => {
  const tr = (key: string) => translate(language, key)
  const base = import.meta.env.BASE_URL
  const logoSrc = `${base}assets/${theme === 'dark' ? 'umh_nbio_dark.svg' : 'umh_nbio_light.svg'}`

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="about-title">
      <div className="modal-card modal-card-narrow">
        <div className="brand-row">
          <img
            src={`${base}favicon.svg`}
            alt="nBio ERG-Trace icon"
            className="brand-icon"
            style={{ width: 48, height: 48 }}
          />
          <div className="brand-text-col">
            <h2 id="about-title" className="modal-title">
              {APP_NAME}
            </h2>
            <span className="brand-sub">{tr('subtitle_badge')}</span>
          </div>
        </div>

        <div className="about-banner">
          <img
            src={logoSrc}
            alt="Grupo nBio · Instituto de Bioingeniería · Universidad Miguel Hernández"
          />
        </div>

        <p style={{ margin: 0, fontSize: '12.5px', lineHeight: 1.5 }}>{tr('about_description')}</p>

        <div className="about-info-grid">
          <span className="about-info-label">{tr('about_author_label')}</span>
          <strong>{APP_AUTHOR}</strong>

          <span className="about-info-label">{tr('about_group_label')}</span>
          <span>{tr('about_group_value')}</span>

          <span className="about-info-label">{tr('about_web_label')}</span>
          <a className="about-link" href={NBIO_URL} target="_blank" rel="noreferrer">
            {NBIO_URL}
          </a>

          <span className="about-info-label">{tr('about_version_label')}</span>
          <span>v{APP_VERSION}</span>

          <span className="about-info-label">{tr('about_license_label')}</span>
          <span>{APP_LICENSE}</span>

          <span className="about-info-label">{tr('about_repo_label')}</span>
          <a className="about-link" href={REPO_URL} target="_blank" rel="noreferrer">
            {REPO_URL}
          </a>
        </div>

        <div className="modal-footer" style={{ justifyContent: 'flex-end' }}>
          <button
            type="button"
            id="about-close-btn"
            className="btn btn-primary"
            onClick={onClose}
          >
            {tr('about_close')}
          </button>
        </div>
      </div>
    </div>
  )
}
