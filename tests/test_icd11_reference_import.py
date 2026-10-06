"""Synthetic importer mechanics; no WHO content is bundled as test fixtures."""
import json
import sqlite3
import pytest
from scripts import import_icd11_reference as importer
from nova_agent.ontology.icd11_reference import lookup
from nova_agent.ontology.registry import get_default_catalog


def row(code='TEST-CODE', chapter='01'):
    return {'Code':code,'Title':'Synthetic test label','ClassKind':'category','ChapterNo':chapter,
            'Linearization URI':'http://id.who.int/icd/test-only','Foundation URI':'test','Parent':''}


def install(tmp_path, monkeypatch, rows):
    source=tmp_path/'source';source.write_bytes(b'synthetic test source')
    monkeypatch.setattr(importer,'read_rows',lambda archive:iter(rows))
    target=tmp_path/'test.sqlite'
    return importer.build(source,target),target,source


def test_preserves_official_fields_and_separates_reference_types(tmp_path,monkeypatch):
    a=row();b=row('EXT','X');c=row('FUNC','V')
    metadata,path,_=install(tmp_path,monkeypatch,[a,b,c])
    assert metadata['counts']=={'mms_category':1,'extension':1,'functioning':1}
    found=lookup('TEST-CODE',path=path)['matches'][0]
    assert found['code']==a['Code'] and found['title']==a['Title'] and found['uri']==a['Linearization URI']
    assert found['runtime_eligible'] is False
    assert lookup('EXT',path=path)['matches']==[]
    assert len(lookup('EXT',path=path,kind='extension')['matches'])==1
    with sqlite3.connect(path) as db:
        assert json.loads(db.execute('SELECT official_row FROM entries WHERE code=?',(a['Code'],)).fetchone()[0])==a
    assert get_default_catalog().get_condition('onto:ICD11:TEST-CODE') is None


def test_duplicate_codes_fail_atomically(tmp_path,monkeypatch):
    with pytest.raises(sqlite3.IntegrityError):install(tmp_path,monkeypatch,[row(),row()])
    assert not (tmp_path/'test.sqlite').exists()


def test_existing_database_never_overwritten(tmp_path,monkeypatch):
    _,path,source=install(tmp_path,monkeypatch,[row()]);before=path.read_bytes()
    with pytest.raises(FileExistsError):importer.build(source,path)
    assert path.read_bytes()==before


def test_missing_code_or_uri_fails(tmp_path,monkeypatch):
    with pytest.raises(ValueError):install(tmp_path,monkeypatch,[row('')])


def test_query_uses_literal_parameters(tmp_path,monkeypatch):
    _,path,_=install(tmp_path,monkeypatch,[row()])
    assert lookup("' OR 1=1 --",path=path)['matches']==[]
    assert lookup('%',path=path)['matches']==[]
    with pytest.raises(ValueError):lookup('x',limit=1000,path=path)


def test_submission_packager_excludes_operator_database(tmp_path,monkeypatch):
    from scripts import build_nova_submission as packaging
    root=tmp_path/'source'; package=root/'nova_agent';package.mkdir(parents=True)
    (package/'__init__.py').write_text('')
    (package/'operator.sqlite').write_bytes(b'operator data')
    (package/'operator.sqlite-journal').write_bytes(b'journal')
    destination=tmp_path/'submission'
    monkeypatch.setattr(packaging,'ROOT',root)
    monkeypatch.setattr(packaging,'SUBMISSION',destination)
    packaging._copy_package('nova_agent')
    assert (destination/'nova_agent/__init__.py').exists()
    assert not list((destination/'nova_agent').glob('*.sqlite*'))
