"""CasADi NLP — polygon obstacles, waypoints, wrapped angles."""
from __future__ import annotations
import math
import time
from typing import Callable, Optional, List
import threading

import casadi as ca
import numpy as np

from core import config as C
from core.state import ScenarioState
from core.obstacle import Obstacle
from core.geometry import sort_ccw


_SQRT_EPS = 1e-10


def _solver_opts():
    return {
        'ipopt.print_level': 0,
        'ipopt.max_iter': 100000,
        'ipopt.mu_strategy': 'adaptive',
        'ipopt.acceptable_tol': 1e-4,
        'print_time': 0,
    }


def _wrap_angle(theta: float) -> float:
    return (theta + math.pi) % (2.0 * math.pi) - math.pi


def _resolve_thetas(start_theta_raw: float, goal_theta_raw: float):
    start = _wrap_angle(start_theta_raw)
    goal_wrapped = _wrap_angle(goal_theta_raw)
    delta = _wrap_angle(goal_wrapped - start)
    return start, start + delta


def _safe_sqrt(x):
    return ca.sqrt(x + _SQRT_EPS)


def _obstacle_penalty_sq(X_xy, obs: Obstacle):
    """Return (r - d)_+ at every node, shape 1 x (N+1). Squared by caller."""
    pts = obs.points
    r = float(obs.radius)

    if len(pts) == 1:
        cx, cy = pts[0]
        d2 = (X_xy[0, :] - cx) ** 2 + (X_xy[1, :] - cy) ** 2
        d = _safe_sqrt(d2)
    elif len(pts) == 2:
        ax, ay = pts[0]
        bx, by = pts[1]
        ex, ey = bx - ax, by - ay
        L2 = ex * ex + ey * ey
        if L2 < 1e-12:
            d2 = (X_xy[0, :] - ax) ** 2 + (X_xy[1, :] - ay) ** 2
            d = _safe_sqrt(d2)
        else:
            t = ((X_xy[0, :] - ax) * ex + (X_xy[1, :] - ay) * ey) / L2
            tc = ca.fmax(0, ca.fmin(1, t))
            px = ax + tc * ex
            py = ay + tc * ey
            d2 = (X_xy[0, :] - px) ** 2 + (X_xy[1, :] - py) ** 2
            d = _safe_sqrt(d2)
    else:
        ordered = sort_ccw(pts)
        k = len(ordered)
        edge_sds = []
        for i in range(k):
            ax, ay = ordered[i]
            bx, by = ordered[(i + 1) % k]
            ex, ey = bx - ax, by - ay
            nlen = math.hypot(ex, ey)
            if nlen < 1e-12:
                continue
            nx, ny = ey / nlen, -ex / nlen
            sd = (X_xy[0, :] - ax) * nx + (X_xy[1, :] - ay) * ny
            edge_sds.append(sd)
        if not edge_sds:
            return ca.DM.zeros(1, X_xy.shape[1])
        d = edge_sds[0]
        for sd in edge_sds[1:]:
            d = ca.fmax(d, sd)

    return ca.fmax(0, r - d)


def _obstacle_cost(X, state: ScenarioState):
    """Union-aware soft penalty: sum violations, then square."""
    if not state.obstacles:
        return 0
    X_xy = X[0:2, :]
    total = None
    for obs in state.obstacles:
        v = _obstacle_penalty_sq(X_xy, obs)
        total = v if total is None else total + v
    return state.W_OBS * ca.sumsqr(total)


def _hermite_simpson(opti, X, U, dt):
    def fmat(Xm, Um):
        return ca.vertcat(Xm[3, :], Xm[4, :], Xm[5, :],
                          Um[0, :], Um[1, :], Um[2, :])
    Xk, Xk1 = X[:, :-1], X[:, 1:]
    Uk, Uk1 = U[:, :-1], U[:, 1:]
    fk = fmat(Xk, Uk)
    fk1 = fmat(Xk1, Uk1)
    Xc = 0.5 * (Xk + Xk1) + (dt / 8.0) * (fk - fk1)
    Uc = 0.5 * (Uk + Uk1)
    fc = fmat(Xc, Uc)
    opti.subject_to(Xk1 - Xk - (dt / 6.0) * (fk + 4.0 * fc + fk1) == 0)


