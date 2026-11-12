---
description: Đổi giá trị Firebase Remote Config của app Android theo file testcase, hoặc tự chấm checklist SDK Next-Gen khi app dùng SDK 3.7.0 / 3.7.1 / 3.7.2, trên máy thật
argument-hint: "<package> [mục 1|2|3|4|all — chỉ khi app SDK 3.7.0 / 3.7.1 / 3.7.2: tự chấm checklist Next-Gen] [--tc <link sheet | bo-tc.xlsx> [--tab <X.Y.Z>] [--sdk <X.Y.Z>] [--case <key,key>]] [--set key=value] [--report <file.html>] [--app-label '<ten app> <version>'] [--serial <serial>] [--next-gen] [--fresh] [--full-walk|--no-walk|--no-actions] [--keep|--restore]"
---

Chạy `rcr-check` một lượt: đọc baseline remote config, nạp file testcase, đặt
config của một case rồi xác nhận nó sống qua lần mở app. Tham số: $ARGUMENTS

File này là **luồng chính + luật đang áp dụng**. Chi tiết nằm ở `docs/rc-check/`, đọc đúng lúc ghi bên dưới:

| File | Đọc khi |
|---|---|
| `docs/rc-check/luat-qa-da-chot.md` | **luôn đọc trước khi chấm / báo bug** (cách hiểu TC QA đã chốt, kiến thức nền SDK) |
| `docs/rc-check/kha-nang-lai-va-cham.md` | bước Action lạ, tool dừng ở bước lái, cần biết một dòng chấm bằng gì |
| `docs/rc-check/doc-ket-qua-va-precondition.md` | case BLOCKED / KEY_NOT_USED / needs_human, precondition môi trường, nghi tool chấm sai |
| `docs/rc-check/ky-thuat-do-tay.md` | còn dòng phải tự đo trên máy (mục 5b) |

Thêm luật mới: **sửa đúng chỗ luật cũ**, đừng viết chồng đoạn mới lên đoạn cũ. Chạy `pytest tests/test_workflow_rc_check.py`
sau khi sửa (kiểm đường dẫn, lệnh `rcr-*`, độ dài file này).

## 0. Tìm repo trước đã

Command chạy được từ thư mục bất kỳ — **đừng giả định CWD**. Lấy cái đầu tiên có `src/rcr/cli_check.py`:

1. `git rev-parse --show-toplevel` (nếu CWD đang nằm trong chính repo này)
2. biến môi trường `$RC_RUNNER_REPO`
3. `~/projects/check_remote_config`
4. `~/Desktop/check_remote_config`
5. `~/check_remote_config`

Nhiều bản clone thì cái đứng trước thắng dù cũ hơn: đặt `RC_RUNNER_REPO` trỏ vào bản đang dùng, `git log -1` bản tìm
được trước khi chạy. Repo có **hai remote** (DuyenLTA, LuuThiAnDuyen), tên remote mỗi máy một kiểu — đọc `git remote -v`.
Không thấy repo thì dừng, nói rõ đã tìm ở đâu. Gọi đường dẫn tìm được là `<repo>`.

`<bin>` = `<repo>/.venv/bin` (macOS/Linux) hoặc `<repo>/.venv/Scripts` (**Windows**, file `rcr-check.exe`). Luôn gọi
`<bin>/rcr-check` bằng **đường dẫn tuyệt đối**. `command not found` → `cd <repo> && <bin>/python -m pip install -e ".[dev]"`.

## 0b. Chọn nhánh theo bản SDK (tự chọn, không hỏi)

Preflight (3b) mở app, đọc `VslTemplate4FirstOpenSDK: Using version X` của pid app, in dòng **`Bản SDK FO`**.

- **3.7.0 / 3.7.1** (kể cả `-alphaNN`) → `Nhanh: checklist Next-Gen` (`"nhanh": "nextgen"`). **Không chạy mục 4–7**: đọc
  toàn bộ `<repo>/sdk-check/WORKFLOW.md` và làm theo (checklist ở `<repo>/sdk-check/references/`, report Khớp/Sai).
- **`$ARGUMENTS` có `--next-gen`** (bot truyền khi tin build ghi next-gen) → truyền `--next-gen` vào preflight: nhánh
  **luôn** Next-Gen, bất kể số SDK.
- **3.7.2** (user chốt 11/11/2026) → chạy **cả hai**: bộ TC **tab `3.6.1`** (`--tab 3.6.1`, mục 4–7) rồi checklist
  Next-Gen (`sdk-check/WORKFLOW.md`). Check ID ads (3c) một lần trước cả hai. Preflight in `Nhanh: CA HAI` và tool tự
  chọn tab 3.6.1 (không lấy tab gần nhất 3.6.2); **vẫn chạy checklist** sau bộ TC và đo tay hết dòng `DO_TAY` của checklist. Report: `KET_QUA.link` = report
  bộ TC; link report checklist ghi trong `tom_tat` và câu báo. Bug của cả hai phần gom chung trường `bugs`.
