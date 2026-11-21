# Release 0.6.4 - Independent Acceptance Record

Acceptance executed independently on 2026-11-21. The release was built and
published through the repository CI, and every check below was run against
the live release rather than the construction report.

## 1. Versions and identifiers

- Tag: v0.6.4, annotated and pushed to main.
- Commits: 30643ae (GUI pattern playback), f84678f (Manchester head-glitch
  robustness), e10e932 (capture window of one DMA block), and d51fe27
  (release notes, acceptance record, and version alignment).
- GitHub Release id: 453646340, neither a draft nor a pre-release.
- CI run: 44899790206. All six jobs completed with success: ensure release,
  matrix resolution, and the Linux, Windows, macOS arm64, and macOS x86_64
  builds.

## 2. Pre-release gates

- ruff check .: All checks passed.
- Unit tests: 104 tests, OK.
- Version consistency: sync_version --check --expect 0.6.4, all managed
  targets match.
- GUI self-check (offscreen): PASS.

## 3. Published assets

All ten assets are in the uploaded state.

| Asset | Size (bytes) |
| --- | --- |
| HJS-Workbench-Setup-0.6.4-windows-x86_64.exe | 46,884,651 |
| HJSWorkbench-CLI-0.6.4-windows-x86_64.exe | 8,720,394 |
| HJSWorkbench-CLI-linux-x86_64 | 20,692,496 |
| HJSWorkbench-CLI-macos-arm64 | 7,759,616 |
| HJSWorkbench-CLI-macos-x86_64 | 8,339,248 |
| HJSWorkbench-GUI-0.6.4-linux-x86_64.tar.gz | 103,345,996 |
| HJSWorkbench-GUI-0.6.4-macos-arm64.tar.gz | 47,533,913 |
| HJSWorkbench-GUI-0.6.4-macos-x86_64.tar.gz | 53,003,451 |
| HJSWorkbench-GUI-0.6.4-windows-x86_64.zip | 67,574,563 |
| install.sh | 12,141 |

The asset names follow the established convention: the Windows CLI and every
GUI asset carry the 0.6.4 version, while the Linux and macOS CLI binaries
keep the unversioned names that scripts/install.sh expects. The release body
was updated with the change highlights and a per-platform download list.

## 4. Hardware-in-the-loop confirmation

Using the product default playback path, I2C decoded the complete four-event
transaction (START, ADDR, DATA, STOP with DATA 0x55 ACK) in ten consecutive
runs, Manchester decoded the three bytes 0x55, 0x48, 0x69, and NEC kept its
three events without regression.

## 5. Retained history and final state

The previous releases v0.6.3 and v0.6.2 remain published with their assets
and were not modified or deleted. After the release the working tree is clean
and the local and remote main branches point at the same commit.
