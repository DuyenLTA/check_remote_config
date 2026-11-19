"""Kich ban `rcr-gen-ngam` nhom R01 (anh xong truoc popup) va R02-R05 + R08 (config Test Data chung).

Moi buoc: lam tren may (gen_ngam_tao / gen_ngam_thao_tac) roi `so.ghi(case, mau_dong_expected, dat, ly_do)` voi so do
that (gio may, chu tren man, log). Khong doan: buoc hong -> ghi FAIL kem ly do lai hong chi khi do la hanh vi app;
lai hut (khong toi man) -> raise LaiHut de CLI bao, khong cham dong do.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import device_app, fo_flow, net_ctl
from . import gen_ngam_may as may
from . import gen_ngam_tao as tao
from . import gen_ngam_thao_tac as tt
from .gen_ngam_cham import So

POPUP_HOME_RE = r"^Add Widget$|rate us|Daily Check|Check-in|Get notified when it"


class LaiHut(Exception):
    """Tool khong lai toi man can do (khong phai hanh vi app) - khong cham, bao ro de sua cong thuc."""


@dataclass
class Ctx:
    client: object
    serial: str
    package: str
    ct: dict
    so: So
    out: Path
    log: object
    nho: dict = field(default_factory=dict)      # hop_ok, so lan tao anh thanh cong...

    async def nhin(self):
        return await may.nhin(self.client, self.serial, self.package)


def _s(x: float) -> str:
    return f"{x:.1f}s"


def _can(kq: dict, buoc: str) -> dict:
    if kq.get("loi"):
        raise LaiHut(f"{buoc}: {kq['loi']}")
    return kq


async def _cho_xong(c: Ctx, tu: float, so: int, giay: float = 300.0) -> list:
    return await tao.cho_worker(c.client, c.serial, tu, so, giay)


async def _popup_home(c: Ctx, giay: float) -> list[str]:
    """Nhin Home `giay` giay: cac popup (widget / rate / check-in / xin quyen) hien."""
    het = await may.gio(c.client, c.serial) + giay
    thay: list[str] = []
    while True:
        m = await c.nhin()
        thay += [s for s in m.chu() if re.search(POPUP_HOME_RE, s, re.I) and s not in thay]
        if m.t > het:
            return thay
        await asyncio.sleep(0.3)


async def vao_nhom(c: Ctx, cho_phep: bool = True) -> dict:
    v = await tao.mo_lanh_user_moi(c.client, c.serial, c.package, cho_phep)
    if not v["home"]:
        raise LaiHut("mở lạnh user mới không lái được tới Home")
    v["sub"] = await tao.dam_bao_premium(c.client, c.serial, c.package, v["premium"])
    c.nho["anh_bat_dau"] = 0          # dem lan tao anh bat dau duoc trong nhom (pm clear dat lai luot ngay)
    if not cho_phep:
        await giu_tu_choi_quyen(c)
    c.log(f"  vào nhóm: hỏi quyền={v['hoi_quyen']} · premium={v['sub']}")
    return v


async def giu_tu_choi_quyen(c: Ctx) -> None:
    """Mua lai goi test -> mo lanh lai app -> app hoi quyen thong bao lan nua va bo lai FO bam Cho phep (luot 16/11
    S01-01 FAIL gia). Nhom can user DA TU CHOI: thu hoi lai, dat co user-set nhu sau mot lan bam Don't allow."""
    q = "android.permission.POST_NOTIFICATIONS"
    out, _, _ = await c.client.shell(c.serial, "dumpsys", "package", c.package)
    if re.search(r"POST_NOTIFICATIONS: granted=true", out or ""):
        await c.client.shell(c.serial, "pm", "revoke", c.package, q)
        await c.client.shell(c.serial, "pm", "set-permission-flags", c.package, q, "user-set")
        c.log("  quyền thông báo bị cấp lại khi mở lạnh sau mua gói → thu hồi, giữ trạng thái đã từ chối")


# ---------------- R01: anh xong truoc moc popup ----------------

