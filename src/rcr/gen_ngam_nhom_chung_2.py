"""Kich ban `rcr-gen-ngam` nhom config chung: R02 (popup giay 12 / ve Home giay 15, History, toast View), R03 (bam OK,
push khi o nen), R04 (video), R05 (2 luot chay chong), R08 (kill mo lai, push sau khi bi tat khoi da nhiem).
"""

from __future__ import annotations

import asyncio
import re

from . import device_app
from . import gen_ngam_may as may
from . import gen_ngam_tao as tao
from . import gen_ngam_thao_tac as tt
from .gen_ngam_nhom_dau import POPUP_HOME_RE as POPUP_HOME, Ctx, LaiHut, _can, _cho_xong, _popup_home, _s, bam_dong_het_luot, mo_lai_vao_home, net


async def tao_anh(c: Ctx, che_do: str = "doi", quay: str = "", **kw) -> dict:
    if quay:
        kq = await tao.tao_quay(c.client, c.serial, c.package, c.ct, "anh", che_do, c.out, quay, hop=c.so.nho, **kw)
    else:
        kq = await tao.tao(c.client, c.serial, c.package, c.ct, "anh", che_do, **kw)
        if not kq.get("loi"):
            kq |= await tao.gio_vao_ra_man_cho(c.client, c.serial, c.package, c.ct, kq)
    _can(kq, "tạo ảnh")
    if kq.get("hop_dem"):
        c.so.nho["hop_dem"], c.so.nho["hop_tieu_de"] = kq["hop_dem"], kq.get("hop_tieu_de") or kq["hop_dem"]
    if kq.get("hop_ok"):
        c.so.nho["hop_ok"] = kq["hop_ok"]
    if kq["t_cho"]:
        c.nho["anh_bat_dau"] = c.nho.get("anh_bat_dau", 0) + 1
    if kq.get("hop_ok"):
        c.nho["hop_ok"] = kq["hop_ok"]
    return kq


async def _bat_toast(c: Ctx, mau: str, dump: bool = True) -> tuple[list[str], str]:
    """Toast sau khi bam. App dung toast he thong (khong co trong dump, luot 16/11 R02-03): soi hang doi toast cua
    he thong toi 3s (dung ngay khi thay); `dump` them mot lan nhin cay node phong toast ve trong app.
    -> (bang chung, activity)."""
    thay: list[str] = []
    het = await may.gio(c.client, c.serial) + 3.0
    while await may.gio(c.client, c.serial) < het and not thay:
        if await may.toast_he_thong(c.client, c.serial, c.package):
            thay.append("toast hệ thống của app đang hiện (dumpsys notification Toast Queue)")
        await asyncio.sleep(0.1)
    if dump and not thay:
        m = await c.nhin()
        thay += [s for s in m.chu() if re.search(mau, s, re.I)]
    _p, act = await device_app.focus(c.client, c.serial)
    return thay, (act or "").rsplit(".", 1)[-1]


def _dem_ok(kq: dict) -> tuple[bool, str]:
    d = kq.get("dem") or {}
    if d.get("loi") or not kq.get("log_vao"):
        return False, f"không đo được popup trên video: {d.get('loi') or 'thiếu mốc vào màn chờ'}"
    hien = d["t_hien"] - kq["log_vao"]
    moc = [d["t_hien"], *d["t_doi"], d["t_ve_home"]]
    khoang = [round(b - a, 1) for a, b in zip(moc, moc[1:])]
    dat = d["so_trang_thai"] == 3 and all(0.6 <= k <= 1.5 for k in khoang)
    return dat, (f"video 10 khung/s: popup hiện {_s(hien)} sau khi vào màn chờ, {d['so_trang_thai']} số đếm, mỗi số "
                 f"đứng {khoang} s rồi về Home")


