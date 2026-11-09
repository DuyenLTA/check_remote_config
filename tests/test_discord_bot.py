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
        self.response = SimpleNamespace(edit_message=self._ghi("edit"), send_message=self._ghi("send"),
                                        defer=self._ghi("defer"))
        self.message = SimpleNamespace(edit=self._ghi("msg_edit"), reply=self._ghi("reply"), embeds=[], content="")

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


def _bug(g) -> str:
    """Noi dung embed "Bug can review" cua mot lan sua tin goc (menu bug nam tren tin goc - bot_tin_goc)."""
    return next(e.description for e in g[2]["embeds"] if e.title == "Bug cần review")


def _con_menu(g) -> bool:
    """View cua lan sua con menu tick bug (chua xu ly xong)."""
    return any(x.custom_id.startswith("rcr:chon:") for x in g[2]["view"].children)


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
    assert it.goi[0][0] == "edit" and not _con_menu(it.goi[0])            # go menu ngay -> khong bam hai lan
    assert it.goi[-1][0] == "msg_edit" and "AIP920-9" in _bug(it.goi[-1])  # ket qua Jira ghi tren tin goc
    assert not any(g[0] in ("reply", "send") for g in it.goi)
    assert c["jira"]["issues"] and not bot.dang_log
    it = _It()
    asyncio.run(bot._review_bug(it, "jira", c))                          # da log roi -> khong log lai, im lang
    assert [g[0] for g in it.goi] == ["defer"]


def test_chua_tick_hoac_thieu_reviewer_thi_khong_log(monkeypatch):
    monkeypatch.setattr(d.bot_log_jira, "chay", lambda *a: pytest.fail("không được log"))
    it = _It()
    asyncio.run(_bot()._review_bug(it, "jira", _c()))
    assert it.goi[0][0] == "edit" and "Chưa tick" in _bug(it.goi[0])
    c, it = {**_c(), "bug_chon": [0]}, _It()
    asyncio.run(_bot(reviewer="")._review_bug(it, "jira", c))
    assert "DISCORD_JIRA_REVIEWER" in _bug(it.goi[0])


def test_khong_co_bug_that_thi_dong_danh_sach():
    bot, c, it = _bot(), _c(), _It()
    asyncio.run(bot._review_bug(it, "khongbug", c))
    assert c["jira"] == {"issues": [], "loi": ""} and not _con_menu(it.goi[0])
    assert "không có bug thật" in _bug(it.goi[0])


def test_log_loi_thi_tra_menu_lai_de_thu_lai(monkeypatch):
    def hong(*a):
        raise RuntimeError("mcp chết")
    monkeypatch.setattr(d.bot_log_jira, "chay", hong)
    bot, c, it = _bot(), {**_c(), "bug_chon": [0]}, _It()
    asyncio.run(bot._review_bug(it, "jira", c))
    assert c["jira"] is None and not bot.dang_log
    assert [g[0] for g in it.goi] == ["edit", "msg_edit"] and "mcp chết" in _bug(it.goi[-1])
    assert _con_menu(it.goi[-1])                                          # tra menu lai de bam thu lai


def test_log_ra_0_issue_thi_chua_tinh_da_log_va_tra_menu(monkeypatch):
    """28/10/2026: MCP Jira khong ket noi -> Claude tra 0 issue; truoc day bot ghi 'da log' nen khong bam lai duoc."""
    monkeypatch.setattr(d.bot_log_jira, "chay", lambda *a: {
        "issues": [{"case": "6.4.0#0", "key": "", "link": "", "ghi_chu": "bỏ qua: không gọi được Jira"}],
        "loi": "tool Jira bị từ chối"})
    bot, c, it = _bot(), {**_c(), "bug_chon": [0]}, _It()
    asyncio.run(bot._review_bug(it, "jira", c))
    assert c["jira"] is None and not bot.dang_log
    assert [g[0] for g in it.goi] == ["edit", "msg_edit"] and _con_menu(it.goi[-1])


