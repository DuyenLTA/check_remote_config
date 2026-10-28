"""Chay `/rc-check <package>` bang Claude headless cho mot build bot da cai xong.

Prompt co dinh, chi ghep PACKAGE da xac nhan bang dumpsys sau khi cai - khong
ghep chu tu tin Discord vao prompt (tin do ai cung go duoc -> prompt injection).

Goi `claude` thang bang subprocess, KHONG qua bash: Git Bash (MSYS) doi
"/rc-check" thanh "C:/Program Files/Git/rc-check" (do 2026-10-27).
Prompt di qua STDIN, khong qua tham so: tren Windows `claude` la claude.CMD, cmd.exe
cat tham so o dau xuong dong dau tien -> mat --allowedTools / --output-format, Claude
dung cho duyet quyen roi bo cuoc (luot bot dau tien 27/10/2026).
Khong dung --dangerously-skip-permissions: luot lai may that, chi mo dung danh
sach tool. Spike 2026-10-27: voi danh sach nay `-p` khong hoi quyen, khong treo.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

SERIAL_RE = re.compile(r"[A-Za-z0-9.:_-]+")
PACKAGE_RE = re.compile(r"^[a-zA-Z][\w]*(\.[a-zA-Z_][\w]*)+$")
# Workflow: buoc check ID ads (rc-check.md muc 3c) chay workflow audit-fanout.
TOOLS = ["Bash", "Read", "Edit", "Write", "Artifact", "Skill", "Workflow"]
KET_QUA_RE = re.compile(r"^KET_QUA:\s*(\{.*\})\s*$", re.M)
# Nhanh bo TC chay lau hon nhieu nhanh checklist Next-Gen. Ca hai cong ~15 phut cho
# buoc check ID ads (capture + agent phan), build chua doi thi audit bo qua nhanh.
TIMEOUT_BO_TC = 135 * 60
TIMEOUT_NEXT_GEN = 45 * 60
DUOI_LOG = 300
# Menu chon cua Discord toi da 25 lua chon; moi truong cat ngan de tin khong phinh.
MAX_BUG = 25
TRUONG_BUG = ("case", "tieu_de", "precondition", "buoc", "expected", "thuc_te", "muc_do")
MAX_TRUONG_BUG = 1000

PROMPT = (
    "/rc-check {package} --serial {serial}\n\n"
    "Tra loi hoan toan bang tieng Viet. Luot nay do bot Discord goi, khong co nguoi ngoi truoc may. Gap diem can nguoi quyet "
    "(ad_click, preflight LOI, ID ads lech sheet, man la) thi dung, khong tu chay tiep. Khong commit/push.\n"
    "Dong CUOI cung cua cau tra loi phai dung mau (mot dong JSON):\n"
    'KET_QUA: {{"trang_thai": "XONG|DUNG|LOI", "link": "<link artifact claude.ai neu publish duoc, khong thi duong dan TUYET DOI file report .html>", '
    '"tom_tat": "<tieng Viet, toi da 300 ky tu: so PASS/FAIL hoac ly do dung>", '
    '"bugs": [{{"case": "<ma case>", "tieu_de": "<tom tat bug>", "precondition": "<config/user state>", '
    '"buoc": "<buoc tai hien>", "expected": "<dong Expected>", "thuc_te": "<so do that>", '
    '"muc_do": "Highest|High|Medium|Low"}}]}}\n'
    "Moi chu trong `tom_tat` va `bugs` (bot dang len Discord) viet tieng Viet CO DAU day du. "
    "`bugs` chi gom FAIL da ra lai theo muc 5d (FAIL gia, loi tool thi khong dua vao); khong co thi []. "
    "KHONG hoi user, KHONG tu log Jira: bot dua danh sach nay len Discord cho QA tick."
)


def lenh(package: str, serial: str) -> tuple[list[str], str]:
    """(lenh, prompt dua vao stdin). Nhieu may cam cung luc -> luon chi dinh serial."""
    if not PACKAGE_RE.match(package or ""):
        raise ValueError(f"package không hợp lệ: {package!r}")
    if not SERIAL_RE.fullmatch(serial or ""):
        raise ValueError(f"serial không hợp lệ: {serial!r}")
    exe = shutil.which("claude") or "claude"
    return [exe, "-p", "--output-format", "json", "--allowedTools", *TOOLS], PROMPT.format(package=package, serial=serial)


def doc_ket_qua(stdout: str) -> dict:
    """Output JSON cua `claude -p` -> {trang_thai, link, tom_tat, bugs, chi_phi, phut}."""
    try:
        d = json.loads(stdout)
    except json.JSONDecodeError:
        return {"trang_thai": "LOI", "link": "", "tom_tat": (stdout or "")[-DUOI_LOG:]}
    text = d.get("result") or ""
    ra = {"trang_thai": "LOI" if d.get("is_error") else "XONG", "link": "", "tom_tat": text[-DUOI_LOG:], "bugs": []}
    m = None
    for m in KET_QUA_RE.finditer(text):
        pass                                     # lay dong KET_QUA cuoi cung
    if m:
        try:
            k = json.loads(m.group(1))
            ra.update({x: str(k.get(x, ra[x])) for x in ("trang_thai", "link", "tom_tat")})
            ra["bugs"] = doc_bugs(k.get("bugs"))
        except json.JSONDecodeError:
            pass
    ra["chi_phi"] = d.get("total_cost_usd")
    ra["phut"] = round((d.get("duration_ms") or 0) / 60000, 1)
    return ra


def doc_bugs(bugs) -> list[dict]:
    """Danh sach bug Claude tra ve -> chi giu dict co `case`, moi truong la chuoi da cat ngan."""
    if not isinstance(bugs, list):
        return []
    ra = []
    for b in bugs:
        if isinstance(b, dict) and str(b.get("case") or "").strip():
            ra.append({x: str(b.get(x) or "").strip()[:MAX_TRUONG_BUG] for x in TRUONG_BUG})
    return ra[:MAX_BUG]


def moi_truong() -> dict[str, str]:
    """Env cua luot: tat webhook `rcr-notify` (DISCORD_NOTIFY=0) - bot da bao vao chinh tin
    cua build, webhook gui them la kenh nhan hai tin cho mot viec (user chot 27/10/2026)."""
    return {**os.environ, "DISCORD_NOTIFY": "0"}


def chay(package: str, serial: str, repo: Path, timeout: int, log_dir: Path) -> dict:
    """Chay mot luot, log day du o `log_dir/bot-luot-<gio>.log`. Qua gio -> kill, trang_thai HET_GIO."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log = log_dir / f"bot-luot-{time.strftime('%Y%m%d-%H%M%S')}-{serial}.log"
    try:
        cmd, prompt = lenh(package, serial)
        p = subprocess.run(cmd, input=prompt, cwd=repo, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout, env=moi_truong())
    except subprocess.TimeoutExpired as exc:
        log.write_text(f"HET GIO sau {timeout}s\n{exc.stdout or ''}\n{exc.stderr or ''}", encoding="utf-8")
        return {"trang_thai": "HET_GIO", "link": "", "tom_tat": f"quá {timeout // 60} phút", "log": str(log)}
    log.write_text(f"exit={p.returncode}\n--- stdout\n{p.stdout}\n--- stderr\n{p.stderr}", encoding="utf-8")
    ra = doc_ket_qua(p.stdout)
    if p.returncode and ra["trang_thai"] == "XONG":
        ra["trang_thai"] = "LOI"
    ra["log"] = str(log)
    return ra
