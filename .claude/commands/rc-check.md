---
description: Đổi giá trị Firebase Remote Config của app Android theo file testcase, hoặc tự chấm checklist SDK Next-Gen khi app dùng SDK 3.7.0 / 3.7.1, trên máy thật
argument-hint: "<package> [mục 1|2|3|4|all — chỉ khi app SDK 3.7.0 / 3.7.1: tự chấm checklist Next-Gen] [--tc <link sheet | bo-tc.xlsx> [--tab <X.Y.Z>] [--sdk <X.Y.Z>] [--case <key,key>]] [--set key=value] [--report <file.html>] [--app-label '<ten app> <version>'] [--serial <serial>] [--next-gen] [--fresh] [--full-walk|--no-walk|--no-actions] [--keep|--restore]"
---

Chạy `rcr-check` một lượt: đọc baseline remote config, nạp file testcase, đặt
config của một case rồi xác nhận nó sống qua lần mở app. Tham số: $ARGUMENTS

## 0. Tìm repo trước đã

Command chạy được từ thư mục bất kỳ — **đừng giả định CWD**. Lấy cái đầu tiên có
`src/rcr/cli_check.py`:

1. `git rev-parse --show-toplevel` (nếu CWD đang nằm trong chính repo này)
2. biến môi trường `$RC_RUNNER_REPO`
3. `~/projects/check_remote_config`
4. `~/Desktop/check_remote_config`
5. `~/check_remote_config`

Máy có **nhiều bản clone** thì cái đứng trước thắng, dù nó cũ hơn: đặt `RC_RUNNER_REPO` trỏ
vào bản đang dùng, và `git log -1` bản tìm được trước khi chạy (bản cũ thiếu `--preflight`,
chốt dừng `ad_click`…).

Repo có **hai remote** (github.com/DuyenLTA và github.com/LuuThiAnDuyen), nhưng
**tên remote mỗi máy đặt một kiểu** — đọc `git remote -v`, đừng giả định `origin`
là repo nào. Mỗi máy thường chỉ có credential của một tài khoản.

Không thấy thì dừng, nói rõ đã tìm ở đâu. Gọi đường dẫn tìm được là `<repo>`.

Gọi `<bin>` là thư mục lệnh của venv: `<repo>/.venv/bin` trên macOS/Linux,
`<repo>/.venv/Scripts` trên **Windows** (file là `rcr-check.exe`). Luôn gọi
`<bin>/rcr-check` — **đường dẫn tuyệt đối**. `rcr-check` không có trong PATH
toàn cục. Báo `command not found` thì
`cd <repo> && <bin>/python -m pip install -e ".[dev]"` rồi thử lại: venv cài
trước khi CLI được thêm thì thiếu file lệnh.

## 0b. SDK 3.7.0 / 3.7.1 → chấm checklist Next-Gen (tự chọn, không cần hỏi)

Không cần user nói SDK nào: bước `--preflight` (mục 3b) mở app một lần, đọc dòng
`VslTemplate4FirstOpenSDK: Using version X` của chính pid app và in dòng **`Bản SDK FO`**.

**Next-Gen = tutorial 3.7.0 và 3.7.1** (user chốt 27/10/2026, thêm 3.7.1 ngày 29/10/2026). 3.6.1 từng là bản Next-Gen nhưng đã *revert next-gen* → chạy
bộ TC như bản thường; bộ TC chưa có tab 3.6.1 thì tool chấm base + delta tới 3.5.3 và ghi chú phần thay đổi chưa có TC.

- **3.7.0 hoặc 3.7.1** (kể cả `-alphaNN`) → preflight in `Nhanh: checklist Next-Gen`, JSON có
  `"nhanh": "nextgen"`. **Không chạy các mục 4–7 dưới**: đọc toàn bộ `<repo>/sdk-check/WORKFLOW.md` và
  làm theo nó (checklist có sẵn trong `<repo>/sdk-check/references/`, report Khớp/Sai). Ở nhánh này bản
  release / ID ads test chỉ là `CHU Y`, không chặn.
- **`$ARGUMENTS` có `--next-gen`** (bot Discord truyền khi tin build của dev ghi next-gen và bot đã cài bản
  release) → truyền `--next-gen` vào lệnh `--preflight`: nhánh **luôn** là checklist Next-Gen, **bất kể số SDK**
  (AIP918 2.4.0: tutorial 3.7.1-alpha01 + GMA Next-Gen bị chạy nhầm bộ TC rồi chặn vì bản release, 29/10/2026).
