"""Read the LIVE Firebase Remote Config of a release app (no run-as / root needed).

usage: python3 -I fetch_remote_config.py <app.apk> <out.json> [country=VN] [appVersion]
Reads google_app_id / google_api_key / project_id / gcm_defaultSenderId from the APK resources
(aapt2), creates a throw-away Firebase installation, then calls the RC fetch REST endpoint.
Read-only: it cannot change RC. Values of keys that look like credentials are masked in stdout
(still present in out.json - keep that file in the scratchpad, never publish it). Conditions on user properties may differ from the real device.
"""
import base64
import json
import os
import re
import subprocess
import sys
import urllib.request



def find_aapt2():
    """Newest build-tools aapt2 under $ANDROID_HOME / $ANDROID_SDK_ROOT or the default SDK dir of Linux, macOS, Windows."""
    roots = [os.environ.get('ANDROID_HOME'), os.environ.get('ANDROID_SDK_ROOT'), '~/Android/Sdk',
             '~/Library/Android/sdk', '~/AppData/Local/Android/Sdk']
    for root in filter(None, roots):
        bt = os.path.join(os.path.expanduser(root), 'build-tools')
        for ver in sorted(os.listdir(bt), key=lambda v: [int(x) if x.isdigit() else 0 for x in v.split('.')],
                          reverse=True) if os.path.isdir(bt) else []:
            for name in ('aapt2', 'aapt2.exe'):
                if os.path.isfile(os.path.join(bt, ver, name)):
                    return os.path.join(bt, ver, name)
    sys.exit('aapt2 not found: install Android SDK build-tools or set ANDROID_HOME')


AAPT2 = find_aapt2()
apk, out = sys.argv[1], sys.argv[2]
country = sys.argv[3] if len(sys.argv) > 3 else 'VN'

# utf-8 explicitly: on Windows the default codepage cannot decode non-ASCII resource strings, the reader thread
# dies and .stdout comes back None
res = subprocess.run([AAPT2, 'dump', 'resources', apk], capture_output=True, encoding='utf-8', errors='replace').stdout
badge = subprocess.run([AAPT2, 'dump', 'badging', apk], capture_output=True, encoding='utf-8', errors='replace').stdout
pkg = re.search(r"package: name='([^']+)'", badge).group(1)
ver = sys.argv[4] if len(sys.argv) > 4 else re.search(r"versionName='([^']+)'", badge).group(1)


def string(name):
    m = re.search(r'string/' + name + r'\b.*?\n\s*\(\)\s*"([^"]+)"', res, re.S)
    return m.group(1)


app_id, api_key, project_id = string('google_app_id'), string('google_api_key'), string('project_id')
number = app_id.split(':')[1]


def post(url, body, headers):
    req = urllib.request.Request(url, json.dumps(body).encode(), {'Content-Type': 'application/json', **headers})
    return json.load(urllib.request.urlopen(req, timeout=20))


fid = base64.urlsafe_b64encode(bytes([0x70 | (os.urandom(1)[0] & 0x0f)]) + os.urandom(16)).decode()[:22]
inst = post(f'https://firebaseinstallations.googleapis.com/v1/projects/{project_id}/installations',
            {'fid': fid, 'appId': app_id, 'authVersion': 'FIS_v2', 'sdkVersion': 'a:17.0.0'},
            {'x-goog-api-key': api_key, 'X-Android-Package': pkg})
tok = inst['authToken']['token']
rc = post(f'https://firebaseremoteconfig.googleapis.com/v1/projects/{number}/namespaces/firebase:fetch?key={api_key}',
          {'appInstanceId': inst['fid'], 'appInstanceIdToken': tok, 'appId': app_id, 'countryCode': country,
           'languageCode': 'en-US', 'platformVersion': '36', 'timeZone': 'Asia/Bangkok', 'appVersion': ver,
           'packageName': pkg, 'sdkVersion': '22.0.0', 'analyticsUserProperties': {}},
          {'X-Android-Package': pkg, 'X-Goog-Firebase-Installations-Auth': tok})
json.dump(rc, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
entries = rc.get('entries', {})
print(pkg, ver, 'state', rc.get('state'), len(entries), 'keys')
SECRET = re.compile(r'key|token|secret|password', re.I)
for k in sorted(entries):
    v = '***' if SECRET.search(k) else entries[k][:100]  # never echo credentials stored in RC
    print(f'{k} = {v}')
