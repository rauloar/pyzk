from PyQt5 import QtWidgets
from datetime import datetime
from data.db import init_db
from data.repositories import AttendanceRepository, DeviceRepository, SettingsRepository


class AttendanceCard(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        init_db()
        self.att_repo = AttendanceRepository()
        self.dev_repo = DeviceRepository()
        self.set_repo = SettingsRepository()
        self._toast = None
        self._last_fmt = None  # track last shown format to avoid duplicate toasts
        self._build_ui()
        self._load()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        toolbar = QtWidgets.QHBoxLayout()
        self.btn_refresh = QtWidgets.QPushButton('Refrescar')
        self.btn_export = QtWidgets.QPushButton('Exportar…')
        toolbar.addWidget(self.btn_refresh)
        toolbar.addWidget(self.btn_export)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)
        self.table = QtWidgets.QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(['ID','Dispositivo','User ID','Timestamp','Status','Punch'])
        self.table.setColumnHidden(0, True)
        header = self.table.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(True)
        layout.addWidget(self.table)
        # Use refresh() to ensure post-load hooks (like toast) run
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_export.clicked.connect(self._export_choose)

    def _load(self):
        # Reset table contents to force re-render
        try:
            self.table.setSortingEnabled(False)
        except Exception:
            pass
        self.table.clearContents()
        self.table.setRowCount(0)
        devices = {d.id: d for d in self.dev_repo.list()}
        # Fetch all attendance entries; for brevity we rely on repo-level pagination later if needed
        # Here, we use a direct connection to read rows to avoid expanding repository API
        from data.db import get_conn
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id,device_id,user_id,timestamp,status,punch FROM attendance ORDER BY id DESC LIMIT 1000")
            rows = cur.fetchall()
        for r in rows:
            rr = self.table.rowCount(); self.table.insertRow(rr)
            dev_name = devices.get(r[1]).name if devices.get(r[1]) else ''
            self.table.setItem(rr, 0, QtWidgets.QTableWidgetItem(str(r[0]) if r[0] is not None else ''))
            self.table.setItem(rr, 1, QtWidgets.QTableWidgetItem(dev_name))
            self.table.setItem(rr, 2, QtWidgets.QTableWidgetItem(str(r[2]) if r[2] is not None else ''))
            self.table.setItem(rr, 3, QtWidgets.QTableWidgetItem(self._fmt_ts(r[3])))
            self.table.setItem(rr, 4, QtWidgets.QTableWidgetItem(str(r[4]) if r[4] is not None else ''))
            self.table.setItem(rr, 5, QtWidgets.QTableWidgetItem(str(r[5]) if r[5] is not None else ''))
        # Ensure UI updates to reflect new text formatting
        try:
            self.table.resizeColumnsToContents()
            self.table.viewport().update()
            self.table.setSortingEnabled(True)
        except Exception:
            pass

    def refresh(self):
        self._load()
        # After refresh, optionally show active format toast
        if self._toast:
            date_qt = self.set_repo.get('date_format') or 'dd/MM/yyyy'
            time_qt = self.set_repo.get('time_format') or 'HH:mm'
            clock_fmt = self.set_repo.get('clock_format') or '24'
            fmt_tuple = (time_qt, date_qt, clock_fmt)
            if fmt_tuple != self._last_fmt:
                clock_text = '24 hs' if clock_fmt == '24' else 'AM/PM'
                self._toast.show_message(f"Asistencia actualizada. Formato: {time_qt} {date_qt}, reloj {clock_text}")
                self._last_fmt = fmt_tuple

    def attach_toast(self, toast):
        self._toast = toast

    def _export_choose(self):
        # Offer CSV or Excel via file dialog filter selection
        path, selected_filter = QtWidgets.QFileDialog.getSaveFileName(
            self,
            'Guardar asistencia',
            'asistencias.csv',
            'CSV (*.csv);;Excel (*.xlsx)'
        )
        if not path:
            return
        if selected_filter.startswith('CSV') or path.lower().endswith('.csv'):
            self._export_csv_to(path)
        else:
            if not path.lower().endswith('.xlsx'):
                path += '.xlsx'
            self._export_excel_to(path)

    def _export_csv_to(self, path: str):
        import csv
        with open(path, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['device','user_id','timestamp','status','punch'])
            for r in range(self.table.rowCount()):
                device = self.table.item(r,1).text() if self.table.item(r,1) else ''
                user_id = self.table.item(r,2).text() if self.table.item(r,2) else ''
                ts = self.table.item(r,3).text() if self.table.item(r,3) else ''
                status = self.table.item(r,4).text() if self.table.item(r,4) else ''
                punch = self.table.item(r,5).text() if self.table.item(r,5) else ''
                w.writerow([device, user_id, ts, status, punch])
        QtWidgets.QMessageBox.information(self, 'Exportar', 'CSV exportado')

    def _export_excel_to(self, path: str):
        # Minimal Excel export using SpreadsheetML (XML) to avoid dependencies
        # Excel opens this format as a workbook
        def esc(s: str) -> str:
            return (s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')) if s is not None else ''
        rows = []
        # Header
        rows.append(['device','user_id','timestamp','status','punch'])
        # Data
        for r in range(self.table.rowCount()):
            device = self.table.item(r,1).text() if self.table.item(r,1) else ''
            user_id = self.table.item(r,2).text() if self.table.item(r,2) else ''
            ts = self.table.item(r,3).text() if self.table.item(r,3) else ''
            status = self.table.item(r,4).text() if self.table.item(r,4) else ''
            punch = self.table.item(r,5).text() if self.table.item(r,5) else ''
            rows.append([device, user_id, ts, status, punch])
        xml_header = (
            '<?xml version="1.0"?>\n'
            '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"\n'
            ' xmlns:o="urn:schemas-microsoft-com:office:office"\n'
            ' xmlns:x="urn:schemas-microsoft-com:office:excel"\n'
            ' xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"\n'
            ' xmlns:html="http://www.w3.org/TR/REC-html40">\n'
            '<Worksheet ss:Name="Asistencia"><Table>'
        )
        xml_rows = []
        for row in rows:
            cells = ''.join([f'<Cell><Data ss:Type="String">{esc(str(col))}</Data></Cell>' for col in row])
            xml_rows.append(f'<Row>{cells}</Row>')
        xml_footer = '</Table></Worksheet></Workbook>'
        content = xml_header + ''.join(xml_rows) + xml_footer
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        QtWidgets.QMessageBox.information(self, 'Exportar', 'Excel exportado')

    def _fmt_ts(self, ts_val) -> str:
        if ts_val is None:
            return ''
        s = str(ts_val).strip()
        if not s:
            return ''
        # Normalize Zulu to offset for fromisoformat
        s_norm = s.replace('Z', '+00:00')
        # Get UI formats from settings and map explicitly to strftime
        date_qt = self.set_repo.get('date_format') or 'dd/MM/yyyy'
        time_qt = self.set_repo.get('time_format') or 'HH:mm'
        clock_fmt = self.set_repo.get('clock_format') or '24'
        date_map = {
            'dd/MM/yyyy': '%d/%m/%Y',
            'MM/dd/yyyy': '%m/%d/%Y',
            'yyyy-MM-dd': '%Y-%m-%d',
        }
        time_map = {
            'HH:mm': '%H:%M',
            'HH:mm:ss': '%H:%M:%S',
        }
        # Base time fmt from selection
        base_time = time_map.get(time_qt, '%H:%M')
        # Apply 12h clock if selected
        if clock_fmt == '12':
            base_time = base_time.replace('%H', '%I')
            # ensure seconds mapping remains
            if '%S' in base_time:
                base_time = base_time.replace('%S', '%S')
            # append AM/PM designator
            base_time = base_time + ' %p'
        py_fmt = base_time + ' ' + date_map.get(date_qt, '%d/%m/%Y')
        # First try ISO parser (handles YYYY-MM-DD[ T]HH:MM:SS[.fff][+HH:MM])
        try:
            dt = datetime.fromisoformat(s_norm)
            return dt.strftime(py_fmt)
        except Exception:
            pass
        # Try common formats
        fmts = [
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y/%m/%d %H:%M:%S',
            '%Y/%m/%d %H:%M',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M',
        ]
        for fmt in fmts:
            try:
                dt = datetime.strptime(s, fmt)
                return dt.strftime(py_fmt)
            except Exception:
                continue
        # Fallback to original string if unknown format
        return s

    def _to_iso_str(self, ts_val) -> str:
        if ts_val is None:
            return ''
        s = str(ts_val).strip()
        if not s:
            return ''
        s_norm = s.replace('Z', '+00:00')
        try:
            dt = datetime.fromisoformat(s_norm)
            return dt.isoformat()
        except Exception:
            pass
        fmts = [
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y/%m/%d %H:%M:%S',
            '%Y/%m/%d %H:%M',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M',
        ]
        for fmt in fmts:
            try:
                dt = datetime.strptime(s, fmt)
                return dt.isoformat()
            except Exception:
                continue
        return s
