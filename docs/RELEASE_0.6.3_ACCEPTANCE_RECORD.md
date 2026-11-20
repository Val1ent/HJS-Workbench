# Release 0.6.3 - Independent Acceptance Record

Acceptance executed independently on 2026-11-20. The release was built and
published through the repository CI, and every check below was run against
the live release rather than the construction report.

## 1. Versions and identifiers

- Tag: v0.6.3, annotated and pushed to main.
- Commits: e0bbad4 (GUI usability changes) and c3d953c (CLI version
  alignment).
- GitHub Release id: 452773028, neither a draft nor a pre-release.
- CI run: 44751148561. All six jobs completed with success: ensure release,
  matrix resolution, and the Linux, Windows, macOS arm64, and macOS x86_64
  builds.

## 2. Pre-release gates

- ruff check .: All checks passed.
- Unit tests: 81 tests, OK.
- GUI self-check (offscreen): PASS.

## 3. Published assets

All ten assets are in the uploaded state.

| Asset | Size (bytes) |
| --- | --- |
| HJS-Workbench-Setup-0.6.3-windows-x86_64.exe | 46,857,484 |
| HJSWorkbench-CLI-0.6.3-windows-x86_64.exe | 8,716,445 |
| HJSWorkbench-CLI-linux-x86_64 | 20,689,728 |
| HJSWorkbench-CLI-macos-arm64 | 7,755,568 |
| HJSWorkbench-CLI-macos-x86_64 | 8,336,192 |
| HJSWorkbench-GUI-0.6.3-linux-x86_64.tar.gz | 103,328,936 |
| HJSWorkbench-GUI-0.6.3-macos-arm64.tar.gz | 47,518,933 |
| HJSWorkbench-GUI-0.6.3-macos-x86_64.tar.gz | 52,987,546 |
| HJSWorkbench-GUI-0.6.3-windows-x86_64.zip | 67,558,394 |
| install.sh | 12,141 |

The asset names follow the same convention as the previous release, with the
Windows CLI and every GUI asset carrying the 0.6.3 version and the Linux and
macOS CLI binaries keeping the unversioned names that scripts/install.sh
expects. The release body was updated with the change highlights and a
per-platform download list.

## 4. Version alignment

The CLI and GUI were both published at 0.6.3 so that every asset name matches
the version inside its binary. The shared release notes carry a 0.6.3 entry,
and the prior 0.6.2 entry is retained for the version comparison logic.

## 5. Retained history and final state

The previous release v0.6.2 remains published with its ten assets and was not
modified or deleted. The working tree is clean after the release, and the
local and remote main branches point at the same commit.
