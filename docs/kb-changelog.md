# Change log knowledge base — rc-check

KB của workflow này: `.claude/commands/rc-check.md` (quy trình, luật audit PASS/FAIL),
`src/rcr/data/*.yaml` (`ad_id_keys`, `ad_units`, `fo_flow`, `reset_rules`, `sdk_rules`, `ui_names`),
`docs/`, sheet "Check thông số KT" (tải lại mỗi lượt).

Mỗi lần sửa KB: thêm một dòng vào mục "Bài học" nếu sửa vì đầu ra sai, ghi số trước và sau.

## Bài học (sửa vì đầu ra sai)

| Ngày | Đầu ra sai | Sửa gì | Trước → sau |
|---|---|---|---|
| 06/10/2026 | Report "35 PASS" có 3 PASS giả | Mọi PASS phải dẫn đúng ad unit của vị trí theo sheet, §5c (`c3ac959`) | 3 PASS giả → bị bắt trước khi publish |
| 07/10/2026 | 8/12 FAIL là sai, do app tự fetch Firebase ghi đè giá trị đã patch | Chạy lại mọi FAIL, đọc lại config sau khi chấm, §5d (`09d23ee`) | 8 FAIL sai → BLOCKED kèm lý do |
| 07/10/2026 | Luật viết riêng cho từng app (ID nút X) | Bỏ, dùng luật chung (`12e2be3`) | Quy tắc cũ đã xóa |
| 07/10/2026 | Bằng chứng trong report lấy từ lượt khác lượt ra verdict | Bằng chứng phải cùng lượt (`a8de060`) | — |
| 24/10/2026 | Piclux 2.4.0: REG-002 "preload 201" và SPLA-003 "preload 106" ra PASS bằng native test …110 / …379 không thuộc vị trí nào | Dòng thứ tự preload chỉ xét unit map được về vị trí trong câu, như dòng "show" | 2 PASS giả → FAIL (ID vị trí đã biết) hoặc không chấm (chưa biết) |
| 24/10/2026 | Piclux 2.4.0: build dùng unit test Google cho native/banner, chạy 50 phút mới biết | Preflight mở app một lần, request bằng `ca-app-pub-3940256099942544/` → LỖI, dừng | Phát hiện sau ~20s thay vì sau 50 phút |
| 24/10/2026 | BACK trên inter thật …588 → 2 `ad_click`; tool chưa từng đọc event này (cùng ngày tool tự bấm BACK trên AdActivity 23 lần, không biết có click không) | Đếm `ad_click` mỗi case; có thì BLOCKED, không chạy lại, dừng cả lượt; cấm Claude gửi phím/tap lên ad thật khi chấm tay | 0 → đo được mọi click trong lượt |
| 10/10/2026 | Sorapix 1.6.0: 11 FAIL lặp lại, nghi do tool bắt thiếu frame (OB3X) và chưa đủ tiền đề | Xem dòng 23/10 | — |
| 23/10/2026 | Sorapix 1.6.0 OB3X-001/002/004/005: "nút X không hiện" trong khi OB3 đứng 8,6s mà tool chỉ có 1–2 khung. `dumpsys activity top` treo cả cửa sổ, uiautomator chỉ được gọi lại sau mỗi khung nhanh nên dừng theo. OB3X-013: khung uiautomator ghi 0,12s sau lúc rời OB3 bị tính là màn kế | Hai vòng nhìn chạy độc lập, dumpsys quá 2s thì bỏ khung đó. Có quãng >3s không nhìn được màn thì không kết luận "không hiện", trả NEEDS_HUMAN. Khung uiautomator trong 0,5s sau lúc rời OB3 không tính là màn kế | Chấm lại offline dữ liệu 10/10: 6 FAIL OB3X → 5 cần chạy lại, 1 PASS. Chưa chạy lại trên máy |

## Commit đụng tới KB

