"""Tab TC daily checkin tu lai + tu cham (act_checkin / checkin_may / assert_checkin) - phan thuan, khong goi may."""

from rcr import act_checkin, act_resolver, assert_checkin, checkin_may, rating_cong_thuc
from rcr.ui_dump import parse_dump

P = 'package="p" class="android.view.View"'
CHECKIN = f"""<hierarchy><node {P} text="" bounds="[0,0][1080,2400]">
<node {P} content-desc="Close" text="" bounds="[903,1113][1047,1257]"/>
<node {P} text="QA - Today's Check-In" bounds="[60,1218][1020,1289]"/>
<node {P} text="QA - Banner check-in" bounds="[114,1464][617,1523]"/>
<node {P} text="Day 1" bounds="[130,1847][205,1882]"/><node {P} text="Day 2" bounds="[255,1847][330,1882]"/>
<node {P} text="Complete your daily check-in" bounds="[60,2002][1020,2100]"/>
<node {P} text="Check-in" clickable="true" bounds="[445,2228][636,2285]"/>
</node></hierarchy>"""
UNLOCKED = f"""<hierarchy><node {P} content-desc="Close" text="" bounds="[903,1430][1047,1574]"/>
<node {P} text="Unlocked Successfully!" bounds="[60,1535][1020,1606]"/>
<node {P} text="You've unlocked a free generation!" bounds="[60,2218][1020,2316]"/></hierarchy>"""
WIDGET = f"""<hierarchy><node {P} content-desc="Close" text="" bounds="[904,614][970,680]"/>
<node {P} text="Add Widget" bounds="[333,641][747,733]"/><node {P} text="Add Widget Now" bounds="[404,1675][761,1735]"/>
</hierarchy>"""
SHEET = f"""<hierarchy><node {P} content-desc="Close sheet" text="" bounds="[0,0][1080,774]"/>
<node {P} text="Free Generate (2 left)" clickable="true" bounds="[335,2039][746,2090]"/>
<node {P} text="Watch Ads (0/2)" clickable="true" bounds="[337,2207][647,2258]"/></hierarchy>"""


def test_doc_man_checkin_unlocked_widget():
    c = checkin_may.doc(parse_dump(CHECKIN))["checkin"]
    assert (c["title"], c["banner"], c["description"], c["cta"]) == (
        "QA - Today's Check-In", "QA - Banner check-in", "Complete your daily check-in", "Check-in")
    u = checkin_may.doc(parse_dump(UNLOCKED))
    assert u["unlocked"]["title"] == "Unlocked Successfully!" and not u["checkin"]
    w = checkin_may.doc(parse_dump(WIDGET))
    assert w["widget"] and not w["checkin"] and not w["unlocked"]


def test_sheet_chi_ket_luan_khi_tai_xong():
    s = checkin_may.sheet(parse_dump(SHEET), "^Watch Ads")
    assert s["free"] == "Free Generate (2 left)" and s["left"] == 2 and s["enabled"]
    dang_tai = SHEET.replace("Watch Ads (0/2)", "Unlock Now").replace("Free Generate (2 left)", "x")
    assert checkin_may.sheet(parse_dump(dang_tai), "^Watch Ads") is None


def test_resolver_cau_chung_chi_doi_khi_dang_o_tab_checkin():
    k = lambda s, n=(): act_resolver.resolve(s, list(n)).summary["kind"]
    assert k("Kill app, mở lại, vào Home.") == "kill"
    tk = act_checkin.CFG.set({"show_checkin_screen": "true"})
    try:
        assert k("Kill app, mở lại, vào Home.") == "checkin_kill"
        assert k("Mở app vào Home, bấm Check-in, đóng Unlocked.") == "checkin_full"   # khong bo im ve sau
        assert k("Bấm X.", parse_dump(CHECKIN)) == "checkin_x"
        assert act_resolver.resolve("Gen free với template B, quay lại.", []).thu == 2
    finally:
        act_checkin.CFG.reset(tk)


