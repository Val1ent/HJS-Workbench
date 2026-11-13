#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compile the Windows installer with the version taken from gui/version.py.

The installer script keeps a fallback version string for a direct ISCC run,
but the authoritative version lives in gui/version.py. This script reads
that file and passes the version to the Inno Setup compiler as
/DMyAppVersion=<version>, so a released Setup executable always matches the
application version without editing packaging/installer.iss by hand.

Only the Python standard library is used.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = REPO_ROOT / "gui" / "version.py"
INSTALLER_SCRIPT = REPO_ROOT / "packaging" / "installer.iss"
GUI_ONEDIR = REPO_ROOT / "dist" / "HJSWorkbench-GUI"
GUI_EXE_NAME = "HJSWorkbench-GUI.exe"
SETUP_NAME_TEMPLATE = "HJS-Workbench-Setup-{version}.exe"
INNO_SETUP_URL = "https://jrsoftware.org/isinfo.php"

_VERSION_ASSIGNMENT = re.compile(r'__version__\s*=\s*["\']([^"\']+)["\']')
_VERSION_SHAPE = re.compile(r"^\d+\.\d+\.\d+$")

_COMMON_ISCC_PATHS = (
    Path("C:/Program Files (x86)/Inno Setup 6/ISCC.exe"),
    Path("C:/Program Files/Inno Setup 6/ISCC.exe"),
)


class BuildError(Exception):
    """A build problem reported to the user without a raw traceback."""


def read_version(version_file=VERSION_FILE):
    """Return the version declared in version_file.

    The file is read as text rather than imported, so building the
    installer never executes application code.
    """
    try:
        text = version_file.read_text(encoding="utf-8")
    except OSError as exc:
        raise BuildError(
            "Cannot read the version file {}: {}".format(
                version_file, exc.strerror or exc
            )
        ) from None

    match = _VERSION_ASSIGNMENT.search(text)
    if match is None:
        raise BuildError(
            "No __version__ assignment found in {}. Expected a line such "
            'as: __version__ = "1.2.3"'.format(version_file)
        )

    version = match.group(1)
    if not _VERSION_SHAPE.match(version):
        raise BuildError(
            "Version {!r} in {} is not in MAJOR.MINOR.PATCH form.".format(
                version, version_file
            )
        )
    return version


def find_iscc():
    """Return the Inno Setup compiler executable.

    Lookup order: the ISCC environment variable, the PATH, then the default
    Inno Setup 6 installation directories.
    """
    env_value = os.environ.get("ISCC")
    if env_value:
        candidate = Path(env_value).expanduser()
        if candidate.is_file():
            return candidate
        print(
            "warning: the ISCC environment variable points to {}, which is "
            "not a file; continuing with the remaining lookup steps.".format(
                candidate
            ),
            file=sys.stderr,
        )

    on_path = shutil.which("ISCC")
    if on_path:
        return Path(on_path)

    for candidate in _COMMON_ISCC_PATHS:
        if candidate.is_file():
            return candidate

    raise BuildError(
        "Inno Setup 6 was not found. Install it from {} and run this script "
        "again, or set the ISCC environment variable to the full path of "
        "ISCC.exe.".format(INNO_SETUP_URL)
    )


def check_gui_bundle(onedir=GUI_ONEDIR):
    """Confirm the GUI onedir bundle the installer packages exists."""
    if not onedir.is_dir():
        raise BuildError(
            "The GUI onedir bundle {} is missing. Build it first:\n"
            "  pyinstaller packaging/gui.spec --noconfirm".format(onedir)
        )

    executable = onedir / GUI_EXE_NAME
    if not executable.is_file():
        raise BuildError(
            "{} was not found in {}. Build the bundle first:\n"
            "  pyinstaller packaging/gui.spec --noconfirm".format(
                GUI_EXE_NAME, onedir
            )
        )
    return executable


def compile_installer(iscc, version):
    """Run the Inno Setup compiler and return the produced Setup file."""
    setup_name = SETUP_NAME_TEMPLATE.format(version=version)
    setup_file = REPO_ROOT / "dist" / setup_name
    # The compiler runs with REPO_ROOT as its working directory, so the
    # installer script is passed relative to it.
    script_arg = INSTALLER_SCRIPT.relative_to(REPO_ROOT).as_posix()
    command = [
        str(iscc),
        "/DMyAppVersion={}".format(version),
        script_arg,
    ]

    print("Command: {}".format(" ".join(command)))
    try:
        completed = subprocess.run(command, cwd=str(REPO_ROOT))
    except OSError as exc:
        raise BuildError(
            "Could not start the Inno Setup compiler {}: {}".format(
                iscc, exc.strerror or exc
            )
        ) from None

    if completed.returncode != 0:
        raise BuildError(
            "The Inno Setup compiler exited with code {}; the installer was "
            "not built.".format(completed.returncode)
        )

    if not setup_file.is_file():
        raise BuildError(
            "The compiler reported success but {} is missing.".format(
                setup_file
            )
        )

    size = setup_file.stat().st_size
    if size <= 0:
        raise BuildError(
            "The Setup executable {} is empty.".format(setup_file)
        )

    print("Setup executable: {} ({} bytes)".format(setup_file.resolve(), size))
    return setup_file


def build():
    """Read the version, locate the compiler, and build the installer."""
    version = read_version()
    print("Repository root: {}".format(REPO_ROOT))
    print("Version from {}: {}".format(VERSION_FILE, version))

    if os.name != "nt":
        raise BuildError(
            "The Inno Setup compiler only runs on Windows; build the "
            "installer on Windows."
        )

    iscc = find_iscc()
    print("Inno Setup compiler: {}".format(iscc))

    check_gui_bundle()
    print("GUI bundle: {}".format(GUI_ONEDIR))

    return compile_installer(iscc, version)


def main(argv=None):
    """Command-line entry point; returns the process exit code."""
    parser = argparse.ArgumentParser(
        description=(
            "Compile the Windows installer with the version read from "
            "gui/version.py."
        )
    )
    parser.add_argument(
        "--print-version",
        action="store_true",
        help=(
            "Print the version parsed from gui/version.py and exit without "
            "looking for the compiler or building anything."
        ),
    )
    args = parser.parse_args(argv)

    try:
        if args.print_version:
            print(read_version())
            return 0
        build()
    except BuildError as exc:
        print("error: {}".format(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
