"""Dong Expected ve ads co NHIEU vi tri, hoac co ca ve khang dinh lan ve phu dinh.

Vi du that, bo TC 3.6.1 tren AIP936 1.9.0 (02/11/2026):
    "Native 301-onb1-n-native-high hiển thị, không show 202-lfo2-n-native-high."
    "Logcat load tại Splash: 105-spl-n-native-high, 102-spl-n-inter-high, 201-lfo1-n-native-high."
    "Không có loadAd cho bất kỳ unit high1/high2 nào: 102-spl-n-inter-high1, 201-lfo1-n-native-high1/high2."
Truoc day ca dong chi lay MOT vi tri (cai dau tien): ve phu dinh "khong show 202" bi ap
len 301 -> "van co request native cua 301" FAIL oan; dong liet ke "Logcat load ..." khong
co chu show -> "khong neu ro ky vong"; "bat ky ... nao: <danh sach>" tinh moi request la
sai, ke ca unit high cua man -> FAIL oan.

Luat cham, khong gan theo app:
  - ve khang dinh (show / load / reload / preload): moi vi tri liet ke phai co request
    dung unit. Khong fill van dat (user chot 25/09/2026);
  - ve phu dinh co dong tu load/request: vi tri do khong duoc request;
  - ve phu dinh CHI noi "khong show / khong hien thi" ma case KHONG tat vi tri do: request
    (preload o man nha) la dung cho, chi xet unit do co show hay khong;
  - unit dung chung ID cho hai vi tri (AIP936: ...633 = 301_onb1_o_native_high va
    302_onb2_n_native_high) khong quy duoc cho vi tri nao trong cau phu dinh.
"""

from __future__ import annotations

import re

from .ad_positions import _khop_vi_tri, da_biet
from .verdict_levels import FAIL, NEEDS_HUMAN, NOT_VERIFIABLE, PASS, out, worst

# Ma day du, kem duoi viet tat "/high1/high2" hoac "/native" (= unit allprice cua vi tri).
CODE_RE = re.compile(r"\b(\d{3}(?:[-_][a-z0-9]+)+)((?:/[a-z0-9]+)*)", re.I)
TRAN_RE = re.compile(r"(?<![\d.])([1-5]\d{2})(?![\d%]|\.\d)")
LOAD_RE = re.compile(r"\b(?:re|pre)?load(?:ad)?\b", re.I)
SHOW_RE = re.compile(r"hi[ểe]n\s*th[ịi]|\bshow\b|xu[ấa]t\s*hi[ệe]n", re.I)
REQ_RE = re.compile(r"request|g[ọo]i\b", re.I)
# "OB2: native 302-onb2-n-native-high" - man: loai ad + vi tri = ad do hien o man do.
MAN_HIEN_RE = re.compile(r"\b(?:OB\d|LFO\d|splash|question|home)\s*:\s*(?:native|inter|banner)", re.I)
NEG_RE = re.compile(r"\bkh[oô]ng\b|\bko\b|requests?\s*=\s*0", re.I)
# "Logcat preload tuan tu A -> B": dong thu tu, de luat thu tu preload cham.
THU_TU_RE = re.compile(r"→|->|tu[ầa]n\s*t[ựu]|alternate|tr[ưu][ớo]c.{0,40}sau", re.I)
TACH_RE = re.compile(r"[;,()]|\s\+\s")
RESUME_RE = re.compile(r"resume", re.I)
# "(102-spl-n-inter-high da show)": ve dieu kien, khong phai ky vong - bo ra truoc khi cham.
DIEU_KIEN_RE = re.compile(r"(?<!\w)(?:đ|d)[ãa]\s+(?:show|hi[ểe]n|load)", re.I)
RESUME_KEY_RE = re.compile(r"_50\d_")


def ma_vi_tri(text: str) -> list[str]:
    """Moi ma vi tri trong cau, da mo duoi viet tat: `201-lfo1-n-native-high1/high2`
    -> 201_lfo1_n_native_high1, 201_lfo1_n_native_high2."""
    ra = []
    for m in CODE_RE.finditer(text):
        goc = m.group(1).replace("-", "_").lower()
        ra.append(goc)
        dau = goc.rpartition("_")[0]
        for alt in filter(None, m.group(2).lower().split("/")):
            ra.append(dau if dau.endswith("_" + alt) else f"{dau}_{alt}")
    # Ma 3 so dung mot minh ("khong co loadAd 301") - bo so thap phan / phan tram ("100%").
    for so in TRAN_RE.findall(CODE_RE.sub(" ", text)):
        ra.append(so)
    return list(dict.fromkeys(ra))


def tach_ve(text: str) -> list[str]:
    """Cat cau theo dau phay / ngoac; manh khong co dong tu thuoc ve manh truoc no."""
    nhom: list[str] = []
    for p in (x.strip(" .:") for x in TACH_RE.split(text)):
        if not p:
            continue
        if NEG_RE.search(p) or SHOW_RE.search(p) or LOAD_RE.search(p) or not nhom:
            nhom.append(p)
        else:
            nhom[-1] += ", " + p
    return nhom


def _tat(code: str, cfg) -> bool:
    """Case dat show_/enable_ cua vi tri nay = false."""
    return any(str(v).lower() == "false" and k.startswith(("show_", "enable_"))
               and _khop_vi_tri({"rc_keys": [k]}, code) for k, v in (cfg or {}).items())


