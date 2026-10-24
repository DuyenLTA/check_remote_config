#!/bin/bash
export MSYS_NO_PATHCONV=1  # Git Bash: keep /sdcard/... paths for adb as-is
# Cold start as a NEW user (pm clear unless "keep") and wait until the app leaves Splash.
# Prints "<seconds since launch> <activity>" each second. Marks the launch in <marks-file>.
# usage: cold-start-new-user.sh <package> <marks-file> [keep]
P=$1; M=${2:-marks.txt}
adb shell am force-stop "$P"; adb shell am force-stop com.android.chrome; adb shell am force-stop com.android.vending
[ "$3" = keep ] || { adb shell pm clear "$P" >/dev/null; adb shell pm grant "$P" android.permission.POST_NOTIFICATIONS 2>/dev/null; }
adb shell input keyevent HOME; sleep 1
adb shell monkey -p "$P" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1
T0=$(date +%s.%N); echo "launch $(date +%T.%N | cut -c1-12)" >> "$M"
for i in $(seq 1 60); do
  sleep 1
  a=$(adb shell dumpsys activity activities | grep -m1 -E "topResumedActivity|mResumedActivity" | grep -oE '/[a-zA-Z.0-9_$]+' | tail -1)
  awk -v a="$(date +%s.%N)" -v b="$T0" -v s="$a" 'BEGIN{printf "%.1fs %s\n", a-b, s}'
  case $a in *Splash*|*permission*) ;; *) break ;; esac
done
