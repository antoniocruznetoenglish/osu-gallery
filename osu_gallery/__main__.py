"""osu gallery — a visual reference library for osu! beatmap objects."""

from __future__ import annotations

import sys
import traceback

from osu_gallery._logging import setup_logging


def _show_fatal_error(title: str, message: str) -> None:
    """Display a fatal error to the user.

    Tries a QMessageBox if Qt is available; falls back to stderr.
    """
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv[:1])
        box = QMessageBox()
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle(title)
        box.setText(message)
        box.setDetailedText(traceback.format_exc())
        box.exec()
    except Exception:
        print(f"Fatal error: {title}\n{message}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)


def main() -> None:
    logger = setup_logging()
    logger.info("osu gallery starting")

    try:
        from PySide6.QtWidgets import QApplication

        from osu_gallery._constants import APP_NAME
        from osu_gallery.db.database import get_data_dir

        app = QApplication(sys.argv)
        app.setApplicationName(APP_NAME)
        app.setOrganizationName(APP_NAME)

        # Ensure the data directory (and log file location) exist.
        get_data_dir()
        logger.info("data directory ready: %s", get_data_dir())

        from osu_gallery.ui.main_window import MainWindow

        window = MainWindow()
        window.show()
        sys.exit(app.exec())

    except ImportError as err:
        _show_fatal_error(
            "Missing dependency",
            (
                f"osu gallery could not import a required module.\n\n"
                f"Details: {err}\n\n"
                f"Make sure PySide6 is installed: pip install PySide6"
            ),
        )
        sys.exit(1)

    except OSError as err:
        _show_fatal_error(
            "Qt plugin error",
            (
                f"Qt could not load a required plugin.\n\n"
                f"Details: {err}\n\n"
                f"Check osu_gallery.log for more information."
            ),
        )
        sys.exit(1)

    except Exception as err:
        logger.exception("Unhandled exception during startup")
        _show_fatal_error(
            "Unexpected error",
            f"osu gallery encountered an unexpected error:\n\n{err}",
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
