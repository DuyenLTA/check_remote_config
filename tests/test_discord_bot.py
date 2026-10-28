"""Phan cua bot Discord khong can ket noi: nut, quyen bam."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from rcr import cau_hinh_bot
from rcr import discord_bot as d


def test_nut_mang_hanh_dong_va_msg_id():
    v = d._nut(("check", "Check", d.XANH), ("bo", "Bỏ qua", d.XAM), msg_id=42)
    assert [b.custom_id for b in v.children] == ["rcr:check:42", "rcr:bo:42"]
    assert v.timeout is None                      # bot khoi dong lai nut van bam duoc


def test_chi_nguoi_duoc_duyet_hoac_co_role_moi_bam_duoc():
    bot = object.__new__(d.BuildBot)
    bot.duyet, bot.role = {1476079991161880668}, 0
    assert bot._duoc_duyet(SimpleNamespace(id=1476079991161880668, roles=[]))
    assert not bot._duoc_duyet(SimpleNamespace(id=7, roles=[]))
    bot.role = 99
    assert bot._duoc_duyet(SimpleNamespace(id=7, roles=[SimpleNamespace(id=99)]))


def test_tin_chuyen_tiep_lay_chu_trong_snapshot():
    fwd = SimpleNamespace(content="", message_snapshots=[
        SimpleNamespace(content="Bản build AIP920 v1.6.0 (7) đã được hoàn thiện.\napply next-gen")])
    assert "AIP920 v1.6.0 (7)" in d.noi_dung(fwd)
    assert d.noi_dung(SimpleNamespace(content="abc", message_snapshots=[])) == "abc"


def test_doc_cau_hinh_tu_file_khi_khong_co_bien_moi_truong(tmp_path, monkeypatch):
    """Ubuntu chay bang systemd: khong co ~/.bashrc, cau hinh nam o ~/.config/rcr/bot.env."""
    f = tmp_path / "bot.env"
    f.write_text("# cau hinh bot\nexport DISCORD_QA_CHANNEL_ID=123\nDISCORD_DUYET_USER_IDS = '7,8'\n\n", "utf-8")
    monkeypatch.delenv("DISCORD_QA_CHANNEL_ID", raising=False)
    monkeypatch.delenv("DISCORD_DUYET_USER_IDS", raising=False)
    if cau_hinh_bot.os.name == "nt":              # registry may that co the dang co gia tri that
        monkeypatch.setattr(cau_hinh_bot.os, "name", "posix")
    assert d.env("DISCORD_QA_CHANNEL_ID", f) == "123"
    assert d.env("DISCORD_DUYET_USER_IDS", f) == "7,8"
    monkeypatch.setenv("DISCORD_QA_CHANNEL_ID", "999")   # bien moi truong thang file
    assert d.env("DISCORD_QA_CHANNEL_ID", f) == "999"
    assert d.env("KHONG_CO", tmp_path / "khong-co.env") == ""


BUGS = [{"case": "6.4.0#14", "tieu_de": "preload inter 102", "precondition": "", "buoc": "", "expected": "e",
         "thuc_te": "a", "muc_do": "High"},
        {"case": "6.4.0#44", "tieu_de": "preload 301", "precondition": "", "buoc": "", "expected": "e",
         "thuc_te": "a", "muc_do": "Medium"}]


def test_view_bug_menu_tick_nhieu_va_giu_lua_chon_khi_ve_lai():
    v = d._view_bug(BUGS, [1], msg_id=42)
    menu, *nut = v.children
    assert menu.custom_id == "rcr:chon:42" and menu.min_values == 0 and menu.max_values == 2
    assert [o.default for o in menu.options] == [False, True]
    assert [b.custom_id for b in nut] == ["rcr:jira:42", "rcr:khongbug:42"] and v.timeout is None


class _Q:
    def __init__(self):
        self.luu = []

    def nho_tin(self, c):
        self.luu.append(dict(c))


class _It:
    """Interaction gia: ghi lai bot da tra loi gi."""
    def __init__(self, values=None):
        self.data = {"values": values or []}
        self.user = SimpleNamespace(mention="@qa")
        self.goi = []
        self.response = SimpleNamespace(edit_message=self._ghi("edit"), send_message=self._ghi("send"))
        self.message = SimpleNamespace(edit=self._ghi("msg_edit"), reply=self._ghi("reply"))

    def _ghi(self, ten):
        async def f(*a, **k):
            self.goi.append((ten, a, k))
        return f


def _bot(reviewer="qa.lead"):
    bot = object.__new__(d.BuildBot)
    bot.q, bot.reviewer, bot.dang_log = _Q(), reviewer, set()
    return bot


def _c():
    return {"msg_id": 42, "ma": "AIP920", "ten": "Lingix", "version": "1.5.0 (3)", "package": "pkg.a",
            "bugs": BUGS, "bug_chon": [], "link_report": "https://claude.ai/artifact/x", "jira": None}


def test_tick_roi_log_jira_chi_gui_bug_da_tick(monkeypatch):
    goi = {}

    def chay(bugs, job, link, reviewer, repo, out):
        goi.update(bugs=bugs, link=link, reviewer=reviewer)
        return {"issues": [{"case": "6.4.0#44", "key": "AIP920-9", "link": "u", "ghi_chu": ""}], "loi": ""}
    monkeypatch.setattr(d.bot_log_jira, "chay", chay)
    bot, c = _bot(), _c()
    asyncio.run(bot._review_bug(_It(["1", "9", "x"]), "chon", c))   # gia tri la bi bo
    assert c["bug_chon"] == [1]
    it = _It()
    asyncio.run(bot._review_bug(it, "jira", c))
    assert [b["case"] for b in goi["bugs"]] == ["6.4.0#44"] and goi["reviewer"] == "qa.lead"
    assert goi["link"] == "https://claude.ai/artifact/x"
    assert it.goi[0][0] == "edit" and it.goi[0][2]["view"] is None       # go nut ngay -> khong bam hai lan
    assert it.goi[-1][0] == "reply" and "AIP920-9" in it.goi[-1][1][0]
    assert c["jira"]["issues"] and not bot.dang_log
    it = _It()
    asyncio.run(bot._review_bug(it, "jira", c))                          # da log roi -> khong log lai
    assert it.goi[0][0] == "send" and it.goi[0][2]["ephemeral"]


def test_chua_tick_hoac_thieu_reviewer_thi_khong_log(monkeypatch):
    monkeypatch.setattr(d.bot_log_jira, "chay", lambda *a: pytest.fail("không được log"))
    it = _It()
    asyncio.run(_bot()._review_bug(it, "jira", _c()))
    assert "Chưa tick" in it.goi[0][1][0]
    c, it = {**_c(), "bug_chon": [0]}, _It()
    asyncio.run(_bot(reviewer="")._review_bug(it, "jira", c))
    assert "DISCORD_JIRA_REVIEWER" in it.goi[0][1][0]


def test_khong_co_bug_that_thi_dong_danh_sach():
    bot, c, it = _bot(), _c(), _It()
    asyncio.run(bot._review_bug(it, "khongbug", c))
    assert c["jira"] == {"issues": [], "loi": ""} and it.goi[0][2]["view"] is None
    assert "không có bug thật" in it.goi[0][2]["content"]


def test_log_loi_thi_tra_menu_lai_de_thu_lai(monkeypatch):
    def hong(*a):
        raise RuntimeError("mcp chết")
    monkeypatch.setattr(d.bot_log_jira, "chay", hong)
    bot, c, it = _bot(), {**_c(), "bug_chon": [0]}, _It()
    asyncio.run(bot._review_bug(it, "jira", c))
    assert c["jira"] is None and not bot.dang_log
    assert [g[0] for g in it.goi] == ["edit", "msg_edit", "reply"] and "mcp chết" in it.goi[-1][1][0]


def test_log_ra_0_issue_thi_chua_tinh_da_log_va_tra_menu(monkeypatch):
    """28/10/2026: MCP Jira khong ket noi -> Claude tra 0 issue; truoc day bot ghi 'da log' nen khong bam lai duoc."""
    monkeypatch.setattr(d.bot_log_jira, "chay", lambda *a: {
        "issues": [{"case": "6.4.0#0", "key": "", "link": "", "ghi_chu": "bỏ qua: không gọi được Jira"}],
        "loi": "tool Jira bị từ chối"})
    bot, c, it = _bot(), {**_c(), "bug_chon": [0]}, _It()
    asyncio.run(bot._review_bug(it, "jira", c))
    assert c["jira"] is None and not bot.dang_log
    assert [g[0] for g in it.goi] == ["edit", "reply", "msg_edit"] and it.goi[-1][2]["view"] is not None


def _tin_ghi(goi, ten, jump="https://discord.com/x/1"):
    async def edit(**k):
        goi.append((ten + "_edit", k))

    async def reply(chu, **k):
        goi.append((ten + "_reply", chu))
    return SimpleNamespace(id=7, jump_url=jump, edit=edit, reply=reply)


def test_qa_gui_lai_build_da_hoi_thi_bat_lai_nut_check(monkeypatch):
    goi = []
    c = {"msg_id": 7, "ma": "AIP922", "version": "3.7.0 (30)", "package": "p", "loai_ban": "release"}
    bot = object.__new__(d.BuildBot)
    bot.q = SimpleNamespace(tin={"7": c}, vi_tri=lambda mid: None)
    cu = _tin_ghi(goi, "cu")

    async def tin_qa(mid):
        return cu
    bot._tin_qa = tin_qa
    monkeypatch.setattr(d.bot_cong_viec, "tin_hoi", lambda c: "hoi")
    asyncio.run(bot._hoi_lai(_tin_ghi(goi, "moi"), {"ma": "AIP922", "version": "3.7.0 (30)"}))
    assert goi[0][0] == "cu_edit" and goi[0][1]["view"] is not None
    assert goi[1][0] == "moi_reply" and "Check" in goi[1][1] and cu.jump_url in goi[1][1]

    goi.clear()
    bot.q.vi_tri = lambda mid: 1                       # dang cho / dang chay -> khong bat lai nut
    asyncio.run(bot._hoi_lai(_tin_ghi(goi, "moi"), {"ma": "AIP922", "version": "3.7.0 (30)"}))
    assert [g[0] for g in goi] == ["moi_reply"] and "đang chờ" in goi[0][1]
