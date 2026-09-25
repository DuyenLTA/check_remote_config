---
phase: 4
title: "device_reset + act_resolver (hep)"
status: in-progress
priority: P1
effort: "1.5d"
dependencies: [2, 3]
---

# Phase 4: device_reset + act_resolver

## Overview
Chạy được **một case** từ đầu tới lúc app đứng ở đúng màn cần chấm: reset máy đúng cách,
patch config, mở app, verify, rồi thực thi các bước Action.

Phase này cũng tạo **file TC mẫu cho app thay thế** — bắt buộc, vì file IIP032 không khớp app
đang có.


## Đã làm (2026-09-25)

Cắt một lát chạy được trước, dùng ngay qua slash command `/rc-check` thay vì chờ trọn phase:

- `device_app.py` — force-stop / resolve launcher / `am start -n` / chờ foreground theo
  trạng thái thật (không `sleep` cứng). Mở app bằng component PMS trả về, **không dùng
  `monkey`**: monkey bắn sự kiện thật vào màn hình, gặp quảng cáo hay paywall là bấm bừa.
  PMS không resolve được → báo thẳng "máy đang khoá", vì lỗi đó nhìn y hệt app hỏng.
- `case_run.py` — patch → tắt hẳn app → mở lại → verify → restore.
- `rc_snapshot.py` — lưu nguyên văn config gốc khi giữ patch. **Lỗ hổng đã vá:**
  `rc_patch.restore` chỉ trả về được baseline đọc trong cùng lượt; giữ patch rồi chạy lượt
  khác thì baseline đọc được đã là bản đã patch, "restore" lúc đó ghi lại chính giá trị bẩn.
- `tc_select.py` — chọn bộ case: workbook nhiều tab thì qua `tc_catalog` (cần `--sdk`),
  file một sheet thì `tc_loader`. Thiếu `--sdk` → dừng, không lấy bừa tab đầu.
- `cli_check.py` + entry point `rcr-check` — một lượt headless, stdout 1 dòng JSON.
  Case có `variants` chạy lần lượt từng lượt; verdict case = lượt xấu nhất.
- `sdk_probe.py` — đo bản SDK FO từ logcat (`VslTemplate4FirstOpenSDK: Using version X`).
  Đọc buffer sẵn có trước, không có mới mở lại app (xoá buffer trước để không nhặt
  phải bản của lượt trước). **Bản SDK không suy ra được từ versionName app**: Piclux
  2.8.0 nhúng SDK 3.5.4-alpha02 — đo 2026-09-25 trên Pixel 7.
- `dex_check.py` — soi chuỗi key trong `classes*.dex` của **mọi** APK (base + split),
  cache theo `(package, versionCode)`. Key không có → `KEY_NOT_USED`, không mở app.
  Đo thật trên Piclux: `enable_101_spl_a_banner` có trong RC mà DEX không có →
  đúng hiện tượng "có key trong config ≠ app dùng key đó" đã ghi ở phần Facts.
- `device_reset.py` + `data/reset_rules.yaml` — ba mức: `force-stop` (mặc định) /
  reset mềm (lật `ARG_KEY_SHOW_ONBOARDING`) / `pm clear` (chỉ khi app không có cờ đó).
  Luật "cần state sạch" đọc từ YAML, khớp cả tiếng Việt có dấu lẫn không dấu.
  Sau `pm clear` chờ app sinh lại `frc_*.json` rồi mới cho patch (ghi bằng redirect
  cần file đích tồn tại sẵn), và trả `baseline_stale` để người gọi đọc lại baseline.
- `ui_dump.py` — chụp `uiautomator dump` + parse thành cây node. Giữ
  `index_in_parent` vì resource-id **không unique** (2 hàng cùng có nút `See All`).
  Tap đi thẳng vào pixel, không quy đổi dp — quy đổi là thêm một chỗ sai mà không được gì.