def _box_bounds(opti, X, U, state: ScenarioState):
    hw = state.robot_half_width
    hl = state.robot_half_length
    V, A, k = state.V_LIM, state.A_LIM, state.K_OMEGA
    opti.subject_to(opti.bounded(hw, X[0, :], C.FIELD_MAX - hw))
    opti.subject_to(opti.bounded(hl, X[1, :], C.FIELD_MAX - hl))
    opti.subject_to(opti.bounded(-4.0 * math.pi, X[2, :], 4.0 * math.pi))
    opti.subject_to(opti.bounded(-V, X[3, :], V))
    opti.subject_to(opti.bounded(-V, X[4, :], V))
    opti.subject_to(opti.bounded(-V / k, X[5, :], V / k))
    opti.subject_to(opti.bounded(-A, U[0, :], A))
    opti.subject_to(opti.bounded(-A, U[1, :], A))
    opti.subject_to(opti.bounded(-A / k, U[2, :], A / k))


def _boundary_conditions(opti, X, U, state: ScenarioState):
    N = state.N
    start_theta, goal_theta = _resolve_thetas(
        state.start_theta, state.goal_theta)
    x_start = ca.vertcat(state.start_x, state.start_y, start_theta, 0, 0, 0)
    x_goal = ca.vertcat(state.goal_x, state.goal_y, goal_theta, 0, 0, 0)
    opti.subject_to(X[:, 0] == x_start)
    opti.subject_to(X[:, N] == x_goal)
    opti.subject_to(U[:, 0] == 0)
    opti.subject_to(U[:, N] == 0)


def _waypoint_node_indices(N: int, M: int):
    if M == 0:
        return []
    indices = []
    for i in range(M):
        k = round((i + 1) * N / (M + 1))
        k = max(1, min(N - 1, k))
        indices.append(int(k))
    for i in range(1, len(indices)):
        if indices[i] <= indices[i - 1]:
            indices[i] = indices[i - 1] + 1
    return indices


def _add_waypoint_constraints(opti, X, state: ScenarioState):
    M = len(state.waypoints)
    if M == 0:
        return
    indices = _waypoint_node_indices(state.N, M)
    for i, k in enumerate(indices):
        x, y, th = state.waypoints[i]
        th_wrapped = _wrap_angle(float(th))
        opti.subject_to(X[0, k] == float(x))
        opti.subject_to(X[1, k] == float(y))
        opti.subject_to(X[2, k] == th_wrapped)


def _smooth_initial_guess(state: ScenarioState):
    """Piecewise smoothstep warm start that hits every waypoint exactly."""
    N = state.N
    M = len(state.waypoints)
    T = float(state.T_INIT)

    start_theta, goal_theta = _resolve_thetas(
        state.start_theta, state.goal_theta)
    indices = _waypoint_node_indices(N, M)

    controls = [(0, state.start_x, state.start_y, start_theta)]
    for i, k in enumerate(indices):
        x, y, th = state.waypoints[i]
        controls.append((k, float(x), float(y), _wrap_angle(float(th))))
    controls.append((N, state.goal_x, state.goal_y, goal_theta))

    X0 = np.zeros((6, N + 1))
    U0 = np.zeros((3, N + 1))

    for seg in range(len(controls) - 1):
        k0, x0, y0, th0 = controls[seg]
        k1, x1, y1, th1 = controls[seg + 1]
        n = k1 - k0
        if n <= 0:
            continue
        dt = T * n / N
        s = np.linspace(0.0, 1.0, n + 1)
        h = 3.0 * s ** 2 - 2.0 * s ** 3
        dh = 6.0 * s * (1.0 - s) / dt
        d2h = 6.0 * (1.0 - 2.0 * s) / dt ** 2

        for i, (v0, v1) in enumerate([(x0, x1), (y0, y1), (th0, th1)]):
            delta = v1 - v0
            X0[i, k0:k1 + 1] = v0 + delta * h
            X0[i + 3, k0:k1 + 1] = delta * dh
            U0[i, k0:k1 + 1] = delta * d2h

    return X0, U0


