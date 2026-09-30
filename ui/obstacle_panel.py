"""Right-side obstacle editor panel with minimum-radius warning."""
from __future__ import annotations
from typing import List, Optional

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QScrollArea,
    QLabel, QDoubleSpinBox, QFrame
)

from core import config as C
from core.obstacle import Obstacle


DEFAULT_MIN_RADIUS = 0.258


def _clear_layout(layout):
    if layout is None:
        return
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w is not None:
            w.setParent(None)
            w.deleteLater()
            continue
        sub = item.layout()
        if sub is not None:
            _clear_layout(sub)


class ObstacleCard(QFrame):
    changed = Signal()
    remove_requested = Signal()

    def __init__(self, obstacle: Obstacle, index: int,
                 min_radius: float = DEFAULT_MIN_RADIUS, parent=None):
        super().__init__(parent)
        self.obstacle = obstacle
        self.index = index
        self.min_radius = min_radius
        self.setFrameShape(QFrame.StyledPanel)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 6, 8, 6)
        outer.setSpacing(4)

        header = QHBoxLayout()
        self.title = QLabel(f"Obstacle #{index + 1}")
        self.title.setStyleSheet("font-weight: bold;")
        header.addWidget(self.title)
        header.addStretch()
        self.delete_btn = QPushButton("✕")
        self.delete_btn.setFixedWidth(28)
        self.delete_btn.setToolTip("Remove this obstacle")
        self.delete_btn.clicked.connect(self.remove_requested.emit)
        header.addWidget(self.delete_btn)
        outer.addLayout(header)

        r_row = QHBoxLayout()
        r_row.addWidget(QLabel("Inflation r (m):"))
        self.r_spin = QDoubleSpinBox()
        self.r_spin.setRange(0.001, 2.0)
        self.r_spin.setSingleStep(0.01)
        self.r_spin.setDecimals(3)
        self.r_spin.setValue(obstacle.radius)
        self.r_spin.setKeyboardTracking(True)
        self.r_spin.valueChanged.connect(self._on_radius_changed)
        r_row.addWidget(self.r_spin)
        r_row.addStretch()
        outer.addLayout(r_row)

        self.points_container = QWidget()
        self.points_layout = QVBoxLayout(self.points_container)
        self.points_layout.setContentsMargins(0, 0, 0, 0)
        self.points_layout.setSpacing(2)
        outer.addWidget(self.points_container)

        self.add_pt_btn = QPushButton("+ Add point")
        self.add_pt_btn.clicked.connect(self._on_add_point)
        outer.addWidget(self.add_pt_btn)

        self.error_lbl = QLabel("")
        self.error_lbl.setStyleSheet("color: red; font-size: 11px;")
        self.error_lbl.setWordWrap(True)
        outer.addWidget(self.error_lbl)

        self._rebuild_points()
        self._validate()

    def _on_radius_changed(self, value):
        self.obstacle.radius = float(value)
        self._validate()
        self.changed.emit()

    def _on_add_point(self):
        if self.obstacle.points:
            last = self.obstacle.points[-1]
            new_pt = (min(last[0] + 0.3, C.FIELD_MAX - 0.01),
                      min(last[1] + 0.3, C.FIELD_MAX - 0.01))
        else:
            new_pt = (C.FIELD_MAX / 2, C.FIELD_MAX / 2)
        self.obstacle.points.append(new_pt)
        self._rebuild_points()
        self._validate()
        self.changed.emit()

    def _on_remove_point(self, idx):
        if len(self.obstacle.points) <= 1:
            return
        del self.obstacle.points[idx]
        self._rebuild_points()
        self._validate()
        self.changed.emit()

    def _on_point_changed(self, idx, axis, value):
        pt = list(self.obstacle.points[idx])
        pt[axis] = float(value)
        self.obstacle.points[idx] = tuple(pt)
        self._validate()
        self.changed.emit()

    def _rebuild_points(self):
        _clear_layout(self.points_layout)
        for i, pt in enumerate(self.obstacle.points):
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(QLabel(f"P{i + 1}"))
            row.addWidget(QLabel("x"))
            x_spin = QDoubleSpinBox()
            x_spin.setRange(0.0, C.FIELD_MAX)
            x_spin.setSingleStep(0.05)
            x_spin.setDecimals(3)
            x_spin.setValue(pt[0])
            x_spin.setKeyboardTracking(True)
            row.addWidget(x_spin)

            row.addWidget(QLabel("y"))
            y_spin = QDoubleSpinBox()
            y_spin.setRange(0.0, C.FIELD_MAX)
            y_spin.setSingleStep(0.05)
            y_spin.setDecimals(3)
            y_spin.setValue(pt[1])
            y_spin.setKeyboardTracking(True)
            row.addWidget(y_spin)

            del_btn = QPushButton("−")
            del_btn.setFixedWidth(24)
            del_btn.setToolTip("Remove this point")
            del_btn.clicked.connect(
                lambda _=False, idx=i: self._on_remove_point(idx))
            row.addWidget(del_btn)

            x_spin.valueChanged.connect(
                lambda v, idx=i: self._on_point_changed(idx, 0, v))
            y_spin.valueChanged.connect(
                lambda v, idx=i: self._on_point_changed(idx, 1, v))

            container = QWidget()
            container.setLayout(row)
            self.points_layout.addWidget(container)

    def _validate(self) -> bool:
        ok, msg = self.obstacle.is_valid()
        if ok:
            if self.obstacle.radius < self.min_radius - 1e-9:
                self.setStyleSheet(
                    "QFrame { background: #fff7d6; border: 1px solid #d4b106; "
                    "border-radius: 4px; }")
                self.error_lbl.setStyleSheet(
                    "color: #806000; font-size: 11px;")
                self.error_lbl.setText(
                    f"⚠ radius {self.obstacle.radius:.3f} m < recommended "
                    f"{self.min_radius:.3f} m")
                return True
            self.setStyleSheet(
                "QFrame { background: #fafafa; border: 1px solid #ccc; "
                "border-radius: 4px; }")
            self.error_lbl.setStyleSheet("color: red; font-size: 11px;")
            self.error_lbl.setText("")
        else:
            self.setStyleSheet(
                "QFrame { background: #ffe6e6; border: 1px solid red; "
                "border-radius: 4px; }")
            self.error_lbl.setStyleSheet("color: red; font-size: 11px;")
            self.error_lbl.setText(msg)
        return ok

    def set_min_radius(self, v: float):
        self.min_radius = float(v)
        self._validate()

    def is_valid(self) -> bool:
        return self.obstacle.is_valid()[0]


