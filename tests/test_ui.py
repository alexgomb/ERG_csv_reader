"""Headless PySide6 integration tests for MainWindow UI workflows."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from erg_reader.ui.main_window import MainWindow


def test_mainwindow_load_examples_switch_lang_and_theme(qtbot) -> None:
    win = MainWindow(use_settings=False, initial_language="en", initial_theme="light")
    qtbot.addWidget(win)

    assert win.current_language == "en"
    assert win.current_theme == "light"
    assert "nBio ERG-Trace" in win.windowTitle()

    win.load_example_files()
    assert len(win.records) == 4
    assert win.active_record is not None

    # Switch to Spanish and Dark Mode live
    win.set_language("es", persist=False)
    win.apply_theme("dark", persist=False)
    assert win.current_language == "es"
    assert win.current_theme == "dark"
    assert "nBio ERG-Trace" in win.windowTitle()
    assert "Analizador" in win.windowTitle()
    assert "Cargadas 4 curva(s)" in win.status_bar.currentMessage()

    # Select Flicker trace and confirm Flicker metrics bar becomes visible
    flicker = next(r for r in win.records if "Flicker" in r.file_name)
    win.select_record(flicker.record_id)
    assert win.metrics_panel.flicker_card.isVisibleTo(win.metrics_panel)

    # Select Dark-Adapted 3 trace and confirm Flicker bar hides
    da3 = next(r for r in win.records if "Dark-Adapted_3" in r.file_name)
    win.select_record(da3.record_id)
    assert not win.metrics_panel.flicker_card.isVisibleTo(win.metrics_panel)


def test_mainwindow_manual_marker_drag_reset_and_overlay(qtbot, tmp_path: Path) -> None:
    win = MainWindow(use_settings=False, initial_language="en", initial_theme="light")
    qtbot.addWidget(win)
    win.load_example_files()

    da3 = next(r for r in win.records if "Dark-Adapted_3" in r.file_name)
    da10 = next(r for r in win.records if "Dark-Adapted_10" in r.file_name)
    win.select_record(da3.record_id)

    orig_b1 = da3.markers.b1_idx
    # Simulate dragging B1 marker line to 48.83 ms
    b1_line = win.plot_panel._marker_lines["b1"]
    b1_line.setValue(48.83)
    win.plot_panel._on_line_dragged("b1", b1_line)

    assert da3.markers.is_manual is True
    assert da3.markers.b1_idx != orig_b1
    assert win.metrics_panel.table.item(0, 2).text() == "200.05"

    # Toggle reference overlay
    win.toggle_overlay(da10.record_id, True)
    assert len(win._overlay_records()) == 1

    # Export plot to PNG and SVG
    png_out = win.plot_panel.export_plot(tmp_path / "trace.png")
    svg_out = win.plot_panel.export_plot(tmp_path / "trace.svg")
    assert png_out.is_file() and png_out.stat().st_size > 1000
    assert svg_out.is_file() and svg_out.stat().st_size > 500

    # Reset markers back to automatic detection
    win.reset_active_markers()
    assert da3.markers.is_manual is False
    assert da3.markers.b1_idx == orig_b1


def test_umh_nbio_svg_branding_and_about_dialog(qtbot) -> None:
    from PySide6.QtWidgets import QLabel

    from erg_reader.i18n import Translator
    from erg_reader.ui.branding import render_umh_nbio_pixmap
    from erg_reader.ui.dialogs import AboutDialog

    for dark in (False, True):
        pix = render_umh_nbio_pixmap(width=256, dark_mode=dark)
        assert not pix.isNull()
        assert pix.width() > 200

    for lang in ("en", "es"):
        dlg = AboutDialog(Translator(lang), theme="light")
        qtbot.addWidget(dlg)
        texts = " ".join(lbl.text() for lbl in dlg.findChildren(QLabel))
        assert "Grupo nBio" in texts
        assert "Instituto de Bioingeniería" in texts
        assert "Universidad Miguel Hernández" in texts

