"""Bot tu ghi moi luot Check vao out/usage-log-bot.md - bang chung dung that khong phu thuoc nguoi nho ghi."""
from __future__ import annotations

from rcr import usage_log

JOB = {"ma": "AIP872", "ten": "AI Photo Video Maker", "version": "1.9.0 (14)", "package": "com.a.b",
       "ten_may": "ubuntu", "nguoi_duyet_ten": "QA A"}


def _bang(tmp_path) -> list[str]:
    return [d for d in (tmp_path / usage_log.FILE_BOT).read_text(encoding="utf-8").splitlines() if d.startswith("| ")]


def test_tao_bang_va_ghi_noi_tiep_theo_thu_tu(tmp_path):
    assert usage_log.ghi_luot_bot(JOB, {"trang_thai": "XONG", "tom_tat": "51 PASS", "phut": 48.2,
                                        "link": "https://claude.ai/artifact/x", "bugs": []}, tmp_path, "03/11/2026")
    assert usage_log.ghi_luot_bot(JOB, {"trang_thai": "DUNG", "tom_tat": "Build khác plan tuần", "phut": 0.6},
                                  tmp_path, "04/11/2026")
    dong = _bang(tmp_path)
    assert dong[0].startswith("| Ngày |") and len(dong) == 3
    assert "03/11/2026" in dong[1] and "QA A" in dong[1] and "48 phút" in dong[1] and "132 phút" in dong[1]
    assert "04/11/2026" in dong[2] and dong[2].rstrip().endswith("| — |")   # luot dung khong tinh tiet kiem


def test_luot_sub_va_thieu_thong_tin_khong_tinh_tiet_kiem(tmp_path):
    usage_log.ghi_luot_bot({"ma": "X", "loai_job": "sub"}, {"trang_thai": "XONG", "tom_tat": "a | b"},
                           tmp_path, "05/11/2026")
    dong = _bang(tmp_path)[-1]
    assert "| sub |" in dong and "| ? |" in dong and r"a \| b" in dong and dong.rstrip().endswith("| — |")
    assert "file đính kèm Discord" in dong


def test_khong_ghi_duoc_thi_khong_nem_loi(tmp_path):
    chan = tmp_path / "la-file"
    chan.write_text("x", encoding="utf-8")
    assert usage_log.ghi_luot_bot(JOB, {"trang_thai": "XONG"}, chan, "05/11/2026") is False
