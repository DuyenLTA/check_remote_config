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


def test_back_ve_result_app_compose_nhan_theo_tieu_de():
    # AIP893: Result nam trong MainActivity -> ten activity khong co chu "result", phai nhan bang tieu de man
    main = "AIP893AIPhotoVideoMakerMainActivity"
    sao = {"viec": "sao", "sao": 1, "nut": "RATE", "nut_enabled": True, "da_bam": True, "truoc": main,
           "pkg_sau": "p", "man_sau": "VslRatingFeedbackActivity", "google_play": False, "su_kien": []}
    ve_result = {"viec": "back", "man": main, "pkg": "p", "trong_app": True, "su_kien": [],
                 "chu": ["Result", "Back to Home", "Download"]}
    ve_home = {**ve_result, "chu": ["AI Studio", "Welcome,\nLet's create with AI!"]}
    assert assert_rating.cham("Back về màn result.", _drive(sao, ve_result))["verdict"] == "PASS"
    assert assert_rating.cham("Back về màn result.", _drive(sao, ve_home))["verdict"] == "FAIL"


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


def test_cong_thuc_app_compose_chay_buoc_theo_chu():
    """App Compose (AIP893): cong thuc dung buoc cua iaa_lai (cho / ve_chu / xem_ads_chu) -> chay_ds phai hieu."""
    import asyncio
    pkg = "com.aiphotogenerator.aivideomaker.photoslideshow"
    ds = rating_cong_thuc.cong_thuc(pkg, "anh")
    assert ds and any("xem_ads_chu" in b for b in ds) and any("ve_chu" in b for b in ds)
    assert rating_cong_thuc.cong_thuc(pkg, "video")
    log: list[str] = []
    assert asyncio.run(rating_cong_thuc.chay_ds(None, "s", pkg, [{"cho": 0}, {"back": 0}], log))
    assert log == ["chờ 0s", "BACK ×0"]


def test_back_con_o_google_play_khong_tinh_la_ve_home():
    """Google Play co activity 'MainActivityPrivate': BACK van o Play thi 'Back ve Home/Splash' la FAIL."""
    sao = {"viec": "sao", "sao": 5, "nut": "Rate on Google Play", "nut_enabled": True, "da_bam": True,
           "truoc": "MainActivity", "pkg_sau": "com.android.vending", "man_sau": "TransparentMainActivityPrivate",
           "google_play": True, "su_kien": []}
    o_play = {"viec": "back", "man": "MainActivityPrivate", "pkg": "com.android.vending", "trong_app": False,
              "su_kien": []}
    assert assert_rating.cham("Back về màn Home.", _drive(sao, o_play))["verdict"] == "FAIL"
    ve_app = dict(o_play, man="MainActivity", pkg="p", trong_app=True)
    assert assert_rating.cham("Back về màn Home.", _drive(sao, ve_app))["verdict"] == "PASS"


def test_ve_home_app_compose_back_tu_result_khong_back_o_home(monkeypatch):
    # AIP893: Result va Home chung MainActivity -> buoc "thoat app" phai BACK tu Result ve Home truoc, nhung o Home
    # (hoac khong chac la Result) thi KHONG BACK (BACK o Home = thoat app).
    import asyncio
    pkg = "com.aiphotogenerator.aivideomaker.photoslideshow"
    man = {"chu": "Result"}
    backs = []

    async def focus(client, serial):
        return pkg, f"{pkg}.AIP893AIPhotoVideoMakerMainActivity"

    async def dump(client, serial):
        return (f'<hierarchy><node package="{pkg}" class="android.widget.TextView" text="{man["chu"]}" '
                f'content-desc="" bounds="[0,0][100,100]"/></hierarchy>')

    class Client:
        async def shell(self, serial, *args):
            backs.append(args)
            man["chu"] = "Text to Image Generate"

    async def ngu(*_):
        return None

    monkeypatch.setattr(act_rating.device_app, "focus", focus)
    monkeypatch.setattr(act_rating.ui_dump, "dump", dump)
    monkeypatch.setattr(act_rating.asyncio, "sleep", ngu)
    assert len(asyncio.run(act_rating._ve_home(Client(), "s", pkg))) == 1   # Result -> 1 BACK -> Home
    backs.clear()
    man["chu"] = "Today's Check-In"                                        # popup che, khong chac Result
    assert asyncio.run(act_rating._ve_home(Client(), "s", pkg)) == [] and backs == []


