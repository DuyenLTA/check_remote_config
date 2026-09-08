---
phase: 5
title: "assert_dump + verdict"
status: pending
priority: P1
effort: "1.5d"
dependencies: [4]
---

# Phase 5: assert_dump + verdict

## Overview
Chấm từng dòng Expected Result bằng cây `uiautomator dump`, ra 5 trạng thái, và **mô tả actual
result** đủ rõ để tester tin được khi FAIL.

## Requirements
- Functional: chấm theo **từng dòng assertion**, không chấm cả case một cục
- Functional: verdict case = trạng thái xấu nhất của các assertion
- Functional: FAIL phải kèm actual result cụ thể (node nào thấy / không thấy)
- Functional: không chấm được → `NOT_VERIFIABLE`, **không pass giả, không tính FAIL**

## Architecture

```
assert_dump.judge(expect_line, nodes, proc_alive) -> Assertion
```

Bộ luật, thử theo thứ tự — luật đầu khớp thì dùng:

| # | Mẫu câu Expected | Cách chấm | Actual result khi lệch |
|---|---|---|---|
| 1 | `App không crash` / `không sập` | process còn sống + không có node ANR | "app đã tắt / hiện dialog ANR" |
| 2 | `<X> không hiển thị` / `bị ẩn` / `KHÔNG <verb>` | không có node text/desc khớp `X` | "vẫn thấy node `<text>` tại bounds `[...]`" |
| 3 | `<X> hiển thị` / `hiện` / `vẫn thấy` | có node khớp `X` | "không tìm thấy node nào khớp `X`" |
| 4 | `thứ tự ... khớp <danh sách>` | so thứ tự `y` của các node khớp từng phần tử | "thứ tự thực tế: a, c, b" |
| 5 | `[TBD` trong câu | → `BLOCKED` | "spec chưa chốt" |
| 6 | còn lại | → `NOT_VERIFIABLE` | "dump không mang thông tin này" |

**Bóc `X` từ câu tiếng Việt**: ưu tiên chuỗi trong ngoặc kép; không có thì lấy cụm danh từ
riêng (chuỗi có chữ Hoa liên tiếp, vd `AI Album`, `Wedding Tribute`, `Trending Now`).
Không bóc được → `NOT_VERIFIABLE`, không đoán.

**Phủ định phải xử trước khẳng định** (luật 2 trước luật 3) — câu `Pill AI Album không hiển
thị` chứa cả `hiển thị`. Đây là lỗi kinh điển, test phải gác.

## Chấm case ads — tầng REQUEST, không tầng show

Đã verify tay: `lingospeak` **không có ad fill nào** (mọi ad `has load error`), nên chấm bằng
"ad có hiển thị không" là **không chấm được** — cả bật lẫn tắt đều không hiện. Nhưng tầng
**request** thì độc lập với fill:

```
assert_ads.judge(expect, log) -> Assertion
  tap unit id = set(unit id da 'starting load')  tu FOR_TESTER_LOAD_AD
  case "tat vi tri X"  -> unit cua X phai BIEN MAT so voi baseline
  case "bat/load X"    -> unit cua X phai CO MAT
  case "show X"        -> can FOR_TESTER_SHOW_AD: <TYPE> - <unitId>
```

Tag dùng để chấm (đã đo thật): `FOR_TESTER_LOAD_AD` (`starting load` / `has loaded` /
`has load error`), `FOR_TESTER_SHOW_AD: <TYPE> - <unitId>`,
`BannerAdHelper|BannerAdLogHelper: <Activity>: adBannerState(None|Loading|Loaded)`.

**Verdict `BLOCKED_NO_FILL`**: assertion đòi *show* mà log có `starting load` + `has load error`
→ config đúng, hành vi app đúng, chỉ là **không có quảng cáo để trả**. Không phải FAIL —
báo FAIL là đẩy tester đi tìm bug không tồn tại.

**Verdict `KEY_NOT_USED`**: `dex_check` (phase 4) nói app không tham chiếu key → chặn từ đầu,
không chạy app. Đây là nguồn **PASS giả** nguy hiểm nhất đã gặp thật.

```
verdict.roll_up(assertions) -> Verdict
  BLOCKED > KEY_NOT_USED > FAIL > BLOCKED_NO_FILL > NEEDS_HUMAN > NOT_VERIFIABLE > PASS
```

`KEY_NOT_USED` xếp trên `FAIL`: app không đọc key thì mọi kết luận về hành vi đều vô nghĩa.
`BLOCKED_NO_FILL` xếp dưới `FAIL`: nếu có assertion khác đã FAIL thật thì FAIL là kết luận đúng hơn.

