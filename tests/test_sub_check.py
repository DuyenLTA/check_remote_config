"""Check sub Android: doc sheet TC, doc man (dump that tu spike 04/11/2026, AIP936 Pixel 4), doc log billing, report."""

from __future__ import annotations

import json
from pathlib import Path

from rcr import sub_doc_man as m, sub_log, sub_report, sub_tc
from rcr.ui_dump import parse_dump

FX = Path(__file__).parent / "fixtures" / "sub"


def _nodes(ten):
    return parse_dump((FX / f"{ten}.xml").read_text(encoding="utf-8"))


# --- sheet --------------------------------------------------------------------------------------
TIEU_DE = ["N°", "Feature", "Test Description", "Sub-scenario", "Precondition", "Action", "Expected Result",
           "Actual Result", "PASS/FAIL"]


def _bang():
    return [["", "Generic Test Suite"], TIEU_DE, ["▌ Purchase Flow"],
            [1.0, "Purchase Flow", "Mua gói thành công", "Weekly", "2. Tài khoản không có sub Active", "1. Mở Paywall",
             "1. Premium"],
            [2.0, None, None, "Monthly", "Tài khoản không có sub Active", "Chọn Monthly", "Premium"],
            ["▌ Subscription Lifecycle"],
            [59.0, "Subscription Lifecycle", "Resubscribe", "Trước hết kỳ", "2. Sub đã Cancel nhưng chưa hết kỳ",
             "Resubscribe", "Giữ Premium"],
            [38.0, None, "Đồng bộ", "Thiết bị khác", "Đã mua Sub Active trên thiết bị A", "Cài app trên thiết bị B",
             "Tự nhận Sub"],
            [35.0, None, "Refund", "ASO", "Gửi Order ID cho ASO", "Mở app", "Về chưa mua [Inferred — cần confirm]"],
            [32.0, None, "Grace", "Grace", "Sub Active, Play Console đã bật Grace Period.", "Chờ", "Còn Premium"],
            [], ["▶ COVERAGE REPORT"], ["Purchase Flow: 13 TC"]]


def test_doc_bang_ke_thua_nhom_va_phan_loai():
    cs = sub_tc.doc_bang(_bang())
    assert [c["so"] for c in cs] == ["1", "2", "59", "38", "35", "32"]
    assert cs[1]["nhom"] == "Purchase Flow" and cs[1]["mo_ta"] == "Mua gói thành công"
    assert [c["bat_dau"] for c in cs] == ["chua_mua", "chua_mua", "da_cancel", "active", "active", "grace"]
    assert [c["can"] for c in cs] == ["", "", "", "may_2", "nguoi", "play_console"]
    assert cs[4]["suy_doan"] and not cs[0]["suy_doan"]


def test_lich_xep_theo_trang_thai_va_loc():
    cs = sub_tc.doc_bang(_bang())
    assert [c["so"] for c in sub_tc.lich(cs)] == ["1", "2", "38", "35", "59", "32"]
    assert [c["so"] for c in sub_tc.lich(cs, {"59", "1"})] == ["1", "59"]


def test_doc_bang_thieu_cot_thi_bao():
    try:
        sub_tc.doc_bang([["N°", "Feature"], [1, "x"]])
    except ValueError as exc:
        assert "thiếu cột" in str(exc)
    else:
        raise AssertionError("phai bao thieu cot")


# --- man ------------------------------------------------------------------------------------------
def test_doc_paywall_vsl_billing():
    pw = m.doc_paywall(_nodes("paywall"))
    assert [(g["ten"], g["gia"], g["chon"]) for g in pw["goi"]] == [
        ("weekly", "₫182,000", True), ("monthly", "₫364,000", False), ("yearly", "₫2,350,000", False)]
    assert pw["continue"] == (540, 1913) and pw["ads"] == (540, 2000) and pw["dong"] == (100, 130)


def test_doc_popup_google_play_test():
    p = m.doc_popup(_nodes("popup"))
    assert p["ten_goi"] == "Weekly 6.99" and p["gia"] == "₫182,000/5 min" and p["chu_ky_phut"] == 5
    assert p["la_test"] and p["the"] == "Test card, always approves"
    assert p["subscribe"] == (540, 2052) and p["dong"] == (1002, 294) and p["doi_the"] == (540, 1151)


def test_popup_khong_phai_man_khac():
    assert m.doc_popup(_nodes("paywall")) is None
    assert m.doc_paywall(_nodes("popup")) is None


