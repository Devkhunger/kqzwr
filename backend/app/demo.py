"""Deterministic SIMULATED records, visibly labeled in UI; never presented as Elexon data."""
from datetime import datetime, date, time, timedelta, timezone
from math import pi, sin, cos
from random import Random
from zoneinfo import ZoneInfo


def make_demo():
    rng = Random(71)
    actual, forecast = [], []
    uk = ZoneInfo('Europe/London')
    day = date(2026, 1, 1)
    for d in range(31):
        decision_day = day + timedelta(days=d)
        publish = datetime.combine(decision_day, time(8,30),uk).isoformat()
        older = datetime.combine(decision_day-timedelta(days=1), time(20,30),uk).isoformat()
        late = datetime.combine(decision_day,time(11,30),uk).isoformat()
        target = decision_day + timedelta(days=1)
        for period in range(48):
            start = datetime.combine(target,time(),uk)+timedelta(minutes=30*period)
            baseline = 8600+3500*sin((d+2)*.59)+1800*cos(period/48*2*pi)+800*sin(d*.21+period*.1)
            a = max(350,baseline+rng.gauss(0,210))
            f = max(300,a+700*sin(d*.27+period*.13)+rng.gauss(0,700))
            s = start.isoformat()
            actual.append({'startTime':s,'generation':round(a,1),'fuelType':'WIND', 'publishTime':(start+timedelta(hours=2)).isoformat()})
            # The raw WINDFOR series is hourly, unlike the FUELHH actuals.
            if period % 2 == 0:
                forecast.append({'startTime':s,'publishTime':older,'generation':round(f+rng.gauss(0,420),1)})
                forecast.append({'startTime':s,'publishTime':publish,'generation':round(f,1)})
                forecast.append({'startTime':s,'publishTime':late,'generation':round(a+rng.gauss(0,200),1)})
    return actual,forecast
