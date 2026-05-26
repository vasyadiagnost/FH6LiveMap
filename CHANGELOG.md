# Changelog / historical notes

FH6 Live Map v0.9.15 Compact lower-left nearest POI

Based on stable v0.9.12 rendering. The final hand-corrected road graph is unchanged.

Added:
- PC right-click on the map opens a custom destination menu.
- Mobile double tap opens the same menu for the point under the center crosshair.
- Custom destinations route through /api/route target_x/target_y and do not require POI markers.
- Navigator speed auto-zoom keeps a short route lookahead visible.
- Zoom-out on acceleration is immediate; zoom-in on slowing down is delayed.

Smoke-check after launch:
- open http://127.0.0.1:8766/api/graph/status
- expected: ok=true, around 14561 nodes and 18665 edges.

FH6 Live Map v0.9.8 final manual road-map build

This package keeps the same app structure as the stable v0.9.8 copy, but replaces data/road_graph.json with a graph rebuilt from the final hand-corrected road mask.

Manual routing data included:
- data/road_graph.json — active routing graph used by the app;
- data/fh6_corrected_road_mask_final.png — original final mask from the drawing pass;
- data/fh6_road_edits_final.json — final edit strokes;
- data/fh6_corrected_road_mask_final_clean_for_graph.png — tiny-island-cleaned mask used for graph generation;
- tools/build_road_graph_from_manual_mask.py — reproducibility script.

Smoke-check after launch:
- open http://127.0.0.1:8766/api/graph/status
- expected: ok=true, around 14.5k nodes, around 18.6k edges before/after small runtime stitches.

FH6 Live Map v0.9.6 Asphalt-balanced routing

Fixes in this sprint:
- heading-up rotation from v0.9.5 is kept;
- road routing no longer treats white/asphalt preference as an excuse for absurd loops;
- runtime A* now recomputes edge costs from the current routing profile, so changing route behavior does not require rebuilding road_graph.json;
- route picker tries two profiles: asphalt_balanced first, detour_escape when a short orange/dashed connector is better than a huge white-only loop;
- route response includes debug fields: routing.profile, routing.detour_ratio, routing.road_profile_length_px;
- CV graph builder has stricter white-component cleanup to reduce buildings/roofs/city blocks becoming false asphalt;
- build_road_graph_from_tiles.bat now uses balanced cost factors: white=1.00, orange=1.12, dashed=2.35, unknown=8.00.

Recommended test order:
1) Run run_live_map.bat and test existing graph.
2) Open http://127.0.0.1:8766/api/graph/status and check node/edge class counts.
3) If many false white blobs remain, run build_road_graph_from_tiles.bat and inspect data\road_graph_preview.

FH6 Live Map v0.9.3

Fixes in this sprint:
- broader road snap search so nearby false-positive blobs do not force direct diagonal fallback;
- if a road graph exists but routing fails, the UI no longer draws a misleading diagonal line;
- route failures are shown in the navigator panel and logged in browser console;
- generated CV graph defaults to no diagonal grid links to reduce corner-cutting;
- synthetic bridge edges are heavily penalized at runtime.

FH6 Live Map v0.9.1 Road Graph Routing + Heading-Up Navigation

Purpose
-------
Local live map / companion navigator for Forza Horizon 6 Data Out telemetry.

Version 0.9.1 notes
-------------------
This build is based on the working v0.9.0 line and includes the generated road graph from road_graph.json.

Added/changed:
- data/road_graph.json is included in this project folder and in the PyInstaller spec as a bundled fallback.
- Route building now uses A* over the extracted road graph when possible.
- The loader stitches small CV/tile-seam gaps in the generated graph, so the first graph is usable for MVP routing instead of falling back to a straight preview line too often.
- /api/graph/status now reports graph nodes, edges, stitched edges, components and largest connected components.
- When a route is built from a POI/search result, Navigator mode forces Heading-up: the map auto-rotates against the player heading so the direction of movement points upward.
- North up is still available for manual map browsing, but route navigation intentionally switches it off.
- The green player marker gets a small forward nose in Navigator mode.

Important runtime layout
------------------------
Recommended portable layout:

FH6LiveMap_Portable/
  FH6LiveMap.exe
  run_exe_here.bat
  data/
    markers.json
    map_meta.json
    calibration_points.csv
    road_graph.json
  tile_cache/
    481/
      760/
        18/
          ...cached tiles...

