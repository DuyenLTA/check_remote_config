# Cách đo từng case (đã làm thật trên LingoSpeak 1.9.0, 09–13/10/2026)

Checklist gốc nằm cạnh file này (`checklist-muc*.txt`). File này ghi **đo bằng gì, chấm thế nào, bẫy đã gặp**.
`$SK` = `<repo check_remote_config>/sdk-check`. `python3` dưới đây: Windows gõ `python`. Log luôn là `adb logcat -v threadtime`.

## Mục 1 · SDK / bản build (8 dòng)

| # | Đo | Chấm |
|---|---|---|
| 1 Không còn SDK cũ | grep log `FOR_TESTER_CONFIG` (10 lần mở lạnh) + `NoClassDefFoundError|ClassNotFoundException|NoSuchMethodError`; soi APK: không có `play-services-ads.properties`, có `ads-mobile-sdk.properties` | Bản release tắt log tester (0 dòng FOR_TESTER) → chấm qua APK: không `play-services-ads.properties` + 0 lỗi thiếu lớp = **Khớp** (user chốt 15/10) |
| 2 minSdk | `dumpsys package <demo> | grep minSdk` của app demo lib ads (`com.apero.moduleads`) và SDK tutorial (`com.apero.tutorialsdk.sample`) | **Chỉ chấm lib ads + SDK (24)**. minSdk của app (vd 26) kệ, chỉ ghi tham khảo |
| 3 Thứ tự khởi tạo | tag `AperoAdmob`: `runWhenReady … queued (n)` trước `MobileAds ready, run n pending` | 10/10 lần đúng thứ tự, không `UninitializedPropertyAccessException` |
| 4 Mở nhiều lần không treo | 10× force-stop + `am start -W` (TotalTime), grep `am_anr|ANR in|isn't responding|FATAL` | 0 ANR |
| 5 Adapter sẵn sàng | `AperoAdmob: Adapter name: … State: COMPLETE` | Description của Meta để trống là bình thường |
| 6 Bản release R8 | không cờ debuggable, tên lớp bị rút gọn; hiện đủ inter/native/app open/banner/rewarded | 0 crash |
| 7 Preload native tự viết | `track_ad_request` trước khi vào màn; `ad_show` vài ms sau `*_view` | |
| 8 Compose + app demo | `dumpsys activity <pkg>` thấy ComposeView phủ màn; banner hiện; chạy từng nút app demo | |

### Log `FOR_TESTER_*` của lib ads (đọc từ dex app demo `com.apero.moduleads`, 13/10/2026)

Tag: `FOR_TESTER_CONFIG`, `FOR_TESTER_LOAD_AD`, `FOR_TESTER_SHOW_AD`, `FOR_TESTER_KEY_WORD`, `FOR_TESTER_PRELOAD`, `FOR_TESTER_LOAD_FAILURE`.

- Mọi log FOR_TESTER chỉ in khi app gọi `AdSdk.setShowMessageTester(true)`. Bản release thường tắt cờ này → **không có dòng FOR_TESTER nào** (LingoSpeak 1.9.0 có chuỗi trong dex nhưng không in ra). Muốn đo thì dùng app demo hoặc bản dev bật cờ.
- `FOR_TESTER_LOAD_FAILURE` (`Log.e`): in trong `onAdFailedToLoad` của SDK Next-Gen, qua `AdDebugLogger.logLoadFailed(adType, adUnit, message)`. Format: `<ADTYPE> - <adUnitId> - <LoadAdError.message>`.
  - Có: INTERSTITIAL (`Admob$2`), REWARDED (`Admob$19/$20`), REWARDED_INTERSTITIAL (`Admob$21`), APP_OPEN (`AppOpenManager$3/$4/$5`).
  - **Không có: NATIVE, BANNER** (không có chỗ gọi). Checklist đòi log fail cho mọi format thì native/banner thiếu = bug lib (dev thêm được).
  - Muốn thấy log phải để SDK load fail thật: proxy trễ ≥10 s (SDK timeout), ad unit sai, hoặc lúc no-fill. ID test luôn fill → không ra.
  - Tắt hẳn mạng có thể **không** ra: lib chặn request trước khi gọi SDK ("failing ad request fast"), không qua `onAdFailedToLoad` (chưa đo, suy từ code).
