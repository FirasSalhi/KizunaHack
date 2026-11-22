import json, sys
sys.path.insert(0, sys.argv[1]); sys.stdout.reconfigure(encoding='utf-8')
from irrigation.decision import recommend_irrigation
from irrigation.soil import get_illustrative_soil, typical_system, SoilParams
from irrigation.eto import eto_hargreaves
cases = [
 dict(id='A', label='Tomate, mi-saison, sable limoneux, capteurs réels', crop='tomato', stage='mid_season', soil='loamy_sand', method='drip', vwc=[13.0,5.7,7.0], eto=1.91, horizon=1, rain=0),
 dict(id='B', label='Olivier, mi-saison, limon, sol humide', crop='olive', stage='mid_season', soil='silt', method='sprinkler', vwc=[25,24,26], eto=3.0, horizon=1, rain=0),
 dict(id='C', label='Blé dur, développement, limon, 3 jours', crop='durum_wheat', stage='development', soil='silt', method='drip', vwc=[22.5,22.5,22.5], eto=4.5, horizon=3, rain=0),
 dict(id='D', label='Tomate sans données de sol', crop='tomato', stage='mid_season', soil=None, method='drip', vwc=[13.0,5.7,7.0], eto=1.91, horizon=1, rain=0),
 dict(id='E', label='Tomate, argile limoneuse (capteurs incohérents)', crop='tomato', stage='mid_season', soil='silty_clay', method='drip', vwc=[13.0,5.7,7.0], eto=1.91, horizon=1, rain=0),
 dict(id='F', label='Olivier, initial, sol mesuré, capteurs calibrés', crop='olive', stage='initial', soil='custom', fc=0.30, wp=0.12, method='drip', vwc=[18,17,19], eto=2.5, horizon=2, rain=6, calibrated=True, documented=True),
]
out = []
for c in cases:
    if c['soil'] == 'custom': soil = SoilParams(c['fc'], c['wp'], source='measured')
    elif c['soil']: soil = get_illustrative_soil(c['soil'])
    else: soil = None
    r = recommend_irrigation(crop=c['crop'], stage=c['stage'], soil=soil, system=typical_system(c['method']),
        theta_now_by_depth_cm={10: c['vwc'][0], 30: c['vwc'][1], 60: c['vwc'][2]}, eto_mm_today=c['eto'], horizon_days=c['horizon'],
        rain_forecast_mm_next_days=[c['rain']] + [0.0]*(c['horizon']-1), eto_mm_next_days=[c['eto']]*c['horizon'],
        sensor_calibrated=c.get('calibrated', False), field_documented=c.get('documented', False), eto_method='FAO56_Penman_Monteith', weather_source='test')
    exp = {k: (round(r[k], 3) if isinstance(r[k], float) else r[k]) for k in ('status','timing','taw_mm','raw_mm','dr_now_mm','net_mm','gross_mm','confidence','readiness','etc_mm','p_used')}
    out.append({**c, 'expected': exp}); print(c['id'], exp)
hs = float(eto_hargreaves(19.06, 26.56, 22.73, 35.918, 322))
print('HS', hs)
json.dump({'calc': out, 'hargreaves': {'tmin': 19.06, 'tmax': 26.56, 'tmean': 22.73, 'lat': 35.918, 'date': '2026-11-18', 'expected': round(hs, 3)}},
          open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False)
