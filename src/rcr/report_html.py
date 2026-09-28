"""Dung trang report tu ket qua chay that. HTML tu chua, khong can server.

Bo cuc tester chot 2026-09-28:
    header -> 4 the tong ket (bam de loc) -> khoi "can xu ly" -> thanh loc
    -> danh sach case gap/mo theo nhom -> ghi chu cach chay

Truoc day la mot BANG NGANG 7 cot: doc het mot case phai keo ngang, va 60 case
thi khong con nhin ra toan canh. Danh sach gap cho thay trang thai toan bo
truoc, chi tiet chi mo khi can.

Khoi "can xu ly" o ngay dau: nguoi doc report can biet PHAI LAM GI, khong phai
doc ca 60 case roi tu loc ra.
"""

from __future__ import annotations

import html
import json
import time

from . import report_row
from .report_css import CSS
from .report_js import JS

E = html.escape

FONTS = ("https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600"
         "&family=IBM+Plex+Mono:wght@400;500&display=swap")
CHIPS = (("ALL", "Tất cả"), ("FAIL", "FAIL"), ("BLOCKED", "BLOCKED"),
         ("PASS", "PASS"), ("NA", "N/A"))
HOW = [
    "Mỗi case: soi key trong DEX → reset (force-stop / lật cờ onboarding / pm clear) → patch "
    "remote config → mở lại app → verify config còn sống → lái các bước Action → chấm từng dòng.",
    "Mỗi dòng Expected đi kèm kết quả của chính dòng đó. Verdict của cả case = dòng xấu nhất, "
    "kể cả dòng chưa chấm được — một case PASS nghĩa là mọi dòng đều đã được chấm.",
    "Ảnh chụp cùng lúc với dump UI nên ảnh và cây node tả cùng một màn hình. Ảnh là bằng chứng "
    "ngữ cảnh (màn nào đang hiện), kết luận lấy từ log và cây node.",
    "Case ads chấm ở tầng request/load, không đòi nhìn thấy ad: inter load nhanh hơn banner nên "
    "nó đè lên trước khi kịp nhìn. Request đúng mà kho quảng cáo không trả ad vẫn tính đạt.",
    "ID quảng cáo trong log bị che còn 3 số cuối → chỉ map được về key remote config khi đuôi "
    "khớp duy nhất. Bảng ID từng vị trí lấy từ sheet 'Check thông số KT' của team QA.",
    "N/A = ngoài phạm vi tester: số liệu trên AdMob/Firebase console (việc của PO), hoặc dòng "
    "phải nhìn mắt (đúng design, đúng màu). BLOCKED = chạy lại thì ra kết quả.",
    "Sau mỗi case config trả về nguyên trạng, kèm mốc fetch cũ để app tự lấy lại config thật.",
]


def _thu_tu(d: dict):
    """Xep theo TINH NANG roi toi so case - dung thu tu tester doc sheet TC.

    Khong xep theo trang thai: case cung mot tinh nang nam canh nhau thi moi
    doi chieu duoc "bat key nay thi the nay, tat thi the kia".
    """
    return (d["group"], d["n"], d["key"])


def _chips() -> str:
    return "".join(
        f'<button class="chip" data-f="{v}" aria-pressed="{"true" if v == "ALL" else "false"}">'
        f"{E(ten)}</button>" for v, ten in CHIPS)


def build(data: dict) -> str:
    cases = sorted((report_row.build(c) for c in data["cases"]), key=_thu_tu)
    meta = "".join(f"<span>{E(k)} <b>{E(str(v))}</b></span>" for k, v in data["spec"].items())
    # Ghi chu co the la mot cau tho hoac mot khoi HTML dung san. Tu escape cau
    # tho: note cua tc_catalog co the chua `&` hoac `<`, dan thang vao la vo trang.
    note = data.get("warn") or ""
    warn = f'<div class="warn">{note if note.startswith("<") else E(note)}</div>' if note else ""
    how = "".join(f"<li>{E(x)}</li>" for x in HOW)
    # `</script>` trong du lieu se dong the script som -> vo trang. Chen `\\u003c`
    # thay vi `<`: JSON hop le, va trinh duyet khong con thay the dong.
    payload = json.dumps(cases, ensure_ascii=False).replace("<", "\\u003c")
    return f"""<title>{E(data["title"])}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="{FONTS}">
<style>{CSS}</style>
<div class="wrap">
  <header style="display:flex;flex-direction:column;gap:8px">
    <span class="eyebrow">{E(data["eyebrow"])}</span>
    <h1>{E(data["title"])}</h1>
    <div class="meta">{meta}</div>
  </header>
  {warn}
  <div class="tally" id="tally"></div>

  <section class="card">
    <div class="todo">
      <div><h3>FAIL — cần báo dev</h3><ul id="todoFail"></ul></div>
      <div><h3>BLOCKED — cần chạy lại</h3><ul id="todoBlock"></ul></div>
      <div><h3>Cần PO đối soát console</h3><ul id="todoPo"></ul></div>
    </div>
  </section>

  <div class="bar" role="toolbar" aria-label="Lọc case">
    {_chips()}
    <input class="search" id="q" type="search"
           placeholder="Tìm số case hoặc từ khoá (vd 17, native, mất mạng)" aria-label="Tìm case">
    <button class="linkbtn" id="expandAll">Mở tất cả</button>
    <span class="count" id="count"></span>
  </div>

  <div id="list" style="display:flex;flex-direction:column;gap:14px"></div>

  <details class="find"><summary>Cách chạy &amp; giới hạn của lượt này</summary>
    <ul>{how}</ul></details>
  <p class="foot">Sinh lúc {E(time.strftime("%H:%M %d/%m/%Y"))}</p>
</div>
<script>
const DATA = {payload};
{JS}
</script>
"""
