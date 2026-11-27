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
    assert len(win.records) == 5
    assert win.active_record is not None

    # Switch to Spanish and Dark Mode live
    win.set_language("es", persist=False)
    win.apply_theme("dark", persist=False)
    assert win.current_language == "es"
    assert win.current_theme == "dark"
    assert "nBio ERG-Trace" in win.windowTitle()
    assert "Analizador" in win.windowTitle()
    assert "Cargadas 5 curva(s)" in win.status_bar.currentMessage()

    # Select Flicker trace and confirm Flicker metrics bar becomes visible
    flicker = next(r for r in win.records if "Flicker" in r.file_name)
    win.select_record(flicker.record_id)
    assert win.metrics_panel.flicker_card.isVisibleTo(win.metrics_panel)
    assert not win.metrics_panel.op_card.isVisibleTo(win.metrics_panel)

    # Select Oscillatory Potentials trace and confirm OP metrics bar becomes visible
    ops_rec = next(r for r in win.records if "OSCILLATORY" in r.file_name)
    win.select_record(ops_rec.record_id)
    assert win.metrics_panel.op_card.isVisibleTo(win.metrics_panel)
    assert not win.metrics_panel.flicker_card.isVisibleTo(win.metrics_panel)
    assert "66.06" in win.metrics_panel._op_value_widgets["op_sum"].text()

    # Select Dark-Adapted 3 trace and confirm both specialized bars hide
    da3 = next(r for r in win.records if "Dark-Adapted_3_ERG" in r.file_name)
    win.select_record(da3.record_id)
    assert not win.metrics_panel.flicker_card.isVisibleTo(win.metrics_panel)
    assert not win.metrics_panel.op_card.isVisibleTo(win.metrics_panel)


def test_mainwindow_manual_marker_drag_reset_and_overlay(qtbot, tmp_path: Path) -> None:
    win = MainWindow(use_settings=False, initial_language="en", initial_theme="light")
    qtbot.addWidget(win)
    win.load_example_files()

    da3 = next(r for r in win.records if "Dark-Adapted_3_ERG" in r.file_name)
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


def test_manual_protocol_selector_toggles_flicker_and_op_panels(qtbot) -> None:
    from erg_reader.models import ERGProtocol

    win = MainWindow(use_settings=False, initial_language="en", initial_theme="light")
    qtbot.addWidget(win)
    win.load_example_files()

    da3 = next(r for r in win.records if "Dark-Adapted_3_ERG" in r.file_name)
    win.select_record(da3.record_id)
    assert da3.protocol == ERGProtocol.DARK_ADAPTED_3
    assert not win.metrics_panel.flicker_card.isVisibleTo(win.metrics_panel)
    assert not win.metrics_panel.op_card.isVisibleTo(win.metrics_panel)

    # Manually switch protocol to Flicker in the left sidebar combo box
    flk_idx = win.sidebar.protocol_combo.findData(ERGProtocol.LIGHT_ADAPTED_3_FLICKER.value)
    assert flk_idx >= 0
    win.sidebar.protocol_combo.setCurrentIndex(flk_idx)

    assert da3.protocol == ERGProtocol.LIGHT_ADAPTED_3_FLICKER
    assert win.metrics_panel.flicker_card.isVisibleTo(win.metrics_panel)
    assert not win.metrics_panel.op_card.isVisibleTo(win.metrics_panel)
    assert win.plot_panel.protocol_badge.text() == "LIGHT-ADAPTED 3.0 FLICKER ERG"

    # Manually switch protocol to Oscillatory Potentials -> OP panel shows, Flicker hides
    op_idx = win.sidebar.protocol_combo.findData(ERGProtocol.DARK_ADAPTED_3_OPS.value)
    assert op_idx >= 0
    win.sidebar.protocol_combo.setCurrentIndex(op_idx)
    assert da3.protocol == ERGProtocol.DARK_ADAPTED_3_OPS
    assert win.metrics_panel.op_card.isVisibleTo(win.metrics_panel)
    assert not win.metrics_panel.flicker_card.isVisibleTo(win.metrics_panel)
    assert win.plot_panel.protocol_badge.text() == "DARK-ADAPTED 3.0 OSCILLATORY POTENTIALS"

    # Switch back to Dark-Adapted 3.0 and verify both specialized panels hide again
    da3_idx = win.sidebar.protocol_combo.findData(ERGProtocol.DARK_ADAPTED_3.value)
    win.sidebar.protocol_combo.setCurrentIndex(da3_idx)
    assert da3.protocol == ERGProtocol.DARK_ADAPTED_3
    assert not win.metrics_panel.flicker_card.isVisibleTo(win.metrics_panel)
    assert not win.metrics_panel.op_card.isVisibleTo(win.metrics_panel)


