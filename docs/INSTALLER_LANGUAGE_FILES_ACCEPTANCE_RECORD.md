# Installer Language Files Acceptance Record

Scope: the Windows installer failed to compile on the release workflow
because the default Inno Setup 6.7 installation no longer ships the
Simplified and Traditional Chinese message files. The fix vendors the two
official message files in the repository and has the build script copy them
into the compiler's `Languages` directory only when they are missing.
Acceptance is performed by an independent reviewer running the real build
entry point; the builder's own report is not a substitute.

## 1. Root cause

Starting with Inno Setup 6.7, the Simplified Chinese and Traditional
Chinese translations are classified as unofficial and moved to
`Files/Languages/Unofficial/` in the Inno Setup source. A default install,
including the copy preinstalled on GitHub-hosted Windows runners, therefore
has no `ChineseSimplified.isl` or `ChineseTraditional.isl` in its main
`Languages` directory. The installer's standard
`compiler:Languages\ChineseSimplified.isl` reference cannot resolve and
ISCC aborts with exit code 2. The English, French, and German files remain
in the main directory and are unaffected.

The failure was reproduced locally before the fix: a default Inno Setup
6.7.3 install failed with the same error, and compiling succeeded once the
two files were present.

## 2. Change scope verification

| Check | Result | Notes |
|---|---|---|
| Vendored files | pass | packaging/languages/ holds ChineseSimplified.isl, ChineseTraditional.isl, Inno-Setup-License.txt, and an English README. |
| Build script | pass | packaging/build_installer.py adds VENDOR_LANGUAGE_DIR, VENDORED_LANGUAGES, and ensure_language_files(); standard library only. |
| Compiler launcher resolution | pass | find_iscc() resolves a package-manager launcher on PATH to the installation it starts, so the files land in the directory the compiler reads. |
| Line ending protection | pass | root .gitattributes marks the .isl files and license as -text, so no checkout converts their bytes. |
| Documentation | pass | packaging/BUILD.md and docs/INSTALL.md describe the automatic provisioning and the manual step for a direct ISCC run. |
| Out of scope untouched | pass | installer.iss, both workflows, version files, scripts/install.sh, and application/firmware code are unchanged. |

## 3. Independent acceptance results

| Criterion | Result | Evidence |
|---|---|---|
| Compile after removing the Chinese files | pass | the script copied both files from packaging/languages/ into the compiler Languages directory and produced a non-empty Setup executable, exit 0. |
| Existing files are not overwritten | pass | with both files present the script reported "already present" and the file timestamps were identical before and after the run. |
| Vendored bytes unchanged | pass | SHA-256 of all three vendored files matches the official jrsoftware/issrc tag is-6_7_1. |
| Missing source and write failure | pass | both conditions raise BuildError with actionable messages; no raw traceback and no broad exception clause. |
| --print-version | pass | prints 0.6.2 and exits 0 without locating the compiler. |
| compileall | pass | python -m compileall -q . exits 0. |
| Compliance of added lines | pass | the 169 added non-isl lines contain no emoji, no AI names or markers, and no non-ASCII characters. |
| Release workflow | pass | the workflow_dispatch run completed with conclusion success on every platform. |

The launcher resolution was additionally exercised in an isolated
environment: with a package-manager shim on PATH and a real compiler
directory in the default location, find_iscc() returned the real compiler
path rather than the shim.

## 4. Release asset verification

The release for tag v0.6.2 carries ten assets, all in the uploaded state.
The Windows installer asset is present as
`HJS-Workbench-Setup-0.6.2.exe`, 46,828,607 bytes, matching the size the
build reported.

## 5. Exceptions and notes

Two lines in docs/INSTALL.md use non-ASCII language option names
(Simplified Chinese, Traditional Chinese, and the French cedilla). These
predate the change and are intentional user-facing names, equivalent to the
content of the localization catalogs; they are not AI markers and are not
errors. The two vendored .isl files are translation data and are expected
to contain non-ASCII text.
