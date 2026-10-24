"""CMP-03 / KT-02: per cold start, seconds from launcher START to each splash stage.

usage: python3 -I launch_stage_timing.py <logcat-threadtime.txt> [more logs...]
Stages: Splash Displayed (ms), fb = 'Fetch firebase successfully', ready = 'MobileAds ready',
req = first track_ad_request, load = 'loadInterstitialAd complete' (+ its own duration),
interReq->load = splash inter track_ad_request -> ad_load, show = first non-splash activity Displayed.
Compare old vs new: equal early stages + longer 'interReq->load' means the gap is ad-server/SDK time.
"""
import datetime
import re
import sys

t = lambda l: datetime.datetime.strptime(l.split()[1], '%H:%M:%S.%f')
KEYS = {'fb': 'Fetch firebase successfully', 'ready': 'MobileAds ready',
        'req': 'name=track_ad_request', 'load': 'loadInterstitialAd complete'}

for path in sys.argv[1:]:
    print('==', path)
    st = None; row = {}; ireq = None
    for l in open(path, encoding='utf-8', errors='replace'):
        if 'ActivityTaskManager: START' in l and 'LAUNCHER' in l:
            if row:
                print(' ', row)
            st = t(l); row = {}; ireq = None
            continue
        if not st:
            continue
        m = re.search(r'Displayed \S*SplashActivity.*\+(\d+)ms', l)
        if m:
            row['splashMs'] = int(m.group(1))
        for k, p in KEYS.items():
            if k not in row and p in l:
                row[k] = round((t(l) - st).total_seconds(), 2)
                if k == 'load':
                    d = re.search(r'in ((\d+)m )?([0-9.]+)s', l)
                    row['loadDur'] = round(int(d.group(2) or 0) * 60 + float(d.group(3)), 2)
        if 'name=track_ad_request' in l and 'INTERSTITIAL' in l and 'SplashActivity' in l and ireq is None:
            ireq = t(l)
        if ireq and 'name=ad_load' in l and 'ad_format=interstitial' in l and 'interReq->load' not in row:
            row['interReq->load'] = round((t(l) - ireq).total_seconds(), 2)
        if 'show' not in row and re.search(r'Displayed \S+', l) and 'Splash' not in l:
            row['show'] = round((t(l) - st).total_seconds(), 2)
    if row:
        print(' ', row)
