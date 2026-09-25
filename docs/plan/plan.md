---
title: "Remote Config Case Runner"
status: in-progress   # phase 1-4 xong phan loi, phase 5 dang lam (cham Expected)
created: 2026-09-07
source: docs/plan/reports/from-brainstorm-to-planner-rc-override-design-260904-1425-firebase-remote-config-testcase-runner-report.md
target_repo: ~/projects/check_remote_config
package: rcr
blockedBy: []
blocks: []
reuses: [~/projects/ui-spec-verifier (ui_dump.py, adb_client.py), ~/Downloads/Tool_test_data_app-main (remote_config.py, adb_parsers.py, report_html.py)]
---

# Remote Config Case Runner

> **Đây là bản plan duy nhất.** Nó sống trong repo, cùng lịch sử với code — mọi cập nhật
> trạng thái phase đi vào commit. Không tạo bản sao ở `./plans/` hay ngoài repo: hai bản là
> chắc chắn lệch, và bản người khác đọc lại là bản lạc hậu.

Từ **file testcase XLSX** → đổi giá trị **Firebase Remote Config** trên máy thật (không cần
quyền admin Firebase, không đụng server) → **action trên app** → chấm **PASS/FAIL** kèm
actual result.

Brainstorm + thực nghiệm đã xong (GO). Bằng chứng & số đo: xem `source` ở frontmatter.

## Phases

| # | Phase | Status | Milestone |
|---|---|---|---|
| 1 | [Skeleton + adb + baseline reader](phase-01-skeleton-adb-and-rc-baseline-reader.md) | ✅ **done** (2026-09-07) | chọn device+app → hiện số key RC, file mirror, kiểu từng key |
| 2 | [rc_patch + rc_verify](phase-02-rc-patch-and-verify-survival.md) | ✅ **done** (2026-09-08) | ⭐ đặt 1 key → mở app → **verify giá trị sống** |
| 3 | [tc_loader + rc_extract](phase-03-testcase-loader-and-rc-key-extract.md) | ✅ **done** (2026-09-09) | nạp file TC → bảng case + key/value đã parse |
| 4 | [device_reset + act_resolver](phase-04-device-reset-and-action-resolver.md) | 🟡 **đang làm** | chạy 1 case tới đúng màn cần chấm |
| 5 | [assert_dump + verdict](phase-05-assert-dump-and-verdict.md) | 🟡 **đang làm** | ⭐ chấm được case RC, ra PASS/FAIL + actual result |
| 6 | [report + web UI + e2e](phase-06-report-web-ui-and-e2e.md) | ⬜ pending | ⭐ **ship được cho tester** |

Thứ tự thực thi tuần tự 1→6. Phase 2 là tim của tool — cơ chế đã verified, làm sớm để chốt rủi ro.

## Quyết định đã chốt — KHÔNG tự đổi

1. **Override bằng cách patch file cache của Firebase RC SDK**, không dùng Firebase Admin API,
   không MITM, không sửa APK.
2. **PHẢI patch cả 2 chỗ**: `files/frc_<appId>_firebase_activate.json` (`configs_key` +
   `fetch_time_key`) **và** `shared_prefs/frc_<appId>_firebase_settings.xml`
   (`last_fetch_time_in_millis` = now). Thiếu phần thứ 2 là app fetch đè mất patch.
3. **PHẢI patch cả file mirror của SDK Apero**, giữ nguyên kiểu XML
   (`boolean`/`string`/`long`/`int`). ~45-47% key bị mirror.
   **Nhận mirror bằng GIAO TÊN KEY với `configs_key`, KHÔNG theo tên file.** Không phải file
   `vsl_*` nào cũng là mirror: `vsl_template4_prefs.xml` (0/5 trùng) và
   `vsl_widget_local_prefs.xml` (0/2 trùng) là **state nội bộ app** — ghi vào là làm hỏng
   trạng thái app, không phải đổi config.
