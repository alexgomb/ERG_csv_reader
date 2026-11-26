"""Retimax-inspired right control strip: file loading, pure scale/magnifier controls, markers, export, theme & language."""

from __future__ import annotations

from typing import Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from erg_reader.i18n import Translator


class ControlsPanel(QFrame):
    """Right vertical toolbar mirroring Retimax's ergonomic control column."""

    openCsvRequested = Signal()
    openFolderRequested = Signal()
    loadExamplesRequested = Signal()
    channelChanged = Signal(str)
    magnifierChanged = Signal(float)
    autoScaleToggled = Signal(bool)
    retimaxScaleRequested = Signal()
    resetViewRequested = Signal()
    gridToggled = Signal(bool)
    resetMarkersRequested = Signal()
    settingsRequested = Signal()
    copyTableRequested = Signal()
    exportCsvRequested = Signal()
    exportXlsxRequested = Signal()
    exportPlotRequested = Signal()
    languageChanged = Signal(str)
    themeChanged = Signal(str)
    aboutRequested = Signal()

    def __init__(self, translator: Translator, theme: str = "light", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("ControlsPanel")
        self.setFixedWidth(214)

        self._tr = translator
        self._theme = theme
        self._updating_controls = False

        self._build_ui()
        self.set_language_state(translator.language)
        self.set_theme_state(theme)
        self.retranslate_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("ControlsScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        container.setObjectName("ControlsContainer")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(7)

        # 1. File loading controls
        self.files_group = QGroupBox()
        files_v = QVBoxLayout(self.files_group)
        files_v.setContentsMargins(7, 10, 7, 7)
        files_v.setSpacing(5)

        self.open_csv_btn = QPushButton()
        self.open_csv_btn.setObjectName("PrimaryButton")
        self.open_csv_btn.clicked.connect(self.openCsvRequested.emit)
        files_v.addWidget(self.open_csv_btn)

        files_row = QHBoxLayout()
        files_row.setSpacing(4)
        self.open_folder_btn = QPushButton()
        self.open_folder_btn.clicked.connect(self.openFolderRequested.emit)
        self.examples_btn = QPushButton()
        self.examples_btn.clicked.connect(self.loadExamplesRequested.emit)
        files_row.addWidget(self.open_folder_btn)
        files_row.addWidget(self.examples_btn)
        files_v.addLayout(files_row)
        layout.addWidget(self.files_group)

        # 2. Pure Display & Scale controls (no signal modification)
        self.display_group = QGroupBox()
        disp_v = QVBoxLayout(self.display_group)
        disp_v.setContentsMargins(7, 10, 7, 7)
        disp_v.setSpacing(5)

        self.channel_label = QLabel()
        self.channel_label.setObjectName("MutedLabel")
        self.channel_combo = QComboBox()
        self.channel_combo.currentTextChanged.connect(self._on_channel_changed)
        disp_v.addWidget(self.channel_label)
        disp_v.addWidget(self.channel_combo)

        self.magnifier_label = QLabel()
        self.magnifier_label.setObjectName("MutedLabel")
        disp_v.addWidget(self.magnifier_label)

        mag_row = QHBoxLayout()
        mag_row.setSpacing(4)
        self.scale_down_btn = QPushButton("▼")
        self.scale_down_btn.setFixedWidth(28)
        self.scale_down_btn.clicked.connect(lambda: self._step_magnifier(0.5))

        self.magnifier_spin = QDoubleSpinBox()
        self.magnifier_spin.setRange(0.25, 25.0)
        self.magnifier_spin.setSingleStep(0.25)
        self.magnifier_spin.setDecimals(2)
        self.magnifier_spin.setSuffix("x")
        self.magnifier_spin.setValue(1.0)
        self.magnifier_spin.valueChanged.connect(self._on_magnifier_changed)

        self.scale_up_btn = QPushButton("▲")
        self.scale_up_btn.setFixedWidth(28)
        self.scale_up_btn.clicked.connect(lambda: self._step_magnifier(2.0))

        mag_row.addWidget(self.scale_down_btn)
        mag_row.addWidget(self.magnifier_spin, stretch=1)
        mag_row.addWidget(self.scale_up_btn)
        disp_v.addLayout(mag_row)

        scale_row = QHBoxLayout()
        scale_row.setSpacing(4)
        self.autoscale_btn = QPushButton()
        self.autoscale_btn.setCheckable(True)
        self.autoscale_btn.toggled.connect(self._on_autoscale_toggled)

        self.retimax_250_btn = QPushButton()
        self.retimax_250_btn.clicked.connect(self._on_retimax_250_clicked)

        scale_row.addWidget(self.autoscale_btn)
        scale_row.addWidget(self.retimax_250_btn)
        disp_v.addLayout(scale_row)

        view_row = QHBoxLayout()
        view_row.setSpacing(6)
        self.reset_view_btn = QPushButton()
        self.reset_view_btn.clicked.connect(self.resetViewRequested.emit)
        self.grid_checkbox = QCheckBox()
        self.grid_checkbox.setChecked(True)
        self.grid_checkbox.toggled.connect(self.gridToggled.emit)
        view_row.addWidget(self.reset_view_btn, stretch=1)
        view_row.addWidget(self.grid_checkbox)
        disp_v.addLayout(view_row)

        layout.addWidget(self.display_group)

        # 3. Markers & Settings
        self.markers_group = QGroupBox()
        mk_row = QHBoxLayout(self.markers_group)
        mk_row.setContentsMargins(7, 10, 7, 7)
        mk_row.setSpacing(4)

        self.reset_markers_btn = QPushButton()
        self.reset_markers_btn.clicked.connect(self.resetMarkersRequested.emit)
        self.settings_btn = QPushButton()
        self.settings_btn.clicked.connect(self.settingsRequested.emit)
        mk_row.addWidget(self.reset_markers_btn)
        mk_row.addWidget(self.settings_btn)
        layout.addWidget(self.markers_group)

        # 4. Export actions (clean 2x2 grid)
        self.export_group = QGroupBox()
        exp_grid = QGridLayout(self.export_group)
        exp_grid.setContentsMargins(7, 10, 7, 7)
        exp_grid.setSpacing(4)

        self.copy_table_btn = QPushButton()
        self.copy_table_btn.clicked.connect(self.copyTableRequested.emit)
        self.export_csv_btn = QPushButton()
        self.export_csv_btn.clicked.connect(self.exportCsvRequested.emit)
        self.export_xlsx_btn = QPushButton()
        self.export_xlsx_btn.clicked.connect(self.exportXlsxRequested.emit)
        self.export_plot_btn = QPushButton()
        self.export_plot_btn.clicked.connect(self.exportPlotRequested.emit)

        exp_grid.addWidget(self.copy_table_btn, 0, 0)
        exp_grid.addWidget(self.export_plot_btn, 0, 1)
        exp_grid.addWidget(self.export_csv_btn, 1, 0)
        exp_grid.addWidget(self.export_xlsx_btn, 1, 1)
        layout.addWidget(self.export_group)

        # 5. Appearance (Language EN/ES + Theme Light/Dark)
        self.appearance_group = QGroupBox()
        app_v = QVBoxLayout(self.appearance_group)
        app_v.setContentsMargins(7, 10, 7, 7)
        app_v.setSpacing(5)

        self.lang_label = QLabel()
        self.lang_label.setObjectName("MutedLabel")
        app_v.addWidget(self.lang_label)

        lang_row = QHBoxLayout()
        lang_row.setSpacing(4)
        self.lang_en_btn = QPushButton("EN")
        self.lang_en_btn.setCheckable(True)
        self.lang_en_btn.clicked.connect(lambda: self._emit_language("en"))
        self.lang_es_btn = QPushButton("ES")
        self.lang_es_btn.setCheckable(True)
        self.lang_es_btn.clicked.connect(lambda: self._emit_language("es"))
        lang_row.addWidget(self.lang_en_btn)
        lang_row.addWidget(self.lang_es_btn)
        app_v.addLayout(lang_row)

        self.theme_label = QLabel()
        self.theme_label.setObjectName("MutedLabel")
        app_v.addWidget(self.theme_label)

        theme_row = QHBoxLayout()
        theme_row.setSpacing(4)
        self.theme_light_btn = QPushButton()
        self.theme_light_btn.setCheckable(True)
        self.theme_light_btn.clicked.connect(lambda: self._emit_theme("light"))
        self.theme_dark_btn = QPushButton()
        self.theme_dark_btn.setCheckable(True)
        self.theme_dark_btn.clicked.connect(lambda: self._emit_theme("dark"))
        theme_row.addWidget(self.theme_light_btn)
        theme_row.addWidget(self.theme_dark_btn)
        app_v.addLayout(theme_row)

        layout.addWidget(self.appearance_group)

        layout.addStretch(1)

        self.about_btn = QPushButton()
        self.about_btn.clicked.connect(self.aboutRequested.emit)
        layout.addWidget(self.about_btn)

        scroll.setWidget(container)
        outer.addWidget(scroll)

        self.set_has_record(False)

    def retranslate_ui(self) -> None:
        self.files_group.setTitle(self._tr.tr("ctrl_files_group").replace("&", "&&"))
        self.open_csv_btn.setText(self._tr.tr("btn_open_csv"))
        self.open_folder_btn.setText(self._tr.tr("btn_open_folder"))
        self.examples_btn.setText(self._tr.tr("btn_load_examples"))

        self.display_group.setTitle(self._tr.tr("ctrl_display_group").replace("&", "&&"))
        self.channel_label.setText(self._tr.tr("label_channel"))
        self.magnifier_label.setText(self._tr.tr("label_magnifier"))
        self.scale_up_btn.setToolTip(self._tr.tr("btn_scale_up"))
        self.scale_down_btn.setToolTip(self._tr.tr("btn_scale_down"))
        self.autoscale_btn.setText(self._tr.tr("btn_autoscale"))
        self.retimax_250_btn.setText(self._tr.tr("btn_retimax_250"))
        self.reset_view_btn.setText(self._tr.tr("btn_reset_view"))
        self.grid_checkbox.setText(self._tr.tr("chk_grid"))

        self.markers_group.setTitle(self._tr.tr("ctrl_markers_group").replace("&", "&&"))
        self.reset_markers_btn.setText(self._tr.tr("btn_reset_markers"))
        self.settings_btn.setText(self._tr.tr("btn_settings"))

        self.export_group.setTitle(self._tr.tr("ctrl_export_group").replace("&", "&&"))
        self.copy_table_btn.setText(self._tr.tr("btn_copy_table"))
        self.export_csv_btn.setText(self._tr.tr("btn_export_csv"))
        self.export_xlsx_btn.setText(self._tr.tr("btn_export_xlsx"))
        self.export_plot_btn.setText(self._tr.tr("btn_export_plot"))

        self.appearance_group.setTitle(self._tr.tr("ctrl_appearance_group").replace("&", "&&"))
        self.lang_label.setText(self._tr.tr("label_language"))
        self.theme_label.setText(self._tr.tr("label_theme"))
        self.theme_light_btn.setText(self._tr.tr("theme_light_short"))
        self.theme_dark_btn.setText(self._tr.tr("theme_dark_short"))
        self.about_btn.setText(self._tr.tr("btn_about"))

    def set_channels(self, channels: Sequence[str], active: str | None) -> None:
        self._updating_controls = True
        try:
            self.channel_combo.clear()
            for ch in channels:
                self.channel_combo.addItem(ch)
            if active and active in channels:
                self.channel_combo.setCurrentText(active)
        finally:
            self._updating_controls = False

    def set_has_record(self, has_record: bool) -> None:
        for widget in (
            self.channel_combo,
            self.scale_down_btn,
            self.scale_up_btn,
            self.magnifier_spin,
            self.autoscale_btn,
            self.retimax_250_btn,
            self.reset_view_btn,
            self.reset_markers_btn,
            self.copy_table_btn,
            self.export_csv_btn,
            self.export_xlsx_btn,
            self.export_plot_btn,
        ):
            widget.setEnabled(has_record)

    def set_auto_scale_state(self, enabled: bool) -> None:
        self._updating_controls = True
        try:
            self.autoscale_btn.setChecked(enabled)
        finally:
            self._updating_controls = False

    def set_magnifier_state(self, value: float) -> None:
        self._updating_controls = True
        try:
            self.magnifier_spin.setValue(value)
        finally:
            self._updating_controls = False

    def set_grid_state(self, enabled: bool) -> None:
        self._updating_controls = True
        try:
            self.grid_checkbox.setChecked(enabled)
        finally:
            self._updating_controls = False

    def set_language_state(self, lang: str) -> None:
        self.lang_en_btn.setChecked(lang == "en")
        self.lang_es_btn.setChecked(lang == "es")

    def set_theme_state(self, theme: str) -> None:
        self.theme_light_btn.setChecked(theme == "light")
        self.theme_dark_btn.setChecked(theme == "dark")

    def _on_channel_changed(self, text: str) -> None:
        if not self._updating_controls and text:
            self.channelChanged.emit(text)

    def _on_magnifier_changed(self, value: float) -> None:
        if self._updating_controls:
            return
        self.set_auto_scale_state(False)
        self.magnifierChanged.emit(value)

    def _step_magnifier(self, factor: float) -> None:
        new_val = max(0.25, min(25.0, round(self.magnifier_spin.value() * factor, 2)))
        self.magnifier_spin.setValue(new_val)

    def _on_autoscale_toggled(self, checked: bool) -> None:
        if not self._updating_controls:
            self.autoScaleToggled.emit(checked)

    def _on_retimax_250_clicked(self) -> None:
        self.set_auto_scale_state(False)
        self.set_magnifier_state(1.0)
        self.retimaxScaleRequested.emit()

    def _emit_language(self, lang: str) -> None:
        self.set_language_state(lang)
        self.languageChanged.emit(lang)

    def _emit_theme(self, theme: str) -> None:
        self.set_theme_state(theme)
        self.themeChanged.emit(theme)