async def nhom_r01(c: Ctx) -> None:
    so, ct = c.so, c.ct
    for k in ("GEN-R01-02", "GEN-R01-03", "GEN-R01-04", "GEN-R01-05"):
        so.ep(k, "nhóm R01 đặt generating_wait_image_seconds=45 (Test Data 15) để ảnh (server 30–34s) xong trước mốc "
                 "popup — user chốt 16/11/2026")
    v = await vao_nhom(c)
    so.ghi("GEN-R01-01", "xin quyền thông báo", v["hoi_quyen"],
           "mở app lần đầu sau clear data: " + ("hiện hộp thoại hệ thống xin quyền thông báo, bấm Allow"
                                                if v["hoi_quyen"] else "không hiện hộp thoại xin quyền thông báo"))
    so.ghi("GEN-R01-01", "trạng thái Premium", v["sub"]["premium"],
           f"log billing verifyPurchased SUBS: premium={v['sub']['premium']}"
           + (" (mua gói test weekly)" if v["sub"]["mua"] else ""))
    m = await tao.ve_main(c.client, c.serial, c.package, ct)
    ls = m.tim(ct["lich_su"])
    so.ghi("GEN-R01-01", "nút đồng hồ", ls is not None and ls.bounds.top < 400,
           f"Home: nút History {'ở ' + str(ls.bounds) if ls else 'không có'}")
    so.ghi("GEN-R01-01", "không có badge", may.badge(m, ct) == 0, f"số trên nút History = {may.badge(m, ct)}")

    # TC R01: "chon 1 style (T2I, khong go mo ta)". App co man T2I: AIP893 (18/11/2026) bam Generate khi o mo ta trong
    # khong phan hoi -> go prompt (ghi ro trong report). App chi co style: style + anh nhu cu.
    kq = _can(await tao.tao_quay(c.client, c.serial, c.package, ct, "anh", "doi", c.out, "r01", kieu="t2i"),
              "R01-02 tạo ảnh")
    vao_s = kq["log_vao"] - kq["t_confirm"] if kq.get("log_vao") else -1
    so.ghi("GEN-R01-02", "Không có ads thưởng", not kq["ad"] and 0 <= vao_s < 2.5,
           f"Confirm → ProcessingActivity sau {_s(vao_s)}, AdActivity: {'có' if kq['ad'] else 'không'}")
    creating = [p for p in kq["push_luc_cho"] if re.search(ct["push_dang_tao"], p["text"] + p["title"])]
    so.ghi("GEN-R01-02", "Creating your content", bool(creating),
           f"thông báo lúc ở màn chờ: {[(p['title'], p['text']) for p in kq['push_luc_cho']]}")
    xong = await _cho_xong(c, kq["t_confirm"], 1, 90)
    m = await c.nhin()
    tg = xong[0][0] - kq["log_vao"] if xong and kq.get("log_vao") else -1
    so.ghi("GEN-R01-03", "Vào thẳng màn Kết quả", re.search(ct["man_ket_qua"], kq.get("ra_man", "")) and
           not kq["popup"], f"ảnh xong sau {_s(tg)} ở màn chờ → {kq.get('ra_man') or kq['roi_toi']}; popup đếm "
           f"ngược: {'không' if not kq['popup'] else kq['popup']}")
    pu = await may.push(c.client, c.serial, c.package)
    toast = m.tim(ct["toast_xong"])
    so.ghi("GEN-R01-03", "Không có toast", toast is None and not any(
        re.search(ct["push_xong"], p["title"] + p["text"]) for p in pu),
        f"ở Kết quả: toast {'có' if toast else 'không'}; thông báo: {[(p['title'], p['text']) for p in pu]}")
    so.ghi("GEN-R01-03", "đã tự mất", not any(re.search(ct["push_dang_tao"], p["text"]) for p in pu),
           f"thông báo sau khi xong: {[(p['title'], p['text']) for p in pu] or 'không còn'}")
    rate = m.tim(ct["rate"]) or (await may.cho(c.client, c.serial, c.package, lambda x: x.tim(ct["rate"]), 4.0))
    so.ghi("GEN-R01-03", "popup rate", bool(rate), "Kết quả " + ("hiện popup 'Please rate us…'" if rate else
                                                             "không hiện popup rate trong 4s"))
    sv = await tt.luu(c.client, c.serial, c.package, ct)
    if sv.get("loi"):
        raise LaiHut(f"R01-04: {sv['loi']}")
    so.ghi("GEN-R01-04", "Lưu thành công", bool(sv["t_xong"]),
           f"bấm lưu → {sv.get('cach') or 'chữ đã lưu'} sau {_s(sv['t_xong'] - sv['t_bam'])}" if sv["t_xong"]
           else "không đổi sang 'Saved'")
    anh = [t for t in sv["tep"] if t["bang"] == "images" and t["mime"].startswith("image/")]
    so.ghi("GEN-R01-04", "Ảnh có trong Thư viện", bool(anh), f"MediaStore {ct['thu_muc_luu']}: {sv['tep']}")

    m = await tao.mo_lich_su(c.client, c.serial, c.package, ct)
    if m is None:
        raise LaiHut("R01-05: không mở được History")
    o = may.o_lich_su(m, ct)
    dau = o[0] if o else {}
    nhan = re.search(r"\b(?:Image|Video|Ảnh)\b", dau.get("chu", "") + " " + " ".join(
        n.text for n in m.nodes if n.text))
    so.ghi("GEN-R01-05", "nằm trên cùng", bool(dau) and dau["ten"] == kq["style"] and bool(nhan),
           f"ô đầu History: tên '{dau.get('ten')}' (style vừa tạo '{kq['style']}'), chữ trong ô [{dau.get('chu')}], "
           + ("có nhãn Image/Video" if nhan else "KHÔNG có nhãn Image/Video"))
    await device_app.tap(c.client, c.serial, *dau["xy"])
    kqm = await may.cho(c.client, c.serial, c.package, lambda x: x.o(ct["man_ket_qua"]), 10.0)
    rate2 = kqm and (kqm.tim(ct["rate"]) or await may.cho(c.client, c.serial, c.package,
                                                         lambda x: x.tim(ct["rate"]), 3.0))
    so.ghi("GEN-R01-05", "không có popup rate", bool(kqm) and not rate2,
           f"bấm ô → {kqm.act if kqm else 'không tới Kết quả'}; popup rate: {'có' if rate2 else 'không'}")


