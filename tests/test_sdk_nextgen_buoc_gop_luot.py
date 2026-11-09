"""Do tay checklist Next-Gen ra cung ket qua giua cac luot: buoc bat buoc, luat ngoai pham vi co dinh, Sai dinh, gop luot.

Tai hien ADA895 3.3.0 (09/11/2026): luot chieu HV-01 Sai (bam native → ad resume hien de), luot toi chi bam inter
ra Khop; KT-03/04 luot nay cham theo minSdk lib, luot kia de ngoai pham vi.
"""

from __future__ import annotations

import json
import shutil

import pytest

from rcr import cli_sdk_check, sdk_nextgen_cham, sdk_nextgen_gop_luot, sdk_nextgen_report
from rcr.models import RcError
from rcr.sdk_nextgen_buoc_do_tay import doc_buoc
from test_sdk_nextgen_cham import PKG, _thu_muc

SAI_HV01 = "bấm native Question 305 → YouTube → về app: ad resume 503_high hiện đè 18:52:14"
DU_HV01 = {"inter": "ok", "native": "ok", "banner": "khong:không có banner trong tutorial"}


def _ket(data, ma):
    return next(r for r in data["ket_qua"] if r["ma"] == ma)


KHOA = "3.3.0 (25)|aa11"


def _luot(tmp_path, ten, phien_ban="3.3.0 (25)", sha="aa11"):
    d = tmp_path / f"sdk-{PKG}-{ten}"
    d.mkdir()
    _thu_muc(d)
    bc = json.loads((d / "bang-chung.json").read_text("utf-8"))
    (d / "bang-chung.json").write_text(json.dumps({**bc, "phien_ban": phien_ban, "apk_sha256": sha}), "utf-8")
    data = sdk_nextgen_cham.cham_thu_muc(d)
    data["meta"]["cham_luc"] = ten
    return d, data


def test_khop_thieu_buoc_bi_chan_sai_mot_buoc_la_du(tmp_path):
    data = sdk_nextgen_cham.cham_thu_muc(_thu_muc(tmp_path))
    # luot toi ADA895: chi bam inter roi cham Khop -> phai bi chan vi chua thu native
    with pytest.raises(RcError, match="native"):
        sdk_nextgen_cham.cham_tay(data, "HV-01", "KHOP", "bấm inter → về app không resume", buoc={"inter": "ok"})
    with pytest.raises(RcError, match="khong:<lý do>"):
        sdk_nextgen_cham.cham_tay(data, "HV-01", "KHOP", "x", buoc={**DU_HV01, "banner": "khong:"})
    with pytest.raises(RcError, match="=sai"):
        sdk_nextgen_cham.cham_tay(data, "HV-01", "KHOP", "x", buoc={**DU_HV01, "native": "sai"})
    with pytest.raises(RcError, match="ít nhất một bước =sai"):
        sdk_nextgen_cham.cham_tay(data, "HV-01", "SAI", SAI_HV01, buoc={"inter": "ok"})
    sdk_nextgen_cham.cham_tay(data, "HV-01", "SAI", SAI_HV01, buoc={"native": "sai"})
    r = _ket(data, "HV-01")
    assert r["ket"] == "SAI" and r["buoc"][0]["id"] == "native" and "mo_ta" in r["buoc"][0]
    assert "Bước đã làm" in sdk_nextgen_report.render(data)


def test_doc_buoc_giu_dau_phay_trong_ly_do():
    assert doc_buoc(["inter=ok", "banner=khong:không có banner, chỉ native"]) == {
        "inter": "ok", "banner": "khong:không có banner, chỉ native"}
    with pytest.raises(RcError):
        doc_buoc(["inter"])


def test_minsdk_khong_duoc_ngoai_pham_vi_va_kt03_04_theo_12(tmp_path):
    data = sdk_nextgen_cham.cham_thu_muc(_thu_muc(tmp_path))
    for ma in ("1.2", "KT-03", "KT-04"):
        with pytest.raises(RcError, match="không được để ngoài phạm vi"):
            sdk_nextgen_cham.cham_tay(data, ma, "KHONG_AP_DUNG", "không có máy Android 7")
    sdk_nextgen_cham.cham_tay(data, "1.2", "KHOP", "aapt2: com.apero.moduleads minSdk=24, firstopen.sample minSdk=24",
                              buoc={"demo_lib": "ok", "demo_sdk": "ok"})
    assert {_ket(data, m)["ket"] for m in ("1.2", "KT-03", "KT-04")} == {"KHOP"}
    assert _ket(data, "KT-03")["ly_do"].startswith("Theo 1.2")


