/**
 * Retimax-format 2x6 ERG metrics table plus conditional 30 Hz Flicker analysis bar.
 */

import React, { useMemo } from 'react'

import { computeFlickerMetrics, computePeakMetrics } from '../core/analysis'
import { translate, type Language } from '../core/i18n'
import { getActiveSignal, type ERGSessionRecord } from '../core/models'

interface MetricsTableProps {
  record: ERGSessionRecord | null
  language: Language
}

export const MetricsTable: React.FC<MetricsTableProps> = ({ record, language }) => {
  const tr = (key: string) => translate(language, key)

  const metrics = useMemo(() => {
    if (!record) return null
    return computePeakMetrics(record.time_ms, getActiveSignal(record), record.markers)
  }, [record])

  const flicker = useMemo(() => {
    if (!record || record.protocol !== 'light_adapted_3_flicker') return null
    return computeFlickerMetrics(record.time_ms, getActiveSignal(record))
  }, [record])

  const eyeHeader =
    record?.eye === 'RIGHT - OD' ? tr('plot_eye_header_od') : tr('plot_eye_header_os')

  const fmt = (v: number | undefined) => (v === undefined ? '—' : v.toFixed(2))

  return (
    <section className="panel-card table-card" aria-label="ERG Metrics Summary">
      <table className="retimax-table" id="retimax-metrics-table">
        <thead>
          <tr>
            <th>{eyeHeader}</th>
            <th>A1</th>
            <th>B1</th>
            <th>C1</th>
            <th>A1-B1</th>
            <th>B1-C1</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th>{tr('table_amplitude')}</th>
            <td data-testid="metric-a1-uv">{fmt(metrics?.a1_uv)}</td>
            <td data-testid="metric-b1-uv">{fmt(metrics?.b1_uv)}</td>
            <td data-testid="metric-c1-uv">{fmt(metrics?.c1_uv)}</td>
            <td className="cell-highlight" data-testid="metric-a1b1-uv">
              {fmt(metrics?.a1_b1_uv)}
            </td>
            <td data-testid="metric-b1c1-uv">{fmt(metrics?.b1_c1_uv)}</td>
          </tr>
          <tr>
            <th>{tr('table_peak_time')}</th>
            <td data-testid="metric-a1-ms">{fmt(metrics?.a1_ms)}</td>
            <td data-testid="metric-b1-ms">{fmt(metrics?.b1_ms)}</td>
            <td data-testid="metric-c1-ms">{fmt(metrics?.c1_ms)}</td>
            <td data-testid="metric-a1b1-ms">{fmt(metrics?.a1_b1_ms)}</td>
            <td data-testid="metric-b1c1-ms">{fmt(metrics?.b1_c1_ms)}</td>
          </tr>
        </tbody>
      </table>

      {flicker && (
        <div className="flicker-bar" data-testid="flicker-analysis-bar">
          <h2 className="flicker-bar-title">{tr('flicker_panel_title')}</h2>
          <div className="flicker-grid">
            <div>
              <div className="flicker-metric-label">{tr('flicker_mean_pt')}</div>
              <div className="flicker-metric-value" data-testid="flicker-mean-pt">
                {flicker.mean_peak_to_trough_uv.toFixed(2)} µV
              </div>
            </div>
            <div>
              <div className="flicker-metric-label">{tr('flicker_sd_pt')}</div>
              <div className="flicker-metric-value">
                ± {flicker.std_peak_to_trough_uv.toFixed(2)} µV
              </div>
            </div>
            <div>
              <div className="flicker-metric-label">{tr('flicker_fft_amp')}</div>
              <div className="flicker-metric-value" data-testid="flicker-fft-amp">
                {flicker.fft_fundamental_amp_uv.toFixed(2)} µV
              </div>
            </div>
            <div>
              <div className="flicker-metric-label">{tr('flicker_fft_pp')}</div>
              <div className="flicker-metric-value">
                {flicker.fft_peak_to_peak_uv.toFixed(2)} µV
              </div>
            </div>
            <div>
              <div className="flicker-metric-label">{tr('flicker_dom_freq')}</div>
              <div className="flicker-metric-value" data-testid="flicker-dom-freq">
                {flicker.dominant_freq_hz.toFixed(2)} Hz
              </div>
            </div>
            <div>
              <div className="flicker-metric-label">{tr('flicker_cycles')}</div>
              <div className="flicker-metric-value" data-testid="flicker-cycles">
                {flicker.cycles_detected}
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