Road graph behavior
-------------------
- If data/road_graph.json exists next to the script/EXE, it is used first.
- If it does not exist next to a one-file EXE, the EXE can use the bundled graph from the spec.
- If no graph is available, routes fall back to direct preview.
- Tile cache is still external data. Keep tile_cache next to the script/EXE for offline map tiles.

Quick check
-----------
After launch, open:
http://127.0.0.1:8766/api/graph/status

A healthy v0.9.1 graph response should show ok=true and a large nodes count.


FH6 Live Map v0.9.0 Search + Routing + CV Road Graph

Purpose
-------
Local live map preview for Forza Horizon 6 Data Out telemetry.

What it does:
- receives FH6 UDP telemetry on port 5700;
- converts PositionX / PositionZ into GamerGuides Japan map coordinates using our manual calibration;
- serves a local web map at http://127.0.0.1:8766;
- shows a live car arrow with heading/yaw-derived direction;
- keeps the last known car position visible when FH6 pauses or stops sending packets;
- shows GamerGuides POI markers and nearest POI list;
- lets you click POI markers and nearest POI rows to highlight them and show a small info card;
- proxies and caches GamerGuides map tiles locally.

No third-party Python dependencies are required.

Forza Horizon 6 setup
---------------------
Settings > HUD and Gameplay:
- Data Out: On
- Data Out IP Address: 127.0.0.1
- Data Out IP Port: 5700

Run from Python
---------------
python fh6_live_map_server.py

Then open:
http://127.0.0.1:8766

Phone mode
----------
Run the app on the gaming PC.
The terminal will print LAN URLs like:
http://192.168.x.x:8766/

Open that URL on your phone while both devices are on the same Wi-Fi/LAN.
If Windows Firewall asks, allow Private network access.

Build Windows EXE
-----------------
On a Windows builder PC with Python installed:
1) Run:
   build_exe_windows.bat

2) Copy this file to the gaming PC:
   dist\FH6LiveMap.exe

The gaming PC does not need Python.

Notes
-----
- Map tiles are loaded from gamerguides.com and cached into tile_cache/.
- The first launch/zoom may load tiles slowly; later it will be faster.
- The map formula is an MVP calibration, good enough for first live preview.
- The Locate / Follow button centers the map on the current car position and keeps following it.
- If the car arrow orientation looks offset, we will add a yaw offset control in the next iteration.


Version 0.9.0 Search + Routing + CV Road Graph notes
------------------------------------------------------
Added product-MVP features on top of the confirmed working v0.8.9 telemetry line:
- Search destination panel on the map: search POI by name/category, select it, or press Route directly from results.
- Backend search endpoint: /api/search?q=... for future UI/tooling use.
- Backend route endpoint: /api/route?target_x=...&target_y=... . If data/road_graph.json exists, the app uses graph routing; otherwise it safely falls back to the old direct preview route.
- Graph status endpoint: /api/graph/status shows whether data/road_graph.json is loaded.
- Route rendering was upgraded from a single straight div-line to an SVG polyline layer, ready for real road paths.
- Added tools/extract_roads_from_tiles.py to computer-vision-scan cached GamerGuides tiles and generate data/road_graph.json.
- Added build_road_graph_from_tiles.bat for one-click graph generation from tile_cache on Windows.

Road graph generation
---------------------
1) Make sure tiles are cached in:
   tile_cache\481\760\18\*.png

2) Run:
   build_road_graph_from_tiles.bat

The script installs only builder-side CV packages:
   pillow, numpy, opencv-python

The live map runtime does not need these packages. It only reads the generated:
   data\road_graph.json

If the generated graph is noisy or routes through icons/text, rerun the tool with stricter parameters, for example:
   py tools\extract_roads_from_tiles.py --tile-cache tile_cache --layer 760 --zoom 18 --output data\road_graph.json --stride 12 --min-road-ratio 0.12

If the graph misses thin roads, loosen it:
   py tools\extract_roads_from_tiles.py --tile-cache tile_cache --layer 760 --zoom 18 --output data\road_graph.json --stride 8 --min-road-ratio 0.05

Routing behavior
----------------
- Without data/road_graph.json: route is explicitly a direct preview.
- With data/road_graph.json: route uses A* over the extracted graph.
- If the car/target is too far from graph nodes or the graph is disconnected, the app falls back to direct preview instead of breaking navigation.
- Restart the live map after rebuilding road_graph.json. If you run the one-file EXE from dist, create dist\data\road_graph.json next to FH6LiveMap.exe or run the builder from the same folder where the EXE lives.

