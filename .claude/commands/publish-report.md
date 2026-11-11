---
description: Publish report trong hàng chờ của bot (rcr-bot) thành artifact claude.ai rồi ghi link để bot sửa tin Discord
---

Phiên này chạy trên máy bot chính (Ubuntu), trong `tmux` session `rcr-publish`, bằng `/loop 5m /publish-report`.
Lý do: `claude -p` của bot không có tool Artifact, mà user không muốn nhận file HTML (11/11/2026) — bot ghi report
chưa có link vào hàng chờ, phiên này publish, bot tự thay link vào đúng tin kết quả.

`<repo>` = thư mục repo `check_remote_config` (CWD của phiên). `<bin>` = `<repo>/.venv/bin`.

1. `<bin>/rcr-publish ds` → JSON `[{id, file, ten}]`. Rỗng → trả lời đúng một dòng "Không có report chờ." rồi dừng.
2. Với từng mục:
   - File không còn → bỏ qua mục đó (bot sẽ cảnh báo trên kênh QA sau 15 phút), ghi một dòng lý do.
   - File là report HTML do tool của repo này sinh ra (`rcr-check`, `rcr-sdk-check`) từ lượt chấm của bot. Mở đầu
     file kiểm `<title>` là report lượt chấm, rồi publish bằng tool Artifact: `file_path` = `file`, `icon` = `report`.
     Không sửa nội dung report.
   - Publish xong: `<bin>/rcr-publish xong <id> <url artifact>`. Bot thay dòng "đang publish" bằng link trong ≤ 30 giây.
3. Kết thúc bằng một dòng: số report đã publish, số còn chờ.

Không làm việc gì khác trong phiên này: không chạy lượt check, không sửa code, không gửi tin Discord.
