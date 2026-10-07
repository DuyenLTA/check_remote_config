"""Lai app qua luong First Open toi man can cham.

May trang thai: doc man dang focus -> tim luat khop -> lam MOT buoc -> doc lai.
Nho da lam toi buoc nao cua tung man, nen man can nhieu thao tac (chon ngon ngu
ROI bam xac nhan) tien dan thay vi lap mai buoc dau.

Vi sao nhan man bang TEN ACTIVITY chu khong theo thu tu co dinh: user moi va
user cu di qua nhung man khac nhau; cung mot bo luat chay duoc ca hai, man nao
khong xuat hien thi luat do khong khop lan nao.

Luat de o `data/fo_flow.yaml` - them man moi la sua file, khong sua code.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from . import device_app, fo_steps, ui_dump
from .fo_screens import (  # noqa: F401 - tai xuat cho cho goi cu
    MAN_THEO_MA,
    SCREEN_WORDS,
    THU_TU,
    man_cua_ma,
    man_sau_cung,
    target_for,
    thu_tu,
)
from .adb_parsers import AdbError
from .app_sandbox import guard

log = logging.getLogger(__name__)

DATA = Path(__file__).parent / "data" / "fo_flow.yaml"
# Nhip giua hai lan doc man. 2s -> 1s (do 2026-10-06: moi thao tac lai FO mat
# ~5s, trong do 2s la cho cung; dump UI da ton ~2s nen man kip doi).
POLL_SECONDS = 1.0
# Vong poll lien tiep ma man khong doi va khong con buoc nao de lam -> coi nhu
# ket. Giu NGUONG THOI GIAN ~20s (splash tu load mat ~20s), khong giu so vong:
# nhip ngan lai ma giu 10 vong la bao ket oan luc splash chua xong.
STUCK_POLLS = int(20 / POLL_SECONDS)
DEFAULT_TIMEOUT = 180.0


def rules() -> dict:
    import yaml

    return yaml.safe_load(DATA.read_text(encoding="utf-8")) or {}


def rule_for(activity: str, ruleset: list[dict]) -> dict | None:
    """Luat DAU TIEN co `match` nam trong ten activity."""
    return next((r for r in ruleset if r["match"] in activity), None)


async def _tap(client, serial: str, node) -> None:
    x, y = node.bounds.center
    await device_app.tap(client, serial, x, y)


async def do_step(client, serial: str, step: dict, nodes: list, screen) -> tuple[str, bool]:
    """Lam mot buoc. Tra (nhan viec da lam, co sang buoc ke khong).

    Buoc chon ngon ngu co the moi chi BUNG hang ra chu chua chon duoc gi - luc
    do phai lam lai chinh buoc do o vong sau, khong duoc sang buoc bam xac nhan.

    Buoc tap vao node khong ton tai thi bo qua - man do khong co nut ay, di tiep
    buoc sau con hon dung lai.
    """
    if "wait" in step:
        await asyncio.sleep(step["wait"])
        return f"cho {step['wait']}s", True
    if "swipe" in step:
        direction = step["swipe"] or "left"
        await device_app.swipe(client, serial, direction, screen)
        return f"vuot sang {direction}", True
    if "key" in step:
        await client.shell(serial, "input", "keyevent", step["key"])
        return step["key"], True
    if "language" in step:
        targets = fo_steps.language_targets(nodes, step["language"])
        if not targets:
            return "", True
        await _tap(client, serial, targets[0])
        if len(targets) > 1:      # moi bung hang ra, chua chon duoc
            return f"bung hang {step['language']}", False
        return f"chon {step['language']}", True
    if step.get("tap_continue"):
        node = fo_steps.find_continue(nodes, screen)
        if not node:
            return "", True
        await _tap(client, serial, node)
        return f"nut tiep tuc ({node.label})", True
    if step.get("tap_close"):
        node = fo_steps.find_close(nodes)
        if not node:
            return "", True
        await _tap(client, serial, node)
        return f"dong ({node.label})", True
    target = step.get("tap") or {}
    node = fo_steps.find_node(nodes, target.get("resource_id", ""), target.get("text", ""))
    if not node:
        return "", True
    await _tap(client, serial, node)
    return f"bam {node.label}", True


async def walk_to(client, serial: str, package: str, target: str,
                  timeout: float = DEFAULT_TIMEOUT, log_fn=lambda _m: None,
                  vao_la_tra: bool = False) -> dict:
    """Lai app cho toi khi activity chua `target`. Tra nhat ky duong di.

    Khong raise khi khong toi duoc: tra `reached=False` kem man dang dung va
    cac buoc da lam, de nguoi doc biet ket o dau.

    `vao_la_tra`: case can NHIN THEO THOI GIAN tren trang dich (so dem / nut X
    OB3 song vai giay) -> vuot tu trang lien truoc xong la tra ve NGAY, khong
    dump xac nhan (~2,5s mu dung luc so dem dang chay - do 2026-10-07, khung dau
    tien tre ~7s). Moc vao trang that lay tu log; khong vao duoc thi log khong co
    moc, case khong ra PASS/FAIL va duoc chay lai.
    """
    guard(serial, package)
    data = rules()
    ruleset, screen = data.get("rules") or [], await device_app.screen_size(client, serial)
    target = target or data.get("home_match", "MainActivity")
    trail: list[dict] = []
    progress: dict[str, int] = {}
    idle = 0
    waited = 0.0

    want_activity, _, want_page = target.partition("#")
    page = int(want_page) if want_page.isdigit() else 0
    # (trang vua vuot di, co vuot that) va dump truoc cu vuot - de nhan trang
    # dich khong co cham chi trang (OB3).
    vua_vuot, xml_truoc = (0, False), ""

    while waited < timeout and idle < STUCK_POLLS:
        pkg, activity = await device_app.focus(client, serial)
        if want_activity in activity:
            if not page:
                return {"reached": True, "activity": activity, "trail": trail}
            # Cac trang OB dung chung activity -> vuot cho toi dung trang.
            xml = await ui_dump.dump(client, serial)
            nodes = ui_dump.app_nodes(ui_dump.parse_dump(xml))
            now = fo_steps.onboarding_page(nodes)
            if now == page:
                return {"reached": True, "activity": f"{activity} (trang {now})", "trail": trail}
            if not now and vua_vuot == (page - 1, True) and xml != xml_truoc:
                # OB3 la trang native full man, KHONG co cham chi trang (do tren
                # Pixel 4 + Pixel 7). Vua vuot tu trang lien truoc va man da doi
                # that -> dang o trang dich. Khong nhan thi roi xuong luat lai
                # chung, vuot tiep toi tan Home (do 2026-10-02, ca nhom OB3).
                return {"reached": True, "activity": f"{activity} (trang {page}, suy ra)",
                        "trail": trail}
            vua_vuot = (0, False)
            if now and now < page:
                vua_vuot, xml_truoc = (now, True), xml
                await do_step(client, serial, {"swipe": "left"}, nodes, screen)
                trail.append({"activity": activity.split(".")[-1], "did": f"vuot: trang {now} -> {now + 1}"})
                log_fn(f"      onboarding: vuot sang trang {now + 1}")
                if vao_la_tra and now + 1 == page:
                    return {"reached": True, "activity": f"{activity} (trang {page}, vừa vuốt tới)",
                            "trail": trail}
                await asyncio.sleep(POLL_SECONDS)
                waited += POLL_SECONDS
                continue

        rule = rule_for(activity, ruleset)
        if rule is None:
            # Man la cua app khac ma khong co luat -> app bi day xuong duoi.
            if pkg and pkg != package:
                await device_app.launch(client, serial, package)
                trail.append({"activity": activity, "did": "mo lai app dich"})
            idle += 1
            await asyncio.sleep(POLL_SECONDS)
            waited += POLL_SECONDS
            continue

        steps = rule["steps"]
        index = progress.get(rule["match"], 0)
        if index >= len(steps):
            if "repeat_from" not in rule:
                idle += 1
                await asyncio.sleep(POLL_SECONDS)
                waited += POLL_SECONDS
                continue
            index = rule["repeat_from"]

        try:
            nodes = ui_dump.app_nodes(ui_dump.parse_dump(await ui_dump.dump(client, serial)))
            did, advance = await do_step(client, serial, steps[index], nodes, screen)
        except AdbError as exc:
            # Dump hong (uiautomator thinh thoang tra "null root node") - thu lai
            # chinh buoc do, dung nhay qua.
            did, advance = f"loi: {exc}", False
        progress[rule["match"]] = index + 1 if advance else index
        idle = 0 if did else idle + 1
        if did:
            trail.append({"activity": activity.split(".")[-1], "did": did})
            log_fn(f"      {activity.split('.')[-1]}: {did}")
        await asyncio.sleep(POLL_SECONDS)
        waited += POLL_SECONDS

    _, activity = await device_app.focus(client, serial)
    return {"reached": False, "activity": activity, "trail": trail,
            "reason": f"khong toi duoc {target} sau {waited:g}s, dang dung o {activity}"}