4. **KHÔNG cắt mạng** để chặn fetch — app under test cần mạng cho ads/API/analytics.
5. **Clear data CHỈ khi precondition đòi state sạch**, và phải clear **TRƯỚC** rồi mới patch
   (`pm clear` xoá luôn file vừa ghi). Không clear để "lấy config mới" — việc đó đã hết cần.
6. **`rc_verify` là bắt buộc**: đọc lại config sau khi mở app. Lệch → `BLOCKED`, **không FAIL**.
7. **Verdict 5 trạng thái, không pass giả**: `PASS` / `FAIL` (+ actual result) /
   `NOT_VERIFIABLE` / `NEEDS_HUMAN` / `BLOCKED`. Case = trạng thái xấu nhất của các assertion.
8. **Chấm theo từng dòng assertion**, không chấm cả case một cục (Expected vốn đánh số `1. 2. 3.`).
9. **Whitelist RC key đọc thật từ máy** qua `rc_baseline`. Không hardcode. Nhờ đó param analytics
   (`source = navigation`, `click_area`, `feature_name`) tự bị loại.
10. **Runtime toggle** (mũi tên `→` trong Test Data) → nhận diện, đánh `NEEDS_HUMAN`. Ngoài scope.
11. `act_resolver` round 1 **hẹp**: `Mở tab <tên>`, match text/content-desc trong ngoặc kép,
    `Quan sát...` = no-op. Không dịch được → `NEEDS_HUMAN`, **không đoán**.
12. **Verdict do code Python quyết**, không LLM. (LLM fallback cho resolver là round 2.)
13. Stack: Python 3.12, FastAPI + uvicorn, vanilla JS, `start.sh` — mirror `tsa`/`usv`.
    Chỉ bind `127.0.0.1`. Mọi module **<200 LOC**. Comment tiếng Việt không dấu.
14. Mọi lệnh adb lọc `PACKAGE_RE`/`SERIAL_RE` trước — chặng 2 chạy qua `sh` trên device.
15. Test theo khuôn **FakeAdb** (`tsa/tests/test_remote_config_push.py`) — suite chạy được khi
    không cắm máy. Marker `device` skip mặc định.
16. **Đường ghi tách 2 chiến lược**: `run-as` (app debuggable) và `su` (máy root). Cùng một
    `rc_write` interface. Nhờ `su`, app **release cũng patch được** trên máy root → không phụ
    thuộc dev bật `debuggable`.
17. **Pre-check bằng grep DEX trước khi chạy case**: key không có string trong `classes*.dex`
    → app không đọc key đó → trả `KEY_NOT_USED` ngay, không tốn một lượt mở app.
18. **Chấm case ads bằng logcat, không bằng dump UI**: tag `FOR_TESTER_LOAD_AD` /
    `FOR_TESTER_SHOW_AD` / `BannerAdHelper.adBannerState(...)`. `tsa` đã có tầng đọc logcat
    theo tag để tái dùng.
19. **Case "tắt/bật một vị trí ads" chấm ở TẦNG REQUEST**, không ở tầng show: so **tập ad
    unit id** đã `starting load` giữa baseline và case. Tầng request **độc lập với ad fill**;
    tầng show phụ thuộc fill nên không chấm được khi ad không có quảng cáo để trả.
20. **Case cần đối chứng thì patch LUÔN baseline** với giá trị mặc định của chính các key đó —
    giữ đúng **một biến**. Baseline nguyên trạng khác case ở *hai* thứ (key + trạng thái
    throttle/fetch) nên không quy được khác biệt cho key.
21. **Ép về first-open KHÔNG cần `pm clear`**: lật `ARG_KEY_SHOW_ONBOARDING` = `true` trong
    `vsl_template4_prefs.xml`. Giữ nguyên login/ngôn ngữ. Đây là **thao tác reset riêng**, khác
    hoàn toàn với patch config — `rc_patch` vẫn tuyệt đối không được ghi vào file này.
