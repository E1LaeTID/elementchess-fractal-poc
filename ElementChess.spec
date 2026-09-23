# -*- mode: python ; coding: utf-8 -*-

import sys

analysis = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="ElementChess",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

bundle = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ElementChess",
)

if sys.platform == "darwin":
    application = BUNDLE(
        bundle,
        name="ElementChess.app",
        icon=None,
        bundle_identifier="fr.pascalquesdyel.elementchess",
        info_plist={
            "CFBundleName": "ElementChess",
            "CFBundleDisplayName": "ElementChess",
            "CFBundleShortVersionString": "0.26.2",
            "NSHighResolutionCapable": True,
        },
    )
