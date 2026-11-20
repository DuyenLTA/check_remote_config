"""Dong logcat ghi luc dong ho may chay truoc (OPPO f3466cdb 19/11/2026) phai bi bo khi doc."""

import time

from rcr import log_tuong_lai


def _now() -> float:
    return time.mktime((2026, 11, 19, 17, 40, 0, 0, 0, -1))


def test_bo_dong_epoch_tuong_lai():
    now = _now()
    text = (
        f"{now - 5:.3f}  7764  7764 I FA-SVC: Logging event: name=ad_show\n"
        f"{now + 2 * 86400:.3f} 11032  6325 V FA-SVC: Logging event: name=ad_show (app khac)\n"
        "--------- beginning of main"
    )
    ra = log_tuong_lai.loc(text, now)
    assert "app khac" not in ra
    assert "7764" in ra and "beginning of main" in ra


def test_bo_dong_threadtime_tuong_lai():
    now = _now()
    text = (
        "11-21 16:03:57.114 27983 28107 I AdInitializer: Config variant dev: true\n"
        "11-19 17:39:58.000  7764  7764 I AdSdk   : Config variant dev: false\n"
    )
    ra = log_tuong_lai.loc(text, now)
    assert "dev: true" not in ra
    assert "dev: false" in ra


def test_log_thang_12_doc_vao_thang_1_khong_bi_bo():
    now = time.mktime((2027, 1, 1, 0, 0, 30, 0, 0, -1))
    text = "12-31 23:59:50.000  100  100 I X: cuoi nam\n"
    assert "cuoi nam" in log_tuong_lai.loc(text, now)


def test_chi_loc_lenh_doc_log():
    assert log_tuong_lai.la_lenh_doc_log(("-s", "x", "shell", "logcat", "-d", "-v", "epoch"))
    assert log_tuong_lai.la_lenh_doc_log(("-s", "x", "logcat", "-d"))
    assert not log_tuong_lai.la_lenh_doc_log(("-s", "x", "shell", "logcat", "-c"))
    assert not log_tuong_lai.la_lenh_doc_log(("-s", "x", "shell", "dumpsys", "window"))
