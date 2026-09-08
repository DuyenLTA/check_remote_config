---
phase: 4
title: "device_reset + act_resolver (hep)"
status: pending
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
6. **Tạo file TC mẫu cho app thay thế**: mở app trên máy, `uiautomator dump` để biết UI thật,
   chọn 5-8 key RC thật của app (từ ~200 key baseline) mà đổi được thấy ngay trên UI
   (ưu tiên nhóm `enable_*` điều khiển màn onboarding — nằm trong mirror nên test luôn cả
   đường mirror). Viết đúng cấu trúc cột như file IIP032.
7. `dex_check.py`: pull APK + unzip dex + grep key, cache theo `(package, versionCode)`.
8. Route `POST /api/run-case` chạy 1 case, trả log từng bước.

## Success Criteria
- [ ] Case có Precondition "chưa từng mở app" → có `pm clear`; case chỉ đổi flag → chỉ `force-stop`
- [ ] Sau `pm clear`, tool chờ được `frc_*.json` xuất hiện rồi mới patch (không sleep cứng)
- [ ] `verify` lệch → case trả `BLOCKED`, **không** đi tiếp và không chấm FAIL
- [ ] `Mở tab Moment` resolve ra đúng node nav bar trên fixture dump
- [ ] `Nhấn nút "See All" của hàng AI Album` → resolve được qua chuỗi trong ngoặc kép
- [ ] `Nhấn thẳng vào 1 thẻ style bất kỳ trong hàng AI Video` → `NEEDS_HUMAN` (đúng kỳ vọng)
- [ ] 2 node cùng khớp → `NEEDS_HUMAN`, không tap node đầu
- [ ] Chạy được trọn 1 case trên `com.ai.videogenerator.photocreator.aiart` bằng file TC tự tạo
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
- **File TC tự tạo có thể không đại diện** cho file thật của AIP922 (cấu trúc cột, cách viết
  Action). Rủi ro chấp nhận được ở round 1; phase 3 đã map theo tên cột nên đỡ được phần lớn.
