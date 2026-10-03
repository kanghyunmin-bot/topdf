#!/usr/bin/env python3
"""Trim only the copied headless engine, keeping filters, fonts and dictionaries."""
import json
import importlib.util
import os
import pathlib
import shutil
import subprocess
import sys


def size(root):
    return sum(p.stat().st_size for p in root.rglob('*') if p.is_file() and not p.is_symlink())


def slim(app):
    app = pathlib.Path(app).resolve()
    if app.parent.name != 'Helpers':
        raise ValueError('Only trim a packaged Contents/Helpers copy')
    before = size(app)
    resources = app / 'Contents/Resources'
    paths = [
        app / 'Contents/Frameworks/LibreOfficePython.framework',
        *[app / 'Contents/Frameworks' / name for name in
          ('libpythonloaderlo.dylib', 'libpyuno.dylib', 'pyuno.so')],
        *[resources / name for name in
          ('help', 'gallery', 'template', 'java', 'wizards', 'Scripts',
           'basic', 'python', 'pythonloader.py', 'pythonloader.unorc',
           'pythonscript.py', 'uno.py', 'unohelper.py',
           'extensions/nlpsolver', 'config/wizard')],
        # Keep the native macOS light/dark fallback themes.
        *[p for p in (resources / 'config').glob('images_*.zip')
          if p.name not in ('images_sukapura.zip', 'images_sukapura_dark.zip')],
    ]
    removed = []
    for path in paths:
        if not path.exists() and not path.is_symlink():
            continue
        removed.append(str(path.relative_to(app)))
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()
    # Spellcheck and hyphenation stay; editing-only thesaurus data is unnecessary.
    for pattern in ('th_*.dat', 'th_*.idx', 'thes_*.dat', 'thes_*.idx'):
        for path in (resources / 'extensions').rglob(pattern):
            removed.append(str(path.relative_to(app)))
            path.unlink()
    spec = importlib.util.spec_from_file_location('compact_native', pathlib.Path(__file__).with_name('compact-native.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    native_reports = []
    for folder in ('Frameworks', 'MacOS'):
        for path in sorted((app / 'Contents' / folder).rglob('*')):
            if path.is_file() and not path.is_symlink():
                with path.open('rb') as stream:
                    native = stream.read(4) == b'\xcf\xfa\xed\xfe'
                if native:
                    native_reports.append(module.compact(path))
    # Vendor's original resource seal no longer describes the trimmed bundle.
    # Compacted nested binaries have been resealed; reseal the application too.
    identity = os.environ.get('TOPDF_SIGN_IDENTITY')
    flags = ['--options', 'runtime', '--timestamp'] if identity else []
    subprocess.run(['codesign', '--force', *flags, '--sign', identity or '-', str(app)], check=True)
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
    report = {'profile': 'headless-pdf-v2', 'before_bytes': before,
              'after_bytes': size(app), 'removed': removed, 'native_compaction': native_reports,
              'preserved': ['document filters', 'native conversion libraries',
                            'fonts', 'dictionaries and hyphenation',
                            'locale data', 'registry', 'licenses']}
    return report


if __name__ == '__main__':
    print(json.dumps(slim(sys.argv[1]), indent=2))
