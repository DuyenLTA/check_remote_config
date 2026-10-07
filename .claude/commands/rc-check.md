---
description: Đổi giá trị Firebase Remote Config của app Android theo file testcase, trên máy thật
argument-hint: "<package> [--tc <link sheet | bo-tc.xlsx> [--tab <X.Y.Z>] [--sdk <X.Y.Z>] [--case <key,key>]] [--set key=value] [--report <file.html>] [--app-label '<ten app> <version>'] [--serial <serial>] [--fresh] [--full-walk|--no-walk|--no-actions] [--keep|--restore]"
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
`Tắt mạng` / `Bật lại mạng`, và **bước đi tới cả một màn** (`Hoàn thành luồng FO
đến Home`, `Vào màn Onboarding 2`) — chỗ này `fo_flow` lo, OB1/2/3 sang màn bằng
**vuốt** chứ không bấm Next, vì chính nút Next là thứ đang được test.

Câu ghép (bộ TC 3.5.0) cũng lái được — trước đây chúng bị làm **sai im lặng**:
`Vuốt trái nhanh liên tục 3-4 lần` (vuốt đủ 4 lần, không suy trang theo số lần
vuốt), `Vuốt phải về OB2, rồi vuốt trái…` (đúng thứ tự), `Chờ quá 10s` (chờ quá
mốc, không phải 3s mặc định), `Ở OB3, chờ thêm 5s`, `Sau đó vuốt…`, `Nhấn Home
(background 10s)` rồi `Mở lại app` (đưa app lên thật), `Xoay ngang rồi xoay dọc`
(xong luôn trả chế độ xoay của máy về như cũ), `Tại t0+2s: <thao tác>`.
**t0 = lúc vừa tới màn của case, CHƯA phải lúc ad show** — report ghi rõ thao
tác làm lúc t0+bao nhiêu. `Bấm giờ` / `ghi nhận thời điểm ad show` = tool **đứng
yên quan sát**: đo mốc vào/rời trang OB3 + ad show/fail bằng `logcat -v epoch`
(chính xác tới ms), và nhìn liên tục để thấy nút X / số đếm. Vào tới OB3 là
**nhìn ngay**, không dump + chụp trước bước (mất 3–5s, timer 3s là trang đã đi mất —
đo 06/10/2026). Nhìn bằng `dumpsys activity top` (~0,15s/khung) xen `uiautomator`
(~2,5s, đọc được chữ): chỉ dùng uiautomator thì khung đầu trễ ~7s, cả cụm OB3X ra
FAIL oan (07/10/2026).

**Không gắn cứng theo một app** (user chốt 07/10/2026 — tool dùng cho nhiều app).
Nút X / số đếm nhận theo **vai trò**: gợi ý id trong `data/ui_names.yaml` + nghĩa
tên id (skip/close/dismiss… — timeout/countdown/timer) + content-desc + chữ chỉ là số
ở vùng trên màn. App mới đặt tên id lạ thì **thêm vào yaml**, không sửa code, không
viết id của một app vào code hay vào workflow này.

Câu khác — hoặc **nhiều hơn một node cùng khớp** — thì dừng kèm lý do, **không
tap bừa**: tap sai chỗ trên máy thật là bấm vào quảng cáo hoặc mua hàng thật.

`Mở app không mạng` **không** phải là `Mở app`: tool ngắt wifi + data **trước**
`am start`, rồi bật lại và **chờ ping thông** (lệnh `svc` trả về ngay lúc mạng
chưa lên). Cuối case luôn trả mạng về, kể cả khi case hỏng giữa chừng — để máy
mất mạng là hỏng mọi lượt sau mà không ai biết vì sao.

Hai chỗ nới lỏng có chủ ý, vì cái giá sai khác hẳn cái giá sai của một cú tap:

- **Câu vuốt không nêu hướng** (`Vuốt theo đúng hướng icon gợi ý`) thì lấy hướng
  sang trang kế (trái). Vuốt không bấm trúng gì nên đoán sai chỉ làm màn không đổi
- **Vế sau dấu phẩy nếu chỉ là quan sát, đối soát console, hoặc một cú chờ thì
  không chặn bước đi tới màn**: `Chạy luồng FO đến OB3, quan sát banner` lái được;
  `Vào màn OB2, chờ hết timeout load ad` lái tới rồi **đứng yên 12s** tại đó. Vế
  sau là việc khác mà tool không làm được thì vẫn dừng — lái tới nơi rồi coi như
  xong bước là bỏ im vế sau, case đó có thể ra PASS giả

