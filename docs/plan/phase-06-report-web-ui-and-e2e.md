---
phase: 6
title: "report + web UI + e2e"
status: pending
priority: P1
effort: "1d"
dependencies: [5]
---

# Phase 6: report + web UI + e2e

## Overview
Chạy cả file testcase một lượt, xuất report HTML có bằng chứng, và ghép UI đủ để tester dùng
mà không cần đọc code.

## Requirements
- Functional: chạy hàng loạt case, mỗi case ghi PASS/FAIL/… + actual result
- Functional: report HTML kèm screenshot từng bước
- Functional: luôn `restore` config gốc khi kết thúc (kể cả khi dừng giữa đường)
- Non-functional: report mở được bằng nháy đôi, không cần server

## Architecture

```
runner.run_all(cases) -> RunReport
  for case in cases:
      neu case.needs_human -> ghi NEEDS_HUMAN, bo qua, KHONG patch gi
      ket qua = case_runner.run(case)
      screenshot moi buoc -> exports/shots/
  finally: rc_patch.restore(baseline)   # luon chay
```

Report HTML — mỗi case một khối:
| Cột | Nội dung |
|---|---|
| Case | `N°` + sub-scenario |
| Config đã đặt | `key = value` thực tế đã ghi (không phải cái TC ghi) |
| Verdict | 5 trạng thái, tô màu |
| Assertion | từng dòng Expected + status + **actual result** |
| Bằng chứng | screenshot từng bước, link file |

Xuất `exports/rc-cases-<package>-<ngày giờ>.html`. Khuôn CSS/bảng lấy từ
`tsa/report_html.py` + `report_css.py` (header dính, tô màu cả dòng).

## Related Code Files
- Create: `src/rcr/runner.py`, `src/rcr/report_html.py`, `src/rcr/report_css.py`
- Modify: `src/rcr/main.py` (+ `POST /api/run-all`, `GET /api/report`)
- Modify: `src/rcr/web/index.html`, `web/app.js`, `web/style.css`
- Create: `README.md` (khuôn README của `tsa`: cần gì trước khi chạy, cách chạy, cách dùng,
  bảng ý nghĩa từng verdict)
- Create: `tests/test_report_html.py`, `tests/test_runner.py`
- Read để tham chiếu: `~/Downloads/Tool_test_data_app-main/src/tsa/report_html.py`,
  `.../report_css.py`, `.../README.md`

## Implementation Steps
1. `runner.py`: vòng chạy + `try/finally` gọi `restore`. Case `needs_human` bỏ qua **trước khi**
   patch — không đụng config cho case ngoài scope.
2. Screenshot mỗi bước qua `adb_client.screencap` (đã port ở phase 1), lưu PNG.
3. `report_html.py` + `report_css.py`: port khuôn từ `tsa`, đổi cột cho đúng nội dung phase này.
4. Web UI: chọn device → app → file TC → bảng case (tick chọn case muốn chạy) → nút Chạy →
   progress từng case → panel đường dẫn report.
5. Nút **Restore config** riêng, để tester bấm được bất cứ lúc nào.
6. `README.md`: nêu rõ **cần app debuggable**, kèm lệnh `aapt dump badging | grep
   application-debuggable` để tester tự kiểm APK trước khi cài.
7. e2e trên `com.ai.videogenerator.photocreator.aiart` với file TC tự tạo ở phase 4.

## Success Criteria
- [ ] Chạy cả file TC tự tạo một lượt → report HTML mở được, đủ 5 loại verdict xuất hiện
- [ ] Report ghi **config thực tế đã đặt**, khớp với cái `rc_verify` đọc lại được
- [ ] Ngắt giữa đường (Ctrl+C / đóng tab) → config vẫn được `restore`
- [ ] Case `needs_human` không làm tool patch gì cả
- [ ] Screenshot có mặt cho mọi bước đã chạy
- [ ] `README.md` đủ để tester khác chạy được mà không hỏi
- [ ] Mọi module <200 LOC

## Risk Assessment
- **`restore` không chạy khi process bị kill -9** → config của app kẹt ở giá trị test. Giảm
  thiểu: ghi `baseline.json` ra `exports/` ngay đầu phiên + nút Restore đọc lại từ file đó,
  nên vẫn phục hồi được ở phiên sau.
- **Report chứa giá trị RC thật** (đã thấy `api_key`, `email_feedback` trong config thật) →
  che các key nghi là credential trước khi ghi ra file, theo khuôn `tsa` đã che
  Adjust token / Facebook Client Token.
- Chạy hàng loạt case có `pm clear` → mỗi case tốn 15-30s. 12 case ≈ 5 phút. Chấp nhận được;
  hiện progress để tester không tưởng tool treo.
