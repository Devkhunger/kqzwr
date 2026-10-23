"""FastAPI entry. Real snapshot only if sync_data.py wrote it; explicit simulated fallback."""
from __future__ import annotations
import csv, io, json, os
from datetime import date
from functools import lru_cache
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from .analysis import build_rows, summarize
from .demo import make_demo

ROOT=Path(__file__).resolve().parents[2]
SNAPSHOT=ROOT/'data'/'january_2026.json'
app=FastAPI(title='WindScope | Wind forecast procurement intelligence',version='0.1.0')
app.add_middleware(CORSMiddleware, allow_origins=os.getenv('CORS_ORIGINS','http://localhost:5173,http://localhost:8080').split(','), allow_methods=['GET'], allow_headers=['*'])

@lru_cache(maxsize=1)
def source():
    if SNAPSHOT.is_file():
        blob=json.loads(SNAPSHOT.read_text())
        return blob['actuals'], blob['forecasts'], 'Elexon BMRS', blob.get('updated_at'), blob.get('source_urls',[])
    if os.getenv('ENABLE_DEMO','true').lower() not in ('true','1','yes'):
        raise FileNotFoundError('No Elexon snapshot found. Run python scripts/sync_data.py first.')
    a,f=make_demo()
    return a,f,'SIMULATED DEMO — NOT ELEXON DATA',None,[]

@lru_cache(maxsize=32)
def calculated(cutoff):
    actual,forecast,_,_,_=source()
    return build_rows(actual,forecast,cutoff)

def safe_cutoff(value):
    try:
        h,m=map(int,value.split(':'))
        if 0<=h<=23 and 0<=m<=59: return value
    except (ValueError,AttributeError): pass
    raise HTTPException(status_code=422,detail='cutoff must be HH:MM in UK local time')

@app.get('/api/health')
def health():
    return {'status':'ok','snapshot_available':SNAPSHOT.is_file()}

@app.get('/api/analysis')
def analysis(decision_date: date=Query(date(2026,1,15)),cutoff: str='09:50'):
    if not date(2026,1,1)<=decision_date<=date(2026,1,31):
        raise HTTPException(status_code=422,detail='Decision date must be in January 2026')
    cutoff=safe_cutoff(cutoff)
    a,f,name,updated,urls=source()
    return {'meta':{'source':name, 'is_demo':not SNAPSHOT.is_file(), 'updated_at':updated,
                    'source_urls':urls,'decisions':'2026-01-01 to 2026-01-31',
                    'delivery':'2026-01-02 to 2026-02-01','decision_date':decision_date.isoformat(),
                    'cutoff_uk':cutoff, 'resolution_minutes':60,'actual_source_resolution_minutes':30,
                    'forecast_records':len(f),'actual_records':len(a)},
            **summarize(calculated(cutoff),decision_date.isoformat())}

@app.get('/api/export.csv')
def export(cutoff: str='09:50'):
    rows=calculated(safe_cutoff(cutoff))
    if not rows: raise HTTPException(404,'No records')
    output=io.StringIO()
    writer=csv.DictWriter(output,fieldnames=list(rows[0]))
    writer.writeheader();writer.writerows(rows)
    return StreamingResponse(iter([output.getvalue()]),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="windscope_january_2026.csv"'})

# Docker: serve the compiled React frontend from the same Python process.
DIST=ROOT/'frontend'/'dist'
if DIST.is_dir():
    from fastapi.staticfiles import StaticFiles
    app.mount('/',StaticFiles(directory=DIST,html=True),name='frontend')
