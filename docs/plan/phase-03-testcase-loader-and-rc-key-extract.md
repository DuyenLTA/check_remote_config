---
phase: 3
title: "tc_loader + rc_extract"
status: completed
priority: P1
effort: "1d"
dependencies: [1]
---

# Phase 3: tc_loader + rc_extract

## Overview
Đọc file testcase XLSX → danh sách `Case`, và bóc đúng **cặp key/value remote config** ra khỏi
cột Test Data, lọc bằng whitelist key thật từ `rc_baseline`.

Không cần device — phase này thuần dữ liệu, test bằng file TC thật.

## Requirements
- Functional: parse sheet `Test Cases`, split `Action`/`Expected Result` theo số `1. 2. 3.`
- Functional: bóc `key = value` khỏi Test Data; hỗ trợ bool, số, string có nháy, JSON,
  nhiều key trên 1 dòng, và **sửa field trong JSON** (`restore.enable = false`)
- Functional: nhận diện **runtime toggle** (mũi tên `→`) → gắn cờ `needs_human`
- Functional: lọc bằng whitelist → param analytics tự rơi ra
- Non-functional: file TC khác cấu trúc cột → lỗi rõ ràng, không parse bừa

## Architecture

```
tc_loader.load(path) -> list[Case]
  sheet "Test Cases"; tim dong header chua "Test Data" va "Expected Result"
  -> map ten cot -> index (KHONG hardcode index: file khac co the them cot)
  dong co cot N° la so  -> 1 Case
  Action/Expected split theo regex ^\s*\d+[\.\)]\s*

Case: n, feature, description, sub_scenario, precondition, test_data,
      actions: list[str], expects: list[str]

rc_extract.extract(case, whitelist) -> RcCaseData
  1. co '→' trong test_data           -> needs_human = "runtime toggle, ngoai scope"
  2. tim moi cap  <key> <=|:> <value>  trong test_data
  3. key khong nam trong whitelist     -> bo (la param analytics)
  4. key co dau '.'  (restore.enable)  -> JsonEdit(key_goc, duong_dan, value)
  5. parse value: true/false | so | "..." | [...] / {...} (JSON) | tran
```

**Nested JSON edit** (`restore.enable = false`): cần biết JSON gốc → lấy từ
`baseline.configs[<key gốc>]`. Nhưng **key gốc không nằm trong Test Data** — câu đó chỉ ghi
`restore.enable`, `restore` là `id` của một phần tử trong mảng `moment_spotlight_banners`.
→ Round 1: đánh `NEEDS_HUMAN` kèm lý do "không suy được key gốc từ `restore.enable`".
Không đoán. Ghi rõ ở report để tester tự set.

**Value là JSON**: `moment_spotlight_banners = []` → ghi thẳng string `"[]"` vào `configs_key`
(RC lưu mọi thứ là string). Không cần serialize gì thêm.

## Related Code Files
- Create: `src/rcr/tc_loader.py`, `src/rcr/rc_extract.py`
- Modify: `src/rcr/models.py` (+ `Case`, `RcCaseData`, `JsonEdit`), `src/rcr/main.py` (+ route)
- Modify: `src/rcr/web/index.html` + `app.js` (ô chọn file TC, bảng case)
- Create: `tests/test_tc_loader.py`, `tests/test_rc_extract.py`
- Read để tham chiếu: `~/Downloads/Tool_test_data_app-main/src/tsa/spec_loader.py`
  (khuôn đọc XLSX bằng openpyxl `read_only=True, data_only=True`)
- Fixture: `~/Downloads/TC_IIP032_Moment_Explore_v7.5.0.xlsx`

## Implementation Steps
1. `tc_loader.py`: `openpyxl.load_workbook(read_only=True, data_only=True)`. Tìm sheet
   `Test Cases` (không có → lỗi rõ). Tìm dòng header bằng cách quét 10 dòng đầu tìm ô
   `Test Data`. Map tên cột → index.
2. Dòng nhóm (chỉ có ô đầu, không phải số) → bỏ. Dòng có `N°` là số → `Case`.
   Ô trống ở `Feature`/`Test Description` → kế thừa dòng trên (file thật để trống khi lặp).
3. Split `Action`/`Expected` theo `re.split(r'(?m)^\s*\d+[\.\)]\s*', ...)`, bỏ phần rỗng.
4. `rc_extract.py`: regex cặp key/value
   `([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\s*[:=]\s*(...)`. Cắt nhiều cặp trên 1 dòng theo dấu phẩy
   **ngoài** ngoặc/nháy.
5. Lọc whitelist. Key có `.` → `NEEDS_HUMAN`. Có `→` → `NEEDS_HUMAN`.
6. Parse value: `true`/`false` → `"true"`/`"false"`; số → nguyên văn; `"..."` → bỏ nháy;
   `[...]`/`{...}` → giữ nguyên văn (đã là JSON string).
