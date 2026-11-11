# Building the HJS-Workbench packages

PyInstaller is a build-time tool only; the application itself has no new
runtime dependency. End users run the packaged executables without
installing Python.

## Windows build (this stage)

Requirements: Python 3.12 with PySide6, pyqtgraph, and pyserial installed
(the same environment the application is developed in).

1. Install the build tool once:

   ```
   pip install pyinstaller
   ```

2. From the repository root, build both packages:

   ```
   pyinstaller packaging/gui.spec --noconfirm
   pyinstaller packaging/cli.spec --noconfirm
   ```

3. Artifacts:

   - `dist/HJSWorkbench-GUI/HJSWorkbench-GUI.exe` - GUI, onedir bundle
     (a folder; fast startup, stable with PySide6), no console window.
   - `dist/HJSWorkbench-CLI.exe` - CLI, single lightweight onefile
     executable with a console.

   The GUI bundle contains `locales/`, `examples/`, and `assets/`; the CLI
   bundle contains `locales/`. The `locales/` folder holds the compiled
   catalogs for all five languages (en source, fr, de, zh_CN, zh_TW).
   The application icon is embedded in both executables. Firmware files
   are not bundled and stay separate. The intermediate `build/` folder is
   disposable and both `build/` and `dist/` are ignored by git.

## Windows installer (Setup executable)

The graphical installer packages the GUI onedir output into a single
Setup `.exe` with Inno Setup 6. Inno Setup is a build prerequisite and is
not installed by the project itself; install it from
https://jrsoftware.org/isinfo.php first.

1. Build the GUI onedir as above.
2. From the repository root, compile the installer script:

   ```
   ISCC.exe packaging\installer.iss
   ```

3. Artifact: `dist/HJS-Workbench-Setup-0.6.2.exe`. The Setup asks for
   its own language first (English, ChineseSimplified,
   ChineseTraditional, French, German via the Inno `[Languages]`
   section), then shows the license and install-directory pages, installs
   the full GUI onedir (assets, examples, locales), creates Start Menu
   shortcuts plus an optional desktop shortcut, and registers an
   uninstaller.

The CLI edition has no Windows installer; it is installed by the
cross-platform terminal script `scripts/install.sh` (see
`docs/INSTALL.md`), which asks for language first, then the install
directory, and downloads the matching per-platform CLI binary from the
release.

## Verifying the packages

- CLI self-check: run `dist/HJSWorkbench-CLI.exe`, open menu 6 (Offline
  tools) then 1 (full offline self-test report); it must report
  `Acceptance: 19/19 passed  [OK]`.
- GUI headless check: `dist/HJSWorkbench-GUI/HJSWorkbench-GUI.exe --check`
  runs the packaged self-check (bundled examples, nineteen decoders, a
  measurement, catalogs) and exits with code 0 for PASS and 1 for FAIL.
  The GUI is a windowed executable, so the summary is always written to a
  UTF-8 report file: `--check-output PATH` chooses the path, otherwise it
  is written to `hjs_workbench_gui_check.txt` in the system temporary
  directory. A console build or a normal `python -m gui --check` run also
  prints the summary to stdout, followed by the report file path.
  The catalog check iterates every language in `SUPPORTED_LANGUAGES`
  (en, fr, de, zh_CN, zh_TW) and verifies each non-English catalog
  translates a known msgid away from the English source.
- GUI headless start: set `QT_QPA_PLATFORM=offscreen`, launch the
  executable, and confirm it stays alive; its version reads 0.6.2.

## Other platforms

PyInstaller cannot cross-compile. On macOS or Linux, run the same two
commands with that platform's Python environment; the spec files use
`os.path` throughout and need no changes. The CLI binaries produced there
are the artifacts the terminal install script downloads.