async def r02_r03(c: Ctx) -> None:
    so, ct = c.so, c.ct
    kq = await tao_anh(c, "doi", "r02")
    ve = kq["log_ra"] - kq["log_vao"] if kq.get("log_ra") else -1
    so.ghi("GEN-R02-02", "Giây 15", 14.5 <= ve <= 15.6 and kq["ra_man"] == "MainActivity",
           f"log START {kq.get('ra_man') or '?'} {_s(ve)} sau START ProcessingActivity, không bấm gì")
    # Anh I2I xong ~30-41s; R02-03 (bam o dang tao) va R02-04 (o man chon style TOI KHI xong) deu can anh con dang
    # tao -> moi lan nhin UI ~2,1s deu dat: MOT lan nhin Home (badge + popup + nut History), bam History ngay; bat
    # toast bang hang doi toast (0,1s); BACK ve thang man chon style (app giu tab Image Studio luc tu ve).
    m = await c.nhin()
    thay = [s for s in m.chu() if re.search(POPUP_HOME, s, re.I)]
    so.ghi("GEN-R02-02", "Badge", may.badge(m, ct) == 1, f"số trên nút History = {may.badge(m, ct)}")
    nut = m.tim(ct["lich_su"])
    if nut is None:
        raise LaiHut("R02-03: Home không có nút History")
    await tao.bam(c.client, c.serial, nut, 0.2)
    m = await may.cho(c.client, c.serial, c.package, lambda x: x.o(ct["man_lich_su"]), 8.0)
    o = may.o_lich_su(m, ct) if m else []
    if not o:
        raise LaiHut("R02-03: History trống")
    so.ghi("GEN-R02-03", "vòng xoay", o[0]["dang_tao"], f"ô đầu History lúc {_s(m.t - kq['log_vao'])} sau vào màn "
           f"chờ: [{o[0]['chu']}]")
    t_bam = await may.gio(c.client, c.serial)
    await device_app.tap(c.client, c.serial, *o[0]["xy"])
    toast, act = await _bat_toast(c, ct["toast_dang_tao"], dump=False)
    so.ghi("GEN-R02-03", "Generating, please wait", bool(toast) and "History" in act,
           f"bấm ô đang tạo ({_s(t_bam - kq['log_vao'])} sau vào màn chờ): toast {toast or 'không thấy'}; vẫn ở {act}")
    await tao.back(c.client, c.serial, 0.6)
    m = await c.nhin()
    if not m.tim(r"^Image Studio$") or m.tim(r"^Image Studio$").bounds.top > 400:
        m = await tao.vao_tab(c.client, c.serial, c.package, ct, "tab_anh")
    thay += [s for s in m.chu() if re.search(POPUP_HOME, s, re.I)]
    so.ghi("GEN-R02-02", "Không hiện popup widget", not thay,
           f"Home lúc tự về và khi quay ra từ History: {thay or 'không có popup'}")
    # R02-04: dang o man chon style (Image Studio), o do toi khi xong
    t_toi = m.t
    c.nho.pop("man_view", None)
    xong = await _nhin_toi_xong(c, kq["t_confirm"], 1, cho_view=True)
    view_m = c.nho.get("man_view")
    pu = await may.push(c.client, c.serial, c.package)
    co_push = any(re.search(ct["push_xong"], p["title"] + p["text"]) for p in pu)
    cum = may.cum_toast(kq["t_confirm"])
    if xong and xong[0][0] < t_toi:
        c.log(f"  CẢNH BÁO R02-04: ảnh xong ({_s(xong[0][0] - kq['log_vao'])}) trước khi tool tới màn chọn style "
              f"({_s(t_toi - kq['log_vao'])}) — tool chậm, không phải app")
    so.ghi("GEN-R02-04", "hiện toast", view_m is not None and not co_push,
           f"tới màn chọn style {_s(t_toi - kq['log_vao'])}, ảnh xong {_s(xong[0][0] - kq['log_vao']) if xong else '?'} "
           f"sau vào màn chờ, đang ở màn chọn style "
           f"({view_m.act if view_m else '?'}): toast hiện {len(cum)} lần; thông báo hệ thống: "
           f"{[(p['title'], p['text']) for p in pu] or 'không'}")
    view = view_m
    kqm = await may.cho(c.client, c.serial, c.package, lambda x: x.o(ct["man_ket_qua"]), 8.0)
    rate = kqm and (kqm.tim(ct["rate"]) or await may.cho(c.client, c.serial, c.package,
                                                        lambda x: x.tim(ct["rate"]), 4.0))
    so.ghi("GEN-R02-04", "View", bool(kqm) and bool(rate),
           ("bấm View → " + (kqm.act if kqm else "không tới Kết quả") + "; popup rate: " + ("có" if rate else "không"))
           if view is not None else "toast đã ẩn trước khi bấm được View")
    # R02-05: Back tu Ket qua -> dung man chon style; Home khong con badge
    await tao.dong_rate(c.client, c.serial, c.package, ct)
    await tao.back(c.client, c.serial)
    m = await c.nhin()
    so.ghi("GEN-R02-05", "Back", m.o(ct["man_home"]) and m.tim(ct["tab_anh"]) is not None and
           bool(m.tim(r"^Image Studio$")) and m.tim(r"^Image Studio$").bounds.top < 400,
           f"Back từ Kết quả → {m.act}, tiêu đề: {[s for s in m.chu() if re.search(ct['tab_anh'], s)][:1]}")
    m = await tao.vao_tab(c.client, c.serial, c.package, ct, "tab_home")
    so.ghi("GEN-R02-05", "không còn badge", may.badge(m, ct) == 0, f"Home: số trên nút History = {may.badge(m, ct)}")
    ghi_popup_12s(c, "GEN-R02-01", kq, await _co_crash(c, kq["t_confirm"]))
    await r03(c)


