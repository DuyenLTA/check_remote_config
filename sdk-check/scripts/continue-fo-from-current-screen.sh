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
      # tap only the ad's own close button (close-ad.sh); no blind coordinates, no BACK
      bash "$D/close-ad.sh" 30 >/dev/null || mark close_not_found
      mark ad_closed ;;
    *Language*)
      case $lang_step in
        0) bash "$D/tap-by-id.sh" 'English$' >/dev/null && lang_step=1 ;;
        1) bash "$D/tap-by-id.sh" 'English \(US\)' >/dev/null; lang_step=2 ;;
        *) bash "$D/tap-by-id.sh" 'buttonLanguageNext|imageButtonLanguageNext' >/dev/null && mark lang_next ;;
      esac ;;
    *Onboarding*)
      # AdMob native validator popup (test devices) covers the button centre; tapping its Dismiss opens the
      # validator page on OPPO (AIP882 29/10/2026) -> never touch the popup, tap the button's right edge
      if bash "$D/tap-by-id.sh" 'btnTimeoutSkip|btnSkip' >/dev/null; then :
      else bash "$D/tap-by-id.sh" 'btnNextOnboarding|Next' right >/dev/null; fi ;;
    *Question*)
      # AdMob native validator popup (test devices) covers the button centre; tapping its Dismiss opens the
      # validator page on OPPO (AIP882 29/10/2026) -> never touch the popup, tap the button's right edge
      # pick an item only when no Next button yet (tapping a selected item unselects it and hides Next)
      bash "$D/tap-by-id.sh" 'btnNextQuestion|btnNextOnboardingImage' right >/dev/null && { mark q_next; continue; }
      bash "$D/tap-by-id.sh" 'tvQuestionTitle|ivQuestion|itemQuestion' >/dev/null; sleep 0.8
      bash "$D/tap-by-id.sh" 'btnNextQuestion|btnNextOnboardingImage|Next|Continue|Go to Home' right >/dev/null && mark q_next ;;
    *Billing*)
      sleep 2; bash "$D/tap-by-id.sh" 'Close Billing Screen|ivClose|btnClose' >/dev/null || adb shell input tap 100 130; mark billing_close ;;
    *Paywall*|*revcat*)
      # RevenueCat paywall (no Billing in the name): X is an unlabelled node top-left
      sleep 1.5; bash "$D/close-paywall-top-left.sh" >/dev/null && mark paywall_close ;;
    *MainActivity*) mark at_home; exit 0 ;;
    *chrome*|*Launcher*) adb shell input keyevent BACK ;;
  esac
done
mark continue_timeout; exit 1
