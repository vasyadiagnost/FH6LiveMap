# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['fh6_live_map_server.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('data/markers.json', 'data'),
        ('data/map_meta.json', 'data'),
        ('data/calibration_points.csv', 'data'),
        ('data/road_graph.json', 'data'),
        ('index_work.html', '.'),
        ('data/meme_layer/config.json', 'data/meme_layer'),
        ('data/meme_layer/README_Meme_Layer.txt', 'data/meme_layer'),
        ('data/meme_layer/samples/collision/PUT_YOUR_SAMPLES_HERE.txt', 'data/meme_layer/samples/collision'),
        ('data/meme_layer/samples/mega_fail_crash/PUT_YOUR_SAMPLES_HERE.txt', 'data/meme_layer/samples/mega_fail_crash'),
        ('data/meme_layer/samples/jump_takeoff/PUT_YOUR_SAMPLES_HERE.txt', 'data/meme_layer/samples/jump_takeoff'),
        ('README.txt', '.'),
    ],
    hiddenimports=['qrcode', 'qrcode.image.svg', 'qrcode.image.styles.moduledrawers.svg'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FH6LiveMap',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