- `act_resolver.py` — 4 dạng câu: `Quan sát…` → NoOp, chuỗi trong ngoặc kép → Tap,
  `Mở tab X` → Tap, `Chờ N giây` → Wait. Còn lại → NeedsHuman kèm nguyên văn câu.
  **0 node hoặc >1 node khớp đều là NeedsHuman** — không bao giờ lấy node đầu tiên.
  Node lồng nhau cùng khớp thì chỉ tính node ngoài (cùng một chỗ, đừng đếm 2 lần).
- `case_drive.py` — chạy lần lượt từng bước, dừng ngay khi gặp bước không dịch được.
  Màn hình bị che **chỉ chặn bước phải chạm vào màn hình** (Tap): không tự tìm nút X —
  bấm lệch là vào chính quảng cáo. Bước *quan sát* và bước *chờ* vẫn đi tiếp, và được đánh
  dấu `screen_blocked` để phase 5 biết dump đó không phải UI app — case ads chấm bằng log
  request/load, mà inter thường đè lên trước khi kịp nhìn thấy banner (quyết định 30).
  Dump mỗi bước giữ lại cho phase 5.
- Slash command `/rc-check` (`~/.claude/commands/rc-check.md`).

Đã chạy thật 2026-09-25 trên Pixel 7 `29301FDH2006K7`,
`aiphotogenerator.photoshoot.aiart.aiimagegenerator` (206 key, 96 mirror, `run-as`):
patch → mở lại (foreground 1.6s) → `CONFIG_OK` → restore sạch; vòng `--keep` → `--restore`
trả đúng giá trị gốc kèm mốc fetch cũ.

**Reset mềm verified trên Piclux 2026-09-25** (Pixel 7, `aiphotogenerator.photoshoot...`):
lật cờ `false → true` → mở app → activity stack có `VslTemplate4Language14Activity`,
tức app quay lại luồng first-open (Language → Onboarding) mà **không** `pm clear`,
giữ nguyên login/ngôn ngữ. Cờ trả về `false` sau khi đo.

Lưu ý khi tự nhìn tận mắt: màn onboarding nằm **sau splash ad**, ad không tự đóng.
Tool cố tình không tap để đóng ad (tap sai chỗ = bấm quảng cáo thật) — đóng ad bằng tay
rồi chạy tiếp. `case_drive` nhận ra màn này và dừng kèm lý do, **đo thật 2026-09-25**
trên Piclux: `com.google.android.gms.ads.AdActivity` → `NEEDS_HUMAN`, 0 lệnh tap.

**act_resolver verified trên máy 2026-09-25** (Pixel 7, màn Cài đặt — chọn màn không có
quảng cáo để không phải bấm bừa): `Nhấn vào "Mạng và Internet"` → tap (449, 828) →
màn hình đổi sang trang Internet/SIM; `Chờ 2 giây` → wait; `Quan sát màn hình` → noop.

Verdict của lát này chỉ có `CONFIG_OK` / `BLOCKED` / `KEY_NOT_USED` — **chưa có PASS/FAIL**,
vì chưa ai nhìn màn hình app. Gọi PASS ở đây là pass giả.

## Chạy trên bộ TC chung thật (2026-09-25)

File `TC SDK` 56 tab (link Google Sheet do user đưa), app Piclux 2.8.0 / SDK FO 3.5.4-alpha02:
**538 case, 347 case tool chạy được**, chia theo tab: 6.4.0 65 · 3.2.0 42 · 3.3.0 25 ·
3.4.0 50 · 3.5.0 53 · widget 22 · rating 90. Tab `daily checkin` tự bị loại (app không có
key nào của tính năng đó). Ghi chú đúng: app 3.5.4 mới hơn delta mới nhất (3.5.0).

**Hai lỗi chỉ lộ ra khi chạy file thật, đã vá:**

1. **Đọc nhầm bản SDK của app khác.** Tag `VslTemplate4FirstOpenSDK` không riêng của app
   nào — mọi app nhúng SDK VisionLab đều in, mà logcat thì chung cả máy. Lượt đầu đo ra
   `3.5.4-alpha02`, lượt sau ra `3.5.3` cho cùng một app, chỉ vì app khác vừa chạy.
   → `sdk_probe` lọc theo **PID của app đích** (`pidof`), và lấy dòng **mới nhất**.
   App chưa chạy thì mở lại app chứ không đọc buffer chung.
