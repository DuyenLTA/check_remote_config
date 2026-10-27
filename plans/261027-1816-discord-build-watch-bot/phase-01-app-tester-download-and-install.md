---
phase: 1
title: "Lấy build từ App Tester + cài lên máy"
status: pending
priority: P1
effort: "5h"
dependencies: [0]
---

# Phase 1: Lấy build từ App Tester + cài lên máy (`rcr-cai-build`)

## Overview
User chốt 27/10/2026: **lấy build từ App Tester** (Firebase App Distribution), không từ Drive — link Drive chỉ chứa
apk/aab để ASO submit; dev sẽ đẩy thêm **bản debug** lên App Tester. Lệnh độc lập, chạy tay được không cần bot:
`rcr-cai-build --package <pkg> --version "4.3.0 (40)" --loai debug|release [--serial S]` (bot chọn `--loai` theo SDK trong tin) → 1 dòng JSON
`{package, version, debuggable, da_cai, go_ban_cu}`.

## Đã đo trên máy (27/10/2026, Pixel 6)
- App Tester `dev.firebase.appdistribution` v0.133 đã cài, đã đăng nhập tài khoản tester
- Màn danh sách: mỗi app có `app_name`, **`bundle_id`** (= package), `app_description` ("55 releases")
- Màn chi tiết app: `bundle_id`, `installed_version_info` ("Version 1.4.0 (14) installed"), ô **`search_releases_bar`**,
  mỗi release có `version_info` ("1.4.0 (14)"), nhãn `labels_latest_release` / `labels_installed_release`,
  `distributed_at`, `release_notes_full`, nút `open_button` (bản đã cài; bản chưa cài là nút tải — đo ở phase 0)
→ lái được **theo resource-id**, không tap theo toạ độ.

## Vì sao lái UI chứ không gọi API
Firebase App Distribution API (`releases.list` → `binaryDownloadUri`) cần quyền IAM trên **từng** project Firebase
(mỗi app một project) — tester không có. App Tester trên máy dùng chính quyền tester → lái UI. Nếu sau này admin cấp
service account thì thay riêng bước tải, phần còn lại giữ nguyên.

## Requirements
- Tìm app theo **`bundle_id` khớp chính xác package** (cuộn danh sách tới khi thấy); không khớp theo tên app
- Trong app: gõ version vào `search_releases_bar`, chọn release có `version_info` **khớp chính xác** `4.3.0 (40)`;
  0 hoặc >1 kết quả → dừng kèm lý do, **không chọn bừa**
- **Chọn bản theo SDK dev ghi trong tin** (user chốt 27/10/2026). Bản debug = release **cùng app, cùng package**,
  `release_notes_full` có chữ `debug` (không phân biệt hoa thường); bản release = release cùng version, note không có `debug`.

  Quyết định bằng **chữ next-gen trong tin**, KHÔNG bằng số bản tutorial (next-gen ads và bản tutorial độc lập — mẫu thật dưới):

  | Tin dev ghi | Cài bản | Vì sao |
  |---|---|---|
  | `apply next-gen` / `next-gen` (không có `revert`), hoặc tutorial `3.7.0` | **release** | checklist Next-Gen (= tutorial 3.7.0) chấm được trên bản release |
  | `revert next-gen` | **debug** | không phải next-gen → nhánh bộ TC, phải patch Remote Config |
  | không nhắc next-gen | **debug** | debug chạy được mọi nhánh |

  - Bản cần chọn có đúng 1 → cài. Không có → **không tự đổi sang loại kia** (bot đã kiểm trước ở phase 2, xem `--chi-kiem`).
    Có > 1 bản cùng loại cùng version → dừng, liệt kê `distributed_at`, không chọn bừa
