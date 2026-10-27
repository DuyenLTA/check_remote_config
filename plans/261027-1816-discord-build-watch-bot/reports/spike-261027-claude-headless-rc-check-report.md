# Spike: `claude -p` chạy `/rc-check` headless (27/10/2026, Windows, claude 2.1.311)

Lệnh: `claude -p "/rc-check com.remote.casttotv.screenmirroring --preflight" --output-format json --allowedTools Bash Read Edit Write Artifact Skill`
(không cắm máy)

| Đo | Kết quả |
|---|---|
| Hỏi quyền / treo | Không. `permission_denials: []`, exit 0 |
| Thời gian | 26s, 6 turn |
| Chi phí | $0.69 cho lượt dừng ở preflight → lượt đầy đủ sẽ lớn hơn nhiều |
| Output | JSON có `result` (văn bản cuối), `is_error`, `total_cost_usd`, `duration_ms` |
| Slash command | Chạy được trong `-p` |
| Discord | Claude tự gọi `rcr-notify` báo dừng (webhook) — lượt bot sẽ có 2 nguồn tin: webhook + bot |

## Lưu ý
- Gọi từ **Git Bash** thì MSYS đổi `/rc-check` → `C:/Program Files/Git/rc-check`. Bot gọi `subprocess` thẳng từ Python (không qua bash) → không bị.
- Chưa đo: **publish Artifact headless** (cần máy để chạy tới report). Đo lại khi cắm máy.

## Chưa làm (cần máy)
- Spike 2: lái App Tester tải + cài, lưu fixture XML
- Spike 3: cài bản debug đè bản release

## Câu hỏi còn mở
- Lượt bot có nên tắt webhook (`DISCORD_NOTIFY=0`) để kênh không nhận tin trùng không?
