from PyQt5 import QtCore, QtWidgets
import ipaddress


class DeviceDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle('Dispositivo ZKTeco')
        self.setModal(True)
        form = QtWidgets.QFormLayout()
        self.name = QtWidgets.QLineEdit()
        self.ip = QtWidgets.QLineEdit()
        self.port = QtWidgets.QSpinBox(); self.port.setRange(1, 65535); self.port.setValue(4370)
        self.password = QtWidgets.QSpinBox(); self.password.setRange(0, 999999); self.password.setValue(0)
        self.enabled = QtWidgets.QCheckBox(); self.enabled.setChecked(True)
        self.zone = QtWidgets.QLineEdit()
        if data:
            self.name.setText(data.get('name',''))
            self.ip.setText(data.get('ip',''))
            self.port.setValue(int(data.get('port', 4370)))
            self.password.setValue(int(data.get('password', 0)))
            self.enabled.setChecked(bool(data.get('enabled', True)))
            self.zone.setText(data.get('zone',''))
        form.addRow('Nombre:', self.name)
        form.addRow('IP:', self.ip)
        form.addRow('Puerto:', self.port)
        form.addRow('Password:', self.password)
        form.addRow('Habilitada:', self.enabled)
        form.addRow('Zona:', self.zone)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(btns)

    def _on_accept(self):
        # Validaciones
        try:
            ipaddress.ip_address(self.ip.text().strip())
        except Exception:
            QtWidgets.QMessageBox.warning(self, 'Validación', 'IP inválida')
            return
        self.accept()

    def get_data(self):
        return {
            'name': self.name.text().strip() or f"ZK-{self.ip.text().strip()}",
            'ip': self.ip.text().strip(),
            'port': int(self.port.value()),
            'password': int(self.password.value()),
            'enabled': self.enabled.isChecked(),
            'zone': self.zone.text().strip(),
        }
