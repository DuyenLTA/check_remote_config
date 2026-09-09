---
title: "Remote Config Case Runner"
status: in-progress   # phase 1-3 done, tiep phase 4
created: 2026-09-07
source: docs/plan/reports/from-brainstorm-to-planner-rc-override-design-260904-1425-firebase-remote-config-testcase-runner-report.md
target_repo: ~/projects/rc-case-runner
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
| 4 | [device_reset + act_resolver](phase-04-device-reset-and-action-resolver.md) | ⬜ pending | chạy 1 case tới đúng màn cần chấm |
| 5 | [assert_dump + verdict](phase-05-assert-dump-and-verdict.md) | ⬜ pending | ⭐ chấm được case RC, ra PASS/FAIL + actual result |
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

**Lệch dữ liệu cần xử ở phase 4**: file TC mẫu là của IIP032 — **không khớp app thay thế**
(khác key, khác UI). Phase 1-3 validate được bằng file IIP032; phase 4-6 cần một file TC nhỏ
viết cho chính app thay thế (dùng key thật của nó). Việc tạo file đó nằm trong phase 4.

## Câu hỏi mở

1. File testcase của AIP922 — chưa có. Cấu trúc cột có giống IIP032 không?
2. Bản debuggable AIP922 dùng chung Firebase project với production? Nếu không → whitelist khác.
3. Round 2: app có log analytics ra logcat qua `setprop debug.firebase.analytics.app` không?
