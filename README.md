# Note: The current source code available above is v1.0.0. Newer releases' source code will not exposed from now on due to academic reasons. Exact releasing date is still uncertain. Sorry for the inconvenience.

# Krabby Pathy

An A*-guided two-stage nonlinear trajectory optimization framework for
time-optimal holonomic robot navigation. Built for FTC and FRC autonomous
path planning.

Krabby Pathy solves a genuinely hard problem: given a start pose, a goal
pose, and a set of convex polygon obstacles, find a **time-optimal,
dynamically feasible, collision-free trajectory** that respects actuator
limits. It does this by combining discrete search with continuous
optimization.

## Features

- **A\* global planning** through inflated obstacle regions (polygon
  obstacles with user-configurable inflation radius)
- **Waypoint support** — up to 10 ordered intermediate poses
- **Two-stage NLP solver** — energy-minimizing warm start, then time-optimal
  refinement with smoothed L1 actuator constraints
- **Interactive field editor** — click-free; all poses and obstacles entered
  numerically
- **Live playback** — animate the optimized trajectory at real-time speed
- **Profile plots** — position, velocity, and acceleration vs time
- **Export** — full-state CSV, compact FTC CSV, Pedro Pathing pose
  sequence, waypoints-only, and raw XYZ formats

## Download (for FTC/FRC teams)

1. Go to the [Releases](../../releases) page.
2. Download the latest `KrabbyPathy.exe` or `KrabbyPathy.app`.
3. Run it. Windows may show a SmartScreen warning ("Windows protected
   your PC") — click **More info** → **Run anyway**. For Mac, run the command ```xattr -c (app location) && codesign --force --deep --sign - (app location)``` in order to open the app. This is expected for
   unsigned apps.
5. No installation required. No Python required.
