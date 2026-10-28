"""Thong bao Discord: webhook gia la http.server cuc bo, khong cham mang that."""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from rcr import discord_notify, discord_run_message, usage_log, cli_artifact


class _Hook:
    def __init__(self, status=204, delay=0.0):
        self.bodies: list[dict] = []
        self.agents: list[str] = []
        self.raw: list[bytes] = []
        self.types: list[str] = []
        self.auth: list[str] = []
        self.paths: list[str] = []
        outer = self

        class H(BaseHTTPRequestHandler):
            def do_POST(self):
                n = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(n)
                outer.raw.append(raw)
                outer.types.append(self.headers.get("Content-Type", ""))
                # Tin co dinh kem la multipart: JSON nam trong phan `payload_json`.
                if outer.types[-1].startswith("multipart/form-data; boundary="):
                    phan = raw.split(b'name="payload_json"', 1)[1]
                    raw = phan.split(b"\r\n\r\n", 1)[1].split(b"\r\n--", 1)[0]
                else:
                    assert outer.types[-1] == "application/json"
                outer.bodies.append(json.loads(raw))
                outer.agents.append(self.headers.get("User-Agent", ""))
                outer.auth.append(self.headers.get("Authorization", ""))
                outer.paths.append(self.path)
                time.sleep(delay)
                try:
                    self.send_response(status)
                    self.end_headers()
                    if status != 204:
                        self.wfile.write(b"ok")
                except OSError:
                    pass

            def log_message(self, *a):
                pass

        self.srv = HTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_port}/hook"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def close(self):
        self.srv.shutdown()
        self.srv.server_close()


@pytest.fixture
def hook(monkeypatch):
    monkeypatch.setenv("DISCORD_NOTIFY", "1")
    made: list[_Hook] = []

    def make(**kw):
        h = _Hook(**kw)
        made.append(h)
        monkeypatch.setenv("DISCORD_WEBHOOK_URL", h.url)
        return h

    yield make
    for h in made:
        h.close()


def test_payload_dung_dinh_dang(hook):
    h = hook()
    ok = discord_notify.send("stop", "Có 2 FAIL", ["App: X", "FAIL: a, b"],
                           action="Chạy §5d", link="https://x.test/r")
    assert ok is True
    assert h.bodies == [{
        "content": "⛔ **rc-check** · Có 2 FAIL\nApp: X\nFAIL: a, b\n"
                   "→ Chạy §5d\n[Mở report](<https://x.test/r>)",
        "allowed_mentions": {"parse": ["roles", "users"]}}]


def test_gui_user_agent_rieng_khong_phai_cua_urllib(hook):
    h = hook()
    assert discord_notify.send("done", "t", []) is True
    assert h.agents == ["qa-workflow-bot/1.0"]


def test_noi_dung_dai_bi_cat_2000_ky_tu(hook):
    h = hook()
    assert discord_notify.send("done", "t", ["x" * 5000]) is True
    c = h.bodies[0]["content"]
    assert len(c) == 2000 and c.endswith("…")


def test_khong_action_khong_link_thi_bo_dong_do(hook):
    h = hook()
    assert discord_notify.send("done", "Xong", ["l1"]) is True
    assert h.bodies[0]["content"] == "✅ **rc-check** · Xong\nl1"
    discord_notify.send("bug", "B", [])
    assert h.bodies[1]["content"].startswith("🐞 **rc-check** · B")


def test_thieu_env_tra_false_va_mot_dong_stderr(monkeypatch, capsys):
    monkeypatch.setenv("DISCORD_NOTIFY", "1")
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    assert discord_notify.send("done", "t", []) is False
    cap = capsys.readouterr()
    assert cap.out == ""
    assert cap.err.strip() == "discord: DISCORD_WEBHOOK_URL chưa đặt, bỏ qua thông báo"


