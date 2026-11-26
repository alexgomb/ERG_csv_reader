"""Light (Retimax-inspired clinical) and Dark (clinical slate) themes for PySide6 & PyQtGraph."""

from __future__ import annotations

from dataclasses import dataclass

SUPPORTED_THEMES = ("light", "dark")


@dataclass(frozen=True)
class PlotPalette:
    """Colors used by the PyQtGraph waveform canvas and Retimax metrics table."""

    background: str
    axis: str
    grid: str
    zero_line: str
    primary_trace: str
    primary_badge_bg: str
    primary_badge_fg: str
    overlay_traces: tuple[str, ...]
    marker_a1: str
    marker_b1: str
    marker_c1: str
    marker_border: str
    marker_label_bg: str
    highlight_bg: str
    highlight_fg: str
    text_primary: str
    text_muted: str
    surface: str
    border: str


LIGHT_PLOT_PALETTE = PlotPalette(
    background="#FFFFFF",
    axis="#1E293B",
    grid="#CBD5E1",
    zero_line="#94A3B8",
    primary_trace="#0038E8",
    primary_badge_bg="#0038E8",
    primary_badge_fg="#FFFFFF",
    overlay_traces=("#94A3B8", "#64748B", "#A78BFA", "#F59E0B", "#10B981"),
    marker_a1="#DC2626",
    marker_b1="#0038E8",
    marker_c1="#0D9488",
    marker_border="#FFFFFF",
    marker_label_bg="#FFFFFFDD",
    highlight_bg="#FFF15C",
    highlight_fg="#0F172A",
    text_primary="#0F172A",
    text_muted="#475569",
    surface="#F8FAFC",
    border="#CBD5E1",
)

DARK_PLOT_PALETTE = PlotPalette(
    background="#0B1120",
    axis="#CBD5E1",
    grid="#334155",
    zero_line="#64748B",
    primary_trace="#38BDF8",
    primary_badge_bg="#0284C7",
    primary_badge_fg="#F8FAFC",
    overlay_traces=("#64748B", "#94A3B8", "#C084FC", "#FBBF24", "#34D399"),
    marker_a1="#F87171",
    marker_b1="#38BDF8",
    marker_c1="#2DD4BF",
    marker_border="#0B1120",
    marker_label_bg="#0F172ADD",
    highlight_bg="#FACC15",
    highlight_fg="#0F172A",
    text_primary="#F1F5F9",
    text_muted="#94A3B8",
    surface="#1E293B",
    border="#334155",
)


def get_plot_palette(theme: str) -> PlotPalette:
    return DARK_PLOT_PALETTE if theme == "dark" else LIGHT_PLOT_PALETTE


def get_stylesheet(theme: str) -> str:
    """Return complete QSS stylesheet for either 'light' or 'dark' mode."""
    if theme == "dark":
        return _DARK_QSS
    return _LIGHT_QSS


