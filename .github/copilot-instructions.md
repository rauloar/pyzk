# GitHub Copilot Instructions for pyzk

Goal: Enable AI coding agents to be immediately productive in this repo by understanding architecture, workflows, and project-specific patterns.

## Overview
- Library + Desktop App: This repo contains the `pyzk` SDK (ZKTeco device protocol) and a PyQt5 desktop app "ZKTeco Manager" that uses it.
- Key domains:
  - `zk/`: Core device protocol implementation (`base.py`, `attendance.py`, `user.py`, `finger.py`, `const.py`, `exception.py`).
  - `services/`: App-facing service layer built on `pyzk` (`zk_service.py`, `download_service.py`, `sync_service.py`).
  - `ui/`: PyQt5 UI with `MainWindow` and module cards under `views/`.
  - `data/`: SQLite persistence (`db.py`, `models.py`, `repositories.py`).
  - `workers/`: QThreaded background workers coordinating long-running device operations.
  - `dialogs/`, `widgets/`: UI components (e.g., device dialog, message toast).

## App Architecture (Big Picture)
- Entrypoint: `app.py` starts a PyQt5 app, loads `ui/main_window.py`.
- Main window: `MainWindow` creates module tabs (Terminal, RRHH, Asistencia, Acceso, Reportes, Sistema). Each tab wraps a `views/*_card.py` widget.
- Service boundary:
  - `ZKService` encapsulates device operations (connect, disconnect, info, users, attendance, clear attendance). It wraps `zk.ZK` APIs and returns Python-native objects.
  - `DownloadService` persists attendance/users in SQLite via `data.repositories`.
- Data flow:
  - UI triggers a worker in `workers/zk_workers.py` which calls `ZKService` methods.
  - Results are emitted as Qt signals to update UI and optionally persisted via `DownloadService`.
  - `data/db.py` sets up tables; `models.py` defines simple dataclasses; `repositories.py` provides CRUD.
- Concurrency: Background tasks run via `workers/base_worker.py` + `QThread` to keep UI responsive; avoid blocking the GUI thread.
- Toast notifications: `widgets/message_toast.py` provides user feedback; `TerminalCard.attach_toast()` wires it.

## Coding Patterns & Conventions
- UI composition: Cards live in `ui/views/*_card.py`; add tabs by instantiating cards in `MainWindow` and wrapping with `_wrap_widget()`.
- Signals/Slots: Workers emit signals for completion/progress; UI connects to update state. Do not call device operations directly in the GUI thread.
- Services facade: Put ZKTeco device logic in `services/zk_service.py`; keep UI thin. Persist app data through `services/download_service.py` and `data/repositories.py`.
- SQLite access: Use `data/db.py` for connection/init; CRUD via `data/repositories.py`. Keep SQL localized there.
- Device operations: Use `zk.ZK` and `conn` pattern (connect → disable_device → perform → enable_device → disconnect). Handle exceptions and ensure device is re-enabled.
- Internationalization: UI labels use Spanish tab titles; keep consistent naming when adding modules.
- Files/paths: Assets under `assets/icons/` (fetch via `scripts/fetch_bootstrap_icons.py`). CSV exports may appear under `data/`.

## Developer Workflows
- Run desktop app:
  ```bash
  python -m venv .venv
  . .venv/Scripts/activate  # Windows
  pip install PyQt5
  python app.py
  ```
- Use library directly (examples in `example/`):
  ```bash
  python example/get_users.py
  python example/live_capture.py
  ```
- CLI tests & utilities:
  - Device tests: `python test_machine.py` (see README for flags).
  - Backup/Restore: `python test_backup_restore.py [filename]` (WARNING: destructive).
- Docs: Sphinx under `docs/` (`make.bat` on Windows). Update API docs when changing `zk/*`.
- Packaging: `setup.py` installs library; `pyzk.egg-info/` reflects distribution metadata.

## Integration Points
- `zk.ZK` protocol: Construct with host/port/password and call `connect()`. After getting `conn`, use methods like `get_users()`, `get_attendance()`, `clear_attendance()`, `test_voice(index)`.
- Workers → Services → UI: Add new long-running features by creating a worker class in `workers/zk_workers.py` that calls a method on `ZKService` and emits results.
- Persistence: To store new entities, add models in `data/models.py`, schemas in `data/db.py`, and CRUD in `data/repositories.py`; call from `download_service.py`.

## Examples (Project-Specific)
- Add a new tab:
  - Create `ui/views/new_card.py` widget.
  - In `ui/main_window.py`, instantiate and `self.tabs.addTab(self._wrap_widget(self.card_new), 'Nuevo')`.
- Add a device operation:
  - Implement in `services/zk_service.py` (wrap `zk.ZK` call).
  - Create worker in `workers/zk_workers.py` that invokes the service and emits signals.
  - Wire signals in the corresponding `*_card.py` to update UI.
- Persist attendance download:
  - Use `services/download_service.py` to write to SQLite via `data/repositories.py`.

## Gotchas
- Avoid UI blocking: Do not call `zk` operations inside the GUI thread; use workers.
- Device state: Always `disable_device()` during batch operations and `enable_device()` at the end.
- Large items: Attendance lists can be big; prefer streaming/iteration and batching in workers.
- Spanish UI: Keep consistency with existing labels and layout helpers (`_wrap_widget`).

## Key Files
- `ui/main_window.py` – app shell and module registration.
- `ui/views/terminal_card.py` – terminal management and downloads.
- `services/zk_service.py` – device API wrapper.
- `workers/zk_workers.py` – asynchronous operations.
- `data/db.py`, `data/repositories.py` – persistence.
- `README.md` – usage, CLI tools, voice codes, and run instructions.