async def _co_crash(c: Ctx, tu: float) -> bool:
    crash, _, _ = await c.client.shell(c.serial, "logcat", "-d", "-b", "crash", "-T", f"{tu:.3f}")
    return c.package in (crash or "")


def ghi_popup_12s(c: Ctx, case: str, kq: dict, co_crash: bool | None = None) -> None:
    """Popup dem nguoc anh: hien giay 12, dem 3-2-1 moi so ~1s. Tach khung video o day (sau cac buoc canh gio)."""
    tao.phan_tich_video(kq)
    d = kq.get("dem") or {}
    hien = d["t_hien"] - kq["log_vao"] if d.get("t_hien") and kq.get("log_vao") else -1
    if co_crash is None:
        c.so.ghi(case, "Giây 12", 11.5 <= hien <= 12.8, f"popup hiện {_s(hien)} sau vào màn chờ (khung video) "
                 + (d.get("loi") or ""))
    else:
        c.so.ghi(case, "Giây 12", 11.5 <= hien <= 12.8 and not co_crash,
                 f"popup hiện {_s(hien)} sau khi vào màn chờ (khung video{', ' + d['loi'] if d.get('loi') else ''}); "
                 "crash buffer: " + ("có crash của app" if co_crash else "không"))
    dat, ly = _dem_ok(kq)
    c.so.ghi(case, "đếm 3", dat, ly)


async def r03(c: Ctx) -> None:
    so, ct = c.so, c.ct
    kq = await tao_anh(c, "doi", ok_luc=12.6, hop_ok=c.so.nho.get("hop_ok") or c.ct.get("popup_hop_ok"))
    ve = kq["log_ra"] - kq["t_ok"] if kq.get("t_ok") and kq.get("log_ra") else -1
    tu_vao = kq["log_ra"] - kq["log_vao"] if kq.get("log_ra") else -1
    so.ghi("GEN-R03-01", "Về Home ngay", 0 <= ve < 1.0 and tu_vao < 14.5 and kq["ra_man"] == "MainActivity",
           f"bấm OK ở giây {_s(kq['t_ok'] - kq['log_vao']) if kq.get('t_ok') else '?'} → START {kq.get('ra_man')} "
           f"sau {_s(ve)} (giây {_s(tu_vao)} kể từ vào màn chờ, mốc tự về là 15s)")
    m = await tao.mo_lich_su(c.client, c.serial, c.package, ct)
    o = may.o_lich_su(m, ct) if m else []
    so.ghi("GEN-R03-01", "vòng xoay", bool(o) and o[0]["dang_tao"], f"ô đầu History: [{o[0]['chu'] if o else ''}]")
    await c.client.shell(c.serial, "input", "keyevent", "KEYCODE_HOME")
    xong = await _cho_xong(c, kq["t_confirm"], 1, 60)
    await asyncio.sleep(2.0)
    pu = await may.push(c.client, c.serial, c.package)
    xong_push = [p for p in pu if re.search(ct["push_xong"], p["title"] + p["text"])]
    so.ghi("GEN-R03-02", "có push", bool(xong_push),
           f"app ở nền, ảnh xong {'(worker ' + xong[0][1] + ')' if xong else '?'}: thông báo "
           f"{[(p['title'], p['text']) for p in pu]}")
    so.ghi("GEN-R03-02", "đã tự mất", not any(re.search(ct["push_dang_tao"], p["text"]) for p in pu),
           f"thông báo còn lại: {[(p['title'], p['text']) for p in pu]}")
    b = await tao.mo_shade_bam_push(c.client, c.serial, c.package, ct)
    m = b.get("man")
    rate = m and (m.tim(ct["rate"]) or await may.cho(c.client, c.serial, c.package, lambda x: x.tim(ct["rate"]), 4.0))
    so.ghi("GEN-R03-03", "Mở màn Kết quả", bool(m) and bool(rate) and m.tim(ct["so_sanh"]) is not None,
           f"bấm push → {b.get('toi') or 'không tới Kết quả'} (ảnh I2I: thanh so sánh "
           f"{'có' if m and m.tim(ct['so_sanh']) else 'không'}); popup rate: {'có' if rate else 'không'}")
    thay = [s for s in (m.chu() if m else []) if re.search(r"^Add Widget$|Daily Check|Get notified", s)]
    so.ghi("GEN-R03-03", "Không có popup Home", bool(m) and not thay, f"popup Home đè: {thay or 'không'}")
    pu = await may.push(c.client, c.serial, c.package)
    so.ghi("GEN-R03-03", "đã mất khỏi", not any(re.search(ct["push_xong"], p["title"] + p["text"]) for p in pu),
           f"thông báo của app sau khi bấm: {[(p['title'], p['text']) for p in pu] or 'không còn'}")
    await tao.dong_rate(c.client, c.serial, c.package, ct)
    await tao.back(c.client, c.serial)
    a1 = (await c.nhin()).act
    await tao.back(c.client, c.serial)
    m = await c.nhin()
    so.ghi("GEN-R03-04", "Back 1", "History" in a1, f"Back 1 → {a1}")
    so.ghi("GEN-R03-04", "Back 2", m.o(c.ct["man_home"]) and may.badge(m, ct) == 0,
           f"Back 2 → {m.act}, số trên nút History = {may.badge(m, ct)}")


