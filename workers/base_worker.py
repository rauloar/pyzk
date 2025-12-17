from PyQt5 import QtCore


class BaseWorker(QtCore.QObject):
    progress = QtCore.pyqtSignal(int, str)
    result = QtCore.pyqtSignal(object)
    error = QtCore.pyqtSignal(str)
    log = QtCore.pyqtSignal(str, str)  # message, level: INFO/WARN/ERROR

    def run(self):  # override in subclasses
        pass


_ACTIVE_THREADS = set()


def run_in_thread(worker: BaseWorker) -> QtCore.QThread:
    thread = QtCore.QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)

    # Ensure orderly stop and cleanup
    worker.result.connect(lambda _: thread.quit())
    worker.error.connect(lambda _: thread.quit())

    # Track thread to prevent GC while running
    _ACTIVE_THREADS.add(thread)

    def _cleanup():
        try:
            worker.deleteLater()
        finally:
            _ACTIVE_THREADS.discard(thread)
            thread.deleteLater()

    thread.finished.connect(_cleanup)
    thread.start()
    return thread
