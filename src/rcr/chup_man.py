"""Giu dump + anh (+ so do mau) cua MOI man khac nhau ma `fo_flow.walk_to` di qua.

Truoc day lai luong chi giu man CUOI: case "Di tiep qua OB2" co dong Expected cho ca OB2 lan OB4, tool lai
toi OB4 thi dong OB2 ra "chua lai toi" / FAIL gia vi khong co dump nao cua OB2 (AIP886 31/10/2026, R01-04).
"""

from __future__ import annotations

from . import fo_steps, mau_chu, screencap, ui_dump


def tao(client, serial: str, package: str, mau_can=(), ghi: list | None = None, nhan: str = "lái luồng"):
    """-> (ham chup cho `walk_to(chup=...)`, list record da chup)."""
    ghi = [] if ghi is None else ghi
    da: set = set()

    async def chup(activity: str, xml: str) -> None:
        nodes = ui_dump.app_nodes(ui_dump.parse_dump(xml), package)
        chu = tuple(sorted({n.text for n in nodes if (n.text or "").strip()}))
        if not chu:
            return                  # man chua ve xong / chi co anh: khong co gi de cham chu
        khoa = (activity, fo_steps.onboarding_page(nodes), chu)
        if khoa in da:
            return
        da.add(khoa)
        shot = await screencap.capture(client, serial, giu_png=bool(mau_can))
        rec = {"step": f"{nhan}: màn {activity.split('.')[-1]}", "activity": activity, "dump": xml,
               "action": {"kind": "chup_man", "reason": "màn đi qua khi lái luồng — giữ lại để chấm chữ / màu"},
               "shot": shot.get("thumb", ""), "shot_warning": shot.get("warning", "")}
        if mau_can and shot.get("png"):
            rec["mau"] = mau_chu.do(nodes, shot["png"], list(mau_can))
        ghi.append(rec)

    return chup, ghi


def danh_so(records: list[dict], bat_dau: int) -> list[dict]:
    """Gan so buoc lien tiep cho record da chup (report va dong cham can `n`)."""
    for i, r in enumerate(records):
        r["n"] = bat_dau + i
    return records
