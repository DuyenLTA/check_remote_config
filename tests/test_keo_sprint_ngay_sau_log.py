"""Log Jira xong keo ngay bug vua tao vao sprint active (quet moi board) - AIP892 17/11/2026 board 348 khong co sprint."""

from rcr import bot_cong_viec, bot_keo_sprint as k


def test_keo_ngay_theo_project_va_bo_luu_y_sprint_cu(monkeypatch):
    goi = []
    monkeypatch.setattr(k, "sprint_active", lambda u, t, p: {"id": 2856, "name": "2.2.0"} if p == "AIP892" else None)
    monkeypatch.setattr(k, "them_vao_sprint", lambda u, t, sid, ks: goi.append((sid, ks)))
    dong = k.keo_ngay("https://j", "t", ["AIP892-58", "AIP892-59", "AIP922-1"])
    assert goi == [(2856, ["AIP892-58", "AIP892-59"])] and "2.2.0" in dong
    kq = {"issues": [{"key": "AIP892-58", "case": "x", "link": "l"}], "sprint": dong,
          "luu_y": "Board AIP892 (id 348) không có sprint active"}
    chu = bot_cong_viec.tin_jira(kq, 1)
    assert "2.2.0" in chu and "không có sprint active" not in chu
