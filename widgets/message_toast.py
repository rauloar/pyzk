from PyQt5 import QtCore, QtWidgets


class MessageToast(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Keep as a child widget to avoid Windows geometry warnings for tool windows
        # and show without taking focus.
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setStyleSheet("""
            QFrame { background: rgba(30,30,30,220); color: white; border-radius: 6px; }
            QLabel { color: white; }
        """)
        self.setVisible(False)
        self.setMaximumWidth(420)
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(4000)
        self._timer.timeout.connect(self.hide)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        self.title = QtWidgets.QLabel("Mensajes")
        self.title.setStyleSheet("font-weight: bold;")
        self.text = QtWidgets.QLabel("")
        self.text.setWordWrap(True)
        self.btn_history = QtWidgets.QPushButton("Historial")
        self.btn_history.setFlat(True)
        self.btn_history.setStyleSheet("color: #8bd18b;")
        self.btn_history.clicked.connect(self._toggle_history)
        self.history = QtWidgets.QTextEdit()
        self.history.setReadOnly(True)
        self.history.setVisible(False)
        layout.addWidget(self.title)
        layout.addWidget(self.text)
        layout.addWidget(self.btn_history)
        layout.addWidget(self.history)

    def show_message(self, message: str, level: str = "INFO", auto_hide: bool = True):
        prefix = {"INFO": "ℹ", "WARN": "⚠", "ERROR": "✖"}.get(level, "ℹ")
        self.text.setText(f"{prefix} {message}")
        self._append_history(message, level)
        self._reposition()
        self.show()
        if auto_hide:
            self._timer.start()
        else:
            self._timer.stop()

    def _append_history(self, message: str, level: str):
        self.history.append(f"[{level}] {message}")

    def _toggle_history(self):
        self.history.setVisible(not self.history.isVisible())
        self._reposition()

    def _reposition(self):
        parent = self.parentWidget()
        if not parent:
            return
        self.adjustSize()
        margin = 16
        # Anchor to parent's bottom-right within parent coordinates
        pr = parent.rect()
        target_w = min(self.sizeHint().width(), self.maximumWidth())
        self.resize(target_w, self.sizeHint().height())
        self.adjustSize()
        x = pr.right() - self.width() - margin
        y = pr.bottom() - self.height() - margin
        # Clamp inside parent rect
        x = max(pr.left() + margin, min(x, pr.right() - self.width() - margin))
        y = max(pr.top() + margin, min(y, pr.bottom() - self.height() - margin))
        self.move(x, y)
