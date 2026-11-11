# Installing HJS-Workbench

Two installation paths exist, one for each edition:

- **Windows graphical installer** for the GUI: a single Setup executable
  that asks for the installer language first, then the install location.
- **Cross-platform terminal script** for the CLI: a one-line bash command
  for Ubuntu, WSL, and macOS that asks for language first, then the
  install directory.

Both flows ask for the language before any path or install prompt. The
installer language is the installer's own language; the installed
application still keeps its separate in-app language setting (chosen on
the application's first run, and changeable later from Settings).

## Windows Setup (GUI)

1. Download `HJS-Workbench-Setup-0.6.2.exe` from the release page and
   run it.
2. The first prompt is the installer language: English, 简体中文,
   繁體中文, Français, or Deutsch.
3. The welcome and license pages follow, then the install-directory
   page (default: `C:\Program Files\HJS-Workbench`; no custom location is
   forced).
4. The installer copies the complete GUI application - executable,
   bundled assets, examples, and locales - and creates Start Menu
   shortcuts. A desktop shortcut is offered as an optional task.
5. Uninstall through the registered entry in Windows "Apps" or the
   `Uninstall HJS-Workbench` Start Menu shortcut.

The Setup executable is built from `packaging/installer.iss` with Inno
Setup 6; see [Build prerequisites](#build-prerequisites).

## Terminal script (CLI) - Ubuntu, WSL, macOS

Run the one-line command:

```bash
curl -fsSL https://github.com/Val1ent/HJS-Workbench/releases/download/v0.6.2/install.sh | bash
```

The script runs in this fixed order:

1. **Language first**: a short numbered list of the five supported
   languages is shown and the choice is read before any other prompt.
2. **Install directory**: after the language choice, the script explains
   the install and asks for the directory, defaulting to `~/.local/bin`
   (a user-writable location; the default needs no root). A system-wide
   directory may be chosen and is the only case that may need elevated
   privileges.
3. **Download and install**: the CLI binary matching the running
   platform (Linux x86_64 / arm64, macOS x86_64 / arm64) is downloaded
   from the release, placed in the chosen directory, and made
   executable.
4. **PATH note**: if the chosen directory is not on `PATH`, the script
   prints the exact command to add it.

Failures are reported specifically: unsupported platform or
architecture, a failed download, or a directory that cannot be written.

### Honest platform scope

The Windows CLI executable is available now. The Linux and macOS CLI
binaries are built with PyInstaller on those platforms and become
downloadable once those platform builds are published to a release.
Until then, running the script on Linux or macOS reports that the
binary for that platform is not published yet - the script never
advertises binaries that have not been built. The script itself works
on all three platforms.

## Build prerequisites

- **Windows Setup executable**: Inno Setup 6 (free installer compiler,
  https://jrsoftware.org/isinfo.php). With `dist/HJSWorkbench-GUI` built
  by PyInstaller, compile from the repository root:

  ```
  ISCC.exe packaging\installer.iss
  ```

- **Per-platform CLI binaries**: PyInstaller builds on each platform
  (`pyinstaller packaging/cli.spec --noconfirm`); PyInstaller cannot
  cross-compile. Each platform binary is published to the release before
  its download path in the install script becomes end-to-end.

- **Application packages**: see `packaging/BUILD.md` for the PyInstaller
  build steps.