7. Route `POST /api/testcases` (upload file) → trả bảng case + key/value đã bóc + cờ needs_human.
8. Tests trên file TC thật — số phải khớp Facts đã verify.

## Success Criteria
- [ ] `load()` trên file mẫu → **59 case**, cột map đúng, `actions`/`expects` split đúng số dòng
- [ ] `extract()` với whitelist thật → **15 case** có RC key
- [ ] **3 case runtime toggle** (#7, #9, #29) bị đánh `needs_human`, không parse thành `= false`
- [ ] `click_area`, `template_id`, `feature_name`, `source`, `category` **bị loại** (không có
      trong whitelist)
- [ ] Case #17 (combo) → bóc ra **2 key**
- [ ] Case #12 `moment_spotlight_banners = []` → value `"[]"`
- [ ] Case #14 `restore.enable = false` → `needs_human` kèm lý do
- [ ] Case #15 `sort_features_moments = ""` → value chuỗi rỗng (không bị bỏ qua)
- [ ] File XLSX không có sheet `Test Cases` → lỗi rõ ràng
- [ ] Mọi module <200 LOC

## Risk Assessment
- **Cột Test Data không phải nguồn duy nhất** — Precondition cũng ghi lại giá trị, đôi khi chi
  tiết hơn (`moment_spotlight_banners gồm 2 banner: id="loved_ones"...`). Round 1 **chỉ đọc
  Test Data**; nếu Test Data rỗng mà Precondition có key → `NEEDS_HUMAN`, không tự lấy từ
  Precondition (dễ bóc sai vì là văn xuôi).
- **File TC của AIP922 có thể khác cấu trúc cột** → đó là lý do map theo **tên cột**, không theo
  index. Cột lạ → lỗi rõ, không đoán.
- `[TBD: spec chưa...]` xuất hiện trong Expected của file thật → phase 5 phải đánh `BLOCKED`.


## Ket qua thuc te (2026-09-09)

133 test xanh khi khong cam may. Module: `tc_loader.py` (154), `rc_extract.py` (~120),
`routes.py` (154), `app_state.py` (48) - deu <200 LOC.

Do tren file TC that `TC_IIP032_Moment_Explore_v7.5.0.xlsx` (59 case) voi whitelist la 7 key
RC cua IIP032 - **khop dung so trong Facts**:

| | Ket qua |
|---|---|
| Tong case doc duoc | **59** |
| Case chay duoc | **12** (#6, #8, #10, #11, #12, #15, #16, #17, #28, #30, #31, #59) |
| Runtime toggle bi chan | **3** (#7, #9, #29) |
| Sua field JSON bi chan | **1** (#14 `restore.enable`) |
| Param analytics bi loc | `source`, `category`, `style`, `click_area`, `feature_name`, `template_id` |
| `moment_spotlight_banners = []` | giu `"[]"` |
| `sort_features_moments = ""` | giu chuoi rong (khong bi coi la "khong co gia tri") |
| Combo #17 | ra **2** key |
| Ke thua `Feature` khi o trong | dung |

### HAI SUA PHAT SINH khi chay tren file that

**1. Regex key KHONG duoc doi dau `_`.** Ban dau doi key phai la snake_case >= 2 doan. Hau qua:
`source = navigation` bao *"khong boc duoc cap key=value"* - SAI LY DO (boc duoc, chi la khong
thuoc RC), va **bo sot key hop le**: config that co key `AppSettings` (camelCase, khong
underscore). Sua: regex chi tim ung vien identifier bat ky, **whitelist moi la bo loc**.

**2. Chan gia tri con la cho trong.** `template_id = <id template dang test>` va
`feature_name = <gia tri tuong ung AI Album>` - neu key do nam trong whitelist thi tool se
patch NGUYEN CHUOI MO TA vao config. Them `PLACEHOLDER_RE` -> `NEEDS_HUMAN`.

### Modularization phat sinh

`main.py` da 167 LOC, them route la sat 200 va phase 4-6 con them nua -> tach:
- `main.py` (57) = app + middleware + error handler + static
- `routes.py` (154) = toan bo route API
- `app_state.py` (48) = client adb + baseline da doc (khuon `tsa/app_state.py`)

### Test route bang TestClient thay vi curl

Máy rút giua luc lam nen khong curl duoc `/api/testcases`. Viet `tests/test_routes.py` cam
`FakeAdb` vao `app_state` - tot hon curl vi thanh test vinh vien. Gac ca: `Host` khac -> 403,
loi tang duoi -> 400 (khong 500), file sai duoi / rong / chua doc baseline -> 400.

Luu y: `TestClient` mac dinh gui `Host: testserver` nen bi middleware chan (403) - dung
`TestClient(app, base_url="http://127.0.0.1")`.

### Chua lam

Route `/api/testcases` chua chay thu tren may that (may rut). Logic parse da do tren file TC
that qua CLI; phan con lai (baseline tu device) da co test. Chay lai khi cam may.
