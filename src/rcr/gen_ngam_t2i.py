"""Tab TC "gen ngam": tao anh bang Text to Image (T2I) - app co man T2I rieng (AIP893 18/11/2026: AI Studio ->
"Text to Image Generate" -> o "What do you have in mind?" -> chon style duoi "Choose your style" -> Generate).

TC gen ngam ghi "Tao anh T2I prompt dai" o hau het case; app chi co style (BeautyGenie) thi khong khai `t2i` ->
`gen_ngam_tao.tao` van tao bang style + anh. Cong thuc (`data/gen_ngam_cong_thuc.yaml`, muc `t2i` cua app):
  mo: regex nut mo man T2I o Home      o: regex chu goi y cua o nhap      style_duoi: regex tieu de hang style
  nut: regex nut tao                    prompt: chu go vao o (prompt dai ~300 ky tu, >= 5 dong tren man)
"""

from __future__ import annotations

import asyncio
import shlex

from . import device_app, rating_cong_thuc
from . import gen_ngam_may as may

PROMPT_MAC_DINH = (
    "A cozy mountain cabin at sunset with warm lights glowing through frosted windows, snow covered pine trees "
    "around, a winding river reflecting orange and purple sky, detailed photorealistic style, soft cinematic lighting, "
    "wide angle lens, high detail textures on wood and stone, smoke rising from the chimney")


async def _ban_phim_mo(client, serial) -> bool:
    out, _, _ = await client.shell(serial, "dumpsys", "input_method", "|", "grep", "mInputShown")
    return "mInputShown=true" in (out or "")


async def bat_dau(client, serial, package, ct, ve_home, co_prompt: bool = True) -> dict:
    """Mo man T2I tu Home, go prompt (xoa chu cu), chon style dau tien, bam tao. {t_confirm, style} hoac {loi}.
    `ve_home(...)` = ham ve Home cua gen_ngam_tao (truyen vao de tranh import vong)."""
    cf = ct["t2i"]
    m = await ve_home(client, serial, package, ct, "tab_home")
    nut_mo = m.tim(cf["mo"])
    if nut_mo is None:
        return {"loi": f"Home không có nút mở T2I ({cf['mo']})"}
    await device_app.tap(client, serial, *nut_mo.bounds.center)
    m = await may.cho(client, serial, package, lambda x: x.tim(cf["o"]) is not None or x.tim(r"^\d+/\d+$") is not None, 15.0)
    if m is None:
        return {"loi": "bấm mở T2I không tới màn nhập prompt"}
    o = m.tim(cf["o"]) or next((n for n in m.nodes if n.text and len(n.text) > 40 and n.bounds.top < 800), None)
    if o is None:
        return {"loi": "màn T2I không có ô nhập prompt"}
    await device_app.tap(client, serial, *o.bounds.center)
    await asyncio.sleep(0.8)
    # O co the con prompt lan truoc (app giu chu) -> xoa sach roi go.
    await client.shell(serial, "input", "keyevent", "KEYCODE_MOVE_END", *(["KEYCODE_DEL"] * 520))
    chu = (cf.get("prompt") or PROMPT_MAC_DINH) if co_prompt else ""
    if chu:
        await client.shell(serial, "input", "text", shlex.quote(chu.replace(" ", "%s")))
    await asyncio.sleep(0.8)
    if await _ban_phim_mo(client, serial):
        await client.shell(serial, "input", "keyevent", "KEYCODE_BACK")
        await asyncio.sleep(0.8)
    m = await may.nhin(client, serial, package)
    the = rating_cong_thuc.tim_duoi(m.nodes, cf["style_duoi"])
    if the is None:
        return {"loi": f"màn T2I không có thẻ style dưới '{cf['style_duoi']}'"}
    ten = the.content_desc or the.text          # ten style (History cua app co the ghi ten nay)
    await device_app.tap(client, serial, *the.bounds.center)
    await asyncio.sleep(1.0)
    m = await may.nhin(client, serial, package)
    nut = next((n for n in m.tat_ca(cf["nut"]) if n.bounds.top > 1500), None)
    if nut is None:
        return {"loi": "màn T2I không có nút Generate", "style": ten}
    t = await may.gio(client, serial)
    await device_app.tap(client, serial, *nut.bounds.center)
    return {"t_confirm": t, "style": ten, "kieu": "t2i"}


def dung_t2i(ct: dict, loai: str, kieu: str | None) -> bool:
    """Tao anh bang T2I khi case goi `kieu="t2i"` (hoac "t2i_trong" = khong go mo ta) va app khai `t2i`. Mac dinh van style + anh: AIP893 (18/11/2026)
    anh T2I xong ~7s -> khong tao duoc dieu kien "anh > 15s" (popup / ve Home / tao ngam) cua TC; anh style ~28s."""
    return loai == "anh" and bool(ct.get("t2i")) and (kieu or "").startswith("t2i")
