---
phase: 5
title: "assert_dump + verdict"
status: in-progress
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

> **Đo 2026-09-23 (SDK FO 3.2.0, `photocreator.aiart`)**: app đích **không in**
> `FOR_TESTER_*` — dòng `FOR_TESTER_*` thấy lúc đó là của app khác cùng máy. **Luôn lọc theo
> PID app đích** (quyết định 24). Tín hiệu thay thế: `NativeAdHelper: <Activity>:
> adNativeState(Loading|Loaded|Fail)`, `AdEventLogger: trackAdRequest ... adType: <TYPE>`,
> `FO_VslTemplate4FirstOpenSDK: Native splash impression`. Bản debug dùng ID test Google cho
> mọi native → chấm "unit high vs thường" theo ID là `NOT_VERIFIABLE`.

> **Chốt chặn ép ad (quyết định 27)**: case có ID bị ép → log request phải chứa đúng ID đó
> (`D/TAG: loadInterstitialAd: <id> - <id>` hoặc `trackAdRequest ... adUnitId: *****<3 số cuối>`).
> Không thấy → `BLOCKED` ("app không đọc key ID này"). Case có `X: loaded` không ép được → phải
> thấy X `loaded`/`trackAdMatchedRequest`, không thì `BLOCKED`, không chấm FAIL.

> **Nhận diện unit bằng checklist ID ads** (2026-09-23): sheet thông số kỹ thuật của workflow
> `audit-fanout` (`~/android-ad-audit`, sheet `14XivZl9…`, 1 tab/app) khai **vị trí → ID**
> (`show_105_spl_n_native_high → …/2009698815`). Dùng lại `checklist_source` để map ID trong
> log request về vị trí → chấm được "unit HIGH hiển thị" thay vì `NOT_VERIFIABLE`. Chỉ áp cho
> bản dùng ID thật; bản debug gắn ID test Google cho native thì vẫn không phân biệt được.
> ID này **không** dùng để ép fail: trên AIP922 v3.2.0 các ID nằm cứng trong `classes*.dex`
> (không có key `id_*` trong RC), trừ `splash_inter_*_id`.

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


## Grammar log ads — đo thật 2026-09-25 (Piclux 2.8.0 / FO SDK 3.5.4-alpha02)

**Bản này KHÔNG có tag `FOR_TESTER_*` nào** (quyết định 18 ghi theo bản khác). Chỉ có hai nguồn:

```
BannerAdHelper: SplashActivity: adBannerState(None|Loading|Fail)
AdEventLogger: trackAdRequest adPlatform:Admob  - adUnitId: *****495  -  adType: BANNER
AdEventLogger: trackAdLoadSuccess - adUnitId: *****588  -  adType: interstitial  - ...
AdEventLogger: trackAdLoadFailed  - adUnitId: *****825  -  adType: banner  -  errorMessage: No fill.
AdEventLogger: trackAdShowSuccess - adUnitId: *****588  -  adType: interstitial  -  showStatus: success
```

**ID bị che, chỉ còn 3 số cuối** → đối chiếu với ID trong remote config phải theo đuôi;
nhiều key cùng đuôi thì trả cả hai và nói rõ là mơ hồ, không chọn bừa (`ad_log.match_rc_id`).

**Banner splash của Piclux KHÔNG lấy ID từ remote config**: unit `*****495` / `*****825`
không khớp key nào, và `dex_check` xác nhận app không đọc `id_101_spl_a_banner` (…717).
Chỉ `splash_inter_high_n_id` (…588) là RC-driven. → ép fill/fail theo ID (quyết định 27)
với app này chỉ làm được ở inter high.

## Hai case đối chứng đã chạy thật (bộ TC chung, tab TC SDK 6.4.0)

