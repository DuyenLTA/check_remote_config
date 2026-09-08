# Remote Config Case Runner — brainstorm summary

**Ngày:** 2026-09-04 · **Trạng thái:** design đã chốt, chờ lập plan
**Máy đo:** Pixel 7 (`29301FDH2006K7`) · **App đo:** `com.ai.videogenerator.photocreator.aiart`

## 1. Vấn đề

Tester chỉ có quyền **đọc** trên Firebase. Cần đổi giá trị remote config để chạy test case
mà: không cần quyền admin, không đụng Firebase server thật (tránh ảnh hưởng user thật và
dev khác dùng chung project).

Nguồn case: file testcase XLSX sẵn có (vd `TC_IIP032_Moment_Explore_v7.5.0.xlsx`), sheet
`Test Cases`, cột `N° | Feature | Test Description | Sub-scenario | Precondition | Test Data
| Action | Expected Result | PASS/FAIL`. Giá trị RC nằm ở cột **Test Data**.

Đích cuối: tool đọc file TC → set config → action trên máy thật → so Expected → chấm
PASS/FAIL, fail thì mô tả rõ actual result.

## 2. Cơ chế override — ĐÃ KIỂM CHỨNG THỰC TẾ

Không phải "mỗi app một khác". Firebase RC SDK ghi cùng chỗ, cùng tên, ở mọi app:

| Thứ | Đường dẫn |
|---|---|
| Giá trị RC | `files/frc_<appId>_firebase_activate.json` |
| Schema | `{"configs_key":{key:"value luôn là string"},"fetch_time_key":<ms>,"template_version_number_key":N}` |
| Throttle fetch | `shared_prefs/frc_<appId>_firebase_settings.xml` → `last_fetch_time_in_millis`, `last_fetch_etag` |

App đo: **196 key** (sau đó Firebase đổi template → 200). Yêu cầu: build **debuggable**
(`run-as`). 3/30 app trên máy debuggable — đều là app Apero.

### 2.1 Thực nghiệm (a): patch có sống qua lần mở app?

| Điều kiện | Kết quả |
|---|---|
| Chỉ patch `activate.json`, để `settings.xml` mốc cũ (throttle hết hạn) | ❌ **patch bị đè sạch** — app fetch thật, `rcr_probe` mất, 196→200 key |
| Patch `activate.json` **+** `fetch_time_key` **+** `last_fetch_time_in_millis` = now | ✅ **patch sống** — `rcr_probe` còn, `ad_load_timeout` đặt `99` giữ nguyên sau khi mở app |

**Kết luận:** phải patch cả 2 file. Throttle 12h của SDK chính là đòn bẩy — cùng cái
trước đây buộc tester phải clear cache.

**KHÔNG cắt mạng** để chặn fetch: app under test cần mạng cho ads / API / analytics; cắt
mạng làm hỏng chính case đang test → FAIL oan.

### 2.2 Clear cache: không còn cần cho remote config

Tách 2 lý do trước đây bị gộp:

| Lý do clear | Flow cũ | Flow mới |
|---|---|---|
| Để app lấy config mới | bắt buộc | **bỏ hẳn** — patch file + `force-stop` + `am start` |
| Để reset state app (onboarding, login, counter ads) | tuỳ | **vẫn cần**, chỉ với case có precondition đòi máy sạch. Clear **TRƯỚC** rồi patch |

### 2.3 SDK Apero mirror RC sang prefs riêng — bẫy lớn

| File mirror | Số key | Trùng tên RC |
|---|---|---|
| `vsl_template4_remote_first_open.xml` | 83 | **83/83** |
| `vsl_billing_remote_config.xml` | 3 | **3/3** |
| `vsl_widget_remote_prefs.xml` | 6 | 5/6 (`widget_fetch_successful` là cờ nội bộ) |

**91/196 key bị mirror**, gồm nhóm tester đụng nhiều nhất (`enable_onb1..5_screen`,
`paywall_config`, `layout_onb2_screen`). Chỉ patch `frc_*.json` → gần nửa số key
**không ăn mà không báo lỗi**. Tên key y hệt → không cần bảng map; luật: key có mặt ở
mirror thì patch cả 2 chỗ, **giữ nguyên kiểu XML** (`boolean`/`string`/`long`/`int`).

