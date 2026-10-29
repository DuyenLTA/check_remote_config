#!/bin/bash
export MSYS_NO_PATHCONV=1  # Git Bash: keep /sdcard/... paths for adb as-is
PY=$(python3 -c "" >/dev/null 2>&1 && echo python3 || echo python)  # Windows python3 is a Store stub
# Close an in-app paywall whose X has no id/text (e.g. RevenueCat Compose paywall, AIP918 2.4.0:
# unlabelled clickable View at [60,140][204,284]). Taps the centre of the first clickable node that sits
# fully in the top-left corner (x < 40% width, y < 15% height). Never taps blind coordinates.
# usage: close-paywall-top-left.sh   exit 0 = tapped, 1 = no such node
adb shell uiautomator dump /sdcard/u.xml >/dev/null 2>&1
xy=$(adb shell cat /sdcard/u.xml | $PY -c "
import sys,re
x=sys.stdin.buffer.read().decode('utf-8','replace')
for n in re.findall(r'<node [^>]*>',x):
  g=lambda k:(re.search(k+'=\"([^\"]*)\"',n) or [None,''])[1]
  a=list(map(int,re.findall(r'\d+',g('bounds'))))
  if g('clickable')=='true' and a[2]<=432 and a[3]<=360 and a[2]>a[0]:
    print((a[0]+a[2])//2,(a[1]+a[3])//2); break
")
[ -z "$xy" ] && exit 1
adb shell input tap $xy; echo "paywall close @ $xy"
