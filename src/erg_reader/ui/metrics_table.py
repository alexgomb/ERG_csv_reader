"""Retimax-style ERG amplitude & peak time table plus 30 Hz Flicker analysis bar."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from erg_reader.analysis import compute_flicker_metrics, compute_peak_metrics
from erg_reader.i18n import Translator
from erg_reader.models import ERGProtocol, ERGSessionRecord, EyeSide
from erg_reader.themes import get_plot_palette


class MetricsTablePanel(QFrame):
    """Displays Retimax-format A1/B1/C1/A1-B1/B1-C1 table and optional Flicker metrics."""

    def __init__(self, translator: Translator, theme: str = "light", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("TableCard")
        self._tr = translator
        self._theme = theme
        self._record: ERGSessionRecord | None = None
        self._build_ui()
        self.apply_theme(theme)
        self.retranslate_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        # Retimax-exact 2x6 summary table
        self.table = QTableWidget(2, 6)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.verticalHeader().setVisible(False)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        for col in range(1, 6):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)

        self.table.setRowHeight(0, 32)
        self.table.setRowHeight(1, 32)
        self.table.setFixedHeight(98)

        for row in range(2):
            for col in range(6):
                item = QTableWidgetItem("—")
                align = Qt.AlignmentFlag.AlignVCenter | (
                    Qt.AlignmentFlag.AlignLeft if col == 0 else Qt.AlignmentFlag.AlignCenter
                )
                item.setTextAlignment(align)
                self.table.setItem(row, col, item)

        layout.addWidget(self.table)

        # Dedicated 30 Hz Flicker metrics bar (visible only for Flicker recordings)
        self.flicker_card = QFrame()
        self.flicker_card.setObjectName("FlickerCard")
        fl_layout = QVBoxLayout(self.flicker_card)
        fl_layout.setContentsMargins(10, 6, 10, 8)
        fl_layout.setSpacing(4)

        self.flicker_title = QLabel("")
        title_font = QFont()
        title_font.setBold(True)
        self.flicker_title.setFont(title_font)
        fl_layout.addWidget(self.flicker_title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(2)

        self._flicker_label_widgets: dict[str, QLabel] = {}
        self._flicker_value_widgets: dict[str, QLabel] = {}
        keys = (
            "flicker_mean_pt",
            "flicker_sd_pt",
            "flicker_fft_amp",
            "flicker_fft_pp",
            "flicker_dom_freq",
            "flicker_cycles",
        )
        val_font = QFont()
        val_font.setBold(True)
        val_font.setPointSize(10)

        for idx, key in enumerate(keys):
            lbl = QLabel("")
            lbl.setObjectName("MutedLabel")
            val = QLabel("—")
            val.setFont(val_font)
            grid.addWidget(lbl, 0, idx)
            grid.addWidget(val, 1, idx)
            self._flicker_label_widgets[key] = lbl
            self._flicker_value_widgets[key] = val

        fl_layout.addLayout(grid)
        self.flicker_card.setVisible(False)
        layout.addWidget(self.flicker_card)

    def apply_theme(self, theme: str) -> None:
        self._theme = theme
        self._style_cells()

    def retranslate_ui(self) -> None:
        eye_text = (
            self._tr.tr("plot_eye_header_od")
            if self._record and self._record.eye == EyeSide.RIGHT_OD
            else self._tr.tr("plot_eye_header_os")
        )
        self.table.setHorizontalHeaderLabels([eye_text, "A1", "B1", "C1", "A1-B1", "B1-C1"])
        self.table.item(0, 0).setText(self._tr.tr("table_amplitude"))
        self.table.item(1, 0).setText(self._tr.tr("table_peak_time"))

        self.flicker_title.setText(self._tr.tr("flicker_panel_title"))
        for key, lbl in self._flicker_label_widgets.items():
            lbl.setText(self._tr.tr(key))

    def set_record(self, record: ERGSessionRecord | None) -> None:
        self._record = record
        self.retranslate_ui()
        if record is None:
            for row in range(2):
                for col in range(1, 6):
                    self.table.item(row, col).setText("—")
            self.flicker_card.setVisible(False)
            self._style_cells()
            return

        m = compute_peak_metrics(record.time_ms, record.active_signal, record.markers)
        amp_values = [m.a1_uv, m.b1_uv, m.c1_uv, m.a1_b1_uv, m.b1_c1_uv]
        time_values = [m.a1_ms, m.b1_ms, m.c1_ms, m.a1_b1_ms, m.b1_c1_ms]

        for col_offset, val in enumerate(amp_values, start=1):
            self.table.item(0, col_offset).setText(f"{val:.2f}")
        for col_offset, val in enumerate(time_values, start=1):
            self.table.item(1, col_offset).setText(f"{val:.2f}")

        if record.protocol == ERGProtocol.LIGHT_ADAPTED_3_FLICKER:
            fl = compute_flicker_metrics(record.time_ms, record.active_signal)
            self._flicker_value_widgets["flicker_mean_pt"].setText(f"{fl.mean_peak_to_trough_uv:.2f} µV")
            self._flicker_value_widgets["flicker_sd_pt"].setText(f"± {fl.std_peak_to_trough_uv:.2f} µV")
            self._flicker_value_widgets["flicker_fft_amp"].setText(f"{fl.fft_fundamental_amp_uv:.2f} µV")
            self._flicker_value_widgets["flicker_fft_pp"].setText(f"{fl.fft_peak_to_peak_uv:.2f} µV")
            self._flicker_value_widgets["flicker_dom_freq"].setText(f"{fl.dominant_freq_hz:.2f} Hz")
            self._flicker_value_widgets["flicker_cycles"].setText(str(fl.cycles_detected))
            self.flicker_card.setVisible(True)
        else:
            self.flicker_card.setVisible(False)

        self._style_cells()

    def _style_cells(self) -> None:
        palette = get_plot_palette(self._theme)
        normal_font = QFont()
        bold_font = QFont()
        bold_font.setBold(True)

        for row in range(2):
            for col in range(6):
                item = self.table.item(row, col)
                if col == 0:
                    item.setFont(bold_font)
                    item.setBackground(QBrush(QColor(palette.surface)))
                    item.setForeground(QBrush(QColor(palette.text_primary)))
                elif row == 0 and col == 4:
                    # Iconic Retimax yellow highlight for A1-B1 amplitude
                    item.setFont(bold_font)
                    item.setBackground(QBrush(QColor(palette.highlight_bg)))
                    item.setForeground(QBrush(QColor(palette.highlight_fg)))
                else:
                    item.setFont(normal_font)
                    item.setBackground(QBrush(QColor(palette.background)))
                    item.setForeground(QBrush(QColor(palette.text_primary)))
