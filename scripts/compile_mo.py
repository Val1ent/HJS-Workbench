# -*- coding: utf-8 -*-
"""Pure-Python gettext catalog compiler: locales/*.po -> locales/<code>/LC_MESSAGES/*.mo.

Reads every ``.po`` file directly under ``locales/`` and writes the compiled
catalog for the same language code. It parses msgid/msgstr entries including
multi-line continuation strings and escape sequences, skips comments and
fuzzy entries, and emits a little-endian GNU ``.mo`` (revision 0) that the
standard-library ``gettext`` module loads. No system ``msgfmt`` and no
third-party package is required.
"""
import os
import re
import struct
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from core.i18n import DOMAIN, locale_dir  # noqa: E402

MAGIC = 0x950412de

_STRING_RE = re.compile(r'"(?:\\.|[^"\\])*"')

_ESCAPES = {
    "n": "\n", "t": "\t", "r": "\r", "a": "\a", "b": "\b",
    "f": "\f", "v": "\v", '"': '"', "'": "'", "\\": "\\",
}


def unescape(s):
    """Decode the escape sequences of one concatenated po string."""
    out = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c != "\\" or i + 1 >= n:
            out.append(c)
            i += 1
            continue
        nxt = s[i + 1]
        if nxt in _ESCAPES:
            out.append(_ESCAPES[nxt])
            i += 2
        elif nxt in "01234567":
            j = i + 1
            val = 0
            while j < n and j < i + 4 and s[j] in "01234567":
                val = val * 8 + int(s[j])
                j += 1
            out.append(chr(val & 0xFF))
            i = j
        else:
            out.append(nxt)
            i += 2
    return "".join(out)


def parse_po(path):
    """Parse a .po file; return a list of (msgid, msgstr) pairs.

    Comment lines are ignored, fuzzy entries are skipped, and later
    duplicate msgids override earlier ones.
    """
    entries = []
    by_id = {}
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    msgid_parts = None
    msgstr_parts = None
    current = None
    fuzzy = False

    def flush():
        nonlocal msgid_parts, msgstr_parts, current, fuzzy
        if msgid_parts is not None and not fuzzy:
            mid = unescape("".join(msgid_parts))
            mstr = unescape("".join(msgstr_parts)) if msgstr_parts else ""
            by_id[mid] = mstr
        msgid_parts = msgstr_parts = None
        current = None
        fuzzy = False

    for raw in lines:
        line = raw.rstrip("\n")
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            if stripped.startswith("#,"):
                flags = [w.strip() for w in stripped[2:].split(",")]
                if "fuzzy" in flags:
                    fuzzy = True
            continue
        match = re.match(r"^msgid\s+(.*)$", line)
        if match:
            if msgid_parts is not None:
                flush()
            msgid_parts = []
            current = "msgid"
            for s in _STRING_RE.findall(match.group(1)):
                msgid_parts.append(s[1:-1])
            continue
        match = re.match(r"^msgstr\s+(.*)$", line)
        if match:
            msgstr_parts = []
            current = "msgstr"
            for s in _STRING_RE.findall(match.group(1)):
                msgstr_parts.append(s[1:-1])
            continue
        if current and line.startswith('"'):
            for s in _STRING_RE.findall(line):
                if current == "msgid":
                    msgid_parts.append(s[1:-1])
                else:
                    msgstr_parts.append(s[1:-1])
            continue
        # Unknown directives (msgctxt and friends) are not used and ignored.
    flush()
    entries.extend(sorted(by_id.items(), key=lambda e: e[0].encode("utf-8")))
    return entries


def build_mo(entries):
    """Serialize (msgid, msgstr) pairs into the .mo byte string."""
    ids = [e[0].encode("utf-8") for e in entries]
    strs = [e[1].encode("utf-8") for e in entries]
    count = len(entries)
    table_size = 8 * count
    id_table_off = 20
    str_table_off = id_table_off + table_size
    id_blob_off = str_table_off + table_size

    id_offsets = []
    pos = id_blob_off
    for b in ids:
        id_offsets.append(pos)
        pos += len(b) + 1
    str_blob_off = pos
    str_offsets = []
    pos = str_blob_off
    for b in strs:
        str_offsets.append(pos)
        pos += len(b) + 1

    out = bytearray(struct.pack("<5I", MAGIC, 0, count,
                                id_table_off, str_table_off))
    for b, off in zip(ids, id_offsets):
        out += struct.pack("<II", len(b), off)
    for b, off in zip(strs, str_offsets):
        out += struct.pack("<II", len(b), off)
    for b in ids:
        out += b + b"\x00"
    for b in strs:
        out += b + b"\x00"
    return bytes(out)


def main():
    """Compile every .po file under locales/ into the GNU catalog layout."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    locales = locale_dir()
    po_files = sorted(
        p for p in os.listdir(locales) if p.endswith(".po"))
    if not po_files:
        print(f"No .po files found under {locales}")
        return 1
    for po_name in po_files:
        code = os.path.splitext(po_name)[0]
        entries = parse_po(os.path.join(locales, po_name))
        mo_dir = os.path.join(locales, code, "LC_MESSAGES")
        os.makedirs(mo_dir, exist_ok=True)
        out_path = os.path.join(mo_dir, DOMAIN + ".mo")
        with open(out_path, "wb") as f:
            f.write(build_mo(entries))
        print(f"Compiled {po_name} -> {os.path.relpath(out_path, root)}"
              f" ({len(entries)} entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