- **Bản khác** (3.5.x, 3.6.x — 3.6.1 đã revert next-gen —, 3.8.x…) → nhánh bộ TC. Bộ TC chưa có tab của bản thì
  tool chấm base + delta tới tab gần nhất, ghi chú phần chưa có TC. User truyền `--tc` riêng thì theo `--tc`.
- **`--sdk X.Y.Z`** (bot truyền số trong tin build) → truyền vào preflight và mọi lệnh sau: **số trong tin build quyết
  nhánh + tab, không theo log app**. Lệch (`SDK tin build vs log app` = `CHU Y`) → vẫn theo tin build, ghi dòng lệch lên
  đầu câu báo (AIP882 4.3.0: theo log app là chấm sai cả lượt).
- Không đọc được bản (`Bản SDK FO` = `CHU Y`) → hỏi user, chạy lại preflight với `--sdk`.
- Chạy bộ TC mặc định trên app 3.7.0 / 3.7.1 thì `rcr-check` dừng kèm lỗi (bộ chung không có tab Next-Gen).

## 0c. Máy test AdMob — áp dụng cả hai nhánh

**Mọi máy QA cắm vào đều là máy test AdMob** (user chốt 29/10/2026). `ad_click` (trong case, trong capture 3c, hay SDK tự
bắn) **không** phải lý do dừng chờ người: ghi vào report rồi chạy tiếp. Được bấm quảng cáo khi case / dòng checklist cần đo.
Đóng ad thì chờ hết đếm ngược (tối đa ~20s), không bấm sớm.

## 1. Tool làm được tới đâu — nói trước

Đặt giá trị RC **không cần quyền admin Firebase** trên đúng một máy, đọc lại xem giá trị có sống qua lần mở app; lái app
theo bước Action của case; chấm PASS/FAIL từng dòng Expected bằng log, cây UI, ảnh. Danh sách câu lái được và cách chấm từng
loại dòng: `docs/rc-check/kha-nang-lai-va-cham.md`.

- Câu Action không hiểu, hoặc **nhiều node cùng khớp** → dừng kèm lý do, **không tap bừa** (tap sai = bấm quảng cáo / mua hàng).
- **Không gắn cứng theo một app**: app mới đặt tên id lạ → thêm vào `src/rcr/data/ui_names.yaml`, không sửa code.
- Dòng phải nhìn mắt ra `NOT_VERIFIABLE` — **không đoán thành PASS**; Claude tự đo tiếp theo 5b.
- **Verdict case = dòng xấu nhất trong MỌI dòng, trừ dòng của PO.** Dòng chưa chấm cũng kéo case xuống: case PASS nghĩa
  là mọi dòng đã được chấm.

## 2. Package và đường đổi RC

**Chỉ nhận package id** (`com.abc.xyz`), không nhận tên app (khớp mờ là patch nhầm app). Không có → báo rồi **hỏi**:
`<bin>/rcr-notify --kind stop --title "Thiếu / sai package" --line="<$ARGUMENTS>" --action "Gửi package id dạng com.abc.xyz"`

- Bản **debuggable** (`run-as`) hoặc máy **root** (`su`) → patch file RC trên máy.
- **Bản release (mặc định của bot)** → đổi RC trên Firebase, **chỉ** qua giá trị của điều kiện `testvsl` (cần
  `firebase login` trên máy chạy lượt, `testvsl` đã có và đứng thứ 1). Không đụng default, condition / tham số của người khác.

**Không xin dev bản debuggable** cho bản release (user chốt). Preflight `LOI` ở "Vào được dữ liệu app" → in nguyên văn kèm
việc cần làm: chưa / hết hạn đăng nhập → `firebase login` (hoặc `--reauth`); thiếu `testvsl` → nhắc QA tạo. Không gợi ý sửa APK.
Cần biết APK là bản nào trước khi cài: `aapt dump badging <file.apk> | grep application-debuggable`.

## 3. Chọn máy

`adb devices -l`:
- 0 máy → **dừng**: `<bin>/rcr-notify --kind stop --title "Không có máy Android" --line "<package>" --action "Cắm máy, bật USB debugging, bấm Allow"`
- 1 máy → không truyền `--serial`
- nhiều máy → `--serial` từ `$ARGUMENTS`; không có thì **hỏi** (patch nhầm máy người khác là hỏng data của họ):
  `<bin>/rcr-notify --kind stop --title "Nhiều máy, cần chọn" --line "<danh sách serial>" --action "Chọn serial máy cần chạy"`
- máy `unauthorized` không tính
- có `--serial` (bot luôn truyền) → **mọi** lệnh `rcr-check` / `rcr-sdk-check` / `rcr-cai-build` / `adb` trong lượt đều
  kèm đúng serial đó. Bot chạy song song nhiều máy: sót một lệnh là đụng máy của lượt khác.

