from dataclasses import dataclass
from typing import Optional


@dataclass
class Device:
    id: Optional[int]
    name: str
    ip: str
    port: int
    enabled: bool = True
    password: int = 0
    zone: str = ""
    location: str = ""
    serialnumber: Optional[str] = None
    firmware: Optional[str] = None
    platform: Optional[str] = None
    device_name: Optional[str] = None
    mac: Optional[str] = None
    last_error: Optional[str] = None
    last_seen: Optional[str] = None
    last_download: Optional[str] = None
    last_sync: Optional[str] = None


@dataclass
class Employee:
    id: Optional[int]
    user_id: str
    uid: Optional[int] = None
    name: str = ""
    card: str = ""
    password: str = ""
    privilege: Optional[int] = None
    group_id: str = ""
    dept: str = ""
    photo_path: str = ""
    updated_at: Optional[str] = None


@dataclass
class Attendance:
    id: Optional[int]
    device_id: Optional[int]
    user_id: str
    timestamp: str
    status: int
    punch: int
    workstate_id: Optional[int] = None
    workcode_id: Optional[int] = None
    punch_source: Optional[str] = None
    raw_json: str = ""
