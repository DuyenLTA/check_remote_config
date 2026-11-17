"""Firebase CLI het han thi bot khong nhan job (dem 16/11/2026: 7 case BLOCKED vi CLI het han giua luot)."""

import subprocess

from rcr import firebase_dang_nhap as f


def test_con_han_theo_projects_list_va_nho_ket_qua(monkeypatch):
    goi = []
    monkeypatch.setattr(f.shutil, "which", lambda n: "/usr/bin/firebase")

    def run(cmd, **k):
        goi.append(cmd)
        return subprocess.CompletedProcess(cmd, 1, "", "Failed to list Firebase projects")
    monkeypatch.setattr(f.subprocess, "run", run)
    f.xoa_nho()
    assert f.con_han(1000.0) is False and f.con_han(1100.0) is False and len(goi) == 1   # nho 10 phut
    assert "projects:list" in goi[0]
    f.xoa_nho()