def test_sai_luot_truoc_dinh_tru_khi_chay_lai_buoc_tai_hien(tmp_path):
    d1, cu = _luot(tmp_path, "261109-183740")
    sdk_nextgen_cham.cham_tay(cu, "HV-01", "SAI", SAI_HV01, buoc={"native": "sai"})
    sdk_nextgen_cham.ghi(d1, cu)
    d2, moi = _luot(tmp_path, "261109-220529")
    moi, lay = sdk_nextgen_gop_luot.gop(moi, sdk_nextgen_gop_luot.tim(tmp_path, PKG, KHOA, tru=d2))
    assert "HV-01" in lay and _ket(moi, "HV-01")["ket"] == "SAI" and _ket(moi, "HV-01")["tu_luot"] == str(d1)
    with pytest.raises(RcError, match="đã Sai"):
        sdk_nextgen_cham.cham_tay(moi, "HV-01", "KHOP", "bấm inter → không resume", buoc=DU_HV01)
    sdk_nextgen_cham.cham_tay(moi, "HV-01", "KHOP", "bấm inter + native → không resume", buoc=DU_HV01,
                              khong_tai_hien="bấm native Question 305 ×3, đứng YouTube 6s, về app: 0 ad_show 503")
    r = _ket(moi, "HV-01")
    assert r["ket"] == "KHOP" and r["khong_tai_hien"]["sai_o"] == str(d1) and "tu_luot" not in r
    html = sdk_nextgen_report.render(moi)
    assert "Lệch giữa các lượt cùng build" in html and "chạy lại bước tái hiện" in html


def test_gop_chi_lay_khop_du_buoc_va_khong_tron_build_khac(tmp_path):
    d1, cu = _luot(tmp_path, "261109-183740")
    # do tay cu khong khai buoc (truoc luat buoc) -> khong dung lai; Khop du buoc -> dung lai
    cu = sdk_nextgen_cham.cham_tay(cu, "HV-08", "KHOP", "Home lúc Loading Ads", buoc={"home_loading": "ok"})
    r7 = _ket(cu, "EV-07")
    r7.update(ket="KHOP", ly_do="bấm inter", cham_boi="Claude đo tay 09/11/2026 18:00")
    sdk_nextgen_cham.ghi(d1, cu)
    _luot(tmp_path, "261108-100000", phien_ban="3.2.0 (24)")   # build khac: khong gop
    _luot(tmp_path, "261109-120000", sha="bb22")              # dev day lai cung version = build khac
    d2, moi = _luot(tmp_path, "261109-220529")
    luot_cu = sdk_nextgen_gop_luot.tim(tmp_path, PKG, KHOA, tru=d2)
    assert [l["thu_muc"] for l in luot_cu] == [str(d1)]
    moi, lay = sdk_nextgen_gop_luot.gop(moi, luot_cu)
    assert lay == ["HV-08"] and _ket(moi, "EV-07")["ket"] == "DO_TAY"


def test_cli_luot_moi_tu_gop_va_bao_buoc_con_thieu(tmp_path, monkeypatch):
    d1, cu = _luot(tmp_path, "261109-183740")
    sdk_nextgen_cham.cham_tay(cu, "HV-01", "SAI", SAI_HV01, buoc={"native": "sai"})
    sdk_nextgen_cham.ghi(d1, cu)
    d2 = tmp_path / f"sdk-{PKG}-261109-220529"
    shutil.copytree(d1, d2)
    (d2 / "ket-qua.json").unlink()
    args = cli_sdk_check.build_parser().parse_args(["--cham-lai", str(d2), "--out-dir", str(tmp_path),
                                                    "--gop-luot", str(d1)])
    ra = cli_sdk_check.run(args)
    data = sdk_nextgen_cham.doc(d2)
    assert _ket(data, "HV-01")["ket"] == "SAI" and "HV-01" not in ra["can_do_tay"]
    assert any(s.startswith("native:") for s in ra["can_do_tay"]["EV-07"])
    # cham lai lan nua (khong --gop-luot) van giu luot_truoc + Sai
    ra2 = cli_sdk_check.run(cli_sdk_check.build_parser().parse_args(["--cham-lai", str(d2)]))
    assert _ket(sdk_nextgen_cham.doc(d2), "HV-01")["ket"] == "SAI" and ra2["dem"]["SAI"] >= 1
    with pytest.raises(RcError):
        cli_sdk_check.run(cli_sdk_check.build_parser().parse_args(
            ["--cham-tay", str(d2), "--ma", "HV-01", "--ket", "KHOP", "--ly-do", "x",
             "--buoc", "inter=ok", "--buoc", "native=ok", "--buoc", "banner=khong:không có"]))


