"""Thu bang chung cua mot luot: anh man vua lai toi, log ads, log su kien.

Tach khoi `case_run` de moi file duoi 200 dong: `case_run` lo trinh tu mot
case, file nay lo doc du lieu tu may ve cho khau cham.
"""

from __future__ import annotations

from . import ad_log, ad_units, fa_log, ob3_log, screencap, sdk_probe, ui_dump
from .models import RcBaseline


async def _snapshot(client, baseline: RcBaseline, activity: str) -> dict:
    """Chup man vua lai toi: cham can bang chung, du case khong co buoc Action."""
    xml = await ui_dump.dump(client, baseline.serial)
    shot = await screencap.capture(client, baseline.serial)
    return {
        "status": "DONE", "stopped_at": 0, "blocked_steps": [], "walked": True,
        "steps": [{"n": 0, "step": f"lái tới {activity.split('.')[-1]}",
                   "action": {"kind": "walk"}, "activity": activity, "dump": xml,
                   "shot": shot["thumb"], "shot_warning": shot["warning"]}],
    }


async def _read_ads(client, baseline: RcBaseline, overrides=None) -> dict:
    pid = await sdk_probe.pid_of(client, baseline.serial, baseline.package)
    if not pid:
        return {"pid": "", "note": "app không còn chạy — không đọc được log quảng cáo"}
    parsed = ad_log.parse(await ad_log.read(client, baseline.serial, pid))
    # Checklist cua team truoc, ID doc tu may DE len tren: ID trong RC la cai
    # app that su dung, checklist chi la so team khai va co the cu hon build.
    # `overrides` DE LEN TREN baseline: case co the tu dat `id_*` (vd ep unit
    # fail bang mot ID khong ton tai). Tra bang ID cu thi unit trong log khong
    # khop vi tri nao, va dong Expected ve vi tri do thanh khong cham duoc.
    dang_chay = dict(baseline.configs) | dict(overrides or {})
    rc_ids = ad_units.cho_package(baseline.package) | {
        k: v for k, v in dang_chay.items() if v.startswith("ca-app-pub")
    }
    units = ad_log.summary(parsed)
    for row in units.values():
        # Unit khong khop key nao: app hardcode ID, hoac lay tu key app khong doc.
        row["rc_keys"] = ad_log.match_rc_id(row["unit"], rc_ids, row["type"])
    # Vi tri DA BIET ID: log khong co unit nao cua vi tri do = vi tri do khong
    # duoc request, ket luan duoc. Khong biet ID thi im lang khong noi len gi.
    return {"pid": pid, "units": units, "banner_states": parsed["banner_states"],
            "positions": sorted(k[3:] for k in rc_ids if k.startswith("id_"))}


async def _dong_thoi_gian(client, baseline: RcBaseline, drive: dict) -> dict:
    """Dong thoi gian trang OB3 (ob3_log) + khung nhin lien tuc + moc tool thao tac."""
    pid = await sdk_probe.pid_of(client, baseline.serial, baseline.package)
    luot = ob3_log.luot_ghe(ob3_log.su_kien(await ob3_log.doc(client, baseline.serial, pid))) \
        if pid else []
    return {"luot": luot, "khung": drive.get("khung") or [], "thao_tac": drive.get("thao_tac") or []}
