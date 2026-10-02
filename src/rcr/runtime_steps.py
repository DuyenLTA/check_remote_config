"""Chia buoc Action va dong Expected cua case runtime `a → b → c` theo tung luot.

Quy uoc bo TC 3.5.0: moi mui ten = "Doi <key>, Publish; kill app, chay lai".
Viec doi config + tat app + mo lai la TOOL lam giua hai luot, nen buoc "Doi..."
khong duoc lai nhu mot buoc thuong; ve sau "kill app," (vd "chay lai den OB2")
moi la thao tac cua luot ke.

Expected ghi theo luot: "Lan 2: icon KHONG hien thi". Luot i chi cham dong
"Lan i" cua no + cac dong chung ("Khong crash..."). Cham ca dong "Lan 2" o luot 1
la ra FAIL oan - luot 1 von dang o gia tri cu.
"""

from __future__ import annotations

import re

DOI_RE = re.compile(r"^\s*(?:đổi|doi|change)\b.*\bpublish\b", re.I)
SAU_KILL_RE = re.compile(r"\bkill\s*app\b\s*[,;]?\s*", re.I)
# Ve sau "kill app" chi la "mo lai de fetch RC" -> tool da lam (mo app sau patch).
CHI_FETCH_RE = re.compile(r"^(?:mở\s*lại|mo\s*lai)?\s*(?:để|de)?\s*fetch\b", re.I)
LAN_RE = re.compile(r"^\s*l[ầa]n\s*(\d+)\s*[:.\-–]\s*", re.I)


def chia_buoc(steps, n: int) -> list[tuple[str, ...]]:
    """-> n bo buoc, bo i cho luot i. Luot khong co buoc rieng thi lap bo cua luot 1."""
    doan: list[list[str]] = [[]]
    for step in steps:
        if not DOI_RE.match(step):
            doan[-1].append(step)
            continue
        doan.append([])
        m = SAU_KILL_RE.search(step)
        con = step[m.end():].strip(" .") if m else ""
        if con and not CHI_FETCH_RE.match(con):
            doan[-1].append(con)
    while len(doan) < n:
        doan.append([])
    return [tuple(d or doan[0]) for d in doan[:n]]


def chia_expected(expects, n: int) -> list[tuple[str, ...]]:
    """-> n bo dong Expected. Dong "Lan i: ..." chi vao luot i (bo tien to)."""
    ra: list[list[str]] = [[] for _ in range(n)]
    for line in expects:
        m = LAN_RE.match(line)
        if not m:
            for bo in ra:
                bo.append(line)
            continue
        i = int(m.group(1)) - 1
        if 0 <= i < n:
            ra[i].append(line[m.end():])
    return [tuple(bo) for bo in ra]
