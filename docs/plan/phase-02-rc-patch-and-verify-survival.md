---
phase: 2
title: "rc_patch + rc_verify (tim cua tool)"
status: completed
priority: P1
effort: "1.5d"
dependencies: [1]
---

# Phase 2: rc_patch + rc_verify

## Overview
Ghi giá trị remote config mình muốn vào app, **và chứng minh nó sống** sau khi mở app.
Đây là tim của tool — cơ chế đã verified thực nghiệm, phase này chỉ code hoá cho đúng.

## Requirements
- Functional: `patch(baseline, {key: value})` → ghi `activate.json` + `settings.xml` + mirror.
- Functional: `verify(baseline, expected)` → đọc lại, trả danh sách key lệch.
- Functional: `restore(baseline)` → trả app về giá trị gốc + mốc fetch cũ (app tự lấy lại thật).
- Non-functional: file tạm ở `/data/local/tmp` **luôn bị xoá**, kể cả khi copy lỗi.

## Architecture

```
patch(client, serial, package, baseline, overrides) -> PatchResult
  1. configs = {**baseline.configs, **overrides}
     json = {...baseline goc, "configs_key": configs, "fetch_time_key": now_ms}
  2. settings = re.sub(last_fetch_time_in_millis -> now_ms, baseline.settings_xml)
  3. cho moi mirror file co key trong overrides:
       thay value TAI CHO, GIU NGUYEN kieu XML cua key do
  4. ghi tung file: adb push -> /data/local/tmp/rcr_<n> -> cat | run-as sh -c 'cat > dest'
  5. finally: rm -f moi file tam
```

**Quy tắc kiểu mirror** — RC lưu mọi thứ là string, mirror lưu có kiểu. Khi ghi mirror:
| Kiểu sẵn có trong mirror | Value RC `"false"` ghi thành |
|---|---|
| `boolean` | `<boolean name="k" value="false" />` |
| `string` | `<string name="k">false</string>` (escape `&`, `<`, `"`) |
| `long`/`int` | `<long name="k" value="0" />` — parse số, **fail rõ** nếu không parse được |

Key có trong `overrides` mà **không** có trong mirror → chỉ ghi `activate.json`, không tự thêm
node mới vào mirror (SDK sẽ tự sync; thêm node lạ là đoán).

**Chốt cứng: chỉ ghi vào file nằm trong `baseline.mirrors`.** File trong
`baseline.non_mirror_files` là state nội bộ app (`vsl_template4_prefs.xml`,
`vsl_widget_local_prefs.xml` — 0 key giao với RC) → ghi vào là làm hỏng trạng thái app.
`rc_patch` phải `assert` file đích thuộc `mirrors` trước khi gọi `rc_write`.

```
verify(client, serial, package, expected) -> list[Mismatch]
  doc lai files/frc_<appId>_firebase_activate.json
  so tung key trong expected voi configs_key thuc te
  lech -> Mismatch(key, muon, thuc_te)
```

## Chiến lược ghi — 2 đường, cùng một interface

`rc_write` chọn chiến lược theo máy, phần còn lại của tool không biết gì về chuyện này:

| Chiến lược | Điều kiện | Lệnh |
|---|---|---|
| `run-as` | app debuggable | `adb push` → `/data/local/tmp` → `run-as pkg cp` (fallback `cat tmp \| run-as pkg sh -c 'cat > dest'`) |
| `su` | máy root | `adb push` → `su -c cp tmp dest` + `su -c chown <uid>:<uid> dest` |

Đường `su` quan trọng: **app release cũng patch được** → không phụ thuộc dev bật `debuggable`.
Dò chiến lược 1 lần lúc đọc baseline: thử `run-as pkg id`, không được thì thử `su -c id`,
cả hai không được → `BLOCKED` kèm câu hướng dẫn xin bản debuggable.

## Related Code Files
- Create: `src/rcr/rc_patch.py`, `src/rcr/rc_verify.py`, `src/rcr/rc_write.py` (đường ghi file,
  2 chiến lược `run-as` | `su`)
