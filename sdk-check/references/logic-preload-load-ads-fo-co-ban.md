# Kiến thức nền SDK luồng FO — tổng hợp từ các tab "Tổng hợp SDK x"

Nguồn: sheet TC SDK `1sNFXM7oGzx_addpimZL7RYk2rXpRs_We6YUHpdtWSqU`, các tab **"Tổng hợp SDK 6.4.0 / 3.2.0 /
3.3.0 / 3.4.0 / 3.5.0"**. QA tạo các tab này ngày 06/11/2026 để tool không log nhầm bug. Bản thô từng tab
lưu ở `sdk-check/references/tong-hop-sdk/<ver>.txt`. Mỗi lượt chạy, tool so lại với sheet; tab mới hoặc tab đổi
thì cảnh báo, Claude đọc rồi cập nhật file này (xem `rc-check.md` §5d2).

**Thứ tự áp dụng:** SDK sau kế thừa SDK trước: 6.4.0 (inhouse 1.0.1, nền) → 3.2.0 → 3.3.0 → 3.4.0 → 3.5.0 →
3.5.3/3.5.4 → 3.6.1. App SDK X dùng mọi mục ≤ X. TC của chính bản đó ghi khác thì TC thắng.

**Luật đọc bảng preload:** các cột là màn **đang mở**. Ad nằm ở cột nào thì được preload/load **tại màn đó**.
Tắt một màn chỉ bỏ những ad load TẠI màn đó. Ad của màn bị tắt mà load ở màn trước vẫn load là đúng.

Viết tắt: `high` / `high1` / `high2` là các tầng floor, `allprice` (hoặc thường) là all price.
- Splash: 101 banner, 105 native, 102 inter splash, 106 native splash old user.
- Ngôn ngữ: 201 LFO1, 202 LFO2.
- Onboarding: 301 OB1, 302 OB2, 303 OB3 (native full), 304 OB4, 305 native OB5/Question, 306 inter OB5/Question.
- Old user: 301_o OB1 old.

---

## 1. SDK 6.4.0 (inhouse 1.0.1) — nền

### Preload new user (load TẠI màn →)

| Ad | Điều kiện | Load tại |
|---|---|---|
| 101_high, 101_allprice | `splash_banner_change=false` | Splash |
| 105_high, 105_allprice | `splash_banner_change=true` | Splash |
| 102_n_high, 102_n_high1, 102_n_allprice | `splash_inter_change=true` | Splash |
| 102_n_high, 102_n_high1 | `splash_inter_change=false` | Splash |
| 201_high, 201_high1 · 201_high2, 201_allprice | chưa `complete_lfo` hoặc `pass_lfo_criteria=false` | Splash · Inter splash |
| 202_high, 202_high1 · 202_high2, 202_allprice | như trên | Inter splash · LFO1 |
| 202_high, 202_allprice | ad 102 = false/no fill | LFO1 |
| 301_high, 301_high1 · 301_high2, 301_allprice | lần đầu, hoặc lần sau với `pass_lfo=false` | LFO1 · LFO2 |
| 301_high, 301_high1 · 301_high2, 301_allprice | lần sau với `pass_lfo=true` (bỏ LFO) | Splash · Inter splash |
| 302_high, 302_allprice | | OB1 |
| 303_high, 303_high1 · 303_high2, 303_allprice | check cả `pass_lfo` true/false | OB1 · OB2 |
| 304_high, 304_allprice | | OB3 |

### Preload old user (inter splash)

| Điều kiện | Ad |
|---|---|
| `splash_inter_change=true`, `inter_native_change=false` | 102_o_high, 102_o_allprice |
| `splash_inter_change=true`, `inter_native_change=true` | 106_high, 106_high1, 106_allprice |
| `splash_inter_change=false` | 102_a_high, 102_a_allprice (sheet ghi "theo o khi không a") |

### Màn OB5

