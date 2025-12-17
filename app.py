from PyQt5 import QtWidgets
import sys
from ui.main_window import MainWindow
from data.db import init_db


def main() -> int:
    init_db()
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec_()


if __name__ == '__main__':
    raise SystemExit(main())
