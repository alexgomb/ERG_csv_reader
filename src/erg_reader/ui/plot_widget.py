"""Interactive PyQtGraph waveform plot with Retimax styling and draggable A1/B1/C1 markers."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np
import pyqtgraph as pg
import pyqtgraph.exporters as pg_exporters
from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtSvg import QSvgGenerator
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from erg_reader.analysis import snap_time_to_index
from erg_reader.i18n import Translator
from erg_reader.models import ERGSessionRecord, EyeSide
from erg_reader.themes import PlotPalette, get_plot_palette


class ERGPlotWidget(QFrame):
    """Left-eye focused Retimax-style interactive ERG waveform canvas."""

    markerMoved = Signal(str, int)  # (marker_key: 'a1'|'b1'|'c1', sample_index)

    def __init__(self, translator: Translator, theme: str = "light", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("PlotCard")
        self._tr = translator
        self._theme = theme
        self._palette: PlotPalette = get_plot_palette(theme)

        self._record: ERGSessionRecord | None = None
        self._overlays: list[ERGSessionRecord] = []
        self._auto_scale: bool = False
        self._magnifier: float = 1.0
        self._show_grid: bool = True
        self._updating_markers: bool = False

        self._build_ui()
        self.apply_theme(theme)
        self.retranslate_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(6)

        # Header bar above plot (eye badge, protocol badge, filename, marker status)
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        self.eye_badge = QLabel("LEFT - OS")
        self.eye_badge.setObjectName("EyeBadgeOS")
        header_row.addWidget(self.eye_badge)

        self.protocol_badge = QLabel("—")
        self.protocol_badge.setObjectName("ProtocolBadge")
        header_row.addWidget(self.protocol_badge)

        self.file_label = QLabel("")
        font = QFont()
        font.setBold(True)
        self.file_label.setFont(font)
        header_row.addWidget(self.file_label, stretch=1)

        self.marker_mode_badge = QLabel("")
        self.marker_mode_badge.setObjectName("MarkerModeAuto")
        self.marker_mode_badge.setVisible(False)
        header_row.addWidget(self.marker_mode_badge)

        root.addLayout(header_row)

        # PyQtGraph canvas
        pg.setConfigOptions(antialias=True)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setMinimumHeight(320)
        self.plot_item = self.plot_widget.getPlotItem()
        self.plot_item.setMenuEnabled(False)
        self.plot_item.showButtons()
        self.plot_item.showAxis("top", True)
        self.plot_item.showAxis("right", True)
        self.plot_item.getAxis("top").setStyle(showValues=False, tickLength=0)
        self.plot_item.getAxis("right").setStyle(showValues=False, tickLength=0)

        # Zero-voltage horizontal reference line
        self.zero_line = pg.InfiniteLine(pos=0.0, angle=0, movable=False)
        self.plot_item.addItem(self.zero_line, ignoreBounds=True)

        # Primary waveform curve & channel tag pill (like Retimax's AV1 badge)
        self.primary_curve = self.plot_item.plot([], [], name="Primary")
        self.channel_badge_item = pg.TextItem(text="", anchor=(1.0, 0.5))
        self.channel_badge_item.setVisible(False)
        self.plot_item.addItem(self.channel_badge_item)

        # Reference overlay items managed dynamically
        self._overlay_items: list[pg.GraphicsObject] = []

        # Draggable A1, B1, C1 markers (vertical guide line + curve-snapped dot + text tag)
        self._marker_lines: dict[str, pg.InfiniteLine] = {}
        self._marker_dots: dict[str, pg.ScatterPlotItem] = {}
        self._marker_labels: dict[str, pg.TextItem] = {}

        for key, label_text in (("a1", "A1"), ("b1", "B1"), ("c1", "C1")):
            line = pg.InfiniteLine(pos=0.0, angle=90, movable=True)
            line.setVisible(False)
            line.sigDragged.connect(lambda l_item, k=key: self._on_line_dragged(k, l_item))
            self.plot_item.addItem(line, ignoreBounds=True)

            dot = pg.ScatterPlotItem(size=11, pxMode=True)
            dot.setZValue(20)
            dot.setVisible(False)
            self.plot_item.addItem(dot)

            anchor = (0.5, -0.35) if key == "a1" else (0.5, 1.35)
            txt = pg.TextItem(text=label_text, anchor=anchor)
            txt.setZValue(25)
            txt.setVisible(False)
            self.plot_item.addItem(txt)

            self._marker_lines[key] = line
            self._marker_dots[key] = dot
            self._marker_labels[key] = txt

        # Empty-state prompt centered inside canvas
        self.empty_text_item = pg.TextItem(text="", anchor=(0.5, 0.5))
        self.empty_text_item.setPos(125.0, 0.0)
        self.plot_item.addItem(self.empty_text_item)

        root.addWidget(self.plot_widget, stretch=1)

        # Subtle bottom hint line
        self.drag_hint_label = QLabel("")
        self.drag_hint_label.setObjectName("MutedLabel")
        root.addWidget(self.drag_hint_label)

        self._apply_default_empty_view()

    def apply_theme(self, theme: str) -> None:
        self._theme = theme
        self._palette = get_plot_palette(theme)
        p = self._palette

        self.plot_widget.setBackground(p.background)
        axis_pen = pg.mkPen(color=p.axis, width=1.1)
        for side in ("left", "bottom", "top", "right"):
            ax = self.plot_item.getAxis(side)
            ax.setPen(axis_pen)
            ax.setTextPen(pg.mkPen(color=p.axis))

        self.plot_item.showGrid(x=self._show_grid, y=self._show_grid, alpha=0.35 if theme == "light" else 0.45)
        self.zero_line.setPen(pg.mkPen(color=p.zero_line, width=1.0, style=Qt.PenStyle.DashLine))
        self.primary_curve.setPen(pg.mkPen(color=p.primary_trace, width=2.2))

        marker_colors = {"a1": p.marker_a1, "b1": p.marker_b1, "c1": p.marker_c1}
        bold_font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        for key, color in marker_colors.items():
            c_guide = QColor(color)
            c_guide.setAlpha(115)
            c_hover = QColor(color)
            c_hover.setAlpha(235)
            self._marker_lines[key].setPen(pg.mkPen(color=c_guide, width=1.2, style=Qt.PenStyle.DotLine))
            self._marker_lines[key].setHoverPen(pg.mkPen(color=c_hover, width=2.2))

            label = self._marker_labels[key]
            label.setColor(color)
            label.setFont(bold_font)
            label.fill = pg.mkBrush(p.marker_label_bg)

        self.empty_text_item.setColor(p.text_muted)
        hint_font = QFont("Segoe UI", 11)
        self.empty_text_item.setFont(hint_font)

        # Re-render active record and overlays with updated colors
        self._redraw_all(preserve_range=self._record is not None)

    def retranslate_ui(self) -> None:
        self.plot_item.setLabel("bottom", self._tr.tr("plot_axis_time"), units="ms")
        self.plot_item.setLabel("left", self._tr.tr("plot_axis_amplitude"), units="µV")
        self.drag_hint_label.setText(self._tr.tr("plot_drag_hint"))
        self.empty_text_item.setText(self._tr.tr("plot_empty_message"))
        self._update_header_badges()

    def set_data(
        self,
        record: ERGSessionRecord | None,
        overlays: Sequence[ERGSessionRecord] = (),
        preserve_range: bool = False,
    ) -> None:
        self._record = record
        self._overlays = [ov for ov in overlays if record is None or ov.record_id != record.record_id]
        self._redraw_all(preserve_range=preserve_range)

    def set_show_grid(self, enabled: bool) -> None:
        self._show_grid = enabled
        self.plot_item.showGrid(
            x=enabled,
            y=enabled,
            alpha=0.35 if self._theme == "light" else 0.45,
        )

    def set_auto_scale(self, enabled: bool) -> None:
        self._auto_scale = enabled
        self.apply_scale()

    def set_magnifier(self, magnifier: float) -> None:
        self._magnifier = max(0.1, min(50.0, float(magnifier)))
        self._auto_scale = False
        self.apply_scale()

    def reset_view(self) -> None:
        self.apply_scale()

    def apply_scale(self) -> None:
        if self._record is None:
            self._apply_default_empty_view()
            return

        t = self._record.time_ms
        y = self._record.active_signal
        x_min = float(t[0])
        x_max = float(t[-1])
        # Retimax uses 0-250 ms for standard flash protocols and ~0-167 ms for flicker
        display_x_max = 250.0 if x_max >= 200.0 else max(x_max * 1.02, 10.0)
        self.plot_item.setXRange(x_min, display_x_max, padding=0.02)

        if self._auto_scale:
            all_y = [y] + [ov.active_signal for ov in self._overlays]
            y_min = min(float(np.min(arr)) for arr in all_y)
            y_max = max(float(np.max(arr)) for arr in all_y)
            span = max(y_max - y_min, 10.0)
            pad = 0.16 * span
            self.plot_item.setYRange(y_min - pad, y_max + pad, padding=0.0)
        else:
            half_span = 250.0 / self._magnifier
            self.plot_item.setYRange(-half_span, half_span, padding=0.0)

    def _apply_default_empty_view(self) -> None:
        self.plot_item.setXRange(0.0, 250.0, padding=0.02)
        self.plot_item.setYRange(-250.0, 250.0, padding=0.0)
        self.empty_text_item.setPos(125.0, 0.0)

    def _clear_overlays(self) -> None:
        for item in self._overlay_items:
            self.plot_item.removeItem(item)
        self._overlay_items.clear()

    def _redraw_all(self, preserve_range: bool = False) -> None:
        self._clear_overlays()
        self._update_header_badges()

        if self._record is None:
            self.primary_curve.setData([], [])
            self.channel_badge_item.setVisible(False)
            self.empty_text_item.setVisible(True)
            for key in ("a1", "b1", "c1"):
                self._marker_lines[key].setVisible(False)
                self._marker_dots[key].setVisible(False)
                self._marker_labels[key].setVisible(False)
            self._apply_default_empty_view()
            return

        self.empty_text_item.setVisible(False)
        p = self._palette

        # Draw reference overlays underneath primary curve (GNS-style)
        for idx, ov in enumerate(self._overlays):
            color = p.overlay_traces[idx % len(p.overlay_traces)]
            ov_curve = self.plot_item.plot(
                ov.time_ms,
                ov.active_signal,
                pen=pg.mkPen(color=color, width=1.4),
            )
            ov_curve.setZValue(5)
            self._overlay_items.append(ov_curve)

            # Compact reference label at the right tail of the overlay trace
            ov_tag = ov.metadata.mouse_id_name.strip() or ov.protocol.short_label
            tag_html = (
                f"<div style='background:{p.surface};color:{color};"
                f"border:1px solid {color};padding:1px 4px;font-size:9px;font-weight:600;'>"
                f"{self._tr.tr('plot_reference_tag')}: {ov_tag}</div>"
            )
            ov_label = pg.TextItem(html=tag_html, anchor=(1.0, 0.5))
            ov_label.setPos(float(ov.time_ms[-1]), float(ov.active_signal[-1]))
            ov_label.setZValue(6)
            self.plot_item.addItem(ov_label)
            self._overlay_items.append(ov_label)

        # Primary waveform
        t = self._record.time_ms
        y = self._record.active_signal
        self.primary_curve.setData(t, y)
        self.primary_curve.setZValue(15)

        # Channel pill badge near right tail (like Retimax's AV1 tag)
        short_ch = self._record.active_channel.split("(")[0].strip()
        badge_html = (
            f"<div style='background:{p.primary_badge_bg};color:{p.primary_badge_fg};"
            f"padding:1px 5px;font-size:10px;font-weight:700;'>{short_ch}</div>"
        )
        self.channel_badge_item.setHtml(badge_html)
        self.channel_badge_item.setPos(float(t[-1]), float(y[-1]))
        self.channel_badge_item.setZValue(18)
        self.channel_badge_item.setVisible(True)

        self.refresh_markers()
        if not preserve_range:
            self.apply_scale()

    def refresh_markers(self) -> None:
        if self._record is None:
            return
        self._updating_markers = True
        try:
            t = self._record.time_ms
            y = self._record.active_signal
            m = self._record.markers
            p = self._palette
            bounds = (float(t[0]), float(t[-1]))

            mapping = {
                "a1": (m.a1_idx, p.marker_a1, "A1"),
                "b1": (m.b1_idx, p.marker_b1, "B1"),
                "c1": (m.c1_idx, p.marker_c1, "C1"),
            }
            for key, (idx, color, text) in mapping.items():
                safe_idx = max(0, min(idx, len(t) - 1))
                tx = float(t[safe_idx])
                ty = float(y[safe_idx])

                line = self._marker_lines[key]
                line.setBounds(bounds)
                line.setValue(tx)
                line.setVisible(True)

                dot = self._marker_dots[key]
                dot.setData(
                    x=[tx],
                    y=[ty],
                    brush=pg.mkBrush(color),
                    pen=pg.mkPen(p.marker_border, width=2.0),
                    symbol="o",
                    size=11,
                )
                dot.setVisible(True)

                label = self._marker_labels[key]
                label.setText(text)
                label.setPos(tx, ty)
                label.setVisible(True)
        finally:
            self._updating_markers = False

        self._update_header_badges()

    def _on_line_dragged(self, marker_key: str, line_item: pg.InfiniteLine) -> None:
        if self._updating_markers or self._record is None:
            return
        t = self._record.time_ms
        idx = snap_time_to_index(t, float(line_item.value()))

        if marker_key == "a1":
            self._record.markers.a1_idx = idx
        elif marker_key == "b1":
            self._record.markers.b1_idx = idx
        elif marker_key == "c1":
            self._record.markers.c1_idx = idx
        self._record.markers.is_manual = True

        self.refresh_markers()
        self.markerMoved.emit(marker_key, idx)

    def _update_header_badges(self) -> None:
        if self._record is None:
            self.eye_badge.setText(self._tr.tr("plot_eye_header_os"))
            self.eye_badge.setObjectName("EyeBadgeOS")
            self.protocol_badge.setText("—")
            self.file_label.setText("")
            self.marker_mode_badge.setVisible(False)
        else:
            is_od = self._record.eye == EyeSide.RIGHT_OD
            self.eye_badge.setText(
                self._tr.tr("plot_eye_header_od") if is_od else self._tr.tr("plot_eye_header_os")
            )
            self.eye_badge.setObjectName("EyeBadgeOD" if is_od else "EyeBadgeOS")
            self.protocol_badge.setText(self._record.protocol.display_name)
            self.file_label.setText(self._record.file_name)

            is_manual = self._record.markers.is_manual
            self.marker_mode_badge.setText(
                self._tr.tr("plot_mode_manual") if is_manual else self._tr.tr("plot_mode_auto")
            )
            self.marker_mode_badge.setObjectName("MarkerModeManual" if is_manual else "MarkerModeAuto")
            self.marker_mode_badge.setVisible(True)

        # Force QSS refresh after dynamic objectName changes
        for widget in (self.eye_badge, self.marker_mode_badge):
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    def export_plot(self, output_path: str | Path) -> Path:
        """Export the waveform plot cleanly to high-resolution PNG or vector SVG."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        suffix = out.suffix.lower()
        if suffix == ".svg":
            rect = self.plot_widget.rect()
            width = max(rect.width(), 960)
            height = max(rect.height(), 560)
            generator = QSvgGenerator()
            generator.setFileName(str(out))
            generator.setSize(QSize(width, height))
            generator.setViewBox(QRect(0, 0, width, height))
            generator.setTitle("nBio ERG-Trace Waveform")
            painter = QPainter(generator)
            try:
                self.plot_widget.render(painter)
            finally:
                painter.end()
        else:
            exporter = pg_exporters.ImageExporter(self.plot_item)
            exporter.parameters()["width"] = 1800
            exporter.export(str(out))
        return out
