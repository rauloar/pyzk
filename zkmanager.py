import sys
import os
import json
import csv
from datetime import datetime
from typing import cast
from PyQt5 import QtWidgets, QtCore, QtGui
import os
import json
import qtmodern.styles
import qtmodern.windows
from zk.base import ZK
from zk.exception import ZKError, ZKErrorResponse, ZKNetworkError

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Icon loader (optional Bootstrap Icons in assets/icons)
_ICON_CACHE = {}
def load_icon(name: str) -> QtGui.QIcon:
    if not name:
        return QtGui.QIcon()
    cached = _ICON_CACHE.get(name)
    if cached is not None:
        return cached
    for ext in ('.svg', '.png', '.ico'):
        p = os.path.join(BASE_DIR, 'assets', 'icons', f'{name}{ext}')
        if os.path.exists(p):
            icon = QtGui.QIcon(p)
            _ICON_CACHE[name] = icon
            return icon
    # Not found
    icon = QtGui.QIcon()
    _ICON_CACHE[name] = icon
    return icon

# Helper para arrancar workers con tipado explícito
def _start_worker(worker: QtCore.QRunnable) -> None:
    pool = cast(QtCore.QThreadPool, QtCore.QThreadPool.globalInstance())
    pool.start(worker)


# --- Login Window ---
class LoginWindow(QtWidgets.QWidget):
    login_success = QtCore.pyqtSignal()
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Login - ZKTeco Manager')
        self.setFixedSize(350, 200)
        layout = QtWidgets.QVBoxLayout()
        self.user_label = QtWidgets.QLabel('Usuario:')
        self.user_input = QtWidgets.QLineEdit()
        self.pass_label = QtWidgets.QLabel('Contraseña:')
        self.pass_input = QtWidgets.QLineEdit()
        self.pass_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.login_btn = QtWidgets.QPushButton('Iniciar sesión')
        self.login_btn.clicked.connect(self.handle_login)
        self.error_label = QtWidgets.QLabel('')
        self.error_label.setStyleSheet('color: red')
        layout.addWidget(self.user_label)
        layout.addWidget(self.user_input)
        layout.addWidget(self.pass_label)
        layout.addWidget(self.pass_input)
        layout.addWidget(self.login_btn)
        layout.addWidget(self.error_label)
        self.setLayout(layout)
    def handle_login(self):
        user = self.user_input.text()
        pwd = self.pass_input.text()
        if user == 'admin' and pwd == 'admin':
            self.login_success.emit()
        else:
            self.error_label.setText('Usuario o contraseña incorrectos')