def test_http_500_tra_false_khong_raise_va_khong_lo_url(hook, capsys):
    h = hook(status=500)
    assert discord_notify.send("done", "t", []) is False
    err = capsys.readouterr().err
    assert "HTTP 500" in err
    assert h.url not in err


def test_timeout_tra_false(hook, monkeypatch, capsys):
    hook(delay=1.5)
    monkeypatch.setattr(discord_notify, "TIMEOUT_S", 0.2)
    assert discord_notify.send("done", "t", []) is False
    assert "gửi thất bại" in capsys.readouterr().err


def test_ket_noi_bi_tu_choi_tra_false(monkeypatch):
    monkeypatch.setenv("DISCORD_NOTIFY", "1")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "http://127.0.0.1:9/x")
    assert discord_notify.send("done", "t", []) is False


def test_scheme_la_bi_chan(monkeypatch):
    monkeypatch.setenv("DISCORD_NOTIFY", "1")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "file:///etc/passwd")
    assert discord_notify.send("done", "t", []) is False


def test_discord_notify_0_khong_gui_request(hook, monkeypatch):
    h = hook()
    monkeypatch.setenv("DISCORD_NOTIFY", "0")
    assert discord_notify.send("done", "t", []) is False
    assert h.bodies == []


def test_cli_luon_exit_0_ke_ca_khi_gui_hong(monkeypatch):
    monkeypatch.setenv("DISCORD_NOTIFY", "1")
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    assert discord_notify.main(["--kind", "stop", "--title", "t", "--line", "a"]) == 0
    assert discord_notify.main(["--kind", "sai"]) == 0


def test_cli_gui_dung_noi_dung(hook):
    h = hook()
    discord_notify.main(["--kind", "stop", "--title", "T", "--line", "a", "--line", "b",
                       "--action", "đi", "--link", "https://l.test"])
    assert h.bodies[0]["content"] == "⛔ **rc-check** · T\na\nb\n→ đi\n[Mở report](<https://l.test>)"


# --- tin cuoi luot chay -------------------------------------------------------

def _rec(key, verdict, thieu=()):
    return {"key": key, "verdict": verdict, "precondition_thieu": list(thieu)}


def _msg(records, **kw):
    s = discord_run_message.summarize(records, app="Piclux 2.8.0", package="com.p", sdk="3.4.0",
                                    duration_s=kw.get("duration_s", 125 * 60),
                                    report="out/r.html")
    return discord_run_message.build_run_message(s)


def test_run_message_co_fail_la_stop():
    kind, title, lines, action = _msg([_rec("3.4.0#1", "PASS"), _rec("3.4.0#2", "FAIL"),
                                       _rec("3.4.0#3", "FAIL")])
    assert kind == "stop"
    assert title == "Có 2 FAIL cần audit lại"
    assert action == "Chạy §5d: xác nhận lại từng FAIL trước khi báo dev"
    assert "FAIL: 3.4.0#2, 3.4.0#3" in lines
    assert "Case: 1 PASS · 2 FAIL · 0 BLOCKED · 0 NOT_VERIFIABLE" in lines
    assert "Thời gian: 2 giờ 5 phút" in lines
    assert "Report: out/r.html" in lines


def test_run_message_toi_da_10_case_fail():
    kind, _, lines, _ = _msg([_rec(f"c{i}", "FAIL") for i in range(13)])
    line = next(l for l in lines if l.startswith("FAIL: "))
    assert line.count("c") >= 10 and "c9" in line and "c10" not in line
    assert "+3 case nữa" in line


def test_run_message_blocked_them_dong_ly_do():
    kind, _, lines, action = _msg([_rec("a", "PASS"), _rec("b", "BLOCKED", ["config bị app fetch đè"]),
                                   _rec("c", "NOT_VERIFIABLE")])
    assert kind == "done" and action is None
    blocked = next(l for l in lines if l.startswith("BLOCKED:"))
    assert "config bị ghi đè" in blocked and "config bị app fetch đè" in blocked
    assert "1 BLOCKED · 1 NOT_VERIFIABLE" in next(l for l in lines if l.startswith("Case:"))


