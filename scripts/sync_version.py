#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Keep the version string consistent across the repository.

The GUI version file (gui/version.py) is the single source of truth. Every
other place that must carry the same release version is a managed target:
the CLI version file, the installer fallback definition, the shell install
script, the install documentation link, and the title of every README.

Usage:
  python scripts/sync_version.py            Write the authoritative version
                                            into every managed target.
  python scripts/sync_version.py --check    Report targets that differ and
                                            exit non-zero; change nothing.
  python scripts/sync_version.py --set X.Y.Z
                                            Set the authoritative version and
                                            then synchronize every target.
  python scripts/sync_version.py --check --expect X.Y.Z
                                            Fail unless the authoritative
                                            version equals the given value.
  python scripts/sync_version.py --print    Print the authoritative version.

Only the Python standard library is used. Files are read and written as
UTF-8 with line endings left untouched, so a CRLF installer script and LF
Python files keep their original bytes apart from the version digits.
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUTHORITY_FILE = "gui/version.py"

_VERSION_SHAPE = re.compile(r"^\d+\.\d+\.\d+$")
_AUTHORITY_RE = re.compile(r'__version__\s*=\s*["\']([^"\']+)["\']')

# Each managed pattern captures the current version in group 2 and ends in a
# lookahead instead of consuming the line ending, so CRLF and LF are kept.
_PY_VERSION_RE = re.compile(
    r'(?m)^(__version__\s*=\s*["\'])([^"\']*)(["\'])(?=\r?$)'
)
_ISS_RE = re.compile(
    r'(?m)^(\s*#define\s+MyAppVersion\s+")([^"]*)(")(?=\r?$)'
)
_SH_RE = re.compile(
    r'(?m)^(VERSION=")([^"]*)(")(?=\r?$)'
)
_INSTALL_MD_RE = re.compile(
    r"(releases/download/v)(\d+\.\d+\.\d+)(/)"
)
_README_RE = re.compile(
    r"(?m)^(#\s+HJS-Workbench\s+v?)(\d+\.\d+\.\d+)(?=\r?$)"
)

_README_FILES = (
    "README.md",
    "README.zh-CN.md",
    "README.zh-TW.md",
    "README.fr.md",
    "README.de.md",
    "README.ar.md",
)


class VersionError(Exception):
    """A version management problem reported without a raw traceback."""


def read_text(path):
    """Read a text file as UTF-8 without translating line endings."""
    with open(path, encoding="utf-8", newline="") as handle:
        return handle.read()


def write_text(path, text):
    """Write UTF-8 text without translating line endings."""
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)


class Target:
    """One managed file and the rule that updates its version string."""

    def __init__(self, label, relpath, pattern, template):
        self.label = label
        self.relpath = relpath
        self.path = ROOT / relpath
        self.pattern = pattern
        self.template = template

    def _read(self):
        try:
            return read_text(self.path)
        except OSError as exc:
            raise VersionError(
                "Cannot read {}: {}".format(self.relpath, exc.strerror or exc)
            ) from None

    def current(self):
        """Return the version currently held by the target, or None."""
        match = self.pattern.search(self._read())
        return match.group(2) if match else None

    def write(self, version):
        """Replace the version string; return 'updated' or 'unchanged'."""
        text = self._read()
        new_text, count = self.pattern.subn(
            self.template.format(version=version), text
        )
        if count != 1:
            raise VersionError(
                "Expected one version match in {} but found {}.".format(
                    self.relpath, count
                )
            )
        if new_text == text:
            return "unchanged"
        try:
            write_text(self.path, new_text)
        except OSError as exc:
            raise VersionError(
                "Cannot write {}: {}".format(self.relpath, exc.strerror or exc)
            ) from None
        return "updated"


def build_targets():
    """Return every managed target in reporting order."""
    targets = [
        Target("GUI version file", "gui/version.py", _PY_VERSION_RE,
               r"\g<1>{version}\g<3>"),
        Target("CLI version file", "cli/version.py", _PY_VERSION_RE,
               r"\g<1>{version}\g<3>"),
        Target("installer fallback", "packaging/installer.iss", _ISS_RE,
               r"\g<1>{version}\g<3>"),
        Target("install script", "scripts/install.sh", _SH_RE,
               r"\g<1>{version}\g<3>"),
        Target("install documentation", "docs/INSTALL.md", _INSTALL_MD_RE,
               r"\g<1>{version}\g<3>"),
    ]
    for name in _README_FILES:
        targets.append(
            Target("README title " + name, name, _README_RE,
                   r"\g<1>{version}")
        )
    return targets


