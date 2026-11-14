# Vendored Inno Setup language files

These two message files are redistributed unchanged from the official Inno
Setup source repository:

- Repository: https://github.com/jrsoftware/issrc
- Tag: is-6_7_1
- Source path: Files/Languages/Unofficial/
- Files:
  - ChineseSimplified.isl, maintained by Zhenghan Yang
  - ChineseTraditional.isl, maintained by GoneTone

## Why they are vendored

Starting with Inno Setup 6.7, the Simplified and Traditional Chinese
translations are classified as unofficial. The installer no longer places
them in the main `Languages` directory, so a default installation (including
the copy preinstalled on GitHub-hosted Windows runners) cannot resolve:

    compiler:Languages\ChineseSimplified.isl
    compiler:Languages\ChineseTraditional.isl

Referencing those missing files makes ISCC abort with exit code 2.

`packaging/build_installer.py` copies the files from this directory into the
compiler's `Languages` directory before compiling, but only when they are not
already present. An existing file is never overwritten. The English, French,
and German messages stay in the compiler's own `Languages` directory and are
not vendored here.

## License

The files are distributed under the Inno Setup License, reproduced in
`Inno-Setup-License.txt`. The copyright notices and comments inside the
original files are retained and the files are not modified.
