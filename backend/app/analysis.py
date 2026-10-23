"""Point-in-time wind forecast evaluation. All datetimes are timezone aware."""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, date, time, timedelta, timezone
from statistics import mean, median
from zoneinfo import ZoneInfo
import math

UK = ZoneInfo('Europe/London')
START = date(2026, 1, 1)
END = date(2026, 1, 31)


def parse_dt(value):
    if not value:
        raise ValueError('missing datetime')
    return datetime.fromisoformat(str(value).replace('Z', '+00:00')).astimezone(timezone.utc)


def decision_cutoff(day: date, hhmm: str):
    h, m = map(int, hhmm.split(':'))
    return datetime.combine(day, time(h, m), UK).astimezone(timezone.utc)


def quantile(values, p):
    if not values:
        return None
    data = sorted(values)
    pos = (len(data) - 1) * p
    lo, hi = int(pos), min(int(pos)+1, len(data)-1)
    return data[lo] * (1-(pos-lo)) + data[hi] * (pos-lo)


def metrics(rows):
    matched = [x for x in rows if x.get('forecast_mw') is not None and x.get('actual_mw') is not None]
    err = [x['error_mw'] for x in matched]
    values = [abs(x) for x in err]
    return {
        'matched': len(matched), 'total': len(rows),
        'coverage_pct': round(100 * len(matched) / len(rows), 1) if rows else 0,
        'mae_mw': round(mean(values), 1) if values else None,
        'rmse_mw': round(math.sqrt(mean([e*e for e in err])), 1) if err else None,
        'bias_mw': round(mean(err), 1) if err else None,
        'overforecast_share_pct': round(100 * sum(e>0 for e in err)/len(err),1) if err else None,
        'p90_abs_error_mw': round(quantile(values, .90), 1) if values else None,
        'overforecast_energy_mwh': round(sum(max(0, e) * 1.0 for e in err), 1),
        'underforecast_energy_mwh': round(sum(max(0, -e) * 1.0 for e in err), 1),
        'p10_error_mw': round(quantile(err, .10), 1) if err else None,
        'p90_error_mw': round(quantile(err, .90), 1) if err else None,
    }


def build_rows(actual_records, forecast_records, cutoff='09:50'):
    """Evaluate hourly WINDFOR against two half-hour FUELHH observations.

    Keep missing actual half-hours missing rather than make up a full-hour value.
    Select only forecasts that existed by the preceding day's cutoff.
    """
    # Actuals can be re-issued; take latest publication for each delivery half-hour.
    actuals = {}
    for record in actual_records:
        if str(record.get('fuelType', '')).upper() != 'WIND':
            continue
        try:
            start = parse_dt(record['startTime'])
            mw = float(record['generation'])
            published = parse_dt(record['publishTime']) if record.get('publishTime') else start
        except (ValueError, TypeError, KeyError):
            continue
        previous = actuals.get(start)
        if previous is None or published > previous[0]:
            actuals[start] = (published, mw)

    forecasts = defaultdict(list)
    for record in forecast_records:
        try:
            start = parse_dt(record['startTime'])
            published = parse_dt(record['publishTime'])
            mw = float(record['generation'])
        except (ValueError, TypeError, KeyError):
            continue
        forecasts[start].append((published, mw))
    for items in forecasts.values():
        items.sort(key=lambda item: item[0])

    result = []
    day = START
    while day <= END:
        target_day = day + timedelta(days=1)
        boundary = decision_cutoff(day, cutoff)
        for index in range(24):
            start = datetime.combine(target_day, time(), UK).astimezone(timezone.utc) + timedelta(hours=index)
            options = forecasts.get(start, ())
            # Sorted ascending, choose last eligible only.
            choice = next((f for f in reversed(options) if f[0] <= boundary), None)
            # FUELHH is half-hourly; average the two 30-min MW readings for
            # an hour-equivalent actual power level. Both must be present.
            first = actuals.get(start)
            second = actuals.get(start + timedelta(minutes=30))
            forecast_mw = choice[1] if choice else None
            actual_mw = (first[1] + second[1]) / 2 if first and second else None
            error = round(forecast_mw - actual_mw, 2) if forecast_mw is not None and actual_mw is not None else None
            result.append({
                'decision_date': day.isoformat(), 'delivery_date': target_day.isoformat(),
                'start_time': start.isoformat().replace('+00:00','Z'),
                'time_uk': start.astimezone(UK).strftime('%H:%M'),
                'forecast_mw': round(forecast_mw, 2) if forecast_mw is not None else None,
                'actual_mw': round(actual_mw, 2) if actual_mw is not None else None,
                'error_mw': error,
                'publish_time': choice[0].isoformat().replace('+00:00','Z') if choice else None,
                'decision_cutoff': boundary.isoformat().replace('+00:00','Z'),
                'energy_gap_mwh': round(max(0,error)*1.0,2) if error is not None else None,
            })
        day += timedelta(days=1)
    return result


def summarize(rows, chosen_day):
    daily = []
    for key in sorted({r['decision_date'] for r in rows}):
        selected = [r for r in rows if r['decision_date'] == key]
        stat = metrics(selected)
        daily.append({'date': key, 'delivery_date': selected[0]['delivery_date'],
                      'mae_mw': stat['mae_mw'], 'bias_mw': stat['bias_mw'],
                      'coverage_pct': stat['coverage_pct'],
                      'forecast_avg_mw': round(mean([x['forecast_mw'] for x in selected if x['forecast_mw'] is not None]), 1) if any(x['forecast_mw'] is not None for x in selected) else None,
                      'actual_avg_mw': round(mean([x['actual_mw'] for x in selected if x['actual_mw'] is not None]),1) if any(x['actual_mw'] is not None for x in selected) else None})
    by_hour = []
    for hour in range(24):
        selected = [r for r in rows if int(r['time_uk'][:2]) == hour]
        stat = metrics(selected)
        by_hour.append({'hour': f'{hour:02}:00', 'mae_mw': stat['mae_mw'], 'bias_mw': stat['bias_mw']})
    return {'metrics': metrics(rows), 'daily': daily,
            'hourly': by_hour,
            'selected_metrics': metrics([r for r in rows if r['decision_date'] == chosen_day]),
            'selected_slots': [r for r in rows if r['decision_date'] == chosen_day],
            'worst_intervals': sorted((x for x in rows if x['error_mw'] is not None),key=lambda x: abs(x['error_mw']),reverse=True)[:5]}
