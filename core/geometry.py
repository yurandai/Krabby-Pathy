"""Polygon geometry helpers. No UI, no CasADi."""
from __future__ import annotations
from typing import List, Tuple
import math

Point = Tuple[float, float]


def convex_hull(points: List[Point]) -> List[Point]:
    """Andrew's monotone chain. Returns CCW hull vertices (no duplicate close)."""
    pts = sorted(set(points))
    if len(pts) <= 1:
        return list(pts)

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)

    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    return lower[:-1] + upper[:-1]


def is_strictly_convex(points: List[Point]) -> bool:
    """True iff the points form a strictly convex polygon with no redundant
    (trivial) vertices and no collinear triples."""
    n = len(points)
    if n < 3:
        return True
    if len(set(points)) != n:
        return False

    hull = convex_hull(points)
    if len(hull) != n:
        # Some vertex is inside the hull of the others → trivial point
        return False

    # No collinear triples
    for i in range(n):
        p0, p1, p2 = points[i], points[(i + 1) % n], points[(i + 2) % n]
        cross = (p1[0] - p0[0]) * (p2[1] - p1[1]) - (p1[1] - p0[1]) * (p2[0] - p1[0])
        if abs(cross) < 1e-9:
            return False
    return True


def sort_ccw(points: List[Point]) -> List[Point]:
    """Sort points CCW around their centroid."""
    if len(points) < 3:
        return list(points)
    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    return sorted(points, key=lambda p: math.atan2(p[1] - cy, p[0] - cx))


def inflated_region(points: List[Point], radius: float):
    """Return the Minkowski sum (points ⊕ disk(radius)) as a shapely geometry."""
    from shapely.geometry import Point as SPoint, LineString, Polygon as SPoly
    if len(points) == 0:
        return None
    if len(points) == 1:
        return SPoint(points[0]).buffer(radius, resolution=32)
    if len(points) == 2:
        return LineString(points).buffer(radius, cap_style=1, resolution=32)
    ordered = sort_ccw(points)
    return SPoly(ordered).buffer(radius, join_style=1, resolution=32)