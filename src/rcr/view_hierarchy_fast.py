"""Doc nhanh cay view cua app bang `dumpsys activity top` (~0,1-0,6s/lan).

`uiautomator dump` mat ~2,5s/lan: nut X / so dem nguoc OB3 song vai giay, nhin
bang uiautomator thi lan dau tien da tre 3-7s, trang tu chuyen truoc khi kip
thay (do 2026-10-07: X hien 5-8,6s ma khung dau tien cua tool o 6,9s, dump xong
thi da sang OB4 -> FAIL oan ca cum).

`dumpsys activity top` in cay view kem:
    <class>{<hash> <co> <co2> l,t-r,b #<hex> <pkg>:id/<ten>}
ky tu dau cua <co> la do hien: V (visible) / I (invisible) / G (gone).
Toa do l,t-r,b TINH THEO VIEW CHA -> cong don theo do thut dong de ra toa do man.

Gioi han (ghi ro de khong ai tin qua muc):
  - KHONG co text / content-desc -> khong doc duoc chu so dem; chi biet node hien.
  - ViewPager cuon bang scrollX khong in ra -> trang dang hien va trang ben canh
    deu "V", toa do x cua trang ben canh lech mot be rong man. Chi dung khi da biet
    app dang o dung trang (moc vao/roi trang lay tu log), con ket luan "man ke
    khong con X" phai dung uiautomator (chi thay trang dang hien).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Sau toa do co the co `#<hex>`, `<pkg>:id/<ten>`, va duoi `aid=<so>` (Android 14+).
_VIEW_RE = re.compile(
    r"^(?P<indent>\s*)(?P<cls>[\w.$]+)\{[0-9a-f]+ (?P<flags>\S+) \S+ "
    r"(?P<l>-?\d+),(?P<t>-?\d+)-(?P<r>-?\d+),(?P<b>-?\d+)"
    r"(?: #[0-9a-f]+)?(?: (?P<rid>[\w.]+:id/[^\s}]+))?[^}]*\}"
)


@dataclass(frozen=True, slots=True)
class FastView:
    """Mot view: id da bo prefix `pkg:id/`, toa do tren man, co hien that khong."""
    rid: str
    cls: str
    left: int
    top: int
    right: int
    bottom: int
    visible: bool       # chinh no VA moi view cha deu V

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


def _activity_blocks(text: str, package: str) -> list[list[str]]:
    """Cac dong `View Hierarchy:` cua nhung ACTIVITY thuoc `package`."""
    blocks, cur, in_pkg, in_tree, tree_indent = [], None, False, False, 0
    for line in text.splitlines():
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if stripped.startswith("ACTIVITY "):
            in_pkg = f" {package}/" in f" {stripped.split(' ', 2)[1]}"
            in_tree = False
            continue
        if in_pkg and stripped.startswith("View Hierarchy:"):
            cur, in_tree, tree_indent = [], True, indent
            blocks.append(cur)
            continue
        if in_tree:
            # Het cay khi gap muc ngang hang "View Hierarchy:" (vd "Looper (main...").
            if stripped and indent <= tree_indent:
                in_tree = False
                continue
            cur.append(line)
    return blocks


def parse(text: str, package: str) -> list[FastView]:
    """Moi view trong cay cua app, toa do da quy ve man hinh."""
    out: list[FastView] = []
    for block in _activity_blocks(text, package):
        # stack: (indent, abs_left, abs_top, visible) cua cac view cha dang mo
        stack: list[tuple[int, int, int, bool]] = []
        for line in block:
            m = _VIEW_RE.match(line)
            if not m:
                continue
            indent = len(m["indent"])
            while stack and stack[-1][0] >= indent:
                stack.pop()
            px, py, pvis = (stack[-1][1], stack[-1][2], stack[-1][3]) if stack else (0, 0, True)
            left, top = px + int(m["l"]), py + int(m["t"])
            right, bottom = px + int(m["r"]), py + int(m["b"])
            vis = pvis and m["flags"][:1] == "V"
            stack.append((indent, left, top, vis))
            rid = m["rid"].split(":id/", 1)[1] if m["rid"] else ""
            out.append(FastView(rid, m["cls"].rsplit(".", 1)[-1], left, top, right, bottom, vis))
    return out


async def read(client, serial: str, package: str) -> list[FastView]:
    out, _, _ = await client.shell(serial, "dumpsys", "activity", "top")
    return parse(out, package)
