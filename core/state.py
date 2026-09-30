"""Mutable scenario state shared between UI panels and the solver."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
import math

from core.obstacle import Obstacle


@dataclass
class ScenarioState:
    # Poses
    start_x: float = 0.5
    start_y: float = 0.5
    start_theta: float = math.pi / 2
    goal_x: float = 3.0
    goal_y: float = 3.0
    goal_theta: float = math.pi / 2

    # Robot actuator geometry.
    # W = trackwidth — distance between left and right wheel contact points.
    # L = wheelbase  — distance between front and rear wheel contact points.
    W: float = 0.19
    L: float = 0.175

    # Robot physical bounding box (must enclose the actuator rectangle).
    robot_width: float = 0.38
    robot_length: float = 0.35

    # Actuator limits
    V_LIM: float = 1.2
    A_LIM: float = 3.0
    K_OMEGA: float = 0.365

    # Solver
    N: int = 50
    W_OBS: float = 1.0e5
    W_DEV: float = 1.0
    W_T: float = 0.5
    ASTAR_RES: float = 0.1
    T_INIT: float = 15.0

    # Lists
    obstacles: List[Obstacle] = field(default_factory=list)
    waypoints: List[tuple] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Derived helpers
    # ------------------------------------------------------------------
    @property
    def robot_half_width(self) -> float:
        return self.robot_width / 2.0

    @property
    def robot_half_length(self) -> float:
        return self.robot_length / 2.0

    @property
    def recommended_obstacle_radius(self) -> float:
        """Default obstacle inflation radius: max distance from robot center
        to a corner, so the center stays clear regardless of orientation."""
        return math.hypot(self.robot_half_width, self.robot_half_length)

    # ------------------------------------------------------------------
    # Resets
    # ------------------------------------------------------------------
    def reset_poses(self):
        self.start_x = 0.5
        self.start_y = 0.5
        self.start_theta = math.pi / 2
        self.goal_x = 3.0
        self.goal_y = 3.0
        self.goal_theta = math.pi / 2
        self.waypoints = []

    def reset_robot(self):
        self.W = 0.19
        self.L = 0.175
        self.robot_width = 0.38
        self.robot_length = 0.35
        self.V_LIM = 1.2
        self.A_LIM = 3.0
        self.K_OMEGA = 0.365

    def reset_solver(self):
        self.N = 50
        self.W_OBS = 1.0e5
        self.W_DEV = 1.0
        self.W_T = 0.5
        self.ASTAR_RES = 0.1
        self.T_INIT = 15.0