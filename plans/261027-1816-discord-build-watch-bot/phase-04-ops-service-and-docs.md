---
phase: 4
title: "Vận hành: service, hướng dẫn tạo bot, README"
status: pending
priority: P2
effort: "2h"
dependencies: [3]
---

# Phase 4: Vận hành

## Overview
Bot phải sống khi đóng terminal / khởi động lại máy, và người khác cài lại được từ README.

## Requirements
- File mẫu `deploy/rcr-bot.service` (systemd **user** service, `Restart=on-failure`, đọc env từ `~/.config/rcr/bot.env` quyền 600)
  — user tự `systemctl --user enable --now` (không tự bật thay user)
- Hướng dẫn tạo bot từng bước: Developer Portal → New Application → Bot → bật **Message Content Intent** →
  OAuth2 URL (scopes `bot`, `applications.commands`; quyền Read/Send Messages, Read History) → mời vào server →
  lấy channel ID / role ID (Developer Mode)
- README: mục "Bot build-watch", bảng env, cách xem log (`journalctl --user -u rcr-bot`)
- `rc-check.md`: ghi lượt do bot gọi đi qua khoá máy chung; lượt tay đang chạy thì bot chờ

## Related Code Files
- Create: `deploy/rcr-bot.service`, `docs/discord-bot-setup.md`
- Modify: `README.md`, `.claude/commands/rc-check.md`

## Success Criteria
- [ ] Reboot máy → bot tự lên, vẫn bắt tin build
- [ ] Người mới cài theo README không cần hỏi

## Risk Assessment
- Máy tính ngủ / rút điện thoại → job lỗi `device not found`: báo kênh, giữ job trong hàng đợi để bấm chạy lại