async def r04(c: Ctx) -> None:
    so, ct = c.so, c.ct
    kq = _can(await tao.tao_quay(c.client, c.serial, c.package, ct, "video", "doi", c.out, "r04"), "R04 tạo video")
    c.nho["video_style"] = kq["style"]
    vao = kq["log_vao"] - kq["t_confirm"] if kq.get("log_vao") else -1
    so.ghi("GEN-R04-01", "Không có ads thưởng", not kq["ad"] and 0 <= vao < 2.5,
           f"Confirm → ProcessingActivity sau {_s(vao)}, AdActivity: {'có' if kq['ad'] else 'không'}")
    ve = kq["log_ra"] - kq["log_vao"] if kq.get("log_ra") else -1
    so.ghi("GEN-R04-01", "Giây 8", 7.5 <= ve <= 8.6 and kq["ra_man"] == "MainActivity",
           f"log START {kq.get('ra_man')} {_s(ve)} sau vào màn chờ")
    xong, to = await _o_home_toi_xong(c, kq["t_confirm"])
    _ghi_toast(c, "GEN-R04-02", xong, to)
    d = tao.phan_tich_video(kq)
    hien = d["t_hien"] - kq["log_vao"] if d.get("t_hien") else -1
    so.ghi("GEN-R04-01", "Giây 5", 4.5 <= hien <= 5.8, f"popup hiện {_s(hien)} sau vào màn chờ (khung video) "
           + (d.get("loi") or ""))
    m = await tao.mo_lich_su(c.client, c.serial, c.package, ct)
    o = may.o_lich_su(m, ct) if m else []
    dau = o[0] if o else {}
    nhan = bool(re.search(r"\bVideo\b", dau.get("chu", "")))
    so.ghi("GEN-R04-03", "nhãn Video", dau.get("ten") == kq["style"] and nhan,
           f"ô đầu History '{dau.get('ten')}', chữ trong ô [{dau.get('chu')}]: "
           + ("có nhãn Video" if nhan else "KHÔNG có nhãn chữ 'Video'"))
    await device_app.tap(c.client, c.serial, *dau["xy"])
    m = await may.cho(c.client, c.serial, c.package, lambda x: x.o(ct["man_ket_qua"]), 10.0)
    if m is None:
        raise LaiHut("R04-03: bấm ô video không tới Kết quả")
    await tao.dong_rate(c.client, c.serial, c.package, ct, m)
    vung = (48, 344, 1032, 1328)
    ph = await tt.video_dang_phat(c.client, c.serial, vung)
    m = await c.nhin()
    so.ghi("GEN-R04-03", "video phát được", ph["phat"] and m.tim(ct["so_sanh"]) is None,
           f"2 ảnh cách 1,5s ở vùng video lệch {ph['lech']} ({'đang phát' if ph['phat'] else 'đứng'}); thanh so sánh: "
           f"{'có' if m.tim(ct['so_sanh']) else 'không'}")
    tat = await net(c, False)
    try:
        ph = await tt.video_dang_phat(c.client, c.serial, vung)
        so.ghi("GEN-R04-04", "không có mạng", ph["phat"] and not tat["thong"],
               f"tắt wifi + data (ping {'vẫn thông' if tat['thong'] else 'không ra mạng'}): vùng video lệch {ph['lech']}")
        sv = await tt.luu(c.client, c.serial, c.package, ct)
    finally:
        await net(c, True)
    if sv.get("loi"):
        raise LaiHut(f"R04-04: {sv['loi']}")
    tg = sv["t_xong"] - sv["t_bam"] if sv["t_xong"] else -1
    so.ghi("GEN-R04-04", "Lưu xong", 0 <= tg <= 6, f"offline bấm lưu → 'Saved' sau {_s(tg)}")
    vid = [t for t in sv["tep"] if t["bang"] == "video" or t["mime"].startswith("video/")]
    so.ghi("GEN-R04-04", "Video có trong Thư viện", bool(vid),
           f"MediaStore mới trong {ct['thu_muc_luu']}: {sv['tep'] or 'không có'}"
           + ("" if vid else " — không có bản ghi video (mime video/*)"))


