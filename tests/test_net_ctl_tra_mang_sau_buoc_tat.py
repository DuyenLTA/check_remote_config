"""Buoc Action tat mang giua case thi cuoi case phai tra mang."""

from rcr import net_ctl


def test_buoc_tat_mang_giua_case_duoc_nhan_ra():
    buoc = [{"n": 1, "step": "Tắt wifi + 4G.", "net": {"mang": "tat", "thong": False}},
            {"n": 2, "step": "Phát video."}]
    assert net_ctl.buoc_da_tat_mang(buoc)


def test_khong_buoc_nao_tat_mang():
    assert not net_ctl.buoc_da_tat_mang([{"n": 1, "step": "Bấm Lưu"}, {"n": 2, "net": {"mang": "bat"}}])
    assert not net_ctl.buoc_da_tat_mang([])