def test_run_message_tat_ca_pass_la_done():
    kind, title, lines, action = _msg([_rec("a", "PASS"), _rec("b", "PASS")], duration_s=None)
    assert (kind, action) == ("done", None)
    assert "Piclux 2.8.0" in title
    assert "Thời gian: ?" in lines
    assert not any(l.startswith(("FAIL:", "BLOCKED:")) for l in lines)


# --- usage-log ----------------------------------------------------------------

LOG = """# Log

| Ngày | App |
|---|---|
| 1 | a |
| 2 | b |

Đoạn văn sau bảng.
"""


def test_usage_log_chen_sau_dong_cuoi_bang(tmp_path):
    p = tmp_path / "usage-log.md"
    p.write_text(LOG, encoding="utf-8")
    row = usage_log.build_row(date="22/10/2026", app="X", version="1.0", cases="5",
                              result="5 PASS", bugs="0", report="https://r", tool_minutes=45)
    assert usage_log.append_row(row, p) is True
    out = p.read_text(encoding="utf-8").split("\n")
    assert out[:6] == LOG.split("\n")[:6]
    assert out[6] == row
    assert out[7:] == LOG.split("\n")[6:]
    assert row.endswith("| 45 phút | 3 giờ | 135 phút |")


def test_usage_log_khong_biet_thoi_gian_thi_dau_hoi():
    assert usage_log.saving(None) == "?"
    assert usage_log.build_row(date="d", app="a|b", version="", cases="", result="", bugs="",
                               report="r", tool_minutes=None).count("?") == 2


def test_usage_log_khong_co_bang_thi_khong_ghi(tmp_path):
    p = tmp_path / "x.md"
    p.write_text("khong co bang\n", encoding="utf-8")
    assert usage_log.append_row("| r |", p) is False
    assert p.read_text(encoding="utf-8") == "khong co bang\n"


def test_rcr_artifact_ghi_log_va_gui_discord(hook, tmp_path):
    h = hook()
    log = tmp_path / "u.md"
    log.write_text(LOG, encoding="utf-8")
    rc = cli_artifact.main([
        "--url", "https://claude.ai/a/1", "--generated-at", "2026-10-22T10:00:00+0700",
        "--out", str(tmp_path), "--app", "Piclux", "--tool-minutes", "60",
        "--usage-log", str(log)])
    assert rc == 0
    assert "| Piclux |" in log.read_text(encoding="utf-8")
    assert h.bodies[0]["content"] == ("✅ **rc-check** · Report đã publish · Piclux\n"
                                   "[Mở report](<https://claude.ai/a/1>)")


def test_rcr_artifact_khong_app_thi_khong_dong_vao_log(tmp_path):
    log = tmp_path / "u.md"
    log.write_text(LOG, encoding="utf-8")
    cli_artifact.main(["--url", "https://claude.ai/a/1", "--generated-at", "t",
                       "--out", str(tmp_path), "--usage-log", str(log)])
    assert log.read_text(encoding="utf-8") == LOG


# --- chay khong Claude ---------------------------------------------------------

def _msg_kc(records):
    s = discord_run_message.summarize(records, app="Piclux 2.8.0", package="com.p", sdk="3.4.0",
                                    duration_s=60, report="out/r.html", khong_claude=True)
    return discord_run_message.build_run_message(s)


def test_khong_claude_fail_khong_tro_toi_muc_cua_agent():
    kind, _, _, action = _msg_kc([_rec("a", "FAIL"), _rec("b", "FAIL")])
    assert kind == "stop"
    assert "§5d" not in action and "lặp lại" in action


