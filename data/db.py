import os
import sqlite3
from contextlib import contextmanager

_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.db')


def init_db() -> None:
    conn = sqlite3.connect(_DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                ip TEXT NOT NULL,
                port INTEGER NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                password INTEGER DEFAULT 0,
                zone TEXT,
                last_seen TEXT,
                last_download TEXT,
                last_sync TEXT,
                location TEXT,
                serialnumber TEXT,
                firmware TEXT,
                platform TEXT,
                device_name TEXT,
                mac TEXT,
                last_error TEXT
            )
            """
        )
        # Backfill: add password column if missing in existing DBs
        cur.execute("PRAGMA table_info(devices)")
        cols = [row[1] for row in cur.fetchall()]
        if 'password' not in cols:
            cur.execute("ALTER TABLE devices ADD COLUMN password INTEGER DEFAULT 0")
        backfill_cols = ['location','serialnumber','firmware','platform','device_name','mac','last_error']
        for bc in backfill_cols:
            if bc not in cols:
                cur.execute(f"ALTER TABLE devices ADD COLUMN {bc} TEXT")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                uid INTEGER,
                name TEXT,
                card TEXT,
                password TEXT,
                privilege INTEGER,
                group_id TEXT,
                dept TEXT,
                photo_path TEXT,
                updated_at TEXT
            )
            """
        )
        # Backfill: add missing columns for full user details
        cur.execute("PRAGMA table_info(employees)")
        ecols = [row[1] for row in cur.fetchall()]
        if 'uid' not in ecols:
            cur.execute("ALTER TABLE employees ADD COLUMN uid INTEGER")
        if 'privilege' not in ecols:
            cur.execute("ALTER TABLE employees ADD COLUMN privilege INTEGER")
        if 'group_id' not in ecols:
            cur.execute("ALTER TABLE employees ADD COLUMN group_id TEXT")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER,
                user_id TEXT,
                timestamp TEXT,
                status INTEGER,
                punch INTEGER,
                raw_json TEXT,
                workstate_id INTEGER,
                workcode_id INTEGER,
                punch_source TEXT,
                FOREIGN KEY(device_id) REFERENCES devices(id)
            )
            """
        )
        # Backfill attendance extra columns
        cur.execute("PRAGMA table_info(attendance)")
        acols = [row[1] for row in cur.fetchall()]
        for bc in ['workstate_id','workcode_id','punch_source']:
            if bc not in acols:
                cur.execute(f"ALTER TABLE attendance ADD COLUMN {bc} {'INTEGER' if bc!='punch_source' else 'TEXT'}")
        # Indexes for faster queries
        cur.execute("CREATE INDEX IF NOT EXISTS idx_att_device_ts ON attendance(device_id, timestamp)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_att_user_ts ON attendance(user_id, timestamp)")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        # Departments normalization (must run before closing connection)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                code TEXT
            )
            """
        )
        # Backfill employees.department_id
        cur.execute("PRAGMA table_info(employees)")
        ecols2 = [row[1] for row in cur.fetchall()]
        if 'department_id' not in ecols2:
            cur.execute("ALTER TABLE employees ADD COLUMN department_id INTEGER")
        conn.commit()
    finally:
        conn.close()

@contextmanager
def get_conn():
    conn = sqlite3.connect(_DB_PATH)
    try:
        yield conn
    finally:
        conn.close()