- Cách tự dò lại khi lib đổi bản: `unzip` lấy `classes*.dex`, `grep -a -o "FOR_TESTER[A-Z_]*"` để biết dex nào chứa, `dexdump -d` dex đó, tìm `logLoadFailed` + `invoke` để ra nơi gọi và `AdType;.<X>` để ra format.

## Mục 2 · Hiển thị HT-01 → HT-11

- HT-01 banner splash: chụp liên tục `adb exec-out screencap` (không có ffmpeg) + ghép montage bằng PIL. Có mạng: ô xám → banner; mất mạng (`svc wifi disable; svc data disable`): không ô banner.
- HT-02: đo bounds view banner = 1080. Splash/Main khoá dọc → bước xoay ngang không làm được, ghi rõ.
- HT-03 inter: bấm Learn More → Chrome → BACK về inter → X. **X ở góc phải (1032,214) hoặc trái (80,210) tuỳ creative**; bấm trượt vào video thì video dừng, X biến mất → bấm Play cho chạy hết.
- HT-04 app open: ở Language bấm Home rồi mở lại (lần 1 load, lần 2 hiện). Log tag là `AppResumeManager: app open ad impression`, **không có tag AppOpenManager**. Đóng bằng "Continue to app" (1008,196).
- **EV-25 (chuỗi event app open) cũng đo trong luồng tutorial**, cùng lượt với HT-04. App open/resume **chỉ có ở luồng tutorial**, Home sau FO nằm ngoài phạm vi (user chốt 29/10/2026). Tool tự chấm EV-25 bằng lượt Home → mở lại nên ra `SAI` "không có chuỗi event app open" → **không tin**: đo lại ở Language/OB rồi `--cham-tay` EV-25 theo log thật.
- HT-05: Home khi inter splash đang hiện → mở lại → `dumpsys activity activities | grep -c 'Hist.*AdActivity'` = 1.
- HT-06: cây view native (ad_headline, ad_media, ad_call_to_action…) + AdMob native validator ("0 implementation issues"). Layout không có icon thì không chấm thiếu icon.
- HT-07 native video: cần creative video (MediaView có TextureView/SurfaceView). Test ad thường là ảnh tĩnh; **quảng cáo thật có thể ra video** (13/10 onboarding ra native video Loora).
- HT-08/HT-10: native trong danh sách / vào-ra 20 lần + PSS (`dumpsys meminfo`) — chỉ có trong app → ngoài phạm vi tutorial.
- HT-09 native toàn màn (OB): `btnTimeoutSkip`/`btnSkip`. Hay no-fill → chạy nhiều lượt user mới.
- HT-11 user đã mua: mua sub test (xem memory mua sub), mở lạnh, đếm `track_ad_request`. Log billing tag `PurchaseEG` (`verifyPurchased SUBS code:-1` = mất kết nối billing).

## Mục 3 · Event EV-01 → EV-27 (chấm bằng log FA, không cần DebugView)

1. `adb shell setprop debug.firebase.analytics.app <pkg>`; `setprop log.tag.FA VERBOSE`; `setprop log.tag.FA-SVC VERBOSE`.
2. Capture logcat, lái app, rồi:
   `python3 -I $SK/scripts/parse_fa_events.py log.txt ev.json && python3 -I $SK/scripts/summarize_ad_events.py ev.json [--skip HH:MM:SS HH:MM:SS]`
3. Đọc: thiếu param, matched/load, show↔paid cùng unit, value = valuemicros/1e6, won vs ad_source, click.

