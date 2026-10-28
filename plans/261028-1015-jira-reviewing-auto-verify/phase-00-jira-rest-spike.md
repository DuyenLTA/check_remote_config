---
phase: 0
title: "Spike Jira REST: search / transitions / comment"
status: pending
priority: P1
effort: "0.5h"
dependencies: []
---

# Phase 0: Spike Jira REST trên jira.apero.vn

## Overview
Trước khi viết client, đo thật 3 lệnh REST v2 của Jira Server/DC bằng PAT (Bearer). Chỉ đọc, trừ bước 4 cần user cho phép.

## Key Insights
- mcp-atlassian ở `~/.claude.json` (mcpServers, user scope): `uvx mcp-atlassian`, env `JIRA_URL`, `JIRA_PERSONAL_TOKEN`
- Transition id AIP920-13 đã biết: To Do 11, Done 31, Reviewing 51 — **chưa biết** Done có màn bắt buộc (Resolution) không
- Precedent urllib: `src/rcr/discord_notify.py:18` (đặt User-Agent riêng vì Cloudflare chặn UA mặc định, dòng 31)

## Implementation Steps
1. `GET /rest/api/2/search?jql=key in (AIP920-13) AND status = Reviewing&fields=status` → ghi mã HTTP + shape JSON
2. `GET /rest/api/2/issue/AIP920-13/transitions?expand=transitions.fields` → transition `Done` có field `required: true`
   nào không (resolution?). Có → client gửi `fields.resolution = {"name": "Done"}` (hoặc giá trị spike thấy)
3. Kiểm search trả gì khi key không tồn tại / không có quyền (400 hay bỏ qua) — quyết cách client xử lý
4. (Cần user OK, trên issue thử) `POST /issue/{key}/comment` + `POST /issue/{key}/transitions` rồi trả trạng thái cũ
5. Ghi kết quả vào mục "Đã biết" của `plan.md`

## Success Criteria
- Biết chắc: header auth chạy, field bắt buộc của Done / To Do, mã lỗi khi key sai

## Risk Assessment
- Proxy/VPN công ty chặn từ máy bot (Ubuntu) → spike chạy trên **cả máy sẽ chạy bot**
- Lỡ đổi trạng thái issue thật → bước 4 chỉ làm khi user chỉ issue thử

## Security
- Token đọc từ env trong lệnh; không echo, không ghi vào report/log