| | `#1` bật cả 2 banner | `#4` tắt cả 2 banner |
|---|---|---|
| overrides | `sbc=false`, `show_101_spl_a_banner_high=true`, `show_101_spl_a_banner=true` | `sbc=false`, cả hai `show_101…=false` |
| `adBannerState` | `None → Loading → Fail` | **không có dòng nào** |
| banner unit request | `*****495` (high) rồi `*****825` (thường) | **0 unit** |
| inter | `*****588` loaded + shown | `*****588` loaded + shown |

Case #4 Expected: *"Không load bất kỳ banner nào / Không show banner trên Splash / Không crash"*
→ **khớp**: 0 request banner. Case #1 Expected: *"SDK preload banner 101 theo alternate:
high trước, thường sau"* → **khớp**: đúng 2 request theo thứ tự high → thường. Banner không
hiển thị vì `No fill`, không phải lỗi app.

Đây là tầng chấm mà phase 5 dùng cho case ads: **so tập unit đã request giữa lượt bật và
lượt tắt**, độc lập với chuyện ad có fill hay không.


## Đã làm (2026-09-25)

- `crash_log.py` — đọc buffer `crash` riêng của Android (không grep logcat chính, tránh lẫn
  dòng có chữ "exception" của app). **Không lọc theo PID**: app crash xong tiến trình chết,
  PID biến mất — lọc theo PID là bỏ sót đúng cái đang tìm. Lọc theo tên package trong dòng.
- `assert_check.py` — chấm **từng dòng** Expected, verdict case = dòng xấu nhất.
  Thang bậc: `FAIL` > `BLOCKED` (config không sống) > `BLOCKED_NO_FILL` > `NEEDS_HUMAN` >
  `NOT_VERIFIABLE` > `CONFIG_OK` > `PASS`. `CONFIG_OK` đứng **trước** `PASS`: "đặt được
  config" kén hơn "đã chấm và đúng".

Đo trên 1421 dòng Expected thật của bộ chung: 188 dòng "không crash", 125 dòng phủ định ads,
474 dòng khẳng định hiển thị/show, 100 dòng preload/alternate. Bốn luật hiện có bám đúng
những nhóm đó; dòng ngoài phạm vi → `NOT_VERIFIABLE` kèm nguyên văn, **không đoán thành PASS**.

### Case ads chấm ở tầng request/load

Theo quyết định 30 và 31: có log request/load là đủ, không đòi nhìn thấy ad.
`shown>0` → PASS; `loaded>0, shown=0` → PASS (chấm ở tầng load); `requested>0` mà không
fill → **PASS** kèm ghi chú "request đúng nhưng không fill" (kho quảng cáo không trả ad,
app không sai); `requested=0` → FAIL, hoặc `NEEDS_HUMAN` nếu tool chưa lái tới màn nào.

### Không được báo oan khi ID bị che

Lần chạy đầu case `6.4.0#1` ra **FAIL** ở dòng *"Không hiển thị native ad trên splash"* vì
log có 4 native unit được request. Sai: ID bị che chỉ còn 3 số cuối, không unit nào map được
về key RC, nên **không quy được** những request đó cho native splash — rất có thể là native
của màn sau đang preload. Đã sửa: câu phủ định **có nêu vị trí** (105 / "trên splash") mà
không map được unit → `NOT_VERIFIABLE`. Câu phủ định **"bất kỳ… nào"** (không giới hạn vị
trí) thì vẫn `FAIL` như cũ.

### Hai case đối chứng — chấm thật

| Case | Verdict | Từng dòng |
|---|---|---|
| `6.4.0#4` tắt cả 2 banner | **PASS** | "Không load bất kỳ banner nào" PASS · "Không show banner trên Splash" PASS · "Không crash" PASS |
| `6.4.0#1` bật cả 2 banner | **PASS** (sau quyết định 31) | 2 dòng banner hiển thị → PASS (request đúng, không fill) · "preload alternate" NOT_VERIFIABLE · "không hiển thị native" NOT_VERIFIABLE |

Còn lại của phase 5: chấm thứ tự preload (cần map unit → vị trí, hiện ID bị che nên chưa
làm được), và `NEEDS_HUMAN` cho dòng đòi thao tác tay.
