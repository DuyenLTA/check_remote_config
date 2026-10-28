---
phase: 4
title: "Docs + chạy thật một lượt"
status: pending
priority: P2
effort: "1h"
dependencies: [3]
---

# Phase 4: Docs + lượt thật

## Requirements
- Docs: README mục bot (biến `JIRA_URL`, `JIRA_PERSONAL_TOKEN` trong `~/.config/rcr/bot.env`; tắt = bỏ token);
  docstring đầu `discord_bot.py` thêm 2 biến; `.claude/commands/rc-check.md` §7b thêm ý 5: lượt verify do bot gọi
  (`--case`, không log/sửa Jira — bot tự làm); `plans/261027-1816-discord-build-watch-bot/plan.md` thêm dòng tham chiếu
- Lượt thật: chọn 1 issue bot đã tạo (vd AIP920-13), dev/QA chuyển Reviewing, đăng (forward) tin build cùng mã app
  → xác nhận: tin 🔁 ở qa-auto, cài đúng bản, chỉ chạy case đó, comment + trạng thái đúng

## Related Code Files
- Modify: `README.md`, `src/rcr/discord_bot.py` (docstring), `.claude/commands/rc-check.md`, `plan.md` cũ

## Success Criteria
- Một lượt thật end-to-end ghi lại ở `plan.md` mục "Đã biết" (thời gian, chi phí, verdict, trạng thái Jira sau)

## Risk Assessment
- Lượt thật đổi trạng thái issue thật → chọn issue user đồng ý; sai thì QA chuyển tay lại + ghi lỗi

## Next Steps
- Không commit khi user chưa bảo
