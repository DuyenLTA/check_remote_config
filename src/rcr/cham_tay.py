"""Ghi ket qua cham tay (Claude/tester do tren may) vao file luot, khong can may.

Truoc day muon ha mot PASS gia hay ghi dong da do tay thi phai sua tay JSON roi
`--gop` (24/10/2026, Piclux REG-002/SPLA-003): de go sai key, va report khong
ghi lai ai cham, cham bang gi. Lenh nay ghi tung dong kem ly do, giu dau vet
`cham_tay`, tinh lai verdict cua case theo cung luat (dong xau nhat, tru dong PO).
"""

from __future__ import annotations

import time
from pathlib import Path

from . import luot_file, run_batch
from .models import RcError
from .verdict_levels import FAIL, PASS, worst

KET_HOP_LE = (PASS, FAIL, "NEEDS_HUMAN", "NOT_VERIFIABLE")


def so_dong(text: str) -> list[int]:
    """"1,3" -> [1, 3]. So dong dem tu 1, theo thu tu dong tren report."""
    try:
        ra = [int(x) for x in (text or "").split(",") if x.strip()]
    except ValueError as exc:
        raise RcError(f"--dong phải là số dòng, vd 1 hoặc 1,3 (nhận được {text!r})") from exc
    if not ra or min(ra) < 1:
        raise RcError("--dong phải là số dòng đếm từ 1, vd 1 hoặc 1,3")
    return ra


def cham(record: dict, dong: list[int], ket: str, ly_do: str, ai: str = "Claude",
         dieu_kien: str = "") -> dict:
    """Tra record moi: cac dong `dong` mang verdict `ket` + ly do, verdict case tinh lai.

    `dieu_kien`: cach luot do tay da TAO DUOC precondition ma luot tool khong tao
    duoc (vd chan domain ad bang Private DNS). Co no thi bo `precondition_thieu`
    cua luot tool va ghi cach tao vao `ep_ad_fail`. Khong go `ad_click`: click
    tren unit that thi luot do khong dung duoc, do tay lai cung khong cuu.
    """
    if dieu_kien.strip():
        record = {**record, "precondition_thieu": [],
                  "ep_ad_fail": f"{ai} tạo điều kiện ở lượt đo tay: {' '.join(dieu_kien.split())}"}
    if ket not in KET_HOP_LE:
        raise RcError(f"--ket phải là một trong {', '.join(KET_HOP_LE)}")
    if not (ly_do or "").strip():
        raise RcError("--ly-do bắt buộc: ghi số đo / cách đo để người đọc report kiểm lại được")
    lines = [dict(l) for l in record.get("lines") or []]
    thua = [n for n in dong if n > len(lines)]
    if thua:
        raise RcError(f"Case {record.get('key')} chỉ có {len(lines)} dòng Expected, không có dòng "
                      + ", ".join(map(str, thua)))
    ngay = time.strftime("%d/%m/%Y %H:%M")
    for n in dong:
        lines[n - 1].update(v=ket, r=f"{ai} chấm tay: {' '.join(ly_do.split())}")
    ke = [l["v"] for l in lines if l.get("scope") != "po"]
    verdict = worst(ke) if ke else record.get("verdict", "")
    if record.get("precondition_thieu") or record.get("ad_click"):
        verdict = "BLOCKED"  # dieu kien lan chay khong dat thi cham dong nao cung khong cuu duoc case
    cu = record.get("cham_tay")
    cu = cu if isinstance(cu, list) else []  # file luot cu ghi `cham_tay: true`
    return {**record, "lines": lines, "verdict": verdict,
            "pending": sum(1 for l in lines if l["v"] not in (PASS, FAIL) and l.get("scope") != "po"),
            "cham_tay": cu + [{"dong": n, "v": ket, "ly_do": ly_do.strip(), "ai": ai, "luc": ngay} for n in dong]}


def chay(args, log_fn) -> dict:
    """`--cham-tay FILE --case KEY --dong N --ket PASS --ly-do "..."`: sua file luot, dung lai report."""
    data = luot_file.doc(args.cham_tay, args.package)
    records = data["records"]
    vi_tri = [i for i, r in enumerate(records) if r.get("key") == args.case]
    if len(vi_tri) != 1:
        co = ", ".join(r.get("key", "?") for r in records[:8])
        raise RcError(f"Không thấy đúng một case {args.case!r} trong {args.cham_tay} (có: {co}…)")
    i = vi_tri[0]
    truoc = records[i].get("verdict")
    records[i] = cham(records[i], so_dong(args.dong), args.ket, args.ly_do,
                      dieu_kien=getattr(args, "dieu_kien_dat", "") or "")
    log_fn(f"{args.case}: dòng {args.dong} → {args.ket}; verdict case {truoc} → {records[i]['verdict']}")
    meta = {k: v for k, v in data.items() if k not in ("records", "phien_ban", "xong")}
    report = args.report or data.get("report") or ""
    if report:
        run_batch.ghi_report(luot_file.baseline_tu(data), data.get("tc") or {}, records,
                             args.app_label or data.get("app_label", ""), report, log_fn)
        meta["report"] = report
    luot_file.ghi(Path(args.cham_tay), meta, records, bool(data.get("xong")))
    return {"package": args.package, "case": records[i], "report": report, "luot": args.cham_tay}