**Máy phải mở khoá** (khoá thì không mở được activity, nhìn y hệt app hỏng):
`<bin>/rcr-notify --kind stop --title "Máy đang khoá màn hình" --line "<serial>" --action "Mở khoá máy rồi chạy lại"`

## 3b. Preflight — luôn làm

```
cd <repo> && <bin>/rcr-check --package <pkg> [--serial <S>] --preflight [--next-gen] [--sdk X.Y.Z]
```

~20 giây: máy, màn hình không khoá, app đã cài, **đổi được RC** (debuggable / root, hoặc release qua `testvsl`), ads dùng
ID thật, tải được sheet TC, sheet ID ads có tab của package, RAM máy tính, Private DNS không còn sót của lượt trước, không
còn snapshot `--keep` chưa `--restore`, và **plan tuần**.

- **Exit 1 = có dòng `LOI` → dừng**, in nguyên bảng kèm việc cần làm, không chạy thử:
  `<bin>/rcr-notify --kind stop --title "Chưa đủ điều kiện chạy" --line "<dòng LOI>" --action "<việc cần làm>"`
- **`Ads dùng ID thật` = `CHU Y`** (build request unit test Google `ca-app-pub-3940256099942544/…`): **không dừng, chạy
  tiếp** (user chốt 09/11/2026), không xin dev bản khác. Câu báo cuối mở đầu bằng các unit ID test để dev xác nhận. Ở 5c,
  dòng ads của vị trí dùng ID test **không PASS chỉ vì có request** (mọi vị trí chung một unit) — đối chiếu log màn + ảnh;
  không quy được về vị trí → `--cham-tay ... --ket BLOCKED --ly-do "build dùng ID test, không quy được ad về vị trí"`.
- `CHU Y` RAM < 4 GB: không chặn, nói trước (lượt dài có thể bị tắt giữa chừng).
- **`Plan tuần` = `LOI`** (bản SDK khác dòng của app trong tab tuần này của plan QA, biến `RC_PLAN_TUAN_SHEET`) → **dừng
  ngay**, không check ID ads, không chạy case (user chốt 30/10/2026). Gửi `rcr-notify --kind stop` với nguyên dòng; lượt
  bot thì `KET_QUA.trang_thai` = `DUNG`, `tom_tat` mở đầu "Build khác plan tuần: …" (đúng chữ này: bot dựa vào nó để
  hiện nút **Chạy bỏ qua plan**). Plan chưa có tab / không ghi SDK / không tải được → `CHU Y`, chạy tiếp.
- **`$ARGUMENTS` có `--bo-qua-plan`** (QA bấm "Chạy bỏ qua plan" — dev chỉ nâng / hạ version, bên trong giống nhau,
  user chốt 09/11/2026) → truyền `--bo-qua-plan` vào preflight: dòng `Plan tuần` thành `CHU Y`, **chạy hết như thường**
  (check ID ads, case / checklist). Câu báo mở đầu: "Chạy bỏ qua plan tuần theo QA: <nguyên dòng lệch>".

## 3c. Check ID ads (audit-fanout) — sau preflight, trước khi chạy case

Áp dụng **cả hai nhánh**. Bỏ qua khi lượt không chạy case: kiểu (a)/(b) ở mục 4, `--set` đứng riêng, `--restore`,
`--tiep`, `--cham-tay`, `--gop` chỉ dựng lại report; và lượt chỉ chạy tab tính năng (rating / widget / daily checkin).

1. Repo audit: `$AD_AUDIT_REPO`, rồi `~/android-ad-audit` — cái có `tools/ad-checklist-diff/audit_runner.py`. Không thấy
   → ghi "chưa check ID ads (không thấy repo audit)" vào câu báo, chạy tiếp.
2. Đọc **toàn bộ** `<audit-repo>/.claude/commands/audit-fanout.md` và làm đúng nó với `<package> --serial <serial>`
   (luôn kèm serial). Không tham số phụ (`--apk`/`--skip`/`--force`). Capture `pm clear` app — nói trong câu báo.
   **Audit xong mới chạy mục 4** (cùng lái một máy).
3. Kết quả — **không trường hợp nào dừng rc-check** (user đổi 28/10/2026: "lệch thì không sao, cứ chạy tiếp"):
   - `clean` → chạy tiếp.
   - Lệch ID (dòng `Lệch` / `confirmed` / `disputed` / `unresolved`) → chạy tiếp; ở 5c/5d dòng ads của vị trí lệch đối
     chiếu theo **unit thật trong log**, không theo sheet. Câu báo liệt kê đủ vị trí lệch (vị trí · ID sheet → ID build),
     phát biểu "build lệch sheet, cần dev / ads-team xác nhận".
   - 2 tab cùng package → lượt có người hỏi user theo audit-fanout; lượt bot ghi vào `tom_tat`, chạy tiếp.
   - workflow lỗi → ghi lý do vào câu báo.
