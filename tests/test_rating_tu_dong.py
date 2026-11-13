"""Tab TC rating tu lai + tu cham (act_rating / rating_may / assert_rating) - phan thuan, khong goi may."""

from rcr import act_rating, act_resolver, assert_rating, rating_cong_thuc, rating_may
from rcr.ui_dump import parse_dump

POPUP = """<hierarchy><node package="p" class="android.view.View" text="" content-desc="" bounds="[0,0][1080,2400]">
<node package="p" class="android.view.View" text="" content-desc="Star 1" bounds="[174,1290][282,1398]"/>
<node package="p" class="android.view.View" text="" content-desc="Star 2" bounds="[330,1290][438,1398]"/>
<node package="p" class="android.view.View" text="" content-desc="Star 3" bounds="[486,1290][594,1398]"/>
<node package="p" class="android.view.View" text="" content-desc="Star 4" bounds="[642,1290][750,1398]"/>
<node package="p" class="android.view.View" text="" content-desc="Star 5" bounds="[798,1290][906,1398]"/>
<node package="p" class="android.widget.TextView" text="RATE" content-desc="" bounds="[476,1624][605,1689]"/>
<node package="p" class="android.view.View" text="" content-desc="Close" bounds="[865,660][949,744]"/>
</node></hierarchy>"""


def test_doc_popup_sao_nut_x():
    pop = rating_may.doc_popup(parse_dump(POPUP))
    assert pop["hien"] and pop["nut"] == "RATE" and pop["sao"][3] == (540, 1344) and pop["x"] == (907, 702)


def test_resolver_dich_cau_tab_rating():
    k = lambda s, n=(): act_resolver.resolve(s, list(n)).summary["kind"]
    assert k("Gen ảnh, chờ popup.") == "rating_gen"
    assert k("Chọn 1 sao, bấm button.") == "rating_sao"
    assert k("Thực hiện thao tác thoát app.") == "rating_thoat"
    assert k("Bấm ← trên màn Feedback (không Submit).") == "rating_back"
    assert k("Nhấn giữ icon app, chọn option Rating.") == "rating_shortcut"
    assert k("Bấm X.", parse_dump(POPUP)) == "rating_x"
    assert k("Bấm X.") != "rating_x"          # khong co popup rating: luat bam X chung
    a = act_resolver.resolve('Chọn 4 sao, bấm "Rate on Google Play".', [])
    assert a.sao == 4 and a.bam
    assert not act_resolver.resolve("Đổi sang 5 sao.", []).bam


def test_parse_shortcut_va_su_kien():
    dump = """  Package: com.x
      ShortcutInfo {id=shortcut_uninstall, flags=0x85
        shortLabel=Uninstall, resId=0
        intents=[Intent { act=android.intent.action.VIEW cmp=com.x/.Splash }]
      ShortcutInfo {id=vsl_rating_shortcut, flags=0x85
        shortLabel=Rate, resId=0
        intents=[Intent { act=com.apero.rating.action.RATING cmp=com.x/.VslRatingActivity }/null]
  Package: com.y
"""
    ds = rating_may.parse_shortcut(dump, "com.x")
    assert [s["id"] for s in ds] == ["shortcut_uninstall", "vsl_rating_shortcut"]
    assert [rating_may.la_shortcut_rating(s) for s in ds] == [False, True]
    log = ("1794483777.083 30038 25037 V FA-SVC  : Logging event: origin=app,name=rating_star_clicked,"
           "params=Bundle[{placement_name=result, ga_event_origin(_o)=app, star_value=3}]")
    assert rating_may.parse_su_kien(log) == [
        {"t": 1794483777.083, "ten": "rating_star_clicked", "params": {"placement_name": "result", "star_value": "3"}}]


def test_phan_tich_moc_nut_x():
    chua, co = bytes([10] * 400), bytes([200] * 400)
    khung = [(100.0 + i * 0.25, chua if i < 11 else co) for i in range(16)]   # X hien o khung 11 = 2,75s
    kq = rating_may.phan_tich(khung, 100.0)
    assert kq["x_hien_s"] == 2.75 and kq["x_chua_hien_luc_s"] == 2.5


def test_tim_duoi_lay_node_bam_duoc_dau_tien():
    xml = """<hierarchy><node package="p" class="V" text="Sample" bounds="[48,1800][300,1860]"/>
<node package="p" class="V" text="" clickable="true" bounds="[288,1881][504,2041]"/>
<node package="p" class="V" text="" clickable="true" bounds="[48,1881][264,2041]"/></hierarchy>"""
    assert rating_cong_thuc.tim_duoi(parse_dump(xml), "^Sample$").bounds.left == 48


