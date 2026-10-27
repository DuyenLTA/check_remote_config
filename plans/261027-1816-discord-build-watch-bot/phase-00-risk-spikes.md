---
phase: 0
title: "Spike rủi ro"
status: pending
priority: P1
effort: "1h"
dependencies: []
---

# Phase 0: Spike rủi ro — đo trước khi viết code

## Overview
Ba giả định mà sai thì cả thiết kế đổi. Đo trên máy thật, ghi kết quả vào `plans/.../reports/`.

## Requirements
1. **`claude -p` có chạy được `/rc-check` + publish Artifact không** khi không có người ngồi trước terminal:
   quyền tool (Bash adb, Artifact), đăng nhập claude.ai, thời gian tối đa, lấy được URL artifact từ output.
2. **Tải + cài qua App Tester bằng adb**: chọn 1 release CHƯA cài → dump màn trước/trong/sau khi bấm tải, hộp cài của
   Android (`com.google.android.packageinstaller`), Play Protect, quyền "cài từ nguồn này" → lưu XML làm fixture.
3. **Bản debug trên App Tester** (release cùng app, note có `debug`): cài đè lên bản release cùng package → App Tester
   báo lỗi gì / hộp gì khi khác chữ ký, để phase 1 nhận ra và gỡ app đúng lúc.

## Implementation Steps
1. `claude -p "/rc-check <pkg> --preflight" --output-format json --allowedTools "Bash Read Edit Write Artifact Skill"` →
   xem có hỏi quyền/treo không, `result` có link không. Thử thêm 1 lượt nhỏ có publish.
2. Lái tay bằng adb từng bước trên 1 release thật, sau mỗi bước `uiautomator dump`; không tap node chưa thấy trong dump.
3. Nhờ dev đẩy 1 bản debug của 1 app lên App Tester; quan sát + cài thử.

## Success Criteria
- [ ] Biết chính xác cờ `claude -p` cần (hoặc biết là KHÔNG publish được headless → phase 3 đổi sang publish ở phiên tương tác / gửi file HTML lên Discord)
- [ ] Có fixture XML đủ các màn tải/cài của App Tester; 1 bản chưa có trên máy cài được bằng adb
- [ ] Biết App Tester báo gì khi cài bản debug đè bản release (khác chữ ký)

## Risk Assessment
- Headless không publish Artifact được → fallback: đính kèm report HTML vào tin Discord (đã có trong `discord_notify` cho `--khong-claude`)
- `--dangerously-skip-permissions` **không dùng**: lượt lái máy thật, chỉ mở đúng danh sách tool
