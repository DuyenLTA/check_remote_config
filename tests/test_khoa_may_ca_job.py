"""Khoa may theo CA job: lenh con (env RCR_GIU_MAY) khong tu chan; luot khac thay may ban suot job (16/11/2026)."""

import os

from rcr import bot_hang_doi as h


def test_job_giu_khoa_lenh_con_khong_tu_chan_luot_khac_thay_ban(tmp_path, monkeypatch):
    monkeypatch.delenv(h.ENV_CHA_GIU, raising=False)
    khoa = h.khoa_may(tmp_path, "S1")
    with h.giu_may_ca_job(tmp_path, "S1"):
        assert os.environ[h.ENV_CHA_GIU] == "S1"
        with h.giu_may(khoa):             # lenh con (rcr-check) cung may: khong chan
            pass
        monkeypatch.delenv(h.ENV_CHA_GIU)  # luot khac (khong phai con cua job)
        assert h.may_ban(khoa)
        monkeypatch.setenv(h.ENV_CHA_GIU, "S1")
    monkeypatch.delenv(h.ENV_CHA_GIU, raising=False)
    assert not h.may_ban(khoa)