def _tin_ghi(goi, ten, jump="https://discord.com/x/1"):
    async def edit(**k):
        goi.append((ten + "_edit", k))

    async def reply(chu, **k):
        goi.append((ten + "_reply", chu))
    return SimpleNamespace(id=7, jump_url=jump, edit=edit, reply=reply)


def test_qa_gui_lai_build_da_hoi_thi_hoi_moi_ngay_duoi_khong_day_len_tin_cu(monkeypatch):
    """29/10/2026: QA gui lai tin build -> tin hoi moi (nut Check) tra loi ngay duoi, khong bat lai nut tin cu."""
    goi = []
    c = {"msg_id": 7, "ma": "AIP922", "version": "3.7.0 (30)", "package": "p", "loai_ban": "release",
         "bugs": [{"case": "x"}], "jira": {"issues": []}, "link_tin": "cu"}
    bot = object.__new__(d.BuildBot)
    da_nho = {}
    bot.q = SimpleNamespace(tin={"7": c}, vi_tri=lambda mid: None, nho_tin=lambda c: da_nho.update({c["msg_id"]: c}))

    async def tin_qa(mid):
        raise AssertionError("khong duoc dong toi tin cu")
    bot._tin_qa = tin_qa
    monkeypatch.setattr(d.bot_cong_viec, "tin_hoi", lambda c: "hoi")
    hoi_moi = _tin_ghi(goi, "hoi_moi", jump="https://discord.com/x/9")
    hoi_moi.id = 9
    goi_reply = []

    async def reply(chu, **k):
        goi_reply.append(chu)
        return hoi_moi
    tin_qa_gui = SimpleNamespace(id=8, jump_url="https://discord.com/x/8", reply=reply)
    asyncio.run(bot._hoi_lai(tin_qa_gui, {"ma": "AIP922", "version": "3.7.0 (30)"}))
    assert len(goi_reply) == 1 and "https://discord.com/x/1" not in goi_reply[0]   # khong gui link tin cu
    assert goi == [("hoi_moi_edit", goi[0][1])] and goi[0][1]["view"] is not None and goi[0][1]["content"] == "hoi"
    moi = da_nho[9]
    assert moi["link_tin"] == "https://discord.com/x/8" and moi["package"] == "p" and moi["loai_ban"] == "release"
    assert "bugs" not in moi and "jira" not in moi                    # khong mang ket qua luot cu

    goi_reply.clear(); goi.clear()
    bot.q.vi_tri = lambda mid: 1                       # dang cho / dang chay -> chi bao trang thai ngay duoi
    asyncio.run(bot._hoi_lai(tin_qa_gui, {"ma": "AIP922", "version": "3.7.0 (30)"}))
    assert len(goi_reply) == 1 and "đang chờ" in goi_reply[0] and goi == []


def test_webhook_thong_bao_o_kenh_qa_khong_hoi_lai_ma_app(monkeypatch):
    """Kenh QA nam trong ca danh sach kenh build: webhook thong bao cua tool o day khong phai tin build."""
    gui = []

    async def send(chu, **k):
        gui.append(chu)
    monkeypatch.setattr(d.bot_hoi_dap, "la_cau_hoi", lambda bot, m: False)
    bot = object.__new__(d.BuildBot)
    bot.kenh_qa, bot.kenh_build = 1, {1, 2}
    bot.get_channel = lambda cid: SimpleNamespace(send=send)

    def tin(kenh):
        return SimpleNamespace(author=SimpleNamespace(bot=True), webhook_id=99, channel=SimpleNamespace(id=kenh),
                               guild=None, content="Audit xong: 51/51 khớp", jump_url="u")
    asyncio.run(bot.on_message(tin(1)))
    assert gui == []
    asyncio.run(bot.on_message(tin(2)))                 # kenh build that van hoi QA nhu cu
    assert len(gui) == 1 and "không đọc được" in gui[0]