def test_doc_play_active_canceled_expired():
    a = m.doc_play(_nodes("play-active"))
    assert a["trang_thai"] == "active" and a["gio_ke_tiep"] == "2026-11-04T14:02"
    assert a["the"] == "Test card, always approves" and {"cancel", "update", "pause"} <= set(a["nut"])
    c = m.doc_play(_nodes("play-canceled"))
    assert c["trang_thai"] == "canceled" and c["het_luc"] == "2026-11-04T14:02" and "resubscribe" in c["nut"]
    e = m.doc_play(_nodes("play-danh-sach-expired"))
    assert e["trang_thai"] == "expired"           # danh sach: khong con goi active, goi app nam o Expired


def test_nut_resubscribe_tren_sheet_xac_nhan():
    assert m.nut_xac_nhan_resubscribe(_nodes("resubscribe-xac-nhan")) == (783, 2052)


def test_deep_link_khong_thay_goi_la_none():
    assert m.doc_play(_nodes("play-khong-thay-goi"))["trang_thai"] == "none"


def test_nut_cancel_la_nut_duoi_khong_phai_tieu_de():
    # Man khao sat co tieu de "Cancel subscription" [192,131][688,203] va nut [558,1980][1008,2124]
    assert m.nut_xac_nhan_cancel(_nodes("cancel-khao-sat")) == (783, 2052)
    assert m.nut_xac_nhan_cancel(_nodes("paywall")) is None


# --- log billing ------------------------------------------------------------------------------------
LOG_MUA = """\
11-04 13:57:52.595 E/PurchaseEG(19986): onPurchasesUpdated code: 0
11-04 13:57:52.595 I/AperoAppsflyer(19986): onTrackRevenuePurchase --- idPurchase: aip936.weekly.699
11-04 13:57:52.600 D/NativeAdPreload(19986): purchase detected, releasing every preloaded native ad
11-04 13:57:52.600 D/BannerAdPreload(19986): purchase detected, releasing every preloaded banner ad
11-04 13:57:53.548 D/PurchaseEG(19986): onAcknowledgePurchaseResponse: Server error, please try again.
11-04 13:57:53.549 D/PurchaseEG(19986): onAcknowledgePurchaseResponse: """.splitlines()
LOG_KHOI_DONG = """\
11-04 14:04:06.267 D/PurchaseEG(23887): onBillingSetupFinished: aip936.weekly.699
11-04 14:04:06.267 D/PurchaseEG(23887): onBillingSetupFinished: aip936.monthly.1399
11-04 14:04:06.300 D/PurchaseEG(23887): verifyPurchased INAPP  code:0 ===   size:0
11-04 14:04:06.301 D/PurchaseEG(23887): verifyPurchased SUBS  code:0 ===   size:0""".splitlines()


def test_log_mua_va_khoi_dong():
    d = sub_log.doc(LOG_MUA)
    assert d["premium"] is True and d["mua"] == ["OK"] and d["sku_mua"] == "aip936.weekly.699"
    assert d["ack_loi"] == ["Server error, please try again."] and d["nha_ads"] == ["banner", "native"]
    k = sub_log.doc(LOG_KHOI_DONG)
    assert k["premium"] is False and k["sku_cau_hinh"] == ["aip936.weekly.699", "aip936.monthly.1399"]
    assert sub_log.sku_theo_goi(k["sku_cau_hinh"], "Monthly") == "aip936.monthly.1399"
    assert sub_log.doc(["onPurchasesUpdated code: 1"])["mua"] == ["USER_CANCELED"]
    assert sub_log.doc([])["premium"] is None
    hong = sub_log.doc(["D/PurchaseEG(1): verifyPurchased SUBS  code:-1 ===   size:0"])
    assert hong["premium"] is None and hong["verify_loi"] == ["SERVICE_DISCONNECTED"]


# --- report ------------------------------------------------------------------------------------------
def test_report_dem_va_escape(tmp_path):
    luot = {"package": "p.x", "app": "Homova", "version": "1.9.0 (11)", "may": "Pixel 4",
            "cases": [{"so": "1", "nhom": "Purchase Flow", "kich_ban": "Weekly", "expected": "Premium <ngay>",
                       "verdict": "PASS", "thuc_te": "ok"},
                      {"so": "63", "nhom": "Lifecycle", "kich_ban": "Hết hạn nền", "verdict": "FAIL", "thuc_te": "x"},
                      {"so": "38", "nhom": "Lifecycle", "verdict": "CAN_TEST_TAY", "anh": [str(tmp_path / "khong-co.png")]}]}
    f = tmp_path / "l.json"
    f.write_text(json.dumps(luot, ensure_ascii=False), encoding="utf-8")
    chu = sub_report.ghi(f, tmp_path / "r.html").read_text(encoding="utf-8")
    assert "Premium &lt;ngay&gt;" in chu and "Cần test tay" in chu and chu.count('class="case') == 3
    assert '<b class="ok">1</b>Đạt' in chu and '<b class="bad">1</b>Lỗi' in chu


