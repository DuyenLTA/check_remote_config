"""Report HTML tu chua cho checklist SDK Next-Gen (khung + style cua skill goc).

Bo cuc theo `sdk-check/WORKFLOW.md`: header -> the loc -> khoi "Can bao dev"
(chi dong Sai) -> danh sach dong gap theo muc -> "Ngoai pham vi / khong ap dung"
-> footer luot chay + trang thai may. Dong con DO_TAY hien rieng "Con do tay" de
nguoi doc thay ngay report chua xong.
"""

from __future__ import annotations

import html
from pathlib import Path

from .report_tab_audit import boc
from .sdk_nextgen_buoc_do_tay import BUOC
from .sdk_nextgen_gop_luot import lech
from .sdk_nextgen_ket import DO_TAY, KHONG_AP_DUNG, KHOP, SAI

TEMPLATE = Path(__file__).resolve().parents[2] / "sdk-check" / "assets" / "report-style-and-filter-script.html"
NHAN = {KHOP: ("pass", "Khớp"), SAI: ("fail", "Sai"), DO_TAY: ("todo", "Đo tay")}
TEN_MUC = {"1.": "Mục 1 · SDK / bản build", "HT": "Mục 2 · Hiển thị", "EV-0": "Mục 3A · Từng event",
           "EV-1": "Mục 3A · Từng event", "EV-2": "Mục 3B · Chuỗi event theo định dạng", "EV-3": "Mục 4 · Next-Gen",
           "KT": "Mục 4 · Next-Gen", "ME": "Mục 4 · Next-Gen", "CM": "Mục 4 · Next-Gen", "HV": "Mục 4 · Next-Gen",
           "RG": "Mục 4 · Next-Gen"}
_e = html.escape


def _nhom(ma: str) -> str:
    return TEN_MUC.get(ma[:4]) or TEN_MUC.get(ma[:2]) or "Khác"


def _ten_luot(thu_muc: str) -> str:
    return Path(thu_muc).name or thu_muc


def _buoc(r: dict) -> str:
    """Buoc da khai khi do tay; dong con DO_TAY thi liet ke buoc phai lam."""
    if r.get("buoc"):
        hang = "".join(f'<li><code>{_e(b["id"])}</code> {_e(b["v"])}{" — " + _e(b["mo_ta"]) if b.get("mo_ta") else ""}</li>'
                       for b in r["buoc"])
        return f'<p class="k">Bước đã làm</p><ul>{hang}</ul>'
    if r["ket"] == DO_TAY and BUOC.get(r["ma"]):
        return '<p class="k">Bước phải làm</p><ul>' + "".join(
            f"<li><code>{_e(i)}</code> {_e(m)}</li>" for i, m in BUOC[r["ma"]]) + "</ul>"
    return ""


def _them(r: dict) -> str:
    """Buoc + nguon (lay tu luot cu / da Sai roi chay lai khong tai hien) duoi moi dong."""
    ra = _buoc(r)
    if r.get("tu_luot"):
        ra += f'<p class="k">Lấy từ lượt {_e(_ten_luot(r["tu_luot"]))} (cùng build)</p>'
    if r.get("khong_tai_hien"):
        k = r["khong_tai_hien"]
        ra += f'<p>Đã Sai ở {_e(_ten_luot(k["sai_o"]))}, chạy lại bước tái hiện: {_e(k["ghi"])}</p>'
    return ra


def _muc_lech(data: dict) -> str:
    ds = lech(data)
    if not ds:
        return ""
    ten = {KHOP: "Khớp", SAI: "Sai", DO_TAY: "Đo tay", KHONG_AP_DUNG: "ngoài phạm vi"}
    hang = "".join(
        f'<li><b>{_e(x["ma"])}</b> {_e(x["ten"])}: lượt này <b>{ten[x["ket"]]}</b>; ' + "; ".join(
            f'{_e(_ten_luot(k["thu_muc"]))} <b>{ten.get(k["ket"], k["ket"])}</b> ({_e(k.get("cham_boi", ""))}): '
            f'{_e(k.get("ly_do", "")[:240])}' for k in x["luot_khac"]) + "</li>" for x in ds)
    return f'<section class="todo"><h2>Lệch giữa các lượt cùng build</h2><ol>{hang}</ol></section>'


