"""Loi keo APK tren may bot (o tam het quota) khong duoc bao thanh 'thieu dieu kien testvsl' (Ubuntu 13/11/2026)."""

import os
import tempfile
import time
from pathlib import Path

from rcr import bot_kiem_testvsl, rc_firebase_app


def test_loi_may_bot_khong_nho_sua_condition():
    loi = f"{rc_firebase_app.MAY_BOT} ổ tạm `/tmp` hết chỗ / vượt quota khi kéo APK (Disk quota exceeded)"
    tin = bot_kiem_testvsl.tin_nhac({"ma": "AIP892", "version": "2.2.0 (16)", "nguoi_duyet": 1}, loi, set())
    assert "máy bot" in tin and "condition không cần sửa" in tin and "kéo lên" not in tin


def test_thieu_condition_van_nho_qa():
    tin = bot_kiem_testvsl.tin_nhac({"ma": "AIP892", "version": "2.2.0 (16)"}, "chưa có điều kiện testvsl", {7})
    assert "kéo lên" in tin


def test_don_apk_tam_cu_giu_file_moi():
    tmp = Path(tempfile.gettempdir())
    cu, moi = tmp / "rcr_fb_test_cu.apk", tmp / "rcr_fb_test_moi.apk"
    for f in (cu, moi):
        f.write_bytes(b"x")
    os.utime(cu, (time.time() - 3 * 3600,) * 2)
    rc_firebase_app._don_apk_cu()
    assert not cu.exists() and moi.exists()
    moi.unlink()