**Bổ sung 2026-09-07 — sửa luật ở trên:** đo thêm 2 app cho thấy **không phải file `vsl_*` nào
cũng là mirror**. `vsl_template4_prefs.xml` (0/5 key giao với RC) và `vsl_widget_local_prefs.xml`
(0/2) là **state nội bộ app** — ghi vào là làm hỏng trạng thái app. `vsl_rating_remote_prefs.xml`
chỉ mirror 3/5 key dù tên có chữ `remote`.
→ **Nhận mirror bằng GIAO TÊN KEY với `configs_key`, không theo tên file.**
Số đo: `com.ai.videogenerator.photocreator.aiart` 91/200 key mirror (3/5 file `vsl_*` là mirror
thật) · `aiphotogenerator.photoshoot.aiart.aiimagegenerator` 98/206 (4/6 file).
Kiểu XML gặp trong mirror: `boolean` 74 · `string` 28 · `long` 3 · `int` 3.

## 3. Đo khả năng tự động hoá trên file TC thật

59 case / 108 bước Action.

### Chấm Expected Result bằng gì
| | Case | % |
|---|---|---|
| `uiautomator dump` chấm chắc | 29 | 49% |
| Cần `logcat` (event analytics) | 19 | 32% |
| Có assertion dump không thấy (animation, độ mượt) | 11 | 18% |

Case remote config nằm gọn trong nhóm 29 chấm chắc. 11 case "mờ" không mất trắng —
phải **chấm theo từng dòng assertion** (Expected vốn đánh số `1. 2. 3.`), không chấm cả
case một cục.

### Dịch câu Action thành thao tác
| Nhóm | Bước | % |
|---|---|---|
| `TAP_TEXT` — có động từ, target mơ hồ | 53 | 49% |
| `OBSERVE` — "Quan sát..." = no-op, chuyển sang chấm | 25 | 23% |
| `TAP_QUOTED` — có chuỗi trong ngoặc kép | 14 | 12% |
| `UNKNOWN` | 9 | 8% |
| `CONFIG` — đổi RC giữa case | 6 | 5% |
| `WAIT` | 1 | 0% |

→ **29% không cần resolve · 12% resolve dễ · 57% cần LLM hoặc mapping tay.**

### 3.1 ĐO LẠI CHỈ TRÊN NHÓM CASE REMOTE CONFIG (quan trọng)

Con số 57% ở trên tính trên **cả 59 case**, gồm happy-path Moment/Explore không liên quan RC.
Lọc đúng nhóm RC — nhóm duy nhất trong scope — thì dễ hơn hẳn:

| | Cả 59 case | **Chỉ 15 case RC** |
|---|---|---|
| Bước action | 108 | **14** (12 case × ~1.2 bước) |
| Bước cần LLM/mapping | 57% | **~14%** (1 bước) |
| Assertion dump chấm được | 49% | **28/28 = 100%** |
| Case cần logcat | 19 | **0** |

15 case RC, trừ 3 runtime toggle → **12 case tự động hoá được**.
8/14 bước là cùng một thao tác (`Mở tab Moment` / `Mở tab Explore`), 3 bước là
`Nhấn vào tiêu đề danh mục` → chỉ cần hỗ trợ **2-3 thao tác** là phủ hết.

Assertion toàn dạng "hiển thị / không hiển thị" + "App không crash" (check process còn sống)
→ `uiautomator dump` chấm được 100%, **không cần logcat ở round 1**.

**Kết luận: full end-to-end (set config → action → chấm PASS/FAIL + actual result) khả thi
ngay round 1 cho nhóm case RC.** Đề xuất cắt scope trước đó (chỉ set config, tester tự chấm)
đã rút lại.

57% xác nhận: `act_resolver` là rủi ro lớn nhất của dự án, **không phải** remote config.
Ví dụ khó: `Nhấn thẳng vào 1 thẻ style bất kỳ trong hàng AI Video (không nhấn See All)`,
`Nhấn vào tiêu đề danh mục`.

6 bước `CONFIG` = runtime toggle có thật trong file, dù user nói sẽ chỉ viết `= true/false`.
Tool phải nhận diện → `NEEDS_HUMAN`, không parse sai.

## 4. Giải pháp chốt

**Tool riêng** `~/projects/rc-case-runner`, package `src/rcr/`, FastAPI + vanilla JS —
bám khuôn `ui-spec-verifier` / `tsa` để sau nhập vào tool check thông số KT không phải
viết lại. Module <200 LOC, comment tiếng Việt không dấu.