**Chấm được PASS/FAIL** từng dòng Expected: dòng về quảng cáo chấm bằng log
request/load/show, dòng về chữ và node chấm bằng cây UI, dòng *"icon là animation
lặp"* chấm bằng cách chụp nhiều khung rồi so vùng node, dòng *"user vuốt sang màn
kế"* chấm bằng **một cú vuốt thật**, dòng *"app bắn event X"* chấm bằng log
`FA-SVC`, dòng *"luồng FO thông suốt"* chấm bằng nhật ký lái. Dòng thật sự phải
nhìn mắt (đúng design, đúng màu) ra `NOT_VERIFIABLE` — **không được đoán thành
PASS**. Đó là giới hạn của tool, không phải của lượt chạy: Claude tự đo tiếp theo mục 5b.

**Verdict của case = dòng xấu nhất trong MỌI dòng**, trừ dòng của PO. Dòng chưa
chấm được cũng kéo case xuống: trước đây chúng bị loại khỏi verdict, nên một case
chỉ chấm được mỗi dòng `"không crash"` vẫn ra PASS trong khi dòng quyết định không
ai đụng tới — PASS hụt, người đọc tưởng đã test xong nên không ai test lại.

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

**Người dùng chỉ cần gửi package** (user chốt 06/10/2026). Còn lại tự lấy, không hỏi:

| Cần gì | Lấy ở đâu (mặc định) |
|---|---|
| Bản SDK First Open | log app `VslTemplate4FirstOpenSDK: Using version …` (lọc PID) → tab số lớn nhất ≤ bản đó |
| Bộ TC | sheet TC `https://docs.google.com/spreadsheets/d/1sNFXM7oGzx_addpimZL7RYk2rXpRs_We6YUHpdtWSqU/edit` — tool tải bản mới nhất |
| ID ads từng vị trí | sheet "Check thông số KT" `https://docs.google.com/spreadsheets/d/14XivZl9VPAnyf8hYICgRh-TOUmkGTZDCqoyWmPM57hM/edit` — tool tải mỗi lượt, chọn tab theo dòng `Package name` |
| Version app (tiêu đề report) | `dumpsys package <pkg> \| grep versionName` → `--app-label "<tên> <version>"` |
| User state / test data | cột `User State` (new = `pm clear`, old = đã vào Home) và cột `Test Data` của TC |

Chỉ hỏi khi: log không in bản SDK (hỏi bản SDK), sheet ID không có tab của package
(báo user bổ sung tab), hoặc cắm nhiều máy. SDK riêng `rating` / `widget` /
`daily checkin` chỉ chạy khi user nhắc tên.

Ba kiểu gọi, chọn theo `$ARGUMENTS`:

```
# a. chi doc baseline - xem app co bao nhieu key, key nao bi mirror
cd <repo> && .venv/bin/rcr-check --package <pkg> [--serial <S>]

# b. nap bo testcase - xem case nao tool chay duoc, case nao can nguoi
cd <repo> && .venv/bin/rcr-check --package <pkg> --tc "<link sheet TC>"

# c. chay 1 hay nhieu case, xuat report HTML kem anh tung buoc
cd <repo> && .venv/bin/rcr-check --package <pkg> --tc "<link sheet TC>" --tab 3.4.0 \
  --case 3.4.0#SDK340-SPL-001,3.4.0#SDK340-SPL-003 --report out/run.html
cd <repo> && .venv/bin/rcr-check --package <pkg> --set splash_banner_change=false
```

**Bộ TC lấy từ Google Sheet, KHÔNG tìm file trong Downloads** (user dặn 2026-10-03).
Mặc định `--tc` là link workbook chung mọi bản SDK:

```
https://docs.google.com/spreadsheets/d/1sNFXM7oGzx_addpimZL7RYk2rXpRs_We6YUHpdtWSqU/edit
```