def _dong(r: dict) -> str:
    v, nhan = NHAN[r["ket"]]
    bc = "\n".join(r["bang_chung"])
    return (f'<details data-v="{v}"><summary><span class="id">{_e(r["ma"])}</span>'
            f'<span class="pill {"pass" if v == "pass" else "fail"}">{nhan}</span>'
            f'<span class="t">{_e(r["ten"])}<small>{_e(r["ly_do"])}</small></span></summary><div class="body">'
            + (f'<p>{_e(r["ghi_chu"])}</p>' if r.get("ghi_chu") else "")
            + _them(r) + f'<p class="k">Chấm bởi: {_e(r.get("cham_boi", "code"))}</p>'
            + (f"<pre>{_e(bc)}</pre>" if bc else "") + "</div></details>")


def render(data: dict) -> str:
    m, rs = data["meta"], data["ket_qua"]
    tpl = TEMPLATE.read_text("utf-8")
    style, script = tpl.split("<!-- BODY", 1)[0], tpl[tpl.index("<script>"):]
    chinh = [r for r in rs if r["ket"] != KHONG_AP_DUNG]
    n = {k: sum(r["ket"] == k for r in chinh) for k in (KHOP, SAI, DO_TAY)}
    sai = [r for r in chinh if r["ket"] == SAI]
    nhom: dict[str, list] = {}
    for r in chinh:
        nhom.setdefault(_nhom(r["ma"]), []).append(r)
    clicks = m.get("ad_click") or {}
    the = "".join(f'<button class="card {c}" data-f="{f}" aria-pressed="{str(f == "all").lower()}"><span class="n">{x}</span>'
                  f'<span class="l">{l}</span></button>' for f, c, x, l in
                  (("all", "", len(chinh), "Tất cả"), ("pass", "ok", n[KHOP], "Khớp"), ("fail", "bad", n[SAI], "Sai"),
                   ("todo", "bad" if n[DO_TAY] else "", n[DO_TAY], "Còn đo tay")))
    dau = (f'<div class="wrap"><header><h1>SDK Next-Gen · {_e(m.get("app_label") or m["package"])}</h1><div class="meta">'
            f'<span>Package <b>{_e(m["package"])}</b></span><span>SDK FO <b>{_e(m.get("sdk") or "?")}</b></span>'
            f'<span>Máy <b>{_e(m.get("serial") or "?")}</b></span><span>Chấm lúc <b>{_e(m.get("cham_luc", ""))}</b></span>'
            f'<span>Mục <b>{_e(", ".join(m.get("muc") or []))}</b></span></div></header>')
    body = [f'<div class="cards">{the}</div>']
    if sai:
        body.append('<section class="todo"><h2>Cần báo dev</h2><ol>' + "".join(
            f'<li><b>{_e(r["ma"])}</b> {_e(r["ten"])}: {_e(r["ly_do"])}</li>' for r in sai) + "</ol></section>")
    body.append(_muc_lech(data))
    for ten, ds in nhom.items():
        body.append(f'<section class="sec"><h2>{_e(ten)}</h2>' + "".join(map(_dong, ds)) + "</section>")
    ngoai = [r for r in rs if r["ket"] == KHONG_AP_DUNG]
    if ngoai:
        body.append('<section class="sec"><h2>Ngoài phạm vi / không áp dụng</h2><ul>' + "".join(
            f'<li><b>{_e(r["ma"])}</b> {_e(r["ten"])}: {_e(r["ly_do"])}</li>' for r in ngoai) + "</ul></section>")
    truoc = data.get("luot_truoc") or []
    body.append('<footer class="foot">' + (f'<p>Gộp với lượt cũ cùng build: {_e(", ".join(_ten_luot(t["thu_muc"]) for t in truoc))}</p>'
                                         if truoc else "") + '<p>Lượt chạy: '+ _e(", ".join(f"{k} (ad_click {v})" for k, v in clicks.items()))
                + "</p><p>Dòng chấm bởi code cho cùng kết quả khi chấm lại cùng bộ log (rcr-sdk-check --cham-lai).</p></footer>")
    # Tab 1 = checklist (kem khoi tom tat ID ads), tab 2 = trang audit day du -> mot file report.
    thanh = dau + boc("Checklist", "".join(body), m.get("audit")) + "</div>"
    return (f'<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>SDK Next-Gen check</title>{style}</head><body>{thanh}{script}</body></html>")


def ghi(data: dict, path: Path) -> Path:
    Path(path).write_text(render(data), "utf-8")
    return Path(path)
