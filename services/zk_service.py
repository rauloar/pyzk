from typing import Any, Dict, List
from datetime import datetime
from zk import ZK


class ZKService:
    def __init__(self):
        self._connections: Dict[str, ZK] = {}

    def _key(self, ip: str, port: int) -> str:
        return f"{ip}:{port}"

    def connect(self, ip: str, port: int, password: int = 0, timeout: int = 5) -> None:
        key = self._key(ip, port)
        if key in self._connections:
            return
        zk = ZK(ip, port=port, password=password, ommit_ping=False, verbose=False, timeout=timeout)
        zk.connect()
        self._connections[key] = zk

    def disconnect(self, ip: str, port: int) -> None:
        key = self._key(ip, port)
        zk = self._connections.pop(key, None)
        if zk:
            try:
                zk.disconnect()
            except Exception:
                pass

    def is_connected(self, ip: str, port: int) -> bool:
        return self._key(ip, port) in self._connections

    def get_device_info(self, ip: str, port: int) -> Dict[str, Any]:
        key = self._key(ip, port)
        zk = self._connections.get(key)
        if not zk:
            raise RuntimeError("Not connected")
        info = {
            'serial': zk.get_serialnumber(),
            'name': zk.get_device_name(),
            'fw': zk.get_firmware_version(),
            'platform': zk.get_platform(),
            'mac': zk.get_mac(),
            'time': zk.get_time(),
        }
        zk.read_sizes()
        info.update({'users': zk.users, 'fingers': zk.fingers, 'records': zk.records})
        return info

    def get_users(self, ip: str, port: int) -> List[dict]:
        key = self._key(ip, port)
        zk = self._connections.get(key)
        if not zk:
            raise RuntimeError("Not connected")
        return zk.get_users() or []

    def get_attendance(self, ip: str, port: int) -> List[dict]:
        key = self._key(ip, port)
        zk = self._connections.get(key)
        if not zk:
            raise RuntimeError("Not connected")
        return zk.get_attendance() or []

    def clear_attendance(self, ip: str, port: int) -> None:
        key = self._key(ip, port)
        zk = self._connections.get(key)
        if not zk:
            raise RuntimeError("Not connected")
        zk.clear_attendance()

    def disable_device(self, ip: str, port: int) -> None:
        key = self._key(ip, port)
        zk = self._connections.get(key)
        if not zk:
            raise RuntimeError("Not connected")
        zk.disable_device()

    def enable_device(self, ip: str, port: int) -> None:
        key = self._key(ip, port)
        zk = self._connections.get(key)
        if not zk:
            raise RuntimeError("Not connected")
        zk.enable_device()
