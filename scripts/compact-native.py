#!/usr/bin/env python3
"""Remove local/debug symbols while verifying code and public symbols unchanged."""
import hashlib
import json
import os
import pathlib
import struct
import subprocess
import sys


def text_hash(path):
    data = path.read_bytes()
    if data[:4] != b'\xcf\xfa\xed\xfe':
        return None
    ncmds = struct.unpack_from('<I', data, 16)[0]
    pos = 32
    for _ in range(ncmds):
        cmd, length = struct.unpack_from('<II', data, pos)
        if cmd == 0x19:
            nsects = struct.unpack_from('<I', data, pos + 64)[0]
            for i in range(nsects):
                section = pos + 72 + i * 80
                name = data[section:section + 16].split(b'\0')[0]
                segment = data[section + 16:section + 32].split(b'\0')[0]
                if name == b'__text' and segment == b'__TEXT':
                    size = struct.unpack_from('<Q', data, section + 40)[0]
                    offset = struct.unpack_from('<I', data, section + 48)[0]
                    return hashlib.sha256(data[offset:offset + size]).hexdigest()
        pos += length
    raise RuntimeError('Native binary has no text section: ' + str(path))


def symbols(path):
    result = subprocess.run(['/usr/bin/nm', '-gUj', str(path)], check=True, capture_output=True)
    return hashlib.sha256(b'\n'.join(sorted(result.stdout.splitlines()))).hexdigest()


def compact(path):
    path = pathlib.Path(path).resolve()
    if 'Helpers' not in path.parts:
        raise ValueError('Only compact packaged Helpers copies')
    code = text_hash(path)
    if code is None:
        return None
    before = path.stat().st_size
    exports = symbols(path)
    subprocess.run(['/usr/bin/strip', '-S', '-x', str(path)], check=True, capture_output=True)
    assert text_hash(path) == code, 'Executable code changed: ' + str(path)
    assert symbols(path) == exports, 'Public symbols changed: ' + str(path)
    identity = os.environ.get('TOPDF_SIGN_IDENTITY')
    flags = ['--options', 'runtime', '--timestamp'] if identity else []
    subprocess.run(['codesign', '--force', *flags, '--sign', identity or '-', str(path)],
                   check=True, capture_output=True)
    subprocess.run(['codesign', '--verify', '--strict', str(path)], check=True, capture_output=True)
    return {'file': path.name, 'before_bytes': before, 'after_bytes': path.stat().st_size,
            'text_sha256': code, 'public_symbols_sha256': exports,
            'code_unchanged': True, 'public_symbols_unchanged': True}


if __name__ == '__main__':
    print(json.dumps(compact(pathlib.Path(sys.argv[1])), indent=2))
