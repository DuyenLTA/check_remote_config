"""Parse Firebase FA-SVC 'Logging event' lines from a logcat file into JSON.

Works with `adb logcat -v threadtime` (default) and `-v time` output, and joins wrapped lines.
Device setup before capture:
  adb shell setprop debug.firebase.analytics.app <package>
  adb shell setprop log.tag.FA VERBOSE ; adb shell setprop log.tag.FA-SVC VERBOSE
usage: python3 -I parse_fa_events.py <logcat.txt> <out.json>
Each item: {"t": "MM-DD HH:MM:SS.mmm", "origin": "app|am|auto", "name": "...", "p": {param: value}}
"""
import json
import re
import sys

THREADTIME = re.compile(r'^(\d\d-\d\d \d\d:\d\d:\d\d\.\d+)\s+\d+\s+\d+ V FA-SVC\s*: (.*)$')
TIME = re.compile(r'^(\d\d-\d\d \d\d:\d\d:\d\d\.\d+) V/FA-SVC\s*\(\s*\d+\): (.*)$')

raw = []
cur = None
for line in open(sys.argv[1], encoding='utf-8', errors='replace'):
    line = line.rstrip('\n')
    m = THREADTIME.match(line) or TIME.match(line)
    if not m:
        continue
    t, body = m.groups()
    if body.startswith('Logging event:'):
        cur = {'t': t, 'raw': body}
        raw.append(cur)
    elif cur is not None and not cur['raw'].endswith('}]') and not re.match(r'^[A-Z][a-z]+ ', body):
        cur['raw'] += body  # continuation of a long bundle split by logcat

out = []
for e in raw:
    m = re.match(r'Logging event: origin=(\w+),name=([^,]+),params=Bundle\[\{(.*)\}\]?$', e['raw'])
    if not m:
        continue
    origin, name, ps = m.groups()
    params = {}
    for kv in re.split(r', (?=[\w()]+=)', ps.rstrip('}]')):
        k, _, v = kv.partition('=')
        params[re.sub(r'\(.*\)', '', k)] = v
    out.append({'t': e['t'], 'origin': origin, 'name': re.sub(r'\(.*\)', '', name), 'p': params})

json.dump(out, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print(len(out), 'events')
