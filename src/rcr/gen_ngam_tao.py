"""Thao tac tab TC "gen ngam" (`rcr-gen-ngam`): mo lanh user moi, tao anh / video theo style + anh mau, theo doi man
cho (popup dem nguoc, tu ve Home), toast / push khi xong, History, luu, xoa, tat app khoi da nhiem.

Moi ham tra so do (gio may, chu doc duoc) - KHONG ket luan; `gen_ngam_kich_ban` cham tu so do do.
"""

from __future__ import annotations

import asyncio
import re
import subprocess
from pathlib import Path

from . import device_app, fo_flow, rating_cong_thuc, sub_log, sub_thao_tac, ui_dump
from . import gen_ngam_may as may

CHO_MAN = 15.0
CHO_CHO = 75.0          # toi da o man cho (anh 30-34s; video ve Home o giay 8)


async def bam(client, serial, node, cho: float = 1.0) -> None:
    await device_app.tap(client, serial, *node.bounds.center)
    await asyncio.sleep(cho)


async def back(client, serial, cho: float = 1.2) -> None:
    await client.shell(serial, "input", "keyevent", "KEYCODE_BACK")
    await asyncio.sleep(cho)


async def dong_rate(client, serial, package, ct, man=None) -> bool:
    """Popup danh gia dang che -> bam X (desc Close). BACK khong dong duoc popup nay (do 13/11/2026)."""
    man = man or await may.nhin(client, serial, package)
    if not man.tim(ct["rate"]):
        return False
    x = man.tim("^Close$")
    if x is None:
        # Nut X cua popup hien tre show_rating_button_x giay (AIP892 = 2s, 17/11/2026): BACK luc nay o Home la thoat
        # app (nhom chung / r06 lai hut ra launcher) -> cho X hien roi moi bam.
        m2 = await may.cho(client, serial, package, lambda x2: x2.tim("^Close$"), 5.0)
        x = m2.tim("^Close$") if m2 else None
    if x is None:
        return False
    await bam(client, serial, x, 1.2)
    return True


# ---- vao app ----

async def mo_lanh_user_moi(client, serial, package, cho_phep: bool) -> dict:
    """Clear data, thu hoi quyen thong bao, mo bang icon, tra loi hop thoai he thong, lai FO toi Home.
    {hoi_quyen, cho_phep, premium, home}."""
    for lenh in (("am", "force-stop", package), ("pm", "clear", package),
                 ("pm", "revoke", package, "android.permission.POST_NOTIFICATIONS"),
                 ("pm", "clear-permission-flags", package, "android.permission.POST_NOTIFICATIONS",
                  "user-set", "user-fixed"), ("logcat", "-c")):
        await client.shell(serial, *lenh)
    await device_app.launch(client, serial, package)
    hoi = await _tra_loi_quyen(client, serial, cho_phep)
    home = await sub_thao_tac.ve_home(client, serial, package)
    prem = None
    for _ in range(8):          # verifyPurchased SUBS co the den sau khi toi Home vai giay
        prem = sub_log.doc(await sub_thao_tac.log_billing(client, serial)).get("premium")
        if prem is not None:
            break
        await asyncio.sleep(2.0)
    return {"hoi_quyen": hoi, "cho_phep": cho_phep, "premium": prem, "home": home.get("reached")}


async def _tra_loi_quyen(client, serial, cho_phep: bool, giay: float = 12.0) -> bool:
    het = await may.gio(client, serial) + giay
    while await may.gio(client, serial) < het:
        nodes = ui_dump.parse_dump(await ui_dump.dump(client, serial))
        nut = next((n for n in nodes if n.resource_id.endswith(
            "permission_allow_button" if cho_phep else "permission_deny_button") and not n.bounds.empty), None)
        if nut:
            await bam(client, serial, nut, 1.5)
            return True
        await asyncio.sleep(0.5)
    return False