class ObstaclePanel(QWidget):
    obstacles_changed = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.obstacles: List[Obstacle] = []
        self.cards: List[ObstacleCard] = []
        self._min_radius = DEFAULT_MIN_RADIUS
        self._removal_in_progress = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        title = QLabel("Obstacles")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        hint = QLabel("Each obstacle is a strictly convex polygon. The "
                      "robot's center is kept at least the 'inflation r' "
                      "away from it.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #555; font-size: 11px;")
        layout.addWidget(hint)

        self.add_btn = QPushButton("+ Add obstacle")
        self.add_btn.clicked.connect(self._add_obstacle)
        layout.addWidget(self.add_btn)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.addStretch()
        self.scroll.setWidget(self.list_container)
        layout.addWidget(self.scroll, 1)

        self.status = QLabel("0 obstacles")
        self.status.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.status)

    # ------------------------------------------------------------------
    def set_min_radius(self, v: float):
        self._min_radius = max(0.01, float(v))
        for card in self.cards:
            card.set_min_radius(self._min_radius)

    def _add_obstacle(self):
        obs = Obstacle(points=[(C.FIELD_MAX / 2, C.FIELD_MAX / 2)],
                       radius=self._min_radius)
        self.obstacles.append(obs)
        self._rebuild_cards()
        self._emit()

    def _remove_obstacle(self, index):
        if self._removal_in_progress:
            return
        if 0 <= index < len(self.obstacles):
            self._removal_in_progress = True
            del self.obstacles[index]
            QTimer.singleShot(0, self._finish_removal)

    def _finish_removal(self):
        self._rebuild_cards()
        self._emit()
        self._removal_in_progress = False

    def _rebuild_cards(self):
        for card in self.cards:
            try:
                card.changed.disconnect()
            except Exception:
                pass
            try:
                card.remove_requested.disconnect()
            except Exception:
                pass
            card.setParent(None)
            card.deleteLater()
        self.cards = []

        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        for i, obs in enumerate(self.obstacles):
            card = ObstacleCard(obs, i, min_radius=self._min_radius)
            card.changed.connect(self._on_card_changed)
            card.remove_requested.connect(
                lambda _=False, idx=i: self._remove_obstacle(idx))
            self.list_layout.insertWidget(self.list_layout.count() - 1, card)
            self.cards.append(card)

        self.status.setText(f"{len(self.obstacles)} obstacle(s)")

    def _on_card_changed(self):
        self._emit()

    def _emit(self):
        self.obstacles_changed.emit(self.obstacles)

    def all_valid(self) -> bool:
        return all(c.is_valid() for c in self.cards)