2. **Số case trùng nhau giữa các tab đè lên nhau im lặng.** Số `1` có ở 5 tab; khoá dict
   là con số nên đếm ra **120 case chạy được trong khi thật ra là 347** — mất 227 case mà
   không báo gì. → khoá là `<bản SDK>#<số>` (`6.4.0#1`). Gõ `--case 12` vẫn được nếu số đó
   chỉ có ở một tab; mơ hồ thì dừng và liệt kê, không chạy bừa.

**Độ phủ `act_resolver` đo trên 1272 bước thật:** 597 noop · 42 wait · 159 nhận ra là tap ·
**473 chưa dịch được (37%)**. Phần chưa dịch được là *cả một chuỗi màn hình*
("Hoàn thành luồng FO đến Home", "Vào màn Onboarding 2", "Trigger popup Rating") — đúng
phạm vi round 1, đoán là lạc ngay từ bước đầu. Ba luật thêm sau khi đo: `Mở app` /
`Cold start app` → NoOp (tool đã mở app rồi), `Config RC` → NoOp (vừa đặt xong),
`Bấm <tên nút>` không ngoặc kép → Tap **vẫn phải khớp duy nhất**.

**Chạy trọn case `6.4.0#1`:** soi DEX (3 key app đều đọc) → reset mềm (khớp "first open")
→ patch 3 key → mở lại app → `CONFIG_OK` → lái hết 3 bước (`Mở app` noop, `Chờ Splash load`
wait, `Quan sát bottom banner` noop, bước 3 đánh dấu `screen_blocked` vì inter đang đè)
→ đọc log ads: 2 banner unit đã request, `adBannerState None → Loading → Fail` → restore.

Còn lại của phase 4: route `POST /api/run-case` (web UI — phase 6 mới cần).

## Requirements
- Functional: `run_case(case)` → chuỗi reset/patch/launch/verify đúng thứ tự đã chốt
- Functional: quyết định **có clear data hay không** từ nội dung Precondition
- Functional: `act_resolver` dịch được `Mở tab <tên>`, text trong ngoặc kép, `Quan sát...`
- Functional: không dịch được → `NEEDS_HUMAN`, dừng case, **không đoán và không tap bừa**

## Architecture

```
device_reset.prepare(case, baseline, overrides) -> PrepareResult
  can_sach = precondition khop luat "state sach"
  if can_sach:
      pm clear pkg
      am start  -> cho tới khi frc_*.json xuat hien (poll toi 30s) -> force-stop
      doc lai baseline (appId khong doi, nhung file vua sinh)
  else:
      force-stop
  rc_patch.patch(...)
  am start
  rc_verify.verify(...)  -> lech thi BLOCKED, dung case
```

**Luật "cần state sạch"** — Precondition khớp bất kỳ mẫu nào: `chưa từng`, `lần đầu`,
`first open`, `mới cài`, `onboarding`, `chưa đăng nhập`, `xoá data`, `cài lại`.
Không khớp → chỉ `force-stop`. Luật để trong `data/reset_rules.yaml`, không hardcode.

**Reset first-open MỀM (ưu tiên hơn `pm clear`)** — đã verify tay 2026-09-07: lật
`ARG_KEY_SHOW_ONBOARDING` = `true` trong `shared_prefs/vsl_template4_prefs.xml` là app vào lại
`VslTemplate4OnboardingActivity`, **giữ nguyên login/ngôn ngữ/data**. Rẻ hơn `pm clear` rất
nhiều và không mất bước "mở app lần đầu cho SDK sinh file frc_".
Thứ tự thử: file đó có `ARG_KEY_SHOW_ONBOARDING` → reset mềm; không có → `pm clear`.
**Đây là thao tác reset, KHÁC HOÀN TOÀN patch config** — `rc_patch` vẫn tuyệt đối không ghi
vào `vsl_template4_prefs.xml` (xem phase 2).