Bẫy: **logcat có thể làm rơi dòng `FA-SVC Logging event`** (chatty) → parse thấy "thiếu paid" nhưng event vẫn lên server. Trước khi chấm thiếu event, tìm `name: <event>` trong gói upload `FA-SVC` (khối `param { name: … }` vài trăm ms sau) — Fravix 15/10: inter paid tưởng mất, thực ra có trong upload. `Param value can't be null: ad_source_unit_id` chỉ làm rơi param đó, không rơi event. `ad_show` banner có thể ghi **sai ad unit** so với ad_load/paid (EV-05) và bắn `ad_show failed ERROR_VIEW` trước khi banner load (EV-06) — so từng unit, đừng chỉ đếm. App open resume phải đủ `track_ad_request → matched → ad_load → ad_show → paid` + `event_user_click_ads` khi bấm (EV-25; bản 12/10 thiếu, bản 13/10 đủ). Offline: app chặn request ("no internet, failing ad request fast") nên **không có ad_load failed** — không phải bug nếu checklist ghi vậy (EV-21/24).

## Mục 4 · Next-Gen KT / MED / CMP / EV-30..32 / HV / RG

- **KT-01 không mạng**: tắt wifi+data, `pm clear`, mở → splash phải sang màn kế (~3 s). Log `AperoAdmob: MobileAds ready but no internet`. Bật mạng lại, đi tiếp, xem ad màn sau có `ad_load success`.
- **KT-02 mạng chậm**: `slow_ads_proxy.py 8899 3 8` (mọi host). Đo `launch_stage_timing.py`. App không khai `splash_timeout` thì mốc là **60 s tổng inter splash** (spec "logic preload publishing"). Chạy cùng điều kiện trên bản cũ để so (bản cũ 1.7.0 bị cắt đúng 60,006 s).
- **KT-03/04 Android 7 / 6**: chấm theo minSdk lib ads + SDK (24). Không có máy/emulator (máy không KVM) → đọc manifest.
- **KT-05/06 UMP**: tag `AdsConsentManager`. `3: Publisher misconfiguration … no form(s) configured` = **tài khoản AdMob chưa có form → không phải bug dev**, đưa ra mục không tính. Ép EEA cần dev bật debug geography.
- **KT-07 cài đè**: bản cũ đi FO tới Home → `adb install -r <new.apk>` → mở. Đúng nếu: request unit `_o_` (vd `splash_inter_high_o_id`), 0 lần mở Language/Onboarding, không crash. Vào Question thay vì Home là đúng khi `enable_ob1_old_screen=true`; inter thay vì native 106 là đúng khi `inter_native_change=false`.
- **MED-01**: dòng `Adapter name … State` (bản cũ để so). APK có thể gói thêm adapter (AppLovin, Mintegral, Pangle, Vungle) mà không khởi tạo — danh sách khởi tạo theo cấu hình mediation AdMob, so với bản cũ.
- **MED-02**: Ad Inspector cần **lắc máy** (adb không giả lập) → nhờ user lắc, hoặc chấm bằng `won_ad_source`/`non_won_ad_source` của ad_load + `FacebookMediationAdapter: No fill / Ad was re-loaded too frequently` (Meta rate-limit, không phải lỗi adapter).
- **CMP-01/02**: cài bản cũ (thường ở `~/.cache/ad-checklist-diff/<pkg>-<versionCode>.apk`), `drive-fo-to-home.sh` → log cũ; gỡ, cài bản mới, chạy y hệt → `compare_ad_requests.py old.txt new.txt`. Chênh ±1 sau no-fill = thử lại, không phải xin trùng.
- **CMP-03**: mỗi bản gỡ+cài, 3 lần mở lạnh, rồi đo thêm 3 lần (xen kẽ 2 bản). `launch_stage_timing.py`. Bỏ lần đầu sau cài. Nếu chỉ chênh ở `interReq->load` (cùng 1 unit, 1 request) thì là thời gian SDK Google/server → **dev không sửa được bằng code** → hỏi user có tính không.
- **EV-30**: cần quảng cáo **thật** (không nhãn "Test Ad"); native thật có thể xuất hiện ngay trên máy test. Kiểm `valuemicros>0`, `currency`, `value = valuemicros/1e6`.
- **EV-31**: `summarize_ad_events.py` dòng "won_ad_source vs ad_source mismatches".
- **EV-32**: tag `AperoAppsflyer: pushTrackEventAdmob enableAppsflyer:false|true` và `AdSdkAdjust: Event success callback` — đếm 1:1 với `paid_ad_impression`.
- **HV-01**: bấm inter/native → Chrome → Home → mở lại: không có `…app open unit` request/show. Banner splash chỉ hiện <0,5 s trước khung "Loading Ads…" → không bấm được.
- **HV-02**: đóng inter bằng X → đứng 10 s, không app open. Rewarded chỉ có in-app.
- **HV-06**: Back lúc inter còn đếm ngược vs lúc X đã hiện, **so với bản cũ cùng thời điểm** (cả hai: chặn khi đếm ngược, đóng khi có X). Chụp màn trước khi Back để biết X đã hiện chưa.
- **HV-07**: proxy chỉ làm chậm domain ads, trễ **6 s** (≥10 s thì SDK timeout, ad không "về muộn"). Ở Question (có request inter) bấm Next → paywall → đóng → Home; inter `ad_load success _sc=MainActivity` mà không `ad_show` = Khớp.
- **HV-08**: Home đúng lúc khung "Loading Ads…" (chờ log `InterstitialAds onAdLoaded` rồi HOME ngay) → log `show fail in background after show loading ad`, mở lại không chồng quảng cáo.
- **HV-05/09**: kiểm RC + log `ad_format` / `collapsible=` — không có thì đưa vào mục không áp dụng.
- **RG-01 (36 TC "TC SDK 3.5.0")**: 34/36 cần đổi RC → bản **debuggable** (`run-as`) hoặc máy root: chạy `/rc-check <pkg> --tc <bộ TC> --sdk 3.5.0`, lấy PASS/FAIL report đó; bản release thì đưa vào mục "Cần bản debuggable". Đọc RC thật: `fetch_remote_config.py`.