def test_mainwindow_edge_cases_removal_channel_scale_settings_and_clipboard(qtbot) -> None:
    from PySide6.QtWidgets import QApplication

    from erg_reader.models import DetectionConfig, ERGProtocol
    from erg_reader.ui.dialogs import SettingsDialog

    win = MainWindow(use_settings=False, initial_language="en", initial_theme="light")
    qtbot.addWidget(win)
    win.load_example_files()
    assert len(win.records) == 5

    # Switch active trace channel (AV1 -> GAV) and ensure metrics stay populated
    win._on_channel_changed("GAV(uV)")
    assert win.active_record is not None
    assert win.active_record.active_channel == "GAV(uV)"

    # Scale, magnifier, grid, and clipboard copy
    win._set_auto_scale(True)
    assert win.plot_panel._auto_scale is True
    win._on_magnifier_changed(2.0)
    assert win.plot_panel._auto_scale is False
    assert win.plot_panel._magnifier == 2.0
    win._apply_retimax_250_scale()
    assert win.plot_panel._magnifier == 1.0
    win._set_grid_visible(False, persist=False)
    assert win.plot_panel._show_grid is False
    win.copy_table_to_clipboard()
    assert "LEFT - OS" in QApplication.clipboard().text()

    # SettingsDialog min > max auto-normalization + restore defaults
    dlg = SettingsDialog(DetectionConfig(), win.translator, parent=win)
    qtbot.addWidget(dlg)
    dlg.include_od_chk.setChecked(True)
    dlg._spins[ERGProtocol.DARK_ADAPTED_3]["a_min_ms"].setValue(50.0)
    dlg._spins[ERGProtocol.DARK_ADAPTED_3]["a_max_ms"].setValue(10.0)
    cfg = dlg.get_config()
    assert cfg.include_right_od is True
    assert cfg.get_window(ERGProtocol.DARK_ADAPTED_3).a_min_ms == 10.0
    assert cfg.get_window(ERGProtocol.DARK_ADAPTED_3).a_max_ms == 50.0
    dlg._on_restore_defaults()
    restored_cfg = dlg.get_config()
    assert restored_cfg.include_right_od is False
    assert restored_cfg.get_window(ERGProtocol.DARK_ADAPTED_3).a_min_ms == 8.0

    # Remove records one by one down to empty state without crashing
    for rec_id in [r.record_id for r in list(win.records)]:
        win.remove_record(rec_id)
    assert win.records == []
    assert win.active_record is None
    assert win.metrics_panel.table.item(0, 1).text() == "—"

    # Removing nonexistent ID or resetting markers on empty state is a safe no-op
    win.remove_record("missing_id")
    win.reset_active_markers()
    win.clear_all_records()


def test_i18n_parity_and_institutional_svg_assets(qtbot):
    import erg_reader
    from erg_reader.i18n import TRANSLATIONS
    from erg_reader.ui.branding import render_umh_nbio_pixmap

    en_keys = set(TRANSLATIONS["en"].keys())
    es_keys = set(TRANSLATIONS["es"].keys())
    assert en_keys == es_keys
    for lang in ("en", "es"):
        for k, v in TRANSLATIONS[lang].items():
            assert isinstance(v, str) and v.strip(), f"Empty translation for {lang}.{k}"

    assets_dir = Path(erg_reader.__file__).resolve().parent / "assets"
    for svg_name in ("umh_nbio_light.svg", "umh_nbio_dark.svg"):
        svg_path = assets_dir / svg_name
        assert svg_path.exists()
        content = svg_path.read_text(encoding="utf-8")
        assert "<svg" in content
        # Pure vector without clipPath/mask for QtSvg Tiny 1.2 compatibility
        assert "<clipPath" not in content

    for dark_mode in (False, True):
        pm = render_umh_nbio_pixmap(width=220, dark_mode=dark_mode)
        assert not pm.isNull()
        assert pm.width() > 0 and pm.height() > 0