Version 0.4.1 Telemetry Safe notes
----------------------------------
This build is intentionally based on the last confirmed telemetry-working v0.4 branch.

Added:
- visible packet counter in the UI;
- visible UDP ERROR status if the telemetry port cannot be opened;
- /api/diagnostics endpoint with current telemetry state.

If UDP ERROR appears:
1) Close all FH6LiveMap.exe / FH6TelemetryExtractor.exe processes in Task Manager.
2) Keep FH6 Data Out IP as 127.0.0.1 when the app runs on the same PC as the game.
3) Keep FH6 Data Out Port as 5700, or launch the app with --udp-port and set the same port in FH6.

Version 0.8 Stable notes
------------------------
Based on the confirmed telemetry-working v0.4.1 branch.

Restored/added:
- POI click popup with description placeholder and Build route button;
- local-network phone URL in the UI with Copy button;
- Navigator mode with direct-to-target preview line;
- Spotify/System Media widget using PC system media keys;
- dark navigation speed panel;
- player marker changed from heading arrow to bright green dot;
- visible packet counter removed from the main web UI.

Kept:
- UDP ERROR diagnostics if the telemetry port cannot be opened;
- /api/diagnostics endpoint.

Version 0.8.2 Telemetry Hardening notes
---------------------------------------
Based on the telemetry-working v0.4.1 lineage and the restored v0.8 feature set.

Telemetry changes:
- default UDP bind changed from 0.0.0.0 to 127.0.0.1, matching the recommended FH6 Data Out IP for same-PC use;
- console heartbeat prints packet count every 2 seconds so backend telemetry can be verified even if the web UI misbehaves;
- UDP ERROR diagnostics are kept.

