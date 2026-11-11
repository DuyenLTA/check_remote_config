# Bảo mật và phân quyền dữ liệu — rc-check

Trang này trả lời 3 câu: workflow chạm vào dữ liệu gì, dữ liệu nằm ở đâu và ai đọc được, khi có người nghỉ hoặc
đổi vị trí thì thu hồi quyền thế nào. Cập nhật mỗi khi thêm nguồn dữ liệu hoặc token mới.

Repo `check_remote_config` là **repo public** trên cả hai tài khoản GitHub. Mọi thứ commit vào đây coi như ai cũng đọc được.

## 1. Phân loại dữ liệu

| Mức | Nghĩa | Quy tắc |
|---|---|---|
| **Bí mật** | Lộ ra là người ngoài hành động thay mình được | Chỉ nằm trong `~/.config/rcr/bot.env` (Linux, `chmod 600`) hoặc biến môi trường User (Windows). Không commit, không ghép vào prompt, không in ra log/Discord |
| **Nội bộ** | Tài liệu công việc của team, không phải mật khẩu | Không commit nội dung vào repo public. Đọc qua link có kiểm soát quyền |
| **Trên máy** | Sinh ra khi chạy, có thể chứa dữ liệu app | Nằm trong `out/` (đã `.gitignore`), chỉ trên máy chạy lượt |
| **Công khai được** | Code, luật chấm, tài liệu workflow | Commit bình thường |

## 2. Dữ liệu → nơi lưu → ai đọc được

| Dữ liệu | Mức | Lưu ở đâu | Ai đọc được | Ra khỏi hệ thống? |
|---|---|---|---|---|
| `DISCORD_BOT_TOKEN`, `DISCORD_WEBHOOK_URL` | Bí mật | `bot.env` / biến User | Chủ máy bot | Không |
| `JIRA_PERSONAL_TOKEN` (token cá nhân của người cài bot) | Bí mật | `bot.env` / biến User | Chủ máy bot | Không. Issue bot tạo mang tên chủ token |
| `CLAUDE_CODE_OAUTH_TOKEN` (`claude setup-token`) | Bí mật | `bot.env` | Chủ máy bot | Không |
| `CONFLUENCE_TOKEN` | Bí mật | Biến môi trường của máy chạy `rcr.spec_sync` | Chủ máy | Không |
| Đăng nhập Firebase CLI (`firebase login`) | Bí mật | Hồ sơ người dùng trên máy chạy lượt | Chủ máy | Không. Chỉ ghi giá trị điều kiện `testvsl` |
| Spec SDK từ Confluence | Nội bộ | `src/rcr/data/specs/` (`.gitignore`, tải lại bằng `rcr.spec_sync`) | Người có quyền Confluence | Không |
| Sheet bộ TC, sheet "Check thông số KT" (ID ads), sheet TC sub | Nội bộ | Google Sheet, tool tải lại mỗi lệnh | Xem mục 4 | Xem mục 4 |
| Sheet plan tuần | Nội bộ | Google Sheet, link trong biến `RC_PLAN_TUAN_SHEET` (không trong repo) | Ai có link | Không |
| Log app, ảnh màn hình, file lượt `*.luot.json`, `usage-log-bot.md` | Trên máy | `out/` | Người dùng máy chạy lượt | Report đưa lên artifact riêng tư / Discord nội bộ |
| Report kết quả | Nội bộ | Artifact claude.ai (mặc định riêng tư) + tin trong kênh QA Discord | Thành viên server Discord được chia sẻ | Có, trong phạm vi team |
| Nội dung bug (tiêu đề, bước, log) | Nội bộ | Jira project của app | Thành viên project Jira | Có, trong phạm vi team |
| Tên hiển thị người duyệt | Nội bộ | `out/usage-log-bot.md` | Người dùng máy bot | Không |

### Chặn rò rỉ đang có trong code

- **Prompt cố định cho Claude chạy không người:** chỉ ghép package đã xác nhận bằng `dumpsys`; chữ trong tin Discord
  (ai cũng gõ được) không vào prompt (`src/rcr/bot_chay_claude.py`). Bug đưa qua file JSON và được coi là dữ liệu
  (`src/rcr/bot_log_jira.py`).
