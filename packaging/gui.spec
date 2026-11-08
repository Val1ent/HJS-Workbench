# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: HJS-Workbench GUI as a windowed onedir bundle.

Build from the repository root with:

    pyinstaller packaging/gui.spec --noconfirm

Artifacts land under ``dist/HJSWorkbench-GUI/`` (``HJSWorkbench-GUI.exe``
plus the runtime folder). The ``locales/`` and ``examples/`` folders are
bundled at the bundle root so ``core.paths.resource_path`` finds them in
the frozen application. The decoder modules are listed as hidden imports
so all nineteen are registered in the frozen package.

The same spec builds on macOS and Linux; only the executable extension
differs. PyInstaller cannot cross-compile, so each platform builds its own
package from this spec.
"""
import os

REPO_ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

datas = [
    (os.path.join(REPO_ROOT, "locales"), "locales"),
    (os.path.join(REPO_ROOT, "examples"), "examples"),
    (os.path.join(REPO_ROOT, "assets"), "assets"),
]

hiddenimports = [
    "core.decoders.nec",
    "core.decoders.servo",
    "core.decoders.i2c",
    "core.decoders.spi",
    "core.decoders.stepper",
    "core.decoders.encoder",
    "core.decoders.rc5",
    "core.decoders.ultrasonic",
    "core.decoders.fan",
    "core.decoders.dht11",
    "core.decoders.onewire",
    "core.decoders.swd",
    "core.decoders.modbus",
    "core.decoders.wiegand",
    "core.decoders.hd44780",
    "core.decoders.sirc",
    "core.decoders.ds1302",
    "core.decoders.manchester",
    "core.decoders.nmea",
]

a = Analysis(
    [os.path.join(REPO_ROOT, "gui", "__main__.py")],
    pathex=[REPO_ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="HJSWorkbench-GUI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=os.path.join(REPO_ROOT, "assets", "app.ico"),
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="HJSWorkbench-GUI",
)
