"""Index curated TIA engineering notes without reseeding project knowledge.

Markdown remains authoritative; SQLite docs/FTS are derived search indexes.
An online SQLite backup precedes mutation, including any live WAL contents.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT=Path(__file__).resolve().parents[1]


def index(db, backup, extra):
    assert db.is_file() and not backup.exists()
    paths=sorted((ROOT/'siemens-kb/tia-automation').glob('*.md'))
    paths += [p.resolve() for p in extra]
    assert len(paths)==len({str(p.resolve()).casefold() for p in paths})
    assert all(p.is_file() and p.suffix=='.md' for p in paths)
    backup.parent.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(db)
    try:
        with sqlite3.connect(backup) as saved:con.backup(saved)
        tables=('projects','blocks','symbols','xref_calls','xref_access','io_map','general_knowledge')
        before={t:con.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in tables}
        updated=[]
        with con:
            for path in paths:
                raw=path.read_bytes();text=raw.decode('utf-8-sig');title=text.splitlines()[0].lstrip('# ').strip()
                sha=hashlib.sha256(raw).hexdigest()
                found=con.execute('SELECT id,sha256 FROM docs WHERE path=?',(str(path.resolve()),)).fetchone()
                if found and found[1]==sha:continue
                con.execute('''INSERT INTO docs(title,category,source,path,language,size_bytes,sha256,n_pages,first_line,notes)
                    VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(path) DO UPDATE SET
                    title=excluded.title,category=excluded.category,source=excluded.source,
                    language=excluded.language,size_bytes=excluded.size_bytes,sha256=excluded.sha256,
                    n_pages=excluded.n_pages,first_line=excluded.first_line,notes=excluded.notes''',
                    (title,'tia_automation','curated_measured',str(path.resolve()),'en',len(raw),sha,None,title,text))
                updated.append({'path':str(path.resolve()),'sha256':sha})
            # Existing schema has no FTS synchronization triggers.
            con.execute("INSERT INTO docs_fts(docs_fts) VALUES('rebuild')")
        after={t:con.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in tables}
        assert before==after,'project/general knowledge changed unexpectedly'
        assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        for path in paths:
            raw=path.read_bytes()
            row=con.execute('SELECT id,sha256,notes FROM docs WHERE path=?',(str(path.resolve()),)).fetchone()
            assert row and row[1]==hashlib.sha256(raw).hexdigest() and row[2]==raw.decode('utf-8-sig')
        hits=con.execute("SELECT d.path FROM docs_fts f JOIN docs d ON d.id=f.rowid WHERE docs_fts MATCH ?",('"sequence view"',)).fetchall()
        assert any(Path(p).name=='shared-sequence-view.md' for (p,) in hits)
        return {'database':str(db),'backup':str(backup),'indexed_documents':len(paths),
                'updated':updated,'preserved_table_counts':after,'integrity':'ok','search_hits':[p for (p,) in hits]}
    finally:con.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db',type=Path,default=ROOT/'data/siemens.db')
    p.add_argument('--backup',type=Path,required=True)
    p.add_argument('--extra',type=Path,action='append',default=[])
    p.add_argument('--report',type=Path,required=True)
    a=p.parse_args();assert not a.report.exists()
    result=index(a.db,a.backup,a.extra)
    a.report.write_bytes((json.dumps(result,indent=2)+'\n').encode('ascii'))
    print(json.dumps({'indexed_documents':result['indexed_documents'],'updated_documents':len(result['updated']),'integrity':result['integrity']}))
