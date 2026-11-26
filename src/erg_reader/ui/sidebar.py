"""Retimax-inspired left sidebar: subject/exam metadata, interactive CSV list with overlays, and author credit."""

from __future__ import annotations

from typing import Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from erg_reader import APP_NAME
from erg_reader.i18n import Translator
from erg_reader.models import ERGProtocol, ERGSessionRecord, EyeSide
from erg_reader.ui.branding import create_erg_pixmap, render_umh_nbio_pixmap

PROTOCOL_CHOICES: tuple[ERGProtocol, ...] = (
    ERGProtocol.DARK_ADAPTED_3,
    ERGProtocol.DARK_ADAPTED_10,
    ERGProtocol.LIGHT_ADAPTED_3,
    ERGProtocol.LIGHT_ADAPTED_3_FLICKER,
    ERGProtocol.UNKNOWN,
)


class SidebarPanel(QFrame):
    """Left panel housing editable mouse metadata and loaded CSV trace list."""

    recordSelected = Signal(str)  # record_id
    overlayToggled = Signal(str, bool)  # (record_id, checked)
    metadataEdited = Signal()
    protocolChanged = Signal(object)  # ERGProtocol
    removeRecordRequested = Signal(str)  # record_id
    clearOverlaysRequested = Signal()

    def __init__(self, translator: Translator, theme: str = "light", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("SidebarPanel")
        self.setMinimumWidth(285)
        self.setMaximumWidth(335)

        self._tr = translator
        self._theme = theme
        self._active_record: ERGSessionRecord | None = None
        self._populating_fields = False
        self._populating_list = False

        self._build_ui()
        self.apply_theme(theme)
        self.retranslate_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # App branding header
        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(40, 40)
        brand_row.addWidget(self.logo_label)

        brand_text = QVBoxLayout()
        brand_text.setSpacing(1)
        self.brand_title = QLabel(APP_NAME)
        self.brand_title.setObjectName("AppBrandTitle")
        self.brand_subtitle = QLabel("")
        self.brand_subtitle.setObjectName("MutedLabel")
        self.brand_subtitle.setWordWrap(True)
        brand_text.addWidget(self.brand_title)
        brand_text.addWidget(self.brand_subtitle)
        brand_row.addLayout(brand_text, stretch=1)
        layout.addLayout(brand_row)

        # Subject & Exam Metadata (Retimax left column layout)
        self.meta_group = QGroupBox()
        form = QFormLayout(self.meta_group)
        form.setContentsMargins(8, 12, 8, 8)
        form.setVerticalSpacing(6)
        form.setHorizontalSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.strain_label = QLabel()
        self.strain_edit = QLineEdit()
        self.strain_edit.textEdited.connect(self._on_metadata_changed)

        self.mouse_id_label = QLabel()
        self.mouse_id_edit = QLineEdit()
        self.mouse_id_edit.textEdited.connect(self._on_metadata_changed)

        self.age_label = QLabel()
        self.age_edit = QLineEdit()
        self.age_edit.textEdited.connect(self._on_metadata_changed)

        self.protocol_label = QLabel()
        self.protocol_combo = QComboBox()
        for proto in PROTOCOL_CHOICES:
            self.protocol_combo.addItem("", proto.value)
        self.protocol_combo.currentIndexChanged.connect(self._on_protocol_index_changed)

        self.exam_label = QLabel()
        self.exam_edit = QLineEdit()
        self.exam_edit.textEdited.connect(self._on_metadata_changed)

        self.exam_start_label = QLabel()
        self.exam_start_edit = QLineEdit()
        self.exam_start_edit.setReadOnly(True)

        self.notes_label = QLabel()
        self.notes_edit = QLineEdit()
        self.notes_edit.textEdited.connect(self._on_metadata_changed)

        form.addRow(self.strain_label, self.strain_edit)
        form.addRow(self.mouse_id_label, self.mouse_id_edit)
        form.addRow(self.age_label, self.age_edit)
        form.addRow(self.protocol_label, self.protocol_combo)
        form.addRow(self.exam_label, self.exam_edit)
        form.addRow(self.exam_start_label, self.exam_start_edit)
        form.addRow(self.notes_label, self.notes_edit)
        layout.addWidget(self.meta_group)

        # Loaded CSV traces with reference-overlay checkboxes
        self.traces_group = QGroupBox()
        traces_layout = QVBoxLayout(self.traces_group)
        traces_layout.setContentsMargins(8, 12, 8, 8)
        traces_layout.setSpacing(6)

        self.overlay_hint = QLabel()
        self.overlay_hint.setObjectName("MutedLabel")
        self.overlay_hint.setWordWrap(True)
        traces_layout.addWidget(self.overlay_hint)

        self.trace_list = QListWidget()
        self.trace_list.setAlternatingRowColors(False)
        self.trace_list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.trace_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.trace_list.currentItemChanged.connect(self._on_current_item_changed)
        self.trace_list.itemChanged.connect(self._on_item_check_changed)
        traces_layout.addWidget(self.trace_list, stretch=1)

        list_actions = QHBoxLayout()
        list_actions.setSpacing(6)
        self.remove_btn = QPushButton()
        self.remove_btn.clicked.connect(self._on_remove_clicked)
        self.clear_overlays_btn = QPushButton()
        self.clear_overlays_btn.clicked.connect(self.clearOverlaysRequested.emit)
        list_actions.addWidget(self.remove_btn)
        list_actions.addWidget(self.clear_overlays_btn)
        traces_layout.addLayout(list_actions)

        layout.addWidget(self.traces_group, stretch=1)

        # Institutional UMH · nBio vector SVG logo (Retimax bottom-left placement)
        self.umh_nbio_logo = QLabel()
        self.umh_nbio_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.umh_nbio_logo.setToolTip("Grupo nBio · Instituto de Bioingeniería · Universidad Miguel Hernández")
        layout.addWidget(self.umh_nbio_logo)

        # Subtle author credit footer
        self.author_footer = QLabel()
        self.author_footer.setObjectName("AuthorFooter")
        self.author_footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.author_footer.setWordWrap(True)
        layout.addWidget(self.author_footer)

        self._set_fields_enabled(False)

    def apply_theme(self, theme: str) -> None:
        self._theme = theme
        is_dark = theme == "dark"
        self.logo_label.setPixmap(create_erg_pixmap(40, dark_mode=is_dark))
        self.umh_nbio_logo.setPixmap(render_umh_nbio_pixmap(width=256, dark_mode=is_dark))

    def retranslate_ui(self) -> None:
        self.brand_subtitle.setText(self._tr.tr("subtitle_badge"))
        self.meta_group.setTitle(self._tr.tr("sidebar_subject_group").replace("&", "&&"))
        self.strain_label.setText(self._tr.tr("label_strain"))
        self.strain_edit.setPlaceholderText(self._tr.tr("placeholder_strain"))
        self.mouse_id_label.setText(self._tr.tr("label_mouse_id"))
        self.mouse_id_edit.setPlaceholderText(self._tr.tr("placeholder_mouse_id"))
        self.age_label.setText(self._tr.tr("label_age"))
        self.age_edit.setPlaceholderText(self._tr.tr("placeholder_age"))
        self.protocol_label.setText(self._tr.tr("label_protocol"))
        self._populating_fields = True
        try:
            for idx, proto in enumerate(PROTOCOL_CHOICES):
                self.protocol_combo.setItemText(idx, self._tr.tr(f"protocol_{proto.value}"))
        finally:
            self._populating_fields = False
        self.exam_label.setText(self._tr.tr("label_exam"))
        self.exam_edit.setPlaceholderText(self._tr.tr("placeholder_exam"))
        self.exam_start_label.setText(self._tr.tr("label_exam_start"))
        self.notes_label.setText(self._tr.tr("label_notes"))
        self.notes_edit.setPlaceholderText(self._tr.tr("placeholder_notes"))

        self.traces_group.setTitle(self._tr.tr("sidebar_traces_group").replace("&", "&&"))
        self.overlay_hint.setText(self._tr.tr("sidebar_overlay_hint"))
        self.remove_btn.setText(self._tr.tr("btn_remove_selected"))
        self.clear_overlays_btn.setText(self._tr.tr("btn_clear_overlays"))
        self.author_footer.setText(self._tr.tr("author_credit"))

    def set_records(self, records: Sequence[ERGSessionRecord], active_id: str | None) -> None:
        self._populating_list = True
        try:
            self.trace_list.clear()
            selected_row = -1
            for idx, rec in enumerate(records):
                item = QListWidgetItem(self._format_item_label(rec))
                item.setData(Qt.ItemDataRole.UserRole, rec.record_id)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(
                    Qt.CheckState.Checked if rec.overlay_enabled else Qt.CheckState.Unchecked
                )
                item.setToolTip(f"{rec.file_name}\n{rec.file_path}")
                self.trace_list.addItem(item)
                if rec.record_id == active_id:
                    selected_row = idx

            if selected_row >= 0:
                self.trace_list.setCurrentRow(selected_row)
            elif records:
                self.trace_list.setCurrentRow(0)
        finally:
            self._populating_list = False

        has_records = len(records) > 0
        self.remove_btn.setEnabled(has_records)
        self.clear_overlays_btn.setEnabled(any(r.overlay_enabled for r in records))

    def set_selected_record_id(self, record_id: str | None) -> None:
        """Synchronize the QListWidget selection without triggering recordSelected recursively."""
        self._populating_list = True
        try:
            for row in range(self.trace_list.count()):
                item = self.trace_list.item(row)
                if item.data(Qt.ItemDataRole.UserRole) == record_id:
                    self.trace_list.setCurrentRow(row)
                    break
        finally:
            self._populating_list = False

    def update_record_label(self, record: ERGSessionRecord) -> None:
        self._populating_list = True
        try:
            for row in range(self.trace_list.count()):
                item = self.trace_list.item(row)
                if item.data(Qt.ItemDataRole.UserRole) == record.record_id:
                    item.setText(self._format_item_label(record))
                    break
        finally:
            self._populating_list = False

    def set_active_record(self, record: ERGSessionRecord | None) -> None:
        self._active_record = record
        self._populating_fields = True
        try:
            if record is None:
                self.strain_edit.clear()
                self.mouse_id_edit.clear()
                self.age_edit.clear()
                self.protocol_combo.setCurrentIndex(0)
                self.exam_edit.clear()
                self.exam_start_edit.clear()
                self.notes_edit.clear()
                self._set_fields_enabled(False)
            else:
                self._set_fields_enabled(True)
                self.strain_edit.setText(record.metadata.strain_lastname)
                self.mouse_id_edit.setText(record.metadata.mouse_id_name)
                self.age_edit.setText(record.metadata.age)
                proto_idx = self.protocol_combo.findData(record.protocol.value)
                if proto_idx >= 0:
                    self.protocol_combo.setCurrentIndex(proto_idx)
                self.exam_edit.setText(record.metadata.exam)
                self.exam_start_edit.setText(record.metadata.exam_start)
                self.notes_edit.setText(record.metadata.notes)
                for field in (
                    self.strain_edit,
                    self.mouse_id_edit,
                    self.age_edit,
                    self.exam_edit,
                    self.exam_start_edit,
                    self.notes_edit,
                ):
                    field.setCursorPosition(0)
        finally:
            self._populating_fields = False

    def _set_fields_enabled(self, enabled: bool) -> None:
        for widget in (
            self.strain_edit,
            self.mouse_id_edit,
            self.age_edit,
            self.protocol_combo,
            self.exam_edit,
            self.exam_start_edit,
            self.notes_edit,
        ):
            widget.setEnabled(enabled)

    @staticmethod
    def _format_item_label(rec: ERGSessionRecord) -> str:
        eye_tag = " [OD]" if rec.eye == EyeSide.RIGHT_OD else ""
        manual_tag = " · M" if rec.markers.is_manual else ""
        mouse_prefix = f"{rec.metadata.mouse_id_name} — " if rec.metadata.mouse_id_name.strip() else ""
        return f"[{rec.protocol.short_label}]{eye_tag} {mouse_prefix}{rec.file_name}{manual_tag}"

    def _on_protocol_index_changed(self, index: int) -> None:
        if self._populating_fields or self._active_record is None or index < 0:
            return
        raw = self.protocol_combo.itemData(index)
        if not raw:
            return
        try:
            proto = ERGProtocol(str(raw))
        except ValueError:
            return
        if proto != self._active_record.protocol:
            self.protocolChanged.emit(proto)

    def _on_metadata_changed(self) -> None:
        if self._populating_fields or self._active_record is None:
            return
        meta = self._active_record.metadata
        meta.strain_lastname = self.strain_edit.text().strip()
        meta.mouse_id_name = self.mouse_id_edit.text().strip()
        meta.age = self.age_edit.text().strip()
        meta.exam = self.exam_edit.text().strip()
        meta.notes = self.notes_edit.text().strip()
        self.update_record_label(self._active_record)
        self.metadataEdited.emit()

    def _on_current_item_changed(self, current: QListWidgetItem | None, _previous) -> None:
        if self._populating_list or current is None:
            return
        record_id = current.data(Qt.ItemDataRole.UserRole)
        if record_id:
            self.recordSelected.emit(str(record_id))

    def _on_item_check_changed(self, item: QListWidgetItem) -> None:
        if self._populating_list:
            return
        record_id = item.data(Qt.ItemDataRole.UserRole)
        checked = item.checkState() == Qt.CheckState.Checked
        if record_id:
            self.overlayToggled.emit(str(record_id), checked)

    def _on_remove_clicked(self) -> None:
        current = self.trace_list.currentItem()
        if current is None:
            return
        record_id = current.data(Qt.ItemDataRole.UserRole)
        if record_id:
            self.removeRecordRequested.emit(str(record_id))
