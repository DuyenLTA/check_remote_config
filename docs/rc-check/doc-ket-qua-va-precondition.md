# rc-check — đọc kết quả, precondition, bẫy đã gặp (chi tiết mục 5 / 5c)

Đọc khi: case ra `BLOCKED` / `KEY_NOT_USED` / `needs_human`, case có precondition môi trường, hoặc nghi tool chấm sai.

## Verdict chi tiết

- `PASS` — ad không fill mà có request **đúng unit** của vị trí trong câu (hoặc vị trí case bật) cũng là PASS (user chốt
  25/09, nhắc lại 06/10/2026). Không có request nào của vị trí đó → FAIL. Đừng tự đổi luật này sang BLOCKED.
- `NEEDS_HUMAN` — tool chưa lái tới màn, hoặc quảng cáo che màn. Không kết luận gì về app, không trả cho user → mục 5b.
- `NOT_VERIFIABLE` — dòng nhìn mắt → mục 5b. Dòng hỏi số liệu **AdMob/Firebase console** là việc của **PO** (tester không
  có quyền), đếm riêng `po`, không gộp `pending`; bước Action bảo mở console thì bỏ qua, không dừng case.
- `CONFIG_OK` / `BLOCKED` — case không có Expected: đặt được config / config không sống qua lần mở app (build dev đặt
  `minimumFetchInterval = 0`). `BLOCKED` còn dùng khi precondition chưa thành hiện thực, hoặc điều kiện của dòng
  `"Nếu X thì Y"` không hề xảy ra.
- `KEY_NOT_USED` — key không có chuỗi trong `classes*.dex`: app không đọc key đó (template Firebase dùng chung nhiều app).

Case nhiều lượt (`layout1/2/3`): `run.runs` là từng lượt, verdict case = lượt xấu nhất.

## Precondition có thành hiện thực không

Nhiều case đòi **điều kiện môi trường** (simulate no-fill, chặn ad server, throttle ≤50kbps, mediation test mode). Không tạo
được thì nhiều case tả nhiều nhánh sẽ cùng ra một kết quả (28/09/2026: case 22/23/24 đều PASS khi chỉ một trạng thái xảy ra).

- **Ép được** — đổi `id_*` của vị trí sang slot trống (`…/0000000001`): request vẫn đi, đếm được trong log, không bao giờ
  có ad. Chỉ với vị trí RC có khai `id_*` (Piclux chỉ 12/92 vị trí; 302 không có).
- **ID nằm cứng trong app** → tool bật Private DNS `dns.adguard-dns.com` cho cả case (chặn domain quảng cáo, Firebase vẫn
  chạy), đổi wifi để bỏ cache DNS, xong trả DNS cũ. Khi đó **mọi** vị trí đều không về ad — dòng cần ad vị trí khác thì đo tay.
  Không có cách no-fill riêng một màn: tường lửa theo app chặn từ đầu thì SDK không gửi request nào (= mất mạng), chặn
  giữa chừng thì request treo chứ không fail (đo Pixel 6, 09/11/2026).
- **Ad về muộn** ("Đi qua LFO2 ngay để 202 chưa kịp show", "Rời OB3 trước khi 303 về") → **cần máy Android 13+**.
  Tool chặn mạng của riêng app bằng tường lửa có sẵn (`cmd connectivity set-package-networking-enabled`, không cần root,
  `src/rcr/mang_cham.py`) **theo màn** (`src/rcr/mang_cham_cua_so.py`): đọc logcat trực tiếp (`<màn>_view`, AdActivity
  của inter splash), chặn **ngay khi app gửi request của ad đích** (event `track_ad_request` có ID đầy đủ; chặn sớm hơn thì SDK thấy mất mạng và bỏ luôn request), chặn kèm `com.google.android.gms` (GMA có đường dự phòng qua Play services)
  tới khi rời màn đích rồi trả mạng. Tường lửa chỉ drop gói tin nên request đang chạy treo lại, trả mạng thì về muộn
  (~15s sau); giữ quá 45s thì tự trả (GMA cắt request ở 60s). Trả mạng xong tool đứng ở màn hứng tối đa 30s chờ `ad_load` của ad đích.
  Case chạy riêng (không nối chuỗi), xong luôn trả mạng; preflight bắt app còn bị chặn của lượt chết giữa chừng (`LOI`).
  - Máy Android ≤ 12 → `BLOCKED` "cần Android 13+". **Proxy HTTP không dùng được**: GMA tải ad bằng QUIC đi thẳng,
    proxy giữ hay cắt thì ad vẫn load sau ~2s (đo Pixel 4, 09/11/2026).
  - "Throttle băng thông" không nêu màn → `BLOCKED`: tường lửa chỉ chặn/mở, không bóp băng thông.
  **Chỉ nhận kết quả khi log xác nhận**: ad của màn đó có về nhưng KHÔNG show ngay tại màn đó (`mang_cham` trên report,
  kèm giờ chặn/trả). Vẫn show ngay tại màn, hoặc không về lần nào (fail / timeout) → `BLOCKED`. Ad trùng đuôi ID (202/303
  `…034`) chỉ tính "đã về" khi có `ad_show` mang ID đầy đủ. Giữ mạng không làm kho có ad: cần fill mà kho không fill vẫn BLOCKED.
