"""Tab: start/goal poses, waypoints, robot dims, actuator limits."""
from __future__ import annotations
import math

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QDoubleSpinBox, QPushButton, QScrollArea, QLabel, QFrame
)

from core import config as C
from core.state import ScenarioState


MAX_WAYPOINTS = 10
DEFAULT_WAYPOINT_THETA = 0.0


def _dspin(val, lo, hi, step=0.01, decimals=3):
    s = QDoubleSpinBox()
    s.setRange(lo, hi)
    s.setSingleStep(step)
    s.setDecimals(decimals)
    s.setValue(val)
    s.setKeyboardTracking(True)
    return s


class WaypointRow(QFrame):
    changed = Signal(int)
    remove_requested = Signal(int)

    def __init__(self, index: int, x: float, y: float, th: float,
                 field_max: float, parent=None):
        super().__init__(parent)
        self.index = index
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(
            "QFrame { background: #f4f8ff; border: 1px solid #99b8d8; "
            "border-radius: 4px; }")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)

        self.label = QLabel(f"WP{index + 1}")
        layout.addWidget(self.label)
        layout.addWidget(QLabel("x"))
        self.x_spin = _dspin(x, 0.0, field_max)
        layout.addWidget(self.x_spin)
        layout.addWidget(QLabel("y"))
        self.y_spin = _dspin(y, 0.0, field_max)
        layout.addWidget(self.y_spin)
        layout.addWidget(QLabel("θ"))
        self.th_spin = _dspin(th, -2 * math.pi, 2 * math.pi,
                              step=0.1, decimals=4)
        layout.addWidget(self.th_spin)

        self.del_btn = QPushButton("✕")
        self.del_btn.setFixedWidth(26)
        self.del_btn.clicked.connect(self._on_del)
        layout.addWidget(self.del_btn)

        for s in (self.x_spin, self.y_spin, self.th_spin):
            s.valueChanged.connect(self._on_spin_changed)

    def _on_spin_changed(self, _value):
        self.changed.emit(self.index)

    def _on_del(self):
        self.remove_requested.emit(self.index)

    def values(self):
        return (self.x_spin.value(), self.y_spin.value(),
                self.th_spin.value())