async def dam_bao_premium(client, serial, package, premium) -> dict:
    """Goi test weekly gia han 5 phut / lan: het han giua luot thi mua lai (Premium la precondition cua bo TC)."""
    if premium:
        return {"premium": True, "mua": False}
    if premium is None or premium is False:
        # Log khoi dong chua noi ro (query billing hong / cham): mo lanh lai doc cho chac truoc khi mua - mua lai
        # khi goi con han ton ~40s moi nhom (do 16/11/2026).
        # Ca khi da biet chua Premium: phien dau sau pm clear app dung danh sach SKU mac dinh (AIP892: vip.geni.*,
        # Play tra 0 san pham -> Paywall khong co gia); phai mo lanh lan nua cho app doc SKU tu RC (vip.makeup.*).
        lanh = await sub_thao_tac.mo_lanh(client, serial, package)
        await sub_thao_tac.ve_home(client, serial, package)
        if lanh.get("premium"):
            return {"premium": True, "mua": False}
    kq = await sub_thao_tac.mua(client, serial, package, "weekly", "approves", True)
    lanh = await sub_thao_tac.mo_lanh(client, serial, package)
    await sub_thao_tac.ve_home(client, serial, package)
    return {"premium": bool(lanh.get("premium") or (kq.get("log") or {}).get("premium")), "mua": True,
            "la_test": bool((kq.get("popup") or {}).get("la_test"))}


async def ve_main(client, serial, package, ct) -> may.Man:
    """BACK (dong rate truoc) toi MainActivity; app khong o truoc thi mo lai."""
    for _ in range(6):
        m = await may.nhin(client, serial, package)
        if m.pkg != package:
            await device_app.launch(client, serial, package)
            await asyncio.sleep(2.5)
            continue
        if m.o(ct["man_home"]) and not m.tim(ct["rate"]):
            return m
        if re.search(r"Splash|Question|Billing|Language|Onboarding", m.act or ""):
            # App vua mo lanh lai (bam push sau khi bi tat, kill...) dang o FO -> lai qua FO, BACK o day la thoat app.
            await fo_flow.walk_to(client, serial, package, ct["man_home"])
            continue
        if not await dong_rate(client, serial, package, ct, m):
            await back(client, serial)
    return await may.nhin(client, serial, package)


def dang_o_tab(m: may.Man, ct: dict, tab: str) -> bool:
    """Tab Image / Video Studio: tieu de cung chu voi nut tab, nam o dau man (nut tab nam o day man)."""
    if tab == "tab_home":
        return m.o(ct["man_home"]) and not any(n.bounds.top < 400 for n in m.tat_ca(ct["tab_anh"] + "|" + ct["tab_video"]))
    return any(n.bounds.top < 400 for n in m.tat_ca(ct[tab]))


async def vao_tab(client, serial, package, ct, tab: str) -> may.Man:
    """Bam nut tab o thanh duoi roi KIEM tieu de: bam truot (luot 16/11 dem luot R01-06 dung o tab Home, chon nham
    the 'Before') -> bam lai, toi da 3 lan."""
    m = await ve_main(client, serial, package, ct)
    for _ in range(3):
        if dang_o_tab(m, ct, tab):
            return m
        nut = next((n for n in m.tat_ca(ct[tab]) if n.bounds.top > 1500), None) or m.tim(ct[tab])
        if nut is not None:
            await bam(client, serial, nut, 1.2)
        elif (ct.get("tab_toa_do") or {}).get(tab):
            # Pixel 4 (Android 12, BeautyGenie 2.2.0 16/11/2026): nut tab thanh duoi co chu nhung bounds rong
            # [0,0][0,0] -> bam theo ty le man khai trong cong thuc app.
            rong, cao = await device_app.screen_size(client, serial)
            x, y = ct["tab_toa_do"][tab]
            await device_app.tap(client, serial, int(rong * float(x)), int(cao * float(y)))
            await asyncio.sleep(1.2)
        m = await may.nhin(client, serial, package)
    return m


