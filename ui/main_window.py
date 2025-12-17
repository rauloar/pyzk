from PyQt5 import QtWidgets, QtCore
from ui.views.terminal_card import TerminalCard
from ui.views.employee_card import EmployeeCard
from ui.views.reports_card import ReportsCard
from ui.views.attendance_card import AttendanceCard
from ui.views.system_card import SystemCard
from ui.views.access_card import AccessCard
from widgets.message_toast import MessageToast
from services.zk_service import ZKService


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('ZKTeco Manager')
        self.resize(1100, 720)
        self.zk = ZKService()

        # Menu / modules
        self.tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tabs)

        # Pages
        self.card_terminal = TerminalCard(self.zk)
        self.card_employee = EmployeeCard(self.zk)
        self.card_reports = ReportsCard()
        self.card_attendance = AttendanceCard()
        self.card_system = SystemCard(self.zk)
        self.card_access = AccessCard()

        # As required: 6 módulos (solo Terminal completo)
        self.tabs.addTab(self._wrap_widget(self.card_terminal), 'Terminal')
        self.tabs.addTab(self._wrap_widget(self.card_employee), 'RRHH')
        self.tabs.addTab(self._wrap_widget(self.card_attendance), 'Asistencia')
        self.tabs.addTab(self._wrap_widget(self.card_access), 'Acceso')
        self.tabs.addTab(self._wrap_widget(self.card_reports), 'Reportes')
        self.tabs.addTab(self._wrap_widget(self.card_system), 'Sistema')

        # Status bar for messages
        sb = QtWidgets.QStatusBar(self)
        self.setStatusBar(sb)

        # Secondary toolbar (placeholders)
        tb = QtWidgets.QToolBar('Navegación', self)
        self.addToolBar(tb)
        tb.addAction('Home')
        tb.addAction('Licencia')
        tb.addAction('Acerca de')

        # Toast messages
        self.toast = MessageToast(self)
        self.card_terminal.attach_toast(self.toast)
        try:
            self.card_attendance.attach_toast(self.toast)
        except Exception:
            pass

        # Auto-refresh attendance when new events are saved
        try:
            self.card_terminal.events_saved.connect(lambda _count: self.card_attendance.refresh())
        except Exception:
            pass

        # Reprogram Terminal scheduled downloads when system settings change
        try:
            self.card_system.settings_changed.connect(lambda: self.card_terminal._load_settings())
        except Exception:
            pass

        # Refresh Attendance view to reflect date/time format changes
        try:
            self.card_system.settings_changed.connect(lambda: self.card_attendance.refresh())
        except Exception:
            pass

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.toast._reposition()

    def _wrap_label(self, text: str) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget(); l = QtWidgets.QVBoxLayout(w); l.addStretch(1); l.addWidget(QtWidgets.QLabel(text), 0, QtCore.Qt.AlignmentFlag.AlignCenter); l.addStretch(1)
        return w

    def _wrap_widget(self, w: QtWidgets.QWidget) -> QtWidgets.QWidget:
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.addWidget(w)
        return container
