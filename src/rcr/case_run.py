"""Chay mot case: chan bang DEX -> reset -> patch -> mo lai app -> verify -> restore.

Tach khoi cli_check de cli_check chi con doc tham so va in JSON. Tien do bao ra
ngoai qua `log` (cli truyen ham in stderr), module nay khong tu in.

THU TU KHONG DUOC DOI:
  1. soi DEX  - app khong doc key thi dung luon, khong ton mot luot mo app
  2. reset    - `pm clear` xoa luon file vua ghi, nen reset PHAI truoc patch
  3. patch -> mo lai -> verify -> restore

DIEM DE SAI: giu patch (`keep=True`) thi PHAI luu snapshot config goc ngay luc
do. Luot sau doc baseline se ra ban DA PATCH, luc do khong con duong nao biet
gia tri that nua.
"""

from __future__ import annotations

import logging

from . import (
    ad_log,
    assert_check,
    crash_log,
    case_drive,
    device_app,
    device_reset,
    dex_check,
    rc_baseline,
    rc_patch,
    rc_snapshot,
    rc_verify,
    sdk_probe,
)
from .models import RcBaseline

log = logging.getLogger(__name__)


def _noop(_msg: str) -> None:
    pass


async def apply_case(
    client, baseline: RcBaseline, overrides: dict[str, str], keep: bool, out_dir,
    steps=(), expects=(), log_fn=_noop,
) -> dict:
    """patch -> tat han app -> mo lai -> verify -> lai cac buoc -> restore.

    Lai buoc TRUOC khi restore: restore xong la config da ve cu, luc do bam gi
    tren app cung khong con dinh dang gi toi case nua.
    """
    snapshot = rc_snapshot.save(baseline, out_dir) if keep else None
    patched = await rc_patch.patch(client, baseline, overrides)

    # Xoa log TRUOC khi mo app: khong thi nhat log ads/crash cua luot truoc.
    await ad_log.clear(client, baseline.serial)
    await crash_log.clear(client, baseline.serial)
    launch = await device_app.restart(client, baseline.serial, baseline.package)
    result = await rc_verify.verify(client, baseline, overrides)

    out = {
        "overrides": overrides,
        "patched": list(patched.written),
        "launch": launch,
        "verify": result.summary,
        # Chi noi ve CONFIG, khong phai ve app: PASS/FAIL la viec cua nguoi mo app.
        "verdict": "CONFIG_OK" if result.ok else "BLOCKED",
        "restored": False,
    }
    if steps and result.ok:
        out["drive"] = await case_drive.drive(
            client, baseline.serial, baseline.package, steps, log_fn
        )
    # Cham case ads bang LOG, khong bang mat: inter load nhanh hon banner nen no
    # de len truoc khi kip nhin thay banner.
    out["ads"] = await _read_ads(client, baseline)
    out["crash"] = await crash_log.read(client, baseline.serial, baseline.package)
    if expects:
        out["assert"] = assert_check.check_all(
            expects, out["ads"], out.get("drive") or {}, out["crash"], tuple(baseline.configs)
        )
        # Config khong song thi chua test duoc gi - dung ket luan tu dong Expected.
        out["verdict"] = out["verdict"] if not result.ok else out["assert"]["verdict"]
    if keep:
        out["snapshot"] = str(snapshot)
    else:
        await rc_patch.restore(client, baseline)
        out["restored"] = True
    return out


async def _read_ads(client, baseline: RcBaseline) -> dict:
    pid = await sdk_probe.pid_of(client, baseline.serial, baseline.package)
    if not pid:
        return {"pid": "", "note": "app không còn chạy — không đọc được log quảng cáo"}
    parsed = ad_log.parse(await ad_log.read(client, baseline.serial, pid))
    rc_ids = {k: v for k, v in baseline.configs.items() if v.startswith("ca-app-pub")}
    units = ad_log.summary(parsed)
    for row in units.values():
        # Unit khong khop key nao: app hardcode ID, hoac lay tu key app khong doc.
        row["rc_keys"] = ad_log.match_rc_id(row["unit"], rc_ids)
    return {"pid": pid, "units": units, "banner_states": parsed["banner_states"]}


async def run_case(
    client, baseline: RcBaseline, runs, precondition: str = "", steps=(), expects=(),
    *, keep=False, out_dir=".", dex=True, log_fn=_noop,
) -> tuple[dict, RcBaseline]:
    """Chay tron mot case. Tra (ket qua, baseline dang dung).

    Baseline tra ve co the KHAC cai truyen vao: `pm clear` sinh lai file config,
    ban cu tro toi noi dung khong con nua.
    """
    keys = sorted({k for r in runs for k in r})
    if dex:
        log_fn(f"Soi {len(keys)} key trong DEX cua app...")
        used = await dex_check.check(client, baseline.serial, baseline.package, keys, out_dir)
        unused = [k for k, ok in used.items() if not ok]
        if unused:
            # Key co trong config Firebase KHAC voi app doc key do: template dung
            # chung nhieu app. Chay tiep la cham mot thu app chang he doc.
            log_fn("  app KHONG doc: " + ", ".join(unused) + " -> KEY_NOT_USED, khong mo app")
            return {"verdict": "KEY_NOT_USED", "keys_not_used": unused, "runs": []}, baseline
        log_fn("  app co doc het cac key nay")

    reset = await device_reset.prepare(client, baseline, precondition)
    log_fn(f"Reset: {reset['mode']}" + (f" (khop '{reset['matched']}')" if reset["matched"] else ""))
    if reset["baseline_stale"]:
        log_fn("  app da bi xoa data -> doc lai baseline")
        baseline = await rc_baseline.read(client, baseline.serial, baseline.package)

    out = await _apply_runs(client, baseline, runs, keep, out_dir, steps, expects, log_fn)
    return out | {"reset": reset}, baseline


async def _apply_runs(client, baseline, runs, keep, out_dir, steps, expects, log_fn) -> dict:
    """Case co gia tri lua chon -> nhieu luot. Verdict case = luot xau nhat."""
    done: list[dict] = []
    for index, overrides in enumerate(runs, 1):
        head = f"  luot {index}/{len(runs)}: " if len(runs) > 1 else "  "
        log_fn(head + ", ".join(f"{k}={v}" for k, v in overrides.items()))
        out = await apply_case(client, baseline, overrides, keep, out_dir, steps, expects, log_fn)
        log_fn(f"    foreground sau {out['launch']['waited_s']}s · verify: "
               f"{'CONFIG_OK' if out['verify']['ok'] else 'BLOCKED'} · verdict: {out['verdict']}")
        done.append(out)
    if keep:
        log_fn(f"  GIU patch tren may. Tra ve: rcr-check --package {baseline.package} --restore")
    else:
        log_fn("  da tra config ve nguyen trang")
    # Verdict cua case = luot xau nhat (cung thang bac voi tung dong Expected).
    return {"runs": done, "verdict": assert_check.worst(r["verdict"] for r in done)}


async def restore_saved(client, package: str, serial: str, out_dir) -> dict:
    """Tra config ve ban da luu o luot `--keep` truoc do, roi xoa snapshot.

    Xoa sau khi ghi thanh cong: de lai file la luot sau restore nham ve mot ban
    khong con dung voi may nua.
    """
    path = rc_snapshot.path_for(out_dir, package, serial)
    baseline = rc_snapshot.load(path)
    res = await rc_patch.restore(client, baseline)
    path.unlink(missing_ok=True)
    return {"restored": True, "written": list(res.written), "snapshot": str(path)}
