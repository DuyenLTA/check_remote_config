---
phase: 1
title: "Client Jira REST bot_jira_rest.py"
status: pending
priority: P1
effort: "1.5h"
dependencies: [0]
---

# Phase 1: `src/rcr/bot_jira_rest.py`

## Overview
Ba hàm đồng bộ, stdlib `urllib` (không thêm dependency), gọi qua `asyncio.to_thread` từ bot.

## Requirements
- `bat(env) -> bool`: có `JIRA_URL` (https) + `JIRA_PERSONAL_TOKEN` → tính năng bật
- `dang_reviewing(keys: list[str]) -> list[str]`: JQL `key in (...) AND status = Reviewing`, `fields=status`,
  `maxResults` = len(keys). Key không khớp `^[A-Z][A-Z0-9]{1,9}-\d+$` → bỏ trước khi ghép JQL
- `comment(key, text)`: `POST /rest/api/2/issue/{key}/comment`
- `chuyen(key, ten)`: `GET .../transitions` → tìm theo tên (không phân biệt hoa thường) → `POST` id đó (+ field
  bắt buộc phase 0 tìm ra). Không có transition tên đó → raise lỗi rõ ràng, không đoán
- Lỗi HTTP → `JiraLoi(msg)` với mã + 200 ký tự body; **không bao giờ** chứa token / header
- Timeout mỗi request 30s; User-Agent riêng (như `discord_notify`)
- Key search Jira đổi (issue move project) → key cũ không trả về: coi như không Reviewing

## Architecture
```
bot_job_verify ──to_thread──► bot_jira_rest._goi(method, path, body) ──► urllib.request (Bearer PAT)
```
Đọc config qua `discord_bot.env()` của bot (truyền `url, token` vào hàm, module không tự đọc env → dễ test).

## Related Code Files
- Create: `src/rcr/bot_jira_rest.py` (~90 dòng), `tests/test_bot_jira_rest.py`
- Không sửa file nào khác

## Implementation Steps
1. `_goi()` dựng Request, JSON in/out, map HTTPError/URLError → `JiraLoi`
2. `dang_reviewing`, `comment`, `chuyen` như trên
3. Test bằng monkeypatch `urllib.request.urlopen` (fake response) — không gọi mạng

## Test matrix (unit)
| Case | Kỳ vọng |
|---|---|
| keys rỗng | trả [] không gọi mạng |
| key bẩn `AIP920-13) OR 1=1` | bị loại khỏi JQL |
| search trả 2/3 key | đúng 2 key |
| transition "done" chữ thường | khớp `Done` |
| không có transition tên đó | `JiraLoi` |
| HTTP 401/400 | `JiraLoi`, chuỗi lỗi không chứa token |
| `JIRA_URL` http:// | `bat()` False |

## Success Criteria
- Test xanh, cả bộ `pytest -q` xanh; chạy tay `dang_reviewing(["AIP920-13"])` trên máy thật ra đúng

## Risk Assessment
| Rủi ro | Khả năng × Tác động | Giảm |
|---|---|---|
| Done đòi Resolution | TB × Cao | spike phase 0, gửi field bắt buộc |
| Workflow project khác không có tên `To Do` | Thấp × TB | raise lỗi → bot báo qa-auto, issue giữ nguyên |

## Security
- PAT chỉ trong header; repr/str của lỗi không gồm header. Key issue không nhạy cảm — được log
