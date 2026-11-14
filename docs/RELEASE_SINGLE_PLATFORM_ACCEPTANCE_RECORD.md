# Release Single-Platform Build Acceptance Record

Scope: the release workflow needed a way to rebuild one platform at a time
through workflow_dispatch, so a stale macOS arm64 asset could be refreshed
without rebuilding and re-uploading every platform. The first implementation
filtered the static matrix with a job-level `if` and was rejected by GitHub at
dispatch time. The accepted implementation replaces the static matrix with a
dynamic matrix produced by a setup job. Acceptance is performed by an
independent reviewer using the real dispatch endpoint and the published
release assets; the workflow's own green badge is not a substitute.

## 1. First implementation and its failure

The first change added a `build_target` dispatch input (choices `all` and
`macos-arm64`) and kept the four-entry static matrix, adding a job-level
condition of the form:

    github.event_name != 'workflow_dispatch'
      || inputs.build_target == 'all'
      || inputs.build_target == matrix.target

The workflow file parsed as valid YAML and the push CI passed, but every
dispatch returned HTTP 422 with the message:

    Unrecognized named-value: 'matrix'.
    ... within expression: ... inputs.build_target == matrix.target

Root cause: the `matrix` context is not available to a job-level `if`. The
condition is evaluated before the matrix expansion it tries to read, so GitHub
cannot parse the workflow and refuses to create the run. A local YAML parse
cannot catch this because the restriction is a GitHub Actions context rule,
not a syntax error.

## 2. Accepted change: dynamic matrix

A new `matrix-setup` job runs on ubuntu-latest and emits a JSON array through
its `matrix` output. A shell step selects the entries:

- For a workflow_dispatch with `build_target` equal to `macos-arm64`, the
  array contains only the macOS arm64 entry.
- For every other event, including a tag push and a dispatch with `all`, the
  array contains all four entries in their original order.

The build job now declares `needs: [ensure-release, matrix-setup]` and sets
its matrix with `include: ${{ fromJson(needs.matrix-setup.outputs.matrix) }}`.
The invalid job-level `if` is removed. Excluded platforms are never expanded
into jobs rather than created and then skipped.

## 3. Change scope verification

| Check | Result | Notes |
|---|---|---|
| New setup job | pass | matrix-setup outputs a single `matrix` value from one shell step. |
| Dynamic matrix wiring | pass | build reads `fromJson(needs.matrix-setup.outputs.matrix)`; runner and platform fields are unchanged per entry. |
| Invalid condition removed | pass | the build job has no job-level `if`. |
| Tag push path | pass | non-dispatch events take the full four-entry branch. |
| Entry fields preserved | pass | runner, asset_os, arch, and target match the previous static values for all four platforms. |
| Out of scope untouched | pass | application and firmware code, the installer, ci.yml, and the build steps themselves are unchanged. |

## 4. Independent acceptance results

The fine-grained token used for the write operations was first verified
against the repository and returned push, admin, and maintain permissions.
The dispatch then returned HTTP 204 and created run 43567182678 on head
5768a02.

| Criterion | Result | Evidence |
|---|---|---|
| Dispatch accepted | pass | HTTP 204; the new run was detected with event workflow_dispatch. |
| Matrix filtering | pass | the run contained three jobs only: ensure-release, matrix-setup, and one Build macos arm64 job. No linux, windows, or macOS x86_64 build job was created. |
| Setup job | pass | Resolve build matrix completed success. |
| Target build | pass | Build macos arm64 completed success on macos-latest. |
| Overall run | pass | run status completed, conclusion success. |
| Compliance | pass | added lines contain no emoji, no AI names or markers, and no non-ASCII characters. |

## 5. Release asset verification

The release for tag v0.6.2 still carries exactly ten assets, all uploaded.
Only the two macOS arm64 assets carry the new build timestamp and were
replaced; the other eight assets retained their earlier timestamps and bytes.

| Asset | Size (bytes) | Updated (UTC) | State |
|---|---|---|---|
| HJSWorkbench-CLI-macos-arm64 | 7,744,208 | 2026-11-14 06:38 | replaced |
| HJSWorkbench-GUI-0.6.2-macos-arm64.tar.gz | 47,445,139 | 2026-11-14 06:38 | replaced |

The CLI asset previously measured 7,742,720 bytes and the GUI asset
47,445,670 bytes; the small size differences are expected from a fresh
PyInstaller build. `install.sh` was re-uploaded by the ensure-release job
with `--clobber`; its content is unchanged and its 12,141-byte size is
preserved. The asset names follow the naming contract used by
scripts/install.sh.

## 6. Independent download and binary verification

The metadata checks above do not prove that the published bytes are native
arm64. A separate verification therefore downloaded both assets from the
release and inspected their actual binary headers, without relying on the
workflow's green badge.

### 6.1 Method and network findings

A single full-file request stalled on the GitHub download host and returned
no data. The signed URL redirects to release-assets.githubusercontent.com.
Requests using the `Range` header returned HTTP 206, so the download was
split into 64 KiB blocks with retries, which completed reliably. The CLI was
fetched with one sequential worker; the larger GUI archive was fetched with
eight concurrent workers, each owning a disjoint byte range and writing at
its own offsets into a preallocated file.

### 6.2 CLI result

The downloaded CLI measured exactly 7,744,208 bytes, matching the API. Its
Mach-O header decoded as:

    magic    0xFEEDFACF   (64-bit Mach-O)
    cputype  0x0100000C   (ARM64)
    filetype 2            (MH_EXECUTE)
    ncmds    18

### 6.3 GUI result

The downloaded archive measured exactly 47,445,139 bytes and opened as a
valid gzip tar with 591 entries, confirming the compressed stream is
complete. The PyInstaller launcher at
`HJSWorkbench-GUI/HJSWorkbench-GUI` (5,831,424 bytes) is a 64-bit Mach-O
with magic 0xFEEDFACF and cputype 0x0100000C (ARM64). Every Mach-O binary
in the bundle was then audited: all 121 Mach-O files report cputype
0x0100000C, and no x86_64 or other-architecture binary is present.

### 6.4 Conclusion

Both refreshed macOS arm64 assets are native ARM64 executables, not x86_64
binaries and not mixed-architecture bundles, and their byte counts match
the release API. They are accepted for Apple Silicon hardware.

## 7. Notes

The single-platform input currently offers `macos-arm64` as the only
restricted target alongside `all`. Adding more targets later only requires
new branches in the matrix-setup step; the build job and its steps do not
change. The fine-grained token is scoped to this repository and expires after
90 days; the build's release upload still uses the workflow's automatic
GITHUB_TOKEN and does not depend on the dispatching token's contents scope.