def read_authority():
    """Return the authoritative version from gui/version.py."""
    path = ROOT / AUTHORITY_FILE
    try:
        text = read_text(path)
    except OSError as exc:
        raise VersionError(
            "Cannot read {}: {}".format(AUTHORITY_FILE, exc.strerror or exc)
        ) from None
    match = _AUTHORITY_RE.search(text)
    if match is None:
        raise VersionError(
            "No __version__ assignment found in {}.".format(AUTHORITY_FILE)
        )
    version = match.group(1)
    if not _VERSION_SHAPE.match(version):
        raise VersionError(
            "Authoritative version {!r} is not in MAJOR.MINOR.PATCH form."
            .format(version)
        )
    return version


def set_authority(new_version):
    """Write a new authoritative version into gui/version.py."""
    if not _VERSION_SHAPE.match(new_version):
        raise VersionError(
            "New version {!r} is not in MAJOR.MINOR.PATCH form.".format(
                new_version
            )
        )
    path = ROOT / AUTHORITY_FILE
    try:
        text = read_text(path)
    except OSError as exc:
        raise VersionError(
            "Cannot read {}: {}".format(AUTHORITY_FILE, exc.strerror or exc)
        ) from None
    new_text, count = _PY_VERSION_RE.subn(
        r"\g<1>{}\g<3>".format(new_version), text
    )
    if count != 1:
        raise VersionError(
            "Expected one version match in {} but found {}.".format(
                AUTHORITY_FILE, count
            )
        )
    try:
        write_text(path, new_text)
    except OSError as exc:
        raise VersionError(
            "Cannot write {}: {}".format(AUTHORITY_FILE, exc.strerror or exc)
        ) from None


def run_check(expect=None):
    """Verify every target without changing files; return an exit code."""
    version = read_authority()
    problems = []
    print("Authoritative version: {}".format(version))
    if expect is not None and expect != version:
        problems.append(
            "expected {} but the authoritative version is {}".format(
                expect, version
            )
        )
    for target in build_targets():
        current = target.current()
        if current is None:
            problems.append(
                "{}: no version string found".format(target.relpath)
            )
            print("  [MISSING] {}".format(target.label))
        elif current != version:
            problems.append(
                "{}: has {} but should be {}".format(
                    target.relpath, current, version
                )
            )
            print("  [MISMATCH] {}: {}".format(target.label, current))
        else:
            print("  [OK] {}".format(target.label))
    if problems:
        print("Version check failed:")
        for problem in problems:
            print("  - {}".format(problem))
        return 1
    print("All managed targets match the authoritative version.")
    return 0


def run_sync():
    """Write the authoritative version into every managed target."""
    version = read_authority()
    print("Synchronizing version {}:".format(version))
    for target in build_targets():
        print("  [{}] {}".format(target.write(version), target.label))
    return 0


def run_set(new_version):
    """Set the authoritative version and then synchronize."""
    set_authority(new_version)
    print("Authoritative version set to {}.".format(new_version))
    return run_sync()


def main(argv=None):
    """Command-line entry point; return the process exit code."""
    parser = argparse.ArgumentParser(
        description="Synchronize the version across managed repository files."
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Only verify consistency; exit non-zero on any mismatch.",
    )
    parser.add_argument(
        "--set", metavar="VERSION",
        help="Set the authoritative version to VERSION and synchronize.",
    )
    parser.add_argument(
        "--expect", metavar="VERSION",
        help="Fail unless the authoritative version equals VERSION.",
    )
    parser.add_argument(
        "--print", action="store_true",
        help="Print the authoritative version and exit.",
    )
    args = parser.parse_args(argv)

    try:
        if args.set is not None and args.check:
            raise VersionError("--set and --check cannot be combined.")
        if args.print:
            print(read_authority())
            return 0
        if args.set is not None:
            return run_set(args.set)
        if args.check:
            return run_check(expect=args.expect)
        if args.expect is not None:
            version = read_authority()
            if version != args.expect:
                print("expected {} but found {}".format(args.expect, version))
                return 1
            print("Authoritative version is {}.".format(version))
            return 0
        return run_sync()
    except VersionError as exc:
        print("error: {}".format(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
