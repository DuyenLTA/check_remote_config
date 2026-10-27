---
phase: 3
title: "Chạy Claude headless + đăng kết quả"
status: pending
priority: P1
effort: "3h"
dependencies: [0, 2]
---

# Phase 3: Chạy `/rc-check` bằng Claude headless + đăng kết quả vào kênh

## Overview
Sau khi cài xong: `claude -p "/rc-check <package>" ...` (cờ chốt ở phase 0) trong `<repo>`, giới hạn thời gian,
đọc kết quả, đăng vào kênh: verdict tóm tắt + link artifact (hoặc file HTML nếu headless không publish được).

## Requirements
- Prompt cố định, chỉ ghép **package đã xác nhận bằng dumpsys** sau khi cài (không ghép chữ từ tin Discord → tránh prompt injection)
- Cuối prompt yêu cầu dòng máy-đọc-được: `KET_QUA: {"link": "...", "tom_tat": "..."}`
- Timeout (vd 120 phút nhánh bộ TC, 30 phút nhánh SDK 3.6.1); quá giờ → kill, báo kênh, trả máy (`--restore`)
- Preflight `LOI` (bản không debuggable, ID ads test…) → đăng nguyên bảng LOI vào kênh, dừng
- Có `ad_click` / điểm chặn của người → đăng tin + mention role QA, không tự chạy tiếp
- Log đầy đủ của lượt ở `out/bot-luot-<giờ>.log`

## Related Code Files
- Create: `src/rcr/bot_chay_claude.py`, `tests/test_bot_chay_claude.py`
- Modify: `src/rcr/discord_bot.py` (worker gọi bước này)

## Implementation Steps
1. Hàm `chay(package, repo, timeout)` → subprocess `claude -p`, parse `--output-format json`
2. Tách dòng `KET_QUA:`; thiếu thì đăng 300 ký tự cuối + đường dẫn log
3. Đăng kết quả: reply vào tin build gốc + đổi trạng thái tin bot

## Success Criteria
- [ ] Duyệt 1 build LingoSpeak thật → kênh nhận link report trong một lượt
- [ ] Preflight LOI → kênh nhận bảng LOI, không cài/chạy tiếp
- [ ] Timeout giả lập → máy được restore, kênh nhận báo

## Risk Assessment
- Chi phí token mỗi build (lượt bộ TC đầy đủ rất dài) → hiện số phút + nhắc trong tin; cân nhắc giới hạn số lượt/ngày
- Claude headless hỏi quyền rồi treo → danh sách `--allowedTools` cố định, timeout cứng