async def _nhin_toi_xong(c: Ctx, tu: float, so_xong: int = 1, cho_view: bool = False) -> list:
    """Nhin man (moi lan nhin ghi toast vao nhat ky) toi khi du `so_xong` luot xong + 12s (toast ~8s da an).
    `cho_view`: dung ngay khi dang thay nut View (de bam). Toi da 5 phut."""
    het = await may.gio(c.client, c.serial) + 300
    xong: list = []
    while True:
        m = await c.nhin()
        if cho_view and m.tim(c.ct["toast_view"]) is not None:
            # Bam View NGAY o lan nhin nay: nhin them mot lan (~2,1s) thi toast co the da an (luot 16/11 R02-04).
            c.nho["man_view"] = m
            t = m.tim(c.ct["toast_xong"])
            if c.nho.pop("chup_toast", False) and t is not None:
                img = await tt.anh(c.client, c.serial)
                c.nho["mau_toast"] = str(tt.mau_nen(img, [t.bounds.left, t.bounds.top, t.bounds.right, t.bounds.bottom]))
            await tao.bam(c.client, c.serial, m.tim(c.ct["toast_view"]), 0.3)
            break
        xong = [x for x in may.worker(await may.log(c.client, c.serial, tu)) if x[1] != "bat_dau"]
        if (dem := c.nho.get("_dem_nhin", 0) + 1) % 4 == 0:       # dau vet: dang dung o dau trong luc cho toast
            c.log(f"    chờ xong: {m.act}, {len(xong)}/{so_xong} lượt xong, chữ đầu màn {m.chu()[:4]}")
        c.nho["_dem_nhin"] = dem
        if len(xong) >= so_xong and m.t > xong[so_xong - 1][0] + 12 or m.t > het:
            break
        await asyncio.sleep(0.2)
    return [x for x in may.worker(await may.log(c.client, c.serial, tu)) if x[1] != "bat_dau"]


async def _o_home_toi_xong(c: Ctx, tu: float, so_xong: int = 1) -> tuple[list, dict]:
    await tao.vao_tab(c.client, c.serial, c.package, c.ct, "tab_home")
    xong = await _nhin_toi_xong(c, tu, so_xong)
    return xong, {"hien": may.cum_toast(tu)}


def thoi_gian_toast(cum: tuple) -> tuple[float, float]:
    """(ngan nhat, dai nhat) toast da dung tren man - tinh tu LUC TOAST HIEN, khong tu luc worker xong: app co the
    hien toast tre hon worker vai giay (luot 16/11 R06-02: tre 6,4s khi dang o man khac)."""
    truoc, dau, cuoi, mat = cum
    return cuoi - dau, (mat - truoc) if mat and truoc else 0.0


