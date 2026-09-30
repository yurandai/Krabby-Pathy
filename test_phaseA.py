# test_phaseA.py
from core import config as C
from core.state import ScenarioState
from core.nlp_solver import _solve_phase_a

state = ScenarioState()
state.N = 50
state.T_INIT = 15.0

T, X, U, iters, wall = _solve_phase_a(state)
print(f"Phase A OK: T = {T}, iters = {iters}, wall = {wall:.2f} s")
print(f"X[0,:] start = {X[0,0]:.4f}, end = {X[0,-1]:.4f}")
print(f"X[1,:] start = {X[1,0]:.4f}, end = {X[1,-1]:.4f}")
print(f"Velocity magnitude peak = {max(abs(X[3,:]).max(), abs(X[4,:]).max()):.4f}")