```
act_resolver.resolve(step, nodes) -> Action | NeedsHuman
  1. ^quan sát|kiểm tra|xem|quan sát lại   -> NoOp (chuyen sang cham)
  2. "chuỗi trong ngoặc kép"               -> tim node text==/contains chuoi -> Tap(node)
  3. ^mở tab (\w+)                         -> tim node trong nav bar co text/desc khop -> Tap
  4. ^chờ|đợi (\d+)?                       -> Wait
  5. con lai                               -> NeedsHuman(step)
```

Tap qua `adb shell input tap <cx> <cy>` với tâm `bounds` của node. **Chỉ tap khi resolver
chắc chắn** — 0 node hoặc >1 node khớp → `NeedsHuman`, không lấy node đầu.

**Tool không tự bấm ngoài phạm vi case đang chạy.** Một cú tap sai chỗ là bấm vào quảng cáo
hoặc mua hàng thật (nguyên tắc đã có trong `tsa/adb_operations.py`).

## Related Code Files
- Create: `src/rcr/device_reset.py`, `src/rcr/act_resolver.py`, `src/rcr/case_runner.py`
- Create: `src/rcr/data/reset_rules.yaml`
- Create: `src/rcr/ui_dump.py` — port từ `~/projects/ui-spec-verifier/src/usv/ui_dump.py`
  (`parse_dump`, `app_nodes`, `parse_bounds`, `strip_package`, `is_system_node`)
- Modify: `src/rcr/models.py` (+ `Action`, `Tap`, `NoOp`, `Wait`, `NeedsHuman`, `DeviceNode`)
- Create: `tests/test_device_reset.py`, `tests/test_act_resolver.py`
- **Create: `fixtures/TC_<app-thay-the>_remote_config.xlsx`** — file TC viết cho
  `com.ai.videogenerator.photocreator.aiart`

## Pre-check DEX: app có đọc key không

Trước khi patch bất kỳ case nào, kiểm app có tham chiếu key hay không — rẻ, không cần mở app:

```
dex_check(package, keys) -> dict[key, bool]
  adb shell pm path <pkg>   ->  TAT CA duong dan apk (khong chi base.apk)
  moi apk: adb pull -> unzip 'classes*.dex' -> grep -a <key>
  key khong co string trong BAT KY dex nao  ->  app KHONG doc key do
```

**PHAI quet moi APK, khong chi `base.apk`.** App cai tu AAB qua Play bi chia thanh
base + split (do that tren may: TikTok **101** file, Slack 3 file) va key co the nam trong
`split_df_*.apk` cua feature module -> grep mot minh `base.apk` se bao `KEY_NOT_USED` OAN.
App Apero hien deu 1 `base.apk` (sideload tu APK don) nen khong vap, nhung tool phai dung
cho ca app cai qua Play.

Key không có trong DEX → case trả `KEY_NOT_USED`, **không chạy app**. Đã verify: `songmaker`
không có `splash_banner_change` trong DEX, và runtime xác nhận app không đọc key đó (banner
show bất kể `true`/`false` → nếu chấm ngây thơ sẽ ra **PASS giả**).
Cache kết quả theo `(package, versionCode)` — pull APK ~50MB, không pull lại mỗi case.

## Implementation Steps
1. Port `ui_dump.py` + phần `DeviceNode` từ `usv/models.py`. Giữ nguyên API để phase 5 dùng lại.
2. `adb_client`: thêm `tap(serial, x, y)`, `force_stop`, `clear_data`, `wait_for_file`.
   `clear_data` là **destructive** → chỉ gọi từ `device_reset`, không expose ra route trần.
3. `device_reset.py`: luật YAML + chuỗi lệnh như Architecture. Poll `frc_*.json` sau `pm clear`
   thay vì `sleep` cố định.