# ---------------------------------------------------------------
# Phases
# ---------------------------------------------------------------
def _solve_phase_a(state: ScenarioState, X_init=None, U_init=None):
    N = state.N
    opti = ca.Opti()
    X = opti.variable(6, N + 1)
    U = opti.variable(3, N + 1)
    T = float(state.T_INIT)
    dt = T / N

    opti.minimize(ca.sumsqr(U) + _obstacle_cost(X, state))
    _box_bounds(opti, X, U, state)
    _boundary_conditions(opti, X, U, state)
    _add_waypoint_constraints(opti, X, state)
    _hermite_simpson(opti, X, U, dt)

    if X_init is None:
        X_init, U_init = _smooth_initial_guess(state)
    opti.set_initial(X, X_init)
    opti.set_initial(U, U_init)

    opti.solver('ipopt', _solver_opts())
    t0 = time.time()
    sol = opti.solve()
    wall = time.time() - t0
    iters = sol.stats().get('iter_count', -1)
    return T, np.array(sol.value(X)), np.array(sol.value(U)), int(iters), wall


def _solve_phase_b(state: ScenarioState, warm):
    _, X_ws, U_ws, _, _ = warm
    N = state.N
    opti = ca.Opti()
    X = opti.variable(6, N + 1)
    U = opti.variable(3, N + 1)
    T = opti.variable()
    dt = T / N

    opti.minimize(T + _obstacle_cost(X, state))
    opti.subject_to(T >= 0.1)
    opti.subject_to(T <= 100.0)

    _box_bounds(opti, X, U, state)
    _boundary_conditions(opti, X, U, state)
    _add_waypoint_constraints(opti, X, state)
    _hermite_simpson(opti, X, U, dt)

    V, A, k = state.V_LIM, state.A_LIM, state.K_OMEGA
    opti.subject_to(X[3, :] ** 2 + X[4, :] ** 2 + (k * X[5, :]) ** 2
                    <= V ** 2 / 3)
    opti.subject_to(U[0, :] ** 2 + U[1, :] ** 2 + (k * U[2, :]) ** 2
                    <= A ** 2 / 3)

    opti.set_initial(X, X_ws)
    opti.set_initial(U, U_ws)
    opti.set_initial(T, warm[0])

    opti.solver('ipopt', _solver_opts())
    t0 = time.time()
    sol = opti.solve()
    wall = time.time() - t0
    iters = sol.stats().get('iter_count', -1)
    return float(sol.value(T)), np.array(sol.value(X)), np.array(sol.value(U)), int(iters), wall


def _solve_stage2(state: ScenarioState, warm):
    T_ref, X_ref, U_ref, _, _ = warm
    N = state.N
    opti = ca.Opti()
    X = opti.variable(6, N + 1)
    U = opti.variable(3, N + 1)
    T = opti.variable()
    dt = T / N

    X_ref_dm = ca.DM(X_ref)
    dev = state.W_DEV * ca.sumsqr(X[0:3, :] - X_ref_dm[0:3, :])
    opti.minimize(dev + state.W_T * T + _obstacle_cost(X, state))

    opti.subject_to(T >= 0.1)
    opti.subject_to(T <= 2.0 * T_ref + 5.0)

    _box_bounds(opti, X, U, state)
    _boundary_conditions(opti, X, U, state)
    _add_waypoint_constraints(opti, X, state)
    _hermite_simpson(opti, X, U, dt)

    V, A, k = state.V_LIM, state.A_LIM, state.K_OMEGA
    eps = 1e-4
    opti.subject_to(
        ca.sqrt(X[3, :] ** 2 + eps) + ca.sqrt(X[4, :] ** 2 + eps)
        + k * ca.sqrt(X[5, :] ** 2 + eps) <= V)
    opti.subject_to(
        ca.sqrt(U[0, :] ** 2 + eps) + ca.sqrt(U[1, :] ** 2 + eps)
        + k * ca.sqrt(U[2, :] ** 2 + eps) <= A)

    opti.set_initial(X, X_ref)
    opti.set_initial(U, U_ref)
    opti.set_initial(T, T_ref)

    opti.solver('ipopt', _solver_opts())
    t0 = time.time()
    sol = opti.solve()
    wall = time.time() - t0
    iters = sol.stats().get('iter_count', -1)
    return float(sol.value(T)), np.array(sol.value(X)), np.array(sol.value(U)), int(iters), wall