# ---- tao ----

async def tao_quay(client, serial, package, ct, loai: str, che_do: str, thu_muc, ten: str, style: int = 1,
                   hop: dict | None = None, **kw) -> dict:
    """`tao` co quay man hinh: them {"dem": phan tich popup dem nguoc theo khung hinh} (gen_ngam_quay)."""
    from . import gen_ngam_quay as quay
    hop = {"hop_dem": ct.get("popup_hop_dem"), "hop_tieu_de": ct.get("popup_hop_tieu_de"),
           **{k: v for k, v in (hop or {}).items() if v}}
    proc = await quay.bat(serial, ten, 60)
    await asyncio.sleep(0.8)
    try:
        kq = await tao(client, serial, package, ct, loai, che_do, style, **kw)
    finally:
        mp4 = await quay.dung(serial, ten, proc, thu_muc)
    if kq.get("loi"):
        return kq
    kq |= await gio_vao_ra_man_cho(client, serial, package, ct, kq)
    kq["video"] = str(mp4 or "")
    kq["_hop"] = hop
    return kq


def phan_tich_video(kq: dict) -> dict:
    """Tach khung video man cho (10-20s CPU) - goi SAU cac buoc can canh gio (History khi anh con dang tao, toast)."""
    from . import gen_ngam_quay as quay
    if kq.get("dem") or not kq.get("video"):
        return kq.get("dem") or {}
    hop = kq.get("_hop") or {}
    # Lan nhin UI (~2,1s) co the truot qua popup (luot 16/11 R07-02) -> dung khung popup da doc o lan truoc cung luot.
    hop_dem = kq.get("hop_dem") or hop.get("hop_dem")
    hop_td = kq.get("hop_tieu_de") or hop.get("hop_tieu_de") or hop_dem
    if not (hop_dem and kq.get("log_ra")):
        kq["dem"] = {"loi": "không có khung popup / mốc rời màn chờ để đo"}
        return kq["dem"]
    try:
        kq["dem"] = quay.phan_tich(quay.khung(Path(kq["video"])), hop_td, hop_dem, kq["log_ra"])
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        kq["dem"] = {"loi": f"không tách được khung video: {exc}"}
    return kq["dem"]


async def tao(client, serial, package, ct, loai: str, che_do: str = "doi", style: int = 1, ok_luc: float = 0.0,
              hop_ok=None, popup_luc: float | None = None) -> dict:
    """Tab anh / video -> style thu `style` -> anh mau dau tien -> Confirm, roi theo doi man cho.

    che_do: "doi" = khong bam gi toi khi roi man cho; "ok" = bam OK ngay khi popup hien; "nhanh" = chi cho vao man cho
    roi tra (de tao lien tiep). So do: {t_confirm, t_cho (vao man cho), ad, het_luot, popup [(t, so)], t_ok, t_roi,
    roi_toi (Main/Result...), push_luc_cho, style}."""
    m = await vao_tab(client, serial, package, ct, "tab_anh" if loai == "anh" else "tab_video")
    if not dang_o_tab(m, ct, "tab_anh" if loai == "anh" else "tab_video"):
        return {"loi": f"không vào được tab {'tạo ảnh' if loai == 'anh' else 'tạo video'} ({m.act})"}
    the = [n for n in m.nodes if n.content_desc and not n.text and n.bounds.bottom - n.bounds.top > 300
           and n.bounds.top > 250]
    the.sort(key=lambda n: (n.bounds.top, n.bounds.left))
    if len(the) < style:
        return {"loi": f"không thấy thẻ style thứ {style} ở tab {loai}"}
    ten = the[style - 1].content_desc
    await bam(client, serial, the[style - 1], 0.5)
    m = await may.cho(client, serial, package, lambda x: x.o(ct["man_chon_anh"]) or x.o("AdActivity"), CHO_MAN)
    if m is None or not m.o(ct["man_chon_anh"]):
        return {"loi": f"bấm style '{ten}' không vào màn chọn ảnh ({m.act if m else '?'})", "style": ten}
    anh = rating_cong_thuc.tim_duoi(m.nodes, ct["mau"])
    ok = m.tim(ct["xac_nhan"])
    if anh is None or ok is None:
        return {"loi": "màn chọn ảnh không có ảnh mẫu / nút Confirm", "style": ten}
    await bam(client, serial, anh, 0.8)
    t_confirm = await may.gio(client, serial)
    await bam(client, serial, ok, 0.3)
    kq = {"style": ten, "loai": loai, "t_confirm": t_confirm, "popup": [], "ad": False, "het_luot": "",
          "push_luc_cho": [], "t_ok": 0.0, "t_roi": 0.0, "roi_toi": ""}
    if popup_luc is None:
        popup_luc = float(ct.get("popup_anh_giay" if loai == "anh" else "popup_video_giay") or 0)
    return kq | await theo_doi_cho(client, serial, package, ct, che_do, t_confirm, ok_luc, hop_ok, popup_luc)