def _dung_chung(u: dict, code: str) -> list[str]:
    """Key cua unit KHONG thuoc vi tri `code` (ID dung chung voi vi tri khac)."""
    return [k for k in u.get("rc_keys") or () if not _khop_vi_tri({"rc_keys": [k]}, code)]


def _khang_dinh(code: str, units, biet, da_lai: bool) -> dict:
    cua = [u for u in units if _khop_vi_tri(u, code)]
    for muc, ten in (("shown", "đã show"), ("loaded", "load được"), ("requested", "được request")):
        co = [u["unit"] for u in cua if u.get(muc)]
        if co:
            them = "" if muc != "requested" else " nhưng kho không fill — request đúng là đạt"
            return out(PASS, f"`{code}` {ten} ({', '.join(co)}){them}", "")
    if not cua and not da_biet(code, biet):
        return out(NOT_VERIFIABLE, f"không map được unit nào về `{code}` (ID vị trí chưa biết)", "")
    if not da_lai:
        return out(NEEDS_HUMAN, f"`{code}` chưa có request nhưng tool chưa lái tới màn sau", "")
    return out(FAIL, f"không có request nào của `{code}` (ID vị trí này đã biết)", "")


def _phu_dinh(code: str, units, biet, chi_show: bool) -> dict:
    cua = [u for u in units if _khop_vi_tri(u, code)]
    rieng = [u for u in cua if not _dung_chung(u, code)]
    chung = [u for u in cua if _dung_chung(u, code) and u.get("requested")]
    if not cua and not da_biet(code, biet):
        return out(NOT_VERIFIABLE, f"không map được unit nào về `{code}` (ID vị trí chưa biết)", "")
    if chi_show:
        hien = [u["unit"] for u in rieng if u.get("shown")]
        if hien:
            return out(FAIL, f"`{code}` đã show ({', '.join(hien)})", "")
        req = [u["unit"] for u in cua if u.get("requested")]
        return out(PASS, f"`{code}` không show lần nào" + (f" (có request {', '.join(req)} ở màn "
                         "nhà, không fill/không hiện)" if req else ""), "")
    sai = [u["unit"] for u in rieng if u.get("requested")]
    if sai:
        return out(FAIL, f"vẫn có request của `{code}` ({', '.join(sai)})", "")
    if chung:
        khac = sorted({k for u in chung for k in _dung_chung(u, code)})
        return out(PASS, f"không request riêng nào của `{code}`; "
                         f"{', '.join(u['unit'] for u in chung)} dùng chung ID với {', '.join(khac)} "
                         "nên không tính cho vị trí này", "")
    return out(PASS, f"không request nào của `{code}`", "")


def _resume_phu_dinh(units) -> dict:
    hien = [u["unit"] + " " + "/".join(u.get("rc_keys") or ()) for u in units
            if u.get("shown") and any(RESUME_KEY_RE.search(k) for k in u.get("rc_keys") or ())]
    if hien:
        return out(FAIL, f"ad resume đã show ({', '.join(hien)})", "")
    return out(PASS, "không ad resume (50x) nào show", "")


def _ve(text: str, units, biet, cfg, da_lai: bool) -> list[dict]:
    """Cham mot ve -> mot ket qua cho moi vi tri trong ve."""
    codes = ma_vi_tri(text)
    if NEG_RE.search(text):
        if not codes:
            return [_resume_phu_dinh(units)] if RESUME_RE.search(text) else []
        chi_show = bool(SHOW_RE.search(text)) and not (LOAD_RE.search(text) or REQ_RE.search(text))
        return [_phu_dinh(c, units, biet, chi_show and not _tat(c, cfg)) for c in codes]
    return [_khang_dinh(c, units, biet, da_lai) for c in codes]


def cham(text: str, units, biet, cfg, da_lai: bool) -> dict | None:
    """None -> dong khong thuoc loai nay, de luat mot vi tri cham nhu cu."""
    if THU_TU_RE.search(text):
        return None
    text = ", ".join(v for v in tach_ve(text) if not DIEU_KIEN_RE.search(v))
    codes = ma_vi_tri(text)
    phu = bool(NEG_RE.search(text))
    if phu and not any(u.get("requested") for u in units):
        return None                      # log trong: luat cu tra NEEDS_HUMAN
    ves = tach_ve(text)
    tron = phu and any(not NEG_RE.search(v) and ma_vi_tri(v)
                       and (SHOW_RE.search(v) or LOAD_RE.search(v) or MAN_HIEN_RE.search(v)) for v in ves)
    chi_show_mot = (phu and len(codes) == 1 and SHOW_RE.search(text)
                    and not (LOAD_RE.search(text) or REQ_RE.search(text)) and not _tat(codes[0], cfg))
    nhieu = len(codes) >= 2 and (phu or SHOW_RE.search(text) or LOAD_RE.search(text)
                                 or MAN_HIEN_RE.search(text))
    # "preload" mot vi tri: luat thu tu preload / alternate cu cham.
    load_mot = (not phu and len(codes) == 1 and LOAD_RE.search(text) and not SHOW_RE.search(text)
                and "preload" not in text.lower())
    if not (tron or chi_show_mot or nhieu or load_mot):
        return None
    kq = [k for v in (ves if tron else [text]) for k in _ve(v, units, biet, cfg, da_lai)]
    if not kq:
        return None
    return out(worst(k["verdict"] for k in kq), "; ".join(k["reason"] for k in kq), "")
