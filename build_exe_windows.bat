@echo off
setlocal
cd /d "%~dp0"

echo.
echo ============================================================
echo  FH6 Live Map v0.9.15 compact nearest POI builder
echo ============================================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python launcher "py" was not found.
    echo Install Python 3.11+ on this builder PC, then run this file again.
    echo.
    pause
    exit /b 1
)

echo Python:
py --version
echo.

echo Installing/updating PyInstaller runtime dependencies...
py -m pip install --upgrade pip pyinstaller qrcode pillow numpy opencv-python
if errorlevel 1 (
    echo.
    echo ERROR: Failed to install PyInstaller/qrcode.
    pause
    exit /b 1
)

echo.
echo Building one-file console EXE...
py -m PyInstaller --noconfirm --clean FH6LiveMap.spec
if errorlevel 1 (
    echo.
    echo ERROR: Build failed.
    pause
    exit /b 1
)

echo.
echo Preparing portable data folder next to the EXE...
if not exist "dist\data" mkdir "dist\data"
copy /Y "data\markers.json" "dist\data\" >nul
copy /Y "data\map_meta.json" "dist\data\" >nul
copy /Y "data\calibration_points.csv" "dist\data\" >nul
if exist "data\road_graph.json" copy /Y "data\road_graph.json" "dist\data\" >nul
if exist "tile_cache" (
    echo Copying tile_cache to dist. This can take a while...
    xcopy /E /I /Y "tile_cache" "dist\tile_cache" >nul
)
copy /Y "run_exe_here.bat" "dist\" >nul

echo.
echo ============================================================
echo  Build complete.
echo ============================================================
echo.
echo Portable folder:
echo   %CD%\dist
echo.
echo EXE:
echo   %CD%\dist\FH6LiveMap.exe
echo.
echo Road graph:
echo   %CD%\dist\data\road_graph.json
echo.
echo Copy the whole dist folder to the gaming PC if you want offline data.
echo On first launch, Windows Firewall may ask for network access.
echo Allow it for Private networks.
echo.
pause
