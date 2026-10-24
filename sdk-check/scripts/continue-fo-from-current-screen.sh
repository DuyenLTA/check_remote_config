#!/bin/bash
export MSYS_NO_PATHCONV=1  # Git Bash: keep /sdcard/... paths for adb as-is
# Continue a VslTemplate4 first-open flow from whatever screen is showing (no force-stop, no clear),
# e.g. after re-enabling network mid-flow (KT-01). Stops at Home, or at the screen named by $2.
# usage: continue-fo-from-current-screen.sh <marks-file> [stop-at-regex e.g. 'Onboarding|Question']
D=$(cd "$(dirname "$0")" && pwd)
M=${1:-marks-continue.txt}; STOP=$2
top() { adb shell dumpsys activity activities | grep -m1 -E "topResumedActivity|mResumedActivity" | grep -oE '/[a-zA-Z.0-9_$]+' | tail -1; }
mark() { echo "$1 $(date +%T.%N | cut -c1-12)" >> "$M"; echo "$1 $(date +%T)"; }
lang_step=0; skip_n=0
for step in $(seq 1 60); do
  sleep 2
  a=$(top)
  [ -n "$STOP" ] && echo "$a" | grep -qE "$STOP" && { mark "stop_at_$a"; exit 0; }
  case $a in
    *AdActivity*)
      sleep 6
      bash "$D/tap-by-id.sh" 'dismiss-button' >/dev/null; sleep 1.5
      for xy in "1031 83" "1032 214" "80 210" "1008 196"; do [ "$(top)" != "$a" ] && break; adb shell input tap $xy; sleep 1.5; done
      # no BACK on a real ad: on Sorapix 1.6.0 (24/10/2026) BACK on the splash inter logged 2 ad_click; retry next loop instead
      mark ad_closed ;;
    *Language*)
      case $lang_step in
        0) bash "$D/tap-by-id.sh" 'English$' >/dev/null && lang_step=1 ;;
        1) bash "$D/tap-by-id.sh" 'English \(US\)' >/dev/null; lang_step=2 ;;
        *) bash "$D/tap-by-id.sh" 'buttonLanguageNext|imageButtonLanguageNext' >/dev/null && mark lang_next ;;
      esac ;;
    *Onboarding*)
      bash "$D/dismiss-native-validator.sh" >/dev/null
      if bash "$D/tap-by-id.sh" 'btnTimeoutSkip|btnSkip' >/dev/null; then :
      else bash "$D/tap-by-id.sh" 'btnNextOnboarding|Next' right >/dev/null; fi ;;
    *Question*)
      bash "$D/dismiss-native-validator.sh" >/dev/null
      # pick an item only when no Next button yet (tapping a selected item unselects it and hides Next)
      bash "$D/tap-by-id.sh" 'btnNextQuestion|btnNextOnboardingImage' right >/dev/null && { mark q_next; continue; }
      bash "$D/tap-by-id.sh" 'tvQuestionTitle|ivQuestion|itemQuestion' >/dev/null; sleep 0.8
      bash "$D/tap-by-id.sh" 'btnNextQuestion|btnNextOnboardingImage|Next|Continue|Go to Home' right >/dev/null && mark q_next ;;
    *Billing*)
      sleep 2; bash "$D/tap-by-id.sh" 'Close Billing Screen|ivClose|btnClose' >/dev/null || adb shell input tap 100 130; mark billing_close ;;
    *MainActivity*) mark at_home; exit 0 ;;
    *chrome*|*Launcher*) adb shell input keyevent BACK ;;
  esac
done
mark continue_timeout; exit 1
