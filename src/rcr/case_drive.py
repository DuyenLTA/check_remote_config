"""Lai app qua tung buoc Action cua case, sau khi config da duoc dat.

Moi buoc: chup UI -> dich thanh thao tac -> lam -> ghi lai. Dung NGAY khi gap
buoc khong dich duoc: di tiep voi man hinh sai thi moi thu sau do deu vo nghia.

Buoc noi "di toi mot man hinh" (`GoTo`) khong tu bam mo: giao cho `fo_flow`
lai theo luat o `data/fo_flow.yaml`. Truoc day moi buoc dang nay deu la
NEEDS_HUMAN, trong khi bo luat da biet duong di - case dung lai o buoc 2 du
tool thua suc di tiep.

Buoc VUOT khong bi chan khi quang cao che man: vuot khong bam trung thu gi nen
khong the bam nham vao quang cao, va dung cai dang duoc test (icon SWIPE thay
cho vung ad) lai nam o man co quang cao.

HAI CHO TU CHOI THAO TAC, co y:
  - quang cao dang che man hinh -> khong tu tim nut X. Nut dong quang cao nho,
    lech vai pixel la bam vao chinh quang cao (mo trinh duyet, co khi mua hang).
  - man hinh khong phai cua app dich (app khac bung len) -> dung, bao nguoi.

Dump sau moi buoc duoc giu lai de phase 5 cham - khong phai chup lai lan nua.
"""

from __future__ import annotations

import asyncio
import logging
import time

from . import (act_compound, act_exec, act_resolver, device_app, drive_probes, fo_flow,
               fo_steps, screencap, ui_dump)

log = logging.getLogger(__name__)

AD_HINTS = ("adactivity", "com.google.android.gms.ads")


def _noop(_msg: str) -> None:
    pass


def _di_qua(man_can: str | None, target: str) -> bool:
    """Buoc nay lai QUA man ma case can quan sat?

    `man_can` None nghia la khong biet case noi ve man nao -> di het nhu TC bao.
    """
    return man_can is not None and fo_flow.thu_tu(target) > fo_flow.thu_tu(man_can)


def blocking_screen(package: str, pkg: str, activity: str) -> str:
    """Man hinh hien tai co can nguoi xu ly truoc khong -> ly do, "" neu on."""
    if any(h in activity.casefold() for h in AD_HINTS):
        return (
            f"quang cao dang che man hinh ({activity}) - tool khong tu bam nut dong "
            "(bam lech la vao chinh quang cao). Dong quang cao roi chay lai"
        )
    if pkg and pkg != package:
        return f"man hinh dang o {pkg}, khong phai {package}"
    if not pkg:
        return "khong doc duoc man hinh dang hien (may khoa?)"
    return ""