Tool tự tải bản **mới nhất** về `out/tc-<id>.xlsx` mỗi lần chạy. File tải tay trong
Downloads dễ lệch bản: ngày 02/10 tôi chạy cả buổi bằng `(2).xlsx` trong khi đã có
`(3).xlsx` mới hơn. Người dùng đưa link sheet khác hoặc chỉ định một file `.xlsx` cụ
thể thì dùng đúng cái đó. Tải không được (sheet riêng tư) thì dừng và báo, **đừng lùi
về file cũ trong Downloads**.

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
(`3.5.0#12`, `rating#4`) vì số case trùng nhau giữa các tab. Tab viết theo format mới
(3.4.0 trở đi) dùng cột `TC ID` thay cho `N°` → mã case là chính TC ID
(`3.4.0#SDK340-SPL-001`). Gõ mỗi con số vẫn được nếu
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
| `--app-label "Piclux 2.8.0"` | tên + **version của APP** in trên tiêu đề report — **luôn truyền khi có `--report`**. Đừng nhét version SDK vào đây: "SDK First Open" là ô riêng, nhét nhầm thì ô đó ra `—` và tiêu đề cụt đuôi |
| `--fresh` | ép app về trạng thái chưa từng mở (reset mềm, hoặc `pm clear`) — case Precondition đòi user mới |
| `--sdk 3.2.0` | khai thẳng bản SDK FO. Dùng khi máy không ra log, **và khi workbook chỉ có một sheet** — bộ một sheet không cần bản SDK để chọn tab nên tool chỉ soi buffer log sẵn có, không thấy thì ô SDK trên report để trống |
| `--full-walk` | đi hết luồng FO như TC ghi. **Mặc định tool dừng ở màn SÂU NHẤT case đụng tới**, suy từ cả key case đặt lẫn mã vị trí trong dòng Expected — case tắt 10 unit từ 102 (splash) tới 303 (OB3) thì dừng ở OB3, bỏ 4 màn sau. Chỉ bật khi thật sự cần đi tiếp |
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

- `PASS` — chấm rồi và khớp Expected. **Ad không fill mà có request ĐÚNG unit của
  vị trí trong câu (hoặc vị trí case bật) cũng là PASS** (user chốt 25/09, nhắc lại
  06/10/2026): không fill là chuyện của kho quảng cáo. Không có request nào của vị
  trí đó → FAIL. **Đừng tự đổi luật này sang BLOCKED**
- `FAIL` — lệch Expected, kèm số đo thật (unit nào đã request, log ra sao)
- `NEEDS_HUMAN` — tool chưa lái tới được màn cần, hoặc quảng cáo che màn nên không đọc
  được chữ trên app. **Không kết luận gì về app** từ verdict này, và **không trả về cho
  người dùng** — đi tiếp mục 5b, tự làm trên máy cho ra PASS/FAIL
- `NOT_VERIFIABLE` — dòng đòi nhìn mắt (đúng design, đúng màu), hoặc
  dòng hỏi số liệu trên **AdMob/Firebase console**. Dòng console là việc của **PO**:
  tester không có quyền vào console, nên báo cáo đếm riêng (`po`), **không** gộp vào
  `pending`. Bước Action bảo mở console cũng bỏ qua, không dừng case lại.
  Dòng nhìn mắt (màu, vị trí, animation) **không** dừng ở đây — làm mục 5b
- `CONFIG_OK` / `BLOCKED` — case không có Expected: đặt được config, hoặc config không
  sống qua lần mở app (build dev đặt `minimumFetchInterval = 0`). `BLOCKED` còn
  dùng khi **precondition chưa thành hiện thực** (xem mục dưới) hoặc khi điều kiện
  của một dòng `"Nếu X thì Y"` không hề xảy ra trong lượt chạy
- `KEY_NOT_USED` — key không có chuỗi trong `classes*.dex`: **app không đọc key đó**,
  template Firebase dùng chung nhiều app. Chấm tiếp là ra PASS giả

Case có nhiều lượt thì `run.runs` là từng lượt; verdict case = lượt xấu nhất.

**Verdict case = dòng xấu nhất trong MỌI dòng, trừ dòng của PO.** Dòng chưa chấm
được cũng kéo case xuống — đọc kèm `pending` để biết còn bao nhiêu dòng bỏ ngỏ.
Case PASS nghĩa là **mọi dòng đều đã được chấm**, không phải "dòng nào chấm được
thì đều đạt".

### Precondition có thành hiện thực không

Nhiều case đòi một **điều kiện môi trường** chứ không chỉ đòi config: *simulate
no-fill*, *chặn mạng đến ad server*, *throttle ≤50kbps*, *bật mediation test
mode*. Không tạo được điều kiện đó thì case chạy dưới trạng thái tự nhiên của
máy — và **nhiều case tả nhiều điều kiện khác nhau sẽ cùng ra một kết quả**, đọc
report tưởng đã phủ nhiều nhánh (đo 28/09/2026: case 22/23/24 đều PASS trong khi
chỉ một trạng thái từng xảy ra).