OB5 là màn không cố định. Nó chỉ hiện khi **chưa show** 102_n_high/high1 và 303_high/high1/high2/allprice nào
trước đó, và lấy ad đầu tiên có fill theo thứ tự: 102_n_high → 102_n_high1 → 303_high → 303_high1 → 303_high2 →
303_allprice. Tất cả no fill/off thì không có OB5.
- Đã show một trong các ad trên trước đó → không có OB5.
- `enable_onb5_screen=false` → không có OB5.

### Config UI FO

- `onboard_config_content` là JSON gồm:
  - `lfo`: `lfo_button` (link icon PNG) và `lfo_button_color`.
  - `onb1` / `onb2` / `onb4`, mỗi màn có:
    - `content`: link ảnh JPG hoặc video MP4.
    - `is_image`: "true" là ảnh, "false" là video.
    - `background_text_color`, `enable_background_text`.
    - `title`, `title_color`, `subtitle`, `subtitle_color`.
    - `button_content`, `button_content_color`, `slider_color`.
- Các trường `*_color` là `color_id`, tra mã màu trong `onboard_design_system.custom_colors`.
- **Trường thiếu, bỏ trống hoặc sai format → về giao diện default.**
- `enable_onboard_config_content`: TRUE = dùng config, FALSE = UI default.

### Remote ID ad inter splash

Mỗi key có 3 trường hợp:
- Không fetch được Firebase → dùng ID default trong code.
- Value rỗng → dùng ID default trong code.
- Value khác rỗng → dùng ID remote.

| Điều kiện | Ad | Key |
|---|---|---|
| `splash_inter_change=true` | 102_n_high | `splash_inter_high_n_id` |
| | 102_n_high1 | `splash_inter_high1_n_id` |
| | 102_n_allprice | `splash_inter_n_id` |
| | 102_o_high | `splash_inter_high_o_id` |
| | 102_o_allprice | `splash_inter_o_id` |
| `splash_inter_change=false` | 102_a_high | `splash_inter_high_n_id` (như sheet) |
| | 102_a_allprice | `splash_inter_high1_n_id` (như sheet) |

### Remote layout

| Key | Value | UI |
|---|---|---|
| `layout_native_ads_language_1/_2`, `layout_native_ads_onb1..onb4` | layout1 (default) | native default |
| | layout2 | native thấp (PO chốt không dùng, lỗi nhiều) |
| | layout3 | native cao |
| `layout_onb1_screen`, `layout_onb2_screen`, `layout_onb4_screen` | layout1 | text ở dưới |
| | layout2 | text ở trên |

---

## 2. SDK 3.2.0 — thêm màn Question + Onboarding old (lần 2 vào app)

Base: tutorial 3.0.1 (6.4.0 cũ).

### Preload

| Ad | Load tại |
|---|---|
| 305_onb5_n_native_high, 305_onb5_n_native (new user) | **OB4** |
| 306_onb5_n_inter_high, 306_onb5_n_inter (new user) | **Question** |
| 301_onb1_o_native_high, 301_onb1_o_native (old user) | **Splash** |
| 301_onb1_o_inter_high, 301_onb1_o_inter (old user) | **Question** |

### Ad resume trong tutorial — màn nào CÓ ad resume (Y) / KHÔNG (N)

| Trigger | consent UMP | Splash | ads inter | lfo1 | lfo2 | ob1 | ob2 | ob3 | ob4 | ob5 | question | onb old |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Bấm Home (ẩn app) | N | N | N | **Y** | **Y** | **Y** | **Y** | N | **Y** | N | **Y** | **Y** |
| Đẩy app vào Recent | N | N | N | **Y** | **Y** | **Y** | **Y** | N | **Y** | N | **Y** | **Y** |
| Khoá màn (power) → mở khoá | N | N | N | **Y** | **Y** | **Y** | **Y** | N | **Y** | N | **Y** | **Y** |
| Tap notification → app khác → quay lại | N | N | N | **Y** | **Y** | **Y** | **Y** | N | **Y** | N | **Y** | **Y** |
| Kéo thanh thông báo xuống rồi vuốt lên | N | N | N | N | N | N | N | N | N | N | N | N |
| App bị kill, mở lại từ launcher | N | N | N | N | N | N | N | N | N | N | N | N |
| Mất mạng khi đang background → quay lại | N | N | N | N | N | N | N | N | N | N | N | N |

