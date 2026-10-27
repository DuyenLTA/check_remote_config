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
TOOLS = ["Bash", "Read", "Edit", "Write", "Artifact", "Skill"]
KET_QUA_RE = re.compile(r"^KET_QUA:\s*(\{.*\})\s*$", re.M)
# Nhanh bo TC chay lau hon nhieu nhanh checklist Next-Gen.
TIMEOUT_BO_TC = 120 * 60
TIMEOUT_NEXT_GEN = 30 * 60
DUOI_LOG = 300

PROMPT = (
    "/rc-check {package} --serial {serial}\n\n"
    "Tra loi hoan toan bang tieng Viet. Luot nay do bot Discord goi, khong co nguoi ngoi truoc may. Gap diem can nguoi quyet "
    "(ad_click, preflight LOI, man la) thi dung, khong tu chay tiep. Khong commit/push.\n"
    "Dong CUOI cung cua cau tra loi phai dung mau (mot dong JSON):\n"
    'KET_QUA: {{"trang_thai": "XONG|DUNG|LOI", "link": "<link artifact claude.ai neu publish duoc, khong thi duong dan TUYET DOI file report .html>", '
    '"tom_tat": "<tieng Viet, toi da 300 ky tu: so PASS/FAIL hoac ly do dung>"}}'
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
    """Output JSON cua `claude -p` -> {trang_thai, link, tom_tat, chi_phi, phut}."""
    try:
        d = json.loads(stdout)
    except json.JSONDecodeError:
        return {"trang_thai": "LOI", "link": "", "tom_tat": (stdout or "")[-DUOI_LOG:]}
    text = d.get("result") or ""
    ra = {"trang_thai": "LOI" if d.get("is_error") else "XONG", "link": "", "tom_tat": text[-DUOI_LOG:]}
    m = None
    for m in KET_QUA_RE.finditer(text):
        pass                                     # lay dong KET_QUA cuoi cung
    if m:
        try:
            k = json.loads(m.group(1))
            ra.update({x: str(k.get(x, ra[x])) for x in ("trang_thai", "link", "tom_tat")})
        except json.JSONDecodeError:
            pass
    ra["chi_phi"] = d.get("total_cost_usd")
    ra["phut"] = round((d.get("duration_ms") or 0) / 60000, 1)
    return ra


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
