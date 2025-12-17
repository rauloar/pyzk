from PyQt5 import QtWidgets


class ReportsCard(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QFormLayout(self)
        self.from_date = QtWidgets.QDateEdit(); self.from_date.setCalendarPopup(True)
        self.to_date = QtWidgets.QDateEdit(); self.to_date.setCalendarPopup(True)
        self.btn_export = QtWidgets.QPushButton('Exportar')
        layout.addRow('Desde:', self.from_date)
        layout.addRow('Hasta:', self.to_date)
        layout.addRow(self.btn_export)
