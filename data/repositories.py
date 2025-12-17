from typing import List, Optional, Tuple
from .db import get_conn
from .models import Device, Employee, Attendance


class DeviceRepository:
    def list(self) -> List[Device]:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id,name,ip,port,enabled,password,zone,last_seen,last_download,last_sync,location,serialnumber,firmware,platform,device_name,mac,last_error FROM devices ORDER BY id")
            rows = cur.fetchall()
        return [Device(id=r[0], name=r[1], ip=r[2], port=r[3], enabled=bool(r[4]), password=int(r[5] or 0), zone=r[6] or "", last_seen=r[7], last_download=r[8], last_sync=r[9], location=r[10] or "", serialnumber=r[11], firmware=r[12], platform=r[13], device_name=r[14], mac=r[15], last_error=r[16]) for r in rows]

    def get(self, device_id: int) -> Optional[Device]:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id,name,ip,port,enabled,password,zone,last_seen,last_download,last_sync,location,serialnumber,firmware,platform,device_name,mac,last_error FROM devices WHERE id=?", (device_id,))
            r = cur.fetchone()
        if not r:
            return None
        return Device(id=r[0], name=r[1], ip=r[2], port=r[3], enabled=bool(r[4]), password=int(r[5] or 0), zone=r[6] or "", last_seen=r[7], last_download=r[8], last_sync=r[9], location=r[10] or "", serialnumber=r[11], firmware=r[12], platform=r[13], device_name=r[14], mac=r[15], last_error=r[16])

    def create(self, d: Device) -> Optional[int]:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO devices(name,ip,port,enabled,password,zone,last_seen,last_download,last_sync,location,serialnumber,firmware,platform,device_name,mac,last_error) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (d.name, d.ip, d.port, 1 if d.enabled else 0, int(d.password or 0), d.zone, d.last_seen, d.last_download, d.last_sync, d.location, d.serialnumber, d.firmware, d.platform, d.device_name, d.mac, d.last_error),
            )
            conn.commit()
            return cur.lastrowid

    def update(self, d: Device) -> None:
        if d.id is None:
            return
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE devices SET name=?, ip=?, port=?, enabled=?, password=?, zone=?, last_seen=?, last_download=?, last_sync=?, location=?, serialnumber=?, firmware=?, platform=?, device_name=?, mac=?, last_error=? WHERE id=?",
                (d.name, d.ip, d.port, 1 if d.enabled else 0, int(d.password or 0), d.zone, d.last_seen, d.last_download, d.last_sync, d.location, d.serialnumber, d.firmware, d.platform, d.device_name, d.mac, d.last_error, d.id),
            )
            conn.commit()

    def delete(self, device_id: int) -> None:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM devices WHERE id=?", (device_id,))
            conn.commit()


class EmployeeRepository:
    def list(self) -> List[Employee]:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id,user_id,uid,name,card,password,privilege,group_id,dept,photo_path,updated_at FROM employees ORDER BY id")
            rows = cur.fetchall()
        return [Employee(id=r[0], user_id=r[1], uid=r[2], name=r[3] or "", card=r[4] or "", password=r[5] or "", privilege=r[6], group_id=r[7] or "", dept=r[8] or "", photo_path=r[9] or "", updated_at=r[10]) for r in rows]

    def get(self, emp_id: int) -> Optional[Employee]:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id,user_id,uid,name,card,password,privilege,group_id,dept,photo_path,updated_at FROM employees WHERE id=?", (emp_id,))
            r = cur.fetchone()
        if not r:
            return None
        return Employee(id=r[0], user_id=r[1], uid=r[2], name=r[3] or "", card=r[4] or "", password=r[5] or "", privilege=r[6], group_id=r[7] or "", dept=r[8] or "", photo_path=r[9] or "", updated_at=r[10])

    def upsert_many(self, employees: List[Employee]) -> None:
        with get_conn() as conn:
            cur = conn.cursor()
            for e in employees:
                cur.execute(
                    "SELECT id FROM employees WHERE user_id=?",
                    (e.user_id,)
                )
                r = cur.fetchone()
                if r:
                    cur.execute(
                        "UPDATE employees SET uid=?, name=?, card=?, password=?, privilege=?, group_id=?, dept=?, photo_path=?, updated_at=? WHERE user_id=?",
                        (e.uid, e.name, e.card, e.password, e.privilege, e.group_id, e.dept, e.photo_path, e.updated_at, e.user_id),
                    )
                else:
                    cur.execute(
                        "INSERT INTO employees(user_id,uid,name,card,password,privilege,group_id,dept,photo_path,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (e.user_id, e.uid, e.name, e.card, e.password, e.privilege, e.group_id, e.dept, e.photo_path, e.updated_at),
                    )
            conn.commit()

    def update(self, e: Employee) -> None:
        if e.id is None:
            return
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE employees SET user_id=?, uid=?, name=?, card=?, password=?, privilege=?, group_id=?, dept=?, photo_path=?, updated_at=? WHERE id=?",
                (e.user_id, e.uid, e.name, e.card, e.password, e.privilege, e.group_id, e.dept, e.photo_path, e.updated_at, e.id),
            )
            conn.commit()

    def delete(self, emp_id: int) -> None:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM employees WHERE id=?", (emp_id,))
            conn.commit()


class AttendanceRepository:
    def insert_many(self, device_id: int, events: List[Attendance]) -> None:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.executemany(
                "INSERT INTO attendance(device_id,user_id,timestamp,status,punch,raw_json) VALUES (?,?,?,?,?,?)",
                [ (device_id, e.user_id, e.timestamp, e.status, e.punch, e.raw_json) for e in events ]
            )
            conn.commit()


class SettingsRepository:
    def get(self, key: str) -> Optional[str]:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM settings WHERE key=?", (key,))
            r = cur.fetchone()
        return r[0] if r else None

    def set(self, key: str, value: str) -> None:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO settings(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
            conn.commit()

class DepartmentRepository:
    def list(self) -> List[Tuple[int, str, Optional[str]]]:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id,name,code FROM departments ORDER BY name")
            return cur.fetchall()

    def upsert(self, name: str, code: Optional[str] = None) -> int:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM departments WHERE name=?", (name,))
            r = cur.fetchone()
            if r:
                cur.execute("UPDATE departments SET code=? WHERE id=?", (code, r[0]))
                conn.commit()
                return r[0]
            cur.execute("INSERT INTO departments(name,code) VALUES (?,?)", (name, code))
            conn.commit()
            return cur.lastrowid

