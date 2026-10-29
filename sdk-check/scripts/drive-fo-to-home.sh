#!/bin/bash
export MSYS_NO_PATHCONV=1  # Git Bash: keep /sdcard/... paths for adb as-is
# Drive a VslTemplate4 tutorial first-open flow to Home the same way on any build:
# Splash -> (inter) -> Language -> Onboarding (incl. full-screen native) -> Question -> Billing -> Home.
# Buttons are found by resource-id of the tutorial SDK, so it works across apps on that template.
# Prints/marks one line per step; waits 15 s at Home. Use the same script on old and new build (CMP-01/02).
# usage: drive-fo-to-home.sh <package> <marks-file> [noclear]
D=$(cd "$(dirname "$0")" && pwd)
P=$1; M=${2:-marks-fo.txt}
top() { adb shell dumpsys activity activities | grep -m1 -E "topResumedActivity|mResumedActivity" | grep -oE '/[a-zA-Z.0-9_$]+' | tail -1; }
mark() { echo "$1 $(date +%T.%N | cut -c1-12)" >> "$M"; echo "$1 $(date +%T)"; }
tap() { bash "$D/tap-by-id.sh" "$1" >/dev/null; }

adb shell am force-stop "$P"
[ "$3" = noclear ] || { adb shell pm clear "$P" >/dev/null; adb shell pm grant "$P" android.permission.POST_NOTIFICATIONS 2>/dev/null; }
adb shell input keyevent HOME; sleep 1
mark fo_launch
adb shell monkey -p "$P" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1
lang_step=0; skip_n=0
for step in $(seq 1 90); do
  sleep 0.7  # notice an ad fast: test ads log ad_click by themselves ~10 s after showing
  a=$(top)
  case $a in
    *Splash*|*permission*) tap 'permission_allow_button' ;;
    *AdActivity*)
      # tap only the ad's own close button (close-ad.sh); no blind coordinates, no BACK
      bash "$D/close-ad.sh" 30 >/dev/null || mark close_not_found
      mark ad_closed ;;
    *Language*)
      # first pick a language, then its sub-variant if the list expands, then Next
      case $lang_step in
        0) tap 'English$' && lang_step=1 ;;
        1) tap 'English \(US\)' ; lang_step=2 ;;
        *) tap 'buttonLanguageNext|imageButtonLanguageNext' && mark lang_next ;;
      esac ;;
    *Onboarding*)
      # AdMob native validator popup (test devices) covers the button centre; tapping its Dismiss opens the
      # validator page on OPPO (AIP882 29/10/2026) -> never touch the popup, tap the button's right edge
      if tap 'btnTimeoutSkip|btnSkip'; then mark ob_fullscreen_skip
      else bash "$D/tap-by-id.sh" 'btnNextOnboarding|Next' right >/dev/null; fi ;;
    *Question*)
      # AdMob native validator popup (test devices) covers the button centre; tapping its Dismiss opens the
      # validator page on OPPO (AIP882 29/10/2026) -> never touch the popup, tap the button's right edge
      # pick an item only when no Next button yet (tapping a selected item unselects it and hides Next)
      bash "$D/tap-by-id.sh" 'btnNextQuestion|btnNextOnboardingImage' right >/dev/null || { tap 'tvQuestionTitle'; sleep 0.8; bash "$D/tap-by-id.sh" 'btnNextQuestion|btnNextOnboardingImage|Next|Go to Home' right >/dev/null; } && mark q_next ;;
    *Billing*)
      sleep 2; tap 'Close Billing Screen|ivClose|btnClose' || adb shell input tap 100 130; mark billing_close ;;
    *Paywall*|*revcat*)
      # RevenueCat paywall (no Billing in the name): X is an unlabelled node top-left
      sleep 1.5; bash "$D/close-paywall-top-left.sh" >/dev/null && mark paywall_close ;;
    *MainActivity*)
      mark at_home; sleep 15; mark home_wait_end; exit 0 ;;
    *Launcher*|*chrome*|*vending*)
      mark "left_app_$a"; adb shell monkey -p "$P" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1 ;;
    *) mark "unknown_$a" ;;
  esac
done
mark fo_timeout; exit 1