def test_tim_duoi_chon_template_thu_n():
    xml = f"""<hierarchy><node {P} text="AI Try On Outfits" bounds="[48,1357][408,1415]"/>
<node {P} clickable="true" bounds="[384,1439][684,1979]"/><node {P} clickable="true" bounds="[48,1439][348,1979]"/>
<node {P} clickable="true" bounds="[1056,1439][1080,1979]"/></hierarchy>"""
    n = parse_dump(xml)
    assert [rating_cong_thuc.tim_duoi(n, "^AI Try On Outfits$", t).bounds.left for t in (1, 2, 3)] == [48, 384, 1056]


def _drive(*recs):
    return {"steps": [{"checkin": r} for r in recs]}


CFG = {"checkin_sdk_config": '{"checkin":{"title":"QA - Today\'s Check-In","banner":"QA - Banner check-in"}}',
       "checkin_sdk_design_system": '{"title_text_color":"#FF0000","description_text_color":"#00FF00"}'}


def test_cham_r01_01_man_text_mau_event():
    man = checkin_may.doc(parse_dump(CHECKIN))["checkin"]
    mau = [{"bounds": man["khung"]["title"], "dem": {"#FF0000": [900, 0], "#00FF00": [0, 0]}},
           {"bounds": man["khung"]["description"], "dem": {"#FF0000": [0, 0], "#00FF00": [500, 2]}}]
    ev = [{"t": 1.0, "ten": "daily_checkin_screen_view", "params": {}}]
    d = _drive({"viec": "quan_sat", "widget": True, "checkin": man, "mau": mau, "su_kien": ev})
    c = lambda s: assert_checkin.cham(s, d, CFG)["verdict"]
    assert c("Màn Daily Checkin hiện sau Add widget.") == "PASS"
    assert c("Button X hiện ngay khi màn xuất hiện.") == "PASS"
    assert c('Title "QA - Today\'s Check-In", banner "QA - Banner check-in" theo khối checkin của checkin_sdk_config; '
             'các text khác đúng giá trị trong JSON.') == "PASS"
    assert c("Màu title #FF0000, description #00FF00 theo checkin_sdk_design_system; các màu khác đúng giá trị trong "
             "JSON.") == "PASS"
    assert c("Màu title #00FF00.") == "FAIL"
    assert c("Event daily_checkin_screen_view fire 1 lần.") == "PASS"
    assert assert_checkin.cham("Câu không liên quan.", d, CFG) is None


def test_cham_free_generate_gen_va_khong_hien_lai():
    s1 = {"free": "Free Generate (2 left)", "left": 2, "enabled": True}
    s2 = {"free": "Free Generate (1 left)", "left": 1, "enabled": True}
    het = {"free": None, "left": None, "enabled": False}
    g = {"bam": True, "xong": True, "moi_nhat": "1 minute ago"}
    d = _drive({"viec": "gen_tpl", "sheet": s1, "gen": g, "su_kien": []},
               {"viec": "gen_tpl", "sheet": s2, "gen": g, "su_kien": []},
               {"viec": "vao_unlock", "sheet": het, "su_kien": []},
               {"viec": "ve_home", "lan": [{"widget": False, "checkin": None}], "su_kien": []},
               {"viec": "kill", "lan": [{"widget": True, "checkin": None}], "su_kien": []})
    c = lambda s: assert_checkin.cham(s, d, {})["verdict"]
    assert c("Cả 2 lần gen thành công.") == "PASS"
    assert c("Sau lần 1 button Free Generate vẫn hiện (còn 1 lượt).") == "PASS"
    assert c("Button Free Generate ẩn (đã dùng 2/2 lượt trong ngày).") == "PASS"
    assert c("Daily Checkin không hiện lại ở cả 2 bước.") == "PASS"
    assert c("Button Free Generate hiện, enabled.") == "FAIL"


def test_buoc_dung_giua_chung_thi_khong_cham_gia():
    d = _drive({"viec": "vao_unlock", "dung": "app chưa có công thức", "su_kien": []})
    assert assert_checkin.cham("Button Free Generate hiện, enabled.", d, {})["verdict"] == "NEEDS_HUMAN"
