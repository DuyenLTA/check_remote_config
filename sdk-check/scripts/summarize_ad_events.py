"""Summarise ad events from parse_fa_events.py output for the EV-xx checklist.

usage: python3 -I summarize_ad_events.py <events.json> [--skip HH:MM:SS-HH:MM:SS ...]
--skip excludes a time window (e.g. the offline part of a run) from the online checks.
Prints: counts per format, missing params, matched/load pairing, show<->paid pairing,
paid vs paid_value math, won_ad_source vs ad_source, clicks, units by format.
"""
import collections as C
import json
import sys
from datetime import datetime

E = json.load(open(sys.argv[1], encoding='utf-8'))
skips = [a.split('-') for a in sys.argv[3::2]] if '--skip' in sys.argv else []
ts = lambda e: datetime.strptime('2000-' + e['t'], '%Y-%m-%d %H:%M:%S.%f').timestamp()  # year avoids leap-day ambiguity
for e in E:
    e['ts'] = ts(e)
    p = e['p']
    e['u'] = (p.get('adunitid') or p.get('ad_unit_id') or p.get('ad_unit_name') or '').split('/')[-1]
    e['f'] = p.get('ad_format', '').lower()
in_skip = lambda e: any(a <= e['t'][6:14] < b for a, b in skips)
AD = ('track_ad_request', 'track_ad_matched_request', 'ad_load', 'ad_show', 'paid_ad_impression',
      'paid_ad_impression_value', 'event_user_click_ads', 'ad_impression', 'ad_click')
A = [e for e in E if e['name'] in AD]
on = [e for e in A if not in_skip(e)]

print('== counts per format (online)')
cnt = C.Counter()
for e in on:
    k = e['name']
    if k == 'ad_load':
        k += ':' + e['p'].get('load_status', '?')
    if k == 'ad_show':
        k += ':' + e['p'].get('show_status', '?')
    cnt[(e['f'] or '-', k)] += 1
for f in sorted({f for f, _ in cnt}):
    print(' ', f, {k: v for (ff, k), v in sorted(cnt.items()) if ff == f})

print('== missing params')
need = {'track_ad_request': ['adunitid', 'ad_format', 'network_status'],
        'track_ad_matched_request': ['ad_platform', 'adunitid', 'network_status', 'ad_format', 'ad_source'],
        'paid_ad_impression': ['valuemicros', 'currency', 'precision', 'adunitid', 'network', 'ad_platform', 'ad_format', 'ad_source'],
        'event_user_click_ads': ['ad_unit_id'], 'paid_ad_impression_value': ['value', 'currency']}
for n, ks in need.items():
    xs = [e for e in on if e['name'] == n]
    print(' ', n, len(xs), 'missing:', dict(C.Counter(k for e in xs for k in ks if k not in e['p'])))
ls = [e for e in on if e['name'] == 'ad_load' and e['p'].get('load_status') == 'success']
lf = [e for e in A if e['name'] == 'ad_load' and e['p'].get('load_status') != 'success']
print('  ad_load failed', len(lf), 'error fields:', C.Counter((e['p'].get('error_code'), e['p'].get('error_code_name'), 'error_domain' in e['p'], e['p'].get('error_message', '')[:40]) for e in lf).most_common(6))
sf = [e for e in A if e['name'] == 'ad_show' and e['p'].get('show_status') != 'success']
print('  ad_show failed', len(sf), C.Counter(tuple(sorted(k for k in e['p'] if not k.startswith('ga_'))) for e in sf).most_common(3))

print('== load success without exactly one matched (same unit, <=3s before)')
for l in ls:
    m = [e for e in on if e['name'] == 'track_ad_matched_request' and e['u'] == l['u'] and -0.5 <= l['ts'] - e['ts'] < 3]
    if len(m) != 1:
        print(' ', l['t'], l['u'], l['f'], 'matched=', len(m))

print('== show success <-> paid (same unit, <3s)')
ss = [e for e in on if e['name'] == 'ad_show' and e['p'].get('show_status') == 'success']
pi = [e for e in on if e['name'] == 'paid_ad_impression']
pv = [e for e in on if e['name'] == 'paid_ad_impression_value']
print('  show_success', len(ss), 'paid', len(pi), 'paid_value', len(pv))
for s in ss:
    if not any(p['u'] == s['u'] and abs(p['ts'] - s['ts']) < 3 for p in pi):
        print('  show without paid same unit:', s['t'], s['u'], s['f'], '| paid near:', [p['u'] for p in pi if abs(p['ts'] - s['ts']) < 3])
for p in pi:
    if not any(s['u'] == p['u'] and abs(p['ts'] - s['ts']) < 3 for s in ss):
        print('  paid without show same unit:', p['t'], p['u'], p['f'], '| shows near:', [s['u'] for s in ss if abs(p['ts'] - s['ts']) < 3])

print('== paid vs paid_value / won source')
won = {}
for e in on:
    if e['name'] == 'ad_load' and e['p'].get('load_status') == 'success':
        won[e['u']] = e['p'].get('won_ad_source')
mism = 0
for p in pi:
    v = [x for x in pv if x['u'] == p['u'] and abs(x['ts'] - p['ts']) < 1]
    bad = []
    pr = p['p'].get('precision')
    if not pr or not pr.isdigit() or int(pr) > 3:
        bad.append('precision=' + str(pr))
    for k in ('network', 'ad_source'):
        if p['p'].get(k, '') in ('', 'null'):
            bad.append(k + ' empty')
    if not v:
        bad.append('no paid_value')
    elif abs(float(v[0]['p'].get('value', -1)) - float(p['p'].get('valuemicros', 0)) / 1e6) > 1e-9:
        bad.append(f"value {v[0]['p'].get('value')} vs micros {p['p'].get('valuemicros')}")
    if p['u'] in won and won[p['u']] != p['p'].get('ad_source'):
        mism += 1
        bad.append(f"won {won[p['u']]} != ad_source {p['p'].get('ad_source')}")
    if bad:
        print(' ', p['t'], p['u'], p['f'], bad)
print('  valuemicros:', C.Counter(p['p'].get('valuemicros') for p in pi).most_common(5), '| currency:', C.Counter(p['p'].get('currency') for p in pi))
print('  won_ad_source vs ad_source mismatches:', mism, 'of', sum(p['u'] in won for p in pi))
print('== clicks')
for e in A:
    if e['name'] in ('event_user_click_ads', 'ad_click'):
        print(' ', e['t'], e['name'], e['u'], e['origin'])
print('== units by format')
u = C.defaultdict(set)
for e in on:
    u[e['f'] or '-'].add(e['u'])
for f, s in sorted(u.items()):
    print(' ', f, sorted(x for x in s if x))