# ---------------- R02 - R05, R08: config Test Data chung ----------------

async def nhom_chung(c: Ctx) -> None:
    from . import gen_ngam_nhom_chung_2 as tiep, gen_ngam_nhom_sau as sau
    v = await vao_nhom(c, cho_phep=False)
    await sau.s01_trong_nhom(c, v)
    await xem_het_moi(c)            # R02-02 dem badge = 1: anh cua S01 phai da xem
    await tiep.r02_r03(c)
    await tiep.r04(c)
    await tiep.r05(c)
    await tiep.r08(c)
    await dem_het_luot_anh(c, "GEN-R01-06", "trừ đúng 1",
                           "đếm ở nhóm R02–R08 cùng lượt, config đúng Test Data R01 (limit_gen_image_sub_per_day=10)")


async def nhom_dem_r01(c: Ctx) -> None:
    """Chi dem het luot anh cho R01-06 (cung Test Data R01) - khi nhom chung hong o buoc cuoi, khoi chay lai ca nhom."""
    await vao_nhom(c)
    await dem_het_luot_anh(c, "GEN-R01-06", "trừ đúng 1",
                           "đếm riêng sau clear data, config đúng Test Data R01 (limit_gen_image_sub_per_day=10)")


async def dem_het_luot_anh(c: Ctx, case: str, mau: str, ghi_chu: str, toi_da: int = 10) -> int:
    """Tao anh lien tiep (bam OK o giay 12,6) toi khi app bao het luot. Tong lan tao duoc trong nhom = `toi_da` ->
    moi lan tru dung 1 luot. Khong vao man cho ma chua het luot (dang chay du max_concurrent) -> doi mot luot xong."""
    ct = c.ct
    het = ""
    for _ in range(toi_da + 8):
        tu = await may.gio(c.client, c.serial)
        kq = await tao.tao(c.client, c.serial, c.package, ct, "anh", "doi", ok_luc=12.6, hop_ok=c.so.nho.get("hop_ok") or c.ct.get("popup_hop_ok"))
        if kq.get("loi"):
            raise LaiHut(f"{case}: {kq['loi']}")
        if kq["het_luot"]:
            het = kq["het_luot"]
            await bam_dong_het_luot(c)
            break
        if kq["t_cho"]:
            c.nho["anh_bat_dau"] = c.nho.get("anh_bat_dau", 0) + 1
            continue
        m = await c.nhin()
        c.log(f"  ảnh không vào màn chờ ({m.chu()[:5]}) → chờ một lượt xong rồi thử lại")
        await tao.ve_main(c.client, c.serial, c.package, ct)
        await _cho_xong(c, tu - 60, 1, 120)
    dung = c.nho.get("anh_bat_dau", 0)
    c.so.ghi(case, mau, dung == toi_da and bool(het),
             f"tạo được {dung} ảnh trong nhóm rồi app báo '{het or 'không chặn'}' ({ghi_chu}) → mỗi lần trừ "
             + ("đúng 1" if dung == toi_da else f"lệch (limit {toi_da})"))
    return dung


