from PyQt5 import QtWidgets
from typing import Optional
from data.db import init_db
from data.repositories import EmployeeRepository, DeviceRepository
from data.models import Employee
from workers.base_worker import run_in_thread
from workers.zk_workers import DownloadUsersWorker
from services.zk_service import ZKService


class EmployeeCard(QtWidgets.QWidget):
    def __init__(self, zk: ZKService, parent=None):
        super().__init__(parent)
        init_db()
        self.zk = zk
        self.repo = EmployeeRepository()
        self.dev_repo = DeviceRepository()
        self._build_ui()
        self._load()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        toolbar = QtWidgets.QHBoxLayout()
        self.btn_import = QtWidgets.QPushButton('Importar desde dispositivo')
        self.btn_upload = QtWidgets.QPushButton('Subir al dispositivo')
        self.btn_edit = QtWidgets.QPushButton('Editar')
        self.btn_refresh = QtWidgets.QPushButton('Refrescar')
        self.btn_export = QtWidgets.QPushButton('Exportar CSV')
        toolbar.addWidget(self.btn_import)
        toolbar.addWidget(self.btn_upload)
        toolbar.addWidget(self.btn_edit)
        toolbar.addWidget(self.btn_refresh)
        toolbar.addWidget(self.btn_export)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)
        self.table = QtWidgets.QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(['ID','User ID','Nombre','Tarjeta','Password','Privilegio','Grupo','Departamento'])
        self.table.setColumnHidden(0, True)
        header = self.table.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(True)
        layout.addWidget(self.table)
        self.btn_export.clicked.connect(self._export_csv)
        self.btn_refresh.clicked.connect(self._load)
        self.btn_import.clicked.connect(self._on_import)
        self.btn_edit.clicked.connect(self._on_edit)
        self.btn_upload.clicked.connect(self._on_upload)

    def _load(self):
        self.table.setRowCount(0)
        for e in self.repo.list():
            r = self.table.rowCount(); self.table.insertRow(r)
            self.table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(e.id or '')))
            self.table.setItem(r, 1, QtWidgets.QTableWidgetItem(e.user_id))
            self.table.setItem(r, 2, QtWidgets.QTableWidgetItem(e.name))
            self.table.setItem(r, 3, QtWidgets.QTableWidgetItem(e.card))
            self.table.setItem(r, 4, QtWidgets.QTableWidgetItem(e.password))
            self.table.setItem(r, 5, QtWidgets.QTableWidgetItem(self._priv_to_text(e.privilege)))
            self.table.setItem(r, 6, QtWidgets.QTableWidgetItem(e.group_id))
            self.table.setItem(r, 7, QtWidgets.QTableWidgetItem(e.dept))

    def _export_csv(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Guardar CSV', 'empleados.csv', 'CSV (*.csv)')
        if not path:
            return
        import csv
        with open(path, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['user_id','name','card','password','privilege','group_id','dept'])
            for r in range(self.table.rowCount()):
                user_id = self.table.item(r,1).text() if self.table.item(r,1) else ''
                name = self.table.item(r,2).text() if self.table.item(r,2) else ''
                card = self.table.item(r,3).text() if self.table.item(r,3) else ''
                pwd = self.table.item(r,4).text() if self.table.item(r,4) else ''
                privilege = self.table.item(r,5).text() if self.table.item(r,5) else ''
                group_id = self.table.item(r,6).text() if self.table.item(r,6) else ''
                dept = self.table.item(r,7).text() if self.table.item(r,7) else ''
                w.writerow([user_id, name, card, pwd, privilege, group_id, dept])
        QtWidgets.QMessageBox.information(self, 'Exportar', 'CSV exportado')

    def _priv_to_text(self, priv) -> str:
        try:
            from zk.const import USER_ADMIN
            if priv == USER_ADMIN:
                return 'Administrador'
        except Exception:
            pass
        return 'Usuario Normal'

    def _text_to_priv(self, text: str) -> int:
        from zk.const import USER_ADMIN, USER_DEFAULT
        return USER_ADMIN if text == 'Administrador' else USER_DEFAULT

    def _selected_employee_id(self) -> Optional[int]:
        sm = self.table.selectionModel()
        sel = sm.selectedRows() if sm else []
        if not sel:
            return None
        row = sel[0].row()
        id_item = self.table.item(row, 0)
        if not id_item or not id_item.text().strip():
            return None
        try:
            return int(id_item.text())
        except Exception:
            return None

    def _on_edit(self):
        emp_id = self._selected_employee_id()
        if not emp_id:
            QtWidgets.QMessageBox.warning(self, 'Editar', 'Selecciona un usuario')
            return
        emp = self.repo.get(emp_id)
        if not emp:
            return
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle('Editar usuario')
        form = QtWidgets.QFormLayout(dlg)
        ed_user = QtWidgets.QLineEdit(emp.user_id)
        ed_name = QtWidgets.QLineEdit(emp.name)
        ed_card = QtWidgets.QLineEdit(str(emp.card or ''))
        ed_pwd = QtWidgets.QLineEdit(emp.password or '')
        cb_priv = QtWidgets.QComboBox(); cb_priv.addItems(['Usuario Normal','Administrador'])
        cb_priv.setCurrentText(self._priv_to_text(emp.privilege))
        ed_group = QtWidgets.QLineEdit(emp.group_id or '')
        ed_dept = QtWidgets.QLineEdit(emp.dept or '')
        form.addRow('User ID', ed_user)
        form.addRow('Nombre', ed_name)
        form.addRow('Tarjeta', ed_card)
        form.addRow('Password', ed_pwd)
        form.addRow('Privilegio', cb_priv)
        form.addRow('Grupo', ed_group)
        form.addRow('Departamento', ed_dept)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        form.addRow(btns)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            emp.user_id = ed_user.text().strip()
            emp.name = ed_name.text().strip()
            emp.card = ed_card.text().strip()
            emp.password = ed_pwd.text().strip()
            emp.privilege = self._text_to_priv(cb_priv.currentText())
            emp.group_id = ed_group.text().strip()
            emp.dept = ed_dept.text().strip()
            self.repo.update(emp)
            self._load()

    def _on_upload(self):
        emp_id = self._selected_employee_id()
        if not emp_id:
            QtWidgets.QMessageBox.warning(self, 'Subir', 'Selecciona un usuario')
            return
        emp = self.repo.get(emp_id)
        if not emp:
            return
        picked = self._pick_device()
        if not picked:
            return
        device_id, device_name, ip, port, password = picked
        from workers.zk_workers import UploadUserWorker
        worker = UploadUserWorker(self.zk, ip, port, emp)
        worker.result.connect(lambda _: QtWidgets.QMessageBox.information(self, 'Subir', f'Usuario actualizado en {device_name}'))
        worker.error.connect(lambda e: QtWidgets.QMessageBox.critical(self, 'Subir', e))
        run_in_thread(worker)

    def _pick_device(self) -> Optional[tuple]:
        devices = self.dev_repo.list()
        if not devices:
            QtWidgets.QMessageBox.warning(self, 'Importar', 'No hay dispositivos configurados')
            return None
        if len(devices) == 1:
            d = devices[0]
            return (d.id, d.name, d.ip, d.port, int(d.password or 0))
        items = [f"{d.name} ({d.ip}:{d.port})" for d in devices]
        item, ok = QtWidgets.QInputDialog.getItem(self, 'Seleccionar dispositivo', 'Dispositivo:', items, 0, False)
        if not ok or not item:
            return None
        idx = items.index(item)
        d = devices[idx]
        return (d.id, d.name, d.ip, d.port, int(d.password or 0))

    def _on_import(self):
        picked = self._pick_device()
        if not picked:
            return
        device_id, device_name, ip, port, password = picked
        worker = DownloadUsersWorker(self.zk, ip, port)
        def on_result(users):
            try:
                employees = []
                for u in users or []:
                    # u may be a dict or zk.User
                    if hasattr(u, '__dict__'):
                        uid = getattr(u, 'uid', None)
                        name = getattr(u, 'name', '') or ''
                        privilege = getattr(u, 'privilege', None)
                        password_u = getattr(u, 'password', '') or ''
                        group_id = str(getattr(u, 'group_id', '') or '')
                        user_id = str(getattr(u, 'user_id', '') or '')
                        card = str(getattr(u, 'card', '') or '')
                    else:
                        uid = u.get('uid')
                        name = u.get('name') or ''
                        privilege = u.get('privilege')
                        password_u = u.get('password') or ''
                        group_id = str(u.get('group_id') or '')
                        user_id = str(u.get('user_id') or '')
                        card = str(u.get('card') or '')
                    employees.append(Employee(id=None, user_id=user_id, uid=uid, name=name, card=card, password=password_u, privilege=privilege, group_id=group_id))
                if employees:
                    self.repo.upsert_many(employees)
                QtWidgets.QMessageBox.information(self, 'Importar', f'Importados {len(employees)} usuarios desde {device_name}')
                self._load()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, 'Importar', str(e))
        worker.result.connect(on_result)
        worker.error.connect(lambda e: QtWidgets.QMessageBox.critical(self, 'Importar', e))
        run_in_thread(worker)
