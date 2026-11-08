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

   `locales/` and `examples/` are bundled inside both packages; firmware
   files are not bundled and stay separate. The intermediate `build/`
   folder is disposable and both `build/` and `dist/` are ignored by git.

## Verifying the packages

- CLI self-check: run `dist/HJSWorkbench-CLI.exe`, open menu 6 (Offline
  tools) then 1 (full offline self-test report); it must report
  `Acceptance: 9/9 passed  [OK]`.
- GUI headless check: `dist/HJSWorkbench-GUI/HJSWorkbench-GUI.exe --check`
  runs the packaged self-check (bundled examples, nine decoders, a
  measurement, catalogs) and exits with code 0 for PASS and 1 for FAIL.
  The GUI is a windowed executable, so the summary is always written to a
  UTF-8 report file: `--check-output PATH` chooses the path, otherwise it
  is written to `hjs_workbench_gui_check.txt` in the system temporary
  directory. A console build or a normal `python -m gui --check` run also
  prints the summary to stdout, followed by the report file path.
- GUI headless start: set `QT_QPA_PLATFORM=offscreen`, launch the
  executable, and confirm it stays alive; its version reads 0.3.0.

## Other platforms

PyInstaller cannot cross-compile. On macOS or Linux, run the same two
commands with that platform's Python environment; the spec files use
`os.path` throughout and need no changes.