→ Ẩn app rồi mở lại ở LFO1/LFO2/OB1/OB2/OB4/Question/OB old mà **có ad resume là ĐÚNG, không phải bug**.
OB3, OB5 (native full), Splash, lúc đang có inter, consent thì **không** được có ad resume.

### Config UI

- `question_screen_config` (new user) và `onboarding_old_config` (old user) cùng cấu trúc:
  - `header_text`: bắt buộc, trống thì dùng mặc định.
  - `styles[]` gồm `style_id`, `style_name`, `style_url`.
    - Hiển thị theo `style_id` tăng dần, từ trên xuống, trái qua phải.
    - `style_name` trống → dùng giá trị mặc định.
    - `style_url` chỉ nhận webp (ảnh hoặc animation); đang tải thì hiện skeleton.
  - `cta_text`: mặc định "Go to Home".
- `layout_question_screen`: layout1 / layout2 / layout3.

### Remote nghiệm thu

- `show_305_*`, `show_306_*`: bật/tắt từng ad.
- `enable_question_screen`: bật/tắt màn Question (new user).
- `enable_ob1_old_screen`: bật/tắt OB old (old user).
- `show_301_onb1_o_*`: bật/tắt ad của OB old.
- `enable_all_ads`.

---

## 3. SDK 3.3.0 — đổi UI màn Language + logic reload ad ở màn Language

Base: 3.2.0. Preload như 6.4.0, cộng thêm một điểm: **202_high và 202_allprice còn được load tại LFO2** (dùng
khi reload lúc chọn ngôn ngữ). Khi `splash_inter_change=false` thì inter splash là 102_a_high, 102_a_allprice.

### List ngôn ngữ (`list_language`)

- Thứ tự hiển thị lấy theo JSON remote.
- Default (sai format hoặc không nhận remote): `fr, en-US, en-GB, en-CA, en-PH, en-ZA, en-IN, hi, pt-PT, pt-BR,
  fr-CA, es, es-US, zh, ru, in, bn, af-ZA, de, ko, nl`.
- **3 vị trí đầu luôn là Pháp, Anh, India.** Truyền sai → về default.
- Truyền thêm ngôn ngữ ngoài list → fallback về default cũ.

### Load / show ad

- **LFO2:** thứ tự show 202-high → high1 → high2 → normal.
- **User bấm chọn một ngôn ngữ:** reload 202-high/normal; đổi sang ngôn ngữ khác thì show 202-high → 202-normal.
  **Reload fail → vẫn giữ ad cũ.**
- **Inter splash 2 sau LFO:** chỉ hiện khi `enable_inter_splash_2_screen=true` VÀ 102-spl-n-inter-high có fill VÀ
  chưa show. Ưu tiên high → high1.
- `layout_native_ads_language_2`: layout1 / layout2 / layout3.

---

## 4. SDK 3.4.0 — delta: chỉ Splash + inter splash (LFO/OB giữ như 3.3.0)

- **Preload không đổi.**
  - New user tại Splash: 101 hoặc 105 theo `splash_banner_change`, cùng inter 102-spl-n-inter-high → high1 → inter.
  - Old user: 106-spl-o-native-high/high1/native, cùng 102-spl-o-inter-high/inter.
- **`splash_ui_config`:**
  - `type`: image hoặc gif.
  - `media_url` / `image_url`: nền (.webp) phủ kín màn. Rỗng hoặc lỗi → nền màu + icon.
  - `title`, `title_color`, `sub_title`, `sub_title_color`: chữ đè trên ảnh.
  - `video_loop`, `video_mute`: dùng khi `type` là gif/video.
