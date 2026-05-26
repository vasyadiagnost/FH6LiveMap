# FH6 Live Map v0.9.15 compact nearest POI

## Download

Use the attached ZIP asset, extract it, then run `run_live_map.bat`.

## Quick start

1. Install Python 3.11+ for Windows.
2. Extract the ZIP.
3. In FH6, set:
   - Data Out: `On`
   - Data Out IP Address: `127.0.0.1`
   - Data Out IP Port: `5700`
4. Double-click `run_live_map.bat`.
5. Open `http://127.0.0.1:8766` if the browser does not open automatically.

## What's new in v0.9.15

- Mobile Nearest POI opens as a compact lower-left overlay in map and navigator modes.
- PC right-click on the map opens a custom destination menu.
- Mobile double tap opens the same menu for the point under the center crosshair.
- Custom destinations route through `/api/route` and do not require POI markers.
- Navigator speed auto-zoom keeps a short route lookahead visible.
- Zoom-out on acceleration is immediate; zoom-in on slowing down is delayed.

## Included routing graph

The included manual corrected road graph should report:

- `ok=true`
- `nodes=14561`
- `edges=18665`

Check after launch:

```text
http://127.0.0.1:8766/api/graph/status
```

## Notes

This is an unofficial fan-made local tool. It is not affiliated with Microsoft, Xbox, Playground Games, Turn 10, Forza, or GamerGuides.