- Create: `src/rcr/mirror_xml.py` (thay value giữ kiểu — tách riêng vì là logic thuần, dễ test)
- Modify: `src/rcr/models.py` (+ `PatchResult`, `Mismatch`), `src/rcr/main.py` (+ routes)
- Create: `tests/test_rc_patch.py`, `tests/test_mirror_xml.py`, `tests/test_rc_verify.py`
- Read để tham chiếu: `~/Downloads/Tool_test_data_app-main/src/tsa/remote_config.py`
  (đường `push` → `run-as cp` + fallback stdin + xoá tmp) và
  `.../tests/test_remote_config_push.py` (khuôn FakeAdb)

## Implementation Steps
1. `rc_write.py`: `write_file(client, serial, package, dest_rel, content: bytes)`.
   Chặng 1 `adb push` vào `/data/local/tmp/rcr_<uuid>`; chặng 2 thử
   `run-as pkg cp tmp dest`, lỗi thì `cat tmp | run-as pkg sh -c 'cat > "dest"'`.
   `finally: rm -f tmp`. Bọc nháy `dest` (tên `frc_*` có dấu `:`).
2. `mirror_xml.py`: `set_value(xml, key, kieu, value_str) -> str`. Thuần string, không parse XML.
3. `rc_patch.py`: dựng json + settings + mirror rồi gọi `rc_write` lần lượt. Ghi
   `activate.json` **sau cùng** — nếu mirror lỗi giữa đường thì config chính chưa bị đổi.
4. `rc_verify.py`: đọc lại + so sánh.
5. `restore(baseline)`: ghi lại `configs` gốc, và set `last_fetch_time_in_millis` về
   **mốc cũ trong baseline** → app tự fetch lại config thật ở lần mở sau.
6. Routes: `POST /api/patch`, `POST /api/verify`, `POST /api/restore`.
7. Tests FakeAdb — các điểm phải gác:
   - đúng thứ tự lệnh cho từng file, `activate.json` ghi sau cùng
   - file tạm **luôn** bị `rm`, kể cả khi chặng 2 raise
   - `run-as cp` lỗi → tự đi đường stdin, không báo lỗi oan
   - `fetch_time_key` **và** `last_fetch_time_in_millis` đều được set = now
   - mirror: `boolean` giữ `boolean`, `string` giữ `string`, `long`/`int` parse số
     (kiểu gặp thật: `boolean` 74 · `string` 28 · `long` 3 · `int` 3)
   - key không có trong mirror → không thêm node mới
   - **file trong `non_mirror_files` KHÔNG BAO GIỜ bị ghi** — kể cả khi trùng tên key do
     trùng ngẫu nhiên; guard phải là `assert file in baseline.mirrors`
   - `vsl_rating_remote_prefs.xml` (3/5 key là RC): chỉ 3 key RC được ghi, 2 key nội bộ
     giữ nguyên nguyên văn
   - `verify` phát hiện đúng key lệch

## Success Criteria
- [ ] Trên máy thật: `patch({"ad_load_timeout": "99"})` → mở app → `verify` trả **rỗng**
- [ ] Cố tình bỏ bước settings.xml → `verify` trả mismatch (tái hiện được thất bại đã đo)
- [ ] Key bị mirror (vd `enable_onb3_screen`) → đọc lại **cả** `activate.json` **và** file
      mirror, cả 2 đều mang giá trị mới
- [ ] `vsl_template4_prefs.xml` và `vsl_widget_local_prefs.xml` **không đổi 1 byte** sau khi patch
      (so hash trước/sau) — chống ghi vào state nội bộ app
- [ ] Test mirror chạy trên **cả** `aiphotogenerator.photoshoot.aiart.aiimagegenerator`
      (4 file mirror, có file mirror một phần) để phủ biến thể
- [ ] `mirrors` rỗng (`com.aiartvideo.imageai.aigenerator`) → chỉ ghi `activate.json` +
      `settings.xml`, không lỗi
