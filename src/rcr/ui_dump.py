"""Chup cay UI cua man hinh dang hien (`uiautomator dump`) va parse ra node.

Parse thuan ham -> test bang fixture XML, khong can may.

Giu `index_in_parent` vi resource-id KHONG UNIQUE: mot hang the co 4 card dung
chung mot resource-id. Khoa doi chieu la (resource_id, index_in_parent).

`bounds` luon la pixel cua may - tap di thang vao toa do nay, khong quy doi dp:
quy doi la them mot cho sai ma khong duoc gi.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from .adb_parsers import AdbError
from .app_sandbox import guard

DUMP_PATH = "/data/local/tmp/rcr_uidump.xml"
DUMP_TIMEOUT = 30.0

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


async def dump(client, serial: str) -> str:
    """Chup man hinh dang hien. Tra nguyen van XML."""
    guard(serial)
    out, err, _ = await client.shell(serial, "uiautomator", "dump", DUMP_PATH, timeout=DUMP_TIMEOUT)
    joined = f"{out} {err}"
    if "ERROR" in joined.upper() or "Exception" in joined:
        raise AdbError(f"uiautomator dump that bai: {joined.strip()}")
    xml, err, _ = await client.shell(serial, "cat", DUMP_PATH, timeout=DUMP_TIMEOUT)
    await client.shell(serial, "rm", "-f", DUMP_PATH)
    if "<hierarchy" not in xml:
        raise AdbError(f"Khong doc duoc dump UI: {(err or xml).strip()[:200]}")
    return xml