- **Chỉ mở đúng danh sách tool** (`--allowedTools`), không dùng `--dangerously-skip-permissions`.
- **Web UI chỉ nhận `127.0.0.1`:** tool không có đăng nhập mà điều khiển được adb; middleware chặn host khác (`src/rcr/main.py`).
- **Firebase bản release:** chỉ gắn / gỡ giá trị của điều kiện `testvsl`; cấm đụng default, condition hay tham số người khác.
- **`bot.env` quyền 600** do `deploy/cai-bot-linux.sh` và `deploy/cai-24-24-ubuntu.sh` đặt.
- **Quét lịch sử git 11/11/2026:** 269 commit, không thấy token Discord / Jira / Claude / GitHub / Google API hay webhook.

## 3. Thu hồi quyền khi có người nghỉ hoặc đổi vị trí

Làm theo thứ tự, mỗi dòng xong thì tick. Người làm: trưởng nhóm QA hoặc người tiếp quản bot.

| # | Việc | Ở đâu | Sau khi làm |
|---|---|---|---|
| 1 | Reset token bot Discord (Reset Token), dán token mới vào `bot.env` mọi máy bot | Discord Developer Portal → Bot | Token cũ chết ngay. Restart bot khi rảnh |
| 2 | Xoá webhook cũ, tạo webhook mới | Kênh Discord → Integrations | Cập nhật `DISCORD_WEBHOOK_URL` |
| 3 | Thu hồi Jira personal token của người rời đi; người tiếp quản tạo token của mình | Jira → Profile → Personal Access Tokens | Issue mới mang tên người tiếp quản. Đổi `DISCORD_JIRA_REVIEWER` nếu cần |
| 4 | Thu hồi token Confluence tương tự | Confluence → Personal Access Tokens | Cập nhật `CONFLUENCE_TOKEN` |
| 5 | Đăng xuất Claude trên máy bot, người tiếp quản chạy `claude setup-token` | Máy bot | Ghi token mới vào `bot.env` |
| 6 | `firebase logout` trên máy chạy lượt; gỡ quyền Firebase project của người rời đi | Máy bot + Firebase Console → IAM | Người tiếp quản `firebase login` |
| 7 | Gỡ người rời đi khỏi `DISCORD_DUYET_USER_IDS` và role QA (là dev thì gỡ khỏi `DISCORD_DEV_IDS` / `DISCORD_DEV_THEO_ASSIGNEE`) | `bot.env` + Server Settings | Họ không bấm Check / Log Jira được nữa, bot không tag họ |
| 8 | Gỡ quyền ghi trên 2 repo GitHub, và quyền sửa các Google Sheet | GitHub Collaborators, Google Sheet → Share | — |
| 9 | Kiểm lại: bot chạy 1 lượt thử, `rcr-notify` gửi được | Kênh qa-auto | Ghi ngày thu hồi vào cuối file này |

Token bị lộ (dán nhầm vào chat, commit nhầm) thì làm ngay dòng tương ứng ở trên, không chờ người nghỉ.

## 4. Rủi ro đang mở

| Ngày phát hiện | Rủi ro | Mức | Hướng xử lý | Trạng thái |
|---|---|---|---|---|
| 11/11/2026 | Một số sheet nội bộ (TC, ID ads) đang đọc được bằng link, và link có trong repo public. Chi tiết (sheet nào, file nào) để ngoài repo | Cao | (a) chuyển repo sang private, hoặc (b) đưa link vào `bot.env` + đổi sang sheet mới / tải có đăng nhập | Chờ quyết định |

## Lịch sử siết quyền

| Ngày | Việc | Commit |
|---|---|---|
| 08/09/2026 | Web UI chỉ bind `127.0.0.1`, middleware chặn host khác | `0ce04f9` |
| 24/09/2026 | Spec Confluence không commit vào repo public | `613bf20` |
| 27/10/2026 | Bot: prompt cố định, chặn prompt injection từ tin Discord, giới hạn tool | `741be81` |
| 11/11/2026 | Viết trang phân loại + quy trình thu hồi; quét lịch sử git không thấy token | — |