def test_log_jira_xong_bao_duoc_dev_thi_khong_dang_them_o_kenh_qa(monkeypatch):
    """Log du bug + bao duoc dev o kenh project -> kenh QA chi sua dong trang thai, khong tra loi them."""
    monkeypatch.setattr(d.bot_log_jira, "chay", lambda *a: {
        "issues": [{"case": "6.4.0#44", "key": "AIP920-9", "link": "u", "ghi_chu": "tạo mới"}], "loi": ""})
    gui = []

    da_keys = []

    async def bao(bot, c, tin, tin_qa, keys=(), kenh=SimpleNamespace(mention="#aip920-dev")):
        gui.append(tin)
        da_keys.append(list(keys))
        return kenh
    monkeypatch.setattr(d.bot_kenh_project, "bao", bao)
    bot, c = _bot(), {**_c(), "bug_chon": [1]}
    it = _It()
    asyncio.run(bot._review_bug(it, "jira", c))
    assert gui and "AIP920-9" in gui[0] and da_keys == [["AIP920-9"]]      # tag theo assignee cua bug vua log
    assert not [g for g in it.goi if g[0] == "reply"]
    assert it.goi[-1][0] == "msg_edit" and "đã báo dev ở #aip920-dev" in _bug(it.goi[-1])

    async def bao_hong(bot, c, tin, tin_qa, keys=()):
        return None                                   # khong bao duoc dev -> bao o kenh QA
    monkeypatch.setattr(d.bot_kenh_project, "bao", bao_hong)
    c2, it = {**_c(), "bug_chon": [1]}, _It()
    asyncio.run(_bot()._review_bug(it, "jira", c2))
    assert it.goi[-1][0] == "msg_edit" and "AIP920-9" in _bug(it.goi[-1])   # ket qua Jira ghi tren tin goc
    assert not [g for g in it.goi if g[0] == "reply"]


def test_build_khong_ghi_sdk_van_verify_bug_reviewing_nhung_khong_hoi_check(monkeypatch):
    """Build fix bug thuong khong ghi SDK: khong co nut Check, chi BAO QA (kem lenh /check de QA tu chay neu
    build that ra co SDK - user chot 05/11/2026) va van xep verify bug Reviewing."""
    gui, xep = [], []

    async def send(chu, **k):
        gui.append(chu)

    async def xep_(bot, c, kenh):
        xep.append(c)
        return "ok"
    monkeypatch.setattr(d.bot_hoi_dap, "la_cau_hoi", lambda bot, m: False)
    monkeypatch.setattr(d.bot_cong_viec, "package_cua", lambda ma, out: "pkg.nexus")
    monkeypatch.setattr(d.bot_job_verify, "xep", xep_)
    bot = object.__new__(d.BuildBot)
    bot.kenh_qa, bot.kenh_build, bot.q = 1, {1, 2}, SimpleNamespace(tin={})
    bot.get_channel = lambda cid: SimpleNamespace(send=send)
    m = SimpleNamespace(author=SimpleNamespace(bot=False, id=7), webhook_id=None, channel=SimpleNamespace(id=2),
                        guild=None, content="AIP922---Nexus AI v3.7.1 (31) fix bug round 1", jump_url="u")
    asyncio.run(bot.on_message(m))
    assert len(gui) == 1 and "không ghi SDK" in gui[0]       # chi bao, khong co nut Check
    assert "/check AIP922 3.7.1 (31)" in gui[0]
    assert len(xep) == 1 and xep[0]["version"] == "3.7.1 (31)" and xep[0]["package"] == "pkg.nexus"

    gui.clear(), xep.clear()
    bot.q.tin = {"9": {"ma": "AIP922", "version": "3.7.1 (31)", "loai_job": "verify"}}
    m.channel = SimpleNamespace(id=1)                       # QA gui lai o qa-auto: da xep verify roi
    asyncio.run(bot.on_message(m))
    assert gui == [] and xep == []


def test_cai_chi_qua_app_tester(monkeypatch):
    goi = []
    monkeypatch.setattr(d.bot_cong_viec, "_cli", lambda args, timeout, khoa: goi.append(args) or {})
    d.bot_cong_viec.cai("p", "1.0 (1)", "release", "S1")
    assert goi[0] == ["--package", "p", "--version", "1.0 (1)", "--loai", "release", "--serial", "S1"]


