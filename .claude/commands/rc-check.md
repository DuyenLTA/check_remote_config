---
description: Đổi giá trị Firebase Remote Config của app Android theo file testcase, trên máy thật
argument-hint: "<package> [--tc <bo-tc.xlsx> [--tab <X.Y.Z>] [--case <key,key>]] [--set key=value] [--report <file.html>] [--app-label '<ten app>'] [--serial <serial>] [--fresh] [--no-walk|--no-actions] [--keep|--restore]"
---

Chạy `rcr-check` một lượt: đọc baseline remote config, nạp file testcase, đặt
config của một case rồi xác nhận nó sống qua lần mở app. Tham số: $ARGUMENTS

## 0. Tìm repo trước đã

Command chạy được từ thư mục bất kỳ — **đừng giả định CWD**. Lấy cái đầu tiên có
`src/rcr/cli_check.py`:

1. `git rev-parse --show-toplevel` (nếu CWD đang nằm trong chính repo này)
2. biến môi trường `$RC_RUNNER_REPO`
3. `~/projects/check_remote_config` (clone của github.com/LuuThiAnDuyen/check_remote_config)

Repo có **hai remote**, và máy này chỉ có credential của một tài khoản:
`luu` (LuuThiAnDuyen) **chỉ đọc** — `git pull luu main` để lấy code người khác đẩy lên;
`origin` (DuyenLTA) là chỗ **ghi**. Push URL của `luu` đã đặt thành `no_push` để một cú
push nhầm chết ngay tại chỗ thay vì đi hỏi mật khẩu.

Không thấy thì dừng, nói rõ đã tìm ở đâu. Gọi đường dẫn tìm được là `<repo>`.

Luôn gọi `<repo>/.venv/bin/rcr-check` — **đường dẫn tuyệt đối**. `rcr-check`
không có trong PATH toàn cục. Báo `command not found` thì
`cd <repo> && .venv/bin/python -m pip install -e ".[dev]"` rồi thử lại: venv cài
trước khi CLI được thêm thì thiếu file lệnh.

## 1. Tool này làm được tới đâu — nói trước, đừng để người dùng tưởng nhầm

Làm được: đặt giá trị remote config **không cần quyền admin Firebase**, không
đụng server, chỉ ảnh hưởng đúng một máy đang cắm; rồi đọc lại xem giá trị có
sống qua lần mở app không.

Lái được app qua các bước Action của case: `Quan sát…` (không thao tác),
`Nhấn nút "X"` / `Mở tab X` (tap), `Chờ N giây`, `Vuốt sang trái/phải/lên/xuống`,
và **bước đi tới cả một màn** (`Hoàn thành luồng FO đến Home`, `Vào màn Onboarding 2`)
— chỗ này `fo_flow` lo, OB1/2/3 sang màn bằng **vuốt** chứ không bấm Next, vì chính
nút Next là thứ đang được test. Câu khác — hoặc **nhiều hơn một node cùng khớp** —
thì dừng kèm lý do, **không tap bừa**: tap sai chỗ trên máy thật là bấm vào quảng
cáo hoặc mua hàng thật.

Hai chỗ nới lỏng có chủ ý, vì cái giá sai khác hẳn cái giá sai của một cú tap:

- **Câu vuốt không nêu hướng** (`Vuốt theo đúng hướng icon gợi ý`) thì lấy hướng
  sang trang kế (trái). Vuốt không bấm trúng gì nên đoán sai chỉ làm màn không đổi
- **Vế sau dấu phẩy nếu chỉ là quan sát thì không chặn bước đi tới màn**
  (`Chạy luồng FO đến OB3, quan sát banner` vẫn lái được). Vế sau là việc khác
  (`Vào OB3, ghi nhận thời điểm ad show`) thì vẫn dừng — lái tới nơi rồi coi như
  xong bước là bỏ im vế sau, case đó có thể ra PASS giả

**Chấm được PASS/FAIL** từng dòng Expected: dòng về quảng cáo chấm bằng log
request/load/show, dòng về chữ và node chấm bằng cây UI. Dòng nào không đo được
bằng máy (đúng design, đúng màu, animation mượt) ra `NOT_VERIFIABLE` — **không
được đoán thành PASS**. Verdict của case = dòng xấu nhất trong các dòng đo được.

## 2. Package và điều kiện vào được app

**Chỉ nhận package id**, không nhận tên app: khớp theo tên là khớp mờ, gõ thiếu
một ký tự là patch nhầm app hàng xóm. `$ARGUMENTS` không có chuỗi nào trông như
`com.abc.xyz` thì **dừng và hỏi**.