- **Bản khác** (3.5.x, 3.6.x, 3.7.2, 3.8.x…) không có `--next-gen` → nhánh bộ TC như thường. User truyền `--tc` riêng thì luôn theo `--tc`.
- **`$ARGUMENTS` có `--sdk X.Y.Z`** (bot truyền số tutorial trong tin build) → truyền nguyên `--sdk` vào
  `--preflight` và mọi lệnh sau: **số trong tin build quyết nhánh + tab TC, không theo số app in ra log**. App in
  khác (`SDK tin build vs log app` = `CHU Y`) → vẫn chạy theo tin build, ghi dòng lệch lên đầu câu báo để dev xác
  nhận. AIP882 4.3.0 (29/10/2026): tin build + plan tuần ghi tutorial 3.6.1 (revert next-gen), app in
  `Using version 3.7.0` → tool tự chọn checklist Next-Gen, cả lượt chấm sai bản (user: "check vô nghĩa").
- Không đọc được bản (dòng `Bản SDK FO` là `CHU Y`) → hỏi user bản SDK, chạy lại preflight với `--sdk X.Y.Z`.
- Chạy case bằng bộ TC mặc định trên app 3.7.0 / 3.7.1 thì `rcr-check` dừng kèm lỗi (bộ chung không có tab
  Next-Gen, chọn tab cũ là chấm sai bản).

## 0c. Máy test AdMob — áp dụng cả nhánh bộ TC lẫn Next-Gen

**Mọi máy QA cắm vào đều là máy test AdMob** (user chốt 29/10/2026: "máy nào cũng là máy test"). Nên:
- `ad_click` (trong case, trong capture của bước 3c check ID ads, hay SDK tự bắn) **không** phải lý do dừng chờ
  người: ghi vào report rồi chạy tiếp. Được bấm quảng cáo khi case / dòng checklist cần đo.
- Lượt AIP805 1.4.0 (14) 29/10/2026 dừng ở 3c vì "máy chưa đăng ký test device" — sai.

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
`FA-SVC`, dòng *"luồng FO thông suốt"* chấm bằng nhật ký lái. Dòng **bố cục splash**
(*"progress + text neo ngay trên mép native"*, *"không đè banner"*, *"cách mép 12–16dp"*,
*"nhãn ngay dưới progress"*, *"giữa màn"*, *"không dịch chuyển khi native show"*) chấm bằng
bounds trong dump, đổi dp theo `wm density` (id ở mục `bo_cuc` của `data/ui_names.yaml`).
Dòng **màu chữ** (*"Title đúng màu #4957FF"*) chấm trên ảnh PNG gốc: đếm pixel trùng màu
(lệch ≤4/kênh) trong khung chữ so với dải đối chứng sát bên, bounds đọc lại theo từng khung
(cụm chữ splash nhảy lên khi native về). Nền trùng màu chữ thì ra NEEDS_HUMAN, không FAIL.
Dòng thật sự phải nhìn mắt (đúng design, ảnh full-screen) ra `NOT_VERIFIABLE` — **không được đoán thành
PASS**. Đó là giới hạn của tool, không phải của lượt chạy: Claude tự đo tiếp theo mục 5b.

**Verdict của case = dòng xấu nhất trong MỌI dòng**, trừ dòng của PO. Dòng chưa
chấm được cũng kéo case xuống: trước đây chúng bị loại khỏi verdict, nên một case
chỉ chấm được mỗi dòng `"không crash"` vẫn ra PASS trong khi dòng quyết định không
ai đụng tới — PASS hụt, người đọc tưởng đã test xong nên không ai test lại.

## 2. Package và điều kiện vào được app

**Chỉ nhận package id**, không nhận tên app: khớp theo tên là khớp mờ, gõ thiếu
một ký tự là patch nhầm app hàng xóm. `$ARGUMENTS` không có chuỗi nào trông như
`com.abc.xyz` thì **dừng và hỏi**. Trước khi hỏi, báo Discord (lỗi gửi thì bỏ qua):
`<bin>/rcr-notify --kind stop --title "Thiếu / sai package" --line="<$ARGUMENTS>" --action "Gửi package id dạng com.abc.xyz"`

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

- 0 máy → **dừng**: cần máy Android thật, USB debugging, đã bấm Allow. Báo Discord:
  `<bin>/rcr-notify --kind stop --title "Không có máy Android" --line "<package>" --action "Cắm máy, bật USB debugging, bấm Allow"`
- đúng 1 máy → không truyền `--serial` (tool tự lấy)
- nhiều máy → `--serial` lấy từ `$ARGUMENTS`; không có thì in danh sách và
  **hỏi**. Patch bừa lên máy người khác đang dùng là hỏng data của họ. Báo Discord:
  `<bin>/rcr-notify --kind stop --title "Nhiều máy, cần chọn" --line "<danh sách serial>" --action "Chọn serial máy cần chạy"`
