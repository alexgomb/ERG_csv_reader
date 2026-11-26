"""Programmatic vector app icon and UMH · nBio SVG logo renderers for nBio ERG-Trace."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtSvg import QSvgRenderer


def _find_asset_path(filename: str) -> Path | None:
    """Locate bundled SVG asset across editable installs, wheels, and PyInstaller bundles."""
    candidates: list[Path] = []
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS) / "erg_reader" / "assets" / filename)
        candidates.append(Path(sys._MEIPASS) / "assets" / filename)

    candidates.append(Path(__file__).resolve().parents[1] / "assets" / filename)
    for path in candidates:
        if path.is_file():
            return path
    return None


def render_umh_nbio_pixmap(width: int = 250, dark_mode: bool = False) -> QPixmap:
    """Render the crisp vector UMH · nBio SVG logo at 2x HiDPI resolution."""
    svg_name = "umh_nbio_dark.svg" if dark_mode else "umh_nbio_light.svg"
    svg_path = _find_asset_path(svg_name)

    aspect = 102.0 / 426.0
    height = max(24, int(round(width * aspect)))
    dpr = 2.0
    pixmap = QPixmap(int(round(width * dpr)), int(round(height * dpr)))
    pixmap.fill(Qt.GlobalColor.transparent)
    pixmap.setDevicePixelRatio(dpr)

    if svg_path is not None:
        renderer = QSvgRenderer(str(svg_path))
        if renderer.isValid():
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            renderer.render(painter, QRectF(0.0, 0.0, float(width), float(height)))
            painter.end()
    return pixmap


def create_erg_pixmap(size: int = 44, dark_mode: bool = False) -> QPixmap:
    """Render a crisp stylized eye + mouse ERG waveform emblem."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    bg_color = QColor("#0C4A6E") if dark_mode else QColor("#1D4ED8")
    border_color = QColor("#38BDF8") if dark_mode else QColor("#1E3A8A")
    wave_color = QColor("#F8FAFC")
    accent_color = QColor("#AEE033")

    margin = size * 0.06
    rect_size = size - 2 * margin
    radius = size * 0.22

    # Rounded square badge background
    bg_path = QPainterPath()
    bg_path.addRoundedRect(margin, margin, rect_size, rect_size, radius, radius)
    painter.fillPath(bg_path, bg_color)
    painter.setPen(QPen(border_color, max(1.2, size * 0.035)))
    painter.drawPath(bg_path)

    # Stylized ERG waveform (baseline -> a-wave trough -> b-wave peak -> recovery)
    wave = QPainterPath()
    w = float(size)
    wave.moveTo(w * 0.14, w * 0.56)
    wave.lineTo(w * 0.27, w * 0.56)
    wave.lineTo(w * 0.36, w * 0.76)  # A1 trough
    wave.lineTo(w * 0.50, w * 0.22)  # B1 peak
    wave.quadTo(w * 0.62, w * 0.34, w * 0.70, w * 0.56)  # C1 return
    wave.lineTo(w * 0.86, w * 0.56)

    wave_pen = QPen(wave_color, max(2.0, size * 0.065))
    wave_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    wave_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(wave_pen)
    painter.drawPath(wave)

    # Highlight dot on B1 peak (nBio lime accent)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(accent_color)
    dot_r = max(2.2, size * 0.068)
    painter.drawEllipse(QPointF(w * 0.50, w * 0.22), dot_r, dot_r)

    painter.end()
    return pixmap


def create_erg_icon(dark_mode: bool = False) -> QIcon:
    """Create a multi-resolution QIcon for window titlebar and dialogs."""
    icon = QIcon()
    for sz in (24, 32, 48, 64):
        icon.addPixmap(create_erg_pixmap(sz, dark_mode=dark_mode))
    return icon
