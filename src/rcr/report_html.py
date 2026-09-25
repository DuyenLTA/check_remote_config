"""Dung trang report tu ket qua chay that. HTML tu chua, khong can server.

Bo cuc de LUOT duoc khi nhieu case (khuon theo report tay cua tester):
    header + meta luot chay   -> chay gi, tren may nao, ban nao
    o dem theo verdict        -> bam vao la loc
    thanh loc + o tim         -> nhieu case thi loc chu khong lan tay
    nhom theo TINH NANG       -> moi case MOT DONG, bung ra moi hien chi tiet
    cach chay & gioi han      -> doc mot lan la biet so lieu tin duoc toi dau

Chi tiet mot case xep canh nhau: Expected <-> tool do duoc gi, Precondition,
config da dat, anh tung buoc, log quang cao.
"""

from __future__ import annotations

import html
import time

from .report_css import CSS
from .report_js import JS
from .verdict_levels import FAIL, NEEDS_HUMAN, NOT_VERIFIABLE, PASS

E = html.escape

ORDER = (FAIL, NEEDS_HUMAN, NOT_VERIFIABLE, PASS)
VN = {
    PASS: "Đúng như Expected",
    FAIL: "Sai so với Expected",
    NEEDS_HUMAN: "Cần người làm tay",
    NOT_VERIFIABLE: "Tool không đo được",
    "CONFIG_OK": "Đặt được config",
    "KEY_NOT_USED": "App không đọc key",
    "BLOCKED": "Config không sống",
}
HOW = [
    "Mỗi case: soi key trong DEX → reset (force-stop / lật cờ onboarding / pm clear) → patch "
    "remote config → mở lại app → verify config còn sống → lái các bước Action → chấm từng dòng.",
    "Ảnh chụp cùng lúc với dump UI nên ảnh và cây node tả cùng một màn hình. Ảnh là bằng chứng "
    "ngữ cảnh (màn nào đang hiện), kết luận lấy từ log và cây node.",
    "Case ads chấm ở tầng request/load, không đòi nhìn thấy ad: inter load nhanh hơn banner nên "
    "nó đè lên trước khi kịp nhìn. Request đúng mà kho quảng cáo không trả ad vẫn tính đạt.",
    "ID quảng cáo trong log bị che còn 3 số cuối → chỉ map được về key remote config khi đuôi "
    "khớp duy nhất. Không map được thì không quy request đó cho vị trí nào.",
    "Quảng cáo che màn hình chỉ chặn bước phải chạm vào màn; bước quan sát và bước chờ vẫn đi tiếp.",
    "Sau mỗi case config trả về nguyên trạng, kèm mốc fetch cũ để app tự lấy lại config thật.",
]


def _pending(c: dict) -> str:
    """Bao nhieu dong chua cham duoc - de khong ai tuong case da cham tron ven."""
    n = c.get("pending") or 0
    return f' · còn {n} dòng cần người' if n else ""


def pill(v: str) -> str:
    return f'<span class="pill {v}">{E(v)}</span>'


def _detail(c: dict) -> str:
    exp = "".join(
        f'<li>{pill(l["v"])}<span>{E(l["e"])}<span class="why">{E(l["r"])}</span></span></li>'
        for l in c.get("lines", [])
    ) or '<li class="why">Case không có dòng Expected nào.</li>'
    cfg = "".join(f"<div>{E(k)} = <code>{E(str(v)[:70])}</code></div>"
                  for k, v in (c.get("overrides") or {}).items())
    shots = "".join(
        f'<figure class="{"blocked" if s.get("blocked") else ""}">'
        f'<img src="{s["shot"]}" alt="bước {s["n"]}" loading="lazy">'
        f'<figcaption><span class="k">{E(s["k"])}</span> {s["n"]}. {E(s["s"])}'
        + (" · màn bị quảng cáo che" if s.get("blocked") else "")
        + (f' · {E(s["shot_warning"])}' if s.get("shot_warning") else "")
        + "</figcaption></figure>"
        for s in c.get("steps", []) if s.get("shot")
    )
    ads = "".join(
        f'<tr><td>{E(a["t"])}</td><td class="mono">{E(a["u"])}</td>'
        f'<td class="num2">{a["req"]}</td><td class="num2">{a["load"]}</td>'
        f'<td class="num2">{a["show"]}</td><td class="mono">{E(", ".join(a["keys"]) or "—")}</td></tr>'
        for a in sorted(c.get("ads", []), key=lambda x: (x["t"], x["u"]))
    )
    blocks = [
        f'<div class="full"><h4>Expected ↔ tool đo được gì</h4><ul class="exp">{exp}</ul></div>',
        f'<div class="box"><h4>Config đã đặt</h4>{cfg or "<span class=why>—</span>"}'
        f'<h4 style="margin-top:10px">Lượt chạy</h4>'
        f'<div class="why">{E(c.get("actual", ""))}</div></div>',
        f'<div class="box"><h4>Precondition</h4>'
        f'<div class="pre">{E(c.get("precondition") or "—")}</div></div>',
    ]
    if shots:
        blocks.append(
            f'<div class="full"><h4>Màn hình từng bước</h4><div class="shots">{shots}</div></div>'
        )
    if ads:
        blocks.append(
            '<div class="full"><h4>Log quảng cáo</h4><table class="ads"><thead><tr><th>Loại</th>'
            "<th>Unit</th><th>Req</th><th>Load</th><th>Show</th><th>Key RC</th></tr></thead>"
            f"<tbody>{ads}</tbody></table></div>"
        )
    return f'<div class="detail">{"".join(blocks)}</div>'