_LIGHT_QSS = """
QMainWindow, QDialog {
    background-color: #EFF3F8;
    color: #0F172A;
    font-family: "Segoe UI", "Inter", "DejaVu Sans", sans-serif;
    font-size: 12px;
}

QMenuBar {
    background-color: #FFFFFF;
    color: #0F172A;
    border-bottom: 1px solid #CBD5E1;
    padding: 2px 6px;
}

QMenuBar::item {
    padding: 5px 10px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #E2E8F0;
}

QMenu {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #CBD5E1;
    padding: 4px;
}

QMenu::item {
    padding: 6px 24px 6px 14px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #DBEAFE;
    color: #1E3A8A;
}

QMenu::separator {
    height: 1px;
    background: #E2E8F0;
    margin: 4px 8px;
}

QFrame#SidebarPanel, QFrame#ControlsPanel, QFrame#PlotCard, QFrame#TableCard, QFrame#FlickerCard {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
}

QScrollArea#ControlsScrollArea, QWidget#ControlsContainer {
    background-color: transparent;
    border: none;
}

QFrame#HeaderBanner {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
}

QGroupBox {
    font-weight: 600;
    color: #1E293B;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    margin-top: 10px;
    padding: 10px 8px 8px 8px;
    background-color: #FAFCFF;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: #1E3A8A;
}

QLabel {
    color: #0F172A;
    background: transparent;
}

QLabel#MutedLabel, QLabel#AuthorFooter {
    color: #64748B;
    font-size: 11px;
}

QLabel#AppBrandTitle {
    color: #1E3A8A;
    font-size: 15px;
    font-weight: 700;
}

QLabel#EyeBadgeOS {
    background-color: #DBEAFE;
    color: #1D4ED8;
    border: 1px solid #93C5FD;
    border-radius: 4px;
    padding: 2px 8px;
    font-weight: 700;
    font-size: 11px;
}

QLabel#EyeBadgeOD {
    background-color: #FEF3C7;
    color: #B45309;
    border: 1px solid #FCD34D;
    border-radius: 4px;
    padding: 2px 8px;
    font-weight: 700;
    font-size: 11px;
}

QLabel#ProtocolBadge {
    background-color: #E2E8F0;
    color: #1E293B;
    border-radius: 4px;
    padding: 2px 8px;
    font-weight: 600;
    font-size: 11px;
}

QLabel#MarkerModeAuto {
    color: #047857;
    background-color: #D1FAE5;
    border-radius: 4px;
    padding: 2px 8px;
    font-weight: 600;
    font-size: 11px;
}

QLabel#MarkerModeManual {
    color: #B45309;
    background-color: #FEF3C7;
    border-radius: 4px;
    padding: 2px 8px;
    font-weight: 600;
    font-size: 11px;
}

QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #CBD5E1;
    border-radius: 5px;
    padding: 4px 7px;
    min-height: 22px;
}

QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus {
    border: 1px solid #2563EB;
}

QLineEdit:read-only {
    background-color: #F1F5F9;
    color: #475569;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QPushButton {
    background-color: #F8FAFC;
    color: #0F172A;
    border: 1px solid #CBD5E1;
    border-radius: 5px;
    padding: 4px 7px;
    font-weight: 500;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #EFF6FF;
    border-color: #93C5FD;
    color: #1D4ED8;
}

QPushButton:pressed {
    background-color: #DBEAFE;
}

QPushButton:checked {
    background-color: #1D4ED8;
    color: #FFFFFF;
    border-color: #1D4ED8;
}

QPushButton#PrimaryButton {
    background-color: #1D4ED8;
    color: #FFFFFF;
    border: 1px solid #1E40AF;
    font-weight: 600;
}

QPushButton#PrimaryButton:hover {
    background-color: #1E40AF;
}

QPushButton:disabled {
    background-color: #F1F5F9;
    color: #94A3B8;
    border-color: #E2E8F0;
}

QListWidget {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    outline: none;
    padding: 2px;
}

QListWidget::item {
    padding: 6px 6px;
    border-radius: 4px;
    margin: 1px 0;
}

QListWidget::item:hover {
    background-color: #F1F5F9;
}

QListWidget::item:selected {
    background-color: #DBEAFE;
    color: #1E3A8A;
    font-weight: 600;
}

QTableWidget {
    background-color: #FFFFFF;
    color: #0F172A;
    gridline-color: #CBD5E1;
    border: 1px solid #CBD5E1;
    border-radius: 5px;
    selection-background-color: #DBEAFE;
    selection-color: #0F172A;
}

QHeaderView::section {
    background-color: #F1F5F9;
    color: #0F172A;
    font-weight: 700;
    padding: 5px 8px;
    border: none;
    border-right: 1px solid #CBD5E1;
    border-bottom: 1px solid #CBD5E1;
}

QCheckBox {
    color: #0F172A;
    spacing: 6px;
}

QStatusBar {
    background-color: #FFFFFF;
    color: #475569;
    border-top: 1px solid #CBD5E1;
}

QScrollBar:vertical {
    background: #F1F5F9;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: #CBD5E1;
    border-radius: 5px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background: #94A3B8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

_DARK_QSS = """
QMainWindow, QDialog {
    background-color: #0F172A;
    color: #F1F5F9;
    font-family: "Segoe UI", "Inter", "DejaVu Sans", sans-serif;
    font-size: 12px;
}

QMenuBar {
    background-color: #1E293B;
    color: #F1F5F9;
    border-bottom: 1px solid #334155;
    padding: 2px 6px;
}

QMenuBar::item {
    padding: 5px 10px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #334155;
}

QMenu {
    background-color: #1E293B;
    color: #F1F5F9;
    border: 1px solid #334155;
    padding: 4px;
}

QMenu::item {
    padding: 6px 24px 6px 14px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #0284C7;
    color: #FFFFFF;
}

QMenu::separator {
    height: 1px;
    background: #334155;
    margin: 4px 8px;
}

QFrame#SidebarPanel, QFrame#ControlsPanel, QFrame#PlotCard, QFrame#TableCard, QFrame#FlickerCard {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 8px;
}