Tool xử lý:

- **Ép được** — đổi `id_*` của vị trí sang slot trống (`…/0000000001`): request
  vẫn đi, vẫn đếm được trong log, nhưng không bao giờ có ad. **Chỉ dùng được với
  vị trí mà remote config có khai `id_*`** — Piclux chỉ 12/92 vị trí, và 302
  (OB2) không có
- **Không ép được** — throttle băng thông, mediation test mode, cần root: case
  **không được ra PASS**, verdict hạ xuống `BLOCKED` kèm lý do ở
  `precondition_thieu`
- **Dù ép hay không, vẫn kiểm bằng log**: `ep_ad_fail` nói đã ép bằng cách nào,
  hoặc "không ép được nhưng log cho thấy ad tự không fill". Ép rồi mà ad vẫn fill
  thì cũng là `BLOCKED` — ép hỏng

**Ngắt mạng KHÔNG phải cách giả lập no-fill.** Đo trên máy thật 28/09/2026: mất
mạng thì log **không có unit ads nào** — SDK không gửi nổi request. No-fill thật
là *"có request, kho không trả ad"*. Hai trạng thái khác hẳn nhau.

Cách thủ công của tester: **lắc máy → Ad Inspector → chọn Meta**. App lưu trạng
thái này ở `shared_prefs/admob.xml` key `inspector_info`, trường `networkExtras`
— tool ghi được file đó bằng `run-as`, nhưng **chưa biết schema** của trường này.
Muốn tự động hoá thì nhờ tester lắc máy chọn Meta một lần rồi đọc `inspector_info`
ra để lấy đúng payload.

`run.runs[i].drive` là nhật ký lái: từng bước ra thao tác gì, dừng ở bước nào và vì
sao. `status: NEEDS_HUMAN` ở đây **không phải bug app** — là tool từ chối đoán. Hai
lý do hay gặp: quảng cáo đang che màn hình (đóng ad rồi chạy lại), và nhiều node
cùng khớp một chuỗi (sửa câu Action cho rõ node nào). `--no-actions` để chỉ đặt
config, không lái.

`run.reset` nói đã đặt lại trạng thái kiểu gì: `force-stop` / `soft` (lật cờ
onboarding) / `clear` (`pm clear` — **mất login và data của app trên máy đó**,
nói cho người dùng biết, đừng để họ phát hiện sau).

Sau reset mềm, **màn onboarding nằm sau splash ad** và ad không tự đóng. Tool cố
tình không tap để đóng — tap sai chỗ là bấm quảng cáo thật. Đừng báo như app không
vào được onboarding, và đừng bảo người dùng tự đóng ad: lấy bằng chứng theo mục 5b.

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

Case `needs_human` **không phải lỗi tool và không phải bug app**. Nếu lý do là giá trị
còn chỗ trống mà server của chính app đang có giá trị thật cùng loại (vd
`splash_ui_config` type gif có `media_url` thật) thì dùng giá trị đó, chạy theo mục 5b,
ghi rõ trên report là đã thay. Không có giá trị thật nào thì báo tách hẳn khỏi phần
chạy được, kèm nguyên văn lý do.

## 5b. Còn dòng NEEDS_HUMAN / NOT_VERIFIABLE → tự làm trên máy, KHÔNG hỏi, KHÔNG giao lại

User đã nhắc **hai lần** (28/09 và 03/10/2026): *"cái nào need_human hoặc not_verify
thì phải tự mà action để trả ra pass/fail"*. Verdict của tool chỉ là điểm xuất phát.
Lượt chạy **chưa xong** khi còn dòng `NEEDS_HUMAN` / `NOT_VERIFIABLE` (trừ dòng console
của PO). Không báo kết quả, không publish, không viết "bạn tự mở app xem" trước khi
làm hết các bước dưới đây:

1. Đặt config của case bằng `--set '<key>=<value>' --keep` (cùng reset như tool:
   `pm clear` + mở app 1 lần cho fetch nếu case là new_user). **Giữa hai lượt `--keep`
   phải `--restore`**: `--keep` lần 2 ghi đè snapshot, restore khi đó ra giá trị bẩn