| Ngày | Commit | Loại | Thay đổi | File KB |
|---|---|---|---|---|
| 10/10/2026 | `3ea8391` | Sửa sau lỗi | fix: wait for a filled config file after reset and settle sooner after an onboarding swipe | `.claude/commands/rc-check.md` |
| 07/10/2026 | `a8de060` | Thêm quy tắc | feat: require report evidence to come from the run the verdict is based on | `.claude/commands/rc-check.md` |
| 07/10/2026 | `c1b0ca4` | Thêm quy tắc | feat: grade per-screen ad shows from events and pass LFO quickly on demand | `.claude/commands/rc-check.md` |
| 07/10/2026 | `12e2be3` | Thêm quy tắc | feat: require /rc-check to re-verify every FAIL and avoid app-specific rules | `.claude/commands/rc-check.md` |
| 07/10/2026 | `09d23ee` | Thêm quy tắc | feat: confirm FAILs and detect config overwrites before reporting | `src/rcr/data/ui_names.yaml` |
| 06/10/2026 | `67f0b39` | Thêm quy tắc | feat: read per-position ad unit IDs from the QA spec sheet on every run | `.claude/commands/rc-check.md` |
| 06/10/2026 | `c3ac959` | Thêm quy tắc | feat: make /rc-check audit every PASS for the right ad unit before reporting | `.claude/commands/rc-check.md` |
| 06/10/2026 | `0beb3be` | Thêm quy tắc | feat: grade OB3 timers, the X button and ad lines from real measurements | `src/rcr/data/ui_names.yaml` |
| 06/10/2026 | `4e84384` | Thêm quy tắc | feat: tell the command how to hold a short-lived screen with a broken Private DNS | `.claude/commands/rc-check.md` |
| 05/10/2026 | `ff142d3` | Thêm quy tắc | feat: load the testcase workbook straight from its Google Sheet link | `.claude/commands/rc-check.md` |
| 03/10/2026 | `baa8e3a` | Thêm quy tắc | feat: grade NEEDS_HUMAN and NOT_VERIFIABLE lines on the device instead of handing them back | `.claude/commands/rc-check.md` |
| 02/10/2026 | `f35b195` | Thêm quy tắc | feat: drive compound test steps instead of misreading them | `.claude/commands/rc-check.md` |
| 29/09/2026 | `07d9c72` | Thêm quy tắc | feat: bring the slash command back in line with the tool | `.claude/commands/rc-check.md` |
| 28/09/2026 | `37aed96` | Thêm quy tắc | feat: say in the command who reconciles the console figures | `.claude/commands/rc-check.md` |
| 28/09/2026 | `14b8836` | Thêm quy tắc | feat: read ad unit ids from the team checklist so ad lines can be graded | `src/rcr/data/ad_units.yaml` |
| 28/09/2026 | `31e2e71` | Thêm quy tắc | feat: drive a swipe step, and let an observation clause follow a goto step | `.claude/commands/rc-check.md` |
| 28/09/2026 | `9c22abf` | Thêm quy tắc | feat: say which remote is read-only and which one takes the pushes | `.claude/commands/rc-check.md` |
| 28/09/2026 | `e16432d` | Thêm quy tắc | feat: keep the /rc-check command in the repo, matching what the tool now does | `.claude/commands/rc-check.md` |
| 27/09/2026 | `ac9d0bb` | Thêm quy tắc | feat: let the first-open walker drive a step that says go to a screen | `docs/plan/phase-04-device-reset-and-action-resolver.md` |
| 27/09/2026 | `ce31eab` | Thêm quy tắc | feat: hand the report path to the publisher and remember its link | `docs/plan/phase-06-report-web-ui-and-e2e.md` |
| 27/09/2026 | `32aea30` | Thêm quy tắc | feat: an ad that is requested but never filled counts as a pass | `docs/plan/phase-05-assert-dump-and-verdict.md`, `docs/plan/plan.md` |
| 25/09/2026 | `f557529` | Thêm quy tắc | feat: reach the exact onboarding page, and read UI names from the test case | `src/rcr/data/ui_names.yaml` |
| 25/09/2026 | `a5a2296` | Thêm quy tắc | feat: walk the first-open flow to the screen a case is about | `src/rcr/data/fo_flow.yaml` |
| 25/09/2026 | `c4d5b10` | Khác | docs: record what was measured on the device and what it changed | `docs/plan/phase-04-device-reset-and-action-resolver.md`, `docs/plan/phase-05-assert-dump-and-verdict.md`, `docs/plan/phase-06-report-web-ui-and-e2e.md`, `docs/plan/plan.md` |
| 25/09/2026 | `3162cfd` | Thêm quy tắc | feat: put the app back to the state a case asks for | `src/rcr/data/reset_rules.yaml` |
| 24/09/2026 | `613bf20` | Thêm quy tắc | feat: sync SDK tutorial specs from Confluence and lint cases with spec rules | `docs/plan/plan.md`, `src/rcr/data/sdk_rules.yaml` |
| 23/09/2026 | `9d8c048` | Thêm quy tắc | feat(plan): record shared per-SDK test sheets and 2026-09-23 device findings | `docs/plan/phase-03-testcase-loader-and-rc-key-extract.md`, `docs/plan/phase-04-device-reset-and-action-resolver.md`, `docs/plan/phase-05-assert-dump-and-verdict.md`, `docs/plan/plan.md` |
| 23/09/2026 | `ab593d3` | Thêm quy tắc | feat: merge precondition keys, expand choice values, force ad fill/fail | `src/rcr/data/ad_id_keys.yaml` |
| 09/09/2026 | `3861f00` | Thêm quy tắc | feat: read test cases from an xlsx file and pull out the keys to set | `docs/plan/phase-03-testcase-loader-and-rc-key-extract.md`, `docs/plan/plan.md` |
| 08/09/2026 | `4478828` | Khác | docs: make the in-repo plan the single source of truth | `docs/plan/plan.md` |
| 08/09/2026 | `fb81847` | Khác | docs: version the implementation plan with the code | `docs/plan/phase-01-skeleton-adb-and-rc-baseline-reader.md`, `docs/plan/phase-02-rc-patch-and-verify-survival.md`, `docs/plan/phase-03-testcase-loader-and-rc-key-extract.md`, `docs/plan/phase-04-device-reset-and-action-resolver.md` +4 |

Sinh lại bảng: `git log --name-only -- .claude src/rcr/data docs`
