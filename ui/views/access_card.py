from PyQt5 import QtWidgets, QtCore


class AccessCard(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        title = QtWidgets.QLabel('Módulo de Acceso')
        title.setStyleSheet('font-weight: bold;')
        layout.addWidget(title)
        layout.addWidget(QtWidgets.QLabel('Funciones de control de acceso (placeholder)'))
        layout.addStretch(1)