Thứ tự này có nghĩa: một case có 3 assertion PASS + 1 NOT_VERIFIABLE → case là
`NOT_VERIFIABLE`, và report ghi rõ 3 dòng đã pass, 1 dòng không chấm được. **Không** làm tròn
thành PASS.

## Related Code Files
- Create: `src/rcr/assert_dump.py`, `src/rcr/assert_ads.py` (chấm ads theo tag logcat),
  `src/rcr/verdict.py`, `src/rcr/vn_text.py` (bóc `X`, chuẩn hoá tiếng Việt có/không dấu)
- Modify: `src/rcr/models.py` (+ `Assertion`, `Verdict`, `CaseResult`)
- Modify: `src/rcr/case_runner.py` (gọi chấm sau mỗi `NoOp`/bước cuối)
- Create: `tests/test_assert_dump.py`, `tests/test_verdict.py`, `tests/test_vn_text.py`
- Fixture: dump XML thật của app thay thế ở 2 trạng thái (key `true` và `false`)

## Implementation Steps
1. `vn_text.py`: chuẩn hoá (lower, bỏ dấu) để match `Hiển thị` ≈ `hien thi`; bóc `X` theo
   ngoặc kép → cụm chữ Hoa.
2. `assert_dump.py`: 6 luật theo thứ tự. Mỗi luật trả `Assertion(status, expect, actual)`.
   Match node: so `text` và `content-desc`, contains **không phân biệt dấu/hoa thường**.
3. `verdict.py`: `roll_up` theo thứ tự ưu tiên đã chốt.
4. Nối vào `case_runner`: chấm ở bước `Quan sát...`, và luôn chấm ở cuối case.
5. Fixture 2 dump thật: chạy app thay thế với 1 key `enable_*` = `true` rồi `= false`,
   lưu 2 file XML vào `tests/fixtures/`. Nhờ đó test chấm được **không cần cắm máy**.
6. Tests — điểm phải gác:
   - `Pill AI Album không hiển thị` → luật phủ định, **không** rơi vào luật khẳng định
   - `App không crash` khi process đã tắt → FAIL kèm actual đúng
   - `[TBD: spec chưa...]` → `BLOCKED`
   - `mở ra với hiệu ứng trượt kiểu App Store` → `NOT_VERIFIABLE` (không FAIL)
   - roll-up: 3 PASS + 1 NOT_VERIFIABLE → case `NOT_VERIFIABLE`
   - roll-up: 1 FAIL + 1 BLOCKED → case `BLOCKED`
   - `assert_ads`: log có `starting load` + `has load error`, assertion đòi *show*
     → `BLOCKED_NO_FILL`, **không** FAIL
   - `assert_ads` case tắt vị trí: tập unit id baseline trừ tập unit id case = đúng unit của
     vị trí bị tắt → PASS (fixture lấy từ 2 log thật của `lingospeak`)

## Success Criteria
- [ ] Chấm 12 case RC của file TC tự tạo (app thay thế) → mỗi case ra 1 trong 5 trạng thái
- [ ] Đổi key sang giá trị **sai kỳ vọng** → case ra `FAIL` kèm actual result nêu đúng node còn thấy
- [ ] Không có case nào `PASS` mà thực tế UI chưa đổi (chống pass giả) — kiểm bằng cách patch
      key rồi **cố tình không** force-stop: phải ra FAIL/BLOCKED, không PASS
- [ ] Assertion mơ hồ → `NOT_VERIFIABLE`, không tính vào FAIL
- [ ] `pytest` xanh khi không cắm máy (nhờ fixture dump)
- [ ] Mọi module <200 LOC

## Risk Assessment
- **Bóc `X` từ văn xuôi tiếng Việt là chỗ dễ sai nhất của phase này.** Giảm thiểu: thà
  `NOT_VERIFIABLE` còn hơn chấm sai. Đo tỉ lệ `NOT_VERIFIABLE` trên file mẫu; cao quá thì báo
  user, **không** nới luật match để ép ra PASS.
- **Node ẩn vẫn có trong dump** (`visible=false`, bounds rỗng) → phải lọc bằng `app_nodes` +
  bounds có diện tích, nếu không "không hiển thị" sẽ chấm sai.
- **RecyclerView chưa scroll tới** → node chưa tồn tại trong dump, dễ chấm "không hiển thị" oan
  cho câu khẳng định. Round 1 chấp nhận; ghi rõ trong report là chỉ chấm phần đang thấy trên màn.