App phải cho vào vùng dữ liệu riêng — một trong hai:

- app là bản build **debuggable** (`run-as`), hoặc
- máy đã **root** (`su`) — đường này bản release cũng patch được

Không đường nào vào được thì tool in nguyên lý do (`run-as: ...` / `su: ...`).
In lại nguyên văn cho người dùng: đó là thứ duy nhất phân biệt "app không
debuggable" với "chưa cài app" với "SELinux chặn". **Không đi vòng, không gợi ý
sửa APK** — phải xin dev bản bật `debuggable`.

Kiểm APK trước khi cài, khỏi gỡ app xong mới biết sai bản:

```
aapt dump badging <file.apk> | grep application-debuggable
```

## 3. Chọn máy

```
adb devices -l
```

- 0 máy → **dừng**: cần máy Android thật, USB debugging, đã bấm Allow
- đúng 1 máy → không truyền `--serial` (tool tự lấy)
- nhiều máy → `--serial` lấy từ `$ARGUMENTS`; không có thì in danh sách và
  **hỏi**. Patch bừa lên máy người khác đang dùng là hỏng data của họ
- máy `unauthorized` không tính là dùng được

**Máy phải đang mở khoá.** Máy khoá thì PMS không resolve được activity nào, tool
báo không mở được app — nhìn y hệt app hỏng. Gặp lỗi đó thì bảo người dùng mở
khoá rồi chạy lại, đừng đi tìm bug trong app.

## 4. Chạy

Ba kiểu gọi, chọn theo `$ARGUMENTS`:

```
# a. chi doc baseline - xem app co bao nhieu key, key nao bi mirror
cd <repo> && .venv/bin/rcr-check --package <pkg> [--serial <S>]

# b. nap bo testcase - xem case nao tool chay duoc, case nao can nguoi
cd <repo> && .venv/bin/rcr-check --package <pkg> --tc <bo-tc.xlsx>

# c. chay 1 hay nhieu case, xuat report HTML kem anh tung buoc
cd <repo> && .venv/bin/rcr-check --package <pkg> --tc <bo-tc.xlsx> --tab 3.4.0 \
  --case 3.4.0#1,3.4.0#3 --report out/run.html
cd <repo> && .venv/bin/rcr-check --package <pkg> --set splash_banner_change=false
```

**Người dùng nêu bản SDK nào thì chỉ chạy đúng tab đó** — `sdk 3.4.0` → `--tab 3.4.0`.
**Mặc định tool tự chọn sheet, đừng chỉ định thừa.** Tool đọc bản SDK First Open từ
log của chính app (`VslTemplate4FirstOpenSDK: Using version 3.5.4-alpha02`, lọc theo PID
app) rồi lấy **đúng một tab số** tương ứng — tab số lớn nhất ≤ bản app (app 3.5.4 →
`TC SDK 3.5.0`). Không đụng tới tab nào khác.

**Người dùng nêu tên thì làm đúng cái đó**, chỉ việc dịch sang `--tab`:

| Người dùng gõ | Lệnh |
|---|---|
| `sdk 3.4.0` | `--tab 3.4.0` |
| `sdk rating` | `--tab rating` |
| `sdk widget` | `--tab widget` |
| `sdk daily checkin` | `--tab "daily checkin"` |
| không nêu gì | không truyền `--tab` — tool tự đo bản SDK rồi chọn tab số |

`rating`, `widget`, `daily checkin` là **SDK riêng, không thuộc luồng First Open**.
Người dùng không nhắc thì **đừng tự chạy**; chạy chúng thì cũng không cần đo bản SDK FO.

**Đừng đoán bản SDK từ versionName của app** — Piclux 2.8.0 nhúng SDK 3.5.4-alpha02,
hai con số không liên quan. Lấy nhầm tab là chấm bằng TC của bản khác mà không ai biết.

`--case` nhận nhiều case ngăn bằng dấu phẩy; case định danh bằng **`<tên tab>#<số>`**
(`3.5.0#12`, `rating#4`) vì số case trùng nhau giữa các tab. Gõ mỗi con số vẫn được nếu
nó chỉ có ở một tab; mơ hồ thì tool dừng và liệt kê — **đừng chọn bừa một cái**.

Chạy cả tab thì lấy danh sách case chạy được từ lượt `--tc` không kèm `--case`, rồi
truyền hết vào `--case`. Mỗi case khoảng một phút trên máy thật: 53 case ≈ 50 phút →
**luôn `run_in_background`** và chỉ báo lại khi có FAIL, có case hỏng, hoặc khi xong.