- [ ] Chạy được trên **Android 12** (Pixel 4) — cả `run-as cp` lẫn đường stdin đều đã đo là chạy
- [ ] Máy không root + app không debuggable → `BLOCKED` kèm hướng dẫn, **không** traceback
- [ ] `patch` với giá trị **bằng đúng giá trị gốc** → hành vi app không đổi (đã verify tay:
      lượt nguyên trạng và lượt patch-giá-trị-gốc cho kết quả giống hệt)
- [ ] `restore` → app mở lại lấy config thật, `rcr_probe` không còn
- [ ] `/data/local/tmp` sạch sau mọi lần chạy (kể cả lần lỗi)
- [ ] Mọi module <200 LOC

## Risk Assessment
- **`minimumFetchInterval = 0` ở build dev** → throttle vô hiệu, patch bị đè. `verify` bắt được
  → trả `BLOCKED`. Nếu app nào cũng vậy thì phải bàn lại (cắt mạng có chọn lọc), **không**
  tự ý làm trong phase này.
- **Ghi mirror lúc app đang chạy** → app có thể ghi đè prefs từ bộ nhớ. Luôn `force-stop`
  trước khi patch. Phase 4 sở hữu thứ tự này.
- **Escape XML sai** → prefs hỏng, app crash hoặc mất hết config. Test `mirror_xml` phải phủ
  value có `&`, `<`, `"`, và chuỗi JSON (mirror có key chứa JSON dài).


## Ket qua thuc te (2026-09-08)

77 test xanh khi khong cam may. Module: `rc_write.py` (98), `rc_patch.py` (137),
`rc_verify.py` (107) - deu <200 LOC.

Do that tren Pixel 4, app `lingospeak.english.learnlanguage.speak` (131 key, 4 file mirror):

| Kiem tra | Ket qua |
|---|---|
| patch 2 key (ca 2 deu bi mirror) -> mo app -> verify | `ok=True` |
| thu tu ghi | mirror -> settings -> `activate.json` sau cung |
| `vsl_template4_prefs.xml` (state noi bo) | **hash khong doi 1 byte** |
| `/data/local/tmp` sau khi chay | **0** file `rcr_` |
| restore | verify `ok=True`, moc fetch tra ve **moc cu** |
| **CO TINH bo moc throttle** -> mo app | `verify ok=False`, `verdict_hint=BLOCKED`, bat duoc lech o **ca** activate **va** mirror |

### BUG DA SUA (dang bug nay se tai xuat hien neu ai viet lai tang ghi)

`adb shell run-as pkg sh -c "cat tmp > dest"` **KHONG chay dung**: adb noi argv thanh MOT
dong roi cho `sh` NGOAI tren device chay -> dau `>` bi shell ngoai an mat, no tao file theo
cwd cua chinh no (`/`) va bao `No such file or directory`. Ket qua: **moi** file deu roi xuong
duong stdin du phong (ton 2 vong adb thay vi 1), va fallback CHE MAT loi nay - end-to-end van
dung nen khong ai biet.

Sua: dung `shell_line` + boc nhay ca cau lenh trong, giong duong `su` da lam dung tu dau.
Gac bang 2 test: `test_duong_1_khong_de_shell_ngoai_an_dau_redirect` (dau `>` phai nam trong
cap nhay cua `sh -c`) va `test_duong_1_thanh_cong_thi_khong_dung_fallback`.

### Ngu nghia so sanh cua verify (da chot)

- **activate**: so **thang tung ky tu**. `activate.json` giu y nguyen chuoi da ghi.
- **mirror**: so sau khi **dich dinh dang** - mirror luu co kieu (`<int value="7">`), RC luu
  string (`"7"`). Day la DICH, khong phai noi long.

Nen patch `'true'` roi verify `'TRUE'` -> LECH, va lech nay dung: bao khop se che mat truong
hop config that su khong phai cai minh dat. Gia tri di tu file TC qua patch va verify deu la
MOT chuoi nen thuc te khong vap.
