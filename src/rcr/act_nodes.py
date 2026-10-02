"""Tim node tren man hinh de tap. Tach khoi `act_resolver` de file duoi 200 dong.

NGUYEN TAC giu nguyen: chi tap khi khop DUY NHAT mot node. Khong thay, hoac
thay nhieu hon mot, deu tra NeedsHuman - tap sai cho la bam quang cao that.
"""

from __future__ import annotations

from .act_types import Action, NeedsHuman, Tap
from .ui_dump import DeviceNode


def tap_by_text(wanted: str, nodes: list[DeviceNode], matched: str) -> Action:
    """Tim node theo text/content-desc. Phai DUY NHAT moi tap."""
    hits = find(wanted, nodes)
    if not hits:
        return NeedsHuman(f"không thấy phần tử nào khớp {wanted!r} trên màn hình")
    if len(hits) > 1:
        names = ", ".join(n.label for n in hits[:4])
        return NeedsHuman(
            f"{len(hits)} node cung khop {wanted!r} ({names}) - khong doan node nao la dung"
        )
    node = hits[0]
    x, y = node.bounds.center
    return Tap(node.label, x, y, matched)


def find(wanted: str, nodes: list[DeviceNode]) -> list[DeviceNode]:
    """Node khop text/content-desc. Uu tien khop DUNG HAN truoc khi khop mot phan.

    Chi xet node bam duoc: chu tren man hinh thuong nam o TextView khong
    clickable, con cai bam duoc la cha no - tap vao chu van trung vao cha.
    """
    want = wanted.casefold()
    pool = [n for n in nodes if n.visible and not n.bounds.empty]
    exact = [n for n in pool if want in (n.text.casefold(), n.content_desc.casefold())]
    if exact:
        return _outermost(exact)
    partial = [
        n for n in pool
        if want in n.text.casefold() or want in n.content_desc.casefold()
    ]
    return _outermost(partial)


def _outermost(hits: list[DeviceNode]) -> list[DeviceNode]:
    """Bo node nam TRONG node khac cung khop - cung mot chu, dung dem 2 lan."""
    ids = {n.node_id for n in hits}
    return [n for n in hits if not _has_ancestor(n, ids)]


def _has_ancestor(node: DeviceNode, ids: set[str]) -> bool:
    parent = node.parent_id
    while parent:
        if parent in ids:
            return True
        parent = parent.rsplit(".", 1)[0] if "." in parent else None
    return False