def test_go_sai_bang_khong_tai_hien_khong_bi_luot_sau_bat_lai(tmp_path):
    d1, a = _luot(tmp_path, "261109-183740")
    sdk_nextgen_cham.cham_tay(a, "HV-01", "SAI", SAI_HV01, buoc={"native": "sai"})
    sdk_nextgen_cham.ghi(d1, a)
    d2, b = _luot(tmp_path, "261109-220529")
    b, _ = sdk_nextgen_gop_luot.gop(b, sdk_nextgen_gop_luot.tim(tmp_path, PKG, KHOA, tru=d2))
    sdk_nextgen_cham.cham_tay(b, "HV-01", "KHOP", "không resume", buoc=DU_HV01, khong_tai_hien="bấm native ×3: 0 ad_show 503")
    sdk_nextgen_cham.ghi(d2, b)
    d3, c = _luot(tmp_path, "261110-090000")
    c, lay = sdk_nextgen_gop_luot.gop(c, sdk_nextgen_gop_luot.tim(tmp_path, PKG, KHOA, tru=d3))
    assert "HV-01" in lay and _ket(c, "HV-01")["ket"] == "KHOP" and _ket(c, "HV-01")["tu_luot"] == str(d2)
    assert sdk_nextgen_gop_luot.sai_truoc(c, "HV-01") is None
    sdk_nextgen_cham.cham_tay(c, "HV-01", "KHOP", "lại không resume", buoc=DU_HV01)   # khong doi --khong-tai-hien nua


def test_cham_12_khong_xoa_sai_rieng_cua_kt03(tmp_path):
    data = sdk_nextgen_cham.cham_thu_muc(_thu_muc(tmp_path))
    sdk_nextgen_cham.cham_tay(data, "KT-03", "SAI", "cài lên máy API 24: crash khi mở")
    with pytest.raises(RcError, match="KT-03 đã Sai"):
        sdk_nextgen_cham.cham_tay(data, "1.2", "KHOP", "minSdk=24", buoc={"demo_lib": "ok", "demo_sdk": "ok"})
    assert _ket(data, "KT-03")["ket"] == "SAI"


def test_sai_do_code_luot_cu_khong_dinh(tmp_path):
    d1, a = _luot(tmp_path, "261109-183740")
    _ket(a, "HV-01").update(ket="SAI", ly_do="code", cham_boi="code")
    sdk_nextgen_cham.ghi(d1, a)
    d2, b = _luot(tmp_path, "261109-220529")
    b, _ = sdk_nextgen_gop_luot.gop(b, sdk_nextgen_gop_luot.tim(tmp_path, PKG, KHOA, tru=d2))
    assert sdk_nextgen_gop_luot.sai_truoc(b, "HV-01") is None


def test_gop_luot_chi_thu_muc_hien_tai_bi_bo_qua(tmp_path):
    d1, a = _luot(tmp_path, "261109-183740")
    sdk_nextgen_cham.cham_tay(a, "HV-01", "SAI", SAI_HV01, buoc={"native": "sai"})
    sdk_nextgen_cham.ghi(d1, a)
    cli_sdk_check.run(cli_sdk_check.build_parser().parse_args(
        ["--cham-lai", str(d1), "--out-dir", str(tmp_path), "--gop-luot", f"{d1},{d1}/."]))
    assert not sdk_nextgen_cham.doc(d1).get("luot_truoc")
