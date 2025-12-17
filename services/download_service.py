from typing import List, Any
from datetime import datetime
import json
from data.models import Attendance
from data.repositories import AttendanceRepository
from .zk_service import ZKService


class DownloadService:
    def __init__(self, zk: ZKService, attendance_repo: AttendanceRepository):
        self.zk = zk
        self.attendance_repo = attendance_repo

    def download_events(self, device_id: int, ip: str, port: int) -> int:
        att = self.zk.get_attendance(ip, port)
        return self._persist(device_id, att)

    def persist_events(self, device_id: int, events_raw: List[Any]) -> int:
        return self._persist(device_id, events_raw)

    def _persist(self, device_id: int, att: List[Any]) -> int:
        events: List[Attendance] = []
        for a in att:
            # a fields can vary; normalize
            user_id = str(getattr(a, 'user_id', getattr(a, 'uid', ''))) if hasattr(a, '__dict__') else str(a.get('user_id') or a.get('uid') or '')
            ts = getattr(a, 'timestamp', None) if hasattr(a, '__dict__') else a.get('timestamp')
            status = int(getattr(a, 'status', 0)) if hasattr(a, '__dict__') else int(a.get('status', 0))
            punch = int(getattr(a, 'punch', 0)) if hasattr(a, '__dict__') else int(a.get('punch', 0))
            ts_text = str(ts)
            events.append(Attendance(
                id=None,
                device_id=device_id,
                user_id=user_id,
                timestamp=ts_text,
                status=status,
                punch=punch,
                raw_json=json.dumps(getattr(a, '__dict__', a), default=str)
            ))
        self.attendance_repo.insert_many(device_id, events)
        return len(events)