def _ghi_toast(c: Ctx, case: str, xong: list, to: dict) -> None:
    hien = to["hien"]
    if not xong or not hien:
        c.so.ghi(case, "toast", False, f"không thấy toast xong (worker: {xong}, toast: {hien})")
        return
    c.so.ghi(case, "toast \\+ View|có toast", True, f"worker xong lúc {xong[0][0]:.1f}, toast thấy từ {hien[0][1]:.1f}")
    ngan, dai = thoi_gian_toast(hien[0])
    c.so.ghi(case, "tự ẩn sau 8s", bool(dai) and ngan <= 9.0 and dai >= 7.0,
             f"toast đứng trên màn trong khoảng {_s(ngan)}–{_s(dai)} (nhìn UI ~2,1s/lần) rồi tự mất")


async def r05(c: Ctx) -> None:
    """2 luot chay chong. Anh I2I xong ~31s nen tao anh truoc (doi popup 15s) thi video bat dau ~giay 23 -> anh xong
    truoc khi mo duoc History (bot 13/11 thu 3 lan hut). Tao VIDEO truoc (video >= 45s) roi anh ngay sau."""
    so, ct = c.so, c.ct
    v = _can(await tao.tao(c.client, c.serial, c.package, ct, "video", "doi"), "R05 video")
    a = await tao_anh(c, "doi")
    m = await c.nhin()
    bd = may.badge(m, ct)
    so.ghi("GEN-R05-01", "Cả 2 lần", bool(v["t_cho"] and a["t_cho"]) and not (v["ad"] or a["ad"]),
           f"video '{v['style']}' rồi ảnh '{a['style']}' (video trước để 2 lượt chạy chồng): cả 2 vào màn chờ, "
           f"AdActivity: {'có' if v['ad'] or a['ad'] else 'không'}")
    so.ghi("GEN-R05-01", "Badge History = 2", bd == 2, f"về Home sau lượt 2: số trên nút History = {bd}")
    m = await tao.mo_lich_su(c.client, c.serial, c.package, ct)
    o = may.o_lich_su(m, ct) if m else []
    quay = [x for x in o if x["dang_tao"]]
    so.ghi("GEN-R05-01", "2 ô vòng xoay", len(quay) >= 2 and o[0]["ten"] == a["style"],
           f"History: {[(x['ten'], x['chu']) for x in o[:3]]}")
    await c.client.shell(c.serial, "input", "keyevent", "KEYCODE_HOME")
    xong = await _cho_xong(c, v["t_confirm"], 2, 300)
    await asyncio.sleep(2.0)
    pu = [p for p in await may.push(c.client, c.serial, c.package)
          if re.search(ct["push_xong"], p["title"] + p["text"])]
    so.ghi("GEN-R05-02", "2 push", len(pu) == 2 and len({p["id"] for p in pu}) == 2,
           f"app ở nền tới khi 2 lượt xong ({[x[1] for x in xong]}): {len(pu)} thông báo xong, id {[p['id'] for p in pu]}")
    ket = {}
    for lan in range(2):
        b = await tao.mo_shade_bam_push(c.client, c.serial, c.package, ct)
        m = b.get("man")
        loai = "anh" if m and m.tim(ct["so_sanh"]) else "video"
        await tao.dong_rate(c.client, c.serial, c.package, ct)
        h = await tao.ve_main(c.client, c.serial, c.package, ct)
        ket[loai] = {"toi": b.get("toi"), "badge": may.badge(h, ct), "lan": lan + 1}
    a_, v_ = ket.get("anh"), ket.get("video")
    so.ghi("GEN-R05-03", "Kết quả ảnh I2I", bool(a_), f"bấm push ảnh (lần {a_['lan'] if a_ else '?'}) → "
           f"{a_['toi'] if a_ else 'không mở được Kết quả có thanh so sánh'}")
    b1 = next((x["badge"] for x in ket.values() if x["lan"] == 1), -1)
    b2 = next((x["badge"] for x in ket.values() if x["lan"] == 2), -1)
    so.ghi("GEN-R05-03", "Badge History = 1", b1 == 1, f"mở push thứ nhất rồi về Home: số trên nút History = {b1}")
    so.ghi("GEN-R05-04", "Kết quả video", bool(v_), f"bấm push video → {v_['toi'] if v_ else 'không thấy'}")
    so.ghi("GEN-R05-04", "Không còn badge", b2 == 0, f"mở push thứ hai rồi về Home: số trên nút History = {b2}")
    m = await tao.mo_lich_su(c.client, c.serial, c.package, ct)
    x = await tt.xoa_hai(c.client, c.serial, c.package, ct)
    if x.get("loi"):
        raise LaiHut(f"R05-05: {x['loi']}")
    so.ghi("GEN-R05-05", "Nhấn giữ", bool(re.search(r"\b1 selected", x["chon_1"])) and "2 selected" in x["chon_2"],
           f"nhấn giữ → '{x['chon_1']}', bấm ô 2 → '{x['chon_2']}'")
    toast = [s for s in x["toast_ui"] if re.search(r"2 items deleted", s, re.I)] + x["su_kien"]
    mat_2 = x["dau_sau"] == x["dau_truoc"][2:4]
    so.ghi("GEN-R05-05", "2 items deleted", bool(toast) and mat_2,
           f"hộp '{x['hop_thoai']}' → Delete: 4 ô đầu trước {x['dau_truoc']}, 2 ô đầu sau {x['dau_sau']} "
           f"({'2 ô đã chọn biến mất' if mat_2 else 'không khớp 2 ô biến mất'}); toast: "
           f"{toast or 'không có (hàng đợi toast hệ thống + cây giao diện 3s sau khi xoá)'}")


