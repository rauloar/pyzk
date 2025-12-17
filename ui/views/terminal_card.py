from typing import Optional
from datetime import datetime
from PyQt5 import QtCore, QtWidgets

from data.db import init_db
from data.models import Device
from data.repositories import DeviceRepository, SettingsRepository
from dialogs.device_dialog import DeviceDialog
from workers.base_worker import run_in_thread
from workers.zk_workers import ConnectWorker, DisconnectWorker, DownloadEventsWorker
from services.zk_service import ZKService
from services.download_service import DownloadService
from data.repositories import AttendanceRepository
from widgets.message_toast import MessageToast
from config import CONFIG


class TerminalCard(QtWidgets.QWidget):
    events_saved = QtCore.pyqtSignal(int)
    def __init__(self, zk: ZKService, parent=None):
        super().__init__(parent)
        init_db()
        self.zk = zk
        self.dev_repo = DeviceRepository()
        self.att_repo = AttendanceRepository()
        self.set_repo = SettingsRepository()
        self.download_service = DownloadService(self.zk, self.att_repo)
        self.toast: Optional[MessageToast] = None
        self.statusbar: Optional[QtWidgets.QStatusBar] = None
        self._build_ui()
        self._load_table()
        self._load_settings()

    def attach_toast(self, toast: MessageToast):
        self.toast = toast

    def attach_statusbar(self, statusbar: QtWidgets.QStatusBar):
        self.statusbar = statusbar

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        # Toolbar
        toolbar = QtWidgets.QHBoxLayout()
        self.btn_add = QtWidgets.QPushButton('Agregar dispositivo')
        self.btn_edit = QtWidgets.QPushButton('Editar dispositivo')
        self.btn_connect = QtWidgets.QPushButton('Conectar')
        self.btn_disconnect = QtWidgets.QPushButton('Desconectar')
        self.btn_download = QtWidgets.QPushButton('Descargar eventos')
        self.btn_sync = QtWidgets.QPushButton('Sincronizar datos')
        for b in (self.btn_add, self.btn_edit, self.btn_connect, self.btn_disconnect, self.btn_download, self.btn_sync):
            toolbar.addWidget(b)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)
        # Table
        self.table = QtWidgets.QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(['ID','Nombre','IP','Puerto','Habilitada','Conectado','Última sync','Última descarga','Zona'])
        self.table.setColumnHidden(0, True)
        header = self.table.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        layout.addWidget(self.table)
        # Programación se maneja desde Sistema; aquí solo mostramos tabla y acciones de dispositivo

        # Connections
        self.btn_add.clicked.connect(self._on_add)
        self.btn_edit.clicked.connect(self._on_edit)
        self.btn_connect.clicked.connect(self._on_connect)
        self.btn_disconnect.clicked.connect(self._on_disconnect)
        self.btn_download.clicked.connect(self._on_download)
        self.btn_sync.clicked.connect(self._on_sync)
        # Programación y opciones se configuran en Sistema

        # Timer para programación diaria
        self._daily_timer = QtCore.QTimer(self)
        self._daily_timer.setSingleShot(True)

    def _log(self, msg: str, level: str = 'INFO'):
        if self.toast:
            self.toast.show_message(msg, level, auto_hide=(level != 'ERROR'))
        if self.statusbar:
            # Show message for 4 seconds; keep ERROR longer
            timeout = 8000 if level == 'ERROR' else 4000
            self.statusbar.showMessage(msg, timeout)

    def _selected_device(self) -> Optional[Device]:
        sm = self.table.selectionModel()
        sel = sm.selectedRows() if sm else []
        if not sel:
            return None
        row = sel[0].row()
        dev_id_item = self.table.item(row, 0)
        if not dev_id_item:
            return None
        dev_id = int(dev_id_item.text())
        return self.dev_repo.get(dev_id)

    def _load_table(self):
        self.table.setRowCount(0)
        for d in self.dev_repo.list():
            self._append_device_row(d)

    def _append_device_row(self, d: Device):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(d.id or "")))
        self.table.setItem(r, 1, QtWidgets.QTableWidgetItem(d.name))
        self.table.setItem(r, 2, QtWidgets.QTableWidgetItem(d.ip))
        self.table.setItem(r, 3, QtWidgets.QTableWidgetItem(str(d.port)))
        self.table.setItem(r, 4, QtWidgets.QTableWidgetItem('Sí' if d.enabled else 'No'))
        connected = self.zk.is_connected(d.ip, d.port)
        self.table.setItem(r, 5, QtWidgets.QTableWidgetItem('Sí' if connected else 'No'))
        self.table.setItem(r, 6, QtWidgets.QTableWidgetItem(d.last_sync or ''))
        self.table.setItem(r, 7, QtWidgets.QTableWidgetItem(d.last_download or ''))
        self.table.setItem(r, 8, QtWidgets.QTableWidgetItem(d.zone or ''))

    def _refresh_row_connected(self, device: Device):
        # Find row by id and update "Conectado"
        for r in range(self.table.rowCount()):
            id_item = self.table.item(r, 0)
            if id_item and id_item.text() == str(device.id):
                self.table.setItem(r, 5, QtWidgets.QTableWidgetItem('Sí' if self.zk.is_connected(device.ip, device.port) else 'No'))
                break

    def _on_add(self):
        d = DeviceDialog(self)
        if d.exec_() == QtWidgets.QDialog.Accepted:
            data = d.get_data()
            new_dev = Device(id=None, name=data['name'], ip=data['ip'], port=data['port'], enabled=data['enabled'], password=data.get('password',0), zone=data['zone'])
            new_id = self.dev_repo.create(new_dev)
            new_dev.id = new_id
            self._append_device_row(new_dev)
            self._log(f"Dispositivo agregado: {new_dev.name}")

    def _on_edit(self):
        dev = self._selected_device()
        if not dev:
            self._log('Selecciona un dispositivo', 'WARN'); return
        # Prefill dialog with current values
        data = {
            'name': dev.name,
            'ip': dev.ip,
            'port': dev.port,
            'password': int(dev.password or 0),
            'enabled': dev.enabled,
            'zone': dev.zone,
        }
        dlg = DeviceDialog(self, data=data)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            nd = dlg.get_data()
            dev.name = nd['name']
            dev.ip = nd['ip']
            dev.port = nd['port']
            dev.password = nd.get('password', 0)
            dev.enabled = nd['enabled']
            dev.zone = nd['zone']
            self.dev_repo.update(dev)
            self._load_table()
            self._log('Dispositivo actualizado')

    def _on_connect(self):
        dev = self._selected_device()
        if not dev:
            self._log('Selecciona un dispositivo', 'WARN'); return
        worker = ConnectWorker(self.zk, dev.ip, dev.port)
        worker.log.connect(self._log)
        worker.result.connect(lambda _: self._refresh_row_connected(dev))
        worker.error.connect(lambda e: self._log(e, 'ERROR'))
        run_in_thread(worker)

    def _on_disconnect(self):
        dev = self._selected_device()
        if not dev:
            self._log('Selecciona un dispositivo', 'WARN'); return
        worker = DisconnectWorker(self.zk, dev.ip, dev.port)
        worker.log.connect(self._log)
        worker.result.connect(lambda _: self._refresh_row_connected(dev))
        worker.error.connect(lambda e: self._log(e, 'ERROR'))
        run_in_thread(worker)

    def _on_download(self):
        dev = self._selected_device()
        if not dev:
            self._log('Selecciona un dispositivo', 'WARN'); return
        clear_after = (self.set_repo.get('delete_after_download') == '1')
        # Pass password=0 for now (DeviceDialog has no password); extend if needed
        self._start_download_for_device(dev, clear_after)

    def _on_sync(self):
        self._log('Sincronización aún no implementada (placeholder)')

    def _load_settings(self):
        # Programar descargas diarias según ajustes guardados en Sistema
        self._setup_daily_timer()

    # Ajustes se guardan desde Sistema; aquí solo reprogramamos cuando cambian

    def _setup_daily_timer(self):
        self._daily_timer.stop()
        daily_enabled = self.set_repo.get('auto_download_daily_enabled') == '1'
        daily_time = self.set_repo.get('auto_download_daily_time') or '02:00'
        if not daily_enabled:
            return
        try:
            hh, mm = [int(x) for x in daily_time.split(':', 1)]
            qtime = QtCore.QTime(hh, mm)
        except Exception:
            qtime = QtCore.QTime(2, 0)
        ms = self._ms_until_next(qtime)
        if ms <= 0:
            return
        try:
            self._daily_timer.timeout.disconnect()  # type: ignore
        except Exception:
            pass
        self._daily_timer.timeout.connect(self._run_scheduled_downloads)
        self._daily_timer.start(ms)
        # Log próxima ejecución
        next_dt = QtCore.QDateTime.currentDateTime().addMSecs(ms)
        self._log(f"Próxima descarga: {next_dt.toString('dd/MM/yyyy HH:mm')}")

    def _ms_until_next(self, qtime: QtCore.QTime) -> int:
        now = QtCore.QDateTime.currentDateTime()
        target = QtCore.QDateTime(now.date(), qtime)
        if target <= now:
            target = QtCore.QDateTime(now.date().addDays(1), qtime)
        return int(now.msecsTo(target))

    def _run_scheduled_downloads(self):
        # Reschedule next day first
        self._setup_daily_timer()
        self._log('Descarga programada iniciada')
        clear_after = (self.set_repo.get('delete_after_download') == '1')
        for dev in self.dev_repo.list():
            if not dev.enabled:
                continue
            self._start_download_for_device(dev, clear_after)

    def _start_download_for_device(self, dev: Device, clear_after: bool):
        worker = DownloadEventsWorker(self.zk, dev.ip, dev.port, clear_after=clear_after, password=int(dev.password or 0))
        worker.log.connect(self._log)
        def on_result(events):
            try:
                # Persist the events we already downloaded in the worker
                count = self.download_service.persist_events(dev.id or 0, events)
                dev.last_download = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.dev_repo.update(dev)
                self._load_table()
                self._log(f"Eventos guardados: {count}")
                self.events_saved.emit(count)
            except Exception as e:
                self._log(str(e), 'ERROR')
        worker.result.connect(on_result)
        worker.error.connect(lambda e: self._log(e, 'ERROR'))
        run_in_thread(worker)
