"""rcr-do-thoi-gian: bang theo loai va so ket qua tung dong (so lieu gia lap theo lan do AIP918 12/11/2026)."""

from rcr import do_thoi_gian, do_thoi_gian_bang as b


def test_bang_gom_theo_loai_va_phan_tram():
    d = {"tong": 100.0, "ghi": [
        ("adb", "shell uiautomator dump /data/local/tmp/rcr_uidump.xml", 30.0, 1.0, "fo_flow.py:10"),
        ("adb", "shell input tap 10 20", 1.0, 2.0, "act_exec.py:5"),
        ("http", "GET https://firebaseremoteconfig.googleapis.com/v1/x", 13.0, 3.0, "rc_firebase.py:9"),
        ("sleep", "1s", 18.0, 4.0, "fo_flow.py:20"),
        ("adb_bin", "exec-out screencap -p", 5.0, 5.0, "screencap.py:1"),
    ]}
    text = b.bang(d, "uiautomator dump")
    assert "uiautomator dump" in text and "30.0%" in text and "http firebase" in text and "screencap" in text
    assert "(khong do duoc)" in text and "33.0s" in text      # 100 - 67
    assert "fo_flow.py:10" in text                              # chi tiet theo noi goi


def test_so_dong_danh_dau_dong_lech():
    a = {"records": [{"key": "k1", "verdict": "FAIL", "lines": [{"v": "PASS", "e": "x"}, {"v": "FAIL", "e": "y"}]}]}
    c = {"records": [{"key": "k1", "verdict": "PASS", "lines": [{"v": "PASS", "e": "x"}, {"v": "PASS", "e": "y"}]}]}
    text, lech = b.so_dong([a, c])
    assert lech == 1 and "LECH" in text


def test_main_bang_doc_file(tmp_path, capsys):
    f = tmp_path / "do.json"
    f.write_text('{"tong": 10, "ghi": [["adb", "shell input tap 1 2", 1.0, 0.0, ""]]}', encoding="utf-8")
    assert do_thoi_gian.main(["bang", str(f)]) == 0
    assert "input tap/swipe" in capsys.readouterr().out