def test_khong_claude_con_blocked_na_thi_stop_can_nguoi_xem():
    kind, title, lines, action = _msg_kc([_rec("a", "PASS"), _rec("b", "BLOCKED"),
                                          _rec("c", "NOT_VERIFIABLE")])
    assert kind == "stop"
    assert title == "Xong, 2 case cần người xem · Piclux 2.8.0"
    assert any(l.startswith("Cần người xem: 2 case (1 BLOCKED") for l in lines)
    assert "BLOCKED" in action


def test_khong_claude_tat_ca_pass_van_done():
    kind, _, lines, action = _msg_kc([_rec("a", "PASS")])
    assert (kind, action) == ("done", None)
    assert not any(l.startswith("Cần người xem") for l in lines)


def test_co_claude_giu_nguyen_tin_cu():
    kind, _, lines, action = _msg([_rec("a", "PASS"), _rec("b", "BLOCKED")])
    assert (kind, action) == ("done", None)
    assert not any(l.startswith("Cần người xem") for l in lines)


def test_gui_kem_file_report_bang_multipart(hook, tmp_path):
    h = hook()
    report = tmp_path / "rc-x.html"
    report.write_text("<h1>Báo cáo</h1>", encoding="utf-8")
    assert discord_notify.send("done", "Xong", ["dòng 1"], file=report)
    assert h.types[0].startswith("multipart/form-data; boundary=")
    assert b'filename="rc-x.html"' in h.raw[0]
    assert "<h1>Báo cáo</h1>".encode("utf-8") in h.raw[0]
    assert "dòng 1" in h.bodies[0]["content"]


def test_file_qua_lon_thi_gui_tin_khong_kem(hook, tmp_path, monkeypatch):
    h = hook()
    report = tmp_path / "to.html"
    report.write_text("x" * 50, encoding="utf-8")
    monkeypatch.setattr(discord_notify, "MAX_FILE", 10)
    assert discord_notify.send("done", "Xong", [], file=report)
    assert h.types[0] == "application/json"
    assert "quá lớn" in h.bodies[0]["content"]


def test_upload_hong_thi_van_gui_tin_chu_kem_duong_dan(tmp_path, monkeypatch):
    from pathlib import Path
    monkeypatch.setenv("DISCORD_NOTIFY", "1")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "http://127.0.0.1:9/hook")
    report = tmp_path / "r.html"
    report.write_text("x", encoding="utf-8")
    gui: list = []

    def post(url, payload, dinh_kem, them=None):
        gui.append((payload["content"], dinh_kem is not None))
        return dinh_kem is None

    monkeypatch.setattr(discord_notify, "_post", post)
    assert discord_notify.send("done", "Xong", [], file=report)
    assert [co for _, co in gui] == [True, False]
    assert "Không gửi kèm được report" in gui[1][0]
    assert discord_notify._ten_file(Path('báo "cáo".html')) == "b_o__c_o_.html"


def test_may_co_bot_thi_gui_bang_bot_vao_kenh_qa(hook, monkeypatch):
    """User chot 28/10/2026: tin rcr-notify ve kenh qa-auto qua bot, khong qua webhook kenh chung."""
    webhook, api = hook(), hook()
    monkeypatch.setattr(discord_notify, "_qua_bot",
                        lambda: (api.url.replace("/hook", "/channels/42/messages"), {"Authorization": "Bot tk"}))
    assert discord_notify.send("done", "Report đã publish", ["AI Song"]) is True
    assert webhook.bodies == [] and api.paths == ["/channels/42/messages"] and api.auth == ["Bot tk"]
    assert api.bodies[0]["content"].startswith("✅ **rc-check** · Report đã publish")


def test_dich_bot_tu_token_va_kenh_qa():
    url, them = discord_notify._dich_bot("tk", "1562794153082097695")
    assert url == "https://discord.com/api/v10/channels/1562794153082097695/messages" and them == {"Authorization": "Bot tk"}
    assert discord_notify._dich_bot("tk", "khong-phai-so") is None
    assert discord_notify._dich_bot("", "1") is None