def test_tin_build_cua_bot_assistant_dev_van_doc(monkeypatch):
    """30/10/2026: DungNT2-Assistant / TrungHD-Assistant (bot, co trong bang tag dev) gui build -> doc nhu tin dev;
    bot khac van bo qua."""
    gui = []

    async def send(chu, **k):
        gui.append(chu)
    monkeypatch.setattr(d.bot_hoi_dap, "la_cau_hoi", lambda bot, m: False)
    monkeypatch.setattr(d.bot_kenh_project, "env", lambda ten: "DungNT2:111;TrungHD:222")
    bot = object.__new__(d.BuildBot)
    bot.kenh_qa, bot.kenh_build = 1, {2}
    bot.get_channel = lambda cid: SimpleNamespace(send=send)

    def tin(tac_gia):
        return SimpleNamespace(author=SimpleNamespace(bot=True, id=tac_gia), webhook_id=None,
                               channel=SimpleNamespace(id=2), guild=None, content="AIP927 ban build moi", jump_url="u")
    asyncio.run(bot.on_message(tin(333)))
    assert gui == []
    asyncio.run(bot.on_message(tin(111)))               # Assistant cua dev -> doc tin (khong ra version -> hoi QA)
    assert len(gui) == 1 and "không đọc được" in gui[0]


class _KenhGhi:
    def __init__(self):
        self.sent = []

    async def send(self, chu, **kw):
        self.sent.append(chu)


def _xep_verify_voi(monkeypatch, loi: list) -> tuple[list, _KenhGhi]:
    """`loi`: moi lan goi xep lay mot phan tu - Exception thi raise, con lai tra tom tat."""
    goi = []

    async def xep(bot, c, kenh):
        goi.append(1)
        r = loi.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    monkeypatch.setattr(d.bot_job_verify, "xep", xep)
    monkeypatch.setattr(d.bot_nhan_build, "CHO_JIRA", 0)
    k = _KenhGhi()
    asyncio.run(object.__new__(d.BuildBot)._xep_verify({"ma": "AIP936", "version": "1.0.0 (2)"}, k))
    return goi, k


def test_jira_mat_ket_noi_thi_im_lang_thu_lai(monkeypatch):
    mat = d.bot_jira_rest.JiraMatKetNoi("Jira GET /rest/api/2/search khong ket noi duoc: [WinError 10060]")
    goi, k = _xep_verify_voi(monkeypatch, [mat, mat, "AIP936: không có bug nào của bot đang Reviewing."])
    assert len(goi) == 3 and k.sent == []


def test_jira_mat_ket_noi_het_luot_thi_bao_tieng_viet(monkeypatch):
    mat = d.bot_jira_rest.JiraMatKetNoi("khong ket noi duoc: [WinError 10060]")
    goi, k = _xep_verify_voi(monkeypatch, [mat] * d.bot_nhan_build.SO_LAN_JIRA)
    assert len(goi) == d.bot_nhan_build.SO_LAN_JIRA and len(k.sent) == 1
    assert "Jira không kết nối được" in k.sent[0] and "WinError" not in k.sent[0]


def test_loi_jira_khac_bao_ngay_khong_thu_lai(monkeypatch):
    goi, k = _xep_verify_voi(monkeypatch, [d.bot_jira_rest.JiraLoi("Jira GET -> HTTP 401: x")])
    assert len(goi) == 1 and "HTTP 401" in k.sent[0]


def test_chi_nhan_build_o_kenh_project_va_qa_auto_bo_kenh_chung(monkeypatch):
    gui = []

    async def send(chu, **k):
        gui.append(chu)
    monkeypatch.setattr(d.bot_hoi_dap, "la_cau_hoi", lambda bot, m: False)
    bot = object.__new__(d.BuildBot)
    bot.kenh_qa, bot.kenh_build = 1, {1}
    bot.get_channel = lambda cid: SimpleNamespace(send=send)

    def tin(kenh_id, ten):
        return SimpleNamespace(author=SimpleNamespace(bot=True, id=5), webhook_id=4, guild=SimpleNamespace(id=9),
                               channel=SimpleNamespace(id=kenh_id, name=ten), content="Bản build AIP918 nhé",
                               jump_url="u")
    asyncio.run(bot.on_message(tin(7, "build-notification")))     # kenh chung: bo qua
    assert gui == []
    asyncio.run(bot.on_message(tin(8, "aip918-abc-official-group")))   # kenh project, server nao cung nhan
    assert len(gui) == 1 and "không đọc được" in gui[0]