## Bẫy chung

- Sub test còn hạn làm app bỏ paywall / ẩn ads → kiểm `play.google.com/store/account/subscriptions` (trang có lúc "Server error", thử link có `?sku=&package=`).
- Bản mới có thể hỏi quyền thông báo trước splash → `pm grant <pkg> android.permission.POST_NOTIFICATIONS` sau `pm clear`.
- **Popup "AdMob native ad validator"** (chỉ máy test + native test) nổi đè lên nút của app (vd "Get Started" OB4): bấm nút mà trúng popup → mở trang validator (AdActivity), nhìn như native che nút. KHÔNG phải bug app. **Đừng chạm vào popup, kể cả nút "Dismiss" hay "What is this?"**: trên OPPO, bấm Dismiss qua adb không tắt được popup mà lại mở trang validator (AIP882, 29/10/2026). Mỗi lần native refresh lại chồng thêm một popup. Hãy bấm vào phần nút của app không bị che (`tap-by-id.sh '<id>' right`, tức mép phải nút). Lỡ mở trang validator thì `close-ad.sh` đóng bằng `custom-close`. Kiểm bằng screencap trước khi kết luận "native che nút" (HT-06).
- Tap nhầm vào native → mở Chrome/validator → BACK. Tap toạ độ đáy màn khi có thanh điều hướng = bấm Home/Recents.
- Native hay no-fill sau nhiều lần mở liên tục → chờ rồi chạy lại, đừng kết luận app lỗi.
- Luôn gỡ proxy: `settings put global http_proxy :0; adb reverse --remove-all`.
