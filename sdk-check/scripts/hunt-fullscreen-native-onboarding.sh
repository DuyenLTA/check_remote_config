#!/bin/bash
export MSYS_NO_PATHCONV=1  # Git Bash: keep /sdcard/... paths for adb as-is
# HT-09 / HV-06(native): repeat new-user runs until the onboarding full-screen native actually fills,
# then screenshot it, dump its views and test Back. Fill is low on test devices, so try up to N runs.
# usage: hunt-fullscreen-native-onboarding.sh <package> <out-dir> [max-runs=4]
P=$1; O=${2:-.}; N=${3:-4}; cd "$O" || exit 1
D=$(cd "$(dirname "$0")" && pwd)
top() { adb shell dumpsys activity activities | grep -m1 -E "topResumedActivity|mResumedActivity" | grep -oE '/[a-zA-Z.0-9_$]+' | tail -1; }
for run in $(seq 1 $N); do
  :
  adb shell am force-stop $P; adb shell pm clear $P >/dev/null; adb shell pm grant $P android.permission.POST_NOTIFICATIONS
  adb shell monkey -p $P -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1
  timeout 120 bash $D/continue-fo-from-current-screen.sh marks-HUNT.txt 'Onboarding' >/dev/null
  for i in $(seq 1 16); do
    sleep 1.5
    x=$(adb shell uiautomator dump /sdcard/u.xml >/dev/null; adb shell cat /sdcard/u.xml)
    if echo "$x" | grep -qE 'btnTimeoutSkip|btnSkip' && echo "$x" | grep -q 'ad_headline'; then
      echo "run $run: FULLSCREEN NATIVE FILLED $(date +%T)"
      adb exec-out screencap -p > hunt-full.png; bash $D/ui-dump.sh > hunt-full-dump.txt
      adb logcat -d -v threadtime > log-HUNT.txt
      adb shell input keyevent BACK; sleep 2; echo "after BACK: $(top)" | tee hunt-back.txt
      exit 0
    fi
    echo "$x" | grep -qE 'Get Started|Start Now|Continue' && break
    bash $D/tap-by-id.sh btnNextOnboarding right >/dev/null
  done
  echo "run $run: no filled full-screen native"
done
exit 1
