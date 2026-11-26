"""Settings (physiological detection windows & eye filter) and About dialogs."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from erg_reader import APP_NAME, REPO_URL, __author__, __license__, __version__
from erg_reader.i18n import Translator
from erg_reader.models import (
    DetectionConfig,
    DetectionWindow,
    ERGProtocol,
    default_detection_windows,
)
from erg_reader.ui.branding import create_erg_pixmap, render_umh_nbio_pixmap

PROTOCOL_ORDER = (
    ERGProtocol.DARK_ADAPTED_3,
    ERGProtocol.DARK_ADAPTED_10,
    ERGProtocol.LIGHT_ADAPTED_3,
    ERGProtocol.LIGHT_ADAPTED_3_FLICKER,
    ERGProtocol.UNKNOWN,
)


class SettingsDialog(QDialog):
    """Dialog for configuring physiological marker windows (ms) and RIGHT - OD filtering."""

    def __init__(self, config: DetectionConfig, translator: Translator, parent=None) -> None:
        super().__init__(parent)
        self._tr = translator
        self._config = DetectionConfig.from_dict(config.to_dict())
        self._spins: dict[ERGProtocol, dict[str, QDoubleSpinBox]] = {}

        self.setWindowTitle(self._tr.tr("settings_title"))
        self.setMinimumWidth(680)
        self._build_ui()
        self._populate_from_config(self._config)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        intro = QLabel(self._tr.tr("settings_intro"))
        intro.setWordWrap(True)
        layout.addWidget(intro)

        # Eye filter group
        eye_group = QGroupBox(self._tr.tr("settings_eye_group"))
        eye_v = QVBoxLayout(eye_group)
        self.include_od_chk = QCheckBox(self._tr.tr("settings_include_od"))
        eye_v.addWidget(self.include_od_chk)
        layout.addWidget(eye_group)

        # Per-protocol search windows grid
        win_group = QGroupBox(self._tr.tr("settings_windows_group"))
        grid = QGridLayout(win_group)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        headers = [
            self._tr.tr("settings_col_protocol"),
            "A1 Min",
            "A1 Max",
            "B1 Min",
            "B1 Max",
            "C1 Min",
            "C1 Max",
        ]
        for col, text in enumerate(headers):
            lbl = QLabel(text)
            font = QFont()
            font.setBold(True)
            lbl.setFont(font)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter if col > 0 else Qt.AlignmentFlag.AlignLeft)
            grid.addWidget(lbl, 0, col)

        fields = ("a_min_ms", "a_max_ms", "b_min_ms", "b_max_ms", "c_min_ms", "c_max_ms")
        for row_idx, proto in enumerate(PROTOCOL_ORDER, start=1):
            proto_lbl = QLabel(self._tr.tr(f"protocol_{proto.value}"))
            grid.addWidget(proto_lbl, row_idx, 0)
            self._spins[proto] = {}
            for col_idx, field_name in enumerate(fields, start=1):
                spin = QDoubleSpinBox()
                spin.setRange(0.0, 500.0)
                spin.setDecimals(1)
                spin.setSingleStep(1.0)
                spin.setFixedWidth(74)
                grid.addWidget(spin, row_idx, col_idx)
                self._spins[proto][field_name] = spin

        layout.addWidget(win_group)

        # Action buttons
        btn_row = QHBoxLayout()
        restore_btn = QPushButton(self._tr.tr("settings_btn_restore"))
        restore_btn.clicked.connect(self._on_restore_defaults)
        btn_row.addWidget(restore_btn)
        btn_row.addStretch(1)

        cancel_btn = QPushButton(self._tr.tr("settings_btn_cancel"))
        cancel_btn.clicked.connect(self.reject)
        apply_btn = QPushButton(self._tr.tr("settings_btn_apply"))
        apply_btn.setObjectName("PrimaryButton")
        apply_btn.clicked.connect(self.accept)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(apply_btn)
        layout.addLayout(btn_row)

    def _populate_from_config(self, cfg: DetectionConfig) -> None:
        self.include_od_chk.setChecked(cfg.include_right_od)
        for proto in PROTOCOL_ORDER:
            win = cfg.get_window(proto)
            spins = self._spins[proto]
            spins["a_min_ms"].setValue(win.a_min_ms)
            spins["a_max_ms"].setValue(win.a_max_ms)
            spins["b_min_ms"].setValue(win.b_min_ms)
            spins["b_max_ms"].setValue(win.b_max_ms)
            spins["c_min_ms"].setValue(win.c_min_ms)
            spins["c_max_ms"].setValue(win.c_max_ms)

    def _on_restore_defaults(self) -> None:
        default_cfg = DetectionConfig(windows=default_detection_windows(), include_right_od=False)
        self._populate_from_config(default_cfg)

    def get_config(self) -> DetectionConfig:
        windows: dict[ERGProtocol, DetectionWindow] = {}
        for proto in PROTOCOL_ORDER:
            s = self._spins[proto]
            a_min, a_max = s["a_min_ms"].value(), s["a_max_ms"].value()
            b_min, b_max = s["b_min_ms"].value(), s["b_max_ms"].value()
            c_min, c_max = s["c_min_ms"].value(), s["c_max_ms"].value()
            windows[proto] = DetectionWindow(
                a_min_ms=min(a_min, a_max),
                a_max_ms=max(a_min, a_max),
                b_min_ms=min(b_min, b_max),
                b_max_ms=max(b_min, b_max),
                c_min_ms=min(c_min, c_max),
                c_max_ms=max(c_min, c_max),
            )
        return DetectionConfig(
            windows=windows,
            include_right_od=self.include_od_chk.isChecked(),
        )


class AboutDialog(QDialog):
    """About dialog showing UMH · nBio vector logo, institutional affiliation, author, and MIT license."""

    def __init__(self, translator: Translator, theme: str = "light", parent=None) -> None:
        super().__init__(parent)
        self._tr = translator
        self.setWindowTitle(self._tr.tr("about_title"))
        self.setMinimumWidth(490)

        is_dark = theme == "dark"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(14)
        logo = QLabel()
        logo.setPixmap(create_erg_pixmap(54, dark_mode=is_dark))
        header.addWidget(logo)

        title_col = QVBoxLayout()
        title_lbl = QLabel(APP_NAME)
        title_lbl.setObjectName("AppBrandTitle")
        subtitle_lbl = QLabel(self._tr.tr("subtitle_badge"))
        subtitle_lbl.setObjectName("MutedLabel")
        title_col.addWidget(title_lbl)
        title_col.addWidget(subtitle_lbl)
        header.addLayout(title_col, stretch=1)
        layout.addLayout(header)

        # Crisp vector UMH · nBio institutional banner
        banner_lbl = QLabel()
        banner_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        banner_lbl.setPixmap(render_umh_nbio_pixmap(width=400, dark_mode=is_dark))
        layout.addWidget(banner_lbl)

        desc = QLabel(self._tr.tr("about_description"))
        desc.setWordWrap(True)
        layout.addWidget(desc)

        info_form = QFormLayout()
        info_form.setVerticalSpacing(5)
        info_form.addRow(self._tr.tr("about_author_label"), QLabel(f"<b>{__author__}</b>"))

        group_lbl = QLabel(self._tr.tr("about_group_value"))
        group_lbl.setWordWrap(True)
        info_form.addRow(self._tr.tr("about_group_label"), group_lbl)

        link_color = "#38BDF8" if is_dark else "#1D4ED8"
        web_lbl = QLabel(
            f"<a href='http://nbio.umh.es' style='color:{link_color};'>http://nbio.umh.es</a>"
        )
        web_lbl.setOpenExternalLinks(True)
        info_form.addRow(self._tr.tr("about_web_label"), web_lbl)

        info_form.addRow(self._tr.tr("about_version_label"), QLabel(f"v{__version__}"))
        info_form.addRow(self._tr.tr("about_license_label"), QLabel(__license__))
        repo_lbl = QLabel(
            f"<a href='{REPO_URL}' style='color:{link_color};'>{REPO_URL}</a>"
        )
        repo_lbl.setOpenExternalLinks(True)
        info_form.addRow(self._tr.tr("about_repo_label"), repo_lbl)
        layout.addLayout(info_form)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        close_btn = QPushButton(self._tr.tr("about_close"))
        close_btn.setObjectName("PrimaryButton")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)
