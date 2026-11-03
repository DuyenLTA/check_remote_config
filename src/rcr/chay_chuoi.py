"""Che do chay chuoi (`rcr-check --chuoi`): case "Tiep noi <case truoc>" chay tiep tren app dang mo.

Moi case thuong tu dat config -> pm clear -> mo app -> qua splash + inter splash -> lai toi man (~55s truoc khi
toi buoc dau tien, do 03/11/2026). Case "Tiep noi" cung config voi case vua chay thi bo het phan do: app con
mo, config con giu (`giu`), lai tiep tu man dang dung.

An toan ket qua (khong de PASS/FAIL gia vi log dung chung mot lan mo app):
- moi dong cham HAI lan: log RIENG case (tu moc bat dau case) va log DON tu splash cua chuoi (case_run);
- case chi duoc nhan ket qua chuoi khi PASS tron ven ca hai (hoac chi con dong suy tu cau chu, xem `nhan_duoc`);
  con lai (FAIL, lai khong toi man, ad_click...) thi run_batch chay RIENG case do theo cach thuong - ket luan
  FAIL luon tu lan chay rieng.
"""

from __future__ import annotations

from . import chay_lai, fo_ngon_ngu


def moc_chuoi(key: str, runs: list[dict], giu: bool) -> dict:
    """Trang thai de case sau xet noi tiep: case vua chay xong, config nao, con giu config tren may khong."""
    return {"key": key, "runs": [dict(r) for r in runs], "giu": giu}


def ly_do_khong_noi(truoc: dict | None, chosen: dict, runs: list[dict], ep) -> str:
    """'' neu case nay chay noi tiep duoc tren app cua case `truoc`; khong thi ly do (ghi log)."""
    if not truoc:
        return "chưa có case trước trong chuỗi"
    m = fo_ngon_ngu.TIEP_NOI_RE.search(chosen.get("precondition") or "")
    if not m:
        return "precondition không ghi 'Tiếp nối'"
    if not truoc["key"].endswith(m.group(1)):
        return f"tiếp nối {m.group(1)}, case vừa chạy là {truoc['key'].split('#')[-1]}"
    if ep:
        return "case ép ad fail (đổi ID / chặn DNS) phải chạy riêng"
    if chosen.get("runtime") or len(runs) != 1:
        return "case nhiều lượt config"
    if [dict(r) for r in runs] != truoc["runs"]:
        return "config khác case trước"
    if not truoc["giu"]:
        return "case trước không giữ config / chạy hỏng"
    return ""


def nhan_duoc(result: dict) -> bool:
    """Nhan ket qua chay chuoi khi:
    - PASS tron ven (ca log rieng lan log don), hoac
    - log rieng va log don ra CUNG mot ket qua chua cham duoc, khong dong nao FAIL, va: tool dung o buoc no khong
      lam duoc, hoac moi dong con mo deu suy tu cau chu (phai nhin mat / khong neu ky vong) - chay rieng lai cung
      ra y het (do 03/11/2026 RG01-06: chay
      rieng them 63s ra dung NOT_VERIFIABLE do), Claude do tay cac dong nay o buoc 5b.
    FAIL va moi truong hop khac -> chay rieng (ket luan FAIL luon tu lan chay rieng)."""
    if result.get("ad_click") or result.get("precondition_thieu"):
        return False
    v = result.get("verdict")
    if v == "PASS" and not result.get("chuoi_khong_chac"):
        return True
    if v not in ("NEEDS_HUMAN", "NOT_VERIFIABLE") or result.get("chuoi_don") != v:
        return False
    if any(l.get("verdict") == "FAIL" for l in chay_lai._dong(result)):
        return False
    # Tool dung o mot buoc no khong lam duoc ("Chon ngon ngu." -> needs_human): chay rieng cung dung dung buoc do
    # (03/11/2026 RG01-02/03: chay rieng them ~65s ra y het NEEDS_HUMAN). Dong do Claude do tay o buoc 5b.
    if any(((r.get("drive") or {}).get("status") == "NEEDS_HUMAN") for r in result.get("runs") or []):
        return True
    return chay_lai.ly_do_khong_chay_lai(result, None).endswith("(phải nhìn mắt / không nêu kỳ vọng)")