22. **Bộ TC dùng chung cho mọi app, mỗi bản SDK một bộ** (chốt 2026-09-23). Logic key giống
    nhau giữa các app, chỉ khác package. Tool **không** cần file TC riêng từng app: whitelist
    từ `rc_baseline` + `dex_check` tự lọc key app không có (→ `KEY_NOT_USED`, không FAIL).
23. **Đối chiếu bản SDK trước khi chạy**: đọc `VslTemplate4FirstOpenSDK: Using version X` từ
    logcat lần mở app, so với dòng `spec: SDK visionlab:tutorial:X` ở đầu sheet. Lệch bản →
    cảnh báo rõ trên report (không tự chặn — tester quyết có chạy tiếp hay không).
24. **Log ads lọc theo PID app đích** (`Start proc <pid>:<pkg>`), không theo tag. App ads khác
    chạy nền in cùng tag `FOR_TESTER_*` và có thể bung `AdActivity` đè lên splash app đích →
    trước mỗi case: force-stop các app ads khác + `KEYCODE_HOME`.
25. **Key lấy từ CẢ Precondition lẫn Test Data** (chốt 2026-09-23). Trùng key → Test Data thắng.
    Dòng Precondition có mũi tên (`high=true -> load fail`) bị bỏ. Test Data ép trạng thái ad
    (`105-...-high: fail`) → `NEEDS_HUMAN`; giá trị dạng lựa chọn (`layout1/2/3`) →
    `NEEDS_HUMAN`. Bộ chung 3.0.2: **56/98** case chạy được trên `photocreator.aiart`
    (54 `photoshoot`, 54 `aiartcreator`); 33 case chờ cách ép ad fail (câu hỏi mở #6).
26. **Giá trị lựa chọn tự nhân ra từng lượt** (chốt 2026-09-23): `layout1/2/3`,
    `layout1/layout2`, `layout1 / layout2` → mỗi giá trị 1 lượt; nhiều key lựa chọn → tích
    Descartes (`RcCaseData.variants`, `.runs`). Quá 16 tổ hợp → `NEEDS_HUMAN`. Bộ chung 3.0.2:
    **60/98** case, **77 lượt** mở app trên `photocreator.aiart`.

27. **Ép fill/fail theo TỪNG unit bằng ID ads trong RC** (đo 2026-09-23, `ad_state.py`):
    ký hiệu TC `102-spl-n-inter-high: fail` → key RC chứa ID → **ID sai** = chắc fail, **ID test
    Google** cùng loại = chắc fill. Đo thật: high=ID sai → `onAdFailedToLoad` → fallback unit
    thường (ID test) `loaded` → show. Không cần lắc máy / nguồn Meta.
    **Ký hiệu → key lấy từ bảng ĐÃ ĐO** `src/rcr/data/ad_id_keys.yaml`, KHÔNG suy từ tên:
    `id_102_spl_n_inter_high`, `id_201_lfo1_n_native*`, `id_101_spl_a_banner` có trong RC
    nhưng FO 3.2.0 **không đọc** (đặt ID sai, request giữ nguyên). Hiện bảng có 2 cặp:
    `102-spl-n-inter-high → splash_inter_high_n_id`, `102-spl-n-inter → splash_inter_n_id`.
    `fail` không ép được → `NEEDS_HUMAN`. `loaded` không ép được → vẫn chạy (native bản debug
    tự fill bằng ID test) nhưng **phase 5 phải thấy unit đó loaded trong log, không thì
    BLOCKED** (inter dùng ID thật, thường no-fill). Ký hiệu viết tắt không đọc được
    (`102-n-high/high1: fail`) → `NEEDS_HUMAN`, không bỏ qua im lặng.
    **Private DNS chặn ads KHÔNG dùng được**: `dns.adguard-dns.com` đã validated mà native vẫn
    fill. Bộ chung 3.0.2: **69/98 case, 86 lượt** trên `photocreator.aiart`.
28. **Chạy xong → report publish thành artifact và tự mở link** (user dặn 2026-09-23). Report
    HTML self-contained để publish thẳng.
29. **Luật SDK lấy từ spec Confluence, tự cập nhật** (user dặn 2026-09-24): theo dõi trang
    "SDK Tutorial - Ver 6.4.0" + mọi `visionlab:tutorial:X.Y.Z` ≥ 3.0.1 dưới trang cha "SDK Tutorial"
    (pageId 168689676), kể cả trang thêm sau. `python -m rcr.spec_sync` trước mỗi lượt chạy TC →
    trang NEW/CHANGED thì đọc (bản cũ giữ ở `.prev.txt`) và cập nhật `data/sdk_rules.yaml` kèm pageId.
    Text spec ở `data/specs/` **không commit** — repo public, spec là tài liệu nội bộ.

30. **Case ads chấm ở tầng LOG request/load, không đòi nhìn thấy ad** (user chốt 2026-09-25):
    "chỉ cần logic preload load show banner nó đúng là được, tại vì inter nó load nhanh quá
    nên nhảy sang inter trước khi show banner ở splash rồi… có log load là cũng được rồi".
    Test tay cũng phải chạy vài lần mới thấy banner. → `case_drive` không được coi "quảng
    cáo che màn hình" là fail của case ads; `ad_log` đọc log theo PID app và chấm bằng
    tập unit đã request/loaded.

31. **Ad không fill vẫn tính PASS** (user chốt 2026-09-25): "ads no fill không sao nhá
    vẫn coi là pass nhé". Unit được request đúng là logic app đúng; kho quảng cáo không trả
    ad là chuyện của kho. → bỏ hẳn trạng thái `BLOCKED_NO_FILL`; `assert_ads` trả `PASS` kèm
    ghi chú "request đúng nhưng không fill". Chỉ còn FAIL khi **không có request nào**.
    Màn hình bị quảng cáo che (không đọc được chữ trên app) vẫn là `NEEDS_HUMAN` — đó là
    chuyện khác: đóng ad rồi chạy lại.

## Facts đã verify — không cần verify lại

Đo 2026-09-04 (Pixel 7 `29301FDH2006K7`) và 2026-09-07 (thêm Pixel 4 `99261FFAZ0077C`):

- Schema: `{"configs_key":{key:"value LUÔN là string"},"fetch_time_key":<ms>,"template_version_number_key":N}`
- Chỉ patch `activate.json` → **patch bị đè sạch** (probe mất, 196→200 key)
- Patch thêm `last_fetch_time_in_millis` = now → **patch sống** (`ad_load_timeout`=99 giữ nguyên)
- Mirror (đo 2026-09-07, 2 app): `_remote_first_open.xml` 83/83 và 87/87 ·
  `_billing_remote_config.xml` 3/3 · `_widget_remote_prefs.xml` 5/6 ·
  `_rating_remote_prefs.xml` 3/5 — **nhưng** `vsl_template4_prefs.xml` 0/5 và
  `vsl_widget_local_prefs.xml` 0/2 **không phải mirror**
- Tỉ lệ key bị mirror: `com.ai.videogenerator.photocreator.aiart` 91/200 (45%, 8 node vsl không
  phải RC) · `aiphotogenerator.photoshoot.aiart.aiimagegenerator` 98/206 (47%, 10 node)
- Kiểu XML gặp trong mirror: `boolean` 74 · `string` 28 · `long` 3 · `int` 3
- Đường ghi: **cả 2 đường đều chạy trên Android 12** — `run-as cp` và
  `cat tmp | run-as pkg sh -c 'cat > dest'`. Vẫn giữ fallback làm bảo hiểm cho ROM chặt hơn.
- **Cơ chế verified chéo 2 máy / 2 bản Android / 2 app / 2 Firebase project:**
  Pixel 7 `com.ai.videogenerator.photocreator.aiart` (`enable_onb3_screen` true→false, 200 key,
  file state nội bộ không đổi 1 byte) và Pixel 4 Android 12
  `com.aiphotogenearator.aivideogenerator.photogallery` (`show_102_spl_n_inter` true→false,
  195 key giữ nguyên). Cả 2 lần: giá trị sống qua lần mở app, mirror đổi theo, restore sạch.
- Máy test: **Pixel 7** 17 app debuggable / 5 có RC · **Pixel 4** (Android 12, SDK 31, user build,
  không root) 17 app debuggable / 7 có RC

### Case đã chấm thật bằng tay (2026-09-07, `lingospeak.english.learnlanguage.speak`)

| Case | Verdict | Bằng chứng |
|---|---|---|
| `splash_banner_change = false` → load & show banner | load **PASS** / show **BLOCKED_NO_FILL** | `adBannerState(None→Loading)`, `FOR_TESTER_LOAD_AD: Banner ...4020637064`, node `bannerAdView` + `shimmer_container_banner` `[0,2100][1080,2148]`. Lượt `true`: 0 log, 0 node. Show fail do `has load error` (không fill), **không phải lỗi app** |
| `sbc=true` + `show_105_spl_n_native=false` + `_high=false` | **PASS** | request native **6 → 4**; biến mất đúng 2 unit `...5974670961`, `...9913915974`; 2 unit khác giữ nguyên; 0 unit mới; banner = 0 (đúng vì `sbc=true`) |

Case 2 **chạy 2 lần độc lập, trùng khớp từng con số** → kết quả tái lập được, đủ điều kiện tự động hoá.
Lượt nguyên trạng và lượt patch-đúng-giá-trị-gốc cho kết quả **giống hệt** (kể cả số lần request
từng unit) → patch bằng giá trị gốc không tự làm đổi hành vi.

- `songmaker` **không có string `splash_banner_change` trong DEX** → app không đọc key đó; banner
  vẫn show bất kể `true`/`false` (PASS giả). Grep DEX phát hiện đúng, khớp quan sát runtime.
- Có key trong config Firebase **≠** app dùng key đó: `photogallery` có
  `enable_101_spl_a_banner='true'` mà code không tham chiếu. Template Firebase dùng chung nhiều app.
- File TC mẫu `TC_IIP032_Moment_Explore_v7.5.0.xlsx`: 59 case, **15 case RC** (3 runtime toggle
  → 12 tự động được), 14 bước action, **28/28 assertion dump chấm được**, **0 case cần logcat**
- 8/14 bước action là cùng thao tác `Mở tab <tên>`; 3 bước `Nhấn vào tiêu đề danh mục`

## Chặn ngoài tầm tool

**App đích AIP922 (`ai.photogenerator.aivideo.aivideogenerator.aiart` v3.1.0) KHÔNG debuggable.**
Đo trên cả 2 máy: `flags` thiếu `DEBUGGABLE`, `run-as` từ chối, `aapt dump badging` không có
`application-debuggable`, máy không root (`ro.build.type=user`). Không có đường vào.
→ Phải xin dev bản APK bật `debuggable`. Tool không hardcode app nên đổi sang AIP922 sau chỉ là
đổi package.

**App dựng/validate**: `com.ai.videogenerator.photocreator.aiart` (Pixel 7, **đã verified trọn
cơ chế**, 200 key, 91 key bị mirror qua 3/5 file `vsl_*`).
**App phụ cho test mirror**: `aiphotogenerator.photoshoot.aiart.aiimagegenerator` (Pixel 7,
206 key, 98 mirror qua 4/6 file — nhiều biến thể mirror nhất).
**App test trường hợp KHÔNG có mirror**: `com.aiartvideo.imageai.aigenerator` (Pixel 4, 257 key,
**0 file `vsl_*`**) — app không dùng SDK mirror của Apero, phải chạy đúng khi `mirrors` rỗng.
**App test trên Android 12**: `com.aiphotogenearator.aivideogenerator.photogallery` (Pixel 4,
195 key, 3 mirror — đã verified).

**File TC cho phase 4-6**: dùng **bộ TC dùng chung** (quyết định 22), không tạo file riêng
cho app thay thế nữa. Bộ đầu tiên: sheet `SDK visionlab:tutorial:3.0.2 — Ads Preload per Screen
(Splash → OB5)` (Google Sheet `1KYsyRJ8qTR-FrkWFZ0zMHPv7-jveBeMgRGJz22ulVlE`, 98 case).
Đọc được từ 2026-09-23: **50/98** case bóc ra key chạy được trên `photocreator.aiart`, 44 trên
`photoshoot`, 43 trên `aiartcreator`.

### Đo 2026-09-23 (Pixel 7, `com.ai.videogenerator.photocreator.aiart`, SDK FO 3.2.0)

Chạy tay case 5-10 của bộ TC chung bằng module `rc_*` + script ghép tạm (phase 4 chưa có):

- **Bug `is_debuggable` đã sửa**: `dumpsys` in `flags=0x0` (section khác) trước dòng
  `flags=[ DEBUGGABLE ... ]` → mọi app bị báo không debuggable. Giờ chỉ đọc dòng dạng `[ ]`.
- Verify sống qua lần mở app: **12/12 lượt** (reset mềm onboarding + patch).
- **Native splash 105 chỉ phụ thuộc `show_105_spl_n_native`; `_high` không có tác dụng.**
  Đối chứng 1 biến: (high,thường) = (T,T) có · (F,T) có · (T,F) **không** (3 lượt) · (F,F)
  không. → case 6/7 (TC chỉ đặt `high=true`) FAIL. Chưa rõ bug app hay TC thiếu key.
- Bản debug dùng **ID test Google** `ca-app-pub-3940256099942544/2247696110` cho mọi native →
  không phân biệt unit high/thường qua ID; không ép được "high fail" (case 8 → `BLOCKED`).
- App đích **không in `FOR_TESTER_*`**. Tín hiệu dùng được: `NativeAdHelper: <Activity>:
  adNativeState(...)`, `AdEventLogger: trackAdRequest ... adType: NATIVE`,
  `FO_VslTemplate4FirstOpenSDK: Native splash impression` / `<Activity> is showing`.
- Native splash chỉ hiện **~0.1-0.5s** rồi sang màn Language → screenshot mốc cố định trượt;
  phải chụp liên tục, và chấm hiển thị bằng log là chính.
- Mọi layout native đều log `NullPointerException` khi populate (SDK bắt, không crash).
- Case mạng (tắt mạng trước splash, bật lại sau) **tự động được**: `svc wifi/data
  disable|enable` — không còn là `NEEDS_HUMAN`.

## Câu hỏi mở

1. ~~File testcase của AIP922~~ → dùng bộ TC chung theo bản SDK (quyết định 22).
2. Bản debuggable AIP922 dùng chung Firebase project với production? Nếu không → whitelist khác.
3. Round 2: app có log analytics ra logcat qua `setprop debug.firebase.analytics.app` không?
4. ~~Precondition hay Test Data là nguồn key?~~ → gộp cả hai (quyết định 25).
5. `_high` không có tác dụng (xem Đo 2026-09-23) — bug app hay TC thiếu `show_105_spl_n_native`?
   Kiểm thêm trên `photoshoot` / `aiartcreator` để biết riêng app hay chung SDK 3.2.0.
6. ~~Case "ép ad X fail"~~ → quyết định 27. Còn mở: đo thêm cặp ký hiệu → key cho high1,
   `_o_` (old user), banner 101, native 105/201/202/30x (hiện app không đọc key ID nào của
   chúng). Ghi chú cũ: tester làm tay bằng **lắc máy → Ad Inspector →
   chọn nguồn Meta** → no fill. `shared_prefs/admob.xml` có `inspector_info`
   (`"gesture":"SHAKE","networkExtras":"{}"`) → nhiều khả năng lựa chọn lưu ở `networkExtras`.
   Đang đo: snapshot sandbox trước/sau khi tester chọn Meta, xem ghi lại được không.
   Lưu ý: bản debug dùng **chung 1 ID test** cho mọi native → ép Meta có thể làm fail CẢ
   high lẫn thường, không tách được "high fail, thường loaded".
