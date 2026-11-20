# GUI Usability Rework - Independent Acceptance Record

Task: 123, Round 2 rework of the GUI usability changes.
Acceptance executed independently on 2026-11-20. Every check below was run
against the working tree, not taken from the construction report.

## 1. Scope

The Round 2 rework is limited to three files:

- gui/main_window.py: hiding the side panel now hides the whole container so
  the waveform expands.
- packaging/installer.iss: the custom uninstaller forms were removed so
  uninstall uses the standard Windows dialogs.
- docs/PATTERN_PLAYBACK_ACCEPTANCE_RECORD.md: a name was removed from line 4.

No firmware, HAL, backend, capture, or decoder logic was changed. No new
dependency and no new translation entry were introduced.

## 2. Automated gates

- ruff check .: All checks passed.
- Unit tests: Ran 81 tests, OK.
- gui --check (offscreen): Self-check PASS.

## 3. Side panel measurement

An independent offscreen script resized the window to 1280x760 and ran two
full hide/show cycles. All 16 checks passed.

- Waveform width: 550 while visible, 1280 while hidden, 550 after restore.
- Side container width: 726 while visible, 0 while hidden.
- The persisted value side_panel_hidden matched every state.
- The toolbar toggle stayed visible while the header button hid together
  with the container, so the panel can always be restored.

## 4. Installer compile

- ISCC 6.7.3: Successful compile, exit 0.
- 26 warnings are emitted, all from the installed ChineseTraditional.isl
  message-name version mismatch. The same set appears before and after the
  change, so the script itself adds no error or warning.
- The [Code] section contains no uninstaller event function and no custom
  form; only the finished-page brand block remains.

## 5. Silent install and uninstall cycle

A per-user very-silent install into a test directory followed by a
very-silent uninstall:

- Install exit 0. The GUI executable, the uninstaller, and the HKCU
  uninstall key were present.
- Uninstall exit 0. The directory was removed, the HKCU key was removed, and
  no related process remained.

## 6. Additional correction

During review, one [Files] comment still referenced the removed branded
uninstaller forms. The comment was corrected to state that the icon is
installed in the application directory. The installer was recompiled with
the same result, including the same byte count and warning set.

## 7. Final state

The working tree holds 18 modified files and no untracked files. A
repository-wide scan of the tracked files found no vendor names, no
AI-generated or AI-assisted markers, and no emoji. The four .po files remain
at 342 entries each, with no new msgid. The pre-existing UTF-8 byte order
mark at the start of installer.iss was preserved.
