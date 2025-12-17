from PyQt5 import QtCore, QtWidgets, QtGui
from data.repositories import SettingsRepository, DeviceRepository
from services.zk_service import ZKService
import os


class SystemCard(QtWidgets.QWidget):
    settings_changed = QtCore.pyqtSignal()
    def __init__(self, zk: ZKService = None, parent=None):
        super().__init__(parent)
        self.zk = zk
        self.set_repo = SettingsRepository()
        self.dev_repo = DeviceRepository()
        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)

        # Configuración: Ajustes Básicos (inspirado en captura)
        gb_basic = QtWidgets.QGroupBox('Ajustes Básicos')
        basic = QtWidgets.QFormLayout(gb_basic)
        self.cb_delete_after = QtWidgets.QCheckBox('Borrar eventos de los dispositivos después de la descarga')
        self.cmb_date = QtWidgets.QComboBox(); self.cmb_date.addItems(['dd/MM/yyyy','MM/dd/yyyy','yyyy-MM-dd'])
        self.cmb_time = QtWidgets.QComboBox(); self.cmb_time.addItems(['HH:mm','HH:mm:ss'])
        opt_row = QtWidgets.QHBoxLayout()
        self.cb_opt_access = QtWidgets.QCheckBox('Activar Control de Acceso')
        self.cb_opt_email = QtWidgets.QCheckBox('Activar Reporte de Email Push')
        self.cb_opt_usb = QtWidgets.QCheckBox('Activar Gestión de Memoria USB')
        self.cb_opt_photo = QtWidgets.QCheckBox('Activar Descarga de Foto de Asistencia')
        opt_row.addWidget(self.cb_opt_access); opt_row.addWidget(self.cb_opt_email); opt_row.addWidget(self.cb_opt_usb); opt_row.addWidget(self.cb_opt_photo); opt_row.addStretch(1)
        cal_row = QtWidgets.QHBoxLayout()
        self.rb_cal_normal = QtWidgets.QRadioButton('Normal'); self.rb_cal_normal.setChecked(True)
        self.rb_cal_iran = QtWidgets.QRadioButton('Irán')
        self.rb_cal_arab = QtWidgets.QRadioButton('Árabe')
        cal_row.addWidget(self.rb_cal_normal); cal_row.addWidget(self.rb_cal_iran); cal_row.addWidget(self.rb_cal_arab); cal_row.addStretch(1)
        basic.addRow(self.cb_delete_after)
        basic.addRow('Formato de Fecha', self.cmb_date)
        basic.addRow('Formato de Hora', self.cmb_time)
        basic.addRow('Funciones Opcionales', opt_row)
        basic.addRow('Tipo de Calendario', cal_row)

        # Configuración: Ajustes de Tareas Planeadas
        gb_sched = QtWidgets.QGroupBox('Ajustes de Tareas Planeadas')
        sched = QtWidgets.QFormLayout(gb_sched)
        self.cb_daily_at = QtWidgets.QCheckBox('Descargar a las')
        self.time_daily = QtWidgets.QTimeEdit(); self.time_daily.setDisplayFormat('HH:mm'); self.time_daily.setTime(QtCore.QTime(2,0))
        # Formato de reloj: 24h o AM/PM
        self.cmb_clock = QtWidgets.QComboBox(); self.cmb_clock.addItems(['24 hs','AM/PM'])
        self.cmb_clock.currentIndexChanged.connect(self._apply_clock_format)
        row_daily = QtWidgets.QHBoxLayout(); row_daily.addWidget(self.cb_daily_at); row_daily.addWidget(self.time_daily); row_daily.addStretch(1)
        sched.addRow(row_daily)
        # Días de la semana
        days_row = QtWidgets.QHBoxLayout()
        self.chk_days = [
            QtWidgets.QCheckBox('Lunes'),
            QtWidgets.QCheckBox('Martes'),
            QtWidgets.QCheckBox('Miércoles'),
            QtWidgets.QCheckBox('Jueves'),
            QtWidgets.QCheckBox('Viernes'),
            QtWidgets.QCheckBox('Sábado'),
            QtWidgets.QCheckBox('Domingo'),
        ]
        for c in self.chk_days:
            days_row.addWidget(c)
        days_row.addStretch(1)
        sched.addRow('Días de la semana', days_row)
        sched.addRow('Formato de reloj', self.cmb_clock)

        # Botón Guardar
        self.btn_save = QtWidgets.QPushButton('Guardar')

        # Utilidades
        util = QtWidgets.QHBoxLayout()
        self.btn_open_data = QtWidgets.QPushButton('Abrir carpeta de datos')
        self.btn_open_logs = QtWidgets.QPushButton('Abrir carpeta del proyecto')
        util.addWidget(self.btn_open_data); util.addWidget(self.btn_open_logs); util.addStretch(1)

        root.addWidget(gb_basic)
        root.addWidget(gb_sched)
        root.addLayout(util)
        root.addWidget(self.btn_save)

        self.btn_open_data.clicked.connect(self._open_data)
        self.btn_open_logs.clicked.connect(self._open_project)
        self.btn_save.clicked.connect(self._save_settings)

    def _open_data(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_dir = os.path.join(base_dir, 'data')
        os.makedirs(data_dir, exist_ok=True)
        # Open folder using desktop services
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(data_dir))

    def _open_project(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(base_dir))

    def _load_settings(self):
        delete_after = self.set_repo.get('delete_after_download')
        self.cb_delete_after.setChecked(delete_after == '1')
        date_fmt = self.set_repo.get('date_format') or 'dd/MM/yyyy'
        time_fmt = self.set_repo.get('time_format') or 'HH:mm'
        self.cmb_date.setCurrentText(date_fmt)
        self.cmb_time.setCurrentText(time_fmt)
        opt_access = self.set_repo.get('opt_access_control') == '1'
        opt_email = self.set_repo.get('opt_email_push') == '1'
        opt_usb = self.set_repo.get('opt_usb_mem') == '1'
        opt_photo = self.set_repo.get('opt_attendance_photo') == '1'
        self.cb_opt_access.setChecked(opt_access)
        self.cb_opt_email.setChecked(opt_email)
        self.cb_opt_usb.setChecked(opt_usb)
        self.cb_opt_photo.setChecked(opt_photo)
        cal = self.set_repo.get('calendar_type') or 'normal'
        self.rb_cal_normal.setChecked(cal == 'normal')
        self.rb_cal_iran.setChecked(cal == 'iran')
        self.rb_cal_arab.setChecked(cal == 'arab')
        daily_enabled = self.set_repo.get('auto_download_daily_enabled') == '1'
        daily_time = self.set_repo.get('auto_download_daily_time') or '02:00'
        days_csv = self.set_repo.get('auto_download_days') or ''
        clock_fmt = self.set_repo.get('clock_format') or '24'
        self.cb_daily_at.setChecked(daily_enabled)
        try:
            hh, mm = [int(x) for x in daily_time.split(':', 1)]
            self.time_daily.setTime(QtCore.QTime(hh, mm))
        except Exception:
            pass
        # Apply days selection (1=Mon ... 7=Sun)
        try:
            days = {int(x) for x in days_csv.split(',') if x}
        except Exception:
            days = set()
        for idx, cb in enumerate(self.chk_days, start=1):
            cb.setChecked(idx in days)
        # Apply clock format
        self.cmb_clock.setCurrentIndex(0 if clock_fmt=='24' else 1)
        self._apply_clock_format()

    def _save_settings(self):
        self.set_repo.set('delete_after_download', '1' if self.cb_delete_after.isChecked() else '0')
        self.set_repo.set('date_format', self.cmb_date.currentText())
        self.set_repo.set('time_format', self.cmb_time.currentText())
        self.set_repo.set('opt_access_control', '1' if self.cb_opt_access.isChecked() else '0')
        self.set_repo.set('opt_email_push', '1' if self.cb_opt_email.isChecked() else '0')
        self.set_repo.set('opt_usb_mem', '1' if self.cb_opt_usb.isChecked() else '0')
        self.set_repo.set('opt_attendance_photo', '1' if self.cb_opt_photo.isChecked() else '0')
        cal = 'normal'
        if self.rb_cal_iran.isChecked():
            cal = 'iran'
        elif self.rb_cal_arab.isChecked():
            cal = 'arab'
        self.set_repo.set('calendar_type', cal)
        self.set_repo.set('auto_download_daily_enabled', '1' if self.cb_daily_at.isChecked() else '0')
        self.set_repo.set('auto_download_daily_time', self.time_daily.time().toString('HH:mm'))
        # Save days list as CSV (1=Mon ... 7=Sun)
        days = [str(i+1) for i, cb in enumerate(self.chk_days) if cb.isChecked()]
        self.set_repo.set('auto_download_days', ','.join(days))
        self.set_repo.set('clock_format', '24' if self.cmb_clock.currentIndex()==0 else '12')
        QtWidgets.QMessageBox.information(self, 'Sistema', 'Configuración guardada')
        self.settings_changed.emit()

    def _apply_clock_format(self):
        # Change display format only; stored value is always HH:mm
        if self.cmb_clock.currentIndex() == 0:
            self.time_daily.setDisplayFormat('HH:mm')
        else:
            self.time_daily.setDisplayFormat('hh:mm AP')
