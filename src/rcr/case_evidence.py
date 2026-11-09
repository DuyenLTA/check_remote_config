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
    rc_ids = ung_vien_id(ad_units.cho_package(baseline.package), dict(baseline.configs),
                         dict(overrides or {}))
    # Key RC ten khong mang ma vi tri ma SDK that su doc (`splash_inter_high_n_id` = 102-spl-n-inter-high, da do
    # trong data/ad_id_keys.yaml): them ten vi tri de dong "Inter 102 hien thi" quy duoc unit (AIP999 …794).
    rc_ids |= {f"id_{ma.replace('-', '_')}#{key}": rc_ids[key]
               for ma, key in ad_state._table().items() if key in rc_ids}
    units = ad_log.summary(parsed)
    for row in units.values():
        # Unit khong khop key nao: app hardcode ID, hoac lay tu key app khong doc.
        row["rc_keys"] = ad_log.match_rc_id(row["unit"], rc_ids, row["type"])
        # Log app chi in 3 so cuoi: hai vi tri trung duoi (AIP872: 202 high …2764762034 va 303 high
        # …8588924034) gop thanh MOT unit. Giu ID day du ung vien cua tung key de event Firebase
        # `ad_show` (co ID day du) tach lai dung vi tri (assert_ad_screen.show_theo_man).
        row["ids"] = {k: list(rc_ids.get(k) or ()) for k in row["rc_keys"]}
    # Vi tri DA BIET ID: log khong co unit nao cua vi tri do = vi tri do khong
    # duoc request, ket luan duoc. Khong biet ID thi im lang khong noi len gi.
    return {"pid": pid, "units": units, "banner_states": parsed["banner_states"],
            "positions": sorted({k[3:].split("#")[0] for k in rc_ids if k.startswith("id_")})}


def ung_vien_id(checklist: dict[str, str], rc: dict[str, str],
                overrides: dict[str, str] | None = None) -> dict[str, tuple[str, ...]]:
    """{key: cac ID ung vien} = ID trong RC + ID checklist cua team.

    Khong de ID RC DE MAT ID checklist: app SDK moi hardcode ID theo ten vi tri
    va khong doc `id_*` trong RC (AIP872 3.5.4: moi `id_*` trong RC deu khac
    checklist, log chi thay ID checklist). RC de len thi unit that thanh "khong
    khop vi tri nao" va hai vi tri trung duoi ID chi con mot key.
    Key case tu dat (`overrides`, vd ep unit fail bang ID gia) thi CHI lay ID do.
    """
    def _ids(d):
        return {k: v for k, v in (d or {}).items() if str(v).startswith("ca-app-pub")}
    rc, dat = _ids(rc), _ids(overrides)
    ra = {k: tuple(dict.fromkeys(i for i in (rc.get(k), checklist.get(k)) if i))
          for k in checklist.keys() | rc.keys()}
    return ra | {k: (v,) for k, v in dat.items()}


async def _dong_thoi_gian(client, baseline: RcBaseline, drive: dict) -> dict:
    """Dong thoi gian trang OB3 (ob3_log) + khung nhin lien tuc + moc tool thao tac."""
    pid = await sdk_probe.pid_of(client, baseline.serial, baseline.package)
    luot = ob3_log.luot_ghe(ob3_log.su_kien(await ob3_log.doc(client, baseline.serial, pid))) \
        if pid else []
    return {"luot": luot, "khung": drive.get("khung") or [], "thao_tac": drive.get("thao_tac") or []}
