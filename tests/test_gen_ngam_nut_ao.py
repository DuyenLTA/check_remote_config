"""Nut NAF (khong chu / desc) duoc khai `nut_ao` trong gen_ngam_cong_thuc.yaml -> `nhin` them node ao."""
from rcr import gen_ngam_may as may
from rcr.ui_dump import parse_dump

XML_HOME = ('<hierarchy><node text="Explore styles" resource-id="" class="android.widget.TextView" package="p" '
            'content-desc="" clickable="false" bounds="[44,318][1036,384]" />'
            '<node NAF="true" text="" resource-id="" class="android.view.View" package="p" content-desc="" '
            'clickable="true" bounds="[807,139][923,271]" /></hierarchy>')
XML_KHAC = ('<hierarchy><node text="Result" resource-id="" class="android.widget.TextView" package="p" '
            'content-desc="" clickable="false" bounds="[154,190][580,248]" /></hierarchy>')
NUT = {"desc": "History", "khung": [807, 139, 923, 271], "khi_chu": "^Explore styles$"}


def _man(xml):
    return may.Man(0.0, "p", "MainActivity", parse_dump(xml))


def test_them_nut_history_ao_khi_o_home(monkeypatch):
    monkeypatch.setattr(may, "NUT_AO", [NUT])
    m = _man(XML_HOME)
    may.them_nut_ao(m, "p")
    nut = m.tim("^History$")
    assert nut is not None and nut.bounds.center == (865, 205)
    may.them_nut_ao(m, "p")                                   # goi lai khong nhan doi
    assert len(m.tat_ca("^History$")) == 1


def test_khong_them_khi_man_khong_co_chu_nhan_dien(monkeypatch):
    monkeypatch.setattr(may, "NUT_AO", [NUT])
    m = _man(XML_KHAC)
    may.them_nut_ao(m, "p")
    assert m.tim("^History$") is None


def test_khong_khai_nut_ao_thi_giu_nguyen(monkeypatch):
    monkeypatch.setattr(may, "NUT_AO", [])
    m = _man(XML_HOME)
    n = len(m.nodes)
    may.them_nut_ao(m, "p")
    assert len(m.nodes) == n