# ---------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------
def solve_pipeline(state: ScenarioState, pipeline: List[str],
                   progress_cb: Callable[[str], None] = lambda s: None,
                   cancel_event: Optional[threading.Event] = None):
    if cancel_event is None:
        cancel_event = threading.Event()

    phases = {}
    errors = {}
    wall_total = 0.0

    progress_cb("Phase A (energy warm start)")
    try:
        T, X, U, iters, wall = _solve_phase_a(state)
        phases['A'] = (T, X, U, iters, wall)
        wall_total += wall
    except Exception as e:
        errors['A'] = f"{type(e).__name__}: {e}"
        return {'phases': phases, 'errors': errors,
                'final_phase': None, 'wall_total': wall_total}

    if cancel_event.is_set():
        return _finalize(phases, errors, wall_total, state)

    if 'B' in pipeline:
        progress_cb("Phase B (L2 time-optimal)")
        try:
            T, X, U, iters, wall = _solve_phase_b(state, phases['A'])
            phases['B'] = (T, X, U, iters, wall)
            wall_total += wall
        except Exception as e:
            errors['B'] = f"{type(e).__name__}: {e}"

    if cancel_event.is_set():
        return _finalize(phases, errors, wall_total, state)

    if 'C' in pipeline:
        progress_cb("Stage 2 (L1 refinement)")
        ref = phases.get('B') or phases.get('A')
        try:
            T, X, U, iters, wall = _solve_stage2(state, ref)
            phases['C'] = (T, X, U, iters, wall)
            wall_total += wall
        except Exception as e:
            errors['C'] = f"{type(e).__name__}: {e}"

    return _finalize(phases, errors, wall_total, state)


def _finalize(phases, errors, wall_total, state):
    final_phase = None
    for name in ['C', 'B', 'A']:
        if name in phases:
            final_phase = name
            break

    result = {'phases': phases, 'errors': errors,
              'final_phase': final_phase, 'wall_total': wall_total}
    if final_phase is not None:
        T, X, U, iters, wall = phases[final_phase]
        result.update({'T': T, 'X': X, 'U': U, 'iters': iters})
        result['report'] = _build_report(state, phases, final_phase, wall_total)
    return result


def _build_report(state, phases, final_phase, wall_total):
    T, X, U, iters, _ = phases[final_phase]
    eps = 1e-4
    k = state.K_OMEGA

    peak_v = float(np.max(
        np.sqrt(X[3, :] ** 2 + eps) + np.sqrt(X[4, :] ** 2 + eps)
        + k * np.sqrt(X[5, :] ** 2 + eps)))
    peak_a = float(np.max(
        np.sqrt(U[0, :] ** 2 + eps) + np.sqrt(U[1, :] ** 2 + eps)
        + k * np.sqrt(U[2, :] ** 2 + eps)))

    min_clear = float('inf')
    try:
        from shapely.geometry import Point as SPoint
        from core.geometry import inflated_region
        regions = []
        for obs in state.obstacles:
            try:
                g = inflated_region(obs.points, obs.radius)
                if g is not None:
                    regions.append(g)
            except Exception:
                pass
        for i in range(X.shape[1]):
            p = SPoint(X[0, i], X[1, i])
            for r in regions:
                d = p.distance(r)
                if d < min_clear:
                    min_clear = d
    except Exception:
        min_clear = float('nan')

    lines = [f"Final phase: {final_phase}",
             f"Final time T: {T:.4f} s",
             f"Wall-clock: {wall_total:.2f} s",
             ""]
    for name in ['A', 'B', 'C']:
        if name in phases:
            _, _, _, iters, wall = phases[name]
            lines.append(f"Phase {name}: {iters} iters, {wall:.2f} s")
    lines.append("")
    lines.append(f"Peak L1 velocity: {peak_v:.4f} / {state.V_LIM:.4f} "
                 f"({100 * peak_v / state.V_LIM:.1f}%)")
    lines.append(f"Peak L1 acceleration: {peak_a:.4f} / {state.A_LIM:.4f} "
                 f"({100 * peak_a / state.A_LIM:.1f}%)")
    if math.isfinite(min_clear):
        lines.append(f"Min obstacle clearance: {min_clear * 100:.2f} cm")
    return "\n".join(lines)