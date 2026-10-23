"""Fetch only FUELHH and WINDFOR publications from Elexon, archive raw records.

Run from repository root: python scripts/sync_data.py
API access required; no synthetic records will be saved to the real snapshot.
"""
import json, sys, time
from pathlib import Path
from datetime import datetime, timezone, timedelta
import httpx

ROOT=Path(__file__).resolve().parents[1]
BASE='https://data.elexon.co.uk/bmrs/api/v1/datasets'
JOBS=[
    # Forecasts that could be available for decisions in January, including Dec 31.
    ('WINDFOR',datetime(2025,12,30,tzinfo=timezone.utc),datetime(2026,2,1,tzinfo=timezone.utc)),
    # Final actual publication may lag delivery; use a generous follow-on window.
    ('FUELHH',datetime(2026,1,2,tzinfo=timezone.utc),datetime(2026,2,15,tzinfo=timezone.utc)),
]

def fetch(client, code, begin, end):
    url=f'{BASE}/{code}/stream'
    params={'publishDateTimeFrom':begin.isoformat().replace('+00:00','Z'),
            'publishDateTimeTo':end.isoformat().replace('+00:00','Z')}
    for attempt in range(5):
        try:
            r=client.get(url,params=params)
            if r.status_code in (429,500,502,503,504):
                raise httpx.HTTPStatusError('retryable',request=r.request,response=r)
            r.raise_for_status()
            data=r.json()
            if isinstance(data,dict): data=data.get('data',[])
            if not isinstance(data,list): raise ValueError(f'Unexpected {code} payload type')
            return data
        except (httpx.RequestError,httpx.HTTPStatusError) as e:
            if attempt==4: raise
            time.sleep(1.5*(2**attempt))
    return []

def main():
    data={}
    with httpx.Client(timeout=90, headers={'User-Agent':'WindScopePilot/0.1','Accept':'application/json'}) as client:
        for code,start,end in JOBS:
            all_rows=[];day=start
            while day<end:
                stop=min(day+timedelta(days=1),end)
                part=fetch(client,code,day,stop)
                all_rows.extend(part)
                print(f'{code} {day:%Y-%m-%d}: {len(part)} records',flush=True)
                day=stop
                time.sleep(.1)
            if not all_rows:
                raise RuntimeError(f'No records returned for {code}; not writing incomplete snapshot')
            data[code]=all_rows
    target=ROOT/'data'/'january_2026.json'
    target.parent.mkdir(parents=True,exist_ok=True)
    blob={'actuals':[x for x in data['FUELHH'] if str(x.get('fuelType','')).upper()=='WIND'],
          'forecasts':data['WINDFOR'],
          'updated_at':datetime.now(timezone.utc).isoformat(),
          'source_urls':[f'{BASE}/{code}/stream' for code,_,_ in JOBS]}
    if not blob['actuals'] or not blob['forecasts']:
        raise RuntimeError('No WIND actuals or WINDFOR forecasts; refusing to write snapshot')
    temp=target.with_suffix('.tmp');temp.write_text(json.dumps(blob,separators=(',',':')))
    temp.replace(target)
    print(f'Saved {len(blob["actuals"])} wind actuals, {len(blob["forecasts"])} forecasts to {target}')

if __name__=='__main__':
    main()