async def _bam_ok_dung_giay(client, serial, package, ct, ok_luc: float, hop_ok) -> dict:
    """Nhin UI mat ~2,1s / lan nen "bam OK ngay khi popup hien" thanh bam o giay ~14,5. Popup hien dung giay 12,0
    (do bang khung video cung luot) -> canh vao man cho bang dumpsys (0,02s), toi `ok_luc` giay thi bam toa do nut OK
    da doc o lan popup truoc CUNG luot. Man cho Premium khong co ad nen bam truot cung khong trung gi."""
    t_vao = 0.0
    for _ in range(100):
        _p, act = await device_app.focus(client, serial)
        if re.search(ct["man_cho"], act or ""):
            t_vao = await may.gio(client, serial)
            break
        await asyncio.sleep(0.05)
    if not t_vao:
        return {}
    while await may.gio(client, serial) < t_vao + ok_luc:
        await asyncio.sleep(0.05)
    pkg, act = await device_app.focus(client, serial)
    if act and not re.search(ct["man_cho"], act):          # act rong = dialog popup dang giu focus -> van bam
        return {"t_vao_nhanh": t_vao}
    t = await may.gio(client, serial)
    await device_app.tap(client, serial, (hop_ok[0] + hop_ok[2]) // 2, (hop_ok[1] + hop_ok[3]) // 2)
    return {"t_vao_nhanh": t_vao, "t_ok": t}


async def _cho_vao(client, serial, ct, giay: float = 6.0) -> float:
    """Gio may luc ProcessingActivity len truoc (dumpsys window 0,02s/lan). Khong vao trong `giay` -> 0."""
    het = await may.gio(client, serial) + giay
    while await may.gio(client, serial) < het:
        _p, act = await device_app.focus(client, serial)
        if re.search(ct["man_cho"], act or ""):
            return await may.gio(client, serial)
        await asyncio.sleep(0.05)
    return 0.0


async def theo_doi_cho(client, serial, package, ct, che_do: str, t0: float, ok_luc: float = 0.0,
                       hop_ok=None, popup_luc: float = 0.0) -> dict:
    kq = {"popup": [], "ad": False, "het_luot": "", "push_luc_cho": [], "t_ok": 0.0, "t_roi": 0.0, "roi_toi": "",
          "t_cho": 0.0}
    if ok_luc and hop_ok:
        kq |= await _bam_ok_dung_giay(client, serial, package, ct, ok_luc, hop_ok)
        # Da vao man cho (canh bang dumpsys) - lan nhin UI dau tien co the da o Home sau khi bam OK, nen t_cho lay
        # tu day (luot 16/11: t_cho = 0 -> dem luot tao ra 0-1 anh, R06/R07 FAIL gia).
        kq["t_cho"] = kq.get("t_vao_nhanh", 0.0)
    elif popup_luc and che_do == "doi":
        # Popup chi dung ~3s ma moi lan nhin ~2,1s -> co luc truot qua (luot 16/11 R02-01/R07-02 khong co khung popup
        # de tach video). Canh vao man cho bang dumpsys, doc push "Creating", roi nhin DUNG giay `popup_luc`.
        t_vao = await _cho_vao(client, serial, ct)
        if t_vao:
            kq["t_cho"] = t_vao
            for _ in range(20):
                kq["push_luc_cho"] = await may.push(client, serial, package)
                if any(re.search(ct["push_dang_tao"], x["text"] + x["title"]) for x in kq["push_luc_cho"]) or \
                        await may.gio(client, serial) > t_vao + popup_luc - 1.5:
                    break
                await asyncio.sleep(0.3)
            while await may.gio(client, serial) < t_vao + popup_luc:
                await asyncio.sleep(0.05)
    het = t0 + CHO_CHO
    while True:
        m = await may.nhin(client, serial, package)
        if m.o("AdActivity"):
            kq["ad"] = True
        lim = m.tim(ct["het_luot"])
        if lim is not None:
            kq["het_luot"] = lim.text or lim.content_desc
            return kq
        # Popup dem nguoc la dialog rieng: luc no giu focus, `dumpsys window` co the khong ra ten activity (act rong)
        # -> van coi la dang o man cho, khong ket thuc theo doi dung luc popup hien (luot 16/11 R02-01/R03-01).
        if m.o(ct["man_cho"]) or (m.pkg in ("", package) and (not m.act or m.tim(ct["popup_dem"]))):
            if not kq["t_cho"]:
                kq["t_cho"] = m.t
                if che_do == "nhanh":
                    return kq
            if not any(re.search(ct["push_dang_tao"], p["text"] + p["title"]) for p in kq["push_luc_cho"]):
                # Push "Creating..." len khi worker bat dau (~0,5-2s sau khi vao man cho): doc lai moi vong toi khi co.
                kq["push_luc_cho"] = await may.push(client, serial, package)
            p = m.tim(ct["popup_dem"])
            if p is not None:
                so = re.search(ct["popup_dem"], p.text or p.content_desc or "")
                kq["popup"].append((m.t, int(so.group(1)) if so else -1))
                tieu_de = m.tim(ct.get("popup_tieu_de") or "^Still generating")
                kq["hop_dem"] = [p.bounds.left, p.bounds.top, p.bounds.right, p.bounds.bottom]
                nut_ok = m.tim(ct["popup_ok"])
                if nut_ok is not None:
                    b = nut_ok.bounds
                    kq["hop_ok"] = [b.left, b.top, b.right, b.bottom]
                if tieu_de is not None:
                    b = tieu_de.bounds
                    kq["hop_tieu_de"] = [b.left, b.top, b.right, b.bottom]
                if che_do == "ok" and not kq["t_ok"]:
                    nut = m.tim(ct["popup_ok"])
                    if nut is not None:
                        kq["t_ok"] = await may.gio(client, serial)
                        await bam(client, serial, nut, 0.2)
        elif kq["t_cho"] or m.t > t0 + 8:
            kq["t_roi"], kq["roi_toi"] = m.t, m.act
            return kq
        if m.t > het:
            kq["roi_toi"] = f"vẫn ở {m.act} sau {CHO_CHO:.0f}s"
            return kq
        await asyncio.sleep(0.15)


async def gio_vao_ra_man_cho(client, serial, package, ct, kq: dict) -> dict:
    """Moc START ProcessingActivity / START man ke tiep tu logcat (chinh xac hon lan nhin UI ~1s)."""
    dong = await may.log(client, serial, kq["t_confirm"] - 1)
    mo = may.mo_man(dong, package)
    vao = next((t for t, a in mo if re.search(ct["man_cho"], a) and t >= kq["t_confirm"] - 0.5), 0.0)
    ra = next((t for t, a in mo if t > vao and not re.search(ct["man_cho"], a)), 0.0) if vao else 0.0
    return {"log_vao": vao, "log_ra": ra, "ra_man": next((a for t, a in mo if t == ra), "")}


async def cho_worker(client, serial, tu: float, so: int, giay: float = 300.0) -> list[tuple[float, str]]:
    """Cho toi khi co `so` ket qua GenerationWorker sau moc `tu`. Tra [(gio, SUCCESS|FAILURE)]."""
    het = await may.gio(client, serial) + giay
    kq: list = []
    while await may.gio(client, serial) < het:
        kq = [x for x in may.worker(await may.log(client, serial, tu)) if x[1] != "bat_dau"]
        if len(kq) >= so:
            return kq
        await asyncio.sleep(2.0)
    return kq


async def theo_doi_toast(client, serial, package, ct, giay: float) -> dict:
    """Nhin lien tuc: toast xong hien luc nao, an luc nao, co dem duoc may toast. {hien: [(t_hien, t_an)]}."""
    het = await may.gio(client, serial) + giay
    hien, dang = [], None
    while True:
        m = await may.nhin(client, serial, package)
        co = m.tim(ct["toast_xong"]) is not None
        if co and dang is None:
            dang = m.t
        elif not co and dang is not None:
            hien.append((dang, m.t))
            dang = None
            if m.t > het:
                break
        if m.t > het and dang is None:
            break
        if m.t > het + 15:
            hien.append((dang, 0.0))
            break
        await asyncio.sleep(0.1)
    return {"hien": hien}


async def mo_lich_su(client, serial, package, ct) -> may.Man | None:
    m = await may.nhin(client, serial, package)
    if not m.o(ct["man_lich_su"]):
        m = await ve_main(client, serial, package, ct)
        nut = m.tim(ct["lich_su"])
        if nut is None:
            return None
        await bam(client, serial, nut, 0.3)
    return await may.cho(client, serial, package, lambda x: x.o(ct["man_lich_su"]), CHO_MAN)


async def mo_shade_bam_push(client, serial, package, ct, thu: int = 1) -> dict:
    """Keo thanh thong bao, bam push xong thu `thu` cua app (tu tren xuong), cho app len truoc."""
    await client.shell(serial, "cmd", "statusbar", "expand-notifications")
    await asyncio.sleep(1.5)
    nodes = ui_dump.parse_dump(await ui_dump.dump(client, serial))
    ds = [n for n in nodes if re.search(ct["push_xong"], n.text or "", re.I) and not n.bounds.empty]
    ds.sort(key=lambda n: n.bounds.top)
    if len(ds) < thu:
        await client.shell(serial, "cmd", "statusbar", "collapse")
        return {"bam": False, "so_push": len(ds)}
    t = await may.gio(client, serial)
    await bam(client, serial, ds[thu - 1], 0.5)
    m = await may.cho(client, serial, package, lambda x: x.pkg == package and x.o(ct["man_ket_qua"]), 25.0)
    return {"bam": True, "so_push": len(ds), "t_bam": t, "toi": m.act if m else "", "man": m}


async def tat_khoi_da_nhiem(client, serial, package) -> bool:
    """Vuot the app len trong man da nhiem; con song thi `am kill` (giu thong bao, khong nhu force-stop)."""
    await client.shell(serial, "input", "keyevent", "KEYCODE_APP_SWITCH")
    await asyncio.sleep(1.5)
    w, h = await device_app.screen_size(client, serial)
    await client.shell(serial, "input", "swipe", str(w // 2), str(h // 2), str(w // 2), str(h // 10), "250")
    await asyncio.sleep(1.5)
    await client.shell(serial, "input", "keyevent", "KEYCODE_HOME")
    pid, _, _ = await client.shell(serial, "pidof", package)
    if pid.strip():
        await client.shell(serial, "am", "kill", package)
        await asyncio.sleep(1.0)
        pid, _, _ = await client.shell(serial, "pidof", package)
    return not pid.strip()
