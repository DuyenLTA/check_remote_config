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
from .verdict_levels import CONFIG_BLOCKED, FAIL, PASS, worst

# BLOCKED: precondition khong tao duoc (case doi may OPPO ma khong co may, can throttle mang...).
# Do thay tren may khac roi chấm PASS la lam gia (user 03/11/2026) - phai ghi BLOCKED kem ly do.
KET_HOP_LE = (PASS, FAIL, "NEEDS_HUMAN", "NOT_VERIFIABLE", CONFIG_BLOCKED)


def doc_anh(text: str) -> list[dict]:
    """"out/manual/A_ob2.png,out/manual/A_ob4.png" -> [{ten, src}] anh da thu nho (JPEG data URI)."""
    from .screencap import to_thumb

    ra = []
    for p in (x.strip() for x in (text or "").split(",")):
        if not p:
            continue
        f = Path(p)
        if not f.is_file():
            raise RcError(f"--anh: không thấy file ảnh {p!r}")
        ra.append({"ten": f.stem, "src": to_thumb(f.read_bytes())})
    return ra


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
         dieu_kien: str = "", anh: list[dict] = ()) -> dict:
    """Tra record moi: cac dong `dong` mang verdict `ket` + ly do, verdict case tinh lai.

    `ket=BLOCKED`: precondition khong tao duoc - ly do vao `precondition_thieu`, case ra BLOCKED.
    `dieu_kien`: cach luot do tay da TAO DUOC precondition ma luot tool khong tao
    duoc (vd chan domain ad bang Private DNS). Co no thi bo `precondition_thieu`
    cua luot tool va ghi cach tao vao `ep_ad_fail`. Khong go `ad_click`: click
    tren unit that thi luot do khong dung duoc, do tay lai cung khong cuu.
    `anh`: [{ten, src (data URI)}] anh chup luot do tay - report hien ngay o case, nguoi doc khong phai tin
    chu (user 29/10/2026: report kho nhin). Trung ten thi giu ban moi.
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
    if ket == CONFIG_BLOCKED:
        record = {**record, "precondition_thieu": [*(record.get("precondition_thieu") or []),
                                                   " ".join(ly_do.split())]}
    for n in dong:
        lines[n - 1].update(v=ket, r=f"{ai} chấm tay: {' '.join(ly_do.split())}")
    ke = [l["v"] for l in lines if l.get("scope") != "po"]
    verdict = worst(ke) if ke else record.get("verdict", "")
    if record.get("precondition_thieu") or record.get("ad_click"):
        verdict = "BLOCKED"  # dieu kien lan chay khong dat thi cham dong nao cung khong cuu duoc case
    cu = record.get("cham_tay")
    cu = cu if isinstance(cu, list) else []  # file luot cu ghi `cham_tay: true`
    cu_anh = {a["ten"]: a for a in record.get("anh_tay") or []}
    cu_anh.update({a["ten"]: a for a in anh if a.get("src")})
    return {**record, "lines": lines, "verdict": verdict, "anh_tay": list(cu_anh.values()),
            "pending": sum(1 for l in lines if l["v"] not in (PASS, FAIL) and l.get("scope") != "po"),
            "cham_tay": cu + [{"dong": n, "v": ket, "ly_do": ly_do.strip(), "ai": ai, "luc": ngay} for n in dong]}


def _chuan(s) -> str:
    return " ".join(str(s or "").split())


def dung_lai(records: list[dict], cu: list[dict]) -> tuple[list[dict], int]:
    """Dong chua PASS/FAIL cua luot moi ma luot cu (CUNG build + config) da cham tren may, cung cau ky vong -> dung
    lai ket qua + anh. Luot 03/11/2026 AIP936: 44 dong phai chep tay bang script. Tra (records moi, so dong)."""
    theo_key = {r.get("key"): r for r in cu}
    ra, dem = [], 0
    for r in records:
        c = theo_key.get(r.get("key"))
        if not c:
            ra.append(r)
            continue
        cl = c.get("lines") or []
        for i, l in enumerate(list(r.get("lines") or [])):
            if l.get("v") in (PASS, FAIL) or i >= len(cl) or _chuan(cl[i].get("e")) != _chuan(l.get("e")):
                continue
            ai, sep, ly = (cl[i].get("r") or "").partition(" chấm tay: ")
            if not sep:
                continue
            r = cham(r, [i + 1], cl[i]["v"], f"lượt trước cùng build + config: {ly}", ai=ai or "Claude")
            dem += 1
        if r is not c and c.get("anh_tay") and r.get("cham_tay"):
            co = {a["ten"] for a in r.get("anh_tay") or []}
            r = {**r, "anh_tay": (r.get("anh_tay") or []) + [a for a in c["anh_tay"] if a["ten"] not in co]}
        ra.append(r)
    return ra, dem


def chay(args, log_fn) -> dict:
    """`--cham-tay FILE --case KEY --dong N --ket PASS --ly-do "..."`: sua file luot, dung lai report.
    `--cham-tay FILE --dung-lai FILE_CU`: dung lai moi dong luot cu da cham tren may (cung build + config)."""
    data = luot_file.doc(args.cham_tay, args.package)
    records = data["records"]
    if getattr(args, "dung_lai", ""):
        if getattr(args, "case", ""):
            raise RcError("--dung-lai áp cho cả lượt, không kèm --case")
        cu = luot_file.doc(args.dung_lai, args.package)["records"]
        records, dem = dung_lai(records, cu)
        log_fn(f"Dùng lại {dem} dòng đã chấm trên máy ở {args.dung_lai}")
        meta = {k: v for k, v in data.items() if k not in ("records", "phien_ban", "xong")}
        report = args.report or data.get("report") or ""
        if report:
            run_batch.ghi_report(luot_file.baseline_tu(data), data.get("tc") or {}, records,
                                 args.app_label or data.get("app_label", ""), report, log_fn)
            meta["report"] = report
        luot_file.ghi(Path(args.cham_tay), meta, records, bool(data.get("xong")))
        return {"package": args.package, "dung_lai": dem, "report": report, "luot": args.cham_tay}
    vi_tri = [i for i, r in enumerate(records) if r.get("key") == args.case]
    if len(vi_tri) != 1:
        co = ", ".join(r.get("key", "?") for r in records[:8])
        raise RcError(f"Không thấy đúng một case {args.case!r} trong {args.cham_tay} (có: {co}…)")
    i = vi_tri[0]
    truoc = records[i].get("verdict")
    records[i] = cham(records[i], so_dong(args.dong), args.ket, args.ly_do,
                      dieu_kien=getattr(args, "dieu_kien_dat", "") or "",
                      anh=doc_anh(getattr(args, "anh", "") or ""))
    log_fn(f"{args.case}: dòng {args.dong} → {args.ket}; verdict case {truoc} → {records[i]['verdict']}")
    meta = {k: v for k, v in data.items() if k not in ("records", "phien_ban", "xong")}
    report = args.report or data.get("report") or ""
    if report:
        run_batch.ghi_report(luot_file.baseline_tu(data), data.get("tc") or {}, records,
                             args.app_label or data.get("app_label", ""), report, log_fn)
        meta["report"] = report
    luot_file.ghi(Path(args.cham_tay), meta, records, bool(data.get("xong")))
    return {"package": args.package, "case": records[i], "report": report, "luot": args.cham_tay}
