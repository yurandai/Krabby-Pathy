"""Export tab — format selection, copyable preview, CSV download."""
from __future__ import annotations
import os
import csv
from datetime import datetime

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QTextEdit,
    QPushButton, QLabel, QFileDialog, QMessageBox, QGroupBox,
    QFormLayout, QDoubleSpinBox
)

from core import config as C
from core.state import ScenarioState


INCHES_PER_METER = 39.3701


class ExportPanel(QWidget):
    def __init__(self, state: ScenarioState, parent=None):
        super().__init__(parent)
        self.state = state
        self.nlp_result = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        # ---- Format selector ----
        gb = QGroupBox("Export format")
        form = QFormLayout(gb)
        self.format_combo = QComboBox()
        self.format_combo.addItems([
            "Full state CSV (Time, X, Y, θ, Vx, Vy, ω, Ax, Ay, α)",
            "Compact FTC CSV (Time, X, Y, θ, Vx, Vy, ω) — no header",
            "Pedro Pathing poses (X_in, Y_in, θ_rad) — inches, CCW",
            "Waypoints only (start → WP1..n → goal)",
            "Raw trajectory CSV (X, Y, θ) — meters, no header",
        ])
        self.format_combo.currentIndexChanged.connect(self._refresh_preview)
        form.addRow("Format:", self.format_combo)
        layout.addWidget(gb)

        # ---- Preview ----
        lbl = QLabel("Preview (copyable)")
        lbl.setStyleSheet("font-weight: bold; margin-top: 6px;")
        layout.addWidget(lbl)

        self.preview = QTextEdit()
        self.preview.setReadOnly(False)
        self.preview.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 11px;")
        self.preview.setMinimumHeight(220)
        layout.addWidget(self.preview, 1)

        # ---- Buttons ----
        btn_row = QHBoxLayout()
        self.copy_btn = QPushButton("Copy to Clipboard")
        self.download_btn = QPushButton("Download CSV…")
        self.refresh_btn = QPushButton("Refresh")
        btn_row.addWidget(self.copy_btn, 1)
        btn_row.addWidget(self.download_btn, 2)
        btn_row.addWidget(self.refresh_btn, 1)
        layout.addLayout(btn_row)

        self.copy_btn.clicked.connect(self._copy_to_clipboard)
        self.download_btn.clicked.connect(self._download)
        self.refresh_btn.clicked.connect(self._refresh_preview)

        self.info_lbl = QLabel(
            "Run NLP first to populate this tab. "
            "Pedro Pathing format uses inches and X-right/Y-up heading "
            "in radians.")
        self.info_lbl.setWordWrap(True)
        self.info_lbl.setStyleSheet("color: #555; font-size: 11px;")
        layout.addWidget(self.info_lbl)

        self.setEnabled(False)

    # ------------------------------------------------------------------
    def set_trajectory(self, result):
        """Called by MainWindow after a successful NLP run."""
        self.nlp_result = result
        self.setEnabled(True)
        self._refresh_preview()

    def clear(self):
        self.nlp_result = None
        self.preview.setPlainText("")
        self.setEnabled(False)

    # ------------------------------------------------------------------
    def _refresh_preview(self):
        if self.nlp_result is None:
            self.preview.setPlainText(
                "No trajectory available. Run NLP first.")
            return
        try:
            text = self._generate_text()
            self.preview.setPlainText(text)
        except Exception as e:
            self.preview.setPlainText(f"Error generating export: {e}")

    # ------------------------------------------------------------------
    def _generate_text(self) -> str:
        idx = self.format_combo.currentIndex()
        X, U, T = (self.nlp_result['X'],
                   self.nlp_result['U'],
                   self.nlp_result['T'])
        N = X.shape[1] - 1
        t = np.linspace(0.0, T, N + 1)

        if idx == 0:
            return self._full_state_csv(t, X, U)
        if idx == 1:
            return self._compact_ftc_csv(t, X)
        if idx == 2:
            return self._pedro_poses_csv(t, X)
        if idx == 3:
            return self._waypoints_only_csv()
        if idx == 4:
            return self._raw_xyz_csv(X)
        return ""

    def _full_state_csv(self, t, X, U) -> str:
        lines = ["Time,X,Y,Theta,Vx,Vy,Omega,Ax,Ay,Alpha"]
        for i in range(len(t)):
            lines.append(
                f"{t[i]:.6f},{X[0,i]:.6f},{X[1,i]:.6f},{X[2,i]:.6f},"
                f"{X[3,i]:.6f},{X[4,i]:.6f},{X[5,i]:.6f},"
                f"{U[0,i]:.6f},{U[1,i]:.6f},{U[2,i]:.6f}")
        return "\n".join(lines)

    def _compact_ftc_csv(self, t, X) -> str:
        lines = []
        for i in range(len(t)):
            lines.append(
                f"{t[i]:.6f},{X[0,i]:.6f},{X[1,i]:.6f},{X[2,i]:.6f},"
                f"{X[3,i]:.6f},{X[4,i]:.6f},{X[5,i]:.6f}")
        return "\n".join(lines)

    def _pedro_poses_csv(self, t, X) -> str:
        """Pedro Pathing uses inches, X-right, Y-up, heading CCW from +X."""
        lines = ["# Pedro Pathing pose sequence",
                 "# Units: inches, heading in radians (CCW from +X axis)",
                 "# X increases right, Y increases up",
                 "# Time_s,X_in,Y_in,heading_rad"]
        for i in range(len(t)):
            xi = X[0, i] * INCHES_PER_METER
            yi = X[1, i] * INCHES_PER_METER
            lines.append(f"{t[i]:.6f},{xi:.4f},{yi:.4f},{X[2,i]:.6f}")
        return "\n".join(lines)

    def _waypoints_only_csv(self) -> str:
        lines = ["# Ordered poses: start, waypoints, goal",
                 "# Units: meters, heading in radians",
                 "# role,X,Y,Theta"]
        s = self.state
        lines.append(f"start,{s.start_x:.6f},{s.start_y:.6f},"
                     f"{s.start_theta:.6f}")
        for i, (wx, wy, wth) in enumerate(s.waypoints):
            lines.append(f"waypoint_{i+1},{wx:.6f},{wy:.6f},{wth:.6f}")
        lines.append(f"goal,{s.goal_x:.6f},{s.goal_y:.6f},"
                     f"{s.goal_theta:.6f}")
        return "\n".join(lines)

    def _raw_xyz_csv(self, X) -> str:
        lines = []
        for i in range(X.shape[1]):
            lines.append(f"{X[0,i]:.6f},{X[1,i]:.6f},{X[2,i]:.6f}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    def _copy_to_clipboard(self):
        text = self.preview.toPlainText()
        if not text:
            return
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)
        self.info_lbl.setText("Copied to clipboard.")
        self.info_lbl.setStyleSheet("color: green; font-size: 11px;")

    def _download(self):
        if self.nlp_result is None:
            return
        text = self.preview.toPlainText()
        if not text:
            return

        default_name = self._default_filename()
        path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV", default_name, "CSV files (*.csv);;All files (*)")
        if not path:
            return
        try:
            with open(path, "w", newline="") as fh:
                fh.write(text)
            self.info_lbl.setText(f"Saved: {path}")
            self.info_lbl.setStyleSheet("color: green; font-size: 11px;")
        except Exception as e:
            QMessageBox.critical(self, "Save failed", str(e))

    def _default_filename(self) -> str:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        idx = self.format_combo.currentIndex()
        tag = ["full_state", "compact_ftc", "pedro_poses",
               "waypoints_only", "raw_xyz"][idx]
        return f"trajectory_{tag}_{stamp}.csv"