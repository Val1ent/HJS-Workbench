# Windows Asset Naming Acceptance Record

Scope: the Linux and macOS release assets carry their platform and
architecture in the file name (for example `HJSWorkbench-CLI-linux-x86_64`
and `HJSWorkbench-CLI-macos-arm64`), while the Windows assets carried only
the version, so a user could not read the target platform from the file name.
The change adds the `windows-x86_64` tag to every Windows asset so all three
platforms follow the same naming pattern. The version number is kept. The
Windows Setup installer is renamed as well, making the symmetry complete.
Acceptance is performed by an independent reviewer against the rebuilt
release assets and the real download endpoint; the workflow's green badge is
not a substitute.

## 1. Name change

| Old name | New name |
|---|---|
| HJS-Workbench-Setup-0.6.2.exe | HJS-Workbench-Setup-0.6.2-windows-x86_64.exe |
| HJSWorkbench-CLI-0.6.2.exe | HJSWorkbench-CLI-0.6.2-windows-x86_64.exe |
| HJSWorkbench-GUI-0.6.2.zip | HJSWorkbench-GUI-0.6.2-windows-x86_64.zip |

The Linux and macOS asset names are unchanged.

## 2. Files changed

- `.github/workflows/release.yml`: the five Windows asset name references
  (Setup upload, GUI archive build, CLI rename, CLI upload, GUI upload) now
  include `windows-x86_64`.
- `packaging/installer.iss`: `OutputBaseFilename` and the matching comment
  now include `windows-x86_64`.
- `packaging/build_installer.py`: `SETUP_NAME_TEMPLATE` now includes
  `windows-x86_64`; the template still agrees with the Inno Setup output
  name.
- `docs/INSTALL.md` and `packaging/BUILD.md`: the Setup file name
  references are updated.

The local lint check passed and all 81 unit tests passed before the change
was committed.

## 3. Per-platform dispatch

The release workflow's `workflow_dispatch` input previously offered only
`all` and `macos-arm64`. The matrix setup job is generalized so a single
target can be selected for every platform: `all`, `windows-x86_64`,
`linux-x86_64`, `macos-arm64`, or `macos-x86_64`. The Windows rebuild was
then dispatched with `build_target` set to `windows-x86_64`, so the run
executed only the release, matrix, and Windows build jobs without
rebuilding Linux or macOS.

## 4. Build and upload

The dispatched release run completed with success. The three Windows assets
were uploaded with the new names and the uploaded state:

| New asset | Size (bytes) |
|---|---|
| HJS-Workbench-Setup-0.6.2-windows-x86_64.exe | 46,831,567 |
| HJSWorkbench-CLI-0.6.2-windows-x86_64.exe | 8,702,386 |
| HJSWorkbench-GUI-0.6.2-windows-x86_64.zip | 67,540,558 |

The small size differences from the previous build are the normal result of
rebuilding the same sources; the byte sizes above are the values reported by
the release API after upload.

## 5. Old asset removal

After the new assets were confirmed present, the three old-name assets were
deleted through the release asset API, each returning HTTP 204. The release
then holds ten assets: three Windows, two Linux, four macOS, and
`install.sh`. No old-name Windows asset remains.

## 6. Download verification

Each new Windows asset was requested with a `Range: bytes=0-4095` header.
All three returned HTTP 206 from the release asset host. The two executable
assets begin with the `MZ` header and the zip begins with the `PK` header,
matching their file types.

## 7. Historical records

`docs/INSTALLER_LANGUAGE_FILES_ACCEPTANCE_RECORD.md` records the state of
the earlier build and keeps the old Setup name and its byte size. It is a
historical snapshot of that build and is left unchanged on purpose; this
record documents the later rename rather than rewriting the earlier
evidence.
