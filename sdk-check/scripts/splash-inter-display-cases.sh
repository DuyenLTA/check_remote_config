#!/bin/bash
export MSYS_NO_PATHCONV=1  # Git Bash: keep /sdcard/... paths for adb as-is
# Old-user display cases on the splash inter + resume ad, one logcat file:
#  HT-03 click CTA -> landing -> BACK -> X ; HV-02 wait 10 s after X ; HT-05 Home while inter shows -> reopen x2 ;
#  HT-04/EV-25 Home + reopen twice (resume ad) ; HV-01 return from inter landing.
# usage: splash-inter-display-cases.sh <package> <out-dir>   (writes log-DISP.txt, marks-DISP.txt, disp-*.png)
P=$1; O=${2:-.}; cd "$O" || exit 1
D=$(cd "$(dirname "$0")" && pwd)
top() { adb shell dumpsys activity activities | grep -m1 -E "topResumedActivity|mResumedActivity" | grep -oE '/[a-zA-Z.0-9_$]+' | tail -1; }
M=marks-DISP.txt; mark() { echo "$1 $(date +%T.%N | cut -c1-12)" >> $M; echo "$1 $(date +%T) $(top)"; }
stack() { adb shell dumpsys activity activities | grep -E '^ +\* Hist +#' | grep "$P" | grep -c AdActivity; }
close_ad() { bash $D/close-ad.sh 30 >/dev/null; }  # only the ad's own close button, no blind taps / BACK
launch_until_ad() { adb shell am force-stop $P; sleep 1; adb shell monkey -p $P -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1
  for k in $(seq 1 40); do sleep 0.5; case "$(top)" in *AdActivity*) return 0 ;; *Language*|*Main*|*Question*|*Onboarding*) return 1 ;; esac; done; return 1; }
adb logcat -v threadtime -T 1 > log-DISP.txt & LC=$!
# HT-03 + HV-01(inter) + HV-02
for t in $(seq 1 10); do launch_until_ad && break; done
mark inter_up; sleep 3
bash $D/tap-by-id.sh 'Learn More|Install|Open|OPEN|Tìm Hiểu' || adb shell input tap 540 1950
mark inter_click; sleep 4; mark after_click
adb shell input keyevent BACK; sleep 3; mark back_from_landing; adb exec-out screencap -p > disp-ht03-back.png
sleep 2; close_ad; mark inter_x; sleep 10; mark hv02_10s
# HT-05 x2
for r in 1 2; do
  for t in $(seq 1 10); do launch_until_ad && break; done; sleep 2; adb shell input keyevent HOME; mark ht05_home$r; sleep 5
  adb shell monkey -p $P -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1; sleep 5
  mark "ht05_reopen$r stack=$(stack)"; sleep 6; close_ad; mark "ht05_closed$r stack=$(stack)"
done
# HT-04 / EV-25: background twice from the screen we are on
for r in 1 2 3; do
  adb shell input keyevent HOME; mark resume_home$r; sleep 5
  adb shell monkey -p $P -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1; sleep 5; mark "resume_reopen$r"
  case "$(top)" in *AdActivity*) adb exec-out screencap -p > disp-resume$r.png; sleep 5; close_ad; mark resume_closed$r ;; esac
done
sleep 3; kill $LC
