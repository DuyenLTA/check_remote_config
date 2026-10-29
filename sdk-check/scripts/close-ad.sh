#!/bin/bash
export MSYS_NO_PATHCONV=1  # Git Bash: keep /sdcard/... paths for adb as-is
PY=$(python3 -c "" >/dev/null 2>&1 && echo python3 || echo python)  # Windows python3 is a Store stub
# Close a full-screen ad (AdActivity) by tapping ITS close button only - never blind coordinates, never BACK.
# The whole ad is one WebView: any tap outside the close button is a click on the ad (24/10/2026, Sorapix:
# old fallback taps at (1031,83)/(1032,214) landed on the creative). The close button is exposed in the
# uiautomator tree once the WebView builds its accessibility nodes: resource-id `dismiss-button` (GMA web
# creatives, label "Đóng"/"Close") or a node whose text/desc is a close word. Tap the centre of its text
# label, not the node centre: on Sorapix a "More" node overlapped the right half of `dismiss-button`.
# usage: close-ad.sh [max-wait-s=30]   exit 0 = left AdActivity, 1 = close button not found (nothing tapped)
WAIT=${1:-30}
top() { adb shell dumpsys activity activities | grep -m1 -E "topResumedActivity|mResumedActivity" | grep -oE '/[a-zA-Z.0-9_$]+' | tail -1; }
# The first dump only primes the WebView accessibility tree (it comes back as one empty WebView,
# 24/10/2026): do it right away so the real dump at ~5 s already sees the close button. Test ads log
# 2 ad_click by themselves ~10 s after showing, so the ad must be closed before that.
t0=$(date +%s)
adb shell uiautomator dump /sdcard/u.xml >/dev/null 2>&1
rest=$(( 5 - ($(date +%s) - t0) )); [ "$rest" -gt 0 ] && sleep "$rest"  # close button is active after ~5 s
end=$(( $(date +%s) + WAIT ))
while [ "$(date +%s)" -lt "$end" ]; do
  case "$(top)" in *AdActivity*) ;; *) exit 0 ;; esac
  adb shell uiautomator dump /sdcard/u.xml >/dev/null 2>&1
  xy=$(adb shell cat /sdcard/u.xml | $PY -c "
import re, sys
x = sys.stdin.buffer.read().decode('utf-8', 'replace')
nodes = re.findall(r'<node [^>]*>', x)
g = lambda n, k: (re.search(k + r'=\"([^\"]*)\"', n) or [None, ''])[1]
box = lambda n: list(map(int, re.findall(r'\d+', g(n, 'bounds'))))
CLOSE = re.compile(r'^(close|close ad|đóng|skip|skip ad|bỏ qua|continue to app|tiếp tục.*ứng dụng|interstitial close button|×|x)$', re.I)
def inside(a, b):
    return a[0] >= b[0] and a[1] >= b[1] and a[2] <= b[2] and a[3] <= b[3]
hit = None
# custom-close: X of the AdMob native ad validator page (test device + native test ad), opened when a
# tap lands on a native; it is an AdActivity too (AIP882 4.3.0 OPPO 29/10/2026: FO looped 'close_not_found' 11 min)
for n in nodes:
    if g(n, 'resource-id').split('/')[-1] in ('dismiss-button', 'custom-close'):
        hit = box(n); break
if hit is None:
    for n in nodes:
        if CLOSE.match(g(n, 'text').strip()) or CLOSE.match(g(n, 'content-desc').strip()):
            hit = box(n); break
if hit is None and nodes:
    # Icon-only X (AIP882 4.3.0 OPPO 29/10/2026: GMA next-gen web creative, no id, no label - only a square
    # View holding an Image at the top-right corner; the script looped 'close_not_found' for 10 min).
    # Accept only a small square in the top-right corner that wraps an Image: never a creative area.
    W = max(box(n)[2] for n in nodes if box(n)); H = max(box(n)[3] for n in nodes if box(n))
    imgs = [box(n) for n in nodes if g(n, 'class') == 'android.widget.Image' and box(n)]
    for n in nodes:
        b = box(n)
        if len(b) != 4: continue
        w, h = b[2] - b[0], b[3] - b[1]
        if 32 <= w <= 100 and abs(w - h) <= 16 and b[1] < H * 0.2 and b[2] >= W * 0.85 \
           and not g(n, 'content-desc') and any(inside(i, b) for i in imgs):
            hit = b; break
if hit and hit[2] > hit[0] and hit[3] > hit[1]:
    # prefer the close word's own text node inside the button (stays clear of overlapping CTA nodes)
    lab = [box(n) for n in nodes if CLOSE.match(g(n, 'text').strip()) and inside(box(n), hit)]
    b = lab[0] if lab else hit
    print((b[0] + b[2]) // 2, (b[1] + b[3]) // 2)
")
  if [ -n "$xy" ]; then
    adb shell input tap $xy; echo "close @ $xy"; sleep 1
    case "$(top)" in *AdActivity*) ;; *) exit 0 ;; esac
  fi
  sleep 0.5
done
echo "close button not found in ${WAIT}s - nothing tapped"; exit 1
