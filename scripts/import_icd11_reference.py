"""Offline WHO simple-tabulation importer. Reference registration, not diagnostic activation.

Keep the WHO archive and generated database local; no network access at runtime.
Requires openpyxl only for the one-time import, not reference queries.
"""
import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import re
import sqlite3
import tempfile
import zipfile

SOURCE_URL = 'https://icdcdn.who.int/static/releasefiles/2026-01/SimpleTabulation-ICD-11-MMS-en.zip'
LICENSE_URL = 'https://icd.who.int/en/docs/ICD11-license.pdf'
ATTRIBUTION = ('International Classification of Diseases, Eleventh Revision (ICD-11), '
               'World Health Organization (WHO) 2019. https://icd.who.int/browse11. '
               'CC BY-ND 3.0 IGO. Release 2026-01, English. No WHO endorsement of NOVA.')


def read_rows(archive):
    from openpyxl import load_workbook
    with zipfile.ZipFile(archive) as z:
        names = [n for n in z.namelist() if n == 'SimpleTabulation-ICD-11-MMS-en.xlsx']
        if len(names) != 1:
            raise ValueError('Expected official English MMS workbook')
        info = z.getinfo(names[0])
        if info.file_size > 64 * 1024 * 1024:
            raise ValueError('Workbook exceeds import bound')
        workbook = load_workbook(io.BytesIO(z.read(names[0])), read_only=True, data_only=False)
        try:
            values = iter(workbook.active.values)
            headers = next(values)
            required = {'Foundation URI','Linearization URI','Code','Title','ClassKind','ChapterNo','Parent'}
            if not required.issubset(headers):
                raise ValueError('Unexpected official workbook schema')
            if not any(str(h).startswith('Version:2026 Jan') for h in headers):
                raise ValueError('This importer is pinned to release 2026-01')
            for values_row in values:
                row = {str(k): v for k, v in zip(headers, values_row) if k}
                if row.get('ClassKind') in {'chapter','block','category'}:
                    yield row
        finally:
            workbook.close()


def build(archive, output):
    archive, output = Path(archive), Path(output)
    if output.exists():
        raise FileExistsError('Refusing to overwrite an existing registered release')
    output.parent.mkdir(parents=True, exist_ok=True)
    metadata = dict(source_url=SOURCE_URL,source_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                    release='2026-01',language='en',license_url=LICENSE_URL,attribution=ATTRIBUTION,
                    role='REFERENCE_ONLY',runtime_eligible=False,clinical_validation_status='NOT_VERIFIED',
                    additions_origin='NOVA adds row_kind and reference-only status; official data retained unchanged.')
    counts = Counter()
    with tempfile.NamedTemporaryFile(dir=output.parent, suffix='.sqlite', delete=False) as tmp:
        temporary = Path(tmp.name)
    try:
        with sqlite3.connect(temporary) as db:
            db.executescript('''CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE entries (id INTEGER PRIMARY KEY, code TEXT NOT NULL,
                title TEXT NOT NULL, uri TEXT NOT NULL, foundation_uri TEXT,
                row_kind TEXT NOT NULL, chapter TEXT NOT NULL, official_row TEXT NOT NULL);
                CREATE UNIQUE INDEX unique_code ON entries(code) WHERE code != '';
                CREATE INDEX kind_index ON entries(row_kind);''')
            for row in read_rows(archive):
                cls=row['ClassKind'];code=str(row.get('Code') or ''); title=row.get('Title') or ''
                uri=row.get('Linearization URI') or '';chapter=str(row.get('ChapterNo') or '')
                if not title or not uri.startswith('http://id.who.int/icd/'):
                    raise ValueError('Missing official title or URI')
                if cls=='category' and not code:
                    raise ValueError('Category missing code')
                kind = ('extension' if chapter=='X' else 'functioning' if chapter=='V' else 'mms_category') if cls=='category' else cls
                counts[kind]+=1
                # Title retains the official table indentation; no translation or crosswalk.
                db.execute('INSERT INTO entries(code,title,uri,foundation_uri,row_kind,chapter,official_row) VALUES(?,?,?,?,?,?,?)',
                           (code,title,uri,row.get('Foundation URI'),kind,chapter,json.dumps(row,ensure_ascii=False)))
            if not counts['mms_category']:
                raise ValueError('Empty import')
            metadata['counts']=dict(counts)
            db.executemany('INSERT INTO metadata VALUES(?,?)',[(k,json.dumps(v,ensure_ascii=False)) for k,v in metadata.items()])
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
                raise ValueError('Database integrity check failed')
        db.close()
        temporary.replace(output)
    except BaseException:
        if "db" in locals():
            db.close()
        temporary.unlink(missing_ok=True)
        raise
    return metadata


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--report',type=Path,required=True)
    a=p.parse_args();report=build(a.archive,a.output)
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report['counts']))