File TC một sheet (bộ cũ viết riêng cho một app) thì không cần `--sdk`.

Kiểu (c) có tắt/mở lại app nên mất vài chục giây → chạy `run_in_background`, ghi
stdout/stderr vào `<scratchpad>` của phiên. Kiểu (a)/(b) chạy thẳng, vài giây.

stdout là **đúng một dòng JSON** (`baseline`, `tc`, `run`); tiến độ ra stderr.

Case có giá trị lựa chọn (`layout1/2/3`) chạy **nhiều lượt** — mỗi giá trị một
lượt mở app, `run.runs` là từng lượt. Verdict của case = lượt xấu nhất.

Các flag còn lại, dùng khi cần:

| Flag | Khi nào dùng |
|---|---|
| `--app-label "Piclux 2.8.0"` | tên app in trên tiêu đề report — **luôn truyền khi có `--report`**, không thì báo cáo không nói được nó đo app nào |
| `--fresh` | ép app về trạng thái chưa từng mở (reset mềm, hoặc `pm clear`) — case Precondition đòi user mới |
| `--sdk 3.2.0` | khai thẳng bản SDK FO, bỏ qua bước đo từ logcat. Chỉ dùng khi máy không ra log |
| `--no-walk` | không lái qua luồng First Open để tới màn của case |
| `--no-actions` | chỉ đặt config, không lái bước Action nào |
| `--no-dex-check` | bỏ bước soi key trong DEX — **nhanh hơn nhưng có thể ra PASS giả**, chỉ dùng khi đã biết chắc app đọc key đó |
| `--adb <đường dẫn>` | adb không nằm trong PATH |
| `--out-dir <thư mục>` | nơi lưu snapshot config gốc (mặc định `<repo>/out`) |

**Mặc định tool trả config về nguyên trạng sau khi verify.** Muốn giữ giá trị đã
đặt để tự mở app xem thì phải thêm `--keep` — và hầu hết lượt của người dùng là
loại này. Không có `--keep` mà bảo người dùng "giờ mở app xem đi" là sai: config
đã bị trả về rồi.

Chạy xong với `--keep` thì tool **lưu snapshot config gốc** ra `<repo>/out/`.
Test xong, trả máy về nguyên trạng bằng đúng một lệnh:

```
cd <repo> && .venv/bin/rcr-check --package <pkg> [--serial <S>] --restore
```

**Đừng trả về bằng cách patch tay giá trị cũ.** Lượt sau đọc baseline sẽ ra bản
*đã patch* — giá trị "gốc" nhìn thấy lúc đó chính là giá trị bẩn. Chỉ snapshot
mới biết giá trị thật.

Để nguyên patch trên máy là lượt test sau chạy trên config bẩn mà không ai biết
— nhắc người dùng restore, đừng nói xong rồi thôi.

## 5. Đọc kết quả

`run.verdict` — đừng dịch thành PASS/FAIL của app khi case không có dòng Expected:

- `PASS` — chấm rồi và khớp Expected. **Ad request đúng mà không fill cũng là PASS**:
  không fill là chuyện của kho quảng cáo, logic app vẫn đúng. Đừng báo như lỗi
- `FAIL` — lệch Expected, kèm số đo thật (unit nào đã request, log ra sao)
- `NEEDS_HUMAN` — tool chưa lái tới được màn cần, hoặc quảng cáo che màn nên không đọc
  được chữ trên app. **Không kết luận gì về app** — đóng ad rồi chạy lại
- `NOT_VERIFIABLE` — dòng đòi nhìn mắt (đúng design, đúng màu, animation mượt)
- `CONFIG_OK` / `BLOCKED` — case không có Expected: đặt được config, hoặc config không
  sống qua lần mở app (build dev đặt `minimumFetchInterval = 0`)
- `KEY_NOT_USED` — key không có chuỗi trong `classes*.dex`: **app không đọc key đó**,
  template Firebase dùng chung nhiều app. Chấm tiếp là ra PASS giả

Case có nhiều lượt thì `run.runs` là từng lượt; verdict case = lượt xấu nhất.

`run.runs[i].drive` là nhật ký lái: từng bước ra thao tác gì, dừng ở bước nào và vì
sao. `status: NEEDS_HUMAN` ở đây **không phải bug app** — là tool từ chối đoán. Hai
lý do hay gặp: quảng cáo đang che màn hình (đóng ad rồi chạy lại), và nhiều node
cùng khớp một chuỗi (sửa câu Action cho rõ node nào). `--no-actions` để chỉ đặt
config, không lái.

