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


_GITHUB_SVG_PATH = (
    "M12 0.5C5.65 0.5 0.5 5.65 0.5 12c0 5.08 3.29 9.39 7.86 10.91.58.11.79-.25.79-.56 "
    "0-.28-.01-1.02-.02-2-3.2.7-3.88-1.54-3.88-1.54-.52-1.33-1.28-1.69-1.28-1.69-1.05-.72.08-.7.08-.7 "
    "1.16.08 1.77 1.19 1.77 1.19 1.03 1.77 2.71 1.26 3.37.96.1-.75.4-1.26.73-1.55-2.55-.29-5.24-1.28-5.24-5.69 "
    "0-1.26.45-2.29 1.19-3.09-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.18 1.18a11.08 11.08 0 0 1 5.79 0 "
    "c2.21-1.49 3.18-1.18 3.18-1.18.63 1.59.23 2.76.11 3.05.74.8 1.19 1.83 1.19 3.09 0 4.42-2.69 5.39-5.26 5.68 "
    ".41.36.78 1.06.78 2.13 0 1.54-.01 2.78-.01 3.16 0 .31.21.67.8.56A11.51 11.51 0 0 0 23.5 12 "
    "C23.5 5.65 18.35 0.5 12 0.5Z"
)

_LINKEDIN_SVG_PATH = (
    "M20.45 2H3.55A1.55 1.55 0 0 0 2 3.55v16.9A1.55 1.55 0 0 0 3.55 22h16.9A1.55 1.55 0 0 0 22 20.45V3.55 "
    "A1.55 1.55 0 0 0 20.45 2ZM8.08 19H5.13V9.5h2.95V19ZM6.6 8.2a1.71 1.71 0 1 1 0-3.42 1.71 1.71 0 0 1 0 3.42Z "
    "M19 19h-2.95v-4.62c0-1.1-.02-2.52-1.54-2.52-1.54 0-1.78 1.2-1.78 2.44V19h-2.95V9.5h2.83v1.3h.04 "
    "c.39-.75 1.36-1.54 2.8-1.54 2.99 0 3.55 1.97 3.55 4.53V19Z"
)


def create_social_icon(kind: str, size: int = 18, dark_mode: bool = False) -> QIcon:
    """Render a crisp 2x HiDPI vector icon for GitHub or LinkedIn."""
    if kind == "linkedin":
        color = "#38BDF8" if dark_mode else "#0A66C2"
        path_d = _LINKEDIN_SVG_PATH
    else:
        color = "#F8FAFC" if dark_mode else "#0F172A"
        path_d = _GITHUB_SVG_PATH

    svg_bytes = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">'
        f'<path fill="{color}" d="{path_d}"/>'
        f"</svg>"
    ).encode("utf-8")

    dpr = 2.0
    px = int(round(size * dpr))
    pixmap = QPixmap(px, px)
    pixmap.fill(Qt.GlobalColor.transparent)
    pixmap.setDevicePixelRatio(dpr)

    renderer = QSvgRenderer(svg_bytes)
    if renderer.isValid():
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        renderer.render(painter, QRectF(0.0, 0.0, float(size), float(size)))
        painter.end()

    return QIcon(pixmap)