2. Tự lái bằng adb (`am start`, `am force-stop`, `input swipe`, `svc wifi`) theo đúng
   câu Action. **Vẫn không tap vào vùng ad**: lấy bằng chứng trước khi ad hiện, hoặc
   từ log
3. Lấy bằng chứng, chọn theo loại dòng:
   - màn qua nhanh / bị ad che: `screenrecord` rồi tách khung. Máy không có ffmpeg:
     `python3 -m venv <scratchpad>/fv && <scratchpad>/fv/bin/pip install imageio-ffmpeg pillow`.
     Splash thật thường chỉ đứng 1–2s trước "Loading Ads…"
   - màu / chữ / vị trí: `screencap -p` (PNG, **không** lấy màu từ video) + `uiautomator
     dump`. Màu chữ = pixel không đổi giữa hai khung khác nền
   - thời điểm, chớp trắng, animation: timestamp từng khung thật
     (`-fps_mode passthrough` + `showinfo`), đừng đếm khung đã nội suy
   - "cold start lần 2", "kill app": `am force-stop` + `am start`, đo **ít nhất 3 lượt**
   - màn đứng quá ngắn để thấy hết (GIF lặp, timeout, animation dài): **giữ splash bằng
     Private DNS hỏng** — `settings put global private_dns_specifier invalid-dns.example.invalid`
     + `private_dns_mode hostname`. Máy vẫn báo có Wi-Fi nên app không bỏ qua ads,
     request ad treo tới timeout → splash Photomaker đứng ~18s (đo 05/10/2026). Xong
     **luôn** `settings delete global private_dns_mode` + `private_dns_specifier` rồi
     chờ ping tên miền thông. Ngắt hẳn wifi/data thì KHÔNG được: app bỏ qua ads, splash
     còn ngắn hơn. GIF lặp chấm bằng cách khớp từng khung quay được với khung của file
     GIF gốc (centerCrop + autocontrast): chỉ số khung tăng rồi rơi về đầu = một lần lặp
   - log app thường trả lời thẳng: `adb logcat -d | grep <Activity>` (vd
     `Splash media ready … source=DATA_DISK_CACHE view=1080x2280`)
