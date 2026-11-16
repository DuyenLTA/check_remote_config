"""Thao tac phu cua `rcr-gen-ngam` o man Ket qua / History: luu, xem video co phat, xoa nhieu o, bat toast he
thong, doc mau nen toast, mo lai app sau khi bi kill. Tra so do, khong ket luan.
"""

from __future__ import annotations

import asyncio
import io
import re

from . import device_app, fo_flow
from . import gen_ngam_may as may
from .gen_ngam_tao import bam, dong_rate



async def anh(client, serial: str):
    """Anh chup man hinh (PIL RGB)."""
    from PIL import Image
    png, _, _ = await client.run_binary("-s", serial, "exec-out", "screencap -p")
    return Image.open(io.BytesIO(png)).convert("RGB")


async def video_dang_phat(client, serial: str, hop) -> dict:
    """Hai anh cach 1,5s, so vung video: doi -> dang phat."""
    from PIL import ImageChops, ImageStat
    a = await anh(client, serial)
    await asyncio.sleep(1.5)
    b = await anh(client, serial)
    lech = ImageStat.Stat(ImageChops.difference(a.crop(hop), b.crop(hop)).convert("L")).mean[0]
    return {"lech": round(lech, 2), "phat": lech > 1.0}


def mau_nen(img, hop) -> tuple[int, int, int]:
    """Mau nen toast: pixel gan mep trai khung toast (giua chieu cao)."""
    l, t, r, b = hop
    return img.getpixel((max(0, l - 12), (t + b) // 2))


async def luu(client, serial, package, ct) -> dict:
    """Man Ket qua: dong rate, cuon toi nut luu, bam, cho chu da luu. {t_bam, t_xong, tep: [...]} (MediaStore)."""
    await dong_rate(client, serial, package, ct)
    m = await may.nhin(client, serial, package)
    nut = m.tim(ct["luu"])
    for _ in range(2):
        if nut is not None:
            break
        w, h = await device_app.screen_size(client, serial)
        await client.shell(serial, "input", "swipe", str(w // 2), str(h * 3 // 4), str(w // 2), str(h // 3), "300")
        await asyncio.sleep(1.0)
        m = await may.nhin(client, serial, package)
        nut = m.tim(ct["luu"])
    if nut is None:
        return {"loi": "không thấy nút lưu ở màn Kết quả"}
    t = await may.gio(client, serial)
    await bam(client, serial, nut, 0.2)
    xong = await may.cho(client, serial, package, lambda x: x.tim(ct["da_luu"]) is not None, 15.0)
    await asyncio.sleep(1.5)
    tep = await may.tep_moi(client, serial, ct["thu_muc_luu"], int(t) - 2)
    return {"t_bam": t, "t_xong": xong.t if xong else 0.0, "tep": tep}


async def xoa_hai(client, serial, package, ct) -> dict:
    """History: nhan giu o 1 -> chon nhieu, bam o 2, Delete, xac nhan. {chon_1, chon_2, hop_thoai, toast, truoc, sau}."""
    m = await may.nhin(client, serial, package)
    o = may.o_lich_su(m, ct)
    if len(o) < 2:
        return {"loi": f"History chỉ có {len(o)} ô"}
    x, y = o[0]["xy"]
    await client.shell(serial, "input", "swipe", str(x), str(y), str(x), str(y), "1200")
    await asyncio.sleep(1.0)
    m = await may.nhin(client, serial, package)
    c1 = m.tim(ct["chon_nhieu"])
    await device_app.tap(client, serial, *o[1]["xy"])
    await asyncio.sleep(1.0)
    m = await may.nhin(client, serial, package)
    c2 = m.tim(ct["chon_nhieu"])
    nut = sorted(m.tat_ca(ct["xoa"]), key=lambda n: -n.bounds.top)
    if not nut:
        return {"loi": "không thấy nút Delete ở chế độ chọn nhiều", "chon_1": c1 and c1.text}
    await bam(client, serial, nut[0], 1.0)
    m = await may.nhin(client, serial, package)
    hop = next((n.text for n in m.nodes if re.search(r"Delete \d+ item", n.text or "")), "")
    xn = sorted(m.tat_ca(ct["xoa"]), key=lambda n: n.bounds.top)
    if not xn:
        return {"loi": "không thấy hộp xác nhận xoá", "chon_1": c1 and c1.text, "chon_2": c2 and c2.text}

    await device_app.tap(client, serial, *xn[0].bounds.center)
    chu: list[str] = []
    het = await may.gio(client, serial) + 3.0
    while await may.gio(client, serial) < het and not chu:
        if await may.toast_he_thong(client, serial, package):
            chu.append("toast hệ thống của app đang hiện (dumpsys notification Toast Queue)")
        await asyncio.sleep(0.15)
    m = await may.nhin(client, serial, package)
    return {"chon_1": c1.text if c1 else "", "chon_2": c2.text if c2 else "", "hop_thoai": hop, "su_kien": chu,
            "toast_ui": [s for s in m.chu() if re.search(r"deleted", s, re.I)], "truoc": len(o),
            "sau": len(may.o_lich_su(m, ct)),
            # Dem o dang thay tren man khong phai tong so (luoi cuon) -> so ten o dau truoc / sau khi xoa 2 o dau.
            "dau_truoc": [x["ten"] for x in o[:4]], "dau_sau": [x["ten"] for x in may.o_lich_su(m, ct)[:2]]}


async def lai_toi(client, serial, package, ct, man: str, giay: float = 60.0) -> may.Man | None:
    """App vua mo lanh (bam push sau khi bi kill): lai qua Splash / Question / Billing toi man `man`."""
    het = await may.gio(client, serial) + giay
    while await may.gio(client, serial) < het:
        m = await may.nhin(client, serial, package)
        if m.o(man):
            return m
        if m.pkg == package and re.search(r"Splash|Question|Billing|Language|Onboarding|AdActivity", m.act):
            await fo_flow.walk_to(client, serial, package, man)
            continue
        await asyncio.sleep(1.0)
    return None
