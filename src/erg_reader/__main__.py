"""Allow running the application via `python -m erg_reader`."""

from erg_reader.app import main

if __name__ == "__main__":
    raise SystemExit(main())