async def xem_het_moi(c: Ctx) -> None:
    """Mo tung o 'New' trong History cho het badge (anh cua case truoc chua xem). App khong co nhan New (AIP893
    Compose 18/11/2026): badge Home > 0 thi mo lan luot o tu tren xuong toi khi badge ve 0."""
    for i in range(4):
        m = await tao.mo_lich_su(c.client, c.serial, c.package, c.ct)
        cac_o = may.o_lich_su(m, c.ct) if m else []
        moi = [o for o in cac_o if o["moi"]]
        if not moi and cac_o and not any(o["moi"] for o in cac_o):
            home = await tao.ve_main(c.client, c.serial, c.package, c.ct)
            c.log(f"  xem kết quả chưa xem: badge Home = {may.badge(home, c.ct)}, History {len(cac_o)} ô, lần {i + 1}")
            if may.badge(home, c.ct) == 0 or i >= len(cac_o):
                break
            m = await tao.mo_lich_su(c.client, c.serial, c.package, c.ct)
            cac_o = may.o_lich_su(m, c.ct) if m else []
            moi = [o for o in cac_o if not o["dang_tao"]][i:i + 1]
        if not moi:
            break
        await device_app.tap(c.client, c.serial, *moi[0]["xy"])
        await may.cho(c.client, c.serial, c.package, lambda x: x.o(c.ct["man_ket_qua"]), 10.0)
        await tao.dong_rate(c.client, c.serial, c.package, c.ct)
        await tao.back(c.client, c.serial)
    await tao.ve_main(c.client, c.serial, c.package, c.ct)


async def bam_dong_het_luot(c: Ctx) -> None:
    m = await c.nhin()
    nut = m.tim(c.ct.get("het_luot_dong") or "$^")
    if nut is not None:
        await tao.bam(c.client, c.serial, nut)


async def net(c: Ctx, bat: bool) -> dict:
    return await (net_ctl.bat if bat else net_ctl.tat)(c.client, c.serial)


async def mo_lai_vao_home(c: Ctx) -> None:
    """Kill + mo lai bang icon, lai FO toi Home KHONG dong popup (R08-01 can nhin popup Home)."""
    await c.client.shell(c.serial, "am", "force-stop", c.package)
    await asyncio.sleep(1.0)
    await device_app.launch(c.client, c.serial, c.package)
    await asyncio.sleep(2.0)
    await fo_flow.walk_to(c.client, c.serial, c.package, c.ct["man_home"])