- **Không ép được** (mediation test mode, cần root, sai hãng máy) → case không được PASS, hạ `BLOCKED` kèm `precondition_thieu`.
- Dù ép hay không, vẫn kiểm bằng log (`ep_ad_fail`). Ép rồi mà ad vẫn fill → `BLOCKED`, ép hỏng.
- **Ngắt mạng KHÔNG phải no-fill.** Mất mạng thì log không có unit nào; no-fill thật là "có request, kho không trả ad".
- Cách tay của tester: lắc máy → Ad Inspector → chọn Meta. Lưu ở `shared_prefs/admob.xml` key `inspector_info`, trường
  `networkExtras` — chưa biết schema; muốn tự động thì nhờ tester làm một lần rồi đọc payload.

## Nhật ký lái và reset

- `run.runs[i].drive`: từng bước ra thao tác gì, dừng ở đâu, vì sao. `NEEDS_HUMAN` ở đây là tool từ chối đoán, không phải
  bug app — hay gặp: ad che màn, nhiều node cùng khớp. `--no-actions` để chỉ đặt config.
- `run.reset`: `force-stop` / `soft` (lật cờ onboarding) / `clear` (`pm clear` — mất login và data app, **nói cho user**).
- Sau reset mềm, onboarding nằm sau splash ad và ad không tự đóng; tool cố tình không tap. Đừng báo như app không vào được
  onboarding — lấy bằng chứng theo 5b.

## Bảng `tc.cases`

- `overrides` — key/value tool sẽ đặt, đã lọc bằng key thật của app
- `ignored` — key trong `Test Data` không thuộc RC (param analytics `source`, `click_area`…). Bị loại là đúng
- `needs_human` — tool cố tình không đoán: runtime toggle (`a → b → a`, cả ở tên case / Precondition), sửa field trong
  JSON, giá trị còn chỗ trống (`<id template đang test>`), ký hiệu ép trạng thái ad chưa có key ID đã đo
  (`src/rcr/data/ad_id_keys.yaml`), quá 16 tổ hợp, hoặc không key nào thuộc RC
- `from_precondition` — key lấy từ cột Precondition (TC từ 3.2.0 bỏ cột Test Data). Trùng key thì Test Data thắng
- `tc_lech` — JSON TC có trường mà giá trị server không có (TC 3.4.0 `image_url`, server Piclux `media_url`). **Chỉ cảnh
  báo**: đọc log app trước khi kết luận TC sai (Piclux 2.4.0 đọc cả `image_url`). Report hiện ở "TC lệch giá trị server"

TC hay viết vị trí bằng **mã**: *"tắt unit 102-spl-n-inter-high1 (key show_* tương ứng) = false"* → tool suy
`show_102_spl_n_inter_high1`, **chỉ nhận khi key có thật** trên máy và giá trị lấy được từ chính câu đó.

Case `needs_human` không phải lỗi tool hay bug app. Lý do là chỗ trống mà server của app có giá trị thật cùng loại (vd
`splash_ui_config` gif có `media_url` thật) → dùng giá trị đó, chạy theo 5b, ghi rõ trên report là đã thay. Không có giá trị
thật → báo tách khỏi phần chạy được, kèm nguyên văn lý do.

## Bẫy đã gặp — tool đã xử lý, đừng đi tìm bug app

- `activate.json không phải JSON hợp lệ` ngay sau `pm clear`: đọc trúng lúc SDK đang ghi; tool tự đọc lại 4 lần.
- Mã viết tắt `302` phải khớp `302_onb2_n_native`.
- TC ghi `layout_native_ads_language_1`, APK chỉ có `layout_ad_native_lfo_1` → chấm bằng đủ bộ `nativeAdView, ad_headline,
  ad_media, ad_call_to_action` (`src/rcr/data/ui_names.yaml`, trường `ids_all`).
- Sau `pm clear` config mới có `enable_all_ads*=false` → tool tự đặt nền `true`; log ads trống thì đọc 3 key này trước.
- "Ad X show / KHÔNG show tại màn Y": tool chấm bằng event `ad_show` gán theo `<màn>_view` gần nhất (`assert_ad_screen`),
  không bằng request. `ad_show` có mà màn trống → dòng "hiển thị" vẫn phải mở ảnh đối chiếu (5d).
- "Đi qua LFO2 nhanh": tool học tọa độ lượt đầu rồi bấm qua LFO trong ~0,8s; ad LFO2 vẫn show ở LFO2 → BLOCKED, tự chạy
  lại. Không đạt sau các lần chạy lại thì là giới hạn thời gian của máy, nói rõ.
- OB3 không fill: phải có request native 303 và khung chụp không thấy X. ID 303 nằm cứng trong app, không ép fill được
  bằng đổi ID — đừng tốn lượt thử. Timer OB3 không ad tính từ lúc ad **fail**: 3.0/4.0/5.0/6.0s là đúng.