def test_cong_thuc_aip892_co_san():
    assert rating_cong_thuc.cong_thuc("com.aimakeup.aifaceeditor.facemakeup.faceswap", "anh")
    assert rating_cong_thuc.cong_thuc("com.khong.co", "anh") is None


def _drive(*recs):
    return {"steps": [{"rating": r} for r in recs]}


def test_cham_nhan_mo_feedback_back_ve_result():
    gen = {"viec": "gen", "popup": True, "man": "ResultActivity", "do_x": {}, "su_kien": [
        {"t": 1.0, "ten": "rating_placement_viewed", "params": {"placement_name": "result"}}]}
    sao = {"viec": "sao", "sao": 1, "nut": "RATE", "nut_enabled": True, "da_bam": True, "truoc": "ResultActivity",
           "pkg_sau": "p", "man_sau": "VslRatingFeedbackActivity", "google_play": False, "su_kien": []}
    back = {"viec": "back", "man": "ResultActivity", "pkg": "p", "su_kien": []}
    d = _drive(gen, sao, back)
    assert assert_rating.cham('Nhãn button "Rate" (1 < 2).', d)["verdict"] == "PASS"
    assert assert_rating.cham("Mở màn Feedback.", d)["verdict"] == "PASS"
    assert assert_rating.cham("Back về màn result.", d)["verdict"] == "PASS"
    assert assert_rating.cham('Nhãn "Rate on Google Play" (2 ≥ 2), mở store listing.', d)["verdict"] == "FAIL"
    assert assert_rating.cham('Event rating_placement_viewed, placement_name = "result".', d)["verdict"] == "PASS"
    assert assert_rating.cham("Câu không liên quan.", d) is None
    assert assert_rating.cham("Mở màn Feedback.", {"steps": []}) is None


def test_cham_nut_x_theo_moc():
    gen = {"viec": "gen", "popup": True, "su_kien": [],
           "do_x": {"khung": 20, "x_hien_s": 2.9, "x_chua_hien_luc_s": 2.65, "khung_dau_s": 0.3}}
    d = _drive(gen)
    assert assert_rating.cham("X chưa hiện ở mốc 2 giây.", d)["verdict"] == "PASS"
    assert assert_rating.cham("X hiện sau 3 giây.", d)["verdict"] == "PASS"
    assert assert_rating.cham("Button X hiện sau 2 giây.", d)["verdict"] == "FAIL"
    assert assert_rating.cham("Button X hiện ngay cùng lúc popup.", d)["verdict"] == "FAIL"


def test_cham_thoat_va_shortcut_khi_tat_rating():
    thoat = {"viec": "thoat", "popup": False, "con_trong_app": False, "pkg": "launcher", "man": "Nexus", "su_kien": []}
    sc = {"viec": "shortcut", "shortcuts": ["Uninstall"], "co_rating": False, "su_kien": []}
    d = _drive(thoat, sc)
    assert assert_rating.cham("Bước 3 app thoát bình thường.", d)["verdict"] == "PASS"
    assert assert_rating.cham("Shortcut không có option Rating.", d)["verdict"] == "PASS"
    assert assert_rating.cham("Home, result, exit_click: popup không hiện, không có event rating_placement_viewed.",
                              d)["verdict"] == "PASS"


def test_phan_tich_x_co_tu_khung_dau():
    co = bytes([200] * 400)
    kq = rating_may.phan_tich([(100.3, co), (100.6, co), (101.0, co)], 100.0)
    assert kq["co_tu_khung_dau"] and kq["x_hien_s"] == 0.3
    d = _drive({"viec": "thoat", "popup": True, "su_kien": [], "do_x": {**kq}})
    assert assert_rating.cham("Button X hiện ngay cùng lúc popup.", d)["verdict"] == "PASS"


def test_cham_popup_theo_vi_tri_chi_bat_result():
    ev = [{"t": 1.0, "ten": "rating_placement_viewed", "params": {"placement_name": "result"}}]
    gen = {"viec": "gen", "popup": True, "man": "ResultActivity", "su_kien": ev}
    thoat = {"viec": "thoat", "popup": False, "con_trong_app": False, "pkg": "l", "man": "Nexus", "su_kien": []}
    d = _drive(gen, thoat)
    assert assert_rating.cham("Home không hiện popup.", d)["verdict"] == "PASS"
    assert assert_rating.cham('Result hiện popup; event placement_name = "result".', d)["verdict"] == "PASS"
    assert assert_rating.cham("Exit_click không hiện popup, app thoát bình thường.", d)["verdict"] == "PASS"
