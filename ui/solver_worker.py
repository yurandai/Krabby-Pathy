"""Background worker thread for the NLP solve."""
from __future__ import annotations
import threading
import traceback

from PySide6.QtCore import QObject, Signal

from core.state import ScenarioState


class SolverWorker(QObject):
    progress = Signal(str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, state: ScenarioState, pipeline):
        super().__init__()
        self.state = state
        self.pipeline = pipeline
        self._cancel = threading.Event()

    def cancel(self):
        self._cancel.set()

    def run(self):
        try:
            from core.nlp_solver import solve_pipeline
            result = solve_pipeline(
                self.state, self.pipeline,
                progress_cb=self.progress.emit,
                cancel_event=self._cancel,
            )
            self.finished.emit(result)
        except Exception as e:
            self.failed.emit(f"{type(e).__name__}: {e}\n"
                             f"{traceback.format_exc()}")