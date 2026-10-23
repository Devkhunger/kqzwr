from datetime import date
from backend.app.analysis import build_rows, decision_cutoff, metrics, parse_dt


def test_cutoff_and_no_hindsight():
    slot='2026-01-02T00:00:00Z'
    actual=[{'fuelType':'WIND','startTime':slot,'generation':1000},
            {'fuelType':'WIND','startTime':'2026-01-02T00:30:00Z','generation':1200}]
    forecast=[
        {'startTime':slot,'publishTime':'2026-01-01T08:00:00Z','generation':900},
        {'startTime':slot,'publishTime':'2026-01-01T09:49:00Z','generation':1100},
        {'startTime':slot,'publishTime':'2026-01-01T10:00:00Z','generation':1000},
    ]
    row=build_rows(actual,forecast)[0]
    assert row['forecast_mw']==1100
    assert row['actual_mw']==1100
    assert row['error_mw']==0
    assert row['publish_time']=='2026-01-01T09:49:00Z'
    assert row['energy_gap_mwh']==0


def test_missing_forecasts_remain_missing():
    rows=build_rows([{'fuelType':'WIND','startTime':'2026-01-02T00:00:00Z','generation':800}],[])
    assert len(rows)==31*24
    assert rows[0]['forecast_mw'] is None
    assert metrics(rows)['coverage_pct']==0


def test_filter_fuel_and_rmse():
    rows=build_rows([{'fuelType':'GAS','startTime':'2026-01-02T00:00:00Z','generation':333}],
                    [{'startTime':'2026-01-02T00:00:00Z','publishTime':'2026-01-01T09:00:00Z','generation':222}])
    assert rows[0]['actual_mw'] is None
    assert metrics(rows)['matched']==0


def test_cutoff_timezone_january():
    assert decision_cutoff(date(2026,1,1),'09:50').isoformat()=='2026-01-01T09:50:00+00:00'


def test_hourly_mean_requires_both_actuals():
    slot='2026-01-02T00:00:00Z'
    one=[{'fuelType':'WIND','startTime':slot,'generation':1200}]
    forecast=[{'startTime':slot,'publishTime':'2026-01-01T08:30:00Z','generation':1300}]
    incomplete=build_rows(one,forecast)
    assert incomplete[0]['actual_mw'] is None
    assert incomplete[0]['error_mw'] is None
    one.append({'fuelType':'WIND','startTime':'2026-01-02T00:30:00Z','generation':800})
    full=build_rows(one,forecast)
    assert full[0]['actual_mw']==1000
    assert full[0]['error_mw']==300
    assert full[0]['energy_gap_mwh']==300

def test_hourly_completeness_demo():
    from backend.app.demo import make_demo
    actual,forecast=make_demo()
    rows=build_rows(actual,forecast)
    assert len(rows)==31*24
    assert metrics(rows)['coverage_pct']==100.0
