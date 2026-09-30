"""Main window — tabs, worker thread, playback, profiles, export."""
from __future__ import annotations
from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import (
    QMainWindow, QSplitter, QScrollArea, QWidget, QVBoxLayout,
    QHBoxLayout, QTabWidget, QPushButton, QLabel, QApplication,
    QProgressBar, QMessageBox
)

from core import config as C
from core.state import ScenarioState
from core.validation import validate_state
from core.astar import run_astar_segmented
from core.config import APP_DISPLAY

from ui.field_canvas import FieldCanvas
from ui.obstacle_panel import ObstaclePanel
from ui.poses_panel import PosesPanel
from ui.solver_panel import SolverPanel
from ui.profiles_panel import ProfilesPanel
from ui.export_panel import ExportPanel
from ui.playback_bar import PlaybackBar
from ui.solver_worker import SolverWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_DISPLAY)
        self.resize(1650, 980)

        self.state = ScenarioState()
        self.astar_path = None
        self.nlp_result = None
        self.worker = None
        self.worker_thread = None

        splitter = QSplitter(Qt.Horizontal)

        # ---- Left: field + playback ----
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.field = FieldCanvas(self.state)
        self.field.setMinimumSize(420, 420)
        field_scroll = QScrollArea()
        field_scroll.setWidget(self.field)
        field_scroll.setWidgetResizable(True)
        left_layout.addWidget(field_scroll, 1)

        self.playback = PlaybackBar()
        left_layout.addWidget(self.playback)

        splitter.addWidget(left)

        # ---- Right: tabs ----
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 4, 4, 4)

        self.tabs = QTabWidget()
        self.poses_panel = PosesPanel(self.state)
        self.obstacle_panel = ObstaclePanel()
        self.solver_panel = SolverPanel(self.state)
        self.profiles_panel = ProfilesPanel()
        self.export_panel = ExportPanel(self.state)

        self.state.obstacles = self.obstacle_panel.obstacles

        self.tabs.addTab(self.poses_panel, "Poses & Robot")
        self.tabs.addTab(self.obstacle_panel, "Obstacles")
        self.tabs.addTab(self.solver_panel, "Solver")
        self.tabs.addTab(self.profiles_panel, "Profiles")
        self.tabs.addTab(self.export_panel, "Export")
        right_layout.addWidget(self.tabs, 1)

        # Banner
        self.banner = QLabel("")
        self.banner.setWordWrap(True)
        self.banner.setStyleSheet(
            "background: #ffe6e6; color: #a00000; "
            "border: 1px solid #d00000; border-radius: 4px; "
            "padding: 6px; font-size: 12px;"
        )
        self.banner.setVisible(False)
        right_layout.addWidget(self.banner)

        # Progress
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        self.progress_label.setStyleSheet("color: #333; font-size: 11px;")
        right_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        right_layout.addWidget(self.progress_bar)

        # Buttons
        btn_row = QHBoxLayout()
        self.run_astar_btn = QPushButton("▶  Run A*")
        self.run_nlp_btn = QPushButton("▶▶  Run NLP")
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setVisible(False)
        self.clear_btn = QPushButton("Clear")
        btn_row.addWidget(self.run_astar_btn, 2)
        btn_row.addWidget(self.run_nlp_btn, 2)
        btn_row.addWidget(self.cancel_btn, 1)
        btn_row.addWidget(self.clear_btn, 1)
        right_layout.addLayout(btn_row)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([1050, 550])
        self.setCentralWidget(splitter)

        # ---- Wiring ----
        self.poses_panel.changed.connect(self._on_state_changed)
        self.solver_panel.changed.connect(self._on_state_changed)
        self.obstacle_panel.obstacles_changed.connect(self._on_obstacles_changed)
        self.run_astar_btn.clicked.connect(self._run_astar)
        self.run_nlp_btn.clicked.connect(self._run_nlp)
        self.cancel_btn.clicked.connect(self._cancel_nlp)
        self.clear_btn.clicked.connect(self._clear_results)
        self.playback.time_changed.connect(self._on_playback_time)

        self._on_state_changed()

    # ==================================================================
    # State-change handlers
    # ==================================================================
    def _on_state_changed(self):
        # Update obstacle panel's recommended min radius
        self.obstacle_panel.set_min_radius(
            self.state.recommended_obstacle_radius)
        self._invalidate_results()
        self.field.redraw()
        self._validate()

    def _on_obstacles_changed(self, obstacles):
        self.state.obstacles = obstacles
        self._invalidate_results()
        self.field.redraw()
        self._validate()

    def _invalidate_results(self):
        if self.astar_path is not None:
            self.astar_path = None
            self.field.set_astar_path(None)
        if self.nlp_result is not None:
            self.nlp_result = None
            self.field.clear_trajectory()
            self.playback.clear()
            self.profiles_panel.clear()
            self.export_panel.clear()

    # ==================================================================
    # Validation
    # ==================================================================
    def _validate(self):
        ok, msg = validate_state(self.state)
        self.run_astar_btn.setEnabled(ok)
        self.run_nlp_btn.setEnabled(ok)
        if not ok:
            self.banner.setText(msg)
            self.banner.setVisible(True)
        elif not self.banner.text().startswith("NLP"):
            self.banner.setVisible(False)

        status = f"{len(self.state.obstacles)} obstacle(s)"
        if self.astar_path is not None:
            status += f"  |  A* path: {len(self.astar_path)} nodes"
        if self.nlp_result is not None:
            status += (f"  |  NLP T = {self.nlp_result['T']:.3f} s "
                       f"({self.nlp_result['final_phase']})")
        self.statusBar().showMessage(status)

    # ==================================================================
    # Run A*
    # ==================================================================
    def _run_astar(self):
        ok, msg = validate_state(self.state)
        if not ok:
            self.banner.setText(msg)
            self.banner.setVisible(True)
            return

        self.astar_path = None
        self.field.set_astar_path(None)
        self.field.redraw()

        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()
        try:
            path, err = run_astar_segmented(
                (self.state.start_x, self.state.start_y),
                (self.state.goal_x, self.state.goal_y),
                self.state.waypoints,
                self.state.obstacles, C.FIELD_MAX,
                res=self.state.ASTAR_RES,
                robot_W=self.state.robot_half_width,
                robot_L=self.state.robot_half_length,
            )
        finally:
            QApplication.restoreOverrideCursor()

        if path is None:
            self.banner.setText(err or "A* failed.")
            self.banner.setVisible(True)
            self.statusBar().showMessage("A* failed.")
            return

        self.astar_path = path
        self.field.set_astar_path(path)
        self.field.redraw()
        self.banner.setVisible(False)
        self._validate()

    # ==================================================================
    # Run NLP
    # ==================================================================
    def _run_nlp(self):
        ok, msg = validate_state(self.state)
        if not ok:
            self.banner.setText(msg)
            self.banner.setVisible(True)
            return

        if self.worker_thread is not None:
            return

        if self.astar_path is None:
            self._run_astar()

        pipeline = self.solver_panel.get_pipeline()

        self.run_astar_btn.setEnabled(False)
        self.run_nlp_btn.setEnabled(False)
        self.cancel_btn.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress_label.setText("Starting…")
        self.banner.setVisible(False)

        self.field.clear_trajectory()
        self.playback.clear()
        self.profiles_panel.clear()
        self.export_panel.clear()

        self.worker = SolverWorker(self.state, pipeline)
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._on_nlp_progress)
        self.worker.finished.connect(self._on_nlp_finished)
        self.worker.failed.connect(self._on_nlp_failed)
        self.worker_thread.start()

    def _cancel_nlp(self):
        if self.worker is not None:
            self.worker.cancel()
            self.progress_label.setText("Cancelling…")

    def _on_nlp_progress(self, phase_name):
        self.progress_label.setText(f"Running {phase_name}…")

    def _on_nlp_finished(self, result):
        self._teardown_worker()
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)

        if result.get('final_phase') is None:
            errs = result.get('errors', {})
            msg_lines = ["NLP failed."]
            if errs:
                for k, v in errs.items():
                    msg_lines.append(f"Phase {k}: {v}")
            text = "\n".join(msg_lines)
            self.banner.setText(text)
            self.banner.setVisible(True)
            self.statusBar().showMessage("NLP failed — see banner.")
            self.solver_panel.set_report(text)
            self._validate()
            return

        self.nlp_result = result
        X, U, T = result['X'], result['U'], result['T']

        self.field.set_trajectory(X, U, T)
        self.playback.set_trajectory(T)
        self.profiles_panel.set_trajectory(X, U, T)
        self.export_panel.set_trajectory(result)

        report = result.get('report', '')
        if result.get('errors'):
            report += "\n\nNote: some phases failed:\n"
            for k, v in result['errors'].items():
                report += f"  {k}: {v}\n"
        self.solver_panel.set_report(report)

        if result.get('errors'):
            self.banner.setText(
                "NLP completed, but some phases failed:\n"
                + "\n".join(f"  Phase {k}: {v}"
                            for k, v in result['errors'].items()))
            self.banner.setVisible(True)
        else:
            self.banner.setVisible(False)

        self._validate()

    def _on_nlp_failed(self, msg):
        self._teardown_worker()
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.banner.setText(f"NLP crashed:\n{msg.splitlines()[0]}")
        self.banner.setVisible(True)
        self.statusBar().showMessage("NLP crashed — see report.")
        self.solver_panel.set_report(msg)
        self._validate()

    def _teardown_worker(self):
        if self.worker_thread is not None:
            self.worker_thread.quit()
            self.worker_thread.wait()
        self.worker_thread = None
        self.worker = None
        self.run_astar_btn.setEnabled(True)
        self.run_nlp_btn.setEnabled(True)
        self.cancel_btn.setVisible(False)

    # ==================================================================
    # Playback / Clear
    # ==================================================================
    def _on_playback_time(self, t):
        if self.nlp_result is None:
            return
        self.field.set_animation_time(t)

    def _clear_results(self):
        self.astar_path = None
        self.field.set_astar_path(None)
        self.nlp_result = None
        self.field.clear_trajectory()
        self.playback.clear()
        self.profiles_panel.clear()
        self.export_panel.clear()
        self.solver_panel.set_report("")
        self._validate()

    # ==================================================================
    def closeEvent(self, event):
        if self.worker is not None:
            self.worker.cancel()
            if self.worker_thread is not None:
                self.worker_thread.quit()
                self.worker_thread.wait(2000)
        event.accept()