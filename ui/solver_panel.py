"""Tab: A* resolution, N, NLP weights, pipeline selection, report box."""
from __future__ import annotations
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QGroupBox,
    QDoubleSpinBox, QSpinBox, QPushButton, QComboBox, QTextEdit, QLabel
)
from core.state import ScenarioState


class SolverPanel(QWidget):
    changed = Signal()

    def __init__(self, state: ScenarioState, parent=None):
        super().__init__(parent)
        self.state = state

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        # ---- Pipeline ----
        gb = QGroupBox("Pipeline")
        form = QFormLayout(gb)
        self.pipeline_combo = QComboBox()
        self.pipeline_combo.addItems([
            "Full: A → B → C",
            "Skip L2: A → C",
            "L2 only: A → B",
            "Energy only: A",
        ])
        self.pipeline_combo.setCurrentIndex(0)
        form.addRow("Mode:", self.pipeline_combo)
        layout.addWidget(gb)

        # ---- A* ----
        gb = QGroupBox("A* configuration")
        form = QFormLayout(gb)
        self.res_spin = QDoubleSpinBox()
        self.res_spin.setRange(0.02, 1.0)
        self.res_spin.setSingleStep(0.01)
        self.res_spin.setDecimals(3)
        self.res_spin.setValue(state.ASTAR_RES)
        form.addRow("Grid resolution (m):", self.res_spin)
        layout.addWidget(gb)

        # ---- NLP ----
        gb = QGroupBox("NLP discretization")
        form = QFormLayout(gb)
        self.n_spin = QSpinBox()
        self.n_spin.setRange(10, 500)
        self.n_spin.setValue(state.N)
        form.addRow("Collocation intervals N:", self.n_spin)

        self.t_init_spin = QDoubleSpinBox()
        self.t_init_spin.setRange(0.1, 1000.0)
        self.t_init_spin.setSingleStep(1.0)
        self.t_init_spin.setDecimals(2)
        self.t_init_spin.setValue(state.T_INIT)
        form.addRow("Phase A fixed T (s):", self.t_init_spin)
        layout.addWidget(gb)

        # ---- Weights ----
        gb = QGroupBox("NLP weights")
        form = QFormLayout(gb)
        self.wobs_spin = QDoubleSpinBox()
        self.wobs_spin.setRange(0.0, 1e12); self.wobs_spin.setDecimals(0)
        self.wobs_spin.setValue(state.W_OBS)
        form.addRow("W_OBS:", self.wobs_spin)
        self.wdev_spin = QDoubleSpinBox()
        self.wdev_spin.setRange(0.0, 1e6); self.wdev_spin.setDecimals(3)
        self.wdev_spin.setValue(state.W_DEV)
        form.addRow("W_DEV:", self.wdev_spin)
        self.wt_spin = QDoubleSpinBox()
        self.wt_spin.setRange(0.0, 1e6); self.wt_spin.setDecimals(3)
        self.wt_spin.setValue(state.W_T)
        form.addRow("W_T:", self.wt_spin)
        layout.addWidget(gb)

        self.reset_btn = QPushButton("Reset solver parameters")
        self.reset_btn.clicked.connect(self._reset)
        layout.addWidget(self.reset_btn)

        # ---- Report ----
        lbl = QLabel("Last run report")
        lbl.setStyleSheet("font-weight: bold; margin-top: 6px;")
        layout.addWidget(lbl)
        self.report_box = QTextEdit()
        self.report_box.setReadOnly(True)
        self.report_box.setMinimumHeight(140)
        self.report_box.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 11px;")
        layout.addWidget(self.report_box)

        layout.addStretch()

        for w in (self.res_spin, self.n_spin, self.t_init_spin,
                  self.wobs_spin, self.wdev_spin, self.wt_spin):
            w.valueChanged.connect(self._on_change)

    # ------------------------------------------------------------------
    def get_pipeline(self):
        idx = self.pipeline_combo.currentIndex()
        return [['A', 'B', 'C'],
                ['A', 'C'],
                ['A', 'B'],
                ['A']][idx]

    def set_report(self, text: str):
        self.report_box.setPlainText(text)

    def _on_change(self, _=None):
        self.state.ASTAR_RES = self.res_spin.value()
        self.state.N = self.n_spin.value()
        self.state.T_INIT = self.t_init_spin.value()
        self.state.W_OBS = self.wobs_spin.value()
        self.state.W_DEV = self.wdev_spin.value()
        self.state.W_T = self.wt_spin.value()
        self.changed.emit()

    def _reset(self):
        self.state.reset_solver()
        self._sync_from_state()
        self.changed.emit()

    def _sync_from_state(self):
        for spin, val in [
            (self.res_spin, self.state.ASTAR_RES),
            (self.n_spin, self.state.N),
            (self.t_init_spin, self.state.T_INIT),
            (self.wobs_spin, self.state.W_OBS),
            (self.wdev_spin, self.state.W_DEV),
            (self.wt_spin, self.state.W_T),
        ]:
            spin.blockSignals(True)
            spin.setValue(val)
            spin.blockSignals(False)