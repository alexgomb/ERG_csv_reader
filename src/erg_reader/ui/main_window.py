"""Main application window for nBio ERG-Trace."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterable

from PySide6.QtCore import QSettings
from PySide6.QtGui import QAction, QActionGroup, QDragEnterEvent, QDropEvent, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from erg_reader import APP_NAME, __author__
from erg_reader.analysis import auto_detect_markers
from erg_reader.exporters import (
    export_summary_csv,
    export_summary_xlsx,
    format_record_clipboard_tsv,
    load_session_json,
    save_session_json,
)
from erg_reader.i18n import SUPPORTED_LANGUAGES, Translator
from erg_reader.models import DetectionConfig, ERGProtocol, ERGSessionRecord
from erg_reader.parser import load_csv_batch
from erg_reader.themes import SUPPORTED_THEMES, get_stylesheet
from erg_reader.ui.branding import create_erg_icon
from erg_reader.ui.controls_panel import ControlsPanel
from erg_reader.ui.dialogs import AboutDialog, SettingsDialog
from erg_reader.ui.metrics_table import MetricsTablePanel
from erg_reader.ui.plot_widget import ERGPlotWidget
from erg_reader.ui.sidebar import SidebarPanel


def find_example_files_dir() -> Path | None:
    """Locate bundled example_files/ directory across source checkouts and PyInstaller builds."""
    candidates: list[Path] = []
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS) / "example_files")
        candidates.append(Path(sys.executable).resolve().parent / "example_files")

    # Package source tree: src/erg_reader/ui/main_window.py -> repo_root/example_files
    here = Path(__file__).resolve()
    candidates.append(here.parents[3] / "example_files")
    candidates.append(Path.cwd() / "example_files")

    for candidate in candidates:
        if candidate.is_dir() and any(candidate.glob("*.csv")):
            return candidate
    return None


class MainWindow(QMainWindow):
    """Primary Retimax-inspired left-eye ERG CSV analyzer window."""

    SETTINGS_ORG = "AlejandroGombauGarcia"
    SETTINGS_APP = "nBioERGTrace"

    def __init__(
        self,
        *,
        use_settings: bool = True,
        initial_language: str | None = None,
        initial_theme: str | None = None,
    ) -> None:
        super().__init__()
        self._use_settings = use_settings
        self._settings = QSettings(self.SETTINGS_ORG, self.SETTINGS_APP) if use_settings else None

        saved_lang = self._load_setting("language", "en")
        saved_theme = self._load_setting("theme", "light")
        saved_grid = self._load_setting("show_grid", True, as_bool=True)

        lang = initial_language if initial_language in SUPPORTED_LANGUAGES else saved_lang
        theme = initial_theme if initial_theme in SUPPORTED_THEMES else saved_theme

        self.translator = Translator(lang)
        self._theme = theme if theme in SUPPORTED_THEMES else "light"
        self._show_grid = bool(saved_grid)
        self._last_dir = str(self._load_setting("last_dir", str(Path.home())))

        self.config = self._load_detection_config()
        self.records: list[ERGSessionRecord] = []
        self._active_record_id: str | None = None
        self._last_status: tuple[str, dict[str, object]] = ("status_ready", {})

        self.setAcceptDrops(True)
        self.resize(1360, 840)
        self.setMinimumSize(1040, 700)

        self._build_menus()
        self._build_central_layout()
        self._connect_signals()

        self.apply_theme(self._theme, persist=False)
        self.set_language(self.translator.language, persist=False)
        self._set_grid_visible(self._show_grid, persist=False)
        self._set_status("status_ready")

    # ------------------------------------------------------------------
    # Settings persistence helpers
    # ------------------------------------------------------------------
    def _load_setting(self, key: str, default: object, as_bool: bool = False) -> object:
        if self._settings is None:
            return default
        val = self._settings.value(key, default)
        if as_bool:
            if isinstance(val, bool):
                return val
            return str(val).lower() in ("1", "true", "yes")
        return val if val is not None else default

    def _save_setting(self, key: str, value: object) -> None:
        if self._settings is not None:
            self._settings.setValue(key, value)

    def _load_detection_config(self) -> DetectionConfig:
        raw = self._load_setting("detection_config_json", "")
        if isinstance(raw, str) and raw.strip():
            try:
                return DetectionConfig.from_dict(json.loads(raw))
            except (ValueError, TypeError):
                pass
        return DetectionConfig()

    def _save_detection_config(self) -> None:
        self._save_setting("detection_config_json", json.dumps(self.config.to_dict()))

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------
    def _build_menus(self) -> None:
        bar = self.menuBar()

        # File menu
        self.menu_file = bar.addMenu("")
        self.act_open_csv = QAction(self)
        self.act_open_csv.setShortcut(QKeySequence.StandardKey.Open)
        self.act_open_folder = QAction(self)
        self.act_open_folder.setShortcut(QKeySequence("Ctrl+Shift+O"))
        self.act_load_examples = QAction(self)

        self.act_save_session = QAction(self)
        self.act_save_session.setShortcut(QKeySequence.StandardKey.Save)
        self.act_load_session = QAction(self)

        self.act_export_csv = QAction(self)
        self.act_export_xlsx = QAction(self)
        self.act_export_png = QAction(self)
        self.act_export_svg = QAction(self)
        self.act_copy_table = QAction(self)
        self.act_copy_table.setShortcut(QKeySequence("Ctrl+Shift+C"))
        self.act_clear_all = QAction(self)
        self.act_exit = QAction(self)
        self.act_exit.setShortcut(QKeySequence.StandardKey.Quit)

        self.menu_file.addAction(self.act_open_csv)
        self.menu_file.addAction(self.act_open_folder)
        self.menu_file.addAction(self.act_load_examples)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.act_save_session)
        self.menu_file.addAction(self.act_load_session)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.act_export_csv)
        self.menu_file.addAction(self.act_export_xlsx)
        self.menu_file.addAction(self.act_export_png)
        self.menu_file.addAction(self.act_export_svg)
        self.menu_file.addAction(self.act_copy_table)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.act_clear_all)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.act_exit)

        # View menu
        self.menu_view = bar.addMenu("")
        self.theme_group = QActionGroup(self)
        self.act_theme_light = QAction(self, checkable=True)
        self.act_theme_dark = QAction(self, checkable=True)
        self.theme_group.addAction(self.act_theme_light)
        self.theme_group.addAction(self.act_theme_dark)

        self.lang_group = QActionGroup(self)
        self.act_lang_en = QAction(self, checkable=True)
        self.act_lang_es = QAction(self, checkable=True)
        self.lang_group.addAction(self.act_lang_en)
        self.lang_group.addAction(self.act_lang_es)

        self.act_toggle_grid = QAction(self, checkable=True)
        self.act_toggle_grid.setShortcut(QKeySequence("G"))
        self.act_auto_scale = QAction(self, checkable=True)
        self.act_fixed_scale = QAction(self)
        self.act_reset_zoom = QAction(self)
        self.act_reset_zoom.setShortcut(QKeySequence("Ctrl+0"))

        self.menu_view.addAction(self.act_theme_light)
        self.menu_view.addAction(self.act_theme_dark)
        self.menu_view.addSeparator()
        self.menu_view.addAction(self.act_lang_en)
        self.menu_view.addAction(self.act_lang_es)
        self.menu_view.addSeparator()
        self.menu_view.addAction(self.act_toggle_grid)
        self.menu_view.addAction(self.act_auto_scale)
        self.menu_view.addAction(self.act_fixed_scale)
        self.menu_view.addAction(self.act_reset_zoom)

        # Analysis menu
        self.menu_analysis = bar.addMenu("")
        self.act_reset_markers = QAction(self)
        self.act_reset_markers.setShortcut(QKeySequence("Ctrl+R"))
        self.act_redetect_all = QAction(self)
        self.act_settings = QAction(self)
        self.menu_analysis.addAction(self.act_reset_markers)
        self.menu_analysis.addAction(self.act_redetect_all)
        self.menu_analysis.addSeparator()
        self.menu_analysis.addAction(self.act_settings)

        # Help menu
        self.menu_help = bar.addMenu("")
        self.act_about = QAction(self)
        self.menu_help.addAction(self.act_about)

    def _build_central_layout(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 8)
        main_layout.setSpacing(10)

        # Left column: subject metadata + loaded CSV list with reference checkboxes
        self.sidebar = SidebarPanel(self.translator, theme=self._theme)
        main_layout.addWidget(self.sidebar)

        # Center column: interactive LEFT - OS waveform plot + Retimax table + Flicker card
        center_col = QVBoxLayout()
        center_col.setSpacing(10)
        self.plot_panel = ERGPlotWidget(self.translator, theme=self._theme)
        self.metrics_panel = MetricsTablePanel(self.translator, theme=self._theme)
        center_col.addWidget(self.plot_panel, stretch=1)
        center_col.addWidget(self.metrics_panel)
        main_layout.addLayout(center_col, stretch=1)

        # Right column: Retimax-style ergonomic controls panel
        self.controls = ControlsPanel(self.translator, theme=self._theme)
        main_layout.addWidget(self.controls)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def _connect_signals(self) -> None:
        # Menu actions
        self.act_open_csv.triggered.connect(self.open_csv_dialog)
        self.act_open_folder.triggered.connect(self.open_folder_dialog)
        self.act_load_examples.triggered.connect(self.load_example_files)
        self.act_save_session.triggered.connect(self.save_session_dialog)
        self.act_load_session.triggered.connect(self.load_session_dialog)
        self.act_export_csv.triggered.connect(self.export_csv_dialog)
        self.act_export_xlsx.triggered.connect(self.export_xlsx_dialog)
        self.act_export_png.triggered.connect(lambda: self.export_plot_dialog(default_fmt="png"))
        self.act_export_svg.triggered.connect(lambda: self.export_plot_dialog(default_fmt="svg"))
        self.act_copy_table.triggered.connect(self.copy_table_to_clipboard)
        self.act_clear_all.triggered.connect(self.clear_all_records)
        self.act_exit.triggered.connect(self.close)

        self.act_theme_light.triggered.connect(lambda: self.apply_theme("light"))
        self.act_theme_dark.triggered.connect(lambda: self.apply_theme("dark"))
        self.act_lang_en.triggered.connect(lambda: self.set_language("en"))
        self.act_lang_es.triggered.connect(lambda: self.set_language("es"))
        self.act_toggle_grid.toggled.connect(self._set_grid_visible)
        self.act_auto_scale.toggled.connect(self._set_auto_scale)
        self.act_fixed_scale.triggered.connect(self._apply_retimax_250_scale)
        self.act_reset_zoom.triggered.connect(self.plot_panel.reset_view)

        self.act_reset_markers.triggered.connect(self.reset_active_markers)
        self.act_redetect_all.triggered.connect(self.redetect_all_markers)
        self.act_settings.triggered.connect(self.open_settings_dialog)
        self.act_about.triggered.connect(self.open_about_dialog)

        # Sidebar signals
        self.sidebar.recordSelected.connect(self.select_record)
        self.sidebar.overlayToggled.connect(self.toggle_overlay)
        self.sidebar.metadataEdited.connect(self._on_metadata_edited)
        self.sidebar.protocolChanged.connect(self._on_protocol_changed)
        self.sidebar.removeRecordRequested.connect(self.remove_record)
        self.sidebar.clearOverlaysRequested.connect(self.clear_overlays)

        # Plot signals
        self.plot_panel.markerMoved.connect(self._on_marker_moved)

        # Controls panel signals
        self.controls.openCsvRequested.connect(self.open_csv_dialog)
        self.controls.openFolderRequested.connect(self.open_folder_dialog)
        self.controls.loadExamplesRequested.connect(self.load_example_files)
        self.controls.channelChanged.connect(self._on_channel_changed)
        self.controls.magnifierChanged.connect(self._on_magnifier_changed)
        self.controls.autoScaleToggled.connect(self._set_auto_scale)
        self.controls.retimaxScaleRequested.connect(self._apply_retimax_250_scale)
        self.controls.resetViewRequested.connect(self.plot_panel.reset_view)
        self.controls.gridToggled.connect(self._set_grid_visible)
        self.controls.resetMarkersRequested.connect(self.reset_active_markers)
        self.controls.settingsRequested.connect(self.open_settings_dialog)
        self.controls.copyTableRequested.connect(self.copy_table_to_clipboard)
        self.controls.exportCsvRequested.connect(self.export_csv_dialog)
        self.controls.exportXlsxRequested.connect(self.export_xlsx_dialog)
        self.controls.exportPlotRequested.connect(lambda: self.export_plot_dialog(default_fmt="png"))
        self.controls.languageChanged.connect(self.set_language)
        self.controls.themeChanged.connect(self.apply_theme)
        self.controls.aboutRequested.connect(self.open_about_dialog)

    # ------------------------------------------------------------------
    # Theme & Localization
    # ------------------------------------------------------------------
    @property
    def current_theme(self) -> str:
        return self._theme

    @property
    def current_language(self) -> str:
        return self.translator.language

    def apply_theme(self, theme: str, persist: bool = True) -> None:
        if theme not in SUPPORTED_THEMES:
            return
        self._theme = theme
        qss = get_stylesheet(theme)
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(qss)
        else:
            self.setStyleSheet(qss)

        self.setWindowIcon(create_erg_icon(dark_mode=(theme == "dark")))
        self.act_theme_light.setChecked(theme == "light")
        self.act_theme_dark.setChecked(theme == "dark")
        self.controls.set_theme_state(theme)
        self.sidebar.apply_theme(theme)
        self.plot_panel.apply_theme(theme)
        self.metrics_panel.apply_theme(theme)
        if persist:
            self._save_setting("theme", theme)

    def set_language(self, language: str, persist: bool = True) -> None:
        if language not in SUPPORTED_LANGUAGES:
            return
        self.translator.set_language(language)
        self.act_lang_en.setChecked(language == "en")
        self.act_lang_es.setChecked(language == "es")
        self.controls.set_language_state(language)
        self._retranslate_all()
        if persist:
            self._save_setting("language", language)

    def _retranslate_all(self) -> None:
        tr = self.translator.tr
        self.setWindowTitle(tr("app_title"))

        self.menu_file.setTitle(tr("menu_file"))
        self.menu_view.setTitle(tr("menu_view"))
        self.menu_analysis.setTitle(tr("menu_analysis"))
        self.menu_help.setTitle(tr("menu_help"))

        self.act_open_csv.setText(tr("action_open_csv"))
        self.act_open_folder.setText(tr("action_open_folder"))
        self.act_load_examples.setText(tr("action_load_examples"))
        self.act_save_session.setText(tr("action_save_session"))
        self.act_load_session.setText(tr("action_load_session"))
        self.act_export_csv.setText(tr("action_export_csv"))
        self.act_export_xlsx.setText(tr("action_export_xlsx"))
        self.act_export_png.setText(tr("action_export_png"))
        self.act_export_svg.setText(tr("action_export_svg"))
        self.act_copy_table.setText(tr("action_copy_table"))
        self.act_clear_all.setText(tr("action_clear_all"))
        self.act_exit.setText(tr("action_exit"))

        self.act_theme_light.setText(tr("action_theme_light"))
        self.act_theme_dark.setText(tr("action_theme_dark"))
        self.act_lang_en.setText(tr("action_lang_en"))
        self.act_lang_es.setText(tr("action_lang_es"))
        self.act_toggle_grid.setText(tr("action_toggle_grid"))
        self.act_auto_scale.setText(tr("action_auto_scale"))
        self.act_fixed_scale.setText(tr("action_fixed_scale"))
        self.act_reset_zoom.setText(tr("action_reset_zoom"))

        self.act_reset_markers.setText(tr("action_reset_markers"))
        self.act_redetect_all.setText(tr("action_redetect_all"))
        self.act_settings.setText(tr("action_settings"))
        self.act_about.setText(tr("action_about"))

        self.sidebar.retranslate_ui()
        self.plot_panel.retranslate_ui()
        self.metrics_panel.retranslate_ui()
        self.controls.retranslate_ui()
        self._refresh_status_bar()

    def _set_status(self, key: str, **kwargs: object) -> None:
        self._last_status = (key, kwargs)
        self._refresh_status_bar()

    def _refresh_status_bar(self) -> None:
        key, kwargs = self._last_status
        self.status_bar.showMessage(self.translator.tr(key, **kwargs))

    # ------------------------------------------------------------------
    # Drag & Drop Support
    # ------------------------------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    p = Path(url.toLocalFile())
                    if p.is_dir() or p.suffix.lower() in (".csv", ".json"):
                        event.acceptProposedAction()
                        return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        if not paths:
            return
        if len(paths) == 1 and paths[0].suffix.lower() == ".json":
            self.load_session_from_path(paths[0])
            return
        self.load_paths(paths)

    # ------------------------------------------------------------------
    # Record State & Loading
    # ------------------------------------------------------------------
    @property
    def active_record(self) -> ERGSessionRecord | None:
        for rec in self.records:
            if rec.record_id == self._active_record_id:
                return rec
        return None

    def _overlay_records(self) -> list[ERGSessionRecord]:
        return [
            rec
            for rec in self.records
            if rec.overlay_enabled and rec.record_id != self._active_record_id
        ]

    def load_paths(self, paths: Iterable[str | Path], *, replace: bool = False) -> int:
        """Load one or more CSV files or folders into the session."""
        tr = self.translator.tr
        result = load_csv_batch(paths, config=self.config)

        if not result.records and not result.skipped_right_od and not result.errors:
            self._set_status("status_no_csv_found")
            return 0

        if replace:
            self.records = []
            self._active_record_id = None

        existing_paths = {rec.file_path for rec in self.records}
        added: list[ERGSessionRecord] = []
        for rec in result.records:
            if rec.file_path not in existing_paths:
                self.records.append(rec)
                existing_paths.add(rec.file_path)
                added.append(rec)

        if added:
            self._active_record_id = added[0].record_id

        self._refresh_entire_view(preserve_range=False)

        if result.errors:
            err_lines = "\n".join(f"• {p.name}: {msg}" for p, msg in result.errors[:10])
            QMessageBox.warning(self, tr("msg_parse_errors_title"), err_lines)

        if added and result.skipped_right_od:
            self._set_status("status_loaded", loaded=len(added), skipped=len(result.skipped_right_od))
        elif added:
            self._set_status("status_loaded_no_skip", loaded=len(added))
        elif result.skipped_right_od:
            self._set_status("status_all_skipped_od", skipped=len(result.skipped_right_od))

        return len(added)

    def open_csv_dialog(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            self.translator.tr("dialog_open_csv_title"),
            self._last_dir,
            "CSO Retimax CSV (*.csv);;All Files (*)",
        )
        if files:
            self._last_dir = str(Path(files[0]).parent)
            self._save_setting("last_dir", self._last_dir)
            self.load_paths(files)

    def open_folder_dialog(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            self.translator.tr("dialog_open_folder_title"),
            self._last_dir,
        )
        if folder:
            self._last_dir = folder
            self._save_setting("last_dir", self._last_dir)
            self.load_paths([folder])

    def load_example_files(self) -> None:
        example_dir = find_example_files_dir()
        if example_dir is None:
            QMessageBox.information(
                self,
                self.translator.tr("msg_examples_missing_title"),
                self.translator.tr("msg_examples_missing_body"),
            )
            return
        self.load_paths([example_dir], replace=False)

    def select_record(self, record_id: str) -> None:
        if record_id == self._active_record_id:
            return
        if any(r.record_id == record_id for r in self.records):
            self._active_record_id = record_id
            self.sidebar.set_selected_record_id(record_id)
            self._refresh_active_display(preserve_range=False)

    def toggle_overlay(self, record_id: str, checked: bool) -> None:
        for rec in self.records:
            if rec.record_id == record_id:
                rec.overlay_enabled = checked
                break
        self.sidebar.clear_overlays_btn.setEnabled(any(r.overlay_enabled for r in self.records))
        self.plot_panel.set_data(
            self.active_record,
            overlays=self._overlay_records(),
            preserve_range=True,
        )

    def clear_overlays(self) -> None:
        for rec in self.records:
            rec.overlay_enabled = False
        self._refresh_entire_view(preserve_range=True)

    def remove_record(self, record_id: str) -> None:
        idx_to_remove = next((i for i, r in enumerate(self.records) if r.record_id == record_id), -1)
        if idx_to_remove < 0:
            return
        self.records.pop(idx_to_remove)
        if self._active_record_id == record_id:
            if self.records:
                next_idx = min(idx_to_remove, len(self.records) - 1)
                self._active_record_id = self.records[next_idx].record_id
            else:
                self._active_record_id = None
        self._refresh_entire_view(preserve_range=False)

    def clear_all_records(self) -> None:
        self.records.clear()
        self._active_record_id = None
        self._refresh_entire_view(preserve_range=False)
        self._set_status("status_ready")

    # ------------------------------------------------------------------
    # Active Plot, Markers, Channel & Display Synchronization
    # ------------------------------------------------------------------
    def _refresh_entire_view(self, preserve_range: bool = False) -> None:
        self.sidebar.set_records(self.records, self._active_record_id)
        self._refresh_active_display(preserve_range=preserve_range)

    def _refresh_active_display(self, preserve_range: bool = False) -> None:
        rec = self.active_record
        self.sidebar.set_active_record(rec)
        self.controls.set_has_record(rec is not None)
        if rec is not None:
            self.controls.set_channels(rec.available_channels, rec.active_channel)
        else:
            self.controls.set_channels([], None)

        self.plot_panel.set_data(rec, overlays=self._overlay_records(), preserve_range=preserve_range)
        self.metrics_panel.set_record(rec)

    def _on_metadata_edited(self) -> None:
        self.plot_panel.set_data(
            self.active_record,
            overlays=self._overlay_records(),
            preserve_range=True,
        )

    def _on_protocol_changed(self, protocol: ERGProtocol) -> None:
        rec = self.active_record
        if rec is None or rec.protocol == protocol:
            return
        old_default_exam = rec.protocol.display_name
        rec.protocol = protocol
        if not rec.metadata.exam.strip() or rec.metadata.exam.strip().upper() == old_default_exam:
            rec.metadata.exam = protocol.display_name
        if not rec.markers.is_manual:
            rec.markers = auto_detect_markers(rec.time_ms, rec.active_signal, rec.protocol, self.config)
        self.sidebar.set_active_record(rec)
        self.sidebar.update_record_label(rec)
        self.plot_panel.set_data(rec, overlays=self._overlay_records(), preserve_range=True)
        self.metrics_panel.set_record(rec)

    def _on_marker_moved(self, _marker_key: str, _sample_idx: int) -> None:
        rec = self.active_record
        if rec is None:
            return
        self.metrics_panel.set_record(rec)
        self.sidebar.update_record_label(rec)

    def _on_channel_changed(self, channel_name: str) -> None:
        rec = self.active_record
        if rec is None or channel_name not in rec.channels:
            return
        rec.active_channel = channel_name
        if not rec.markers.is_manual:
            rec.markers = auto_detect_markers(rec.time_ms, rec.active_signal, rec.protocol, self.config)
        self.plot_panel.set_data(rec, overlays=self._overlay_records(), preserve_range=True)
        self.metrics_panel.set_record(rec)

    def _on_magnifier_changed(self, value: float) -> None:
        self.act_auto_scale.blockSignals(True)
        self.act_auto_scale.setChecked(False)
        self.act_auto_scale.blockSignals(False)
        self.plot_panel.set_magnifier(value)

    def _set_auto_scale(self, enabled: bool) -> None:
        self.act_auto_scale.blockSignals(True)
        self.act_auto_scale.setChecked(enabled)
        self.act_auto_scale.blockSignals(False)
        self.controls.set_auto_scale_state(enabled)
        self.plot_panel.set_auto_scale(enabled)

    def _apply_retimax_250_scale(self) -> None:
        self.act_auto_scale.blockSignals(True)
        self.act_auto_scale.setChecked(False)
        self.act_auto_scale.blockSignals(False)
        self.controls.set_auto_scale_state(False)
        self.controls.set_magnifier_state(1.0)
        self.plot_panel.set_magnifier(1.0)

    def _set_grid_visible(self, enabled: bool, persist: bool = True) -> None:
        self._show_grid = enabled
        self.act_toggle_grid.blockSignals(True)
        self.act_toggle_grid.setChecked(enabled)
        self.act_toggle_grid.blockSignals(False)
        self.controls.set_grid_state(enabled)
        self.plot_panel.set_show_grid(enabled)
        if persist:
            self._save_setting("show_grid", enabled)

    def reset_active_markers(self) -> None:
        rec = self.active_record
        if rec is None:
            return
        rec.markers = auto_detect_markers(rec.time_ms, rec.active_signal, rec.protocol, self.config)
        self.plot_panel.refresh_markers()
        self.metrics_panel.set_record(rec)
        self.sidebar.update_record_label(rec)
        self._set_status("status_markers_reset")

    def redetect_all_markers(self, *, only_auto: bool = False) -> None:
        for rec in self.records:
            if only_auto and rec.markers.is_manual:
                continue
            rec.markers = auto_detect_markers(rec.time_ms, rec.active_signal, rec.protocol, self.config)
            self.sidebar.update_record_label(rec)
        self.plot_panel.refresh_markers()
        self.metrics_panel.set_record(self.active_record)

    # ------------------------------------------------------------------
    # Export, Clipboard & Sessions
    # ------------------------------------------------------------------
    def _ensure_records(self) -> bool:
        if self.records:
            return True
        QMessageBox.information(
            self,
            self.translator.tr("msg_no_records_title"),
            self.translator.tr("msg_no_records_body"),
        )
        return False

    def copy_table_to_clipboard(self) -> None:
        rec = self.active_record
        if rec is None:
            self._ensure_records()
            return
        tsv = format_record_clipboard_tsv(rec)
        QApplication.clipboard().setText(tsv)
        self._set_status("status_copied_clipboard")

    def export_csv_dialog(self) -> None:
        if not self._ensure_records():
            return
        default_path = str(Path(self._last_dir) / "erg_summary.csv")
        out_path, _ = QFileDialog.getSaveFileName(
            self,
            self.translator.tr("dialog_export_csv_title"),
            default_path,
            "CSV Files (*.csv)",
        )
        if not out_path:
            return
        if not out_path.lower().endswith(".csv"):
            out_path += ".csv"
        try:
            saved = export_summary_csv(self.records, out_path)
            self._last_dir = str(saved.parent)
            self._save_setting("last_dir", self._last_dir)
            self._set_status("status_exported", path=str(saved))
        except OSError as exc:
            QMessageBox.critical(self, self.translator.tr("msg_export_error_title"), str(exc))

    def export_xlsx_dialog(self) -> None:
        if not self._ensure_records():
            return
        default_path = str(Path(self._last_dir) / "erg_summary.xlsx")
        out_path, _ = QFileDialog.getSaveFileName(
            self,
            self.translator.tr("dialog_export_xlsx_title"),
            default_path,
            "Excel Workbook (*.xlsx)",
        )
        if not out_path:
            return
        if not out_path.lower().endswith(".xlsx"):
            out_path += ".xlsx"
        try:
            saved = export_summary_xlsx(self.records, out_path)
            self._last_dir = str(saved.parent)
            self._save_setting("last_dir", self._last_dir)
            self._set_status("status_exported", path=str(saved))
        except OSError as exc:
            QMessageBox.critical(self, self.translator.tr("msg_export_error_title"), str(exc))

    def export_plot_dialog(self, default_fmt: str = "png") -> None:
        rec = self.active_record
        if rec is None:
            self._ensure_records()
            return
        stem = Path(rec.file_name).stem.replace(" ", "_")
        ext = ".svg" if default_fmt == "svg" else ".png"
        default_path = str(Path(self._last_dir) / f"{stem}{ext}")
        filters = "PNG Image (*.png);;SVG Vector (*.svg)"
        selected_filter = "SVG Vector (*.svg)" if default_fmt == "svg" else "PNG Image (*.png)"
        out_path, chosen = QFileDialog.getSaveFileName(
            self,
            self.translator.tr("dialog_export_plot_title"),
            default_path,
            filters,
            selected_filter,
        )
        if not out_path:
            return
        if not out_path.lower().endswith((".png", ".svg")):
            out_path += ".svg" if "SVG" in chosen else ".png"
        try:
            saved = self.plot_panel.export_plot(out_path)
            self._last_dir = str(saved.parent)
            self._save_setting("last_dir", self._last_dir)
            self._set_status("status_exported", path=str(saved))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, self.translator.tr("msg_export_error_title"), str(exc))

    def save_session_dialog(self) -> None:
        if not self._ensure_records():
            return
        default_path = str(Path(self._last_dir) / "erg_session.json")
        out_path, _ = QFileDialog.getSaveFileName(
            self,
            self.translator.tr("dialog_save_session_title"),
            default_path,
            "ERG Session (*.json)",
        )
        if not out_path:
            return
        if not out_path.lower().endswith(".json"):
            out_path += ".json"
        try:
            saved = save_session_json(
                self.records,
                out_path,
                config=self.config,
                active_record_id=self._active_record_id,
            )
            self._last_dir = str(saved.parent)
            self._save_setting("last_dir", self._last_dir)
            self._set_status("status_session_saved", path=str(saved), count=len(self.records))
        except OSError as exc:
            QMessageBox.critical(self, self.translator.tr("msg_session_error_title"), str(exc))

    def load_session_dialog(self) -> None:
        in_path, _ = QFileDialog.getOpenFileName(
            self,
            self.translator.tr("dialog_load_session_title"),
            self._last_dir,
            "ERG Session (*.json)",
        )
        if in_path:
            self.load_session_from_path(Path(in_path))

    def load_session_from_path(self, session_path: Path) -> None:
        try:
            records, cfg, active_id, warnings = load_session_json(session_path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, self.translator.tr("msg_session_error_title"), str(exc))
            return

        self.config = cfg
        self._save_detection_config()
        self.records = records
        if active_id and any(r.record_id == active_id for r in records):
            self._active_record_id = active_id
        elif records:
            self._active_record_id = records[0].record_id
        else:
            self._active_record_id = None

        self._refresh_entire_view(preserve_range=False)
        self._set_status("status_session_loaded", count=len(self.records))
        if warnings:
            QMessageBox.warning(
                self,
                self.translator.tr("msg_parse_errors_title"),
                "\n".join(f"• {w}" for w in warnings[:10]),
            )

    # ------------------------------------------------------------------
    # Dialogs
    # ------------------------------------------------------------------
    def open_settings_dialog(self) -> None:
        dlg = SettingsDialog(self.config, self.translator, parent=self)
        if dlg.exec():
            self.config = dlg.get_config()
            self._save_detection_config()
            self.redetect_all_markers(only_auto=True)
            self._set_status("status_settings_updated")

    def open_about_dialog(self) -> None:
        dlg = AboutDialog(self.translator, theme=self._theme, parent=self)
        dlg.exec()


def _app_metadata_tag() -> str:
    return f"{APP_NAME} — {__author__}"