def test_x_sau_n_giay_khung_dau_da_co_x_khong_fail_gia():
    # Chup bat dau tre (khung dau 12.9s sau popup da co X) -> khong ket luan "X hien 12.9s"; sau khi tool da tu do lai
    # ma van tre thi FAIL kem so lan do (khong tra NEEDS_HUMAN)
    gen = {"viec": "gen", "popup": True, "man": "M", "su_kien": [],
           "do_x": {"khung": 20, "x_hien_s": 12.94, "x_chua_hien_luc_s": None, "co_tu_khung_dau": True}}
    kq = assert_rating.cham("Button X hiện sau 2 giây.", _drive(gen))
    assert kq["verdict"] == "FAIL" and "đo 1 lần" in kq["reason"] and kq["da_thu_lai"]
    gen["do_lai"] = 2
    assert "đo 3 lần" in assert_rating.cham("Button X hiện sau 2 giây.", _drive(gen))["reason"]
    gen.pop("do_lai")
    gen["do_x"] = {"khung": 20, "x_hien_s": 2.1, "x_chua_hien_luc_s": 1.6}
    assert assert_rating.cham("Button X hiện sau 2 giây.", _drive(gen))["verdict"] == "PASS"


def test_khong_con_needs_human_o_tab_rating():
    # Ba nhanh truoc day tra NEEDS_HUMAN: buoc dung, khong co khung chup, ho khung o moc N -> gio la FAIL co ly do
    dung = {"viec": "gen", "dung": "gen anh không tới được result: hết giờ", "do_lai": 2, "su_kien": []}
    kq = assert_rating.cham("Popup rating hiển thị.", _drive(dung))
    assert kq["verdict"] == "FAIL" and "3 lần" in kq["reason"] and kq["da_thu_lai"]
    khong_khung = {"viec": "gen", "popup": True, "man": "M", "su_kien": [], "do_x": {}, "do_lai": 2}
    kq = assert_rating.cham("Button X hiện sau 2 giây.", _drive(khong_khung))
    assert kq["verdict"] == "FAIL" and "đo 3 lần" in kq["reason"]
    ho = {"viec": "gen", "popup": True, "man": "M", "su_kien": [],
          "do_x": {"khung": 20, "x_hien_s": 3.4, "x_chua_hien_luc_s": 1.2}}
    kq = assert_rating.cham("Button X chưa hiện ở mốc 2 giây.", _drive(ho))
    assert kq["verdict"] == "FAIL" and "mốc 2s" in kq["reason"]


def test_fail_da_thu_lai_khong_bi_ha_ve_needs_human():
    from rcr import assert_check
    dong = [{"verdict": "FAIL", "reason": "làm bước rating 3 lần, tool vẫn dừng: không thấy popup", "da_thu_lai": True},
            {"verdict": "FAIL", "reason": "không thấy 'Rate' trên màn nào"}]
    ra = assert_check._ha_fail_khi_buoc_dung(dong, {"status": "NEEDS_HUMAN", "stopped_at": 2})
    assert [r["verdict"] for r in ra] == ["FAIL", "NEEDS_HUMAN"]


def _lam_gia(monkeypatch, ket_lan):
    """Chay act_rating.lam voi _lam_an_toan tra lan luot `ket_lan`; tra (record, so lan lam, so lan dong popup)."""
    import asyncio
    goi = {"lam": 0, "dong": 0}

    async def lam(*_):
        goi["lam"] += 1
        return ket_lan[min(goi["lam"], len(ket_lan)) - 1]

    async def dong(*_):
        goi["dong"] += 1

    async def moc(*_):
        return "m"

    async def su_kien(*_):
        return []

    monkeypatch.setattr(act_rating, "_lam_an_toan", lam)
    monkeypatch.setattr(act_rating, "_dong_popup_rating", dong)
    monkeypatch.setattr(act_rating.log_moc, "bay_gio", moc)
    monkeypatch.setattr(act_rating.rating_may, "su_kien", su_kien)
    record = {}
    action = act_rating.Rating("gen", "gen", loai="anh")
    asyncio.run(act_rating.lam(None, "s", action, record, {"package": "p"}))
    return record, goi["lam"], goi["dong"]