Media fix:
- /api/media/* now works with POST as used by the web UI buttons.

Version 0.8.3 Frontend Poll Fix notes
-------------------------------------
This build keeps the v0.8.2 backend telemetry hardening.

Fixed:
- frontend telemetry polling now starts immediately, before marker loading and before any optional render step;
- UI updates speed/map/LIVE status independently from POI rendering;
- marker loading errors can no longer stop telemetry polling;
- player position updates no longer require full map/marker redraw on every packet.

This is a repair build. Offline tile prefetch is intentionally not re-added here yet.

Version 0.8.4 Pan Sync Fix notes
--------------------------------
Fixed:
- telemetry was updating speed/gear/map values, but the visual map layers were not being re-rendered after Follow changed panX/panY;
- the green player dot and the map now update together;
- Locate / Follow now recenters the map, tiles, POI markers, and the player dot in one synchronized pass.

Version 0.8.5 Nav Heading + Pinch notes
---------------------------------------
Added:
- Navigator mode now uses a heading-up map: when Follow is enabled, the map rotates so the road ahead is shown upward, similar to an in-game minimap.
- The green player dot stays fixed near the lower part of the screen in Navigator mode.
- Mobile pinch-to-zoom support was added using Pointer Events.

Notes:
- This does not build road routes yet; it only improves the navigator camera behavior.
- If heading-up rotation feels too aggressive, we can add a toggle later.

Version 0.8.6 Marker Layer Fix notes
------------------------------------
Fixed:
- POI markers could disappear after the heading-up map rotation change because markerLayer was being transformed without an explicit viewport-sized box;
- markerLayer and tileLayer now have position:absolute; inset:0; width/height:100%;
- marker culling is more tolerant in Navigator mode;
- Nearest POI now distinguishes "waiting for telemetry" from "POI markers are loading".

Version 0.8.7 Marker Restore notes
----------------------------------
Fixed:
- updateNearest() had been accidentally removed during the heading-up / marker-layer patch chain;
- loadMarkers() called updateNearest(), threw a JavaScript error, entered catch, and cleared the loaded markers array;
- POI markers therefore disappeared even though markers.json was present and loaded from the backend.

Changed:
- updateNearest() is restored;
- loadMarkers() no longer clears markers after a render-only error;
- markerLayer z-index is explicitly set below the player dot and above tiles.

Version 0.8.8 Pause Hold + Smooth notes
---------------------------------------
Fixed/added:
- Pause coordinate hold: if FH6 sends speed=0 and Gear=0 ("-" in the UI), the app keeps the last accepted driving coordinate instead of jumping to a bogus pause/menu coordinate.
- The API exposes pause_coordinate_hold for diagnostics.
- Frontend smoothing: telemetry polling now updates target position; requestAnimationFrame interpolates the green dot and heading-up camera for smoother motion.
- Marker and nearest-POI redraws are throttled, while player/map/route visuals update more smoothly.

Version 0.8.9 UI Follow + QR notes
----------------------------------
Changed only UI/navigation options:
- Locate / Follow is enabled by default on every page load.
- Added a North up toggle. When enabled, Navigator mode keeps north at the top instead of rotating the map heading-up.
- Zoom buttons and zoom select were removed from the visible UI. Wheel and pinch zoom still work.
- The PC link panel now says "PC URL to open on phone" and includes a QR code generated locally by the PC server.
- The PC link/QR panel is hidden when the page is opened from a phone/tablet.
- Build scripts now install the qrcode Python package so the EXE can generate QR SVG locally.

v0.9.2 notes
------------
- Navigation now trims the active route behind the player instead of drawing back to the original start point.
- While navigation is active, the frontend re-requests /api/route when the car has moved far enough from the route anchor or leaves the current route corridor.
- Heading-up mode still turns on automatically when a route is started.
- The road graph loader now penalizes synthetic CV bridge edges more heavily, so they are used mainly to repair tiny extraction gaps, not as attractive shortcuts.
- The road graph builder now uses stricter default OpenCV thresholds and writes optional preview images to data/road_graph_preview. If the current road_graph.json contains field lines / roofs / non-road shapes, rebuild it with build_road_graph_from_tiles.bat.

v0.9.4 notes
-----------
- QR fix: run_live_map.bat now installs the small qrcode package when missing, so /api/qr.svg can render again when running from source.
- Road graph routing now supports weighted road classes. Rebuild data\road_graph.json with build_road_graph_from_tiles.bat to encode priority:
  white roads = preferred, orange roads = medium, orange dashed/trails = last resort.
- Old road_graph.json files without road_class fields still load, but they cannot benefit from road-type priority until rebuilt from tile_cache.

Version 0.9.5 notes:
- Real heading-up map rotation now uses the actual movement vector from changing map coordinates, not only server yaw/heading.
- Tile, route, and marker layers are rotated together through one shared mapWorld wrapper.
- Route recalculation is less twitchy and suspicious huge detour reroutes are ignored when the car is still close to the current route.


=== v0.9.7 notes ===
This build uses the user-provided rebuilt data\road_graph.json and adds runtime graph repair.
The OpenCV graph may be clean but fragmented; the server now closes small gaps between nearby road components with expensive synthetic links instead of failing with "disconnected components".
Heading-up rotation from v0.9.5 is preserved.
The road graph builder is now magenta-aware: pink/magenta asphalt corridors on the source map are treated as preferred asphalt/white roads during future rebuilds.
Check http://127.0.0.1:8766/api/graph/status after launch; meta should include stitch_edges and component_bridge_edges.


v0.9.8 notes:
- Heading-up rotation from v0.9.5 is preserved.
- Routing now treats short synthetic graph links as CV gap repairs instead of punishing them like off-road shortcuts.
- Long synthetic links remain expensive.
- If routes still make large hooks, rebuild the graph with build_road_graph_from_tiles.bat. This version uses stride=10 and diagonal neighbor links to keep real asphalt roads connected.



---

0.9.8 navfix1 notes

- Navigator touch handling changed: tapping/dragging/pinching the map in navigation mode no longer permanently disables Follow / heading-up rotation. A drag creates only a short temporary look-around pause, then the map resumes following the car.
- Rerouting is now sticky: after a missed turn the app keeps the original route for a while and asks the driver to return to route instead of instantly accepting a much longer detour.
- Long suspicious reroutes are rejected more aggressively while the car is still close enough to the original route.


---
Mobile UI patch v0.9.10
- On phone/tablet, the status, search and settings panels are hidden by default.
- Bottom dock icons open Info, Search, Settings and Media.
- Navigation mode keeps the route bar compact and adds a media toggle on the right.
- Media controls include a collapse button.


---
Patch v0.9.12:
- Rolled map/tile renderer back to the stable v0.9.10 positioning path.
- Kept auto-arrival: navigation ends after arrival radius/hold.
- Added static full-map fallback under tiles, so a blank remote tile/cache situation still shows the map.
- Kept final manual road graph and mobile dock UI.


v0.9.14: English custom point menu, mobile Info panel shows Nearest POI in meters, and Navigator mode has an Info button for nearest POI.

v0.9.15: Mobile Nearest POI opens as a compact lower-left overlay in map and navigator modes.
