"""Mot case -> mot HANG trong bang test case. Tach khoi report_html de moi file
duoi 200 dong va de doi bo cuc mot o khong dung toi phan dung trang.

Cot Expected va cot Actual danh so SONG SONG: dong thu i cua Actual la ket qua
cua dong thu i cua Expected. Cham theo tung dong (Expected von danh so `1. 2. 3.`)
nen ghep nham dong la doc ra ket luan nguoc.
"""

from __future__ import annotations

import html

from .verdict_levels import FAIL

E = html.escape


def pill(v: str) -> str:
    return f'<span class="pill {E(v)}">{E(v)}</span>'


def _case(c: dict) -> str:
    return (f'<td class="c-case"><span class="code">{E(c["key"])}</span>'
            f'<span class="feat">{E(c.get("group") or "—")}</span></td>')


def _desc(c: dict) -> str:
    """Mo ta case + config THAT SU da dat len may.

    Lay tu `overrides` (doc lai tu may), khong lay tu cot Test Data cua sheet:
    sheet ghi y dinh, may ghi su that - hai cai lech nhau la chuyen thuong.
    """
    cfg = "".join(f"<div>{E(k)} = <code>{E(str(v)[:60])}</code></div>"
                  for k, v in (c.get("overrides") or {}).items())
    extra = []
    if c.get("reset") and c["reset"] != "—":
        extra.append("reset: " + c["reset"])
    if c.get("keys_not_used"):
        extra.append("app khong doc key: " + ", ".join(c["keys_not_used"]))
    tail = f'<span class="why">{E(" · ".join(extra))}</span>' if extra else ""
    return (f'<td class="c-desc"><span class="lab">{E(c.get("label", ""))}</span>'
            f'{f"<div class=cfg>{cfg}</div>" if cfg else ""}{tail}</td>')


def _precond(c: dict) -> str:
    return f'<td class="c-pre"><div class="pre">{E(c.get("precondition") or "—")}</div></td>'


def _steps(c: dict) -> str:
    """Cac buoc Action, kem nhan buoc nao tool lai duoc / buoc nao can nguoi."""
    items = []
    for s in c.get("steps", []):
        kind = s.get("k", "")
        mark = f'<span class="k {E(kind)}">{E(kind)}</span>' if kind else ""
        blocked = ('<span class="k blocked">màn bị quảng cáo che</span>'
                   if s.get("blocked") else "")
        cls = ' class="needs_human"' if kind == "needs_human" else ""
        items.append(f"<li{cls}>{E(s.get('s', ''))}{mark}{blocked}</li>")
    if not items:
        return '<td class="c-step"><span class="why">Khong co bước Action nào.</span></td>'
    return f'<td class="c-step"><ol class="steps">{"".join(items)}</ol></td>'


def _expected(c: dict) -> str:
    lines = c.get("lines") or []
    if not lines:
        return '<td class="c-exp"><span class="why">Case không có dòng Expected nào.</span></td>'
    items = "".join(f"<li>{E(l['e'])}</li>" for l in lines)
    return f'<td class="c-exp"><ol class="acts">{items}</ol></td>'


def _ads(c: dict) -> str:
    rows = "".join(
        f'<tr><td>{E(a["t"])}</td><td class="mono">{E(a["u"])}</td>'
        f'<td class="n">{a["req"]}</td><td class="n">{a["load"]}</td><td class="n">{a["show"]}</td></tr>'
        for a in sorted(c.get("ads", []), key=lambda x: (x["t"], x["u"]))
    )
    if not rows:
        return ""
    return ('<table class="ads"><thead><tr><th>Loại</th><th>Unit</th><th>Req</th>'
            f"<th>Load</th><th>Show</th></tr></thead><tbody>{rows}</tbody></table>")


def _shots(c: dict) -> str:
    """Anh tung buoc, bam vao la phong to tai cho (checkbox + CSS).

    KHONG dat data URI vao ca `href` lan `src`: anh nhung base64 chiem gan het
    dung luong trang, viet hai lan la nhan doi file - mot luot 60 case thi
    report cham nguong 16MB cua artifact.

    Man bi quang cao che duoc vien vang ngay tren thumbnail: anh do ta cai
    quang cao chu khong ta app, ket luan tu no la ket luan nham.
    """
    figs = []
    for s in c.get("steps", []):
        if not s.get("shot"):
            continue
        mark = ' class="blocked"' if s.get("blocked") else ""
        cap = f'bước {s["n"]}'
        if s.get("shot_warning"):
            cap += " · " + E(s["shot_warning"])
        figs.append(
            f'<label class="shot" title="bấm để phóng to">'
            f'<input type="checkbox" hidden>'
            f'<img{mark} src="{s["shot"]}" alt="bước {s["n"]}" loading="lazy">'
            f"<span>{cap}</span></label>"
        )
    return f'<div class="shots">{"".join(figs)}</div>' if figs else ""


def _actual(c: dict) -> str:
    """Tool DO duoc gi: tom tat mot dong, roi tung dong Expected mot ket qua."""
    head = f'<div>{E(c.get("actual", "") or "—")}</div>'
    lines = c.get("lines") or []
    body = ""
    if lines:
        items = "".join(
            f'<li>{pill(l["v"])}<span class="why">{E(l["r"] or "—")}</span></li>' for l in lines
        )
        body = f'<ol class="acts" style="margin-top:8px">{items}</ol>'
    bad = [l["r"] for l in lines if l["v"] == FAIL and l.get("r")]
    reason = (f'<div class="reason"><span class="rl">Lý do fail</span>{E(" · ".join(bad))}</div>'
              if bad else "")
    return f'<td class="c-act">{head}{body}{reason}{_ads(c)}{_shots(c)}</td>'


def _status(c: dict) -> str:
    n = c.get("pending") or 0
    note = f'<span class="why">còn {n} dòng cần người</span>' if n else ""
    return f'<td class="c-st">{pill(c["verdict"])}{note}</td>'


def build(c: dict) -> str:
    """-> mot `<tr>`. `data-q` gom moi chu de o tim khong bo sot case."""
    hay = " ".join([
        c["key"], c.get("label", ""), c.get("group", ""), c.get("verdict", ""),
        " ".join(c.get("overrides") or {}), c.get("actual", ""),
    ]).lower()
    cells = (_case(c) + _desc(c) + _precond(c) + _steps(c)
             + _expected(c) + _actual(c) + _status(c))
    # `id` de gui link nhay thang toi mot case: bao bug thi dan link kem so case.
    return (f'<tr class="row {E(c["verdict"])}" id="c-{E(c["key"])}" '
            f'data-v="{E(c["verdict"])}" data-q="{E(hay)}">{cells}</tr>')