4. Audit tự publish + tự báo Discord — **đừng báo thêm**. Giữ link trang audit cho câu báo cuối. **Không commit** bên repo audit.

## 4. Chạy

**User chỉ cần gửi package** (chốt 06/10/2026). Còn lại tự lấy:

| Cần gì | Lấy ở đâu |
|---|---|
| Bản SDK FO | log app (lọc PID) → tab số lớn nhất ≤ bản đó. **Đừng đoán từ versionName** (Piclux 2.8.0 nhúng SDK 3.5.4) |
| Bộ TC | sheet TC `https://docs.google.com/spreadsheets/d/1sNFXM7oGzx_addpimZL7RYk2rXpRs_We6YUHpdtWSqU/edit` — tool tải bản mới nhất **mỗi lệnh** |
| ID ads từng vị trí | sheet "Check thông số KT" `https://docs.google.com/spreadsheets/d/14XivZl9VPAnyf8hYICgRh-TOUmkGTZDCqoyWmPM57hM/edit` — tool tải mỗi lượt, chọn tab theo dòng `Package name` |
| Version app | `dumpsys package <pkg> \| grep versionName` → `--app-label "<tên> <version>"` |
| User state / test data | cột `User State` (new = `pm clear`, old = đã vào Home) và `Test Data` của TC |

Chỉ hỏi khi: log không in bản SDK, sheet ID không có tab của package, hoặc nhiều máy.

**Tab tính năng test từ Home** (user chốt 12/11/2026): rating / widget / daily checkin / IAA / gen ngầm… mỗi case tool tự lái qua FO (splash, ngôn ngữ, onboarding, paywall) **vào tới Home** rồi mới làm theo Action — chỉ tab SDK FO (tên là số phiên bản) mới test ở tutorial. Case nối chuỗi giữ màn của case trước. Vắng event mà tool chưa lái tới chỗ bắn event → đo tay, **không FAIL**.

**Check gì cũng tải lại sheet liên quan trước** (user chốt 12/11/2026, QA sửa sheet liên tục): bộ TC (cả tab SDK,
tab tính năng, `--tc iaa` / `--tc gen-ngam`), sheet Check thông số KT (ID ads, mục 3 IAA), plan tuần, sheet TC sub,
tab "Tổng hợp SDK x" — tool tải bản mới nhất **mỗi lệnh** (kể cả `--gop` / `--tiep`), không dùng bản `out/` có sẵn,
không dựa vào điều Claude nhớ từ lượt trước. Tải hỏng thì dừng báo lỗi, không chấm theo bản cũ. Claude đọc sheet
(mô tả, kỳ vọng, cách hiểu) cũng đọc bản vừa tải của lượt này.

**Bộ TC lấy từ Google Sheet, KHÔNG tìm file trong Downloads.** User đưa link / `.xlsx` khác thì dùng đúng cái đó. Tải
không được → dừng, **đừng lùi về file cũ**:
`<bin>/rcr-notify --kind stop --title "Không tải được sheet TC" --line "<link sheet>" --action "Chia sẻ sheet hoặc gửi file .xlsx"`

Tab: mặc định **không truyền `--tab`** (tool tự chọn đúng một tab số). User nêu tên thì dịch sang `--tab`: `sdk 3.4.0` →
`--tab 3.4.0`, `sdk rating` / `sdk widget` / `sdk daily checkin` → `--tab rating` / `widget` / `"daily checkin"`. Ba SDK
riêng này không thuộc FO — user không nhắc thì **đừng tự chạy**. Lượt chỉ chạy tab tính năng (user nêu, hoặc bot gọi qua
`/check` ô `tinh_nang`, user chốt 11/11/2026): **chọn tab nào chạy tab đó** — không FO, không checklist Next-Gen, không
`--sdk`, **bỏ 3c**, preflight kèm `--bo-qua-plan`; nhiều tab thì mỗi tab một lệnh rồi `--gop` thành một report.

Hai bộ tính năng **không nằm trong sheet TC chung** (user chốt 12/11/2026) — truyền `--tc <tên>` thay cho link, tool
tải lại sheet gốc mỗi lệnh (cả `--gop`/`--tiep`) rồi dựng bộ case, phần còn lại chạy như bộ TC thường:
- `--tc iaa`: mục **"3. ID ads inapp"** của tab app (dòng `Package name`) trong sheet "Check thông số KT" — QA dán kịch bản
  IAA vào đó. Mỗi vị trí (cặp high + thường) ra 4 case `IAA-<vị trí>-01..04`: bật cả hai / chỉ thường / chỉ high / tắt
  remote. Expected của case `-01` = **nguyên văn từng dòng cột Ad description** (không thêm câu tự viết) + dòng ID →
  phần tool không tự chấm được thì chấm tay theo 5b. Mục 3 trống → tool dừng, báo QA dán kịch bản.
  **Chấm IAA đúng chính xác từng câu cột Ad description** (user chốt 12/11/2026), bằng `logcat -v epoch`, không chấm bằng mắt: load/preload
  đúng màn + đúng thời điểm (giờ request so với lúc vào màn / bấm nút), show đúng màn, reload đúng chu kỳ (≥ 3 lần liên
  tiếp, lệch ≤ 1s) và đúng sự kiện (back về Home, chọn lý do, hide app…), giới hạn số lần (1 ad/session, `*_fail_time`),
  tắt remote → 0 request của vị trí. Mỗi vế của câu mô tả là một kết luận riêng; vế nào không đo được thì không PASS.