async def r08(c: Ctx) -> None:
    so, ct = c.so, c.ct
    await mo_lai_vao_home(c)
    thay = await _popup_home(c, 15.0)
    so.ghi("GEN-R08-01", "Popup widget", bool(thay), f"kill + mở lại vào Home, nhìn 15s: {thay or 'không có popup'}")
    for _ in range(3):
        if not await tao.dong_rate(c.client, c.serial, c.package, ct):
            m = await c.nhin()
            x = m.tim("^Close$")
            if x is None:
                break
            await tao.bam(c.client, c.serial, x)
    hai = []
    for _ in range(2):
        kq = await tao_anh(c, "doi")
        hai.append(kq)
    xong = await _cho_xong(c, hai[0]["t_confirm"], 2, 120)
    so.ghi("GEN-R08-02", "không qua ads", all(k["t_cho"] and not k["ad"] for k in hai),
           f"app không có T2I: tạo 2 ảnh I2I, AdActivity: {[k['ad'] for k in hai]}")
    so.ghi("GEN-R08-02", "đúng kết quả", len(xong) == 2 and all(s == "SUCCESS" for _t, s in xong),
           f"GenerationWorker: {[s for _t, s in xong]}")
    kq = await tao_anh(c, "doi")
    await c.client.shell(c.serial, "input", "keyevent", "KEYCODE_HOME")
    await _cho_xong(c, kq["t_confirm"], 1, 90)
    await asyncio.sleep(2.0)
    pu_truoc = [(p["title"], p["text"]) for p in await may.push(c.client, c.serial, c.package)]
    da_tat = await tao.tat_khoi_da_nhiem(c.client, c.serial, c.package)
    pu_sau = [(p["title"], p["text"]) for p in await may.push(c.client, c.serial, c.package)]
    c.log(f"  R08-03 push trước khi tắt: {pu_truoc} · sau khi tắt: {pu_sau}")
    t = await may.gio(c.client, c.serial)
    b = await tao.mo_shade_bam_push(c.client, c.serial, c.package, ct)
    m = b.get("man") or await tt.lai_toi(c.client, c.serial, c.package, ct, ct["man_ket_qua"])
    mo = may.mo_man(await may.log(c.client, c.serial, t), c.package)
    splash = [a for _t, a in mo if re.search("Splash", a)]
    so.ghi("GEN-R08-03", "Splash", da_tat and bool(splash), f"tắt app khỏi đa nhiệm (process "
           f"{'đã chết' if da_tat else 'còn sống'}; push trước {pu_truoc}, sau {pu_sau}), bấm push "
           f"({'bấm được' if b.get('bam') else 'không thấy push trong thanh thông báo'}) → các màn: "
           f"{[a for _t, a in mo][:6]}")
    so.ghi("GEN-R08-03", "Mở màn Kết quả", bool(m) and m.tim(ct["so_sanh"]) is not None,
           f"tới {m.act if m else 'không tới Kết quả'} (ảnh I2I có thanh so sánh: "
           f"{'có' if m and m.tim(ct['so_sanh']) else 'không'})")
    await tao.dong_rate(c.client, c.serial, c.package, ct)
    await bam_dong_het_luot(c)
