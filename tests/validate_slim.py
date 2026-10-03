"""Compare full and trimmed converters, including rendered pixels and old formats."""
import json
import pathlib
import shutil
import subprocess
import sys
from PIL import Image, ImageChops
from pypdf import PdfReader
from create_rich_fixtures import create

ROOT = pathlib.Path(__file__).resolve().parent.parent
FULL = pathlib.Path(sys.argv[2]).resolve() if len(sys.argv)>2 else ROOT / 'build/release/PDF로 변환.app'
SLIM = pathlib.Path(sys.argv[1]).resolve()
OUT = ROOT / 'build/slim-validation' / SLIM.parent.name
OUT.mkdir(parents=True, exist_ok=True)
renderer = shutil.which('pdftoppm')
if not renderer:
    raise SystemExit('pdftoppm is required for rendering equivalence')
inputs = [ROOT / f'tests/sample.{ext}' for ext in ('docx', 'pptx', 'xlsx', 'hwp', 'hwpx')]
lo = FULL / 'Contents/Helpers/LibreOffice.app/Contents/MacOS/soffice'
# Exercise legacy and OpenDocument filters as well as modern Office formats.
for source, formats in [('docx', ['doc', 'rtf', 'odt', 'html', 'epub']),
                         ('xlsx', ['xls', 'ods', 'csv']), ('pptx', ['ppt', 'odp'])]:
    for ext in formats:
        dest = OUT / 'fixtures' / ext
        dest.mkdir(parents=True, exist_ok=True)
        profile = dest / 'profile'
        subprocess.run(['/usr/bin/sandbox-exec', '-p', '(version 1)(allow default)(deny network-outbound (remote ip "*:*"))(deny network-inbound (local ip "*:*"))',
                        str(lo), '-env:UserInstallation=' + profile.as_uri(), '--headless',
                        '--convert-to', ext, '--outdir', str(dest),
                        str(ROOT / f'tests/sample.{source}')], check=True, capture_output=True, timeout=60)
        fixture = dest / ('sample.' + ext)
        assert fixture.is_file(), (ext, 'fixture export failed')
        inputs.append(fixture)
inputs.extend(create(OUT / "rich-fixtures"))
results = []
for source in inputs:
    renders = []
    docs = []
    exits = []
    for label, app in [('full', FULL), ('slim', SLIM)]:
        dest = OUT / label / (source.stem + '-' + source.suffix[1:])
        dest.mkdir(parents=True, exist_ok=True)
        pdf = dest / 'result.pdf'
        process = subprocess.run([str(app / 'Contents/MacOS/TopDF'), '--convert-test', str(source), str(pdf)],
                                 capture_output=True, timeout=60)
        exits.append(process.returncode)
        if process.returncode != 0:
            continue
        doc = PdfReader(pdf)
        docs.append(doc)
        subprocess.run([renderer, '-r', '72', '-png', str(pdf), str(dest / 'page')],
                       check=True, capture_output=True, timeout=60)
        renders.append(sorted(dest.glob('page-*.png')))
    assert (exits[0] == 0) == (exits[1] == 0), (source.suffix, exits)
    if exits[0] != 0:
        results.append({'fixture': source.name, 'format': source.suffix, 'baseline_supported': False, 'slim_supported': False})
        print('PASS:', source.name, 'rejected by both baseline and slim', flush=True)
        continue
    assert len(docs[0].pages) == len(docs[1].pages)
    assert ''.join(p.extract_text() for p in docs[0].pages) == ''.join(p.extract_text() for p in docs[1].pages)
    assert len(renders[0]) == len(renders[1]) > 0
    for a, b in zip(*renders):
        with Image.open(a) as ia, Image.open(b) as ib:
            assert ia.size == ib.size and ImageChops.difference(ia.convert('RGB'), ib.convert('RGB')).getbbox() is None, (source.suffix, a, b)
    result = {'fixture': source.name, 'format': source.suffix, 'pages': len(docs[0].pages), 'text_equal': True, 'pixels_equal': True}
    results.append(result)
    print('PASS:', source.name, 'text and rendered pixels match', flush=True)
(OUT / 'report.json').write_text(json.dumps(results, indent=2))
print('PASS:', len(results), 'format comparisons')