- **`--chi-kiem`** (user chốt 27/10/2026: vào App Tester xem có bản chưa rồi mới báo): chỉ mở App Tester, kéo làm mới,
  tìm app + version, liệt kê các release khớp version kèm loại (debug/release) và `distributed_at` → JSON
  `{co_ban: bool, cac_ban: [...]}`; **không tải, không cài**, xong về Home. ~20s, vẫn phải giữ khoá máy
  - SDK trong tin chỉ để **chọn bản cài**. Nhánh chấm vẫn do `--preflight` đọc từ log app quyết định (mục 0b rc-check):
    tin ghi Next-Gen mà log ra bản khác → preflight báo `LOI` (bản release không debuggable) → bot báo "tin ghi SDK lệch
    log, cần bản debug", không chạy mù
- Bấm tải → chờ tải xong → hộp cài của Android: bấm **Install/Update** theo resource-id của package installer
- Xác nhận bằng `dumpsys package <pkg>`: versionName + versionCode khớp, cờ `DEBUGGABLE`
- Bản debug ký bằng key debug, bản release ký key thật, **cùng package** → đổi qua lại luôn báo khác chữ ký
  (`INSTALL_FAILED_UPDATE_INCOMPATIBLE` hoặc App Tester báo lỗi cài) → `pm uninstall` rồi cài lại, `go_ban_cu: true` (mất data, báo kênh)
- Chặn tuyệt đối: chỉ tap node đã khớp id + text; màn lạ / hộp Play Protect lạ → dừng, chụp màn, báo

## Ánh xạ tin Discord → package
Tin dev: `Bản build AIP882---AI-Video v4.3.0 (40)`. Bot tách **mã app** (`AIP882`) + **version** (`4.3.0 (40)`), rồi lấy
package từ sheet "Check thông số KT" — tab trùng mã app, dòng `Package name` (đã có `ad_units_sheet` đọc sheet này).
Không có tab → hỏi QA package trong kênh, không đoán theo tên.

## Architecture
```
app_tester_ui.py     mở App Tester, tìm app theo bundle_id, tìm release theo version, tải + cài (adb + uiautomator)
build_ma_app.py      tách mã app + version + SDK từ tin → loại bản (debug/release); mã app → package qua sheet KT
cli_cai_build.py     ghép lại + xác nhận bằng dumpsys
```
Dùng lại: `adb_client`, cách dump/tìm node của `act_nodes` / `ui-dump.sh`, `ad_units_sheet` (tải sheet KT).

## Related Code Files
- Create: `src/rcr/app_tester_ui.py`, `src/rcr/build_ma_app.py`, `src/rcr/cli_cai_build.py`
- Create: `tests/test_app_tester_ui.py` (dump XML thật đã lưu làm fixture), `tests/test_build_ma_app.py`
- Modify: `pyproject.toml` (script `rcr-cai-build`)
- Thêm id của App Tester + package installer vào `data/ui_names.yaml` (không viết cứng trong code)

## Implementation Steps
1. Lưu dump XML thật các màn (danh sách, chi tiết, đang tải, hộp cài) làm fixture
2. Hàm thuần: tìm node theo id+text trong XML → toạ độ; test bằng fixture
3. Luồng lái: mở app → cuộn tìm bundle_id → search version → tải → cài → dumpsys xác nhận
4. Tách tin + tra sheet KT

## Success Criteria
- [ ] `rcr-cai-build --package com.remote.casttotv.screenmirroring --version "1.4.0 (14)"` báo đã cài đúng bản
- [ ] Cài được 1 bản chưa có trên máy (tải thật), dumpsys khớp version
- [ ] Version không có trên App Tester → lỗi rõ ràng, không tap gì thêm
- [ ] `--chi-kiem` thấy đúng bản debug/release của 1 version có cả hai, không cài gì
- [ ] `pytest -q` xanh

## Risk Assessment
- App Tester đổi UI → id đổi: id để trong yaml, test fixture báo sớm
- Hộp "cho phép cài từ nguồn này" / Play Protect lần đầu → làm tay 1 lần lúc setup (phase 4 ghi lại)
- Tải chậm (60–300 MB): chờ có giới hạn, theo dõi chữ % trên màn
- Màn hình phải mở khoá suốt lúc lái (preflight đã kiểm)