# --- bot: prompt + phan loai case sub ------------------------------------------------------------------
def test_prompt_sub_va_verify_sub():
    from rcr import bot_chay_claude as b
    _, p = b.lenh("p.home", "S1", sub_version="1.9.0 (11)")
    assert p.startswith('/sub-check p.home --serial S1 --version "1.9.0 (11)"') and "KET_QUA" in p
    _, p = b.lenh("p.home", "S1", ["sub#63", "sub#1"])
    assert p.startswith("/sub-check p.home --serial S1 --case 63,1")
    for xau in ("1.9.0; rm -rf", "1.9.0"):
        try:
            b.lenh("p.home", "S1", sub_version=xau)
        except ValueError:
            continue
        raise AssertionError(xau)


def test_loai_case_sub_va_tach_nhom_khi_lan():
    from rcr import bot_verify_jira as v
    assert v.loai_case("sub#63") == "sub" and v.loai_case("3.6.1#SDK361-RG01-04") == "tc"
    uv = [{"key": f"A-{i}", "case": c, "loai_ban_goc": "release"} for i, c in
          enumerate(["sub#1", "sub#63", "3.6.1#SDK361-RG01-04"])]
    chay, bo = v.phan_loai(uv, "release")
    assert [u["case"] for u in chay] == ["sub#1", "sub#63"] and bo[0][0]["case"] == "3.6.1#SDK361-RG01-04"


def test_luot_sub_cua_bot_khong_kiem_testvsl_va_goi_sub_check(tmp_path, monkeypatch):
    import asyncio
    from types import SimpleNamespace

    from rcr import bot_hang_doi as h, bot_kiem_testvsl as k
    from rcr import discord_bot as d

    async def khong_duoc(*a):
        raise AssertionError("lượt sub không kiểm testvsl")
    monkeypatch.setattr(k, "loi_testvsl", khong_duoc)
    monkeypatch.setattr(d.bot_cong_viec, "cai", lambda *a: {"ok": True})
    goi = []
    monkeypatch.setattr(d.bot_chay_claude, "chay", lambda *a: goi.append(a) or {"trang_thai": "XONG"})
    bot = object.__new__(d.BuildBot)
    bot.q, bot.ban, bot.duyet = h.HangDoi(tmp_path / "q.json"), {}, {7}
    msg = SimpleNamespace(id=5, edits=[], replies=[])

    async def edit(**kw):
        msg.edits.append(kw)

    async def reply(chu, **kw):
        msg.replies.append(chu)
    msg.edit, msg.reply = edit, reply
    job = {"msg_id": 5, "ma": "AIP936", "ten": "", "version": "1.9.0 (11)", "package": "p.home",
           "loai_ban": "release", "loai_job": "sub"}
    bot.q.jobs = [job]
    assert asyncio.run(bot._cai_va_chay(job, msg, "S1", "Pixel")) is True
    assert goi[0][3] == d.bot_chay_claude.TIMEOUT_SUB and goi[0][-1] == "1.9.0 (11)" and job["kq"]["trang_thai"] == "XONG"
    assert "/sub-check" in msg.edits[-1]["content"]


def test_ghi_profile_gop_vao_ban_cu(tmp_path, monkeypatch):
    from rcr import sub_thao_tac as t
    monkeypatch.setattr(t, "PROFILE_DIR", tmp_path)
    t.ghi_profile("p.x", {"duong_vao_paywall": [{"desc": "Premium"}], "quyen_loi": ["a"]})
    t.ghi_profile("p.x", {"quan_ly_sub": [{"desc": "Settings"}]})          # ghi tung phan khong mat phan khac
    assert t.doc_profile("p.x") == {"duong_vao_paywall": [{"desc": "Premium"}], "quyen_loi": ["a"],
                                    "quan_ly_sub": [{"desc": "Settings"}], "package": "p.x"}
