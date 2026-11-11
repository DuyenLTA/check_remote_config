"""Kiem chinh file workflow `.claude/commands/rc-check.md` va cac file chi tiet `docs/rc-check/`.

Workflow la thu agent doc va lam theo moi luot: duong dan sai / lenh da doi ten / luat viet chong len luat cu
lam agent lam sai ma khong ai biet (09/11/2026: 6 cho mau thuan + 6 duong dan `data/*.yaml` khong ton tai).
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
WORKFLOW = REPO / ".claude" / "commands" / "rc-check.md"
CHI_TIET = sorted((REPO / "docs" / "rc-check").glob("*.md"))
CAC_FILE = [WORKFLOW, *CHI_TIET]

# File chinh chi giu luong chinh + luat dang ap dung; chi tiet dua sang docs/rc-check/.
TRAN_DONG_WORKFLOW = 400

# Moi duong dan tuong doi trong backtick phai co that trong repo, tru cac goc nam ngoai repo:
# out/ (sinh luc chay), tools/ (repo audit), shared_prefs/ (tren may Android).
NGOAI_REPO = ("out/", "tools/", "shared_prefs/")
DUONG_DAN = re.compile(r"^\.?[\w-]+(?:/[\w.-]+)*(?:/|/[\w-]+\.\w+)$")  # co duoi file, hoac thu muc ket thuc /

# Cac muc ma code / prompt cua bot tham chieu theo so ("rc-check.md muc 0c").
MUC_BAT_BUOC = ("0", "0b", "0c", "1", "2", "3", "3b", "3c", "4", "5", "5b", "5c", "5d", "5d2", "5e", "6", "7", "7a", "7b")


def _doc(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _duong_dan_trong_backtick(text: str) -> set[str]:
    ra = set()
    for tok in re.findall(r"`([^`\n]+)`", text):
        tok = tok.strip()
        if " " in tok or "<" in tok or "*" in tok or "$" in tok:
            continue
        tok = tok.rstrip(".,;:")
        if DUONG_DAN.match(tok) and not tok.startswith(NGOAI_REPO):
            ra.add(tok)
    return ra


def _frontmatter(text: str) -> dict[str, str]:
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert m, "thieu frontmatter"
    ra = {}
    for dong in m.group(1).splitlines():
        k, _, v = dong.partition(":")
        ra[k.strip()] = v.strip()
    return ra


def test_co_file_chi_tiet():
    assert CHI_TIET, "docs/rc-check/ trong"


@pytest.mark.parametrize("p", CAC_FILE, ids=lambda p: p.name)
def test_duong_dan_trong_repo_ton_tai(p):
    thieu = sorted(d for d in _duong_dan_trong_backtick(_doc(p)) if not (REPO / d).exists())
    assert not thieu, f"{p.name} nhac toi duong dan khong ton tai: {thieu}"


@pytest.mark.parametrize("p", CAC_FILE, ids=lambda p: p.name)
def test_lenh_rcr_co_trong_pyproject(p):
    scripts = tomllib.loads(_doc(REPO / "pyproject.toml"))["project"]["scripts"]
    dung = set(re.findall(r"\brcr-[a-z][a-z-]*[a-z]\b", _doc(p)))
    la = sorted(dung - set(scripts))
    assert not la, f"{p.name} goi lenh khong co trong [project.scripts]: {la}"


def test_workflow_tro_toi_moi_file_chi_tiet():
    text = _doc(WORKFLOW)
    sot = [p.name for p in CHI_TIET if f"docs/rc-check/{p.name}" not in text]
    assert not sot, f"file chi tiet khong duoc workflow tro toi (agent se khong bao gio doc): {sot}"


def test_workflow_gon():
    n = len(_doc(WORKFLOW).splitlines())
    assert n <= TRAN_DONG_WORKFLOW, (
        f"rc-check.md {n} dong > {TRAN_DONG_WORKFLOW}: dua chi tiet / lich su su co sang docs/rc-check/, "
        "sua dung cho luat cu thay vi viet chong")


def test_giu_so_muc_ma_code_tham_chieu():
    co = set(re.findall(r"^## (\w+)\.", _doc(WORKFLOW), re.M))
    thieu = [m for m in MUC_BAT_BUOC if m not in co]
    assert not thieu, f"mat muc {thieu} — bot_chay_claude.py / comment code tham chieu theo so muc"


def test_khong_con_luat_cu_da_bo():
    """Cac cau luat da doi (user chot) khong duoc quay lai qua copy-paste."""
    text = "\n".join(_doc(p) for p in CAC_FILE)
    cam = {
        "DUNG LUOT": "ad_click khong con dung luot (muc 0c)",
        "Xin dev bản debuggable": "khong xin dev ban debuggable; ID test chi canh bao",
        "rồi tự mở link": "publish xong chi dua link, khong tu mo",
        "pull`\n  APK debug": "may moi cai lai ban release tu App Tester",
    }
    gap = [f"{c!r}: {ly_do}" for c, ly_do in cam.items() if c in text]
    assert not gap, gap


def test_ban_tro_toan_cuc_khop_mo_ta():
    """~/.claude/commands/rc-check.md (ban tro tren tung may) phai cung description voi repo."""
    tro = Path.home() / ".claude" / "commands" / "rc-check.md"
    if not tro.exists():
        pytest.skip("may nay khong cai ban tro toan cuc")
    a, b = _frontmatter(_doc(tro)), _frontmatter(_doc(WORKFLOW))
    assert a.get("description") == b.get("description"), "description ban tro lech repo — chep lai tu repo"
    assert a.get("argument-hint") == b.get("argument-hint"), "argument-hint ban tro lech repo — chep lai tu repo"


KB_CHANGELOG = REPO / "docs" / "kb-changelog.md"
FILE_LUAT = [*CAC_FILE, REPO / "sdk-check" / "WORKFLOW.md", REPO / ".claude" / "commands" / "sub-check.md"]
NGAY_CHOT = re.compile(r"(?:chốt|đổi)(?: lại)? (\d{2}/\d{2}/\d{4})")


def test_ngay_chot_luat_co_trong_kb_changelog():
    """Luat moi ghi "user chot dd/mm/yyyy" trong file luat ma kb-changelog khong co dong ngay do -> lich su
    thay doi luat bi dut, khong chung minh duoc luat duoc cap nhat theo nghiep vu."""
    # Chi tim trong muc "Luat user / QA chot": ngay trung voi dong "Bai hoc" khong duoc tinh la da ghi luat.
    kb = _doc(KB_CHANGELOG).split("## Luật user / QA chốt", 1)[-1].split("\n## ", 1)[0]
    ngay = {d for p in FILE_LUAT for d in NGAY_CHOT.findall(_doc(p))}
    thieu = sorted(d for d in ngay if f"| {d} |" not in kb)
    assert not thieu, f"them dong vao docs/kb-changelog.md (muc 'Luat user / QA chot') cho ngay: {thieu}"
