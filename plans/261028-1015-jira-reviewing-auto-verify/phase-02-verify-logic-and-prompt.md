---
phase: 2
title: "Logic verify thuần + prompt --case"
status: pending
priority: P1
effort: "2.5h"
dependencies: []
---

# Phase 2: `bot_verify_jira.py` (thuần, không Discord / mạng) + chế độ verify của `bot_chay_claude.py`

## Key Insights (đã kiểm code 28/10/2026)
- State `out/bot-hang-doi.json`: `tin[msg_id]` có `ma, package, loai_ban, bugs[{case,tieu_de,expected,thuc_te,...}]`,
  `jira = {"issues": [{case, key, link, ghi_chu}], ...}` (`discord_bot.py:213`, `bot_log_jira.py:91-93`)
- `ghi_chu` do Claude ghi: `tạo mới | trùng, đã cập nhật | bỏ qua: <lý do>` (`bot_log_jira.py:47`)
- Mã case bộ TC: `<tab>#<số|TC ID>` hoặc TC ID trần `SDK350-OB3X-013` (`rc-check.md:305-311`);
  Next-Gen checklist: `HT-03`, `RG-01` (`sdk-check/WORKFLOW.md:83-88`) → không chạy được bằng `--case`
- `bot_chay_claude.lenh/chay/doc_ket_qua` (`bot_chay_claude.py:57-123`): prompt cố định, KET_QUA một dòng JSON

## Requirements — `src/rcr/bot_verify_jira.py` (~120 dòng)
1. `ung_vien(tin: dict, ma: str) -> list[dict]`: duyệt mọi `tin` cùng `ma` có `jira.issues`; giữ issue có `key`
   và `ghi_chu` bắt đầu "tạo mới" (câu hỏi mở 2); khử trùng theo `key`; ghép `bug` theo `case` từ `bugs` của tin đó;
   kèm `loai_ban` của tin gốc. Trả `[{key, link, case, bug, loai_ban_goc}]`
2. `phan_loai(uv, loai_ban_moi) -> (chay: list, bo_qua: list[(uv, ly_do)])`:
   - case không khớp `CASE_TC_RE` → bỏ qua "case checklist Next-Gen — cần verify tay"
   - `loai_ban_goc != loai_ban_moi` (vd bug từ bản debug, build mới là release) → bỏ qua "build mới là bản <x>, không chạy được case"
3. `ket_luan(kq_luot, uv) -> "PASS" | "FAIL" | None`: chỉ khi `trang_thai == "XONG"` và case có trong `kq.cases`
   với verdict đúng `PASS`/`FAIL`; mọi thứ khác (BLOCKED, NEEDS_HUMAN, KHÔNG ỔN ĐỊNH, thiếu) → None
4. `noi_dung_comment(uv, kl, job, kq, may) -> str`: "[Bot auto verify] <PASS|FAIL> trên build <version> (<loai_ban>),
   máy <tên>, case <case>. Expected: … Thực tế: … Report: <link>" — chữ do **code** soạn, cắt ngắn từng trường
5. `tin_ket_qua_verify(job, dong) -> str`: tin `qa-auto` ≤ 1900 ký tự: ✅ Done / 🔁 To Do / ⚠️ giữ Reviewing + lý do / ⏭ bỏ qua

`CASE_TC_RE`: `^[\w.]+(?: [\w.]+)*#[\w.-]+$|^SDK\d{3}-[\w-]+$` (tab có dấu cách như `daily checkin#4`).
Case vào prompt **chỉ** khi khớp regex này (chặn injection từ state).

## Requirements — `src/rcr/bot_chay_claude.py` (+~25 dòng)
- `lenh(package, serial, cases: list[str] | None = None)`: có `cases` → `PROMPT_VERIFY`:
  `/rc-check {package} --serial {serial} --case {c1,c2}` + "Lượt verify bug dev đã fix: chỉ chạy các case này, bỏ
  mục 3c, vẫn rà FAIL theo 5d; KHÔNG log/sửa Jira" + dòng `KET_QUA` thêm
  `"cases": [{"case", "verdict": "PASS|FAIL|BLOCKED|NEEDS_HUMAN|KHONG_ON_DINH", "thuc_te"}]`
- `doc_ket_qua` đọc thêm `cases` (giống `doc_bugs`: chỉ dict có `case`, cắt ngắn) — không có thì `[]`
- `chay(..., cases=None)` truyền xuống; `TIMEOUT_VERIFY = 40 * 60`
- Case validate lại trong `lenh` bằng `CASE_TC_RE` (import từ `bot_verify_jira`) → sai thì `ValueError`

## Related Code Files
- Create: `src/rcr/bot_verify_jira.py`, `tests/test_bot_verify_jira.py`
- Modify: `src/rcr/bot_chay_claude.py`, `tests/test_bot_chay_claude.py`

## Test matrix (unit)
| Hàm | Case |
|---|---|
| ung_vien | 2 tin cùng ma, 1 tin khác ma; issue "bỏ qua", "trùng", key rỗng; key lặp ở 2 tin → 1; tin `jira: None` |
| phan_loai | case `3.6.1#SDK361-SPL-001` chạy; `HT-03` bỏ; `daily checkin#4` chạy; lệch loai_ban bỏ |
| ket_luan | XONG+PASS → PASS; XONG+FAIL → FAIL; DUNG+PASS → None; KHONG_ON_DINH → None; case vắng → None |
| lenh | cases → prompt có `--case a,b`; case chứa `\n` / `;` → ValueError; không cases → prompt cũ y nguyên |
| doc_ket_qua | KET_QUA có / không có `cases` |
| comment/tin | dài → cắt ≤ giới hạn; không chứa token |

## Success Criteria
- Test mới xanh; test cũ `test_bot_chay_claude.py` không đổi kỳ vọng (luồng Check y nguyên)

## Risk Assessment
| Rủi ro | K×T | Giảm |
|---|---|---|
| Claude trả verdict sai chính tả / ngoài tập | TB × Cao (chuyển trạng thái sai) | chỉ đúng chuỗi `PASS`/`FAIL` mới hành động |
| PASS giả (tool nhìn sai) → Done sai | Thấp × Cao | comment kèm report để dev/QA mở lại; nằm trong user chốt 3 |
| `--case` trên bộ TC mặc định chọn sai tab | Thấp × TB | case luôn có tiền tố tab (`3.6.1#…`) như lúc log |