| Module | Việc | Round |
|---|---|---|
| `tc_loader` | XLSX → `Case(n, sub, precondition, test_data, actions[], expects[])`, split theo số | 1 |
| `rc_extract` | bóc `key = value` từ Test Data; lọc bằng **whitelist = key đọc thật từ máy** → `source = navigation` tự rơi ra | 1 |
| `rc_baseline` | đọc 1 lần `frc_*_activate.json` + 3 mirror → appId, bản gốc, kiểu XML từng key | 1 |
| `rc_patch` | ghi `activate.json` + mirror + `fetch_time_key` + `last_fetch_time_in_millis` = now | 1 |
| `rc_verify` | mở app xong đọc lại → giá trị còn nguyên? không thì **BLOCKED**, không FAIL | 1 |
| `device_reset` | `pm clear` / `force-stop` / `am start`; chỉ clear khi precondition đòi state sạch | 1 |
| `act_resolver` | Action → node tap. Hẹp: `Mở tab X` + match text/desc. Bí → `NEEDS_HUMAN` | 1 |
| `assert_dump` | chấm bằng cây node (tái dùng `ui_dump.py` của ui-spec-verifier) | 1 |
| `assert_log` | `setprop debug.firebase.analytics.app <pkg>` → logcat tag `FA` → so event + param | 2 |
| `report_html` | report + screenshot mỗi bước (khuôn `report_html.py` của tsa) | 1 |

### Verdict — 5 trạng thái, không pass giả
`PASS` / `FAIL` (+ actual result: node thật thấy gì, event thật bắn gì) /
`NOT_VERIFIABLE` (animation, độ mượt, màu — không tính FAIL) /
`NEEDS_HUMAN` (Action không dịch được) /
`BLOCKED` (config bị đè, app không debuggable, crash, Expected có `[TBD]`).

Verdict case = trạng thái xấu nhất trong các assertion; report chỉ rõ dòng nào không chấm được.
Thống nhất với quyết định `NOT_VERIFIABLE` đã chốt ở `ui-spec-verifier`.

### Flow mỗi case
```
1. pm clear                        (chỉ khi precondition đòi state sạch)
2. am start → chờ → force-stop     (chỉ khi vừa clear, để app tự sinh files/)
3. patch activate.json + mirror + last_fetch_time = now
4. am start
5. đọc lại → verify config còn nguyên → không thì BLOCKED, dừng case
6. chạy Action → dump + logcat + screenshot
7. chấm từng assertion
```

## 5. Scope

**Round 1 — full end-to-end, chỉ nhóm case remote config.** Đầu vào file TC → set config →
action trên máy thật → chấm PASS/FAIL + note actual result. Modules: `tc_loader`,
`rc_extract`, `rc_baseline`, `rc_patch`, `rc_verify`, `device_reset`,
`act_resolver` (hẹp), `assert_dump`, `report_html`.

`act_resolver` round 1 chỉ cần: `Mở tab <tên>` (nav bar), match text/content-desc trong
ngoặc kép, `Quan sát...` = no-op. Không dịch được → `NEEDS_HUMAN`, không đoán.

**Round 2:** mở rộng ra 59 case — `assert_log` (19 case event), `act_resolver` + LLM fallback
cho 57% bước khó, assertion mơ hồ.

**Ngoài scope:** runtime toggle mũi tên (nhận diện → `NEEDS_HUMAN`), AI vision chấm ảnh,
tự sinh mapping màn.

## 6. Rủi ro

| # | Rủi ro | Mức | Giảm thiểu |
|---|---|---|---|
| 1 | `act_resolver` chỉ tự resolve 12%, 57% cần LLM/mapping | **Cao** | đẩy sang round 2; round 1 vẫn dùng được độc lập |
| 2 | App build release → `run-as` chết | **Cao** | không có workaround (trừ máy root). Tool phải báo rõ ngay đầu |
| 3 | `minimumFetchInterval = 0` ở build dev → throttle vô hiệu | Trung | `rc_verify` bắt được → BLOCKED. Nếu app nào cũng vậy mới bàn cắt mạng có chọn lọc |
| 4 | Quên patch mirror → 91/196 key im lặng không ăn | Trung | `rc_patch` luôn quét cả 3 file mirror |
| 5 | Whitelist key theo từng app, không phải hằng số | Thấp | `rc_baseline` đọc lại mỗi khi đổi app |
| 6 | Firebase đổi template giữa phiên (đã thấy 196→200) | Thấp | baseline chụp 1 lần đầu phiên, ghi version vào report |

