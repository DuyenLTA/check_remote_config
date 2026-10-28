---
title: "Bot tự verify lại bug Jira dev chuyển Reviewing khi có build mới, rồi chuyển Done / To Do"
description: "Build mới của app → bot chạy lại đúng các case của bug (bot đã log) đang Reviewing → PASS: Done, FAIL: To Do, kèm comment bằng chứng"
status: pending
priority: P2
effort: 8h
branch: master
tags: [discord-bot, jira, rc-check, automation]
created: 2026-10-28
blockedBy: []
blocks: []
---

# Bot tự verify bug Reviewing

Dev fix bug bot đã log → chuyển issue sang **Reviewing** → đăng build mới. Bot thấy tin build (luồng sẵn có) →
lấy các issue **bot đã tạo** của mã app đó → hỏi Jira cái nào đang Reviewing → tự xếp **job verify** (không cần QA bấm)
→ cài build từ App Tester → `/rc-check <pkg> --case <các case>` headless → mỗi case: **PASS** → comment + Done;
**FAIL** → comment + To Do; còn lại (BLOCKED, không ổn định, lượt lỗi) → giữ Reviewing, báo `qa-auto` cần xem tay.

## User đã chốt (28/10/2026)
1. Phạm vi: **chỉ bug bot tự log** (biết qua state: jira key + case + package). Bug log tay bỏ qua
2. Lúc verify: khi có **tin build MỚI** của cùng mã app → bot tự tải App Tester (luồng cũ), chạy lại **chỉ các case**
   của bug đang Reviewing; **không cần QA bấm Check**
3. PASS → bot tự chuyển **Done** + comment bằng chứng; báo `qa-auto`
4. Vẫn FAIL → comment bằng chứng + chuyển về **To Do**; báo `qa-auto`
5. Jira gọi **REST thẳng**, PAT trong `bot.env` (`JIRA_URL`, `JIRA_PERSONAL_TOKEN`) — user tự chép token
6. Thêm nút **"Verify lại"** ở tin build trong `qa-auto`: QA bấm → verify bug đang Reviewing của app trên bản đã cài
   (đỡ trường hợp dev kéo Reviewing sau khi báo build)
7. Chỉ issue ghi chú **"tạo mới"** là bug của bot; issue "trùng, đã cập nhật" bỏ qua

Mặc định chưa hỏi (theo đề xuất): bỏ mục 3c, chỉ báo ở `qa-auto`, bug checklist Next-Gen bỏ qua + "cần verify tay".

## Đề xuất của planner (user đã gật các điểm trên)
- Câu Check thường **vẫn hỏi như cũ**; job verify là job riêng (`loai_job: "verify"`) xếp hàng ngay, không chờ QA.
  Lý do: verify ít case (vài phút) nên có kết quả trước lượt full; QA bấm Bỏ qua lượt full không chặn verify;
  khoá trùng hàng đợi đổi thành `(package, version, loai_job)` để hai job cùng build không đè nhau
- Jira đi **REST thẳng** (urllib, 3 lệnh: search / comment / transition), không qua Claude headless: thao tác ghi
  trạng thái phải tất định, không tốn $ + 30-60s khởi động `uvx mcp-atlassian`, không có mặt prompt injection.
  Dùng **đúng tên biến** của mcp-atlassian: `JIRA_URL`, `JIRA_PERSONAL_TOKEN` trong `bot.env`. Thiếu token → tính năng tắt
- Transition tra **theo tên** (`Done`, `To Do`) qua `GET /transitions`, không cứng id (31/11 chỉ đúng workflow AIP920)
- Bug nhánh checklist Next-Gen (mã `HT-03`, `RG-01`… không phải case bộ TC) → **bỏ qua**, báo "cần verify tay"
- Lượt verify **bỏ mục 3c** (check ID ads) — việc của lượt full

## Phases
| # | Phase | Status | Effort |
|---|-------|--------|--------|
| 0 | [Spike Jira REST: search / transitions (field bắt buộc) / comment](phase-00-jira-rest-spike.md) | done (mọi transition không field bắt buộc; key không tồn tại → 400 cả JQL, `validateQuery=warn` thì bỏ qua) | 0.5h |
| 1 | [Client Jira REST `bot_jira_rest.py`](phase-01-jira-rest-client.md) | done (12 test; gọi thật `dang_reviewing` OK) | 1.5h |
| 2 | [Logic verify thuần + prompt `--case` (`bot_verify_jira.py`, `bot_chay_claude.py`)](phase-02-verify-logic-and-prompt.md) | done | 2.5h |
| 3 | [Nối vào bot: kích hoạt từ tin build, job verify, worker](phase-03-wire-verify-job-into-bot.md) | done (nút Verify lại ở tin hỏi + tin kết quả + tin verify; review đã sửa: bọc mọi lỗi Jira, chặn redirect, giữ chỗ xếp, bỏ verify build cũ khi có build mới, quote `--case`) | 2.5h |
| 4 | [Docs + chạy thật một lượt](phase-04-docs-and-real-run.md) | in-progress (README xong; chờ build thật có bug Reviewing) | 1h |

Phụ thuộc: 0 → 1; 2 song song với 1 (khác file); 3 cần 1 + 2; 4 cần 3.

## Luồng dữ liệu
```
tin build (ma, version, loai_ban) ──► state tin{} cũ cùng ma ──► ứng viên [{key, case, bug, loai_ban_goc}]
  ──► Jira search `key in (...) AND status = Reviewing` ──► job verify vào hàng đợi (tin riêng ở qa-auto)
worker ──► cai() ──► claude -p "/rc-check pkg --serial s --case c1,c2" ──► KET_QUA.cases[{case, verdict, thuc_te}]
  ──► search lại Reviewing (bỏ issue đã đổi trạng thái giữa chừng) ──► comment ──► transition ──► báo qa-auto
```

## Ràng buộc
- File < 200 dòng; `discord_bot.py` (296 dòng) **chỉ thêm móc nối**, luồng async nằm ở `bot_job_verify.py`
- PAT chỉ ở env, không in, không ghi log/lỗi; `JIRA_URL` phải `https://`
- Key/case từ state vẫn validate regex trước khi vào JQL / prompt
- Một máy một lượt (khoá `out/.may-<serial>.lock` sẵn có); không commit

## Rollback
Xoá `JIRA_PERSONAL_TOKEN` khỏi `bot.env` → bot không tạo job verify (luồng Check giữ nguyên). Job verify còn trong
`bot-hang-doi.json` khi rollback code: worker cũ đọc như job Check (thừa trường) → xoá tay dòng `loai_job: verify`.

## Câu hỏi còn mở
- Chưa chạy thật: cần một build mới của app có bug bot log đang Reviewing
