"""Chup cay UI cua man hinh dang hien (`uiautomator dump`) va parse ra node.

Parse thuan ham -> test bang fixture XML, khong can may.

Giu `index_in_parent` vi resource-id KHONG UNIQUE: mot hang the co 4 card dung
chung mot resource-id. Khoa doi chieu la (resource_id, index_in_parent).

`bounds` luon la pixel cua may - tap di thang vao toa do nay, khong quy doi dp:
quy doi la them mot cho sai ma khong duoc gi.
"""

from __future__ import annotations

import asyncio
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from .adb_parsers import AdbError
from .app_sandbox import guard

DUMP_PATH = "/data/local/tmp/rcr_uidump.xml"
DUMP_TIMEOUT = 30.0
NULL_ROOT_RETRIES = 3
NULL_ROOT_WAIT = 0.5

_BOUNDS_RE = re.compile(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")

# Node cua he thong, khong phai UI app dang test.
_SYSTEM_PREFIXES = (
    "android:id/",
    "com.android.systemui:id/",
    "com.google.android.apps.nexuslauncher:id/",
    "com.android.launcher",
)
_FRAMEWORK_IDS = frozenset({
    "content", "action_bar_root", "decor_content_parent",
    "navigationBarBackground", "statusBarBackground",
})


@dataclass(frozen=True, slots=True)
class Bounds:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def empty(self) -> bool:
        return self.right <= self.left or self.bottom <= self.top

    @property
    def center(self) -> tuple[int, int]:
        return ((self.left + self.right) // 2, (self.top + self.bottom) // 2)


@dataclass(frozen=True, slots=True)
class DeviceNode:
    node_id: str            # duong dan trong cay, vd "0.1.3" - unique
    resource_id: str        # da bo prefix package
    cls: str
    text: str
    content_desc: str
    bounds: Bounds
    clickable: bool
    enabled: bool
    visible: bool
    package: str
    parent_id: str | None
    index_in_parent: int

    @property
    def label(self) -> str:
        """Ten de nguoi doc nhan ra node tren log."""
        if self.text:
            return f"{self.short_cls}({self.text[:24]!r})"
        if self.content_desc:
            return f"{self.short_cls}[{self.content_desc[:24]}]"
        return self.resource_id or f"{self.short_cls}@{self.node_id}"

    @property
    def short_cls(self) -> str:
        return self.cls.rsplit(".", 1)[-1] if self.cls else ""

    @property
    def tappable(self) -> bool:
        return self.clickable and self.enabled and self.visible


def parse_bounds(raw: str) -> Bounds:
    m = _BOUNDS_RE.fullmatch(raw.strip())
    if not m:
        raise ValueError(f"bounds khong doc duoc: {raw!r}")
    return Bounds(*(int(g) for g in m.groups()))


def strip_package(resource_id: str) -> str:
    return resource_id.rsplit("/", 1)[-1] if "/" in resource_id else resource_id


def is_system_node(node: DeviceNode) -> bool:
    """Node cua Framework/SystemUI/Launcher - khong phai UI app."""
    if node.resource_id in _FRAMEWORK_IDS:
        return True
    return any(node.package.startswith(p.split(":", 1)[0]) for p in _SYSTEM_PREFIXES)


def parse_dump(xml_text: str) -> list[DeviceNode]:
    """XML -> danh sach node theo thu tu duyet truoc."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise AdbError(f"Dump UI khong phai XML hop le: {exc}") from exc
    nodes: list[DeviceNode] = []

    def walk(element, parent_id: str | None, path: str) -> None:
        for index, child in enumerate(c for c in element if c.tag == "node"):
            node_id = f"{path}.{index}" if path else str(index)
            nodes.append(_build(child, parent_id, node_id, index))
            walk(child, node_id, node_id)

    walk(root, None, "")
    return nodes


def _build(element, parent_id: str | None, node_id: str, index: int) -> DeviceNode:
    attr = element.attrib
    try:
        bounds = parse_bounds(attr.get("bounds", ""))
    except ValueError:
        # Giu node lai de index khong lech, nhung danh dau khong nhin thay duoc.
        bounds = Bounds(0, 0, 0, 0)
    full_id = attr.get("resource-id", "").strip()
    return DeviceNode(
        node_id=node_id,
        resource_id=strip_package(full_id),
        cls=attr.get("class", ""),
        text=(attr.get("text") or "").strip(),
        content_desc=(attr.get("content-desc") or "").strip(),
        bounds=bounds,
        clickable=attr.get("clickable") == "true",
        enabled=attr.get("enabled", "true") != "false",
        visible=attr.get("visible-to-user", "true") != "false" and not bounds.empty,
        package=attr.get("package", ""),
        parent_id=parent_id,
        index_in_parent=index,
    )


def app_nodes(nodes: list[DeviceNode], package: str = "") -> list[DeviceNode]:
    """Bo node he thong (status bar, nav bar, launcher)."""
    out = [n for n in nodes if not is_system_node(n)]
    return [n for n in out if n.package == package] if package else out


async def _dump_tat_animator(client, serial: str) -> str:
    """Dump voi `animator_duration_scale` = 0 (animation dung ngay) roi luon tra gia tri cu. Tra stdout+stderr."""
    cu, _e, _ = await client.shell(serial, "settings", "get", "global", "animator_duration_scale")
    cu = (cu or "").strip()
    await client.shell(serial, "settings", "put", "global", "animator_duration_scale", "0")
    try:
        await asyncio.sleep(0.5)
        out, err, _ = await client.shell(serial, "uiautomator", "dump", DUMP_PATH, timeout=DUMP_TIMEOUT)
        return f"{out} {err}"
    finally:
        if cu and cu != "null":
            await client.shell(serial, "settings", "put", "global", "animator_duration_scale", cu)
        else:
            await client.shell(serial, "settings", "delete", "global", "animator_duration_scale")


async def dump(client, serial: str, _da_dong_anr: bool = False) -> str:
    """Chup man hinh dang hien. Tra nguyen van XML.
    Hop thoai ANR cua launcher / systemui dang che man -> bam Wait roi dump lai (xem anr_he_thong)."""
    guard(serial)
    for lan in range(NULL_ROOT_RETRIES + 1):
        out, err, _ = await client.shell(serial, "uiautomator", "dump", DUMP_PATH, timeout=DUMP_TIMEOUT)
        joined = f"{out} {err}"
        # "null root node": dump roi dung luc doi cua so (splash -> AdActivity),
        # chua co cua so active. Thu lai sau mot nhip thay vi lam chet ca case
        # (do 24/10/2026, Piclux 2.4.0: 14/22 case BLOCKED vi loi nay).
        if "null root node" not in joined or lan == NULL_ROOT_RETRIES:
            break
        if lan == 0:
            # May tat man / bi khoa giua luot cung bao "null root node" -> bat man + mo khoa roi dump lai.
            from . import mo_khoa_may
            await mo_khoa_may.mo_khoa(client, serial)
        await asyncio.sleep(NULL_ROOT_WAIT)
    if "could not get idle state" in joined:
        # Man co animation lap vo han (Compose: thanh keo so sanh o Result BeautyGenie 2.2.0, Pixel 4 16/11/2026) ->
        # uiautomator khong bao gio thay UI dung yen. Tat animator tam thoi cho mot lan dump roi tra gia tri cu.
        joined = await _dump_tat_animator(client, serial)
    if "ERROR" in joined.upper() or "Exception" in joined:
        raise AdbError(f"uiautomator dump that bai: {joined.strip()}")
    xml, err, _ = await client.shell(serial, "cat", DUMP_PATH, timeout=DUMP_TIMEOUT)
    await client.shell(serial, "rm", "-f", DUMP_PATH)
    if "<hierarchy" not in xml:
        raise AdbError(f"Khong doc duoc dump UI: {(err or xml).strip()[:200]}")
    if not _da_dong_anr:
        from . import anr_he_thong
        if await anr_he_thong.dong_neu_he_thong(client, serial, xml):
            await asyncio.sleep(1.0)
            return await dump(client, serial, _da_dong_anr=True)
    return xml
