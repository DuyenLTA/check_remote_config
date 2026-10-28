---
phase: 3
title: "Nối vào bot: kích hoạt từ tin build, job verify, worker"
status: pending
priority: P1
effort: "2.5h"
dependencies: [1, 2]
---

# Phase 3: Job verify trong `rcr-bot`

## Key Insights (đã kiểm code 28/10/2026)
- `on_message` (`discord_bot.py:125-143`): tách tin → `package_cua` → gửi câu hỏi Check → `q.nho_tin(c)`
- Hàng đợi khoá trùng theo `(package, version)` (`bot_hang_doi.py:71-72`, `them` dòng 98-104) → job verify cùng
  build với job Check sẽ bị coi là trùng → **phải** thêm `loai_job` vào khoá
- Worker (`discord_bot.py:231-249`) lấy job FIFO cho máy rảnh, gọi `_chay_tren` → `_chay` (cài + `/rc-check` full)
- Job sống qua khởi động lại (`jobs` lưu file); bot chết giữa lượt → job chạy lại từ đầu (`bot_hang_doi.py:86`)
- `discord_bot.py` đã 296 dòng → luồng mới để ở module riêng

## Architecture
```
on_message ─(sau khi hỏi Check)─► bot_job_verify.xep(bot, c)
   ├─ jira tắt (thiếu token) → return
   ├─ uv = ung_vien(q.tin, ma); chay, bo_qua = phan_loai(uv, c.loai_ban); chay rỗng → return (im lặng)
   ├─ keys = to_thread(dang_reviewing, [u.key for u in chay]); rỗng → return
   └─ gửi tin qa-auto "🔁 Verify N bug Reviewing — <dau_tin>: KEY (case)…" → job {**c, loai_job: "verify",
      msg_id: <tin đó>, verify: [uv đang Reviewing], bo_qua} → q.them(job)
worker ─► _chay_tren ─► job.loai_job == "verify" ? bot_job_verify.chay(bot, job, serial, ten) : _chay(...)
bot_job_verify.chay:
   cai() lỗi → sửa tin: "⛔ cài không được" (không chuyển Jira), xong
   kq = to_thread(bot_chay_claude.chay, pkg, serial, REPO, TIMEOUT_VERIFY, OUT, cases)
   con = dang_reviewing(keys)   # bỏ issue người đã đổi trạng thái trong lúc chạy
   mỗi uv ∈ con: kl = ket_luan(kq, uv)
       PASS → comment → chuyen "Done";  FAIL → comment → chuyen "To Do";  None → giữ, ghi lý do
       JiraLoi ở issue nào → ghi lỗi dòng đó, đi tiếp issue sau
   reply tin verify: tin_ket_qua_verify(...) + report (dùng lại file_report / tin_ket_qua)
```
Comment **trước**, transition **sau**: transition hỏng thì bằng chứng vẫn nằm trên issue; job chạy lại sau khi bot
chết giữa chừng chỉ có thể trùng comment, không chuyển trạng thái hai lần (lần sau issue không còn Reviewing).

## Quyết định: quan hệ với câu hỏi Check cùng build
- Câu Check vẫn gửi như cũ (luồng không đổi). Job verify độc lập, xếp ngay → thường chạy trước lượt full
- QA bấm Bỏ qua / Check không ảnh hưởng job verify; hai job cùng build được phép cùng trong hàng
  (khoá `(package, version, loai_job)`), 2 máy rảnh thì chạy song song trên 2 máy
- Cùng build đăng lại (forward vào qa-auto) khi job verify còn trong hàng → `them` trả None → bỏ, không tin thừa

## Related Code Files
- Create: `src/rcr/bot_job_verify.py` (~110 dòng: `xep`, `chay`), `tests/test_bot_job_verify.py`
- Modify: `src/rcr/bot_hang_doi.py` (`_khoa_job` thêm `job.get("loai_job", "check")`),
  `src/rcr/discord_bot.py` (~10 dòng: gọi `xep` cuối `on_message`; rẽ nhánh trong `_chay_tren`; đọc
  `JIRA_URL`/`JIRA_PERSONAL_TOKEN` trong `__init__`), `tests/test_bot_hang_doi.py`, `tests/test_discord_bot.py`
- Job cũ trong file không có `loai_job` → mặc định `"check"` (tương thích ngược)

## Implementation Steps
1. `bot_hang_doi._khoa_job` + test: verify và check cùng build cùng vào được; hai verify cùng build → None
2. `bot_job_verify.xep` (lỗi Jira khi search → log warning + 1 dòng ở qa-auto, không chặn luồng Check)
3. `bot_job_verify.chay` theo sơ đồ; mọi lỗi bắt trong `_chay_tren` sẵn có
4. Móc vào `discord_bot.py`; `xep` bọc try/except riêng để lỗi verify không làm hỏng tin Check vừa gửi
5. Chạy cả bộ `pytest -q`

## Test matrix
| Mức | Case |
|---|---|
| Unit `bot_job_verify` (fake bot/kênh/jira như `test_discord_bot.py`) | Jira tắt → không gửi gì; 0 Reviewing → không job; 2 Reviewing → 1 job, tin liệt kê 2 key; PASS → comment rồi Done; FAIL → comment rồi To Do; DUNG → không gọi chuyen; issue hết Reviewing lúc chạy xong → bỏ; `chuyen` lỗi 1 issue → issue sau vẫn chạy; cài lỗi → không gọi Claude/Jira |
| Unit hàng đợi | khoá mới + job cũ không `loai_job` |
| Tích hợp (máy thật, phase 4) | build mới AIP920 với 1 bug Reviewing → Done/To Do đúng, tin qa-auto đúng |
| Hồi quy | toàn bộ test cũ luồng Check / Log Jira giữ nguyên |

## Success Criteria
- Tin build mới của app có bug bot log đang Reviewing → trong ≤ 1 phút có tin "🔁 Verify" ở qa-auto, không cần bấm
- Sau lượt: trạng thái Jira + comment khớp verdict; issue verdict khác PASS/FAIL vẫn Reviewing
- `pytest -q` xanh (≥ ~798 + test mới)

## Risk Assessment
| Rủi ro | K×T | Giảm |
|---|---|---|
| Dev chuyển Reviewing sau khi đăng build → bỏ lỡ | TB × TB | câu hỏi mở 4; QA vẫn có lượt Check |
| Chuyển trạng thái sai do lượt hỏng | Thấp × Cao | chỉ `trang_thai == XONG` + verdict đúng chuỗi |
| Job verify chiếm máy trước lượt Check | Cao × Thấp | ít case, timeout 40 phút |
| `tin{}` mất (xoá file state) | Thấp × TB | không có ứng viên → im lặng, đúng phạm vi user chốt 1 |

## Rollback
Gỡ `JIRA_PERSONAL_TOKEN` → `xep` return sớm. Revert code: job verify còn lưu → xoá tay khỏi `bot-hang-doi.json`.

## Security
- Key/case từ state đi qua regex trước JQL/prompt; chữ tin Discord không vào prompt (chỉ package + case đã validate)