# --- Main Panel ---
class MainPanel(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Panel de Control - ZKTeco Manager')
        self.setMinimumSize(800, 500)
        self.topTabs = QtWidgets.QTabWidget()
        # Secciones al estilo ZKTime.Net
        self.page_sistema = SistemaPage()
        self.page_rh = RecursosHumanosPage()
        self.page_asistencia = AsistenciaPage()
        self.page_terminal = TerminalPage()
        self.page_reportes = ReportesPage()
        self.topTabs.addTab(self.page_sistema, 'Sistema')
        self.topTabs.addTab(self.page_rh, 'Recursos Humanos')
        self.topTabs.addTab(self.page_asistencia, 'Asistencia')
        self.topTabs.addTab(self.page_terminal, 'Terminal')
        self.topTabs.addTab(self.page_reportes, 'Reportes')
        self.setCentralWidget(self.topTabs)

    def _terminales_tab(self):
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(QtWidgets.QLabel('Gestión de terminales ZKTeco (Agregar, editar, eliminar, conectar)'))
        # Aquí irán los controles para gestionar terminales
        w.setLayout(layout)
        return w

    def _logs_tab(self):
        # Mantener compatibilidad si se invoca; devolver widget real
        return LogsTab()

    def _usuarios_tab(self):
        return UsuariosTab()

# ---- Barra superior simple (botonera tipo ribbon) ----
class RibbonWidget(QtWidgets.QWidget):
    def __init__(self, title: str = ''):
        super().__init__()
        self._layout = QtWidgets.QHBoxLayout(self)
        self._layout.setContentsMargins(6,6,6,6)
        if title:
            label = QtWidgets.QLabel(title)
            label.setStyleSheet('font-weight: bold;')
            self._layout.addWidget(label)
            self._layout.addSpacing(12)
        self._layout.addStretch(0)
    def add_button(self, text: str, on_click=None, enabled: bool = True, icon: str = '') -> QtWidgets.QPushButton:
        btn = QtWidgets.QPushButton(text)
        if icon:
            btn.setIcon(load_icon(icon))
        btn.setEnabled(enabled)
        if on_click:
            btn.clicked.connect(on_click)
        self._layout.addWidget(btn)
        return btn

# ---- Páginas de alto nivel (matching ZKTime.Net) ----
class SistemaPage(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self._settings = SettingsStore()
        layout = QtWidgets.QVBoxLayout(self)
        bar = RibbonWidget('Acciones')
        bar.add_button('Guardar', self._on_save, icon='save')
        bar.add_button('Abrir carpeta', self._on_open_dir, icon='folder')
        layout.addWidget(bar)
        form = QtWidgets.QFormLayout()
        self.ed_dir = QtWidgets.QLineEdit()
        self.btn_browse = QtWidgets.QPushButton('Examinar...')
        dir_row = QtWidgets.QHBoxLayout()
        dir_row.addWidget(self.ed_dir, 1)
        dir_row.addWidget(self.btn_browse)
        dir_w = QtWidgets.QWidget(); dir_w.setLayout(dir_row)
        self.chk_auto = QtWidgets.QCheckBox('Abrir carpeta al terminar descargas')
        self.spin_interval = QtWidgets.QSpinBox(); self.spin_interval.setRange(1, 1440); self.spin_interval.setSuffix(' min')
        form.addRow('Carpeta de datos:', dir_w)
        form.addRow('Auto-abrir:', self.chk_auto)
        form.addRow('Intervalo descarga:', self.spin_interval)
        layout.addLayout(form)
        self.status = QtWidgets.QLabel('')
        layout.addWidget(self.status)
        # Cargar settings
        cfg = self._settings.get_all()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        default_dir = os.path.join(base_dir, 'data')
        self.ed_dir.setText(cfg.get('data_dir', default_dir))
        self.chk_auto.setChecked(bool(cfg.get('auto_open', False)))
        self.spin_interval.setValue(int(cfg.get('interval_min', 15)))
        # Conexiones
        self.btn_browse.clicked.connect(self._browse_dir)

    def _browse_dir(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(self, 'Elegir carpeta de datos', self.ed_dir.text() or os.getcwd())
        if d:
            self.ed_dir.setText(d)

    def _on_open_dir(self):
        d = self.ed_dir.text().strip()
        if d and os.path.isdir(d):
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(d))
        else:
            QtWidgets.QMessageBox.information(self, 'Abrir carpeta', 'Configura primero una carpeta válida')

    def _on_save(self):
        cfg = {
            'data_dir': self.ed_dir.text().strip(),
            'auto_open': self.chk_auto.isChecked(),
            'interval_min': int(self.spin_interval.value()),
            'saved_at': datetime.now().isoformat()
        }
        try:
            self._settings.update(cfg)
            self.status.setText('Configuración guardada')
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, 'Error', str(e))

class TerminalPage(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        self.term_tab = TerminalesTab()
        bar = RibbonWidget('Gestión de Dispositivos')
        btn_agregar = bar.add_button('Agregar', self.term_tab._on_add, icon='plus')
        btn_borrar = bar.add_button('Borrar', self.term_tab._on_delete, icon='trash')
        btn_conectar = bar.add_button('Conectar', self.term_tab._on_connect, icon='plug')
        btn_desconectar = bar.add_button('Desconectar', self.term_tab._on_disconnect, icon='plug-fill')
        btn_refrescar = bar.add_button('Refrescar Info', self.term_tab._on_refresh_info, icon='arrow-repeat')
        btn_sync = bar.add_button('Sincronizar Hora', self.term_tab._on_sync_time, icon='clock')
        btn_enable = bar.add_button('Enable', lambda: self.term_tab._device_action('enable'), icon='toggle2-on')
        btn_disable = bar.add_button('Disable', lambda: self.term_tab._device_action('disable'), icon='toggle2-off')
        btn_restart = bar.add_button('Reiniciar', lambda: self.term_tab._device_action('restart'), icon='arrow-repeat')
        btn_poweroff = bar.add_button('Apagar', lambda: self.term_tab._device_action('poweroff'), icon='power')
        layout.addWidget(bar)
        layout.addWidget(self.term_tab)

class AsistenciaPage(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        self.logs = LogsTab()
        bar = RibbonWidget('Asistencia')
        bar.add_button('Descargar', self.logs._on_download, icon='download')
        layout.addWidget(bar)
        layout.addWidget(self.logs)

class RecursosHumanosPage(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        self.users = UsuariosTab()
        bar = RibbonWidget('Empleados')
        bar.add_button('Descargar', self.users._on_download, icon='people')
        layout.addWidget(bar)
        layout.addWidget(self.users)

class ReportesPage(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        # Barra superior
        bar = RibbonWidget('Reportes')
        self.btn_export_resumen = bar.add_button('Exportar resumen', self._on_export_resumen, icon='file-earmark-spreadsheet')
        layout.addWidget(bar)
        # Selector de carpeta y lista de archivos
        top = QtWidgets.QHBoxLayout()
        top.addWidget(QtWidgets.QLabel('Carpeta de datos:'))
        self.ed_dir = QtWidgets.QLineEdit()
        self.btn_browse = QtWidgets.QPushButton('Examinar...')
        self.btn_refresh = QtWidgets.QPushButton('Refrescar')
        top.addWidget(self.ed_dir, 1)
        top.addWidget(self.btn_browse)
        top.addWidget(self.btn_refresh)
        layout.addLayout(top)
        files_row = QtWidgets.QHBoxLayout()
        files_row.addWidget(QtWidgets.QLabel('Archivo de asistencias:'))
        self.cb_files = QtWidgets.QComboBox()
        self.btn_load = QtWidgets.QPushButton('Cargar')
        files_row.addWidget(self.cb_files, 1)
        files_row.addWidget(self.btn_load)
        layout.addLayout(files_row)
        # Tabla de previsualización
        self.table = QtWidgets.QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(['user_id','uid','timestamp','status','punch'])
        header = self.table.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(True)
        layout.addWidget(self.table)
        # Estado
        self.status = QtWidgets.QLabel('')
        layout.addWidget(self.status)

        # Valores iniciales
        base_dir = os.path.dirname(os.path.abspath(__file__))
        try:
            self._settings = SettingsStore()
            cfg = self._settings.get_all()
            default_dir = cfg.get('data_dir') or os.path.join(base_dir, 'data')
        except Exception:
            default_dir = os.path.join(base_dir, 'data')
        self.ed_dir.setText(default_dir)
        self._populate_files()

        # Conexiones
        self.btn_browse.clicked.connect(self._browse_dir)
        self.btn_refresh.clicked.connect(self._populate_files)
        self.btn_load.clicked.connect(self._load_selected)

    def _browse_dir(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(self, 'Elegir carpeta de datos', self.ed_dir.text() or os.getcwd())
        if d:
            self.ed_dir.setText(d)
            self._populate_files()

    def _populate_files(self):
        self.cb_files.clear()
        d = self.ed_dir.text().strip()
        if not d or not os.path.isdir(d):
            return
        # Listar CSVs de asistencias
        files = []
        try:
            for fn in os.listdir(d):
                if fn.lower().endswith('.csv') and fn.startswith('attendance_'):
                    files.append(fn)
        except Exception:
            pass
        files.sort(reverse=True)
        for fn in files:
            self.cb_files.addItem(fn)

    def _load_selected(self):
        d = self.ed_dir.text().strip()
        fn = self.cb_files.currentText().strip()
        if not d or not fn:
            QtWidgets.QMessageBox.information(self, 'Cargar', 'Seleccioná una carpeta y un archivo CSV')
            return
        path = os.path.join(d, fn)
        if not os.path.exists(path):
            QtWidgets.QMessageBox.information(self, 'Cargar', 'El archivo no existe')
            return
        # Cargar CSV a la tabla (lazy y en UI; tamaño típico manejable)
        self.table.setRowCount(0)
        rows = 0
        try:
            with open(path, 'r', encoding='utf-8') as f:
                r = csv.reader(f)
                headers = next(r, None)
                for rec in r:
                    if len(rec) < 5:
                        continue
                    rr = self.table.rowCount(); self.table.insertRow(rr)
                    for i in range(5):
                        self.table.setItem(rr, i, QtWidgets.QTableWidgetItem(str(rec[i])))
                    rows += 1
            self.status.setText(f"Cargado {rows} registros de '{fn}'")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, 'Error', str(e))

    def _on_export_resumen(self):
        # Exporta resumen por user_id (conteo de registros)
        d = self.ed_dir.text().strip()
        fn = self.cb_files.currentText().strip()
        if not d or not fn:
            QtWidgets.QMessageBox.information(self, 'Exportar resumen', 'Cargá primero un archivo de asistencias')
            return
        src = os.path.join(d, fn)
        resumen = {}
        try:
            with open(src, 'r', encoding='utf-8') as f:
                r = csv.reader(f)
                headers = next(r, None)
                for rec in r:
                    if len(rec) < 1:
                        continue
                    uid = rec[0]
                    resumen[uid] = resumen.get(uid, 0) + 1
            out = os.path.join(d, f"resumen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            with open(out, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(['user_id','total_registros'])
                for uid, cnt in sorted(resumen.items(), key=lambda x: x[0]):
                    w.writerow([uid, cnt])
            self.status.setText(f"Resumen exportado: {out}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, 'Error', str(e))


# ---- Almacenamiento simple de terminales (JSON local) ----
class TerminalStore:
    def __init__(self, path=None):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.path = path or os.path.join(base_dir, 'terminals.json')
        self._items = []
        self.load()
    def load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, 'r', encoding='utf-8') as f:
                    self._items = json.load(f)
            else:
                self._items = []
        except Exception:
            self._items = []
    def save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self._items, f, ensure_ascii=False, indent=2)
    def all(self):
        return list(self._items)
    def add(self, item):
        self._items.append(item)
        self.save()
    def update(self, index, item):
        self._items[index] = item
        self.save()
    def remove(self, index):
        del self._items[index]
        self.save()

# ---- Estado local para descargas (asistencias/usuarios) ----
class DataState:
    def __init__(self, filename):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, 'data')
        os.makedirs(data_dir, exist_ok=True)
        self.path = os.path.join(data_dir, filename)
        self._data = {}
        self._load()
    def _load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
            else:
                self._data = {}
        except Exception:
            self._data = {}
    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2, default=str)
    def get_last_att_ts(self, key):
        ts = self._data.get('att_last_ts', {}).get(key)
        if not ts:
            return None
        try:
            return datetime.fromisoformat(ts)
        except Exception:
            return None
    def set_last_att_ts(self, key, dt):
        self._data.setdefault('att_last_ts', {})[key] = dt.isoformat()
        self._save()
    def get_user_ids(self, key):
        ids = self._data.get('user_ids', {}).get(key, [])
        return set(ids)
    def set_user_ids(self, key, ids_set):
        self._data.setdefault('user_ids', {})[key] = sorted(list(ids_set))
        self._save()

# ---- Configuración simple (settings.json) ----
class SettingsStore:
    def __init__(self, path=None):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.path = path or os.path.join(base_dir, 'settings.json')
        self._data = {}
        self._load()
    def _load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
            else:
                self._data = {}
        except Exception:
            self._data = {}
    def _save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2, default=str)
    def get_all(self):
        return dict(self._data)
    def update(self, new_values: dict):
        self._data.update(new_values or {})
        self._save()

# ---- Diálogo para agregar/editar terminal ----
class TerminalDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle('Terminal ZKTeco')
        self.setFixedSize(360, 230)
        layout = QtWidgets.QFormLayout()
        self.name = QtWidgets.QLineEdit()
        self.ip = QtWidgets.QLineEdit()
        self.port = QtWidgets.QSpinBox()
        self.port.setMaximum(65535)
        self.port.setValue(4370)
        self.password = QtWidgets.QLineEdit()
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        if data:
            self.name.setText(data.get('name',''))
            self.ip.setText(data.get('ip',''))
            self.port.setValue(int(data.get('port', 4370)))
            self.password.setText(str(data.get('password', '0')))
        layout.addRow('Nombre:', self.name)
        layout.addRow('IP:', self.ip)
        layout.addRow('Puerto:', self.port)
        layout.addRow('Password (num):', self.password)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        v = QtWidgets.QVBoxLayout(self)
        v.addLayout(layout)
        v.addWidget(btns)
    def get_data(self):
        return {
            'name': self.name.text().strip() or f"ZK-{self.ip.text()}",
            'ip': self.ip.text().strip(),
            'port': int(self.port.value()),
            'password': int(self.password.text().strip() or '0')
        }

# ---- Worker sencillo para tareas bloqueantes ----
class Worker(QtCore.QRunnable):
    class Signals(QtCore.QObject):
        finished = QtCore.pyqtSignal(object)
        error = QtCore.pyqtSignal(Exception)
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = Worker.Signals()
    @QtCore.pyqtSlot()
    def run(self):
        try:
            res = self.fn(*self.args, **self.kwargs)
            self.signals.finished.emit(res)
        except Exception as e:
            self.signals.error.emit(e)

# ---- Pestaña: Gestión de Terminales ----
class TerminalesTab(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.store = TerminalStore()
        self.thread_pool = QtCore.QThreadPool.globalInstance()
        self.zk_instances = {}  # index -> ZK
        self._build_ui()
        self._load_table()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        # Tabla
        self.table = QtWidgets.QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(['Nombre','IP','Puerto','Password','Estado'])
        header = self.table.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        layout.addWidget(self.table)
        # Botonera
        btns = QtWidgets.QHBoxLayout()
        self.btn_add = QtWidgets.QPushButton('Agregar')
        self.btn_edit = QtWidgets.QPushButton('Editar')
        self.btn_del = QtWidgets.QPushButton('Eliminar')
        self.btn_connect = QtWidgets.QPushButton('Conectar')
        self.btn_disconnect = QtWidgets.QPushButton('Desconectar')
        self.btn_refresh_info = QtWidgets.QPushButton('Refrescar Info')
        self.btn_sync_time = QtWidgets.QPushButton('Sincronizar Hora')
        self.btn_enable = QtWidgets.QPushButton('Enable')
        self.btn_disable = QtWidgets.QPushButton('Disable')
        self.btn_restart = QtWidgets.QPushButton('Reiniciar')
        self.btn_poweroff = QtWidgets.QPushButton('Apagar')
        for b in [self.btn_add,self.btn_edit,self.btn_del,self.btn_connect,self.btn_disconnect,
                  self.btn_refresh_info,self.btn_sync_time,self.btn_enable,self.btn_disable,
                  self.btn_restart,self.btn_poweroff]:
            btns.addWidget(b)
        layout.addLayout(btns)
        # Info de dispositivo
        self.info = QtWidgets.QTextEdit()
        self.info.setReadOnly(True)
        self.info.setFixedHeight(160)
        layout.addWidget(self.info)
        # Conexiones
        self.btn_add.clicked.connect(self._on_add)
        self.btn_edit.clicked.connect(self._on_edit)
        self.btn_del.clicked.connect(self._on_delete)
        self.btn_connect.clicked.connect(self._on_connect)
        self.btn_disconnect.clicked.connect(self._on_disconnect)
        self.btn_refresh_info.clicked.connect(self._on_refresh_info)
        self.btn_sync_time.clicked.connect(self._on_sync_time)
        self.btn_enable.clicked.connect(lambda: self._device_action('enable'))
        self.btn_disable.clicked.connect(lambda: self._device_action('disable'))
        self.btn_restart.clicked.connect(lambda: self._device_action('restart'))
        self.btn_poweroff.clicked.connect(lambda: self._device_action('poweroff'))

    def _load_table(self):
        items = self.store.all()
        self.table.setRowCount(0)
        for it in items:
            self._append_row(it, estado='Desconectado')

    def _append_row(self, it, estado='Desconectado'):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QtWidgets.QTableWidgetItem(it.get('name','')))
        self.table.setItem(r, 1, QtWidgets.QTableWidgetItem(it.get('ip','')))
        self.table.setItem(r, 2, QtWidgets.QTableWidgetItem(str(it.get('port',4370))))
        self.table.setItem(r, 3, QtWidgets.QTableWidgetItem(str(it.get('password',0))))
        self.table.setItem(r, 4, QtWidgets.QTableWidgetItem(estado))

    def _selected_index(self):
        sm = self.table.selectionModel()
        if sm is None:
            return None
        sel = sm.selectedRows()
        if not sel:
            return None
        return sel[0].row()

    def _read_row(self, row):
        def item_text(r, c):
            it = self.table.item(r, c)
            return it.text() if it is not None else ''
        name = item_text(row, 0)
        ip = item_text(row, 1)
        port_txt = item_text(row, 2)
        pwd_txt = item_text(row, 3)
        port = int(port_txt) if port_txt.isdigit() else 4370
        try:
            password = int(pwd_txt) if pwd_txt else 0
        except Exception:
            password = 0
        return {'name': name, 'ip': ip, 'port': port, 'password': password}

    def _on_add(self):
        d = TerminalDialog(self)
        if d.exec_() == QtWidgets.QDialog.Accepted:
            data = d.get_data()
            self.store.add(data)
            self._append_row(data)

    def _on_edit(self):
        idx = self._selected_index()
        if idx is None:
            QtWidgets.QMessageBox.information(self, 'Editar', 'Selecciona una terminal')
            return
        current = self._read_row(idx)
        d = TerminalDialog(self, data=current)
        if d.exec_() == QtWidgets.QDialog.Accepted:
            data = d.get_data()
            self.store.update(idx, data)
            for c,v in enumerate([data['name'], data['ip'], str(data['port']), str(data['password'])]):
                self.table.setItem(idx, c, QtWidgets.QTableWidgetItem(v))

    def _on_delete(self):
        idx = self._selected_index()
        if idx is None:
            return
        if QtWidgets.QMessageBox.question(self,'Eliminar','¿Eliminar la terminal seleccionada?') == QtWidgets.QMessageBox.Yes:
            self.store.remove(idx)
            self.table.removeRow(idx)
            if idx in self.zk_instances:
                try:
                    self.zk_instances[idx].disconnect()
                except Exception:
                    pass
                del self.zk_instances[idx]

    def _on_connect(self):
        idx = self._selected_index()
        if idx is None:
            QtWidgets.QMessageBox.information(self,'Conectar','Selecciona una terminal')
            return
        data = self._read_row(idx)
        def task():
            zk = ZK(data['ip'], port=data['port'], password=data['password'], ommit_ping=False, verbose=False)
            conn = zk.connect()
            return zk
        worker = Worker(task)
        worker.signals.finished.connect(lambda zk: self._on_connected(idx, zk))
        worker.signals.error.connect(lambda e: self._show_error('Error al conectar', e))
        self._set_status(idx, 'Conectando...')
        _start_worker(worker)

    def _on_connected(self, idx, zk):
        self.zk_instances[idx] = zk
        self._set_status(idx, 'Conectado')
        self._append_info("Conectado a la terminal")
        self._fetch_info(idx)

    def _on_disconnect(self):
        idx = self._selected_index()
        if idx is None:
            return
        zk = self.zk_instances.get(idx)
        if not zk:
            self._set_status(idx, 'Desconectado')
            return
        def task():
            try:
                zk.disconnect()
            except Exception:
                pass
            return True
        worker = Worker(task)
        worker.signals.finished.connect(lambda _: self._after_disconnect(idx))
        worker.signals.error.connect(lambda e: self._show_error('Error al desconectar', e))
        self._set_status(idx, 'Desconectando...')
        _start_worker(worker)

    def _after_disconnect(self, idx):
        if idx in self.zk_instances:
            del self.zk_instances[idx]
        self._set_status(idx, 'Desconectado')
        self._append_info("Terminal desconectada")

    def _fetch_info(self, idx):
        zk = self.zk_instances.get(idx)
        if not zk:
            return
        def task():
            info = {
                'serial': zk.get_serialnumber(),
                'name': zk.get_device_name(),
                'fw': zk.get_firmware_version(),
                'platform': zk.get_platform(),
                'mac': zk.get_mac(),
                'time': zk.get_time(),
            }
            zk.read_sizes()
            info.update({
                'users': zk.users,
                'fingers': zk.fingers,
                'records': zk.records,
            })
            return info
        worker = Worker(task)
        worker.signals.finished.connect(lambda info: self._show_device_info(info))
        worker.signals.error.connect(lambda e: self._show_error('Error al leer info', e))
        _start_worker(worker)

    def _on_refresh_info(self):
        idx = self._selected_index()
        if idx is None:
            return
        self._fetch_info(idx)

    def _on_sync_time(self):
        idx = self._selected_index()
        if idx is None:
            return
        zk = self.zk_instances.get(idx)
        if not zk:
            QtWidgets.QMessageBox.information(self,'Sincronizar','Conecta primero a la terminal')
            return
        now = datetime.now()
        def task():
            return zk.set_time(now)
        worker = Worker(task)
        worker.signals.finished.connect(lambda _: self._append_info(f"Hora sincronizada a {now}"))
        worker.signals.error.connect(lambda e: self._show_error('Error al sincronizar hora', e))
        _start_worker(worker)

    def _device_action(self, action):
        idx = self._selected_index()
        if idx is None:
            return
        zk = self.zk_instances.get(idx)
        if not zk:
            QtWidgets.QMessageBox.information(self, action, 'Conecta primero a la terminal')
            return
        def task():
            if action == 'enable':
                return zk.enable_device()
            if action == 'disable':
                return zk.disable_device()
            if action == 'restart':
                return zk.restart()
            if action == 'poweroff':
                return zk.poweroff()
        worker = Worker(task)
        worker.signals.finished.connect(lambda _: self._append_info(f"Acción '{action}' ejecutada"))
        worker.signals.error.connect(lambda e: self._show_error(f'Error en {action}', e))
        _start_worker(worker)

    def _set_status(self, idx, text):
        self.table.setItem(idx, 4, QtWidgets.QTableWidgetItem(text))

    def _show_device_info(self, info):
        lines = [
            f"Serial: {info.get('serial','')}",
            f"Nombre: {info.get('name','')}",
            f"Firmware: {info.get('fw','')}",
            f"Plataforma: {info.get('platform','')}",
            f"MAC: {info.get('mac','')}",
            f"Hora: {info.get('time','')}",
            f"Usuarios: {info.get('users','?')} | Huellas: {info.get('fingers','?')} | Registros: {info.get('records','?')}",
        ]
        self.info.setPlainText("\n".join(lines))

    def _append_info(self, text):
        current = self.info.toPlainText()
        self.info.setPlainText((current + ("\n" if current else "")) + text)

    def _show_error(self, title, exc):
        QtWidgets.QMessageBox.critical(self, title, str(exc))

# ---- Pestaña: Descarga de Logs ----
class LogsTab(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.store = TerminalStore()
        self.state = DataState('att_state.json')
        self.settings = SettingsStore()
        self.thread_pool = QtCore.QThreadPool.globalInstance()
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        top = QtWidgets.QHBoxLayout()
        top.addWidget(QtWidgets.QLabel('Terminal:'))
        self.cb = QtWidgets.QComboBox()
        for it in self.store.all():
            self.cb.addItem(f"{it.get('name','')} ({it.get('ip','')}:{it.get('port',4370)})", it)
        self.btn_download = QtWidgets.QPushButton('Descargar')
        top.addWidget(self.cb, 1)
        top.addWidget(self.btn_download)
        layout.addLayout(top)
        self.status = QtWidgets.QLabel('')
        layout.addWidget(self.status)
        self.table = QtWidgets.QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(['user_id','uid','timestamp','status','punch'])
        header = self.table.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(True)
        layout.addWidget(self.table)
        self.btn_download.clicked.connect(self._on_download)

    def _on_download(self):
        data = self.cb.currentData()
        if not data:
            QtWidgets.QMessageBox.information(self,'Descargar','Primero agregá una terminal en la pestaña Terminales')
            return
        key = f"{data['ip']}:{data['port']}"
        last_ts = self.state.get_last_att_ts(key)
        self.status.setText('Conectando y preparando previsualización...')
        def task():
            zk = ZK(data['ip'], port=data['port'], password=data['password'], ommit_ping=False, verbose=False)
            zk.connect()
            zk.disable_device()
            att = zk.get_attendance()
            # calcular nuevas
            if last_ts:
                new_items = [a for a in att if a.timestamp > last_ts]
            else:
                new_items = att
            max_ts = None
            for a in att:
                if (max_ts is None) or (a.timestamp > max_ts):
                    max_ts = a.timestamp
            return {'zk': zk, 'all': att, 'new': new_items, 'max_ts': max_ts}
        worker = Worker(task)
        worker.signals.finished.connect(lambda res: self._preview_and_confirm(res, data))
        worker.signals.error.connect(lambda e: self._error_and_cleanup(e))
        _start_worker(worker)

    def _preview_and_confirm(self, res, data):
        att_all = res['all']
        att_new = res['new']
        zk = res['zk']
        self.table.setRowCount(0)
        for a in att_new:
            r = self.table.rowCount(); self.table.insertRow(r)
            self.table.setItem(r,0, QtWidgets.QTableWidgetItem(str(a.user_id)))
            self.table.setItem(r,1, QtWidgets.QTableWidgetItem(str(getattr(a,'uid',''))))
            self.table.setItem(r,2, QtWidgets.QTableWidgetItem(str(a.timestamp)))
            self.table.setItem(r,3, QtWidgets.QTableWidgetItem(str(a.status)))
            self.table.setItem(r,4, QtWidgets.QTableWidgetItem(str(a.punch)))
        self.status.setText(f"Nuevos: {len(att_new)} de {len(att_all)} totales")
        reply = QtWidgets.QMessageBox.question(self,'Confirmar descarga', f"¿Descargar {len(att_new)} nuevos registros?")
        if reply != QtWidgets.QMessageBox.Yes:
            # enable y desconectar
            def cleanup():
                try:
                    zk.enable_device()
                finally:
                    zk.disconnect()
                return True
            worker = Worker(cleanup)
            _start_worker(worker)
            return
        # Guardar
        self.status.setText('Descargando y guardando CSV...')
        def save_task():
            base_dir = os.path.dirname(os.path.abspath(__file__))
            cfg = self.settings.get_all()
            data_dir = cfg.get('data_dir') or os.path.join(base_dir, 'data')
            os.makedirs(data_dir, exist_ok=True)
            fname = os.path.join(data_dir, f"attendance_{data['ip'].replace('.','-')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            with open(fname, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(['user_id','uid','timestamp','status','punch'])
                for a in att_new:
                    w.writerow([a.user_id, getattr(a,'uid',''), a.timestamp, a.status, a.punch])
            # actualizar estado al max_ts
            key = f"{data['ip']}:{data['port']}"
            if res['max_ts']:
                self.state.set_last_att_ts(key, res['max_ts'])
            try:
                zk.enable_device()
            finally:
                zk.disconnect()
            if cfg.get('auto_open'):
                QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(data_dir))
            return fname
        worker = Worker(save_task)
        worker.signals.finished.connect(lambda fname: self.status.setText(f"Descarga completa: {fname}"))
        worker.signals.error.connect(lambda e: self._error_and_cleanup(e))
        _start_worker(worker)

    def _error_and_cleanup(self, e):
        QtWidgets.QMessageBox.critical(self, 'Error', str(e))
        self.status.setText('Error')

# ---- Pestaña: Descarga/Gestión de Usuarios ----
class UsuariosTab(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.store = TerminalStore()
        self.state = DataState('users_state.json')
        self.settings = SettingsStore()
        self.thread_pool = QtCore.QThreadPool.globalInstance()
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        top = QtWidgets.QHBoxLayout()
        top.addWidget(QtWidgets.QLabel('Terminal:'))
        self.cb = QtWidgets.QComboBox()
        for it in self.store.all():
            self.cb.addItem(f"{it.get('name','')} ({it.get('ip','')}:{it.get('port',4370)})", it)
        self.btn_download = QtWidgets.QPushButton('Descargar')
        top.addWidget(self.cb, 1)
        top.addWidget(self.btn_download)
        layout.addLayout(top)
        self.status = QtWidgets.QLabel('')
        layout.addWidget(self.status)
        self.table = QtWidgets.QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(['user_id','uid','name','privilege','group_id','card'])
        header = self.table.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(True)
        layout.addWidget(self.table)
        self.btn_download.clicked.connect(self._on_download)

    def _on_download(self):
        data = self.cb.currentData()
        if not data:
            QtWidgets.QMessageBox.information(self,'Descargar','Primero agregá una terminal en la pestaña Terminales')
            return
        key = f"{data['ip']}:{data['port']}"
        prev_ids = self.state.get_user_ids(key)
        self.status.setText('Conectando y preparando previsualización...')
        def task():
            zk = ZK(data['ip'], port=data['port'], password=data['password'], ommit_ping=False, verbose=False)
            zk.connect()
            zk.disable_device()
            users = zk.get_users()
            current_ids = set([u.user_id for u in users])
            new_users = [u for u in users if u.user_id not in prev_ids]
            return {'zk': zk, 'all': users, 'new': new_users, 'ids': current_ids}
        worker = Worker(task)
        worker.signals.finished.connect(lambda res: self._preview_and_confirm(res, data, key))
        worker.signals.error.connect(lambda e: self._error_and_cleanup(e))
        _start_worker(worker)

    def _preview_and_confirm(self, res, data, key):
        users_all = res['all']
        users_new = res['new']
        zk = res['zk']
        self.table.setRowCount(0)
        for u in users_new:
            r = self.table.rowCount(); self.table.insertRow(r)
            self.table.setItem(r,0, QtWidgets.QTableWidgetItem(str(u.user_id)))
            self.table.setItem(r,1, QtWidgets.QTableWidgetItem(str(u.uid)))
            self.table.setItem(r,2, QtWidgets.QTableWidgetItem(u.name))
            self.table.setItem(r,3, QtWidgets.QTableWidgetItem(str(u.privilege)))
            self.table.setItem(r,4, QtWidgets.QTableWidgetItem(str(u.group_id)))
            self.table.setItem(r,5, QtWidgets.QTableWidgetItem(str(u.card)))
        self.status.setText(f"Nuevos: {len(users_new)} de {len(users_all)} totales")
        reply = QtWidgets.QMessageBox.question(self,'Confirmar descarga', f"¿Descargar usuarios (nuevos: {len(users_new)})?")
        if reply != QtWidgets.QMessageBox.Yes:
            def cleanup():
                try:
                    zk.enable_device()
                finally:
                    zk.disconnect()
                return True
            worker = Worker(cleanup)
            _start_worker(worker)
            return
        # Guardar CSV y actualizar snapshot de ids
        current_ids = res['ids']
        self.status.setText('Descargando y guardando CSV...')
        def save_task():
            base_dir = os.path.dirname(os.path.abspath(__file__))
            cfg = self.settings.get_all()
            data_dir = cfg.get('data_dir') or os.path.join(base_dir, 'data')
            os.makedirs(data_dir, exist_ok=True)
            fname = os.path.join(data_dir, f"users_{data['ip'].replace('.','-')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            with open(fname, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(['user_id','uid','name','privilege','group_id','card'])
                for u in users_all:
                    w.writerow([u.user_id, u.uid, u.name, u.privilege, u.group_id, u.card])
            self.state.set_user_ids(key, current_ids)
            try:
                zk.enable_device()
            finally:
                zk.disconnect()
            if cfg.get('auto_open'):
                QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(data_dir))
            return fname
        worker = Worker(save_task)
        worker.signals.finished.connect(lambda fname: self.status.setText(f"Descarga completa: {fname}"))
        worker.signals.error.connect(lambda e: self._error_and_cleanup(e))
        _start_worker(worker)

    def _error_and_cleanup(self, e):
        QtWidgets.QMessageBox.critical(self, 'Error', str(e))
        self.status.setText('Error')


def main():
    app = QtWidgets.QApplication(sys.argv)
    qtmodern.styles.dark(app)
    login = LoginWindow()
    mw_login = qtmodern.windows.ModernWindow(login)
    main_panel = MainPanel()
    mw_main = qtmodern.windows.ModernWindow(main_panel)
    # Tema verde tipo ZKTime.Net (acento)
    app.setStyleSheet(
        """
        QTabBar::tab:selected { background: #6BBF59; color: #fff; }
        QTabBar::tab:hover { background: #5aac48; color: #fff; }
        QToolBar { background: #3b3f45; border: 0; }
        QPushButton { padding: 6px 10px; }
        QPushButton:hover { background: #2f3338; }
        """
    )
    def show_panel():
        mw_login.close()
        mw_main.show()
    login.login_success.connect(show_panel)
    mw_login.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
