# Stage 16F Acceptance Record: GUI/CLI Selectors and Multilingual Support

Scope: the host GUI and CLI gain sample-rate and capture-mode selectors
that are always driven by the current backend capabilities, a shared
persistent session module used by both front ends, and a restore-defaults
action. The new user-facing strings are added to every catalog and the
package versions are released as 0.6.2. Acceptance is performed by an
independent reviewer running the real entry points; the builder's own
report is not a substitute. No firmware or HAL transport file is in
scope, and no hardware is required for this stage.

## 0. Prerequisites and method

- Repository: C:\Users\val1ent\Documents\GitHub\PocketDebugKit, working
  tree uncommitted (HEAD stays at 5bf3a19). No commit or push performed.
- Python 3.12.10 interpreter used for every run. GUI tests run with
  QT_QPA_PLATFORM=offscreen. Each subprocess gets an isolated APPDATA
  directory and PYTHONPATH set to the repository root.
- The independent checks live outside the repository and are listed by
  name below so the result can be reproduced.

## 1. Change scope verification

| Check | Result | Notes |
|---|---|---|
| Shared session module | pass | core/session.py added; standard library only, no pyserial import, no device open. |
| GUI selectors | pass | gui/main_window.py adds rate and mode combo boxes and a restore button; gui/worker.py carries the selected rate. |
| CLI selectors | pass | cli/session_flow.py added; cli/app.py settings menu gains the new entries; capture and live flows follow the session. |
| Front-end routing | pass | realtime routes to acquire_serial and burst routes to acquire_burst with the selected rate; burst disables the point count and continuous controls. |
| Catalogs updated | pass | four .po catalogs hold 315 entries with identical msgid sets; .mo files rebuilt with scripts/compile_mo.py. |
| Versions and notes | pass | cli/version.py and gui/version.py read 0.6.2; core/release_notes.py carries a 0.6.2 entry. |
| Firmware and HAL untouched | pass | no firmware or HAL transport file modified. |
| Clean traces | pass | every changed file is pure ASCII with no generator names, no AI markers and no emoji. |

## 2. Independent acceptance results

| Check script | Coverage | Result |
|---|---|---|
| s16f_gui_offscreen.py | 20 GUI behaviors: capability-driven item counts and data, persistence and restore across new windows, intercepted acquire routing for realtime and burst, continuous-worker rate, burst disable states, stale-config fallback, and retranslation | 20/20 pass |
| s16f_catalog.py | 43 catalog checks: entry counts, identical msgid sets, placeholder parity, translations in four languages, French cedilla, no replacement characters | 43/43 pass |
| s16f_cli.py | 15 CLI checks: real entry-point menu navigation, rate and mode saves, invalid-entry re-prompt, defaults restore, English/Chinese/French UTF-8 rendering, and no Qt dependency | 15/15 pass |
| s16f_code_scan.py | 273 compliance checks across 70 Python files: generator names, AI markers, emoji, CJK outside the language picker, and pure ASCII outside the documented whitelist | 273/273 pass |
| s16f_smoke.py | 15 smoke checks: versions, release notes, .mo existence and freshness, and the core public API | 15/15 pass |
| s16f_mo_freshness.py | 4 byte-level checks that each committed .mo is the exact build of its current .po | 4/4 pass |
| s16e_realtime_regression.py | realtime non-blocking acquire returns 2000 points byte-identical and closes the connection | pass |
| compileall core/cli/gui | byte-compilation of every module | exit 0 |

## 3. Functional non-ASCII exceptions

The codebase is English-only and pure ASCII except for four pre-existing
files whose non-ASCII characters are functional. None of them was changed
by this stage, and none contains a generator name, AI marker or emoji.

| File | Characters | Reason |
|---|---|---|
| core/i18n.py | U+00E7 and CJK native names | language picker must show each language in its own name. |
| gui/app.py | CJK native names | language dialog prompt. |
| cli/console_setup.py | U+00E7 | docstring reference explaining why the console is switched to UTF-8. |
| cli/offline_flow.py | U+2588 block element | terminal histogram and comparison-band drawing. |

The block element used elsewhere in cli/live_analyzer.py is written as
the \u2588 escape, keeping that file pure ASCII with identical runtime
output.

## 4. Catalog backlog found during review (not introduced by this stage)

An AST-based coverage check (s16f_msgid_ast.py) confirms the Stage 16F
msgids are all present, but it also finds six Stage 16E msgids that were
never added to the catalogs, plus one stale entry:

- six code msgids are absent from every catalog, including the burst
  upload timeout messages, the serial-port read error, the malformed
  burst header message, and the two unsupported-command messages.
- one catalog entry is now an orphan: the older USB-FS wording of the
  capture timeout message. The code uses an updated High-Speed wording,
  so the new wording is also untranslated and the old wording is no
  longer referenced.

These predate Stage 16F and do not affect its behavior: translation
fallback is enabled, so an unlisted msgid returns the English source and
the program never crashes. The only effect is that those error messages
stay in English under the other languages. The builder correctly limited
its change to the Stage 16F strings rather than editing the backlog.
Backfilling the six missing translations and removing the orphan is
recommended as a separate, scoped cleanup and is not a blocker for this
stage.

## 5. Acceptance criteria summary

| Criterion | Result |
|---|---|
| Selectors driven by backend capabilities in GUI and CLI | pass |
| Persistent session shared by both front ends, with validation and fallback | pass |
| Correct realtime/burst routing and burst control states | pass |
| Restore defaults available in GUI and CLI | pass |
| All new strings present and translated in four catalogs | pass |
| Compiled .mo files match the current .po sources | pass |
| Versions at 0.6.2 with release notes | pass |
| Realtime path unchanged and byte-identical | pass |
| Clean traces (no generator names, AI markers or emoji) | pass |
| Firmware and HAL transport untouched | pass |

Overall: PASS. The GUI/CLI selectors and multilingual support are
independently verified through the real entry points, the Stage 16E
real-time behavior is preserved byte-identically, and the codebase
compliance rules hold. The catalog backlog described in section 4 is
recorded for a separate cleanup. The working tree remains uncommitted at
HEAD 5bf3a19 pending review approval.

Reviewer: independent reviewer  Date: 2026-11-12