def _row(c: dict) -> str:
    hay = (c["key"] + " " + c.get("label", "") + " " + " ".join(c.get("overrides") or {})).lower()
    return f"""<div class="row" id="c-{E(c["key"])}" data-v="{c["verdict"]}" data-q="{E(hay)}">
  <button class="rowbtn" type="button">
    <span class="n">{E(c["key"])}</span>{pill(c["verdict"])}
    <span class="t"><b>{E(c.get("label", ""))}</b>
      <span>{E(c.get("actual", ""))}{_pending(c)}</span></span>
    <span class="chev">›</span>
  </button>{_detail(c)}</div>"""


def _groups(cases: list[dict]) -> str:
    out = []
    for name in dict.fromkeys(c.get("group") or "Khác" for c in cases):
        rows = [c for c in cases if (c.get("group") or "Khác") == name]
        counts = {v: sum(1 for c in rows if c["verdict"] == v) for v in ORDER}
        chips = "".join(f'{pill(v)}<span class="why">{counts[v]}</span>' for v in ORDER if counts[v])
        out.append(
            f'<section class="group"><div class="ghead"><h2>{E(name)}</h2>'
            f'<div class="gcount">{chips}</div></div>{"".join(_row(c) for c in rows)}</section>'
        )
    return "".join(out)


def build(data: dict) -> str:
    cases = sorted(
        data["cases"],
        key=lambda c: (ORDER.index(c["verdict"]) if c["verdict"] in ORDER else 9, c["key"]),
    )
    tally = {v: sum(1 for c in cases if c["verdict"] == v) for v in ORDER}
    tiles = "".join(
        f'<button class="tile {v}" data-f="{v}" aria-pressed="false">'
        f'<span class="num">{tally[v]}</span><span class="lab">{E(VN[v])}</span></button>'
        for v in ORDER
    )
    chips = '<button class="chip" data-f="ALL" aria-pressed="true">Tất cả</button>' + "".join(
        f'<button class="chip" data-f="{v}" aria-pressed="false">{E(v)}</button>'
        for v in ORDER if tally[v]
    )
    meta = "".join(f"<span>{E(k)} <b>{E(str(v))}</b></span>" for k, v in data["spec"].items())
    warn = f'<div class="warn">{E(data["warn"])}</div>' if data.get("warn") else ""
    how = "".join(f"<li>{E(x)}</li>" for x in HOW)
    return f"""<title>{E(data["title"])}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>{CSS}</style>
<div class="wrap">
  <header style="display:flex;flex-direction:column;gap:8px">
    <span class="eyebrow">{E(data["eyebrow"])}</span>
    <h1>{E(data["title"])}</h1>
    <div class="meta">{meta}</div>{warn}
  </header>
  <div class="tally">{tiles}</div>
  <div class="bar" role="toolbar" aria-label="Lọc case">
    {chips}
    <input class="search" id="q" type="search" placeholder="Tìm case hoặc key (vd 6.4.0#1, banner)" aria-label="Tìm case">
    <button class="linkbtn" id="expandAll" type="button">Mở tất cả</button>
    <span class="count" id="count"></span>
  </div>
  <div id="list" style="display:flex;flex-direction:column;gap:14px">{_groups(cases)}</div>
  <details class="find"><summary>Cách chạy &amp; giới hạn của lượt này</summary><ul>{how}</ul></details>
  <p class="why" style="text-align:center">Sinh lúc {E(time.strftime("%H:%M %d/%m/%Y"))}</p>
</div>
<script>{JS}</script>
"""
