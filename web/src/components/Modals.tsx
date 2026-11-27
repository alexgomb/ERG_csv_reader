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
  AUTHOR_GITHUB_URL,
  AUTHOR_LINKEDIN_URL,
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

        <div className="about-social-row" aria-label="Author profiles">
          <a
            id="about-github-link"
            className="social-pill social-pill-github"
            href={AUTHOR_GITHUB_URL}
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Alejandro Gombau García on GitHub"
          >
            <svg
              className="social-pill-icon"
              viewBox="0 0 24 24"
              width="16"
              height="16"
              aria-hidden="true"
            >
              <path
                fill="currentColor"
                d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.11.79-.25.79-.56 0-.28-.01-1.02-.02-2-3.2.7-3.88-1.54-3.88-1.54-.52-1.33-1.28-1.69-1.28-1.69-1.05-.72.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.03 1.77 2.71 1.26 3.37.96.1-.75.4-1.26.73-1.55-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.29 1.19-3.09-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.18 1.18a11.08 11.08 0 0 1 5.79 0c2.21-1.49 3.18-1.18 3.18-1.18.63 1.59.23 2.76.11 3.05.74.8 1.19 1.83 1.19 3.09 0 4.42-2.69 5.39-5.26 5.68.41.36.78 1.06.78 2.13 0 1.54-.01 2.78-.01 3.16 0 .31.21.67.8.56A11.51 11.51 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5Z"
              />
            </svg>
            <span className="social-pill-label">GitHub</span>
            <span className="social-pill-handle">@alexgomb</span>
            <span className="social-pill-arrow" aria-hidden="true">
              ↗
            </span>
          </a>

          <a
            id="about-linkedin-link"
            className="social-pill social-pill-linkedin"
            href={AUTHOR_LINKEDIN_URL}
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Alejandro Gombau García on LinkedIn"
          >
            <svg
              className="social-pill-icon social-pill-icon-linkedin"
              viewBox="0 0 24 24"
              width="16"
              height="16"
              aria-hidden="true"
            >
              <path
                fill="currentColor"
                d="M20.45 2H3.55A1.55 1.55 0 0 0 2 3.55v16.9A1.55 1.55 0 0 0 3.55 22h16.9A1.55 1.55 0 0 0 22 20.45V3.55A1.55 1.55 0 0 0 20.45 2ZM8.08 19H5.13V9.5h2.95V19ZM6.6 8.2a1.71 1.71 0 1 1 0-3.42 1.71 1.71 0 0 1 0 3.42ZM19 19h-2.95v-4.62c0-1.1-.02-2.52-1.54-2.52-1.54 0-1.78 1.2-1.78 2.44V19h-2.95V9.5h2.83v1.3h.04c.39-.75 1.36-1.54 2.8-1.54 2.99 0 3.55 1.97 3.55 4.53V19Z"
              />
            </svg>
            <span className="social-pill-label">LinkedIn</span>
            <span className="social-pill-handle">alejandro-gombau</span>
            <span className="social-pill-arrow" aria-hidden="true">
              ↗
            </span>
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