def test_bot_khong_tha_tim_vao_tin_build(monkeypatch):
    # User chot 07/11/2026: bot thoi tha ❤️ vao tin bao build, ke ca tin cua bot Assistant cua dev.
    monkeypatch.setattr(d.bot_hoi_dap, "la_cau_hoi", lambda bot, m: False)
    monkeypatch.setattr(d.bot_nhan_build.bot_kenh_project, "la_bot_dev", lambda i: i == 6)
    bot = object.__new__(d.BuildBot)
    bot.kenh_qa, bot.kenh_build, bot.duyet, bot.role = 1, {1}, set(), 0
    bot.q = SimpleNamespace(tin={1: {"ma": "AIP882", "version": "4.4.0 (41)", "loai_job": "verify"}})
    bot.get_channel = lambda cid: SimpleNamespace(send=None)
    tha = []

    async def add_reaction(e):
        tha.append(e)
    m = SimpleNamespace(author=SimpleNamespace(bot=True, id=6), webhook_id=None, guild=SimpleNamespace(id=9),
                        channel=SimpleNamespace(id=8, name="aip882-artspire-official-group"), jump_url="u",
                        add_reaction=add_reaction,
                        content="Bản build **AIP882---AI-Video** v4.4.0 (41) đã được hoàn thiện. apply tutorial 3.6.1")
    asyncio.run(bot.on_message(m))
    assert tha == []


def test_may_phu_bo_qua_tin_build_va_nut_chi_nghe_kenh_dieu_phoi(monkeypatch):
    bot = object.__new__(d.BuildBot)
    bot.vai_tro, bot.dieu_phoi, bot.kenh_qa, bot.kenh_build = "phu", 77, 1, {1}
    nhan = []

    async def nhan_dieu_phoi(m):
        nhan.append(m)
    bot._nhan_dieu_phoi = nhan_dieu_phoi
    monkeypatch.setattr(d.bot_hoi_dap, "la_cau_hoi", lambda b, m: (_ for _ in ()).throw(AssertionError("khong hoi dap")))
    tin_build = SimpleNamespace(author=SimpleNamespace(bot=True, id=5), webhook_id=4, guild=SimpleNamespace(id=9),
                                channel=SimpleNamespace(id=8, name="aip882-x"), content="AIP882 v4.4.0 (41)")
    asyncio.run(bot.on_message(tin_build))
    assert nhan == []
    dieu_phoi = SimpleNamespace(channel=SimpleNamespace(id=77), content="RCR giao ubuntu")
    asyncio.run(bot.on_message(dieu_phoi))
    assert nhan == [dieu_phoi]
    asyncio.run(bot.on_interaction(SimpleNamespace(data={"custom_id": "rcr:check:1"})))   # khong tra loi nut


def test_moi_phien_ket_noi_moi_deu_bao_may_phu_xin_lai(monkeypatch):
    """02/11/2026: may phu khong xin lai moi 15 phut nua -> bot chinh phai bao `chinh_khoi_dong` moi lan
    ket noi phien moi (tin `xin` gui luc mat ket noi co the da lo), khong chi lan khoi dong dau."""
    gui = []

    async def gui_(kenh, loai, d):
        gui.append(loai)

    async def kenh():
        return object()

    async def quet(bot):
        return 0
    monkeypatch.setattr(d.bot_may_phu, "gui", gui_)
    monkeypatch.setattr(d.bot_bat_tin_lo, "quet", quet)
    bot = _bot()
    bot.vai_tro, bot.dieu_phoi, bot._kenh_dieu_phoi = "chinh", 123, kenh
    asyncio.run(bot.on_ready())
    asyncio.run(bot.on_ready())
    assert gui == ["chinh_khoi_dong", "chinh_khoi_dong"]
