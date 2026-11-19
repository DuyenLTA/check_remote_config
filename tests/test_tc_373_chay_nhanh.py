"""Tab TC SDK 3.7.3 viet lai (case doc lap): case thieu build BLOCKED ngay, cau 'O LFO1 30 giay' lai roi dung,
buoc Action khong dich duoc thi khong chay lai lan 2."""

from __future__ import annotations

from rcr import act_cau_fo, act_resolver, chay_lai, precond_build
from rcr.act_types import GoTo, NeedsHuman


def test_can_build_dev_thi_blocked_tru_khi_da_co_build():
    pre = "1. Cần build Dev: chặn request của chuỗi inter splash, kho vẫn tải."
    ra = precond_build.thieu_build(pre)
    assert len(ra) == 1 and ra[0].startswith("Cần build Dev") and "--co-build-dev" in ra[0]
    assert precond_build.thieu_build(pre, co_build_dev=True) == []


def test_build_debug_cung_chan():
    assert precond_build.thieu_build("1. Cần build debug (fetch interval = 0): bản release ...")


def test_mang_cham_hoac_build_dev():
    pre = "1. Cần mạng chậm hoặc build Dev để ad của ID high về sau 30 giây."
    assert precond_build.thieu_build(pre)                      # chua co gi -> chan
    assert precond_build.thieu_build(pre, co_build_dev=True) == []   # da co build Dev -> chay


def test_can_nguoi_chi_key_khong_phai_build_van_chan():
    pre = "1. Cần PO/Dev chỉ key bật chế độ 'một bộ ad ID cho mọi user' ..."
    assert precond_build.thieu_build(pre, co_build_dev=True)
    assert precond_build.thieu_build("1. Dev kiểm bằng code hoặc log (khó dựng khi test thường).", True)


def test_precondition_thuong_khong_chan():
    for pre in ("", "1. ID high của chuỗi có fill (unit thật đang có ad).",
                "1. Kho của <ID splash_inter_high_n_id> có ad lúc dựng màn Question.",
                "1. Config đã đồng bộ ở lần mở có mạng (bước tạo old user)."):
        assert precond_build.thieu_build(pre) == []


def test_o_man_n_giay_lai_toi_roi_cho():
    a = act_resolver.resolve("Ở LFO1 30 giây.", [])
    assert isinstance(a, GoTo) and a.target == "Language" and a.cho == 30
    a = act_resolver.resolve("Ở Question 35 giây.", [])
    assert isinstance(a, GoTo) and a.target == "QuestionActivity" and a.cho == 35
    a = act_resolver.resolve("Ở LFO1 2 phút.", [])
    assert isinstance(a, GoTo) and a.cho == 120


def test_toi_man_thi_dung():
    a = act_resolver.resolve("Tới LFO1 thì dừng.", [])
    assert isinstance(a, GoTo) and a.target == "Language" and not a.cho


def test_o_man_ve_sau_la_viec_khac_khong_nhan():
    assert act_cau_fo._o_man_roi_dung("Ở LFO1 chọn ngôn ngữ, bấm Next.") is None
    assert isinstance(act_resolver.resolve("Ở LFO1 chọn ngôn ngữ, bấm Next.", []), NeedsHuman)


def test_cho_qua_lau_thi_bao_nguoi():
    assert isinstance(act_resolver.resolve("Ở Question 65 phút.", []), NeedsHuman)


def _kq(reason: str) -> dict:
    return {"verdict": "NEEDS_HUMAN",
            "runs": [{"verdict": "CONFIG_OK",
                      "drive": {"steps": [{"action": {"kind": "needs_human", "reason": reason}}]},
                      "assert": {"lines": [{"n": 1, "verdict": "NEEDS_HUMAN", "reason": "chưa lái tới"}]}}]}


def test_buoc_khong_dich_duoc_thi_khong_chay_lai():
    ly_do = chay_lai.ly_do_khong_chay_lai(_kq("không dịch được bước: 'Bấm nút 5 lần liên tiếp'"), None)
    assert "không dịch được" in ly_do


def test_needs_human_vi_ly_do_khac_van_chay_lai_lan_dau():
    assert chay_lai.ly_do_khong_chay_lai(_kq("không thấy ô lựa chọn nào"), None) == ""
