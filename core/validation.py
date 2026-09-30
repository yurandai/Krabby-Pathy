"""Scenario validation. Returns (ok, human-readable-message)."""
from __future__ import annotations
import math
from typing import Tuple

from shapely.geometry import Point as SPoint

from core import config as C
from core.state import ScenarioState
from core.geometry import inflated_region


def _pose_extent(half_w: float, half_l: float, theta: float):
    ct, st = math.cos(theta), math.sin(theta)
    x_ext = abs(half_w * ct) + abs(half_l * st)
    y_ext = abs(half_w * st) + abs(half_l * ct)
    return x_ext, y_ext


def pose_inside_field(x, y, theta, half_w, half_l, field_max, tol=1e-6):
    xe, ye = _pose_extent(half_w, half_l, theta)
    return (x - xe >= -tol and x + xe <= field_max + tol
            and y - ye >= -tol and y + ye <= field_max + tol)


def validate_state(state: ScenarioState) -> Tuple[bool, str]:
    # 0. Robot dimension constraint
    if state.robot_width < 2.0 * state.W - 1e-9:
        return False, (f"Robot width ({state.robot_width:.3f} m) must be "
                       f">= 2 x trackwidth ({2.0 * state.W:.3f} m).")
    if state.robot_length < 2.0 * state.L - 1e-9:
        return False, (f"Robot length ({state.robot_length:.3f} m) must be "
                       f">= 2 x wheelbase ({2.0 * state.L:.3f} m).")

    # 1. Obstacle validity
    for i, obs in enumerate(state.obstacles):
        ok, msg = obs.is_valid()
        if not ok:
            return False, f"Obstacle #{i + 1}: {msg}"

    hw = state.robot_half_width
    hl = state.robot_half_length

    # 2. Start / goal fit inside the field
    if not pose_inside_field(state.start_x, state.start_y, state.start_theta,
                             hw, hl, C.FIELD_MAX):
        return False, "Start pose puts the robot outside the field."
    if not pose_inside_field(state.goal_x, state.goal_y, state.goal_theta,
                             hw, hl, C.FIELD_MAX):
        return False, "Goal pose puts the robot outside the field."

    # 3. Start / goal not inside any inflated obstacle region
    for i, obs in enumerate(state.obstacles):
        try:
            region = inflated_region(obs.points, obs.radius)
        except Exception:
            continue
        if region is None:
            continue
        if region.contains(SPoint(state.start_x, state.start_y)):
            return False, (f"Start pose is inside obstacle #{i + 1}'s "
                           f"inflated region.")
        if region.contains(SPoint(state.goal_x, state.goal_y)):
            return False, (f"Goal pose is inside obstacle #{i + 1}'s "
                           f"inflated region.")

    # 4. Waypoints
    if len(state.waypoints) > 10:
        return False, f"Too many waypoints ({len(state.waypoints)} > 10)."

    for i, (wx, wy, wth) in enumerate(state.waypoints):
        if not pose_inside_field(wx, wy, wth, hw, hl, C.FIELD_MAX):
            return False, (f"Waypoint #{i + 1} puts the robot outside the "
                           f"field.")
        for j, obs in enumerate(state.obstacles):
            try:
                region = inflated_region(obs.points, obs.radius)
            except Exception:
                continue
            if region is not None and region.contains(SPoint(wx, wy)):
                return False, (f"Waypoint #{i + 1} is inside obstacle "
                               f"#{j + 1}'s inflated region.")

    return True, ""