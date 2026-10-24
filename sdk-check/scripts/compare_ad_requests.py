"""CMP-01 / CMP-02: compare ad requests and load success between an old-build and a new-build logcat.

Run the SAME flow on both builds (drive-fo-to-home.sh), capture `adb logcat -v threadtime`, then:
usage: python3 -I compare_ad_requests.py <old-logcat.txt> <new-logcat.txt>
Prints per ad unit: format, first screen, requests old/new, load ok/fail old/new;
totals; success rate per format; ad_load failure reasons per build.
"""
import collections
import re
import sys


def parse(path):
    req = collections.Counter(); fmt = {}; ok = collections.Counter(); fail = collections.Counter()
    scr = {}; why = collections.Counter()
    for line in open(path, encoding='utf-8', errors='replace'):
        if 'Logging event: origin=app' not in line:
            continue
        m = re.search(r'name=([a-z_]+),', line)
        u = re.search(r'ad_?unit_?id=ca-app-pub-\d+/(\d+)', line)
        if not m or not u:
            continue
        name, u = m.group(1), u.group(1)
        f = re.search(r'ad_format=([A-Za-z_]+)', line)
        sc = re.search(r'_sc\)=([A-Za-z0-9]+)', line)
        if name == 'track_ad_request':
            req[u] += 1
            if f:
                fmt[u] = f.group(1).upper()
            scr.setdefault(u, sc.group(1) if sc else '?')
        elif name == 'ad_load':
            st = re.search(r'load_status=(\w+)', line).group(1)
            (ok if st == 'success' else fail)[u] += 1
            if f:
                fmt.setdefault(u, f.group(1).upper())
            if st != 'success':
                e = re.search(r'error_message=([^,}]*)', line)
                why[re.sub(r'<https[^>]*>', '', e.group(1)).strip() if e else '?'] += 1
    return req, fmt, ok, fail, scr, why


O = parse(sys.argv[1]); N = parse(sys.argv[2])
units = sorted(set(O[0]) | set(N[0]), key=lambda u: (O[4].get(u, N[4].get(u, '')), u))
print(f"{'unit':12} {'format':12} {'screen':32} old new | old ok/fail  new ok/fail")
for u in units:
    print(f"{u:12} {O[1].get(u, N[1].get(u, '?')):12} {O[4].get(u, N[4].get(u, '?'))[:32]:32} {O[0][u]:3} {N[0][u]:3} | {O[2][u]}/{O[3][u]:<9} {N[2][u]}/{N[3][u]}")
print('TOTAL requests old', sum(O[0].values()), 'new', sum(N[0].values()))
for label, X in (('old', O), ('new', N)):
    by = collections.defaultdict(lambda: [0, 0])
    for u, c in X[0].items():
        by[X[1].get(u, '?')][0] += c
    for u, c in X[2].items():
        by[X[1].get(u, '?')][1] += c
    print(label, 'success/requests:', {k: f"{v[1]}/{v[0]}" for k, v in by.items() if v[0]}, '| fail reasons:', dict(X[5]))