- máy `unauthorized` không tính là dùng được
- `$ARGUMENTS` có `--serial` (bot Discord luôn truyền) → **mọi** lệnh `rcr-check` / `rcr-sdk-check` /
  `rcr-cai-build` / `adb` trong lượt đều kèm đúng serial đó, kể cả các lệnh mẫu dưới không ghi `[--serial]`.
  Bot chạy song song nhiều máy: sót một lệnh là nó đụng máy của lượt khác.

**Máy phải đang mở khoá.** Máy khoá thì PMS không resolve được activity nào, tool
báo không mở được app — nhìn y hệt app hỏng. Gặp lỗi đó thì bảo người dùng mở
khoá rồi chạy lại, đừng đi tìm bug trong app. Báo Discord:
`<bin>/rcr-notify --kind stop --title "Máy đang khoá màn hình" --line "<serial>" --action "Mở khoá máy rồi chạy lại"`

## 3b. Kiểm điều kiện trước khi chạy — luôn làm

```
cd <repo> && <bin>/rcr-check --package <pkg> [--serial <S>] --preflight [--next-gen]
```
(`--next-gen` chỉ khi `$ARGUMENTS` có — xem 0b.)

Khoảng 20 giây, kiểm hết một lượt: máy, màn hình không khoá, app đã cài, **vào được dữ liệu app
(bản debuggable / root)**, **ads dùng ID thật** (mở app một lần, đọc log `FA-SVC` tối đa 15s),
tải được sheet TC, sheet ID ads có tab của package, RAM trống của máy tính, **Private DNS
không còn sót** giá trị chặn/treo ads của lượt trước, và **không còn snapshot `--keep`** chưa
`--restore` (máy đang giữ config đã patch).

Dòng `Ads dùng ID thật` ra `LOI` = build request bằng unit test của Google
(`ca-app-pub-3940256099942544/…`): mọi vị trí chung một ID nên không quy được ad về vị trí
nào, dòng ads ra NEEDS_HUMAN hàng loạt hoặc PASS giả (24/10/2026, Piclux 2.4.0: native/banner
là ID test, inter 102 là ID thật — chạy 50 phút mới biết). **Dừng, xin dev bản debuggable dùng
ID ads thật**, đừng chạy thử. Exit 1 = có dòng `LOI` → **dừng**, in nguyên bảng cho người dùng kèm việc
cần làm (đừng chạy thử cho biết: 23/10/2026 cài nhầm bản release 3 lần mới phát hiện
lúc đọc baseline). Dòng `CHU Y` về RAM (< 4 GB) không chặn nhưng phải nói trước: lượt dài
có thể bị Claude Code tắt giữa chừng. Báo Discord khi dừng:
`<bin>/rcr-notify --kind stop --title "Chưa đủ điều kiện chạy" --line "<dòng LOI>" --action "<việc cần làm>"`

