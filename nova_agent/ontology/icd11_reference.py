"""Opt-in offline reference lookup. Never feeds the diagnostic candidate registry."""
import json
from pathlib import Path
import sqlite3

DEFAULT_PATH=Path(__file__).resolve().parent/'snapshots'/'icd11_reference_2026.sqlite'


def lookup(query, limit=20, kind='mms_category', path=DEFAULT_PATH):
    if kind not in {'mms_category','extension','functioning','block','chapter','all'}:
        raise ValueError('Unknown reference class')
    if not isinstance(limit,int) or not 1 <= limit <= 100:
        raise ValueError('limit must be 1..100')
    path=Path(path)
    if not path.is_file():
        raise FileNotFoundError('WHO reference release has not been registered')
    with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        query=query.strip()
        if not query:
            raise ValueError("A nonempty search term is required")
        # User text is a literal search, never SQL or a wildcard instruction.
        escaped=query.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
        sql="SELECT code,title,uri,foundation_uri,row_kind,chapter FROM entries WHERE (code = ? COLLATE NOCASE OR title LIKE ? ESCAPE '\\')"
        args=[query,'%'+escaped+'%']
        if kind!='all':
            sql+=' AND row_kind = ?';args.append(kind)
        sql+=' ORDER BY CASE WHEN code = ? COLLATE NOCASE THEN 0 ELSE 1 END,code LIMIT ?';args.extend([query,limit])
        results=[dict(r,runtime_eligible=False,clinical_validation_status='NOT_VERIFIED') for r in db.execute(sql,args)]
        metadata={r['key']:json.loads(r['value']) for r in db.execute('SELECT * FROM metadata')}
    return dict(release=metadata['release'],attribution=metadata['attribution'],role='REFERENCE_ONLY',matches=results)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('query');p.add_argument('--kind',default='mms_category')
    p.add_argument('--database',type=Path,default=DEFAULT_PATH)
    a=p.parse_args();print(json.dumps(lookup(a.query,kind=a.kind,path=a.database),ensure_ascii=False,indent=2))