4. `act_resolver.py`: 5 luật, thuần hàm trên `list[DeviceNode]` → test bằng fixture XML dump.
5. `case_runner.py`: ghép prepare → resolve từng step → tap/wait → trả `CaseRun` (chuỗi bước
   đã làm + dump ở mỗi bước, để phase 5 chấm).
6. ~~Tạo file TC mẫu cho app thay thế~~ — **bỏ** (2026-09-23): dùng bộ TC chung theo bản SDK
   (quyết định 22). Thay bằng: đọc bản SDK từ `VslTemplate4FirstOpenSDK: Using version X`,
   so với dòng `spec: SDK ...` đầu sheet, lệch → cảnh báo (quyết định 23).
7. `dex_check.py`: pull APK + unzip dex + grep key, cache theo `(package, versionCode)`.
8. Route `POST /api/run-case` chạy 1 case, trả log từng bước.
9. **Trước mỗi case**: force-stop các app ads khác trên máy + `KEYCODE_HOME` (quyết định 24).
   Đo 2026-09-23: `com.aiprofile...` chạy nền bung `AdActivity` đè splash → SDK FO đứng chờ.
10. **Bước mạng** trong Precondition/Action (`Tắt wifi/data`, `Bật lại mạng khi đã qua Splash`)
    → `svc wifi|data disable/enable`; "đã qua Splash" = chờ log `<Activity> is showing` của
    màn kế. Luôn bật lại mạng trong `finally`.

## Success Criteria
- [ ] Case có Precondition "chưa từng mở app" → có `pm clear`; case chỉ đổi flag → chỉ `force-stop`
- [ ] Sau `pm clear`, tool chờ được `frc_*.json` xuất hiện rồi mới patch (không sleep cứng)
- [ ] `verify` lệch → case trả `BLOCKED`, **không** đi tiếp và không chấm FAIL
- [ ] `Mở tab Moment` resolve ra đúng node nav bar trên fixture dump
- [ ] `Nhấn nút "See All" của hàng AI Album` → resolve được qua chuỗi trong ngoặc kép
- [ ] `Nhấn thẳng vào 1 thẻ style bất kỳ trong hàng AI Video` → `NEEDS_HUMAN` (đúng kỳ vọng)
- [ ] 2 node cùng khớp → `NEEDS_HUMAN`, không tap node đầu
- [ ] Chạy được trọn case 5-10 bộ TC chung (`SDK tutorial 3.0.2`) trên `com.ai.videogenerator.photocreator.aiart`
- [ ] App đích SDK 3.2.0, sheet ghi 3.0.2 → report có cảnh báo lệch bản
- [ ] Case 10 (tắt/bật mạng) chạy tự động, mạng được bật lại kể cả khi case lỗi
- [ ] Reset mềm: lật `ARG_KEY_SHOW_ONBOARDING` → app vào `VslTemplate4OnboardingActivity`,
      login/ngôn ngữ **không mất**
- [ ] `dex_check(songmaker, ['splash_banner_change'])` → `False` (đã verify tay)
- [ ] `dex_check(lingospeak, ['splash_banner_change','show_105_spl_n_native'])` → cả 2 `True`
- [ ] Mọi module <200 LOC

## Risk Assessment
- **`pm clear` mất login + onboarding của app** trên máy tester. Route phải cảnh báo trước
  (khuôn `OpSpec.warning` của `tsa/adb_op_specs.py`), và chỉ chạy trong luồng case.
- **Tap sai chỗ = bấm quảng cáo/mua hàng thật.** Nên resolver thà `NEEDS_HUMAN` còn hơn đoán.
- **App chưa chạy xong splash** khi dump → node chưa có, resolver báo không tìm thấy oan.
  Poll `current_focus` == package + dump lại tối đa N lần trước khi kết luận.
- **Bộ TC chung ghi key bắt buộc ở Precondition** (không ở Test Data) → case chạy thiếu key
  (vd case 6 chỉ đặt `layout2`). Chờ chốt câu hỏi mở #4 trong `plan.md`.
- **Tắt mạng trên máy tester** (case mạng): quên bật lại là hỏng các lượt sau → `finally`.
