from typing import Optional
from PyQt5 import QtCore
from workers.base_worker import BaseWorker
from services.zk_service import ZKService
from data.models import Employee
from zk import const


class ConnectWorker(BaseWorker):
    def __init__(self, zk: ZKService, ip: str, port: int, password: int = 0):
        super().__init__()
        self.zk = zk
        self.ip = ip
        self.port = port
        self.password = password

    def run(self):
        try:
            self.log.emit(f"Conectando a {self.ip}:{self.port}", "INFO")
            self.zk.connect(self.ip, self.port, self.password)
            self.result.emit({"connected": True})
        except Exception as e:
            self.error.emit(str(e))


class DisconnectWorker(BaseWorker):
    def __init__(self, zk: ZKService, ip: str, port: int):
        super().__init__()
        self.zk = zk
        self.ip = ip
        self.port = port

    def run(self):
        try:
            self.zk.disconnect(self.ip, self.port)
            self.result.emit({"disconnected": True})
        except Exception as e:
            self.error.emit(str(e))


class DownloadEventsWorker(BaseWorker):
    def __init__(self, zk: ZKService, ip: str, port: int, clear_after: bool = False, password: int = 0):
        super().__init__()
        self.zk = zk
        self.ip = ip
        self.port = port
        self.clear_after = clear_after
        self.password = password

    def run(self):
        try:
            # Connect, disable, download, (optional) clear, enable, disconnect
            if not self.zk.is_connected(self.ip, self.port):
                self.log.emit(f"Conectando a {self.ip}:{self.port}", "INFO")
                self.zk.connect(self.ip, self.port, self.password)
            self.zk.disable_device(self.ip, self.port)
            events = self.zk.get_attendance(self.ip, self.port)
            self.log.emit(f"Descargados {len(events)} eventos", "INFO")
            if self.clear_after:
                self.zk.clear_attendance(self.ip, self.port)
                self.log.emit("Eventos borrados en el dispositivo", "INFO")
            # Re-enable and disconnect
            try:
                self.zk.enable_device(self.ip, self.port)
            finally:
                self.zk.disconnect(self.ip, self.port)
            self.result.emit(events)
        except Exception as e:
            self.error.emit(str(e))


class DownloadUsersWorker(BaseWorker):
    def __init__(self, zk: ZKService, ip: str, port: int):
        super().__init__()
        self.zk = zk
        self.ip = ip
        self.port = port

    def run(self):
        try:
            if not self.zk.is_connected(self.ip, self.port):
                self.log.emit(f"Conectando a {self.ip}:{self.port}", "INFO")
                self.zk.connect(self.ip, self.port)
            users = self.zk.get_users(self.ip, self.port)
            self.log.emit(f"Descargados {len(users)} usuarios", "INFO")
            self.result.emit(users)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            try:
                self.zk.disconnect(self.ip, self.port)
            except Exception:
                pass

class UploadUserWorker(BaseWorker):
    def __init__(self, zk: ZKService, ip: str, port: int, employee: Employee):
        super().__init__()
        self.zk = zk
        self.ip = ip
        self.port = port
        self.employee = employee

    def run(self):
        try:
            if not self.zk.is_connected(self.ip, self.port):
                self.log.emit(f"Conectando a {self.ip}:{self.port}", "INFO")
                self.zk.connect(self.ip, self.port)
            priv = const.USER_ADMIN if (self.employee.privilege == const.USER_ADMIN) else const.USER_DEFAULT
            # uid no cambia; actualizamos otros campos
            self.log.emit(f"Actualizando usuario {self.employee.user_id}", "INFO")
            self.zk._connections[f"{self.ip}:{self.port}"].set_user(
                uid=self.employee.uid,
                name=self.employee.name or '',
                privilege=priv,
                password=self.employee.password or '',
                group_id=self.employee.group_id or '',
                user_id=self.employee.user_id or '',
                card=int(self.employee.card or 0),
            )
            self.result.emit({"ok": True})
        except Exception as e:
            self.error.emit(str(e))
        finally:
            try:
                self.zk.disconnect(self.ip, self.port)
            except Exception:
                pass