QScrollArea#ControlsScrollArea, QWidget#ControlsContainer {
    background-color: transparent;
    border: none;
}

QFrame#HeaderBanner {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 8px;
}

QGroupBox {
    font-weight: 600;
    color: #E2E8F0;
    border: 1px solid #334155;
    border-radius: 6px;
    margin-top: 10px;
    padding: 10px 8px 8px 8px;
    background-color: #162032;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: #38BDF8;
}

QLabel {
    color: #F1F5F9;
    background: transparent;
}

QLabel#MutedLabel, QLabel#AuthorFooter {
    color: #94A3B8;
    font-size: 11px;
}

QLabel#AppBrandTitle {
    color: #38BDF8;
    font-size: 15px;
    font-weight: 700;
}

QLabel#EyeBadgeOS {
    background-color: #0C4A6E;
    color: #7DD3FC;
    border: 1px solid #0284C7;
    border-radius: 4px;
    padding: 2px 8px;
    font-weight: 700;
    font-size: 11px;
}

QLabel#EyeBadgeOD {
    background-color: #78350F;
    color: #FDE68A;
    border: 1px solid #D97706;
    border-radius: 4px;
    padding: 2px 8px;
    font-weight: 700;
    font-size: 11px;
}

QLabel#ProtocolBadge {
    background-color: #334155;
    color: #E2E8F0;
    border-radius: 4px;
    padding: 2px 8px;
    font-weight: 600;
    font-size: 11px;
}

QLabel#MarkerModeAuto {
    color: #6EE7B7;
    background-color: #064E3B;
    border-radius: 4px;
    padding: 2px 8px;
    font-weight: 600;
    font-size: 11px;
}

QLabel#MarkerModeManual {
    color: #FDE68A;
    background-color: #78350F;
    border-radius: 4px;
    padding: 2px 8px;
    font-weight: 600;
    font-size: 11px;
}

QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox {
    background-color: #0F172A;
    color: #F1F5F9;
    border: 1px solid #475569;
    border-radius: 5px;
    padding: 4px 7px;
    min-height: 22px;
}

QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus {
    border: 1px solid #38BDF8;
}

QLineEdit:read-only {
    background-color: #162032;
    color: #94A3B8;
}

QComboBox QAbstractItemView {
    background-color: #1E293B;
    color: #F1F5F9;
    selection-background-color: #0284C7;
}

QPushButton {
    background-color: #0F172A;
    color: #E2E8F0;
    border: 1px solid #475569;
    border-radius: 5px;
    padding: 4px 7px;
    font-weight: 500;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #1E3A5F;
    border-color: #38BDF8;
    color: #FFFFFF;
}

QPushButton:pressed {
    background-color: #0284C7;
}

QPushButton:checked {
    background-color: #0284C7;
    color: #FFFFFF;
    border-color: #38BDF8;
}

QPushButton#PrimaryButton {
    background-color: #0284C7;
    color: #FFFFFF;
    border: 1px solid #38BDF8;
    font-weight: 600;
}

QPushButton#PrimaryButton:hover {
    background-color: #0369A1;
}

QPushButton:disabled {
    background-color: #162032;
    color: #64748B;
    border-color: #334155;
}

QListWidget {
    background-color: #0F172A;
    color: #E2E8F0;
    border: 1px solid #334155;
    border-radius: 6px;
    outline: none;
    padding: 2px;
}

QListWidget::item {
    padding: 6px 6px;
    border-radius: 4px;
    margin: 1px 0;
}

QListWidget::item:hover {
    background-color: #1E293B;
}

QListWidget::item:selected {
    background-color: #0C4A6E;
    color: #E0F2FE;
    font-weight: 600;
}

QTableWidget {
    background-color: #0F172A;
    color: #F1F5F9;
    gridline-color: #334155;
    border: 1px solid #334155;
    border-radius: 5px;
    selection-background-color: #0C4A6E;
    selection-color: #F1F5F9;
}

QHeaderView::section {
    background-color: #162032;
    color: #E2E8F0;
    font-weight: 700;
    padding: 5px 8px;
    border: none;
    border-right: 1px solid #334155;
    border-bottom: 1px solid #334155;
}

QCheckBox {
    color: #E2E8F0;
    spacing: 6px;
}

QStatusBar {
    background-color: #1E293B;
    color: #94A3B8;
    border-top: 1px solid #334155;
}

QScrollBar:vertical {
    background: #0F172A;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: #475569;
    border-radius: 5px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background: #64748B;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""
