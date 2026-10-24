#!/bin/bash
export MSYS_NO_PATHCONV=1  # Git Bash: keep /sdcard/... paths for adb as-is
PY=$(python3 -c "" >/dev/null 2>&1 && echo python3 || echo python)  # Windows python3 is a Store stub
# Tap the centre of the first node whose resource-id, text or content-desc matches $1 (regex).
# exit 1 when nothing matches. usage: tap-by-id.sh 'buttonLanguageNext|btnNext' [right]
# 'right' taps 30px inside the node's right edge: on test devices the AdMob native validator popup
# (invisible to uiautomator) covers the left/centre of onboarding Next buttons.
adb shell uiautomator dump /sdcard/u.xml >/dev/null 2>&1
xy=$(adb shell cat /sdcard/u.xml | $PY -c "
import sys,re
pat=re.compile(sys.argv[1]); x=sys.stdin.read()
nodes=[m.group(0) for m in re.finditer(r'<node [^>]*>',x)]
g=lambda n,k:(re.search(k+'=\"([^\"]*)\"',n) or [None,''])[1]
# resource-id matches win over text/desc: a hint label like 'Swipe to Next' must not beat btnNextOnboarding
for field in ('resource-id','text','content-desc'):
  hit=next((n for n in nodes if (v:=g(n,field).split('/')[-1] if field=='resource-id' else g(n,field)) and pat.search(v)),None)
  if hit:
    a=list(map(int,re.findall(r'\d+',g(hit,'bounds')))); print(a[2]-30 if sys.argv[2]=='right' else (a[0]+a[2])//2,(a[1]+a[3])//2); break
" "$1" "${2:-centre}")
[ -z "$xy" ] && exit 1
adb shell input tap $xy; echo "tap $1 @ $xy"
