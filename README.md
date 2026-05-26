# FH6 Live Map

Local live map and companion navigator for **Forza Horizon 6 Data Out telemetry**.

This project runs on your gaming PC, receives FH6 telemetry over UDP, and opens a local browser map with the live car position, POI search, nearest POI, custom destination routing, and phone-friendly navigation mode.

> Unofficial fan-made tool. Not affiliated with Microsoft, Xbox, Playground Games, Turn 10, Forza, or GamerGuides.

## Current build

**Version:** `v0.9.15 compact nearest POI`  
**Best platform:** Windows PC  
**Default local URL:** `http://127.0.0.1:8766`  
**Default FH6 Data Out port:** `5700`  
**Included road graph:** manual corrected graph, `14561` nodes / `18665` edges expected

## What it does

- Receives FH6 Data Out UDP telemetry on port `5700`.
- Converts game `PositionX / PositionZ` into map coordinates using the included calibration data.
- Serves a local web UI at `http://127.0.0.1:8766`.
- Shows live speed, gear, heading, car marker, nearest POI, and map coordinates.
- Lets you search POIs, click POI markers, and build routes.
- Lets you set a custom destination by right-clicking the map on PC.
- On mobile, double-tap the map to open the same custom destination menu for the point under the crosshair.
- Uses the included `data/road_graph.json` for A* road routing.
- Supports heading-up navigator mode, auto-follow, auto-arrival, and compact mobile UI panels.
- Generates a LAN/phone URL and QR code from the PC server.
- Proxies map tiles and stores them in `tile_cache/` for faster later loading.

## Quick start: run from source

### 1. Install Python

Install **Python 3.11 or newer** on Windows.

During installation, enable:

```text
Add python.exe to PATH
```

### 2. Download and extract

Download the latest release ZIP, then extract it somewhere simple, for example:

```text
C:\FH6LiveMap\
```

Avoid running it directly from inside the ZIP window. Extract first.

### 3. Configure Forza Horizon 6

In FH6, open:

```text
Settings -> HUD and Gameplay
```

Set:

```text
Data Out:            On
Data Out IP Address: 127.0.0.1
Data Out IP Port:    5700
```

Use `127.0.0.1` when the app runs on the same PC as the game.

### 4. Start the map

Double-click:

```text
run_live_map.bat
```

The first launch may install the small `qrcode` Python package. Keep the console window open while using the map.

### 5. Open the web UI

The browser should open automatically. If it does not, open this manually:

```text
http://127.0.0.1:8766
```

When FH6 starts sending telemetry, the status should change from `WAITING` / `HOLDING` to `LIVE`.

### 6. Use phone mode, optional

Run the app on the gaming PC first. The console and the web UI show a LAN URL like:

```text
http://192.168.x.x:8766/
```

Open that URL on your phone while the phone and PC are on the same Wi-Fi/LAN.

If Windows Firewall asks for permission, allow access on **Private networks**.

## How to use the map

### PC controls

- **Locate / Follow**: center the camera on the car and keep following it.
- **Search**: type a POI name or category, then click a result or `Route`.
- **POI marker click**: select a marker and open its information card.
- **Right-click map**: open the custom destination menu.
- **Mouse wheel**: zoom in/out.
- **North up**: keep the map north-facing instead of heading-up.

### Mobile controls

- **Pinch**: zoom.
- **Drag**: short look-around; navigator follow resumes automatically.
- **Double tap**: open the custom destination menu for the center-crosshair point.
- **Bottom dock**: opens Info, Search, Settings, and Media panels.
- **Navigator Info button**: shows nearest POI in the compact lower-left overlay.

## Health checks

After launch, open:

```text
http://127.0.0.1:8766/api/graph/status
```

Expected for this package:

```text
ok: true
nodes: 14561
edges: 18665
```

Telemetry diagnostics:

```text
http://127.0.0.1:8766/api/diagnostics
```

## Troubleshooting

### The page says WAITING and the car does not move

Check FH6 settings again:

```text
Data Out: On
IP:       127.0.0.1
Port:     5700
```

Also make sure only one telemetry app is listening on the same UDP port.

### The console shows UDP ERROR

Another process is probably already using the port. Close old `FH6LiveMap.exe`, `FH6TelemetryExtractor.exe`, or other telemetry tools in Task Manager, then restart `run_live_map.bat`.

You can also run a different UDP port manually:

```text
python fh6_live_map_server.py --udp-port 5701
```

Then set FH6 Data Out Port to the same number.

### Python is not found

Install Python 3.11+ and make sure `Add python.exe to PATH` was enabled. Then reopen the project folder and double-click `run_live_map.bat` again.

### Phone cannot connect

- Use the LAN URL printed by the app, not `127.0.0.1`.
- Keep the phone and PC on the same Wi-Fi/LAN.
- Allow Windows Firewall access for Private networks.
- Some guest Wi-Fi networks block device-to-device connections.

### Map tiles are slow or blank

The app uses a static full-map fallback and caches map tiles into `tile_cache/`. The first zoom/pan can be slower; later runs should be faster once tiles are cached.

### Route looks wrong

Check graph status first:

```text
http://127.0.0.1:8766/api/graph/status
```

This package already includes the final hand-corrected road graph. Rebuilding is optional and usually not needed.

## Build a Windows EXE, optional

On a Windows builder PC with Python installed, run:

```text
build_exe_windows.bat
```

The portable build will be created in:

```text
dist\
```

To run the built EXE, open `dist` and double-click:

```text
run_exe_here.bat
```

Copy the whole `dist` folder to the gaming PC if you want a portable EXE setup.

## Rebuild the road graph, optional / advanced

The included graph is already built. Rebuild only if you know you need to regenerate it from cached tiles.

Expected tile cache layout:

```text
tile_cache\481\760\18\*.png
```

Then run:

```text
build_road_graph_from_tiles.bat
```

The builder installs CV packages listed in `requirements_cv.txt` and writes a new:

```text
data\road_graph.json
```

Restart the app after rebuilding.

## Project layout

```text
fh6_live_map_server.py              Main local server and telemetry receiver
run_live_map.bat                    One-click source runner for Windows
build_exe_windows.bat               Builds a one-file EXE with PyInstaller
build_road_graph_from_tiles.bat     Advanced road graph rebuild helper
FH6LiveMap.spec                     PyInstaller spec
data/markers.json                   POI marker data
data/map_meta.json                  Map metadata
data/calibration_points.csv         Calibration points
data/road_graph.json                Active routing graph
data/fh6_full_map_source.jpeg       Static full-map fallback image
tools/                              Graph generation / map extraction tools
CHANGELOG.md                        Historical version notes
```

## Notes for contributors

- Runtime has no heavy required dependency; `qrcode` is used for QR SVG generation and is auto-installed by `run_live_map.bat` when missing.
- CV dependencies are only needed for road graph generation.
- The server embeds the current web UI inside `fh6_live_map_server.py`. The `index_*.html` and `script_v095.js` files are kept as reference snapshots.
- `tile_cache/`, `dist/`, `build/`, and generated preview folders are intentionally ignored by Git.

## License

No license file has been selected yet. Add a `LICENSE` file before inviting redistribution or third-party modification.