4. Chấm từng dòng với **số đo thật** làm lý do. Report gửi đi **chỉ có PASS / FAIL**
   (user nhắc lần 3, 06/10/2026: *"không được phép need_human với not_verifiable
   blocked"*). Điều kiện chưa đạt thì tự ép, tự chạy lại; lỗi đọc/race của tool thì
   tool tự thử lại (`run_batch` chạy lại case tối đa 3 lần khi verdict lơ lửng)
5. Trả máy về sạch: `--restore`, rồi đọc lại key đã đổi để đối chiếu với giá trị gốc.
   Lệch (snapshot bị ghi đè) thì `pm clear` + mở app cho fetch lại từ server.
   Mạng đã ngắt thì bật lại và chờ ping thông
6. Dựng report theo đúng bố cục mục 6, ghi rõ dòng nào Claude chấm tay và đo bằng gì,
   rồi publish

## 5c. Rà PASS giả TRƯỚC khi báo — bắt buộc

06/10/2026 báo "35 PASS / 1 FAIL", user hỏi *"liệu có pass giả không"* → rà lại thì 3
case PASS bằng **ad của vị trí khác**. Từ giờ, trước khi báo số, đọc `reason` của
**từng dòng PASS** (`lines[].r` trong JSON) và kiểm:

1. **Dòng ads phải đúng unit của vị trí.** Reason phải nêu unit (`*****993`) thuộc
   đúng vị trí trong câu. Thấy unit của vị trí khác (đòi 302 mà reason là 201 …394)
   = PASS giả, sửa tool. Tra unit ↔ vị trí: sheet **"Check thông số KT"** (mặc định
   `https://docs.google.com/spreadsheets/d/14XivZl9VPAnyf8hYICgRh-TOUmkGTZDCqoyWmPM57hM/edit`).
   Mỗi lượt tool **tự tải bản mới nhất**, chọn tab theo dòng `Package name` (không theo
   tên tab ADA895/AIP916…), đọc mục ID ads FO + resume. Log in `ID ads tung vi tri: …
   N vị trí` — **ra 0 / "không có tab nào ghi package"** thì app chưa có trong sheet:
   báo user bổ sung tab, đừng chạy tiếp như thể có ID. `data/ad_units.yaml` chỉ là bản
   dự phòng; ID đọc từ RC của máy vẫn thắng
2. **Không fill = PASS chỉ khi có request đúng unit.** Không phải "có ad nào đó được
   request"
3. **Dòng nút X / số đếm OB3** khi ad không fill: phải có request native 303
   (…989 / …765) và khung chụp không thấy X. ID 303 **nằm cứng trong app** — RC không
   có `id_303_*`, **không ép fill được** bằng cách đổi ID; đừng tốn lượt thử
4. **Timer OB3 không có ad** tính từ lúc ad **fail** (SDK đếm từ đó): đo ra 3.0/4.0/
   5.0/6.0s là đúng. Nói rõ trong báo cáo là nhánh không-ad
5. **Câu khẳng định có vế phủ định** (`Button X hiển thị NGAY (không có số đếm ngược)`)
   không phải câu phủ định. PASS với lý do "không thấy X" cho câu đòi X hiện = sai
6. **Dòng PASS nhờ luật** (TBD ghi nhận thực tế, `[Assume]`) — nêu riêng trong báo cáo
   để PO chốt, đừng gộp im vào PASS
7. Soi được **offline**: JSON lượt cũ có `cases[].ads` (`u`, `req`, `load`, `show`,
   `keys`). Kiểm request đúng unit từ đó trước, **chỉ chạy lại case thật sự PASS giả**

### Chạy lại: chỉ case chưa PASS / PASS giả, rồi gộp

User: *"chạy lại case chưa chạy được thôi chứ case pass rồi thì đừng chạy lại"*,
*"chạy lại case pass giả thôi"*. Lấy key từ JSON lượt trước, chạy `--case` đúng các
key đó, rồi gộp: record của lượt sau đè lượt trước theo `key`, dựng lại trang bằng
`report_html.build(report_data.page_data(baseline, tc, records, app_label))` (baseline
chỉ cần `serial`, `package`, `configs`, `mirrored_keys`). Publish đè **cùng link**.

### Bẫy đã gặp (06/10/2026, Piclux 2.8.0) — tool đã xử lý, đừng đi tìm bug app

- `activate.json không phải JSON hợp lệ` ngay sau `pm clear`: đọc trúng lúc SDK đang
  ghi. Tool tự đọc lại (4 lần) — không phải lỗi app, không BLOCKED
- Mã vị trí viết tắt `302` phải khớp `302_onb2_n_native` — so nguyên văn thì dòng
  "không load ad 302" luôn không chấm được
- TC ghi `layout_native_ads_language_1`, APK chỉ có `layout_ad_native_lfo_1` (shimmer
  chung bộ id) → chấm bằng đủ bộ `nativeAdView, ad_headline, ad_media, ad_call_to_action`
  (`data/ui_names.yaml`, trường `ids_all`)
- Sau `pm clear` config mới có `enable_all_ads*=false` → tool tự đặt nền `true`; log ads
  trống thì đọc 3 key này trước khi nghi app
- (07/10/2026) "Ad vị trí X show / KHÔNG show tại màn Y": tool chấm bằng event `ad_show`
  gán theo `<màn>_view` gần nhất (`assert_ad_screen`), không bằng request — request ở màn
  nhà là đúng chỗ. Log `ad_show` có thể có mà màn trống → dòng khẳng định "hiển thị" vẫn
  phải mở ảnh đối chiếu (5d)
- (07/10/2026) "Đi qua LFO2 nhanh" / "chưa kịp show ở LFO2": tool học tọa độ ở lượt đầu
  rồi bấm qua LFO trong ~0,8s; log cho thấy ad LFO2 vẫn show ở LFO2 → BLOCKED và tự chạy
  lại. Không đạt sau các lần chạy lại thì đó là giới hạn thời gian của máy, nói rõ

## 5d. Rà FAIL giả TRƯỚC khi báo — bắt buộc

07/10/2026 báo 12 FAIL, user hỏi lại thì 8 FAIL là sai (tool nhìn trễ + video Claude
quay rơi đúng lượt config bị fetch đè). User chốt: *"fail thì phải tìm cách check lại
xem có fail thật hay không trước khi xuất report"*. Mỗi case FAIL, trước khi publish:

1. **FAIL phải lặp lại.** Tool tự chạy lại case FAIL; chỉ giữ FAIL khi lần sau cũng
   FAIL (`lich_su_verdict`). FAIL rồi PASS → chạy thêm phân xử, report ghi "KHÔNG ỔN
   ĐỊNH" kèm các lần — không được giấu
2. **Config còn sống tới cuối lượt.** App fetch Firebase lúc mở; lần fetch thật (log
   `Fetch firebase successfully in` > ~400ms, đọc cache ~280ms) kích hoạt lại giá trị
   server và đè patch. Tool đọc lại config sau khi chấm, lệch → BLOCKED + chạy lại.
   Claude đo tay thì **luôn ghi `logcat -v epoch`** và kiểm dòng fetch trước khi tin
   kết quả. Ad đã tắt mà vẫn chạy / X đã bật mà không hiện → nghi config bị đè trước
3. **Đối chiếu bằng chứng của chính tool.** Mở ảnh chụp của case: ảnh thấy thứ dòng
   FAIL bảo "không thấy" (vd nút X) → tool nhìn sai, không phải app sai
4. **Nguyên nhân phải giải thích được bằng số đo** của lượt có config đúng. Một video
   / một lượt ngược với tool chưa đủ kết luận bug — lặp ít nhất 2 lượt
5. **Thao tác tay canh giờ theo đồng hồ MÁY** (`adb shell 'echo $EPOCHREALTIME'`),
   không theo đồng hồ máy tính (lệch ~0,8s). Chỉ tap khi đã thấy node trong cây UI —
   tap mù theo tọa độ trúng ad (07/10/2026: mở Chrome)
6. FAIL nào đã rà xong mới được ghi "cần báo dev". Ghi rõ đã kiểm gì ở mục thực tế

## 6. Xuất report

Luôn truyền `--report <repo>/out/run-<pkg>-<hhmm>.html` khi chạy `--case`: trang
HTML tự chứa, `out/` đã gitignore. Bố cục **tester đã chốt** — đừng đổi:

1. Header: eyebrow · H1 · dòng meta (App + package + version, Máy, Ngày)
2. **4 thẻ đếm** PASS / FAIL / BLOCKED / N-A — bấm vào là lọc
3. Khối **"cần xử lý"** ngay đầu trang: FAIL cần báo dev · BLOCKED cần chạy lại ·
   cần PO đối soát console
4. Thanh lọc: chip trạng thái + ô tìm + "Mở tất cả"
5. **Danh sách case gập/mở**, nhóm theo Feature. Mỗi dòng Expected mang nhãn +
   lý do của **chính dòng đó** — không phải hai cột đánh số song song
6. Mở một case ra thấy: config đã đặt (kèm cách ép điều kiện nếu có), thực tế,
   precondition, các bước đã lái, bảng ad unit, ảnh từng bước

Trên report chỉ có **4 nhãn**, dịch từ verdict của tool qua `report_row.nhan_cua`:
`BLOCKED` = chạy lại thì ra kết quả (việc của tester); `N/A` = ngoài quyền tester
(console của PO, dòng phải nhìn mắt). Mã thao tác nội bộ (`noop`, `goto`, `net`)
**không được lộ ra** — luôn kèm tên tiếng Việt và lý do của bước.

Lượt đã **đo được thật** (có case ra PASS/FAIL/BLOCKED) thì publish trang đó thành
artifact **rồi tự mở link** cho người dùng — tool chạy ở máy, không tự lên claude.ai
được. Report của tool mà mọi case đều `NEEDS_HUMAN` thì **đừng publish trang đó**,
vì nó không nói được gì về app. Làm mục 5b trước, rồi publish report đã chấm tay.

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
chạy được / cần người, verdict cuối của từng case (sau mục 5b) kèm số đo chính, việc
cần báo dev/PO, và trạng thái máy (đã restore chưa, có `pm clear` không). **Không
liệt kê "bạn tự kiểm tiếp" cho dòng mà mục 5b làm được.** Chỉ nêu phần thật sự ngoài
tầm (console PO, điều kiện đã thử mà không tạo được) và nói đã thử gì.

**Đưa link artifact ngay trong câu trả lời**, đừng bắt người dùng đi tìm. Report
local (`<repo>/out/…html`) vẫn mở được bằng nháy đôi nếu publish hỏng.

**Dừng ở đây. Không `git add`, không `git commit`, không `git push`.** Lượt chạy
không sinh file nào trong repo. Sửa tool là việc riêng, người dùng sẽ tự nói.
