"""Hop thu bug: luot chay tay tha file -> bot gan bug vao tin build + dang menu tick o kenh QA."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

from rcr import bot_hang_doi
from rcr import bot_hop_thu_bug as h

BUG = {"case": "3.5.4#SDK354-R01-06", "tieu_de": "OB1 sai ad", "expected": "301 hien", "thuc_te": "202 hien",
       "muc_do": "High"}


def tin(msg_id, package="pkg.a", version="1.0.0 (1)"):
    return {"msg_id": msg_id, "ma": "AIP1", "ten": "App", "package": package, "version": version}


class _Qa:
    def __init__(self):
        self.tra_loi = []

    async def reply(self, noi_dung, files=None, view=None):
        self.tra_loi.append((noi_dung, view))


def _bot(tmp_path, *cac_tin):
    q = bot_hang_doi.HangDoi(tmp_path / "q.json")
    for c in cac_tin:
        q.nho_tin(c)
    qa = _Qa()

    async def _tin_qa(msg_id):
        qa.msg_id = msg_id
        return qa
    return SimpleNamespace(q=q, out=tmp_path, _tin_qa=_tin_qa), qa


def test_tim_tin_moi_nhat_theo_package_va_version():
    t = {"1": tin(1), "5": tin(5), "3": tin(3, version="2.0.0 (2)"), "9": tin(9, "pkg.b")}
    assert h.tim_tin(t, "pkg.a")["msg_id"] == 5
    assert h.tim_tin(t, "pkg.a", "2.0.0 (2)")["msg_id"] == 3
    assert h.tim_tin(t, "pkg.c") is None


def test_file_hop_thu_dang_menu_va_luu_bug_vao_tin(tmp_path):
    bot, qa = _bot(tmp_path, tin(7), tin(8, "pkg.b"))
    f = h.tha_vao_hop(tmp_path, [BUG], "https://claude.ai/artifact/x", package="pkg.a", version="1.0.0 (1)")
    kq = asyncio.run(h.xu_ly_file(bot, f))
    assert "1 bug" in kq and not f.exists()
    assert qa.msg_id == 7 and "1 bug cần review" in qa.tra_loi[0][0] and qa.tra_loi[0][1] is not None
    c = bot_hang_doi.HangDoi(tmp_path / "q.json").tin_cua(7)       # bot khoi dong lai van tick duoc
    assert c["bugs"][0]["case"] == BUG["case"] and c["bug_chon"] == [] and c["jira"] is None
    assert c["link_report"] == "https://claude.ai/artifact/x"


def test_khong_thay_tin_build_thi_doi_ten_file_loi(tmp_path):
    bot, qa = _bot(tmp_path, tin(7))
    f = h.tha_vao_hop(tmp_path, [BUG], "", msg_id=999)
    kq = asyncio.run(h.xu_ly_file(bot, f))
    assert kq.startswith("loi") and not f.exists() and f.with_suffix(".loi").exists()
    assert qa.tra_loi == []


def test_cli_tu_choi_file_khong_co_bug_va_link_khong_https(tmp_path, capsys):
    rong = tmp_path / "b.json"
    rong.write_text(json.dumps([{"tieu_de": "thieu case"}]), encoding="utf-8")
    assert h.main(["--bugs", str(rong), "--package", "pkg.a", "--out", str(tmp_path)]) == 1
    tot = tmp_path / "c.json"
    tot.write_text(json.dumps([BUG]), encoding="utf-8")
    assert h.main(["--bugs", str(tot), "--package", "pkg.a", "--link", "C:/x.html", "--out", str(tmp_path)]) == 1
    assert h.main(["--bugs", str(tot), "--package", "pkg.a", "--link", "https://claude.ai/a",
                   "--out", str(tmp_path)]) == 0
    assert len(list((tmp_path / h.THU_MUC).glob("*.json"))) == 1
