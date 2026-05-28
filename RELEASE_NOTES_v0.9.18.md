# FH6 Live Map v0.9.18 — Retro VFD HUD polish

## Changes
- HUD mini-map is vertically centered and gives more space to the live map area.
- HUD mini-map header is more compact.
- Gear indicator moved to the right side under TRIP A.
- GEAR label style is aligned with the RPM label style.
- Tapping the HUD mini-map now returns to Navigator mode if HUD was opened from Navigator mode.
- HUD mini-map now auto-zooms by speed in both Map and Navigator source modes: slower speed = closer zoom, higher speed = wider view.
- RPM label remains `x1000 rpm`.

## Checks
- Python compile check passed for `fh6_live_map_server.py`.
- JavaScript syntax check passed for `script_v095.js`.
- Local HTTP smoke test passed for `/` and `/api/state`.
