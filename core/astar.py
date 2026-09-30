"""Grid A* over polygon obstacles with inflation radius."""
from __future__ import annotations
import math
import heapq
from typing import Optional, Tuple

import numpy as np
from shapely.geometry import Point as SPoint
from shapely.prepared import prep

from core.geometry import inflated_region


def run_astar(start_xy, goal_xy, obstacles, field_max,
              res: float = 0.1,
              robot_W: float = 0.19,
              robot_L: float = 0.175):
    """Return (path, None) on success or (None, message) on failure."""
    n_cells = int(math.ceil(field_max / res)) + 1

    prepared_regions = []
    for obs in obstacles:
        try:
            g = inflated_region(obs.points, obs.radius)
            if g is not None:
                prepared_regions.append(prep(g))
        except Exception:
            continue

    def to_grid(pos):
        i = int(np.clip(round(pos[0] / res), 0, n_cells - 1))
        j = int(np.clip(round(pos[1] / res), 0, n_cells - 1))
        return (i, j)

    def to_world(node):
        return (node[0] * res, node[1] * res)

    def is_blocked(node):
        wx, wy = to_world(node)
        if wx < robot_W or wx > field_max - robot_W:
            return True
        if wy < robot_L or wy > field_max - robot_L:
            return True
        pt = SPoint(wx, wy)
        for r in prepared_regions:
            if r.contains(pt):
                return True
        return False

    start = to_grid(start_xy)
    goal = to_grid(goal_xy)

    if is_blocked(start):
        return None, "Start pose is blocked (inside an obstacle or wall)."
    if is_blocked(goal):
        return None, "Goal pose is blocked (inside an obstacle or wall)."

    open_set = [(0.0, start)]
    came_from = {}
    g_score = {start: 0.0}

    moves = [(1, 0), (-1, 0), (0, 1), (0, -1),
             (1, 1), (1, -1), (-1, 1), (-1, -1)]

    while open_set:
        _, current = heapq.heappop(open_set)

        if current == goal:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return np.array([to_world(n) for n in path]), None

        for dx, dy in moves:
            nb = (current[0] + dx, current[1] + dy)
            if not (0 <= nb[0] < n_cells and 0 <= nb[1] < n_cells):
                continue
            if is_blocked(nb):
                continue
            step = math.sqrt(2.0) if (dx and dy) else 1.0
            tentative = g_score[current] + step
            if nb not in g_score or tentative < g_score[nb]:
                came_from[nb] = current
                g_score[nb] = tentative
                h = math.hypot(goal[0] - nb[0], goal[1] - nb[1])
                heapq.heappush(open_set, (tentative + h, nb))

    return None, "No path found. Check obstacles."


def run_astar_segmented(start_xy, goal_xy, waypoints, obstacles, field_max,
                        res=0.1, robot_W=0.19, robot_L=0.175):
    pts = [(start_xy[0], start_xy[1])]
    pts += [(float(wp[0]), float(wp[1])) for wp in waypoints]
    pts.append((goal_xy[0], goal_xy[1]))

    segments = []
    for i in range(len(pts) - 1):
        seg, err = run_astar(pts[i], pts[i + 1], obstacles, field_max,
                             res, robot_W, robot_L)
        if seg is None:
            return None, f"A* segment {_seg_label(i, len(pts) - 1)} " \
                          f"failed: {err}"
        segments.append(seg)

    full = segments[0]
    for seg in segments[1:]:
        full = np.vstack([full, seg[1:]])
    return full, None


def _seg_label(i, total):
    if total == 1:
        return "start -> goal"
    if i == 0:
        return "start -> WP1"
    if i == total - 1:
        return f"WP{total - 1} -> goal"
    return f"WP{i} -> WP{i + 1}"