class PosesPanel(QWidget):
    changed = Signal()

    def __init__(self, state: ScenarioState, parent=None):
        super().__init__(parent)
        self.state = state
        self.waypoint_rows = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(6, 6, 6, 6)

        x_lo, x_hi = 0.0, C.FIELD_MAX
        y_lo, y_hi = 0.0, C.FIELD_MAX
        th_lo, th_hi = -2 * math.pi, 2 * math.pi

        # ---- Start pose ----
        gb = QGroupBox("Start pose")
        form = QFormLayout(gb)
        self.sx = _dspin(state.start_x, x_lo, x_hi)
        self.sy = _dspin(state.start_y, y_lo, y_hi)
        self.sth = _dspin(state.start_theta, th_lo, th_hi,
                          step=0.1, decimals=4)
        form.addRow("x (m):", self.sx)
        form.addRow("y (m):", self.sy)
        form.addRow("θ (rad):", self.sth)
        layout.addWidget(gb)

        # ---- Goal pose ----
        gb = QGroupBox("Goal pose")
        form = QFormLayout(gb)
        self.gx = _dspin(state.goal_x, x_lo, x_hi)
        self.gy = _dspin(state.goal_y, y_lo, y_hi)
        self.gth = _dspin(state.goal_theta, th_lo, th_hi,
                          step=0.1, decimals=4)
        form.addRow("x (m):", self.gx)
        form.addRow("y (m):", self.gy)
        form.addRow("θ (rad):", self.gth)
        layout.addWidget(gb)

        # ---- Waypoints ----
        gb = QGroupBox("Waypoints (ordered, max 10)")
        wl = QVBoxLayout(gb)
        hint = QLabel(
            "Robot must pass through each waypoint's pose at some point. "
            "Velocity and acceleration at waypoints are unconstrained. "
            "New waypoints default to θ = 0.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #555; font-size: 11px;")
        wl.addWidget(hint)

        self.wp_container = QWidget()
        self.wp_layout = QVBoxLayout(self.wp_container)
        self.wp_layout.setContentsMargins(0, 0, 0, 0)
        self.wp_layout.setSpacing(4)
        wl.addWidget(self.wp_container)

        self.add_wp_btn = QPushButton("+ Add waypoint")
        self.add_wp_btn.clicked.connect(self._add_waypoint)
        wl.addWidget(self.add_wp_btn)
        layout.addWidget(gb)

        # ---- Robot geometry ----
        gb = QGroupBox("Robot geometry")
        form = QFormLayout(gb)
        self.W_spin = _dspin(state.W, 0.01, 2.0, step=0.005)
        self.L_spin = _dspin(state.L, 0.01, 2.0, step=0.005)
        self.rw_spin = _dspin(state.robot_width, 0.01, 3.0, step=0.005)
        self.rl_spin = _dspin(state.robot_length, 0.01, 3.0, step=0.005)
        form.addRow("W (trackwidth, m):", self.W_spin)
        form.addRow("L (wheelbase, m):", self.L_spin)
        form.addRow("Robot width (m):", self.rw_spin)
        form.addRow("Robot length (m):", self.rl_spin)
        rinfo = QLabel("Robot dims must be >= 2× W and 2× L respectively.")
        rinfo.setWordWrap(True)
        rinfo.setStyleSheet("color: #555; font-size: 10px;")
        form.addRow(rinfo)
        layout.addWidget(gb)

        # ---- Actuator limits ----
        gb = QGroupBox("Actuator limits")
        form = QFormLayout(gb)
        self.v_spin = _dspin(state.V_LIM, 0.01, 20.0, step=0.05)
        self.a_spin = _dspin(state.A_LIM, 0.01, 50.0, step=0.1)
        self.k_spin = _dspin(state.K_OMEGA, 0.01, 10.0, step=0.01)
        form.addRow("V_LIM (m/s):", self.v_spin)
        form.addRow("A_LIM (m/s²):", self.a_spin)
        form.addRow("κ (rot scale):", self.k_spin)
        layout.addWidget(gb)

        self.reset_btn = QPushButton("Reset poses, waypoints & robot")
        self.reset_btn.clicked.connect(self._reset)
        layout.addWidget(self.reset_btn)
        layout.addStretch()

        scroll.setWidget(inner)
        outer.addWidget(scroll)

        for w in (self.sx, self.sy, self.sth, self.gx, self.gy, self.gth,
                  self.W_spin, self.L_spin,
                  self.rw_spin, self.rl_spin,
                  self.v_spin, self.a_spin, self.k_spin):
            w.valueChanged.connect(self._on_change)

        self._rebuild_waypoints()

    # ------------------------------------------------------------------
    def _add_waypoint(self):
        if len(self.state.waypoints) >= MAX_WAYPOINTS:
            return
        if self.state.waypoints:
            lx, ly, _ = self.state.waypoints[-1]
            nx = min(lx + 0.4, C.FIELD_MAX - self.state.robot_half_width)
            ny = min(ly + 0.4, C.FIELD_MAX - self.state.robot_half_length)
        else:
            nx = (self.state.start_x + self.state.goal_x) / 2
            ny = (self.state.start_y + self.state.goal_y) / 2
        self.state.waypoints.append((nx, ny, DEFAULT_WAYPOINT_THETA))
        self._rebuild_waypoints()
        self._emit_changed()

    def _remove_waypoint(self, index: int):
        if 0 <= index < len(self.state.waypoints):
            del self.state.waypoints[index]
            self._rebuild_waypoints()
            self._emit_changed()

    def _on_wp_changed(self, index: int):
        if 0 <= index < len(self.waypoint_rows):
            self.state.waypoints[index] = self.waypoint_rows[index].values()
        self._emit_changed()

    def _rebuild_waypoints(self):
        while self.wp_layout.count():
            item = self.wp_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self.waypoint_rows = []

        for i, (x, y, th) in enumerate(self.state.waypoints):
            row = WaypointRow(i, x, y, th, C.FIELD_MAX)
            row.changed.connect(self._on_wp_changed)
            row.remove_requested.connect(self._remove_waypoint)
            self.wp_layout.addWidget(row)
            self.waypoint_rows.append(row)

        self.add_wp_btn.setEnabled(len(self.state.waypoints) < MAX_WAYPOINTS)

    def _emit_changed(self):
        self.changed.emit()

    def _on_change(self, _=None):
        W = self.W_spin.value()
        L = self.L_spin.value()
        rw = self.rw_spin.value()
        rl = self.rl_spin.value()

        # Auto-clamp robot dims to >= 2*W, >= 2*L
        if rw < 2.0 * W:
            self.rw_spin.blockSignals(True)
            self.rw_spin.setValue(2.0 * W)
            self.rw_spin.blockSignals(False)
            rw = 2.0 * W
        if rl < 2.0 * L:
            self.rl_spin.blockSignals(True)
            self.rl_spin.setValue(2.0 * L)
            self.rl_spin.blockSignals(False)
            rl = 2.0 * L

        self.state.start_x = self.sx.value()
        self.state.start_y = self.sy.value()
        self.state.start_theta = self.sth.value()
        self.state.goal_x = self.gx.value()
        self.state.goal_y = self.gy.value()
        self.state.goal_theta = self.gth.value()
        self.state.W = W
        self.state.L = L
        self.state.robot_width = rw
        self.state.robot_length = rl
        self.state.V_LIM = self.v_spin.value()
        self.state.A_LIM = self.a_spin.value()
        self.state.K_OMEGA = self.k_spin.value()
        self._emit_changed()

    def _reset(self):
        self.state.reset_poses()
        self.state.reset_robot()
        self._sync_from_state()
        self._rebuild_waypoints()
        self._emit_changed()

    def _sync_from_state(self):
        for spin, val in [
            (self.sx, self.state.start_x), (self.sy, self.state.start_y),
            (self.sth, self.state.start_theta),
            (self.gx, self.state.goal_x), (self.gy, self.state.goal_y),
            (self.gth, self.state.goal_theta),
            (self.W_spin, self.state.W), (self.L_spin, self.state.L),
            (self.rw_spin, self.state.robot_width),
            (self.rl_spin, self.state.robot_length),
            (self.v_spin, self.state.V_LIM), (self.a_spin, self.state.A_LIM),
            (self.k_spin, self.state.K_OMEGA),
        ]:
            spin.blockSignals(True)
            spin.setValue(val)
            spin.blockSignals(False)