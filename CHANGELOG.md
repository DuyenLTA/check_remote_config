# Changelog — rc-check

Chỉ đánh số theo **mốc lớn** (thay đổi cách làm việc của QA), không đánh từng bản vá nhỏ. Bản vá nằm trong
`git log`; luật chấm đổi vì đầu ra sai nằm ở `docs/kb-changelog.md`.

Mở lại bản cũ: `git checkout v2.0` (xem) rồi `git checkout main` (quay về). Mỗi version là một git tag.

## v4.0 — 11/11/2026 · Vận hành 24/7

**Mục tiêu:** bot chạy liên tục không cần người trông, QA chỉ còn duyệt.

- Bot chính chạy 24/7 trên Ubuntu (systemd tự bật lại, chặn sleep, token Claude dài hạn); Windows là máy phụ nhận job.
- Mỗi build một thread trong forum qa-builds; mọi bước chỉ sửa tin gốc.
- `/policy-check` (Ads + Sub) là bước cuối mỗi lượt.
- Chế độ chuỗi (`--chuoi`): case "tiếp nối" chạy tiếp trên app đang mở → lượt full ~50 phút.
- Máy mất kết nối quá hạn → tự dừng lượt; build lệch plan tuần → nút "Chạy bỏ qua plan".
- Tạo được precondition "ad về muộn" bằng tường lửa Android 13+.
- File workflow tách thành luồng chính + tài liệu đọc khi cần, có test kiểm tính nhất quán.
- Bot tự ghi mỗi lượt vào `out/usage-log-bot.md` (người duyệt, thời gian, kết quả).

## v3.0 — 30/10/2026 · Vòng bug khép kín

**Mục tiêu:** từ FAIL tới bug Jira và verify mà không mất kiểm soát của QA.

- QA tick bug thật trên Discord → bot log Jira (nhãn `auto-qa`, marker case) → báo dev ở kênh project.
- Dev kéo bug sang Reviewing → bot cài build mới, chạy lại đúng case, PASS → Done, FAIL → To Do.
- Check ID ads (audit-fanout) trước khi chạy case; lệch ID không dừng lượt.
- Nhánh checklist Next-Gen cho SDK 3.7.0 / 3.7.1; chọn nhánh theo số SDK trong tin build.
- Dừng khi build khác plan tuần của QA.

## v2.0 — 27/10/2026 · Bot Discord

**Mục tiêu:** QA không phải mở terminal; build mới tự được test.

- Bot đọc tin báo build, hỏi QA (nút Check), cài bản từ App Tester, chạy `/rc-check` bằng Claude headless.
- Hàng đợi + khóa theo máy: nhiều điện thoại chạy song song.
- Prompt cố định, chỉ mở đúng danh sách tool; nội dung tin Discord không vào prompt.

## v1.0 — 27/09/2026 · Chạy đầu cuối bằng dòng lệnh

**Mục tiêu:** thay 3 giờ test Remote Config tay bằng một lệnh.

- Đọc baseline RC, nạp bộ TC, đặt giá trị trên một máy (không cần quyền admin Firebase), xác nhận sống qua lần mở app.
- Lái app theo câu Action, chấm từng dòng Expected bằng log / cây UI / ảnh.
- Report HTML dạng bảng testcase; slash command `/rc-check`.
