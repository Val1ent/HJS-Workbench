# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: HJS-Workbench CLI as a console onefile executable.

Build from the repository root with:

    pyinstaller packaging/cli.spec --noconfirm

The artifact is ``dist/HJSWorkbench-CLI.exe`` (no ``.exe`` suffix on other
platforms). The ``locales/`` folder is bundled at the bundle root so
``core.paths.resource_path`` finds it in the frozen application; the CLI
uses translations, and the examples are optional for it. The decoder
modules are listed as hidden imports so all nineteen are registered in
the frozen package.

The same spec builds on macOS and Linux; only the executable extension
differs. PyInstaller cannot cross-compile, so each platform builds its own
package from this spec.
"""
import os

REPO_ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

datas = [
    (os.path.join(REPO_ROOT, "locales"), "locales"),
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
    [os.path.join(REPO_ROOT, "cli", "__main__.py")],
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
    a.binaries,
    a.datas,
    [],
    name="HJSWorkbench-CLI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    icon=os.path.join(REPO_ROOT, "assets", "app.ico"),
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