**Dòng `Plan tuần`** (cả hai nhánh): preflight đối chiếu bản SDK (tin build `--sdk` và số app in ra log) với dòng
của app trong tab tuần này của plan QA (link ở biến `RC_PLAN_TUAN_SHEET`). **Khác plan = `LOI` → dừng ngay, không
check ID ads, không chạy case** (user chốt 30/10/2026: "khác yêu cầu với plan thì dừng lại báo tôi luôn vào
qa-auto"). Gửi `rcr-notify --kind stop` như trên với nguyên dòng `Plan tuần`; lượt bot gọi thì `KET_QUA`
`trang_thai` = `DUNG`, `tom_tat` mở đầu "Build khác plan tuần: …" (tab, plan ghi gì, build ghi/in gì) — bot đăng
dưới tin build ở qa-auto. Plan chưa có tab tuần / không ghi SDK cho app / không tải được → `CHU Y`, chạy tiếp.

## 3c. Check ID ads (audit-fanout) — luôn làm, sau preflight, trước khi chạy case

User chốt 28/10/2026: trước khi auto rc-check phải check ID ads như `/audit-fanout`. Lý do:
mục 5c tra unit ↔ vị trí bằng chính sheet "Check thông số KT"; sheet lệch build thì dòng ads
ra PASS/FAIL theo ID sai mà không ai biết. Audit đối chiếu sheet đó với ID build đang chạy;
lệch thì **vẫn chạy tiếp** (mục 4 dưới) — user đổi lại 28/10/2026, trước đó là lệch thì dừng.

Áp dụng cho **cả hai nhánh** (bộ TC và Next-Gen §0b). **Bỏ qua** khi lượt không chạy case:
kiểu (a)/(b) ở mục 4, `--set` đứng riêng, `--restore`, `--tiep`, `--cham-tay`, `--gop` chỉ dựng
lại report. Preflight ra `LOI` thì đã dừng ở 3b, không audit.

1. Tìm repo audit: `$AD_AUDIT_REPO`, rồi `~/android-ad-audit` — lấy cái có
   `tools/ad-checklist-diff/audit_runner.py`. Không thấy thì **không chặn**: ghi
   "chưa check ID ads (không thấy repo audit)" vào câu báo rồi chạy tiếp mục 4.
2. Đọc **toàn bộ** `<audit-repo>/.claude/commands/audit-fanout.md` và làm đúng nó (bước 0–4:
   phân giải package, workflow, artifact, báo cáo markdown), với tham số
   `<package> --serial <serial>` — **luôn kèm serial** của lượt này (lấy từ `adb devices` khi
   chỉ có một máy). Đừng chép quy trình audit vào đây: hai bản sẽ lệch sau mỗi lần sửa.
3. Audit **không có tham số phụ** (`--apk`/`--skip`/`--force`): capture mặc định, runner tự bỏ
   qua lái máy khi build và sheet đều chưa đổi — lượt rc-check sau trên cùng build gần như không
   tốn thêm. Capture `pm clear` app: rc-check tự reset theo case nên không ảnh hưởng, nhưng nói
   trong câu báo. **Chạy xong audit mới chạy mục 4** — hai bên cùng lái một máy.
4. Theo kết quả audit:
   - `clean` → chạy tiếp mục 4 như thường.
   - **Lệch ID** = có dòng `Lệch` trong thống kê khớp/lệch, hoặc có `confirmed` → **KHÔNG dừng,
     chạy tiếp mục 4** (user đổi 28/10/2026: "lệch thì không sao, cứ chạy tiếp, đừng dừng lại").
     Không gửi `rcr-notify --kind stop`, không đặt `trang_thai` = `DUNG` vì lệch ID. Ở 5c/5d, dòng
     ads của vị trí lệch đối chiếu theo **unit thật trong log**, không theo sheet. Câu báo cuối
     liệt kê đủ vị trí lệch (vị trí · ID sheet → ID build) để người xem lại; phát biểu là "build
     lệch sheet, cần dev / ads-team xác nhận", đừng khẳng định bên nào sai.
   - chỉ có `disputed` / `unresolved` (chưa kết luận được là lệch) → cũng **không dừng**, xử lý
     như vị trí lệch ở trên.
   - `find_app.py` báo sheet không có tab / 2 tab cùng package → preflight đã chặn trường hợp
     thiếu tab; 2 tab thì lượt có người hỏi user theo audit-fanout, lượt bot ghi vào
     `tom_tat` rồi chạy tiếp bằng tab rc-check tự chọn.
   - workflow lỗi (máy rớt, runner lỗi) → không chặn rc-check; ghi lý do vào câu báo.
5. Audit tự publish trang riêng và tự báo Discord một tin (`artifact_link.py`) — **đừng báo
   thêm**. Giữ link trang audit để đưa vào câu báo cuối (mục 7).
6. **Không commit** gì bên repo audit (audit-fanout bước 4 đã dặn).

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
cd <repo> && <bin>/rcr-check --package <pkg> [--serial <S>]

# b. nap bo testcase - xem case nao tool chay duoc, case nao can nguoi
cd <repo> && <bin>/rcr-check --package <pkg> --tc "<link sheet TC>"

# c. chay 1 hay nhieu case, xuat report HTML kem anh tung buoc
cd <repo> && <bin>/rcr-check --package <pkg> --tc "<link sheet TC>" --tab 3.4.0 \
  --case 3.4.0#SDK340-SPL-001,3.4.0#SDK340-SPL-003 --report out/run.html
cd <repo> && <bin>/rcr-check --package <pkg> --set splash_banner_change=false
```

**Đừng truyền `--khong-claude`.** Cờ đó dành cho lượt chạy không có agent
(`chay-khong-claude.bat`): tin Discord của nó để lại case BLOCKED / NOT_VERIFIABLE cho
người, trong khi lượt có agent phải tự làm hết theo §5b–5d.

**Bộ TC lấy từ Google Sheet, KHÔNG tìm file trong Downloads** (user dặn 2026-10-03).
Mặc định `--tc` là link workbook chung mọi bản SDK:

```
https://docs.google.com/spreadsheets/d/1sNFXM7oGzx_addpimZL7RYk2rXpRs_We6YUHpdtWSqU/edit
```

Tool tự tải bản **mới nhất** về `out/tc-<id>.xlsx` mỗi lần chạy. File tải tay trong
Downloads dễ lệch bản: ngày 02/10 tôi chạy cả buổi bằng `(2).xlsx` trong khi đã có
`(3).xlsx` mới hơn. Người dùng đưa link sheet khác hoặc chỉ định một file `.xlsx` cụ
thể thì dùng đúng cái đó. Tải không được (sheet riêng tư) thì dừng và báo, **đừng lùi
về file cũ trong Downloads**. Báo Discord:
`<bin>/rcr-notify --kind stop --title "Không tải được sheet TC" --line "<link sheet>" --action "Chia sẻ sheet hoặc gửi file .xlsx"`

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
File có cột **`TC ID`** (`SDK350-OB3X-013`) thay cho cột số thì truyền thẳng mã đó:
`--case SDK350-OB3X-013,SDK350-OB3X-014` — đừng đánh số lại file.

Chạy cả tab thì lấy danh sách case chạy được từ lượt `--tc` không kèm `--case`, rồi
truyền hết vào `--case`. Mỗi case khoảng một phút trên máy thật: 53 case ≈ 50 phút →
**luôn `run_in_background`** và chỉ báo lại khi có FAIL, có case hỏng, hoặc khi xong.

File TC một sheet (bộ cũ viết riêng cho một app) thì không cần `--sdk`.

Kiểu (c) có tắt/mở lại app nên mất vài chục giây → chạy `run_in_background`, ghi
stdout/stderr vào `<scratchpad>` của phiên. Kiểu (a)/(b) chạy thẳng, vài giây.

stdout là **đúng một dòng JSON** (`baseline`, `tc`, `run`); tiến độ ra stderr.

**Kết quả ghi xuống đĩa sau MỖI case** vào file lượt (trường `luot` trong JSON, cạnh
report: `out/run-x.html` → `out/run-x.luot.json`), report HTML cũng cập nhật theo. Lượt bị tắt
giữa chừng (RAM máy tính, rút cáp, `device not found`) thì **đừng chạy lại từ đầu**:

```
cd <repo> && <bin>/rcr-check --package <pkg> --tiep out/run-x.luot.json
```

`--tiep` lấy lại bộ TC, tab, danh sách case, đường dẫn report từ file; bỏ qua case đã có
kết quả, chạy nốt phần còn lại và ghi tiếp vào chính file đó. Lệnh chết vì lỗi thì JSON
lỗi cũng có trường `luot` trỏ tới file này.

**Lượt tự dừng khi log có `ad_click`** (stderr `DUNG LUOT: case … co N ad_click`, record
có `ad_click > 0`, case BLOCKED). Tool chỉ được đóng ad (`fo_flow`: chạm nút Close, rồi
BACK), không được bấm vào; click trên unit thật là traffic không hợp lệ, và app rời luồng
nên kết quả case đó không dùng được. Case đó không chạy lại, các case sau không chạy. **Đây
là điểm chặn của người**: báo ngay, kèm case + unit đang show, **không tự `--tiep`**:
`<bin>/rcr-notify --kind stop --title "Có ad_click trong lượt" --line "<case> · <N> ad_click" --action "Kiểm cách đóng ad trước khi chạy tiếp"`

**Mọi máy là máy test AdMob (mục 0c):** ad_click không phải traffic không hợp lệ, **không** dừng chờ người:
ghi ad_click vào report (case + unit), chạy lại riêng case bị ad_click (`--case <key>`, kết quả lần đầu không
dùng được vì app rời luồng), rồi `--tiep` chạy nốt các case còn lại.

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
cd <repo> && <bin>/rcr-check --package <pkg> [--serial <S>] --restore
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
- `tc_lech` — giá trị JSON TC đặt có trường mà giá trị server của cùng key không có
  (TC SDK 3.4.0 đặt `image_url`, server Piclux dùng `media_url`). **Chỉ là cảnh báo**:
  đọc log app trước khi kết luận TC sai — Piclux 2.4.0 đọc cả `image_url`
  (`applySplashUiConfig … mediaUrl=<link image_url>`, đo 24/10/2026). Report hiện ở
  "TC lệch giá trị server"

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

**Precondition "ad không fill / chặn ad server"**: RC có khai `id_*` của vị trí thì tool đổi sang slot trống; ID nằm
cứng trong app (RC không khai) thì tool tự bật Private DNS `dns.adguard-dns.com` cho cả case (chặn domain quảng cáo,
Firebase vẫn chạy), đổi wifi để bỏ cache DNS, xong trả DNS cũ về. Report ghi rõ ở `ep_ad_fail`: lúc đó **mọi** vị trí
đều không về ad — dòng Expected cần ad vị trí khác hiện thì đo tay.

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
   từ log. **Không gửi phím hay tap nào khi `AdActivity` đang hiện ad thật** — kể cả
   `input keyevent BACK`: 24/10/2026 (Piclux 2.4.0) BACK trên inter thật …588, 2,2s sau
   log có 2 `ad_click`. Dòng "dismiss ad → sang màn X" chấm tay thì đổi `id_*` của vị trí
   đó sang unit test của Google (ad test đóng an toàn), hoặc để tool lái (`fo_flow` có canh
   `ad_click`), hoặc nhờ người đóng. Muốn qua ad thật thì `am force-stop`
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
   - bước "Xem logcat tag X" (version Lib Ads, Adjust, FB ID…) **là chấm được**: lọc đúng tag
     như check ID ads, tìm theo **nhãn** (`Version Lib Ads`) chứ không theo giá trị kỳ vọng
     (29/10/2026 AIP805: chỉ tìm `1.2.9` không thấy rồi ghi NOT_VERIFIABLE, thật ra build là
     1.2.10). Tag `FOR_TESTER_CONFIG` chỉ in khi bật tester mode: `pm clear` → `pm grant <pkg>
     android.permission.POST_NOTIFICATIONS` (hộp xin quyền che icon thì bấm không ăn) → mở app,
     chờ ~1,5s → bấm `splashAppIcon` 25 lần, có toast "Change to tester ad mode" là được.
     Tab "các tag check" của sheet TC ghi tag nào check gì
   - resume / ẩn app: bấm **Home** rồi mở lại bằng **icon** (`monkey -p <pkg> -c
     android.intent.category.LAUNCHER 1`), không mở qua Recent — nhiều máy không coi Recent là
     ẩn app (user 29/10/2026). Android 11 không có dòng `topResumedActivity`, đọc `mResumedActivity`
   - inter có hiện full màn / lộ nền app không: chụp liên tục `screencap` ~0,15s/khung từ lúc
     bấm tới khi inter đứng yên. Dải trắng status bar được; nhìn thấy màn app phía sau là lỗi
   - precondition đòi máy khác (OPPO, Samsung…): **nhắn qa-auto** (trả lời dưới tin build) nhờ
     cắm máy đó, máy lên là tự chạy tiếp — không để NEEDS_HUMAN, không chỉ hỏi ở terminal.
     App trên máy mới là bản store (không `DEBUGGABLE`, `run-as` lỗi) thì `pm path` + `pull`
     APK debug từ máy cũ, gỡ bản store, cài APK debug
4. Chấm từng dòng với **số đo thật** làm lý do. Report gửi đi **chỉ có PASS / FAIL**
   (user nhắc lần 3, 06/10/2026: *"không được phép need_human với not_verifiable
   blocked"*). Điều kiện chưa đạt thì tự ép, tự chạy lại; lỗi đọc/race của tool thì
   tool tự thử lại (`run_batch` chạy lại case tối đa 3 lần khi verdict lơ lửng). Tool
   **không** chạy lại khi các dòng còn mở đều suy từ câu chữ, khi lần sau ra y hệt lần
   trước, hoặc khi precondition không tạo được (case đó ra BLOCKED kèm lý do ngay)
5. Trả máy về sạch: `--restore`, rồi đọc lại key đã đổi để đối chiếu với giá trị gốc.
   Lệch (snapshot bị ghi đè) thì `pm clear` + mở app cho fetch lại từ server.
   Mạng đã ngắt thì bật lại và chờ ping thông
6. Ghi từng dòng đã đo vào file lượt bằng lệnh, **đừng sửa tay JSON**:
   ```
   cd <repo> && <bin>/rcr-check --package <pkg> --cham-tay out/run-x.luot.json \
     --case 3.4.0#SDK340-UI-001 --dong 1,4 --ket PASS --ly-do "<số đo + cách đo>" \
     --anh out/manual/A_ob2.png,out/manual/A_ob4.png
   ```
   **Luôn kèm `--anh`** ảnh chụp màn đã dùng để chấm (đúng màn của case, không phải ảnh chung cả lượt): report
   nhúng ảnh ngay ở case, đưa kết luận đo tay lên đầu và gập lượt tự động của tool lại — người đọc nhìn ảnh là
   kiểm được, không phải tin chữ (user 29/10/2026: report khó nhìn). Dòng chấm theo log / số đo không có màn
   hình thì không cần ảnh.
   Tool tính lại verdict case (dòng xấu nhất, trừ PO; precondition thiếu / có ad_click thì
   vẫn BLOCKED), giữ dấu vết `cham_tay` (ai, lúc nào, lý do) và dựng lại report. Hạ PASS giả
   cũng bằng lệnh này (`--ket NEEDS_HUMAN`). Lượt đo tay **đã tạo được** precondition mà lượt
   tool không tạo được thì thêm `--dieu-kien-dat "<cách tạo>"`: bỏ `precondition_thieu` của lượt
   tool, ghi cách tạo lên report (không gỡ `ad_click`). Rồi publish
   **Không nối `--cham-tay` qua `| head`/`| tail`**: pipe đóng sớm làm tool chết ngay sau khi dựng report,
   **trước khi ghi file lượt** → lần chấm mất (29/10/2026). Đẩy output vào file rồi đọc lại verdict trong JSON.
   User báo **đã sửa TC** → tải lại sheet, đối chiếu mọi case bị ảnh hưởng, chấm lại **và** sửa câu kỳ
   vọng `lines[].e` theo TC mới (`--cham-tay` chỉ đổi verdict, report sẽ hiện "1.2.9 … PASS"), publish
   vào link cũ, báo qa-auto — không hỏi "có sửa report không" (user 29/10/2026: *"ô kh sửa lại report à"*)

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
   request". Dòng thứ tự preload / alternate cũng vậy: tool chỉ xét unit map được về vị trí
   trong câu (24/10/2026 trước đó đếm mọi unit cùng loại, REG-002 "preload 201" PASS bằng
   native test …110)
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
*"chạy lại case pass giả thôi"*. Lấy key từ file lượt trước, chạy đúng các key đó kèm
`--gop <file lượt trước>` (file lượt mới hoặc JSON kiểu cũ đều đọc được): record của lượt sau đè lượt trước theo `key`, report ra đủ cả
case cũ lẫn case vừa chạy lại.

```
cd <repo> && <bin>/rcr-check --package <pkg> --tc "<link>" --case <key,key> \
  --gop out/run-x.luot.json --report out/run-x-gop.html --app-label "<tên> <ver>"
# chi gop cac file luot co san, dung lai report - KHONG can may:
cd <repo> && <bin>/rcr-check --package <pkg> --gop out/a.json --gop out/b.json --report out/gop.html
```

`--gop` lặp lại được, file sau thắng file trước; file của app khác thì tool từ chối. Đừng
tự viết Python gộp record nữa. Publish đè **cùng link**.

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
7. **Bằng chứng trên report phải cùng lượt với kết luận.** Vá kết quả chấm tay vào report
   thì thay luôn bảng ads / ảnh / config bằng bản ghi của lượt hợp lệ. Lượt điều kiện
   không thành (vd 202 đã show ở LFO2) hoặc config bị đè thì ghi rõ "không dùng làm bằng
   chứng" — 07/10/2026 user đọc bảng ads của lượt sai điều kiện và bắt được FAIL mâu thuẫn

## 5e. Gặp lỗi của tool giữa lượt → Claude tự sửa, KHÔNG giao lại user

User chốt 24/10/2026: chạy app khác mà tool lỗi / chạy chập chờn / PASS giả / BLOCKED thì
**user không phải ngồi sửa**. Lượt chạy chưa xong khi lỗi tool còn làm sai kết quả.

1. Phân biệt trước: **bug app** (báo dev), **điều kiện máy/tài khoản** (mạng, máy khoá, sub
   test — tự xử), hay **lỗi tool** (crash, lái sai màn, nhận nhầm node, regex log không khớp app
   mới, PASS/FAIL giả do cách chấm). Chỉ loại cuối mới sửa code.
2. App mới đặt tên id lạ → thêm vào `data/ui_names.yaml`, không sửa code (mục 1).
3. Lỗi code → sửa đúng chỗ gốc trong `src/rcr/` (hoặc `sdk-check/scripts/`), thêm test tái hiện
   đúng tình huống vừa gặp, chạy **cả bộ** `<bin>/python -m pytest -q` — đỏ thì sửa tới xanh.
4. Chạy lại **chỉ các case bị lỗi đó ảnh hưởng**, gộp vào file lượt (`--gop`), rồi đi tiếp
   5b–5d như thường. Không chạy lại cả bộ.
5. Không sửa được ngay (cần dữ liệu ngoài, đổi kiến trúc) → vẫn đo tay case đó theo 5b để ra
   PASS/FAIL, ghi lỗi tool vào câu báo kèm hướng sửa.
6. Câu báo cuối liệt kê: lỗi tool đã gặp, đã sửa ở file nào, test nào, case nào chạy lại.

## 6. Xuất report

Luôn truyền `--report <repo>/out/run-<pkg>-<serial>-<hhmmss>.html` khi chạy `--case`: trang
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
cd <repo> && <bin>/rcr-artifact --package <pkg> --url <link> --generated-at <generated_at cua luot>
cd <repo> && <bin>/rcr-artifact --package <pkg>          # in link da luu cua luot truoc cua app nay
```

Lệnh ghi link tự báo Discord "Report đã publish". Lần publish **đầu** của một lượt thì thêm
`--app "<tên app>" --version <ver> --cases "<n (m nhóm)>" --result "<x PASS · y FAIL · …>"
--bugs "<bug đã xác nhận>" --tool-minutes <phút máy chạy>` để ghi một dòng vào
`docs/usage-log.md`; republish đè cùng link thì **bỏ `--app`** kẻo ghi trùng dòng.

URL artifact **cố định**: republish cùng file thì giữ nguyên link. Nên lượt sau cứ đọc
link cũ **của đúng app đó** (`--package`) rồi republish đè, người dùng không phải đổi link đang mở.
Luôn truyền `--package`: hai lượt song song trên hai máy mà dùng chung một link thì lượt
sau đè report của lượt trước. Bắt buộc kèm
`--generated-at`: thiếu nó thì không phân biệt được link đang trỏ tới lượt vừa chạy hay
một lượt cũ — gửi nhầm báo cáo cũ cho team là sai một cách im lặng.

## 7. Báo lại

Nói rõ: app + máy đã chạy, số key remote config và số key bị mirror, số case
chạy được / cần người, verdict cuối của từng case (sau mục 5b) kèm số đo chính, việc
cần báo dev/PO, và trạng thái máy (đã restore chưa, có `pm clear` không). **Không
liệt kê "bạn tự kiểm tiếp" cho dòng mà mục 5b làm được.** Chỉ nêu phần thật sự ngoài
tầm (console PO, điều kiện đã thử mà không tạo được) và nói đã thử gì.

Mở đầu câu báo bằng kết quả check ID ads (mục 3c): khớp/tổng, các vị trí lệch
(confirmed / disputed / unresolved) và link trang audit — hoặc lý do chưa check được.

**Đưa link artifact ngay trong câu trả lời**, đừng bắt người dùng đi tìm. Report
local (`<repo>/out/…html`) vẫn mở được bằng nháy đôi nếu publish hỏng.

## 7b. Có FAIL → user review, rồi log Jira

User chốt 28/10/2026: *"auto test xong có bug thì để tôi review lại xem nó có phải bug không,
sau đó dùng skill log bug để tự log bug lên jira"*.

1. Chỉ đưa vào danh sách những FAIL **đã rà xong theo 5d**. Mỗi bug ghi: mã case, dòng Expected,
   thực tế đo được (số đo, unit, log), bước tái hiện, ảnh/video của lượt hợp lệ, link report.
2. **Lượt chạy trong terminal (có người):** hỏi bằng `AskUserQuestion` (multiSelect, mỗi bug một
   lựa chọn). **Chưa có câu trả lời thì không log**: Jira là chỗ cả team nhìn, log nhầm thì dev mất công.
   Bug được chọn → gọi skill `anthropic-skills:jira-log-bug` mode TEXT (`bug_ad`), mỗi bug một lần,
   đủ thông tin ở bước 1 + app, version, SDK FO, máy. Báo lại link từng issue.
   **Mỗi issue phải có label `auto-qa` và một dòng marker riêng ở CUỐI description**, đúng mẫu `AUTOQA case=<mã case> ban=<debug|release> pkg=<package>` (mã case: `<tab>#<số>` / TC ID của bộ TC, hoặc mã dòng checklist Next-Gen như `EV-07`; `ban` = loại bản đã test; `pkg` = package đã test). Bot Discord tìm bug Reviewing theo label này và chạy lại đúng case ghi trong marker, nên sai/thiếu marker là bug bị bỏ qua ("cần verify tay").
   Log xong (có ít nhất một issue tạo được) → **báo dev check bug** bằng một tin Discord:
   `<bin>/rcr-notify --kind bug --title "Nhờ dev check bug · bản build <MÃ>---<Tên app> v<versionName> (<versionCode>)" --line "<KEY-1> — <tóm tắt bug> · <mức độ> · <link issue>" [--line ...]`
   — mỗi issue một `--line`, bỏ bug không tạo được issue. Bản build ghi **đúng mẫu tin build của dev**
   (`AIP882---AI-Video v4.3.0 (40)`); versionName/versionCode lấy từ `dumpsys package <pkg>` của bản đã test.
3. **Lượt do bot Discord gọi (headless, không có người):** KHÔNG hỏi, KHÔNG log Jira. Chỉ đưa danh
   sách bug vào trường `bugs` của dòng `KET_QUA` (mẫu nằm trong prompt của bot). Bot đăng menu tick
   lên kênh QA; QA bấm **Log Jira** thì bot chạy lượt riêng (`src/rcr/bot_log_jira.py`): project key =
   mã app trong tin build, reviewer = `DISCORD_JIRA_REVIEWER` trong `bot.env`. Log xong bot tự trả
   lời ngay dưới tin build của dev ("Nhờ dev check bug": project, link từng issue — link report chỉ báo ở kênh QA).
4. Không có FAIL thì bỏ qua mục này.

**Dừng ở đây. Không `git add`, không `git commit`, không `git push`** khi user chưa bảo.
Code đã sửa theo mục 5e để nguyên trong working tree, liệt kê trong câu báo; user bảo commit
thì push lên mọi remote mà máy có quyền ghi (`git remote -v`, bỏ remote có push URL `no_push`);
remote nào không push được thì nói rõ trong câu báo để push từ máy khác.