async def drive(client, serial: str, package: str, steps, log_fn=_noop,
                man_can: str | None = None, thu_vuot: bool = False) -> dict:
    """Chay lan luot cac buoc. Tra nhat ky tung buoc + dump de phase 5 cham.

    Man hinh bi che CHI chan buoc phai cham vao man hinh. Buoc quan sat va buoc
    cho van di tiep: case ads cham bang log request/load, va inter thuong de len
    truoc khi kip nhin thay banner - dung o day la bao hong mot case dang chay dung.

    Moc "Tai t0+Ns": t0 la luc vua toi man cua case (dau luot lai, hoac sau
    buoc di toi man gan nhat) - CHUA phai luc ad show, viec do can do log rieng.
    """
    done: list[dict] = []
    blocked_steps: list[int] = []
    ctx, dump_cu = act_exec.ctx_moi(), ""
    t0 = time.monotonic()
    for index, raw in enumerate(steps, 1):
        moc = act_compound.moc_t0(raw)
        step = moc[1] if moc else raw
        if moc:
            await asyncio.sleep(max(0.0, t0 + moc[0] - time.monotonic()))
        pkg, activity = await device_app.focus(client, serial)
        blocked = blocking_screen(package, pkg, activity)
        action = act_resolver.resolve(step, [])
        if moc and not isinstance(action, (act_resolver.Tap, act_resolver.NeedsHuman)):
            # Buoc co moc gio va KHONG can cay node: lam ngay, khong dump/chup
            # truoc (mat 2-5s) - tre la lech khoi moc ma case dang do.
            record = {"n": index, "step": raw, "action": action.summary, "activity": activity}
        else:
            xml = await ui_dump.dump(client, serial)
            # Chup cung luc voi dump -> anh va cay node ta CUNG mot man hinh.
            shot = await screencap.capture(client, serial)
            nodes = ui_dump.app_nodes(ui_dump.parse_dump(xml), package)
            anim = {} if moc else await drive_probes._do_animation(client, serial, nodes)
            trang = fo_steps.onboarding_page(nodes)
            if trang:                      # doc duoc thi lay lam moc, bo so dem cu
                ctx["trang_cu"], ctx["vuot_sau"] = trang, 0
            dump_cu = xml
            action = act_resolver.resolve(step, nodes)
            record = {"n": index, "step": raw, "action": action.summary,
                      "activity": activity, "dump": xml,
                      "shot": shot["thumb"], "shot_warning": shot["warning"]}
            if anim:
                record["anim"] = anim
        if moc:
            record["moc"] = {"t0_cong": moc[0], "lam_luc": round(time.monotonic() - t0, 1),
                             "ghi_chu": "t0 = lúc vừa tới màn, chưa đo lúc ad show"}
        if blocked:
            # Ghi lai de phase 5 biet dump nay KHONG phai UI cua app.
            record["screen_blocked"] = blocked
            blocked_steps.append(index)

        if isinstance(action, act_resolver.Tap) and blocked:
            record["action"] = {"kind": "needs_human", "reason": blocked}
            log_fn(f"    buoc {index}: DUNG - {blocked}")
            done.append(record)
            return {"steps": done, "status": "NEEDS_HUMAN", "stopped_at": index,
                    "blocked_steps": blocked_steps}

        log_fn(f"    buoc {index}: {raw!r} -> {action.summary['kind']}"
               + (f" (man hinh bi che: {activity})" if blocked else ""))
        done.append(record)

        if isinstance(action, act_resolver.GoTo) and _di_qua(man_can, action.target):
            # Buoc TC bao di tiep, nhung key cua case nam o man truoc do roi:
            # doc log o day la du. 16 thao tac de toi Home ton ~90 giay va
            # khong them mot so do nao cho case nay.
            record["action"] = {"kind": "noop", "target": action.target,
                                "reason": f"key của case nằm ở {man_can or 'splash'}, "
                                          f"không cần đi tiếp tới {action.target}"}
            log_fn(f"    buoc {index}: dung o {man_can or 'splash'}, bo buoc di toi {action.target}")
            continue
        if isinstance(action, act_resolver.GoTo):
            # Quang cao dang che van lai duoc: `fo_flow` co luat rieng cho
            # AdActivity (cho ad chay xong roi dong), khong phai tu mo nut X.
            walk = await fo_flow.walk_to(client, serial, package, action.target, log_fn=log_fn)
            if not walk["reached"]:
                # Lai hut thi phai noi ket o dau: "khong dich duoc buoc" se lam
                # nguoi doc di sua cau TC, trong khi loi nam o bo luat fo_flow.
                record["action"] = {
                    "kind": "needs_human",
                    "reason": f"không lái tới được {action.target}, dừng ở {walk['activity']}",
                }
                return {"steps": done, "status": "NEEDS_HUMAN", "stopped_at": index,
                        "blocked_steps": blocked_steps}
            record["action"] = {"kind": "goto", "target": action.target,
                                "activity": walk["activity"], "reason": action.reason}
            t0 = time.monotonic()
            if action.cho:
                await asyncio.sleep(action.cho)
            continue
        if isinstance(action, act_resolver.NeedsHuman):
            return {"steps": done, "status": "NEEDS_HUMAN", "stopped_at": index,
                    "blocked_steps": blocked_steps}
        if await act_exec.resume_neu_o_nen(client, serial, package, step, record, ctx):
            continue
        await act_exec.lam(client, serial, action, record, ctx, log_fn)
    cuoi = await drive_probes._chup_ket(client, serial, package, len(done) + 1,
                           ctx["trang_cu"], ctx["vuot_sau"], dump_cu)
    done.append(cuoi)
    ra = {"steps": done, "status": "DONE", "stopped_at": 0,
          "blocked_steps": blocked_steps, "final": cuoi}
    if thu_vuot:
        ra["thu_vuot"] = await drive_probes._thu_vuot(client, serial, package, cuoi, len(done) + 1)
        done.append(ra["thu_vuot"]["anh"])
    return ra
