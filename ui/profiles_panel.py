"""Tab showing position, velocity, and acceleration profiles."""
from __future__ import annotations
import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class ProfilesPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fig = Figure(figsize=(5.5, 8.5), dpi=150, tight_layout=True)
        self.canvas = FigureCanvasQTAgg(self.fig)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        self._draw_empty()

    def _draw_empty(self):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.text(0.5, 0.5,
                "No trajectory yet.\nRun NLP to see profiles.",
                ha="center", va="center", transform=ax.transAxes,
                color="gray", fontsize=13)
        ax.set_xticks([])
        ax.set_yticks([])
        self.canvas.draw_idle()

    def set_trajectory(self, X, U, T):
        self.fig.clear()
        N = X.shape[1] - 1
        t = np.linspace(0.0, T, N + 1)

        ax1 = self.fig.add_subplot(3, 1, 1)
        ax1.plot(t, X[0, :], label="x (m)", lw=1.8, antialiased=True)
        ax1.plot(t, X[1, :], label="y (m)", lw=1.8, antialiased=True)
        ax1.plot(t, X[2, :], label="θ (rad)", lw=1.8, antialiased=True)
        ax1.set_ylabel("Position", fontsize=10)
        ax1.legend(fontsize=8, loc="best")
        ax1.grid(alpha=0.3, linestyle="-", linewidth=0.5)

        ax2 = self.fig.add_subplot(3, 1, 2)
        ax2.plot(t, X[3, :], label="vx", lw=1.8, antialiased=True)
        ax2.plot(t, X[4, :], label="vy", lw=1.8, antialiased=True)
        ax2.plot(t, X[5, :], label="ω", lw=1.8, antialiased=True)
        ax2.set_ylabel("Velocity", fontsize=10)
        ax2.legend(fontsize=8, loc="best")
        ax2.grid(alpha=0.3, linestyle="-", linewidth=0.5)

        ax3 = self.fig.add_subplot(3, 1, 3)
        ax3.plot(t, U[0, :], label="ax", lw=1.8, antialiased=True)
        ax3.plot(t, U[1, :], label="ay", lw=1.8, antialiased=True)
        ax3.plot(t, U[2, :], label="α", lw=1.8, antialiased=True)
        ax3.set_ylabel("Accel", fontsize=10)
        ax3.set_xlabel("Time (s)", fontsize=10)
        ax3.legend(fontsize=8, loc="best")
        ax3.grid(alpha=0.3, linestyle="-", linewidth=0.5)

        self.canvas.draw_idle()

    def clear(self):
        self._draw_empty()