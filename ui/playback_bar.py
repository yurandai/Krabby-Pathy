"""In-app playback with wall-clock timing (1:1 with real time)."""
from __future__ import annotations
import time
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QSlider, QLabel
)


class PlaybackBar(QWidget):
    time_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)

        self.reset_btn = QPushButton("⏮")
        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedWidth(40)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        self.time_label = QLabel("0.00 / 0.00 s")
        self.time_label.setFixedWidth(120)

        layout.addWidget(self.reset_btn)
        layout.addWidget(self.play_btn)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.time_label)

        self.T = 0.0
        self.t = 0.0
        self._play_start_wall = 0.0
        self._play_start_t = 0.0

        self.timer = QTimer(self)
        self.timer.setInterval(16)   # ~60 Hz, so redraws keep up
        self.timer.timeout.connect(self._tick)

        self.play_btn.clicked.connect(self._toggle_play)
        self.reset_btn.clicked.connect(self._reset)
        self.slider.sliderMoved.connect(self._on_slider)
        self.setEnabled(False)

    def set_trajectory(self, T: float):
        self.T = float(T)
        self.t = 0.0
        self.setEnabled(True)
        self._sync_ui()
        self.time_changed.emit(0.0)

    def clear(self):
        self.timer.stop()
        self.play_btn.setText("▶")
        self.T = 0.0
        self.t = 0.0
        self.setEnabled(False)
        self._sync_ui()

    def _toggle_play(self):
        if self.timer.isActive():
            self.timer.stop()
            self.play_btn.setText("▶")
        else:
            if self.T <= 0:
                return
            if self.t >= self.T:
                self.t = 0.0
            self._play_start_wall = time.monotonic()
            self._play_start_t = self.t
            self.timer.start()
            self.play_btn.setText("⏸")

    def _tick(self):
        # Wall-clock based, so slowdowns in the redraw don't slow the animation.
        elapsed = time.monotonic() - self._play_start_wall
        self.t = self._play_start_t + elapsed
        if self.t >= self.T:
            self.t = self.T
            self.timer.stop()
            self.play_btn.setText("▶")
        self._sync_ui()
        self.time_changed.emit(self.t)

    def _reset(self):
        self.timer.stop()
        self.play_btn.setText("▶")
        self.t = 0.0
        self._sync_ui()
        self.time_changed.emit(0.0)

    def _on_slider(self, val):
        if self.T <= 0:
            return
        self.timer.stop()
        self.play_btn.setText("▶")
        self.t = (val / 1000.0) * self.T
        self._sync_ui()
        self.time_changed.emit(self.t)

    def _sync_ui(self):
        if self.T > 0:
            self.slider.blockSignals(True)
            self.slider.setValue(int(1000 * self.t / self.T))
            self.slider.blockSignals(False)
        self.time_label.setText(f"{self.t:.2f} / {self.T:.2f} s")