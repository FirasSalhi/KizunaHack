import json, sys, csv, re
sys.stdout.reconfigure(encoding='utf-8')
R = sys.argv[1]; OUT = sys.argv[2]
def rcsv(p): return list(csv.DictReader(open(p, encoding='utf-8')))
def num(x):
    try: v=float(x); return None if v!=v else round(v,4)
    except: return None
H = rcsv(f'{R}/data/chott_meriam_hourly_clean.csv')
hourly = [{'t': r['timestamp'][:16], **{k: num(r[k]) for k in ('VWC_10cm','VWC_30cm','VWC_60cm','soil_temperature_C_10cm','soil_temperature_C_30cm','soil_temperature_C_60cm')}} for r in H]
E = rcsv(f'{R}/results/eto_daily_chott_meriam.csv')
eto = [{'d': r['date'], 'tmin': num(r['tmin']), 'tmax': num(r['tmax']), 'rain': num(r['rain_mm']), 'pm': num(r['eto_mm']) if r['eto_method'].startswith('FAO56') else None,
        'eto': num(r['eto_mm']), 'method': r['eto_method'], 'hs': num(r['eto_hargreaves_mm'])} for r in E]
fm = rcsv(f'{R}/results/forecast_metrics.csv'); mh = rcsv(f'{R}/results/multi_horizon_evaluation.csv')
dq = rcsv(f'{R}/results/data_quality_report_corrected.csv')
db = json.load(open(f'{R}/FARMLINK_Module5_Deliverables/crop_knowledge/crop_database.json', encoding='utf-8'))['crops']
crops = []
for c in db:
    k = c.get('kc') or {}; rd = c.get('root_depth') or {}; p = c.get('depletion_fraction_p') or {}
    if k.get('ini') is None or k.get('mid') is None or k.get('end') is None or p.get('value') is None: continue
    rng = [rd.get('zr_min_m'), rd.get('zr_max_m'), rd.get('default_for_scheduling_m')]
    crops.append({'id': c['id'], 'fr': c['names'].get('fr') or c['id'], 'ar': c['names'].get('ar'), 'ini': k['ini'], 'mid': k['mid'], 'end': k['end'],
                  'zr': rng, 'p': p['value'], 'stages': c.get('stage_lengths_days'), 'conf': (c.get('confidence') or {}).get('kc'), 'cat': c.get('category'), 'perennial': c.get('perennial')})
farm = json.load(open(f'{R}/FARMLINK_Module5_Deliverables/api/notebook_run_response.json', encoding='utf-8'))['response']
zones = []
for z in farm['zones']:
    zones.append({k: z.get(k) for k in ('zone_id','name','crop','status','stage','kc','etc_mm','zr_m','p','taw_mm','raw_mm','dr_mm','ea','area_ha','irrigation_method','soil_source','stage_estimated','depletion_source','forecast_rain_mm','days_to_raw','timing','missing_inputs')} | {'net_mm': (z.get('volumes') or {}).get('net_mm'), 'm3': (z.get('volumes') or {}).get('m3'), 'proj': z.get('projection')})
rep = open(f'{R}/results/unit_test_report.txt', encoding='utf-8').read()
data = {'hourly': hourly, 'eto': eto, 'forecast': fm, 'horizons': mh, 'dq': dq, 'crops': crops, 'zones': zones,
        'unit_tests': re.findall(r'Ran (\d+) tests', rep)}
open(OUT, 'w', encoding='utf-8').write(json.dumps(data, ensure_ascii=False, separators=(',', ':')))
print(len(hourly), len(eto), len(crops), len(zones), fm[:1], mh[:1], dq[:1], crops[0], sep='\n')
print([ (z['zone_id'], z['proj'][:1] if z['proj'] else None) for z in zones])
