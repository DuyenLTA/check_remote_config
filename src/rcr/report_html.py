"""Dung trang report tu ket qua chay that. HTML tu chua, khong can server.

Bo cuc BANG TEST CASE (tester chot 2026-09-27) - doc ngang mot hang la du:
    Case | Mo ta + config da dat | Precondition | Step | Expected | Actual | Status

Truoc day moi case la mot dong thu gon, phai bam moi thay Expected/Actual; nguoi
doc report khong biet case fail o buoc nao, tool do duoc gi. Bang nay dat
Expected canh Actual, danh so song song, nen so sanh bang mat.

Header + o dem theo verdict (bam de loc) + o tim + gom nhom theo TINH NANG.
Anh chup tung buoc nam trong o Actual, bam vao mo anh day.
"""

from __future__ import annotations

import html
import time

from . import report_row
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
COLS = ("Case", "Description case", "Preconditions", "Step",
        "Expected Result", "Actual Result", "Status Test")
HOW = [
    "Mỗi case: soi key trong DEX → reset (force-stop / lật cờ onboarding / pm clear) → patch "
    "remote config → mở lại app → verify config còn sống → lái các bước Action → chấm từng dòng.",
    "Cột Expected và cột Actual đánh số song song: dòng thứ i của Actual là kết quả của dòng "
    "thứ i của Expected. Verdict của cả case = dòng xấu nhất.",
    "Ảnh chụp cùng lúc với dump UI nên ảnh và cây node tả cùng một màn hình. Ảnh là bằng chứng "
    "ngữ cảnh (màn nào đang hiện), kết luận lấy từ log và cây node.",
    "Case ads chấm ở tầng request/load, không đòi nhìn thấy ad: inter load nhanh hơn banner nên "
    "nó đè lên trước khi kịp nhìn. Request đúng mà kho quảng cáo không trả ad vẫn tính đạt.",
    "ID quảng cáo trong log bị che còn 3 số cuối → chỉ map được về key remote config khi đuôi "
    "khớp duy nhất. Không map được thì không quy request đó cho vị trí nào.",
    "Quảng cáo che màn hình chỉ chặn bước phải chạm vào màn; bước quan sát và bước chờ vẫn đi tiếp.",
    "Sau mỗi case config trả về nguyên trạng, kèm mốc fetch cũ để app tự lấy lại config thật.",
]


def _order_key(c: dict):
    """Xep theo TINH NANG roi toi so case - dung thu tu tester doc sheet TC.

    Khong xep theo verdict: case cung mot tinh nang nam canh nhau thi moi doi
    chieu duoc "bat key nay thi the nay, tat thi the kia".
    """
    n = c["key"].rsplit("#", 1)[-1]
    return (c.get("group") or "~", int(n) if n.isdigit() else 0, c["key"])


def _tiles(tally: dict) -> str:
    """O dem: chi in verdict THUC SU co trong luot - o so 0 chi lam nhieu mat."""
    return "".join(
        f'<button class="tile {v}" data-f="{v}" aria-pressed="false">'
        f'<span class="num">{tally[v]}</span><span class="lab">{E(VN.get(v, v))}</span></button>'
        for v in tally if tally[v]
    )


def _options(tally: dict) -> str:
    opts = '<option value="ALL">Tất cả trạng thái</option>'
    return opts + "".join(
        f'<option value="{v}">{E(v)} — {E(VN.get(v, v))} ({tally[v]})</option>'
        for v in tally if tally[v]
    )


def _body(cases: list[dict]) -> str:
    """Hang tieu de nhom + cac hang case cua nhom do."""
    out = []
    for name in dict.fromkeys(c.get("group") or "Khác" for c in cases):
        rows = [c for c in cases if (c.get("group") or "Khác") == name]
        out.append(f'<tr class="ghead"><td colspan="{len(COLS)}">{E(name)}'
                   f' · {len(rows)} case</td></tr>')
        out.extend(report_row.build(c) for c in rows)
    return "".join(out)


def build(data: dict) -> str:
    cases = sorted(data["cases"], key=_order_key)
    seen = list(ORDER) + [c["verdict"] for c in cases if c["verdict"] not in ORDER]
    tally = {v: sum(1 for c in cases if c["verdict"] == v) for v in dict.fromkeys(seen)}
    meta = "".join(f"<span>{E(k)} <b>{E(str(v))}</b></span>" for k, v in data["spec"].items())
    # Ghi chu co the la mot cau tho hoac mot khoi HTML dung san. Tu escape cau
    # tho: note cua tc_catalog co the chua `&` hoac `<`, dan thang vao la vo trang.
    note = data.get("warn") or ""
    warn = f'<div class="warn">{note if note.startswith("<") else E(note)}</div>' if note else ""
    head = "".join(f"<th>{E(c)}</th>" for c in COLS)
    how = "".join(f"<li>{E(x)}</li>" for x in HOW)
    return f"""<title>{E(data["title"])}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>{CSS}</style>
<div class="wrap">
  <header>
    <div class="htxt">
      <span class="eyebrow">{E(data["eyebrow"])}</span>
      <h1>{E(data["title"])}</h1>
      <div class="sub">{E(data.get("subtitle", ""))}</div>
      <div class="meta">{meta}</div>
    </div>
    <div class="tally">{_tiles(tally)}</div>
  </header>
  {warn}
  <div class="bar" role="toolbar" aria-label="Lọc case">
    <input id="q" type="search" placeholder="Tìm mã case, tên key, mô tả…" aria-label="Tìm case">
    <select id="st" aria-label="Lọc theo trạng thái">{_options(tally)}</select>
    <span class="count" id="count"></span>
  </div>
  <div class="tablewrap"><table><thead><tr>{head}</tr></thead>
    <tbody>{_body(cases)}</tbody></table></div>
  <details class="find"><summary>Cách chạy &amp; giới hạn của lượt này</summary><ul>{how}</ul></details>
  <p class="foot">Sinh lúc {E(time.strftime("%H:%M %d/%m/%Y"))}</p>
</div>
<script>{JS}</script>
"""
