#!/usr/bin/env python3
"""Build tiny deterministic type-2 AppImages for installed CLI/helper tests.

The minimal native ELF exits successfully; it is not a general AppImage runtime.
The real SquashFS payload exercises libappimage's desktop integration reader.
"""
import argparse
from pathlib import Path
import struct
import subprocess
import tempfile


def make_elf(update_info):
    names = ['', '.text', '.upd_info', '.digest_md5', '.sha256_sig', '.sig_key', '.shstrtab']
    strings = b'\0'
    offsets = [0]
    for name in names[1:]:
        offsets.append(len(strings))
        strings += name.encode() + b'\0'
    # x86_64 Linux exit(0), followed by ordinary named AppImage metadata sections.
    sections = [b'\xb8\x3c\0\0\0\x31\xff\x0f\x05', update_info.encode() + b'\0',
                bytes(16), bytes(1), bytes(1), strings]
    body = bytearray(120)
    section_offsets = []
    for section in sections:
        section_offsets.append(len(body))
        body.extend(section)
    while len(body) % 8:
        body.append(0)
    shoff = len(body)
    body.extend(bytes(64))
    for index, section in enumerate(sections, 1):
        body.extend(struct.pack('<IIQQQQIIQQ', offsets[index], 3 if index == 6 else 1,
                                6 if index == 1 else 0,
                                0x400000 + section_offsets[0] if index == 1 else 0,
                                section_offsets[index - 1], len(section), 0, 0, 1, 0))
    ident = b'\x7fELF\x02\x01\x01\0AI\x02' + bytes(5)
    body[:64] = struct.pack('<16sHHIQQQIHHHHHH', ident, 2, 62, 1, 0x400078, 64,
                           shoff, 0, 64, 56, 1, 64, 7, 6)
    body[64:120] = struct.pack('<IIQQQQQQ', 1, 5, 0, 0x400000, 0x400000,
                              len(body), len(body), 4096)
    return body


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    args.destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary) / 'AppDir'
        root.mkdir()
        (root / 'fixture.desktop').write_text('[Desktop Entry]\nType=Application\nName=Fedora RPM Fixture\n'
                                             'Exec=fixture %F\nIcon=fixture\nTerminal=false\nCategories=Utility;\n')
        (root / 'fixture.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16">'
                                        '<rect width="16" height="16" fill="blue"/></svg>\n')
        (root / '.DirIcon').symlink_to('fixture.svg')
        (root / 'AppRun').write_text('#!/bin/sh\nexit 0\n')
        (root / 'AppRun').chmod(0o755)
        payload = Path(temporary) / 'payload.squashfs'
        subprocess.run(['mksquashfs', str(root), str(payload), '-noappend', '-all-root',
                        '-no-xattrs', '-comp', 'gzip', '-processors', '1', '-mkfs-time', '0',
                        '-all-time', '0', '-no-progress'], check=True)
        for name, update in [('Fixture Update.AppImage', 'zsync|https://example.invalid/fixture.AppImage.zsync'),
                             ('Fixture No Update.AppImage', '')]:
            output = args.destination / name
            output.write_bytes(make_elf(update) + payload.read_bytes())
            output.chmod(0o755)


if __name__ == '__main__':
    main()
