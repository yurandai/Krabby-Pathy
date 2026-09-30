"""Obstacle data model."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple

from core.geometry import is_strictly_convex

Point = Tuple[float, float]


@dataclass
class Obstacle:
    points: List[Point] = field(default_factory=lambda: [(1.8, 1.8)])
    radius: float = 0.15

    def __post_init__(self):
        self.points = [tuple(p) for p in self.points]

    def copy(self) -> "Obstacle":
        return Obstacle(points=list(self.points), radius=self.radius)

    def is_valid(self) -> Tuple[bool, str]:
        """Return (ok, reason)."""
        if self.radius <= 0:
            return False, "Inflation radius must be > 0."
        if len(self.points) == 0:
            return False, "Obstacle must have at least one point."
        if len(set(self.points)) != len(self.points):
            return False, "Duplicate points are not allowed."
        if len(self.points) >= 3 and not is_strictly_convex(self.points):
            return False, ("Polygon is not strictly convex "
                           "(redundant vertex, collinear triple, or "
                           "out-of-order points).")
        return True, ""