## 7. Success metrics

- Round 1: set được 100% key dạng `= true/false/<số>/JSON` trong file TC, `rc_verify` xác
  nhận config sống sau khi mở app; 0 case bị chấm FAIL oan do config bị đè.
- Key bị mirror phải ăn — verify bằng cả `frc_*.json` lẫn file mirror.
- Runtime toggle bị đánh `NEEDS_HUMAN`, không parse sai thành `= false`.

## 8. Hiện trạng app đích AIP922 — BỊ CHẶN

`ai.photogenerator.aivideo.aivideogenerator.aiart` v3.1.0 (versionCode 24) — **không debuggable**.
Đo 2026-09-07 trên **cả 2 máy** (Pixel 4 `99261FFAZ0077C`, Pixel 7 `29301FDH2006K7`):

| Kiểm tra | Kết quả |
|---|---|
| `dumpsys package` flags | `[ HAS_CODE ALLOW_CLEAR_USER_DATA ]` — thiếu `DEBUGGABLE` |
| `run-as <pkg>` | `package not debuggable` |
| `aapt dump badging base.apk` | không có dòng `application-debuggable` |
| `adb root` | `adbd cannot run as root in production builds` |
| `su` trên device | không có |
| `ro.build.type` / `ro.debuggable` | `user` / `0` |
| Đọc `/data/data/<pkg>/files/` | Permission denied |
| Bản `.debug`/`.dev` cài kèm | không có |

→ Không có đường vào. **Phải xin dev bản APK bật `debuggable`.** Tải lại APK ở nguồn khác
không giải quyết được — cờ nung trong file lúc build.

Cần hỏi dev thêm: bản debuggable dùng **chung Firebase project với production hay project riêng**?
Nếu riêng → danh sách key RC khác → whitelist phải đọc lại từ chính bản đó.

**Lệnh soi APK trước khi cài** (đã kiểm chứng cả 2 chiều):
```bash
~/Android/Sdk/build-tools/37.0.0/aapt dump badging <file.apk> | grep application-debuggable
# in ra dòng đó = dùng được | không in gì = không dùng được
```

### App thay thế để dựng tool

Tool không gắn app nào (`rc_baseline` đọc theo từng app) → dựng trên app debuggable khác,
trỏ sang AIP922 khi có build.

App debuggable + có RC trên Pixel 7: `com.ai.videogenerator.photocreator.aiart` (**đã kiểm
chứng trọn cơ chế**, 196→200 key, 3 mirror), `com.aiphotogenerator.aivideogenerator.aiart.aiartcreator`,
`aiphotogenerator.photoshoot.aiart.aiimagegenerator`, `com.apero.firstopen.sample`,
`com.screenmirroring.videoandtvcast.smartcast`.

**Chọn:** `com.ai.videogenerator.photocreator.aiart` — cơ chế đã verified, 200 key, 91 key mirror.
**App phụ test mirror:** `aiphotogenerator.photoshoot.aiart.aiimagegenerator` — 206 key, 98 mirror,
có file mirror một phần. Trên Pixel 7: 17 app debuggable, 5 app có Firebase RC.

## 9. Next steps

1. `/ck:plan` round 1.
2. Dựng + validate trên `com.ai.videogenerator.photocreator.aiart`.
3. Song song: xin dev bản debuggable AIP922 + file testcase của AIP922.

## Câu hỏi chưa giải quyết

1. **File testcase của AIP922** — chưa có. File đang phân tích là `TC_IIP032_Moment_Explore_v7.5.0.xlsx`
   (dự án IIP032). Cấu trúc cột của TC AIP922 có giống không? Key RC nó dùng là gì?
2. **Bản debuggable AIP922 có dùng chung Firebase project với production?** Nếu không, whitelist
   key và giá trị baseline sẽ khác.
3. **19 case cần logcat (round 2)**: app có log analytics event ra logcat không?
   `setprop debug.firebase.analytics.app` là cách chuẩn nhưng chưa đo trên app Apero.
4. **`assert_log` (round 2)** cần tên event + param chính xác; cột Expected viết văn xuôi
   (`moments_home_view bắn đúng`) — có sẵn spec analytics ở đâu hay bóc từ TC?
5. **LLM cho `act_resolver` round 2** — tái dùng `ai_provider.py` của tsa hay khác?
