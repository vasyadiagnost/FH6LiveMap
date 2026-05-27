@echo off
setlocal
cd /d "%~dp0"

echo.
echo ============================================================
echo  FH6 Live Map - build CONNECTED road graph from cached tiles
echo ============================================================
echo.

echo Installing CV dependencies for the weighted graph builder...
py -m pip install --upgrade pillow numpy opencv-python qrcode
if errorlevel 1 (
    echo.
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo Building data\road_graph.json from tile_cache...
echo Road classes will be encoded. v0.9.8 uses a denser connected graph to avoid silly hooks:
echo   1. white / magenta asphalt corridors = preferred
echo   2. orange roads                    = medium
echo   3. orange dashed/trails            = allowed only to avoid silly detours
echo Preview masks will be saved to data\road_graph_preview.

echo.
py tools\extract_roads_from_tiles.py ^
  --tile-cache tile_cache ^
  --layer 760 ^
  --zoom 18 ^
  --output data\road_graph.json ^
  --stride 10 ^
  --connect-diagonal ^
  --min-road-ratio 0.13 ^
  --white-min-ratio 0.10 ^
  --orange-solid-ratio 0.24 ^
  --light-value-min 184 ^
  --light-sat-max 56 ^
  --light-minc-min 136 ^
  --orange-r-min 185 ^
  --orange-g-min 75 ^
  --orange-g-max 175 ^
  --orange-b-max 115 ^
  --orange-rb-delta-min 85 ^
  --orange-rg-delta-min 8 ^
  --magenta-r-min 150 ^
  --magenta-b-min 105 ^
  --magenta-g-max 120 ^
  --magenta-rg-delta-min 45 ^
  --magenta-bg-delta-min 35 ^
  --min-component-area 35 ^
  --component-min-span 18 ^
  --component-min-elongation 1.45 ^
  --component-large-area 1200 ^
  --component-max-fill-ratio 0.52 ^
  --white-component-min-elongation 1.85 ^
  --white-component-large-area 5200 ^
  --white-component-max-fill-ratio 0.44 ^
  --white-cost-factor 1.00 ^
  --orange-cost-factor 1.12 ^
  --orange-dashed-cost-factor 2.35 ^
  --unknown-cost-factor 8.00 ^
  --preview-dir data\road_graph_preview
if errorlevel 1 (
    echo.
    echo ERROR: Road graph build failed. Check that tile_cache\481\760\18 contains PNG tiles.
    pause
    exit /b 1
)

echo.
echo Done. Restart FH6 Live Map and use Search or POI - Route.
echo.
pause