- `--tc gen-ngam`: tab "TC Gen ngầm" (khuôn bộ TC, lượt E2E "Tiếp nối" → luôn `--chuoi`) của sheet
  `https://docs.google.com/spreadsheets/d/1FORGiI5X_N6HTmYyFdSiXCsAu7q91vTd59BfoGULT8c/edit`. Đổi sheet: `RC_TC_GEN_NGAM`.
Bot gọi qua `/check` ô `tinh_nang` = `iaa` / `gen ngầm`.

```
# a. chi doc baseline
cd <repo> && <bin>/rcr-check --package <pkg> [--serial <S>]
# b. nap bo TC - xem case nao tool chay duoc
cd <repo> && <bin>/rcr-check --package <pkg> --tc "<link sheet TC>"
# c. chay case, xuat report
cd <repo> && <bin>/rcr-check --package <pkg> --tc "<link>" --case 3.4.0#SDK340-SPL-001,3.4.0#SDK340-SPL-003 \
  --chuoi --report out/run-<pkg>-<serial>-<hhmmss>.html --app-label "<tên> <ver>"
# dat mot key
cd <repo> && <bin>/rcr-check --package <pkg> --set splash_banner_change=false
```

- Case định danh **`<tab>#<số>`** hoặc `<tab>#<TC ID>` (`3.5.0#12`, `3.4.0#SDK340-SPL-001`); TC ID không trùng thì truyền
  thẳng (`SDK350-OB3X-013`). Mơ hồ thì tool dừng và liệt kê — **đừng chọn bừa**.
- Chạy cả tab: lấy danh sách case chạy được từ kiểu (b), truyền hết vào `--case`. ~1 phút/case → (c) luôn
  `run_in_background`, ghi stdout/stderr vào scratchpad; chỉ báo khi có FAIL, case hỏng, hoặc xong.
- stdout là **đúng một dòng JSON** (`baseline`, `tc`, `run`); tiến độ ra stderr.
- **Đừng truyền `--khong-claude`** (dành cho `chay-khong-claude.bat`, lượt không agent).
- Kết quả ghi đĩa **sau mỗi case** vào file lượt (`out/run-x.html` → `out/run-x.luot.json`). Lượt bị tắt giữa chừng →
  **đừng chạy lại từ đầu**: `cd <repo> && <bin>/rcr-check --package <pkg> --tiep out/run-x.luot.json`.
- **`ad_click` không dừng lượt** (0c): `run_batch` tự chạy lại case bị click, report giữ số click; vẫn còn click thì case
  BLOCKED kèm số click, lượt chạy tiếp. Không gửi `rcr-notify --kind stop` vì `ad_click`.

| Flag | Khi nào |
|---|---|
| `--app-label "Piclux 2.8.0"` | tên + version **APP**, luôn truyền khi có `--report`. Đừng nhét version SDK |
| `--chuoi` | **luôn truyền khi chạy cả bộ TC**: case "Tiếp nối…" chạy tiếp trên app đang mở; FAIL / lệch log thì tự chạy riêng từ đầu |
| `--fresh` | ép app về trạng thái chưa từng mở |
| `--sdk X.Y.Z` | khai thẳng bản SDK FO (máy không ra log, workbook một sheet, hoặc bot truyền theo tin build) |
| `--full-walk` / `--no-walk` / `--no-actions` | đi hết luồng FO / không lái FO / chỉ đặt config. Mặc định dừng ở màn sâu nhất case đụng tới |
| `--no-dex-check` | bỏ soi key trong DEX — có thể ra PASS giả, chỉ dùng khi biết chắc app đọc key |
| `--adb <path>` / `--out-dir <dir>` | adb ngoài PATH / nơi lưu snapshot (mặc định `<repo>/out`) |

**Mặc định tool trả config về nguyên trạng sau khi verify.** Muốn giữ để tự mở app xem thì `--keep` (tool lưu snapshot
vào `out/`); xong thì trả bằng `cd <repo> && <bin>/rcr-check --package <pkg> [--serial <S>] --restore`. **Đừng patch tay
giá trị cũ** (lượt sau đọc baseline bẩn). Còn patch trên máy thì nhắc user restore.

## 5. Đọc kết quả

