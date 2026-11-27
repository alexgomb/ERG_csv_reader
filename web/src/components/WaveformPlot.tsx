/**
 * Interactive SVG ERG waveform canvas with Retimax grid, GNS reference overlays,
 * 60 FPS pointer-captured draggable A1/B1/C1 cursors, zoom/pan, and PNG/SVG export.
 */

import React, { useEffect, useImperativeHandle, useMemo, useRef, useState } from 'react'

import { snapTimeToIndex } from '../core/analysis'
import { translate, type Language, type Theme } from '../core/i18n'
import {
  getActiveSignal,
  protocolDisplayName,
  protocolShortLabel,
  type ERGSessionRecord,
} from '../core/models'

export interface WaveformPlotHandle {
  exportSvg: (fileName: string) => void
  exportPng: (fileName: string) => Promise<void>
  resetView: () => void
}

interface WaveformPlotProps {
  record: ERGSessionRecord | null
  overlays: ERGSessionRecord[]
  language: Language
  theme: Theme
  showGrid: boolean
  autoScale: boolean
  magnifier: number
  onMarkerMove: (marker: 'a1' | 'b1' | 'c1', sampleIdx: number) => void
  onLoadExamples: () => void
  onOpenCsv: () => void
}

interface ViewRange {
  xMin: number
  xMax: number
  yMin: number
  yMax: number
}

const PAD = { top: 20, right: 20, bottom: 44, left: 60 }
const OVERLAY_COLORS_LIGHT = ['#94A3B8', '#64748B', '#A78BFA', '#F59E0B', '#10B981']
const OVERLAY_COLORS_DARK = ['#64748B', '#94A3B8', '#C084FC', '#FBBF24', '#34D399']

function computeDefaultRange(
  record: ERGSessionRecord | null,
  overlays: ERGSessionRecord[],
  autoScale: boolean,
  magnifier: number,
): ViewRange {
  if (!record || record.time_ms.length === 0) {
    return { xMin: 0, xMax: 250, yMin: -250, yMax: 250 }
  }
  const t = record.time_ms
  const y = getActiveSignal(record)
  const xMin = t[0]
  const rawXMax = t[t.length - 1]
  const xMax = rawXMax >= 200 ? 250 : Math.max(rawXMax * 1.02, 10)

  if (autoScale) {
    const allSeries = [y, ...overlays.map((o) => getActiveSignal(o))]
    let minV = Infinity
    let maxV = -Infinity
    for (const s of allSeries) {
      for (const v of s) {
        if (v < minV) minV = v
        if (v > maxV) maxV = v
      }
    }
    if (!Number.isFinite(minV) || !Number.isFinite(maxV)) {
      return { xMin, xMax, yMin: -250, yMax: 250 }
    }
    const span = Math.max(maxV - minV, 10)
    const pad = 0.16 * span
    return { xMin, xMax, yMin: minV - pad, yMax: maxV + pad }
  }

  const half = 250 / Math.max(0.1, magnifier)
  return { xMin, xMax, yMin: -half, yMax: half }
}

function niceTicks(min: number, max: number, approxCount: number): number[] {
  const span = max - min
  if (span <= 0 || !Number.isFinite(span)) return [min]
  const rawStep = span / Math.max(2, approxCount)
  const mag = Math.pow(10, Math.floor(Math.log10(rawStep)))
  const norm = rawStep / mag
  let step: number
  if (norm <= 1.2) step = 1 * mag
  else if (norm <= 2.5) step = 2 * mag
  else if (norm <= 5.5) step = 5 * mag
  else step = 10 * mag

  const start = Math.ceil(min / step) * step
  const ticks: number[] = []
  for (let v = start; v <= max + step * 1e-6; v += step) {
    ticks.push(Math.abs(v) < step * 1e-9 ? 0 : Number(v.toFixed(6)))
    if (ticks.length > 40) break
  }
  return ticks
}

function buildPolylinePath(
  xs: readonly number[],
  ys: readonly number[],
  toSvgX: (x: number) => number,
  toSvgY: (y: number) => number,
): string {
  if (xs.length === 0) return ''
  const parts: string[] = new Array(xs.length)
  for (let i = 0; i < xs.length; i++) {
    const cmd = i === 0 ? 'M' : 'L'
    parts[i] = `${cmd}${toSvgX(xs[i]).toFixed(2)},${toSvgY(ys[i]).toFixed(2)}`
  }
  return parts.join(' ')
}