`run.reset` nói đã đặt lại trạng thái kiểu gì: `force-stop` / `soft` (lật cờ
onboarding) / `clear` (`pm clear` — **mất login và data của app trên máy đó**,
nói cho người dùng biết, đừng để họ phát hiện sau).

Sau reset mềm, **màn onboarding nằm sau splash ad** và ad không tự đóng. Tool cố
tình không tap để đóng — tap sai chỗ là bấm quảng cáo thật. Bảo người dùng tự đóng
ad rồi xem, đừng báo như app không vào được onboarding.

Bảng `tc.cases`, đọc ba cột:

- `overrides` — key/value tool sẽ đặt, đã lọc bằng key thật của app
- `ignored` — key trong `Test Data` mà **không** thuộc remote config, thường là
  param analytics (`source`, `click_area`, `category`). Bị loại là đúng
- `needs_human` — lý do tool không tự chạy case, đều là **cố tình không đoán**:
  runtime toggle (`a → b → a` — nhận cả khi nó nằm ở **tên case** hay **Precondition**
  chứ không ở Test Data), sửa field trong JSON, giá trị còn là chỗ trống
  (`<id template đang test>`), ký hiệu ép trạng thái ad chưa có key ID đã đo
  (`data/ad_id_keys.yaml`), quá 16 tổ hợp giá trị, hoặc không key nào thuộc RC
- `from_precondition` — key lấy từ cột Precondition (bộ TC từ SDK 3.2.0 bỏ cột
  Test Data). Trùng key thì Test Data thắng

Bộ TC hay viết vị trí ads bằng **mã** thay vì tên key thật: *"tắt unit
102-spl-n-inter-high1 (key show_* tương ứng) = false"*. Tool suy ra
`show_102_spl_n_inter_high1` — nhưng **chỉ nhận khi key đó có thật** trong danh sách
key đọc từ máy, và giá trị phải lấy được từ chính câu đó. Không có key thì bỏ, không
đặt bừa. Đây là thứ gỡ oan 13/16 case của tab 3.5.0.

Case `needs_human` **không phải lỗi tool và không phải bug app** — báo tách hẳn
khỏi phần chạy được, kèm nguyên văn lý do.

## 6. Xuất report

Luôn truyền `--report <repo>/out/run-<pkg>-<hhmm>.html` khi chạy `--case`: trang HTML
tự chứa, có **ảnh chụp từng bước**, từng dòng Expected kèm tool đo được gì, log quảng
cáo, và nút lọc theo verdict. `out/` đã gitignore.

Lượt đã **đo được thật** (có case ra PASS/FAIL/BLOCKED) thì publish trang đó thành
artifact **rồi tự mở link** cho người dùng — tool chạy ở máy, không tự lên claude.ai
được. Lượt mà mọi case đều `NEEDS_HUMAN` (chưa lái tới màn nào) thì **đừng publish**:
trang đó không nói được gì về app, mở ra rồi đóng lại.

Publish xong thì ghi link lại, lấy `generated_at` từ **chính dòng JSON của lượt vừa chạy**:

```
cd <repo> && .venv/bin/rcr-artifact --url <link> --generated-at <generated_at cua luot>
cd <repo> && .venv/bin/rcr-artifact          # in link da luu cua luot truoc
```

URL artifact **cố định**: republish cùng file thì giữ nguyên link. Nên lượt sau cứ đọc
link cũ rồi republish đè, người dùng không phải đổi link đang mở. Bắt buộc kèm
`--generated-at`: thiếu nó thì không phân biệt được link đang trỏ tới lượt vừa chạy hay
một lượt cũ — gửi nhầm báo cáo cũ cho team là sai một cách im lặng.

## 7. Báo lại

Nói rõ: app + máy đã chạy, số key remote config và số key bị mirror, số case
chạy được / cần người, `verdict` của case đã chạy, và **người dùng cần tự làm gì
tiếp** (mở app, nhìn cái gì trên màn hình). Có `--keep` thì nhắc restore.

**Đưa link artifact ngay trong câu trả lời**, đừng bắt người dùng đi tìm. Report
local (`<repo>/out/…html`) vẫn mở được bằng nháy đôi nếu publish hỏng.

**Dừng ở đây. Không `git add`, không `git commit`, không `git push`.** Lượt chạy
không sinh file nào trong repo. Sửa tool là việc riêng, người dùng sẽ tự nói.
