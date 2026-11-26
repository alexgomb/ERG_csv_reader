"""Application bootstrap and CLI entry point for nBio ERG-Trace."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from erg_reader import APP_NAME, __author__, __version__
from erg_reader.ui.main_window import MainWindow


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nbio-erg-trace",
        description=f"{APP_NAME} v{__version__} — Mouse ERG analyzer for CSO Retimax CSV exports ({__author__})",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional CSV files or folders to load immediately on startup.",
    )
    parser.add_argument(
        "--examples",
        action="store_true",
        help="Load bundled example_files on startup.",
    )
    parser.add_argument(
        "--lang",
        choices=("en", "es"),
        default=None,
        help="Override initial UI language (en or es).",
    )
    parser.add_argument(
        "--theme",
        choices=("light", "dark"),
        default=None,
        help="Override initial UI theme (light or dark).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{APP_NAME} {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("AlejandroGombauGarcia")

    window = MainWindow(
        use_settings=True,
        initial_language=args.lang,
        initial_theme=args.theme,
    )

    if args.examples:
        window.load_example_files()
    elif args.paths:
        window.load_paths([Path(p) for p in args.paths])

    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