export const WaveformPlot = React.forwardRef<WaveformPlotHandle, WaveformPlotProps>(
  (
    {
      record,
      overlays,
      language,
      theme,
      showGrid,
      autoScale,
      magnifier,
      onMarkerMove,
      onLoadExamples,
      onOpenCsv,
    },
    ref,
  ) => {
    const tr = (key: string) => translate(language, key)
    const viewportRef = useRef<HTMLDivElement>(null)
    const svgRef = useRef<SVGSVGElement>(null)
    const [size, setSize] = useState({ width: 820, height: 420 })
    const [customRange, setCustomRange] = useState<ViewRange | null>(null)
    const [draggingMarker, setDraggingMarker] = useState<'a1' | 'b1' | 'c1' | null>(null)
    const panStateRef = useRef<{
      pointerId: number
      startX: number
      startY: number
      startRange: ViewRange
    } | null>(null)

    const defaultRange = useMemo(
      () => computeDefaultRange(record, overlays, autoScale, magnifier),
      [record, overlays, autoScale, magnifier],
    )

    // Reset zoom/pan when active trace or scale controls change
    useEffect(() => {
      setCustomRange(null)
    }, [record?.record_id, autoScale, magnifier])

    // Measure responsive plot viewport size
    useEffect(() => {
      const el = viewportRef.current
      if (!el) return
      const update = () => {
        const rect = el.getBoundingClientRect()
        if (rect.width > 120 && rect.height > 120) {
          setSize({ width: Math.round(rect.width), height: Math.round(rect.height) })
        }
      }
      update()
      if (typeof ResizeObserver !== 'undefined') {
        const ro = new ResizeObserver(update)
        ro.observe(el)
        return () => ro.disconnect()
      }
      window.addEventListener('resize', update)
      return () => window.removeEventListener('resize', update)
    }, [])

    const range = customRange ?? defaultRange
    const plotW = Math.max(100, size.width - PAD.left - PAD.right)
    const plotH = Math.max(100, size.height - PAD.top - PAD.bottom)

    const toSvgX = (t: number) => PAD.left + ((t - range.xMin) / (range.xMax - range.xMin)) * plotW
    const toSvgY = (v: number) => PAD.top + ((range.yMax - v) / (range.yMax - range.yMin)) * plotH
    const fromSvgX = (sx: number) => range.xMin + ((sx - PAD.left) / plotW) * (range.xMax - range.xMin)

    const colors = useMemo(() => {
      const dark = theme === 'dark'
      return {
        bg: dark ? '#0B1120' : '#FFFFFF',
        axis: dark ? '#CBD5E1' : '#1E293B',
        grid: dark ? '#334155' : '#CBD5E1',
        gridMinor: dark ? '#1E293B' : '#E2E8F0',
        zero: dark ? '#64748B' : '#94A3B8',
        primary: dark ? '#38BDF8' : '#0038E8',
        badgeBg: dark ? '#0284C7' : '#0038E8',
        badgeFg: '#FFFFFF',
        surface: dark ? '#1E293B' : '#F8FAFC',
        a1: dark ? '#F87171' : '#DC2626',
        b1: dark ? '#38BDF8' : '#0038E8',
        c1: dark ? '#2DD4BF' : '#0D9488',
        ring: dark ? '#0B1120' : '#FFFFFF',
        labelBg: dark ? 'rgba(15,23,42,0.88)' : 'rgba(255,255,255,0.9)',
        overlays: dark ? OVERLAY_COLORS_DARK : OVERLAY_COLORS_LIGHT,
      }
    }, [theme])

    const xTicks = useMemo(() => niceTicks(range.xMin, range.xMax, 6), [range.xMin, range.xMax])
    const yTicks = useMemo(() => niceTicks(range.yMin, range.yMax, 8), [range.yMin, range.yMax])

    const serializeStandaloneSvg = (): string => {
      const svgEl = svgRef.current
      if (!svgEl) return ''
      const clone = svgEl.cloneNode(true) as SVGSVGElement
      clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
      clone.setAttribute('width', String(size.width))
      clone.setAttribute('height', String(size.height))
      return new XMLSerializer().serializeToString(clone)
    }

    useImperativeHandle(ref, () => ({
      resetView: () => setCustomRange(null),
      exportSvg: (fileName: string) => {
        const xml = serializeStandaloneSvg()
        const blob = new Blob([xml], { type: 'image/svg+xml;charset=utf-8' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = fileName
        a.click()
        setTimeout(() => URL.revokeObjectURL(url), 1000)
      },
      exportPng: async (fileName: string) => {
        const xml = serializeStandaloneSvg()
        const scale = 2
        const img = new Image()
        const svgBlob = new Blob([xml], { type: 'image/svg+xml;charset=utf-8' })
        const url = URL.createObjectURL(svgBlob)
        await new Promise<void>((resolve, reject) => {
          img.onload = () => resolve()
          img.onerror = (e) => reject(e)
          img.src = url
        })
        const canvas = document.createElement('canvas')
        canvas.width = size.width * scale
        canvas.height = size.height * scale
        const ctx = canvas.getContext('2d')!
        ctx.fillStyle = colors.bg
        ctx.fillRect(0, 0, canvas.width, canvas.height)
        ctx.scale(scale, scale)
        ctx.drawImage(img, 0, 0)
        URL.revokeObjectURL(url)
        await new Promise<void>((resolve) => {
          canvas.toBlob((blob) => {
            if (blob) {
              const dlUrl = URL.createObjectURL(blob)
              const a = document.createElement('a')
              a.href = dlUrl
              a.download = fileName
              a.click()
              setTimeout(() => URL.revokeObjectURL(dlUrl), 1000)
            }
            resolve()
          }, 'image/png')
        })
      },
    }))

    const getLocalCoords = (clientX: number, clientY: number) => {
      const rect = svgRef.current?.getBoundingClientRect()
      if (!rect) return { x: 0, y: 0 }
      return { x: clientX - rect.left, y: clientY - rect.top }
    }

    const handleMarkerPointerDown = (
      marker: 'a1' | 'b1' | 'c1',
      e: React.PointerEvent<SVGGElement>,
    ) => {
      if (!record) return
      e.stopPropagation()
      e.currentTarget.setPointerCapture(e.pointerId)
      setDraggingMarker(marker)
    }

    const handleMarkerPointerMove = (
      marker: 'a1' | 'b1' | 'c1',
      e: React.PointerEvent<SVGGElement>,
    ) => {
      if (draggingMarker !== marker || !record) return
      e.stopPropagation()
      const { x } = getLocalCoords(e.clientX, e.clientY)
      const timeVal = fromSvgX(x)
      const clampedT = Math.max(
        record.time_ms[0],
        Math.min(record.time_ms[record.time_ms.length - 1], timeVal),
      )
      const newIdx = snapTimeToIndex(record.time_ms, clampedT)
      onMarkerMove(marker, newIdx)
    }

    const handleMarkerPointerUp = (e: React.PointerEvent<SVGGElement>) => {
      if (draggingMarker) {
        e.stopPropagation()
        try {
          e.currentTarget.releasePointerCapture(e.pointerId)
        } catch {
          // ignore
        }
        setDraggingMarker(null)
      }
    }

    const handleCanvasPointerDown = (e: React.PointerEvent<SVGSVGElement>) => {
      if (!record || draggingMarker) return
      e.currentTarget.setPointerCapture(e.pointerId)
      panStateRef.current = {
        pointerId: e.pointerId,
        startX: e.clientX,
        startY: e.clientY,
        startRange: range,
      }
    }

    const handleCanvasPointerMove = (e: React.PointerEvent<SVGSVGElement>) => {
      const pan = panStateRef.current
      if (!pan || draggingMarker) return
      const dxPx = e.clientX - pan.startX
      const dyPx = e.clientY - pan.startY
      const dxData = (-dxPx / plotW) * (pan.startRange.xMax - pan.startRange.xMin)
      const dyData = (dyPx / plotH) * (pan.startRange.yMax - pan.startRange.yMin)
      setCustomRange({
        xMin: pan.startRange.xMin + dxData,
        xMax: pan.startRange.xMax + dxData,
        yMin: pan.startRange.yMin + dyData,
        yMax: pan.startRange.yMax + dyData,
      })
    }

    const handleCanvasPointerUp = (e: React.PointerEvent<SVGSVGElement>) => {
      if (panStateRef.current?.pointerId === e.pointerId) {
        try {
          e.currentTarget.releasePointerCapture(e.pointerId)
        } catch {
          // ignore
        }
        panStateRef.current = null
      }
    }

    const handleWheel = (e: React.WheelEvent<SVGSVGElement>) => {
      if (!record) return
      e.preventDefault()
      const factor = e.deltaY > 0 ? 1.15 : 1 / 1.15
      const { x, y } = getLocalCoords(e.clientX, e.clientY)
      const fx = Math.max(0, Math.min(1, (x - PAD.left) / plotW))
      const fy = Math.max(0, Math.min(1, (y - PAD.top) / plotH))
      const anchorX = range.xMin + fx * (range.xMax - range.xMin)
      const anchorY = range.yMax - fy * (range.yMax - range.yMin)

      const newSpanX = Math.max(5, Math.min(1000, (range.xMax - range.xMin) * factor))
      const newSpanY = Math.max(4, Math.min(5000, (range.yMax - range.yMin) * factor))

      setCustomRange({
        xMin: anchorX - fx * newSpanX,
        xMax: anchorX + (1 - fx) * newSpanX,
        yMax: anchorY + fy * newSpanY,
        yMin: anchorY - (1 - fy) * newSpanY,
      })
    }

    const activeSignal = record ? getActiveSignal(record) : []
    const primaryPath = record ? buildPolylinePath(record.time_ms, activeSignal, toSvgX, toSvgY) : ''
    const shortChannel = record ? record.active_channel.split('(')[0].trim() : ''

    const markersData = record
      ? ([
          { key: 'a1' as const, label: 'A1', idx: record.markers.a1_idx, color: colors.a1, above: false },
          { key: 'b1' as const, label: 'B1', idx: record.markers.b1_idx, color: colors.b1, above: true },
          { key: 'c1' as const, label: 'C1', idx: record.markers.c1_idx, color: colors.c1, above: true },
        ] as const)
      : []

    return (
      <section className="panel-card plot-card" aria-label="ERG Waveform Plot">
        <div className="plot-header">
          <span className={`badge ${record?.eye === 'RIGHT - OD' ? 'badge-od' : 'badge-os'}`}>
            {record?.eye === 'RIGHT - OD' ? tr('plot_eye_header_od') : tr('plot_eye_header_os')}
          </span>
          <span className="badge badge-proto" id="plot-protocol-badge">
            {record ? protocolDisplayName(record.protocol) : '—'}
          </span>
          <span className="plot-filename" title={record?.file_path ?? ''}>
            {record?.file_name ?? ''}
          </span>
          {record && (
            <span className={`badge ${record.markers.is_manual ? 'badge-manual' : 'badge-auto'}`}>
              {record.markers.is_manual ? tr('plot_mode_manual') : tr('plot_mode_auto')}
            </span>
          )}
        </div>

        <div className="plot-viewport" ref={viewportRef}>
          <svg
            ref={svgRef}
            className="plot-svg"
            viewBox={`0 0 ${size.width} ${size.height}`}
            onPointerDown={handleCanvasPointerDown}
            onPointerMove={handleCanvasPointerMove}
            onPointerUp={handleCanvasPointerUp}
            onWheel={handleWheel}
            onDoubleClick={() => setCustomRange(null)}
            style={{ cursor: draggingMarker ? 'ew-resize' : record ? 'grab' : 'default' }}
          >
            <defs>
              <clipPath id="erg-plot-clip">
                <rect x={PAD.left} y={PAD.top} width={plotW} height={plotH} />
              </clipPath>
            </defs>

            {/* Canvas background */}
            <rect x={0} y={0} width={size.width} height={size.height} fill={colors.bg} />

            {/* Gridlines */}
            {showGrid && (
              <g clipPath="url(#erg-plot-clip)">
                {xTicks.map((tx) => {
                  const sx = toSvgX(tx)
                  return (
                    <line
                      key={`gx-${tx}`}
                      x1={sx}
                      y1={PAD.top}
                      x2={sx}
                      y2={PAD.top + plotH}
                      stroke={colors.grid}
                      strokeWidth={1}
                      opacity={0.55}
                    />
                  )
                })}
                {yTicks.map((ty) => {
                  const sy = toSvgY(ty)
                  return (
                    <line
                      key={`gy-${ty}`}
                      x1={PAD.left}
                      y1={sy}
                      x2={PAD.left + plotW}
                      y2={sy}
                      stroke={colors.grid}
                      strokeWidth={1}
                      opacity={0.55}
                    />
                  )
                })}
              </g>
            )}

            {/* Dashed 0 uV baseline */}
            {range.yMin <= 0 && range.yMax >= 0 && (
              <line
                x1={PAD.left}
                y1={toSvgY(0)}
                x2={PAD.left + plotW}
                y2={toSvgY(0)}
                stroke={colors.zero}
                strokeWidth={1.1}
                strokeDasharray="5 4"
                clipPath="url(#erg-plot-clip)"
              />
            )}

            {/* Reference overlays (GNS style) */}
            <g clipPath="url(#erg-plot-clip)">
              {overlays.map((ov, idx) => {
                const ovSig = getActiveSignal(ov)
                const ovColor = colors.overlays[idx % colors.overlays.length]
                const ovPath = buildPolylinePath(ov.time_ms, ovSig, toSvgX, toSvgY)
                const tailX = toSvgX(ov.time_ms[ov.time_ms.length - 1])
                const tailY = toSvgY(ovSig[ovSig.length - 1])
                const ovTag =
                  ov.metadata.mouse_id_name.trim() || protocolShortLabel(ov.protocol)
                return (
                  <g key={ov.record_id}>
                    <path d={ovPath} fill="none" stroke={ovColor} strokeWidth={1.45} opacity={0.85} />
                    <text
                      x={Math.min(PAD.left + plotW - 6, tailX - 4)}
                      y={tailY - 6}
                      textAnchor="end"
                      fill={ovColor}
                      fontSize={10}
                      fontWeight={600}
                      fontFamily="Inter, sans-serif"
                    >
                      {`${tr('plot_reference_tag')}: ${ovTag}`}
                    </text>
                  </g>
                )
              })}

              {/* Primary raw ERG waveform */}
              {record && (
                <path
                  d={primaryPath}
                  fill="none"
                  stroke={colors.primary}
                  strokeWidth={2.2}
                  strokeLinejoin="round"
                  strokeLinecap="round"
                />
              )}

              {/* Channel tag pill (Retimax AV1 badge) */}
              {record && activeSignal.length > 0 && (
                <g
                  transform={`translate(${Math.min(
                    PAD.left + plotW - 36,
                    toSvgX(record.time_ms[record.time_ms.length - 1]) - 34,
                  )}, ${Math.max(
                    PAD.top + 10,
                    Math.min(
                      PAD.top + plotH - 18,
                      toSvgY(activeSignal[activeSignal.length - 1]) - 9,
                    ),
                  )})`}
                >
                  <rect width={32} height={17} rx={3} fill={colors.badgeBg} />
                  <text
                    x={16}
                    y={12}
                    textAnchor="middle"
                    fill={colors.badgeFg}
                    fontSize={10}
                    fontWeight={700}
                    fontFamily="Inter, sans-serif"
                  >
                    {shortChannel}
                  </text>
                </g>
              )}

              {/* Draggable A1, B1, C1 markers */}
              {record &&
                markersData.map((mk) => {
                  const safeIdx = Math.max(0, Math.min(mk.idx, record.time_ms.length - 1))
                  const sx = toSvgX(record.time_ms[safeIdx])
                  const sy = toSvgY(activeSignal[safeIdx])
                  const labelY = mk.above
                    ? Math.max(PAD.top + 16, sy - 14)
                    : Math.min(PAD.top + plotH - 8, sy + 22)

                  return (
                    <g
                      key={mk.key}
                      data-testid={`marker-${mk.key}`}
                      style={{ cursor: 'ew-resize' }}
                      onPointerDown={(e) => handleMarkerPointerDown(mk.key, e)}
                      onPointerMove={(e) => handleMarkerPointerMove(mk.key, e)}
                      onPointerUp={handleMarkerPointerUp}
                    >
                      {/* Wide invisible hit column for effortless grab */}
                      <rect
                        x={sx - 10}
                        y={PAD.top}
                        width={20}
                        height={plotH}
                        fill="transparent"
                      />
                      {/* Vertical dotted guide line */}
                      <line
                        x1={sx}
                        y1={PAD.top}
                        x2={sx}
                        y2={PAD.top + plotH}
                        stroke={mk.color}
                        strokeWidth={draggingMarker === mk.key ? 2 : 1.2}
                        strokeDasharray="3 3"
                        opacity={draggingMarker === mk.key ? 0.95 : 0.55}
                      />
                      {/* Sample-snapped circular dot */}
                      <circle
                        cx={sx}
                        cy={sy}
                        r={draggingMarker === mk.key ? 7 : 5.5}
                        fill={mk.color}
                        stroke={colors.ring}
                        strokeWidth={2}
                      />
                      {/* Crisp label tag */}
                      <rect
                        x={sx - 12}
                        y={labelY - 11}
                        width={24}
                        height={15}
                        rx={3}
                        fill={colors.labelBg}
                      />
                      <text
                        x={sx}
                        y={labelY}
                        textAnchor="middle"
                        fill={mk.color}
                        fontSize={11}
                        fontWeight={800}
                        fontFamily="Inter, sans-serif"
                      >
                        {mk.label}
                      </text>
                    </g>
                  )
                })}
            </g>

            {/* Plot frame border */}
            <rect
              x={PAD.left}
              y={PAD.top}
              width={plotW}
              height={plotH}
              fill="none"
              stroke={colors.axis}
              strokeWidth={1.1}
            />

            {/* X axis ticks & label */}
            {xTicks.map((tx) => {
              const sx = toSvgX(tx)
              return (
                <g key={`xt-${tx}`}>
                  <line
                    x1={sx}
                    y1={PAD.top + plotH}
                    x2={sx}
                    y2={PAD.top + plotH + 5}
                    stroke={colors.axis}
                    strokeWidth={1}
                  />
                  <text
                    x={sx}
                    y={PAD.top + plotH + 18}
                    textAnchor="middle"
                    fill={colors.axis}
                    fontSize={11}
                    fontFamily="JetBrains Mono, monospace"
                  >
                    {tx}
                  </text>
                </g>
              )
            })}
            <text
              x={PAD.left + plotW / 2}
              y={size.height - 8}
              textAnchor="middle"
              fill={colors.axis}
              fontSize={12}
              fontWeight={600}
              fontFamily="Inter, sans-serif"
            >
              {tr('plot_axis_time')}
            </text>

            {/* Y axis ticks & label */}
            {yTicks.map((ty) => {
              const sy = toSvgY(ty)
              return (
                <g key={`yt-${ty}`}>
                  <line
                    x1={PAD.left - 5}
                    y1={sy}
                    x2={PAD.left}
                    y2={sy}
                    stroke={colors.axis}
                    strokeWidth={1}
                  />
                  <text
                    x={PAD.left - 8}
                    y={sy + 4}
                    textAnchor="end"
                    fill={colors.axis}
                    fontSize={11}
                    fontFamily="JetBrains Mono, monospace"
                  >
                    {ty}
                  </text>
                </g>
              )
            })}
            <text
              x={16}
              y={PAD.top + plotH / 2}
              textAnchor="middle"
              fill={colors.axis}
              fontSize={12}
              fontWeight={600}
              fontFamily="Inter, sans-serif"
              transform={`rotate(-90, 16, ${PAD.top + plotH / 2})`}
            >
              {tr('plot_axis_amplitude')}
            </text>
          </svg>

          {!record && (
            <div className="plot-empty-overlay">
              <p className="plot-empty-title">{tr('plot_empty_title')}</p>
              <p className="plot-empty-sub">{tr('plot_empty_subtitle')}</p>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  type="button"
                  id="empty-open-csv-btn"
                  className="btn btn-primary"
                  onClick={onOpenCsv}
                >
                  {tr('btn_open_csv')}
                </button>
                <button
                  type="button"
                  id="empty-load-examples-btn"
                  className="btn"
                  onClick={onLoadExamples}
                >
                  {tr('btn_load_examples')}
                </button>
              </div>
            </div>
          )}
        </div>

        <p className="muted-hint">{tr('plot_drag_hint')}</p>
      </section>
    )
  },
)

WaveformPlot.displayName = 'WaveformPlot'