`run.verdict` (chi tiết + precondition + bảng `tc.cases`: `docs/rc-check/doc-ket-qua-va-precondition.md`):

- `PASS` — khớp Expected. **Ad không fill mà có request ĐÚNG unit của vị trí cũng là PASS**; không request nào → FAIL
- `FAIL` — lệch Expected, kèm số đo thật
- `NEEDS_HUMAN` / `NOT_VERIFIABLE` — chưa kết luận gì về app, **không trả cho user** → mục 5b. Dòng console AdMob/Firebase
  là của **PO** (đếm riêng `po`)
- `CONFIG_OK` / `BLOCKED` — case không Expected; hoặc precondition chưa thành hiện thực; hoặc điều kiện "Nếu X" không xảy ra
- `KEY_NOT_USED` — app không đọc key đó, chấm tiếp là PASS giả

`run.reset` = `clear` (`pm clear`) → **nói user biết** mất login/data app. **Ngắt mạng không phải giả lập no-fill.**

## 5b. Còn NEEDS_HUMAN / NOT_VERIFIABLE → tự làm trên máy, KHÔNG hỏi, KHÔNG giao lại

User nhắc ba lần (28/09, 03/10, 06/10/2026). Lượt **chưa xong** khi còn dòng này (trừ dòng PO): không báo, không publish,
không viết "bạn tự mở app xem".

1. Đặt config của case: `--set '<key>=<value>' --keep` (cùng reset như tool). **Giữa hai lượt `--keep` phải `--restore`**.
2. Tự lái bằng adb theo đúng câu Action. **Không gửi phím / tap nào khi `AdActivity` đang hiện ad thật** (kể cả BACK).
3. Lấy bằng chứng theo loại dòng — `docs/rc-check/ky-thuat-do-tay.md`.
4. Chấm từng dòng với **số đo thật** làm lý do. Report gửi đi không còn NEEDS_HUMAN / NOT_VERIFIABLE, chỉ PASS / FAIL —
   **trừ** precondition thật sự không tạo được: `BLOCKED` theo 5d2. Điều kiện tạo được mà chưa đạt thì tự ép, tự chạy lại.
5. Trả máy sạch: `--restore`, đọc lại key đã đổi so với giá trị gốc; lệch thì `pm clear` + mở app cho fetch lại. Mạng đã
   ngắt thì bật lại, chờ ping thông.
6. Ghi từng dòng vào file lượt bằng lệnh, **đừng sửa tay JSON**:
   ```
   cd <repo> && <bin>/rcr-check --package <pkg> --cham-tay out/run-x.luot.json \
     --case 3.4.0#SDK340-UI-001 --dong 1,4 --ket PASS --ly-do "<số đo + cách đo>" \
     --anh out/manual/A_ob2.png,out/manual/A_ob4.png > <scratchpad>/cham.json
   ```
   - **Luôn kèm `--anh`** ảnh đúng màn của case (dòng chấm theo log không cần). Report đưa kết luận đo tay lên đầu.
   - **Không nối qua `| head`/`| tail`** (pipe đóng sớm, mất lần chấm) — đẩy ra file rồi đọc.
   - Hạ PASS giả: `--ket NEEDS_HUMAN`. Đo tay **đã tạo được** precondition mà tool không tạo được: thêm
     `--dieu-kien-dat "<cách tạo>"`.
   - User báo **đã sửa TC** → tải lại sheet, chấm lại **và** sửa câu kỳ vọng `lines[].e` theo TC mới, publish vào link cũ,
     báo qa-auto — không hỏi.

## 5c. Rà PASS giả TRƯỚC khi báo — bắt buộc

Đọc `reason` của **từng dòng PASS** (`lines[].r`):

1. **Dòng ads phải đúng unit của vị trí** (tra sheet "Check thông số KT"; vị trí lệch ở 3c thì theo unit thật trong log).
   Unit của vị trí khác = PASS giả. Log `ID ads tung vi tri: … 0 vị trí` / "không có tab nào ghi package" → báo user bổ
   sung tab, đừng chạy như thể có ID. `src/rcr/data/ad_units.yaml` chỉ là dự phòng.
2. **Không fill = PASS chỉ khi có request đúng unit**, không phải "có ad nào đó". Thứ tự preload / alternate cũng vậy.
3. Build dùng ID test (3b) → dòng ads của vị trí đó không PASS chỉ nhờ request.
4. **Câu khẳng định có vế phủ định** (`X hiển thị NGAY (không có số đếm ngược)`): PASS vì "không thấy X" là sai.
5. **PASS nhờ luật** (TBD ghi nhận thực tế, `[Assume]`) — nêu riêng để PO chốt.
6. Soi được **offline** từ `cases[].ads` (`u`, `req`, `load`, `show`, `keys`) — chỉ chạy lại case thật sự PASS giả.

