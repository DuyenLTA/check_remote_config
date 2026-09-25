"""Lai app qua tung buoc Action cua case, sau khi config da duoc dat.

Moi buoc: chup UI -> dich thanh thao tac -> lam -> ghi lai. Dung NGAY khi gap
buoc khong dich duoc: di tiep voi man hinh sai thi moi thu sau do deu vo nghia.

HAI CHO TU CHOI THAO TAC, co y:
  - quang cao dang che man hinh -> khong tu tim nut X. Nut dong quang cao nho,
    lech vai pixel la bam vao chinh quang cao (mo trinh duyet, co khi mua hang).
  - man hinh khong phai cua app dich (app khac bung len) -> dung, bao nguoi.

Dump sau moi buoc duoc giu lai de phase 5 cham - khong phai chup lai lan nua.
"""

from __future__ import annotations

import asyncio
import logging

from . import act_resolver, device_app, screencap, ui_dump

log = logging.getLogger(__name__)

AD_HINTS = ("adactivity", "com.google.android.gms.ads")


def _noop(_msg: str) -> None:
    pass


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


async def drive(client, serial: str, package: str, steps, log_fn=_noop) -> dict:
    """Chay lan luot cac buoc. Tra nhat ky tung buoc + dump de phase 5 cham.

    Man hinh bi che CHI chan buoc phai cham vao man hinh. Buoc quan sat va buoc
    cho van di tiep: case ads cham bang log request/load, va inter thuong de len
    truoc khi kip nhin thay banner - dung o day la bao hong mot case dang chay dung.
    """
    done: list[dict] = []
    blocked_steps: list[int] = []
    for index, step in enumerate(steps, 1):
        pkg, activity = await device_app.focus(client, serial)
        blocked = blocking_screen(package, pkg, activity)

        xml = await ui_dump.dump(client, serial)
        # Chup cung luc voi dump -> anh va cay node ta CUNG mot man hinh.
        shot = await screencap.capture(client, serial)
        nodes = ui_dump.app_nodes(ui_dump.parse_dump(xml), package)
        action = act_resolver.resolve(step, nodes)
        record = {"n": index, "step": step, "action": action.summary,
                  "activity": activity, "dump": xml,
                  "shot": shot["thumb"], "shot_warning": shot["warning"]}
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

        log_fn(f"    buoc {index}: {step!r} -> {action.summary['kind']}"
               + (f" (man hinh bi che: {activity})" if blocked else ""))
        done.append(record)

        if isinstance(action, act_resolver.NeedsHuman):
            return {"steps": done, "status": "NEEDS_HUMAN", "stopped_at": index,
                    "blocked_steps": blocked_steps}
        if isinstance(action, act_resolver.Tap):
            await device_app.tap(client, serial, action.x, action.y)
            await asyncio.sleep(1.0)  # cho man hinh kip doi truoc khi chup buoc sau
        elif isinstance(action, act_resolver.Wait):
            await asyncio.sleep(action.seconds)
    return {"steps": done, "status": "DONE", "stopped_at": 0,
            "blocked_steps": blocked_steps}
