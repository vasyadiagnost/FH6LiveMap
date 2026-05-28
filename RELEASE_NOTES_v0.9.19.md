# FH6 Live Map v0.9.19 — Retro VFD HUD polish

## Changes

- Added a mobile floating **Find / Follow** icon button for both map and navigator modes.
- The Find / Follow icon now has an active highlighted state when following is enabled.
- Removed the mobile text-heavy Find / Follow button from the settings sheet; follow control is now available directly on the map.
- Adjusted HUD **TRIP A** and **GEAR** layout so the gear indicator no longer overlaps the speed/RPM area.
- Reworked HUD mini-map auto-zoom: it now targets roughly the distance the car will cover in about 4.5 seconds at the current speed, with smoothing/hysteresis to avoid constant zoom jumping.
- Improved **TRIP A** logic: it now uses Forza `DistanceTraveled` when valid, but falls back to speed integration if that telemetry field stays at zero.

## Verification

- `python -m py_compile fh6_live_map_server.py`
- `node --check script_v095.js`
- Local server smoke test: `/` and `/api/state` respond successfully.
