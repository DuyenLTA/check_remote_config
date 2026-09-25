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
from .adb_parsers import AdbError
from .app_sandbox import guard

log = logging.getLogger(__name__)

DATA = Path(__file__).parent / "data" / "fo_flow.yaml"
POLL_SECONDS = 2.0
# Vong poll lien tiep ma man khong doi va khong con buoc nao de lam -> coi nhu
# ket. 10 vong ~20s, doi lai 300s cua mot luot ket cung.
STUCK_POLLS = 10
DEFAULT_TIMEOUT = 180.0


def rules() -> dict:
    import yaml

    return yaml.safe_load(DATA.read_text(encoding="utf-8")) or {}


# Case noi ve man nao -> lai toi activity nao. Doc tu nhan/Precondition cua
# case, vi bo TC khong co cot nao khai man hinh.
# `#N` la trang thu N trong cung mot activity (cac trang OB dung chung activity).
SCREEN_WORDS = (
    ("onb2", "OnboardingActivity#2"), ("onb3", "OnboardingActivity#3"),
    ("onb4", "OnboardingActivity#4"), ("onb1", "OnboardingActivity#1"),
    ("ob1", "OnboardingActivity#1"), ("ob2", "OnboardingActivity#2"),
    ("ob3", "OnboardingActivity#3"), ("ob4", "OnboardingActivity#4"),
    ("onboarding 2", "OnboardingActivity#2"), ("onboarding 3", "OnboardingActivity#3"),
    ("onboarding", "OnboardingActivity"), ("onb", "OnboardingActivity"),
    ("question", "QuestionActivity"), ("language", "LanguageActivity"),
    ("lfo", "LanguageActivity"), ("paywall", "BillingActivity"),
    ("home", "MainActivity"),
)


def target_for(text: str) -> str:
    """Man can lai toi, "" neu case chi noi ve splash (app tu o do sau khi mo)."""
    low = (text or "").casefold()
    if "splash" in low or "spl" in low:
        return ""
    for word, activity in SCREEN_WORDS:
        if word in low:
            return activity
    return ""


def rule_for(activity: str, ruleset: list[dict]) -> dict | None:
    """Luat DAU TIEN co `match` nam trong ten activity."""
    return next((r for r in ruleset if r["match"] in activity), None)


async def _screen(client, serial: str) -> tuple[int, int]:
    out, _, _ = await client.shell(serial, "wm", "size")
    for part in out.split():
        if "x" in part and part.replace("x", "").isdigit():
            w, h = part.split("x")
            return int(w), int(h)
    return 1080, 2400


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
        w, h = screen
        await client.shell(serial, "input", "swipe",
                           str(int(w * 0.8)), str(int(h * 0.5)),
                           str(int(w * 0.2)), str(int(h * 0.5)), "300")
        return "vuot sang trai", True
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
                  timeout: float = DEFAULT_TIMEOUT, log_fn=lambda _m: None) -> dict:
    """Lai app cho toi khi activity chua `target`. Tra nhat ky duong di.

    Khong raise khi khong toi duoc: tra `reached=False` kem man dang dung va
    cac buoc da lam, de nguoi doc biet ket o dau.
    """
    guard(serial, package)
    data = rules()
    ruleset, screen = data.get("rules") or [], await _screen(client, serial)
    target = target or data.get("home_match", "MainActivity")
    trail: list[dict] = []
    progress: dict[str, int] = {}
    idle = 0
    waited = 0.0

    want_activity, _, want_page = target.partition("#")
    page = int(want_page) if want_page.isdigit() else 0

    while waited < timeout and idle < STUCK_POLLS:
        pkg, activity = await device_app.focus(client, serial)
        if want_activity in activity:
            if not page:
                return {"reached": True, "activity": activity, "trail": trail}
            # Cac trang OB dung chung activity -> vuot cho toi dung trang.
            nodes = ui_dump.app_nodes(ui_dump.parse_dump(await ui_dump.dump(client, serial)))
            now = fo_steps.onboarding_page(nodes)
            if now == page:
                return {"reached": True, "activity": f"{activity} (trang {now})", "trail": trail}
            if now and now < page:
                await do_step(client, serial, {"swipe": "left"}, nodes, screen)
                trail.append({"activity": activity.split(".")[-1], "did": f"vuot: trang {now} -> {now + 1}"})
                log_fn(f"      onboarding: vuot sang trang {now + 1}")
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
