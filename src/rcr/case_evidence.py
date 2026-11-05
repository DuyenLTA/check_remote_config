"""Thu bang chung cua mot luot: anh man vua lai toi, log ads, log su kien.

Tach khoi `case_run` de moi file duoi 200 dong: `case_run` lo trinh tu mot
case, file nay lo doc du lieu tu may ve cho khau cham.
"""

from __future__ import annotations

from . import ad_log, ad_state, ad_units, fa_log, ob3_log, screencap, sdk_probe, ui_dump
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
    sheet = ad_units.cho_package(baseline.package)
    rc_ids = sheet | {k: v for k, v in dang_chay.items() if v.startswith("ca-app-pub")}
    # RC khai `id_*` ma app KHONG dung (ID nam cung trong app, trung ID sheet): de RC de mat ID sheet thi unit that
    # trong log khong quy duoc ve vi tri, moi dong "native 201 hien thi" ra FAIL oan (AIP999 2.5.0, 04/11/2026:
    # RC id_201_lfo1_n_native_high …3653, app request …9039 dung sheet). Giu ca hai, ID sheet duoi ten "<key>#sheet".
    rc_ids |= {f"{k}#sheet": v for k, v in sheet.items() if rc_ids.get(k) != v}
    # Key RC ten khong mang ma vi tri ma SDK that su doc (`splash_inter_high_n_id` = 102-spl-n-inter-high, da do
    # trong data/ad_id_keys.yaml): them ten vi tri de dong "Inter 102 hien thi" quy duoc unit (AIP999 …794).
    rc_ids |= {f"id_{ma.replace('-', '_')}#{key}": rc_ids[key]
               for ma, key in ad_state._table().items() if key in rc_ids}
    units = ad_log.summary(parsed)
    for row in units.values():
        # Unit khong khop key nao: app hardcode ID, hoac lay tu key app khong doc.
        row["rc_keys"] = ad_log.match_rc_id(row["unit"], rc_ids, row["type"])
    # Vi tri DA BIET ID: log khong co unit nao cua vi tri do = vi tri do khong
    # duoc request, ket luan duoc. Khong biet ID thi im lang khong noi len gi.
    return {"pid": pid, "units": units, "banner_states": parsed["banner_states"],
            "positions": sorted({k[3:].split("#")[0] for k in rc_ids if k.startswith("id_")})}


async def _dong_thoi_gian(client, baseline: RcBaseline, drive: dict) -> dict:
    """Dong thoi gian trang OB3 (ob3_log) + khung nhin lien tuc + moc tool thao tac."""
    pid = await sdk_probe.pid_of(client, baseline.serial, baseline.package)
    luot = ob3_log.luot_ghe(ob3_log.su_kien(await ob3_log.doc(client, baseline.serial, pid))) \
        if pid else []
    return {"luot": luot, "khung": drive.get("khung") or [], "thao_tac": drive.get("thao_tac") or []}
