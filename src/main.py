"""PassXMP entry point — launches the GUI application."""

import sys

from PyQt6.QtWidgets import QApplication

from .app import PassXMPApp


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PassXMP")
    app.setOrganizationName("PassXMP")
    app.setQuitOnLastWindowClosed(False)  # Keep running in tray

    passxmp = PassXMPApp()
    passxmp.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