**Chạy lại chỉ case chưa PASS / PASS giả**, gộp bằng `--gop` (lặp được, file sau thắng; không cần máy khi chỉ dựng report):
```
cd <repo> && <bin>/rcr-check --package <pkg> --tc "<link>" --case <key,key> --gop out/run-x.luot.json \
  --report out/run-x-gop.html --app-label "<tên> <ver>"
```
Đừng tự viết Python gộp record. Publish đè **cùng link**.

## 5d. Rà FAIL giả TRƯỚC khi báo — bắt buộc

1. **FAIL chạy một lần là đủ** (chốt 24/10/2026) — không lặp lượt xác nhận; soát kỹ bằng chứng của lượt đó.
2. **Config còn sống tới cuối lượt**: fetch thật (`Fetch firebase successfully in` > ~400ms) đè patch → tool BLOCKED + chạy
   lại. Đo tay thì luôn ghi `logcat -v epoch`, kiểm dòng fetch trước.
3. **Đối chiếu ảnh của chính tool**: ảnh thấy thứ dòng FAIL bảo "không thấy" → tool nhìn sai.
4. **Nguyên nhân giải thích được bằng số đo** của lượt có config đúng; một lượt tay ngược với tool chưa đủ kết luận bug.
5. Thao tác tay canh theo đồng hồ **máy**; chỉ tap khi đã thấy node.
6. **Bằng chứng trên report cùng lượt với kết luận**; lượt sai điều kiện ghi "không dùng làm bằng chứng".
7. Đối chiếu `docs/rc-check/luat-qa-da-chot.md`: dòng QA đã chốt là đúng thì không phải bug.

## 5d2. Luật QA đã chốt

- **Precondition không tạo được thì BLOCKED, cấm đo thay** (chốt 03/11/2026: "đừng có làm giả"): thiếu máy OPPO, kho
  không trả native full → `--cham-tay ... --ket BLOCKED --ly-do "<vì sao>"`. **Ad về muộn tạo được trên máy Android 13+**:
  tool chặn/trả mạng app theo màn bằng tường lửa có sẵn (không cần root). Máy ≤ 12 → BLOCKED "cần Android 13+", nhắn
  qa-auto đổi máy; proxy HTTP không dùng được (GMA đi QUIC). Throttle băng thông không tạo được; chi tiết ở
  `docs/rc-check/doc-ket-qua-va-precondition.md`. Rà **mọi** dòng `cham_tay` trước khi
  báo. Case cần ad fill mà kho không fill → BLOCKED, báo tên case để user xoá khỏi sheet; **không cố ép fill**.
- **Cách hiểu TC (3.6.1, 3.5.4, kiến thức nền SDK)** → `docs/rc-check/luat-qa-da-chot.md`, đọc trước khi chấm.
- **Mỗi lệnh đều tải lại sheet TC** (kể cả `--gop`/`--tiep`). `CANH BAO: sheet TC da doi` → so `lines[].e` với kỳ vọng mới
  (`tc_catalog.read_tab_ten`): case đổi/mới chạy lại `--gop` + đo tay; case đã xoá bỏ khỏi file lượt (`luot_file.ghi` +
  `run_batch.ghi_report`). Trước `--cham-tay` / publish cũng tải lại tab TC.
- `CANH BAO: tab Tong hop SDK moi/doi` → cập nhật kiến thức nền theo file trên.

## 5e. Gặp lỗi của tool giữa lượt → Claude tự sửa, KHÔNG giao lại user

1. Phân biệt: **bug app** (báo dev), **điều kiện máy/tài khoản** (tự xử), hay **lỗi tool** (crash, lái sai màn, nhận nhầm
   node, regex log không khớp, PASS/FAIL giả do cách chấm). Chỉ loại cuối mới sửa code.
2. Id lạ → `src/rcr/data/ui_names.yaml`. Lỗi code → sửa gốc trong `src/rcr/` (hoặc `sdk-check/scripts/`), thêm test tái
   hiện, chạy **cả bộ** `<bin>/python -m pytest -q` tới xanh.
3. Chạy lại **chỉ case bị ảnh hưởng**, `--gop`, rồi đi tiếp 5b–5d.
4. Không sửa ngay được → đo tay case đó theo 5b, ghi lỗi tool + hướng sửa vào câu báo.
5. Câu báo liệt kê: lỗi tool đã gặp, sửa ở file nào, test nào, case nào chạy lại.

## 6. Xuất report

`--report <repo>/out/run-<pkg>-<serial>-<hhmmss>.html` khi chạy `--case`. Bố cục tester đã chốt — **đừng đổi**: header
(eyebrow · H1 · meta) → 4 thẻ đếm PASS/FAIL/BLOCKED/N-A (bấm lọc) → khối "cần xử lý" → thanh lọc → case gập/mở nhóm theo
Feature, mỗi dòng Expected mang nhãn + lý do riêng. Chỉ **4 nhãn** (`report_row.nhan_cua`); mã thao tác nội bộ (`noop`,
`goto`, `net`) không lộ ra.

