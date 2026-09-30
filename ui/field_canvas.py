"""Field widget — obstacles, poses, A* path, NLP trajectory, animation.

High-DPI rendering and blit-based animation for smooth 60 fps playback.
"""
from __future__ import annotations
import math

from PySide6.QtWidgets import QWidget, QVBoxLayout
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Rectangle, Polygon as MplPolygon

from core import config as C
from core.state import ScenarioState
from core.obstacle import Obstacle
from core.geometry import inflated_region, sort_ccw


class FieldCanvas(QWidget):
    def __init__(self, state: ScenarioState, parent=None):
        super().__init__(parent)
        self.state = state
        self.astar_path = None
        self.traj_X = None
        self.traj_U = None
        self.traj_T = 0.0
        self.anim_t = 0.0

        # Animation caches
        self._bg_cache = None
        self._anim_robot_patch = None

        # High-DPI figure
        self.fig = Figure(figsize=(8, 8), dpi=150, tight_layout=True)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.ax = self.fig.add_subplot(111)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)

        self.redraw()

    # ------------------------------------------------------------------
    def set_astar_path(self, path):
        self.astar_path = path

    def set_trajectory(self, X, U, T):
        self.traj_X = X
        self.traj_U = U
        self.traj_T = float(T)
        self.anim_t = 0.0
        self.redraw()

    def clear_trajectory(self):
        self.traj_X = None
        self.traj_U = None
        self.traj_T = 0.0
        self.anim_t = 0.0
        self.redraw()

    def set_animation_time(self, t: float):
        """Blit-based fast update. Called ~60 Hz by the playback bar."""
        max_t = self.traj_T if self.traj_T > 0 else 0.0
        self.anim_t = max(0.0, min(t, max_t))

        if self._anim_robot_patch is None or self._bg_cache is None:
            return
        try:
            self.canvas.restore_region(self._bg_cache)
            x, y, th = self._interp_state_at(self.anim_t)
            self._anim_robot_patch.set_xy(self._pose_corners(x, y, th))
            self.ax.draw_artist(self._anim_robot_patch)
            self.canvas.blit(self.fig.bbox)
            self.canvas.flush_events()
        except Exception:
            # If blitting fails, fall back to full redraw
            self.redraw()

    # ------------------------------------------------------------------
    def redraw(self):
        ax = self.ax
        ax.clear()
        ax.set_xlim(-0.3, C.FIELD_MAX + 0.3)
        ax.set_ylim(-0.3, C.FIELD_MAX + 0.3)
        ax.set_aspect("equal")
        ax.grid(True, alpha=0.35, linestyle="-", linewidth=0.5)
        ax.set_xlabel("X (m)", fontsize=10)
        ax.set_ylabel("Y (m)", fontsize=10)
        ax.set_title(f"FTC Field — {C.FIELD_FT} ft x {C.FIELD_FT} ft",
                     fontsize=11)

        ax.add_patch(Rectangle(
            (C.FIELD_MIN, C.FIELD_MIN),
            C.FIELD_MAX - C.FIELD_MIN, C.FIELD_MAX - C.FIELD_MIN,
            facecolor="#f7f7f7", edgecolor="black", lw=1.5, zorder=0,
            antialiased=True, snap=True,
        ))

        for i, obs in enumerate(self.state.obstacles):
            self._draw_obstacle(ax, obs, i)

        # A* path
        if self.astar_path is not None and len(self.astar_path) > 0:
            p = self.astar_path
            ax.plot(p[:, 0], p[:, 1], "-", color="cyan",
                    lw=2.0, alpha=0.55, zorder=3, antialiased=True)

        # Waypoints
        for i, (wx, wy, wth) in enumerate(self.state.waypoints):
            self._draw_waypoint(ax, wx, wy, wth, i)

        # NLP trajectory (static line, animated robot is separate)
        if self.traj_X is not None:
            X = self.traj_X
            ax.plot(X[0, :], X[1, :], "-", color="magenta",
                    lw=2.2, alpha=0.85, zorder=4, antialiased=True)
            step = max(1, (X.shape[1] - 1) // 12)
            ax.plot(X[0, ::step], X[1, ::step], "o", color="magenta",
                    ms=3.2, zorder=4, antialiased=True)
            for i in range(0, X.shape[1], step):
                ax.annotate("",
                            xy=(X[0, i] + 0.08 * math.cos(X[2, i]),
                                X[1, i] + 0.08 * math.sin(X[2, i])),
                            xytext=(X[0, i], X[1, i]),
                            arrowprops=dict(arrowstyle="->",
                                            color="magenta", lw=1.0),
                            zorder=5)

        # Start / goal robot poses (static)
        self._draw_robot_pose(ax, self.state.start_x, self.state.start_y,
                              self.state.start_theta, "green", "START")
        self._draw_robot_pose(ax, self.state.goal_x, self.state.goal_y,
                              self.state.goal_theta, "red", "GOAL")

        # Capture the background BEFORE adding the animated robot
        self.canvas.draw()
        self._bg_cache = self.canvas.copy_from_bbox(self.fig.bbox)

        # Now add the animated robot
        if self.traj_X is not None:
            x, y, th = self._interp_state_at(self.anim_t)
            self._anim_robot_patch = MplPolygon(
                self._pose_corners(x, y, th), closed=True, fill=True,
                facecolor="magenta", edgecolor="black",
                lw=1.2, alpha=0.85, zorder=8, antialiased=True)
            ax.add_patch(self._anim_robot_patch)
            self.canvas.draw()
        else:
            self._anim_robot_patch = None

    # ------------------------------------------------------------------
    def _pose_corners(self, x, y, theta):
        hw = self.state.robot_half_width
        hl = self.state.robot_half_length
        c, s = math.cos(theta), math.sin(theta)
        return [(x + lx * c - ly * s, y + lx * s + ly * c)
                for lx, ly in [(-hw, -hl), (hw, -hl), (hw, hl), (-hw, hl)]]

    def _interp_state_at(self, t):
        X = self.traj_X
        T = self.traj_T
        N = X.shape[1] - 1
        if T <= 0:
            return X[0, 0], X[1, 0], X[2, 0]
        idx = (t / T) * N
        k = int(max(0, min(N - 1, int(idx))))
        frac = idx - k
        x = (1 - frac) * X[0, k] + frac * X[0, k + 1]
        y = (1 - frac) * X[1, k] + frac * X[1, k + 1]
        th0 = X[2, k]
        th1 = X[2, k + 1]
        dth = (th1 - th0 + math.pi) % (2 * math.pi) - math.pi
        th = th0 + frac * dth
        return x, y, th

    def _draw_obstacle(self, ax, obs: Obstacle, index: int):
        pts = obs.points
        if not pts:
            return
        ok, _ = obs.is_valid()
        DISP_R = 0.02
        EDGE_LW = 2.0

        if len(pts) == 1:
            ax.add_patch(Circle(pts[0], DISP_R, facecolor="darkred",
                                edgecolor="darkred", lw=1, zorder=4,
                                antialiased=True))
        elif len(pts) == 2:
            ax.plot([pts[0][0], pts[1][0]], [pts[0][1], pts[1][1]],
                    "-", color="darkred", lw=EDGE_LW,
                    solid_capstyle="round", zorder=4, antialiased=True)
            for p in pts:
                ax.add_patch(Circle(p, DISP_R * 0.6, facecolor="darkred",
                                    edgecolor="darkred", lw=0.5,
                                    zorder=5, antialiased=True))
        else:
            ordered = sort_ccw(pts) if ok else pts
            ax.add_patch(MplPolygon(ordered, closed=True,
                                    facecolor=(1, 0, 0, 0.35),
                                    edgecolor="darkred", lw=1.2, zorder=4,
                                    antialiased=True))
            for p in pts:
                ax.add_patch(Circle(p, DISP_R * 0.6, facecolor="darkred",
                                    edgecolor="darkred", lw=0.5,
                                    zorder=5, antialiased=True))

        if ok:
            try:
                geom = inflated_region(pts, obs.radius)
                if geom is not None:
                    coords = list(geom.exterior.coords)
                    ax.add_patch(MplPolygon(coords, closed=True,
                                            facecolor=(1, 0, 0, 0.08),
                                            edgecolor="red", lw=1, ls=":",
                                            zorder=2, antialiased=True))
            except Exception:
                pass
        else:
            if len(pts) >= 3:
                ax.add_patch(MplPolygon(pts, closed=True, fill=False,
                                        edgecolor="red", lw=1.5, ls="--",
                                        zorder=2, antialiased=True))

        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        ax.annotate(f"#{index + 1}", (cx, cy),
                    textcoords="offset points", xytext=(0, 10),
                    fontsize=10, color="darkred", weight="bold",
                    ha="center", va="bottom", zorder=7)

    def _draw_waypoint(self, ax, wx, wy, wth, index):
        c, s = math.cos(wth), math.sin(wth)
        size = 0.08
        diamond = [
            (wx + size * c, wy + size * s),
            (wx - size * s, wy + size * c),
            (wx - size * c, wy - size * s),
            (wx + size * s, wy - size * c),
        ]
        ax.add_patch(MplPolygon(diamond, closed=True, fill=True,
                                facecolor="gold", edgecolor="black",
                                lw=1.0, alpha=0.9, zorder=5,
                                antialiased=True, snap=True))
        arrow_len = 0.15
        ax.annotate("", xy=(wx + arrow_len * c, wy + arrow_len * s),
                    xytext=(wx, wy),
                    arrowprops=dict(arrowstyle="->",
                                    color="darkgoldenrod", lw=1.6),
                    zorder=6)
        ax.annotate(f"WP{index + 1}", (wx, wy), textcoords="offset points",
                    xytext=(0, 12), ha="center", fontsize=8,
                    color="darkgoldenrod", weight="bold", zorder=7)

    def _draw_robot_pose(self, ax, x, y, theta, color, label,
                         filled_alpha=0.55, zorder=5):
        corners = self._pose_corners(x, y, theta)
        ax.add_patch(MplPolygon(corners, closed=True, fill=True,
                                facecolor=color, edgecolor="black",
                                lw=1.2, alpha=filled_alpha, zorder=zorder,
                                antialiased=True, snap=True))
        arrow_len = 0.20
        ax.annotate("",
                    xy=(x + arrow_len * math.cos(theta),
                        y + arrow_len * math.sin(theta)),
                    xytext=(x, y),
                    arrowprops=dict(arrowstyle="->", color=color, lw=2.0),
                    zorder=zorder + 1)
        if label:
            ax.annotate(label, (x, y), textcoords="offset points",
                        xytext=(0, -22), ha="center", fontsize=9,
                        color=color, weight="bold", zorder=zorder + 1)