def test_chup_tre_thi_tu_lam_lai_va_do_lai(monkeypatch):
    # AIP893 17/11/2026: khung dau 12.9s sau popup da co X -> dong popup, gen lai, lan sau do ra 2.0s
    tre = {"popup": True, "do_x": {"khung": 20, "x_hien_s": 12.94, "co_tu_khung_dau": True}}
    dung = {"popup": True, "do_x": {"khung": 20, "x_hien_s": 2.0, "x_chua_hien_luc_s": 1.6}}
    record, lam, dong = _lam_gia(monkeypatch, [tre, dung])
    assert (lam, dong) == (2, 1)
    assert record["rating"]["do_x"]["x_hien_s"] == 2.0 and record["rating"]["do_lai"] == 1


def test_buoc_dung_thi_tu_lam_lai_toi_da_hai_lan(monkeypatch):
    dung = {"dung": "gen anh không tới được result: hết giờ"}
    record, lam, _ = _lam_gia(monkeypatch, [dung])
    assert lam == 3 and record["rating"]["do_lai"] == 2 and record["dung_lai"]


def test_thieu_cong_thuc_thi_khong_lam_lai(monkeypatch):
    record, lam, _ = _lam_gia(monkeypatch, [{"dung": "app chưa có công thức gen anh trong data/rating_gen.yaml"}])
    assert lam == 1 and record["rating"]["do_lai"] == 0


def test_do_duoc_ngay_thi_khong_lam_lai(monkeypatch):
    ok = {"popup": True, "do_x": {"khung": 20, "x_hien_s": 0.3, "co_tu_khung_dau": True}}
    _, lam, dong = _lam_gia(monkeypatch, [ok])
    assert (lam, dong) == (1, 0)


def test_buoc_nhap_feedback_dich_thanh_go_chu():
    # AIP893 R02-02 17/11/2026: buoc nay tung ra needs_human -> Submit khong bat, R02-03 / R02-04 dung theo
    a = act_rating.resolve('Nhập "Test feedback QA <timestamp>".', [])
    assert a.viec == "nhap" and a.chu == "Test feedback QA <timestamp>"
    assert "<timestamp>" not in act_rating._chu_go(a.chu) and act_rating._chu_go(a.chu).startswith("Test feedback QA 20")


def test_nhap_go_vao_o_edittext_va_dong_ban_phim(monkeypatch):
    import asyncio
    pkg = "p"
    o = {"chu": ""}

    def xml():
        return (f'<hierarchy><node package="{pkg}" class="android.widget.EditText" text="{o["chu"]}" '
                f'content-desc="" clickable="true" enabled="true" bounds="[40,600][1040,900]"/></hierarchy>')

    async def dump(client, serial):
        return xml()

    async def tap(client, serial, x, y):
        o["tap"] = (x, y)

    async def focus(client, serial):
        return pkg, f"{pkg}.VslRatingFeedbackActivity"

    class Client:
        lenh = []

        async def shell(self, serial, *args):
            self.lenh.append(args)
            if args[:2] == ("input", "text"):
                o["chu"] = args[2].strip("'").replace("%s", " ")
            if args[:2] == ("dumpsys", "input_method"):
                return "mInputShown=true", "", 0
            return "", "", 0

    async def ngu(*_):
        return None

    monkeypatch.setattr(act_rating.ui_dump, "dump", dump)
    monkeypatch.setattr(act_rating.device_app, "tap", tap)
    monkeypatch.setattr(act_rating.device_app, "focus", focus)
    monkeypatch.setattr(act_rating.asyncio, "sleep", ngu)
    c = Client()
    ket = asyncio.run(act_rating._nhap(c, "s", pkg, "Test feedback QA"))
    assert ket["da_go"] and o["chu"] == "Test feedback QA" and o["tap"] == (540, 750)
    assert ("input", "keyevent", "KEYCODE_BACK") in c.lenh
