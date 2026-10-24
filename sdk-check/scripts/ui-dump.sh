#!/bin/bash
export MSYS_NO_PATHCONV=1  # Git Bash: keep /sdcard/... paths for adb as-is
PY=$(python3 -c "" >/dev/null 2>&1 && echo python3 || echo python)  # Windows python3 is a Store stub
# Dump the current screen: "x,y 'text' 'content-desc' resource-id" for every labelled/clickable node,
# then the top resumed activity. Use it to find buttons instead of guessing coordinates.
adb shell uiautomator dump /sdcard/u.xml >/dev/null 2>&1
adb shell cat /sdcard/u.xml | $PY -c "
import sys,re
x=sys.stdin.read()
for m in re.finditer(r'<node [^>]*>',x):
  n=m.group(0); g=lambda k:(re.search(k+'=\"([^\"]*)\"',n) or [None,''])[1]
  t,d,r,b=g('text'),g('content-desc'),g('resource-id').split('/')[-1],g('bounds')
  if t or d or (g('clickable')=='true' and r):
    a=list(map(int,re.findall(r'\d+',b))); print(f'{(a[0]+a[2])//2},{(a[1]+a[3])//2}',repr(t)[:50],repr(d)[:30],r)
"
adb shell dumpsys activity activities | grep -m1 -E "topResumedActivity|mResumedActivity"
