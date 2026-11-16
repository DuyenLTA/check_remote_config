"""Cong thuc dung chung giua cac app cung khuon (template) - rating_gen.yaml, checkin_cong_thuc.yaml.

File YAML co them muc `khuon: {<ten>: {nhan_dien: <regex chu chi co o Home cua khuon>, ...cong thuc...}}`.
App co muc rieng theo package -> dung muc rieng (muc rieng co `khuon: <ten>` thi lay khuon do roi de phan rieng len).
App CHUA khai -> khuon dau tien co `nhan_dien` khop chu tren man dang hien (Home): app moi cung khuon chay luon,
khong phai do lai tung app (user chot 16/11/2026: tinh nang da dong goi thi doc cong thuc dung chung cho nhanh).
App lech chu thi them chu cua app vao regex khuon (A|B), dung tach muc rieng.
"""

from __future__ import annotations

import re


def chon(data: dict, package: str, nodes=None) -> tuple[str, dict | None]:
    """(nguon, cong thuc): "rieng" / "khuôn <ten>" / ("", None) khi chua co gi khop."""
    khuon = data.get("khuon") or {}
    muc = data.get(package)
    if isinstance(muc, dict):
        if not muc.get("khuon"):
            return "rieng", muc
        k = khuon.get(muc["khuon"])
        if k:
            return f"khuôn {muc['khuon']}", {**k, **{a: b for a, b in muc.items() if a != "khuon"}}
    for ten, k in khuon.items():
        mau = k.get("nhan_dien")
        if mau and nodes and any(re.search(mau, s or "", re.I) for n in nodes for s in (n.text, n.content_desc)):
            return f"khuôn {ten}", k
    return "", None