- **Progress đồng bộ với việc load inter:**
  - Bắt đầu 0%, chạy dần 0 → 50 → ~90 → 100%.
  - (A) Inter load xong → nhảy nhanh lên 100% → show inter → đóng inter thì sang màn kế.
  - (B) Hết `timeout` splash mà chưa load xong → 100% → **bỏ qua inter** → màn Language.
  - (C) Load fail / no fill / không có mạng / remote tắt → ~90%, xác định xong thì 100% → bỏ qua inter.
  - Progress **không bao giờ tụt lùi**, không đứng yên ở 100% quá lâu, không loading mãi.
- **Vị trí progress + text:**
  - Chỉ theo remote bật/tắt ad (`show_105_spl_n_native` / banner), **không theo việc ad có fill hay không**.
  - Ad bật và đang show: progress + text neo trên mép vùng ad, cách 12–16dp, không đè lên ad.
  - Ad bật nhưng fail/no fill: vùng ad **vẫn giữ chỗ**, ảnh nền xuyên qua, không có box trống. Progress không nhảy
    xuống đáy.
  - Ad tắt: progress + text neo ở đáy màn, phía trên safe-area.

---

## 5. SDK 3.5.0 — tắt high1/high2, SWIPE ở OB2, OB3 auto swipe + nút X

### Remote tắt high1/high2 ⇒ 0 request

Remote OFF thì SDK **không được gọi loadAd()**: AdMob Requests = 0, Bid requests = 0. Có request là bug; có
impression là bug nặng. Áp cho:

| Màn | Ad |
|---|---|
| Splash | 102-spl-n-inter-high1; old user 106_spl_o_native_high1 |
| LFO1 | 201 high1/high2 |
| LFO2 | 202 high1/high2 |
| OB1 | 301 high1/high2 |
| OB2 | native onb2 (ID unit hỏi dev) |
| OB3 | 303 high1/high2 |

### OB2 — SWIPE (`swipe_onb2`, default TRUE)

- **Ad OB2 tắt** (`swipe_onb2=true`): không request. Vùng ad hiện icon SWIPE lặp, chỉ hướng vuốt ngang. Vuốt →
  sang OB3.
- **Ad OB2 bật:**
  - Có fill: native + icon SWIPE nhỏ theo figma.
  - No-fill / fail / timeout: để trống phần ad + vẫn có icon SWIPE.

### OB3 — native full + auto swipe (`auto_swipe_onb3` default TRUE, `timer_auto_swipe`)

- `auto_swipe_onb3=TRUE`, timer > 0, ad đã show: hết timer mà user không thao tác → tự sang OB4.
- `auto_swipe_onb3=TRUE`, không có ad (OFF hoặc no-fill) mà vẫn vào OB3: hết timer **vẫn tự chuyển màn**.
- Ad đang loading: timer **đếm từ lúc ad show**.
- `auto_swipe_onb3=FALSE`: **không** auto swipe, kể cả khi không có ad.
- User vuốt tay trước khi hết timer: chuyển ngay, huỷ timer, không chuyển 2 lần. Rời màn thì timer phải huỷ.
- `timer_auto_swipe ≤ 0` → default 5s. Chỉ nhận số nguyên.

### OB3 — nút X (`ob3_show_button_skip` default FALSE, `timer_button_x`)

- `ob3_show_button_skip=TRUE`: đếm ngược theo remote, hết đếm thì hiện X. Trong lúc đếm có thể hiện số thay cho X.
- `timer_button_x = 0` → X hiện ngay từ đầu. `< 0` hoặc ký tự → default 5s.
- Bấm X: đóng native full, sang màn kế, huỷ auto-timer nếu đang chạy.
- **Đếm ngược của X và auto swipe là 2 timer độc lập.**
- Lướt qua lại OB3, reload và show ad mới thành công → đếm ngược X **chạy lại từ đầu**.
