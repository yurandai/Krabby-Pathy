# Krabby Pathy

A time-optimal trajectory planner for holonomic FTC robots.

**This repository publishes release downloads and user documentation only. The source code is not hosted here.**

Give it a start pose, a goal pose, convex obstacles and optional waypoints; it finds a collision-free trajectory that respects the robot's speed, acceleration and jerk limits.

## Download

**Current release: [Krabby Pathy v1.1.1](https://github.com/yurandai/Krabby-Pathy/releases/tag/v1.1.1)**, tested on macOS and 64-bit Windows. Packaged apps do not require Python.

See [all releases](https://github.com/yurandai/Krabby-Pathy/releases) and use `SHA256SUMS.txt` to verify the downloaded files.

### macOS — Apple silicon

1. Download `KrabbyPathy-1.1.1-macOS-arm64.zip` and unzip it.
2. Drag `Krabby Pathy.app` to Applications.
3. For the first launch, **right-click the app → Open**.

Requires macOS 12 or later on Apple silicon. This arm64 build does not support Intel Macs through Rosetta. The app is ad-hoc signed and is not notarised.

### Windows — recommended installer

Download `KrabbyPathy-1.1.1-Setup.exe` and double-click it. The installer:

- installs only for the current Windows user under `%LOCALAPPDATA%\Programs\Krabby Pathy`;
- does not require an administrator password;
- creates Start Menu and Desktop shortcuts;
- registers an uninstaller and can launch the app when finished.

Requires 64-bit Windows 10 or later. Python and Visual C++ runtimes do not need to be installed separately.

### Windows — portable

Extract **all** of `KrabbyPathy-1.1.1-win64.zip`, then run `KrabbyPathy.exe` in the extracted folder. Keep the folder together and do not run the EXE from inside the ZIP preview.

The normal application is `KrabbyPathy.exe`; `KrabbyPathy-console.exe` is for diagnostics.

### Unsigned-app warnings

The installer and apps are not commercially code-signed. If Windows SmartScreen shows “Windows protected your PC”, choose **More info → Run anyway** after verifying the file against `SHA256SUMS.txt`.

## What it does

- **Per-node safety corridors** as hard collision-avoidance constraints.
- **L1 actuator limits** for mecanum drivetrains: `|vx| + |vy| + κ|ω| ≤ V`.
- **Two-phase planning**: first find a feasible trajectory, then reduce its total time without returning a slower result than the feasible phase.
- **Jerk-aware warm starts** and post-solve verification at higher resolution.
- **Interactive field editing** for poses, waypoints and obstacles, with zoom, pan, playback and profile charts.
- **CSV and FTC-oriented exports**, scenario save/open, undo/redo, and English/Chinese interfaces.

## Diagnostics

If the Windows app cannot start, its error dialog includes a log path. The newest report is:

```text
%LOCALAPPDATA%\KrabbyPathy\Logs\latest-crash.log
```

For a full check, use the Start Menu's **Krabby Pathy diagnostics** shortcut, or run the following command from the application folder:

```powershell
KrabbyPathy-console.exe --selftest
```

The self-test checks numerical libraries, Qt, bundled assets, a complete trajectory solve and window rendering.