Lượt **đo được thật** → publish thành artifact và **chỉ đưa link**, **không tự mở trang**. Report mà mọi case
`NEEDS_HUMAN` thì không publish — làm 5b trước.

Publish xong ghi link, `generated_at` lấy từ **chính dòng JSON của lượt vừa chạy**:
```
cd <repo> && <bin>/rcr-artifact --package <pkg> --url <link> --generated-at <generated_at>
cd <repo> && <bin>/rcr-artifact --package <pkg>          # link da luu cua app nay
```
Lệnh tự báo Discord "Report đã publish". Lần publish **đầu** của lượt thêm `--app "<tên>" --version <ver> --cases "<n (m
nhóm)>" --result "<x PASS · y FAIL · …>" --bugs "<bug>" --tool-minutes <phút>` (ghi `docs/usage-log.md`); republish
**bỏ `--app`**. Lượt sau đọc link cũ **của đúng app** (`--package`) rồi republish đè.

## 7. Báo lại

Mở đầu bằng kết quả check ID ads (3c: khớp/tổng, vị trí lệch, link audit — hoặc lý do chưa check) và cảnh báo ID test
(3b) nếu có. Rồi: app + máy, số key RC / key mirror, số case chạy được, verdict cuối từng case kèm số đo chính, việc cần
báo dev/PO, trạng thái máy (đã restore chưa, có `pm clear` không). **Không liệt kê "bạn tự kiểm tiếp"** cho dòng 5b làm
được. **Đưa link artifact ngay trong câu trả lời.**

## 7a. Check policy Ads + Sub — tách riêng, KHÔNG chạy trong lượt

Từ 11/11/2026 (user chốt): lượt nghiệm thu SDK **không** tự chạy `/policy-check`, ở cả nhánh bộ TC lẫn Next-Gen.
Policy là việc riêng: QA gọi `/policy-check <package>` khi cần. Sau này mới gộp lại vào cuối lượt.
Câu báo không nhắc policy; user hỏi thì trả lời là chưa chạy trong lượt này.

## 7b. Có FAIL → user review, rồi log Jira

1. Chỉ đưa FAIL **đã rà xong theo 5d**: mã case, dòng Expected, thực tế (số đo, unit, log), bước tái hiện, ảnh/video lượt
   hợp lệ, link report.
2. **Lượt terminal (có người):** **không hỏi ở terminal**. Ghi bug ra JSON (`case`, `tieu_de`, `precondition`, `buoc`,
   `expected`, `thuc_te`, `muc_do`) rồi đưa lên kênh QA qua bot đang chạy (**không tắt bot**):
   `<bin>/rcr-bao-bug --bugs <file.json> --link <link artifact> --package <pkg> --version "<x.y.z (n)>"` (hoặc `--msg-id`).
   Bot quét `out/bot-hop-thu-bug/` mỗi 20s, trả lời dưới tin build bằng menu tick bug; QA bấm **Log Jira** thì bot log và
   báo dev ở kênh project (tag đúng dev theo assignee, `src/rcr/bot_kenh_project.py`). Không gắn được tin build → file
   `.loi`. Xong thì dừng, không tự log Jira.
   - Chỉ khi user **bảo log ngay trong terminal**: hỏi bằng `AskUserQuestion` (multiSelect, mỗi bug một lựa chọn), chưa có
     câu trả lời thì không log. Bug được chọn → skill `anthropic-skills:jira-log-bug` mode TEXT (`bug_ad`), mỗi bug một
     lần. **Mỗi issue có label `auto-qa` và dòng marker CUỐI description** `AUTOQA case=<mã case> ban=<debug|release>
     pkg=<package>` (bot dùng marker để chạy lại khi verify). Log xong báo dev:
     `<bin>/rcr-notify --kind bug --title "Nhờ dev check bug · bản build <MÃ>---<Tên app> v<versionName> (<versionCode>)" --line "<KEY-1> — <tóm tắt> · <mức độ> · <link issue>"`
     — tin này **không tag dev**; đổi mẫu tin gửi dev thì gửi bản xem trước vào qa-auto cho user duyệt trước.
3. **Lượt bot (headless):** KHÔNG hỏi, KHÔNG log Jira — chỉ đưa bug vào trường `bugs` của `KET_QUA`; bot lo phần còn lại
   (`src/rcr/bot_log_jira.py`, reviewer = `DISCORD_JIRA_REVIEWER`).
4. Không có FAIL thì bỏ qua.

**Dừng ở đây. Không `git add` / `commit` / `push`** khi user chưa bảo. Code sửa theo 5e để nguyên, liệt kê trong câu báo;
user bảo commit thì push lên mọi remote máy có quyền ghi (`git remote -v`, bỏ remote push URL `no_push`); remote nào không
push được thì nói rõ.
