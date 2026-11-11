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

from . import audit_tom_tat, bot_tien_trinh

SERIAL_RE = re.compile(r"[A-Za-z0-9.:_-]+")
SDK_RE = re.compile(r"\d+\.\d+\.\d+(?:-[\w.]+)?")   # so tutorial tu tin build (3.6.1, 3.7.1-alpha01)
VERSION_RE = re.compile(r"\d+(?:\.\d+)+ \(\d+\)")   # version build "3.7.0 (30)" (/check-sub)
PACKAGE_RE = re.compile(r"^[a-zA-Z][\w]*(\.[a-zA-Z_][\w]*)+$")
# Workflow: buoc check ID ads (rc-check.md muc 3c) chay workflow audit-fanout.
TOOLS = ["Bash", "Read", "Edit", "Write", "Skill", "Workflow"]   # Artifact: -p khong nap
KET_QUA_RE = re.compile(r"^KET_QUA:\s*(\{.*\})\s*$", re.M)
# Luot check (bo TC / checklist Next-Gen) KHONG gioi han thoi gian: chay het case moi thoi (user chot 04/11/2026
# sau khi AIP893 52 case bi cat o 135 phut giua vong chay lai case chua PASS). Luot treo thi QA bam Dung.
# Vo han chi ap cho ca phien `claude -p`: lenh nen BEN TRONG phien van bi Claude Code cat ~2 gio (AIP862 3.0.0 (23)
# 11/11/2026 cat o 10/33 case) -> PROMPT bat chay tiep bang --tiep moi lan bi cat.
KHONG_GIOI_HAN = float("inf")
TIMEOUT_BO_TC = KHONG_GIOI_HAN
TIMEOUT_NEXT_GEN = KHONG_GIOI_HAN
DUOI_LOG = 300
# Menu chon cua Discord toi da 25 lua chon; moi truong cat ngan de tin khong phinh.
MAX_BUG = 25
TRUONG_BUG = ("case", "tieu_de", "precondition", "buoc", "expected", "thuc_te", "muc_do")
MAX_TRUONG_BUG = 1000

# Nhanh checklist: chay het, do tay het, chi Khop/Sai; moi may la may test AdMob, duoc bam ad (rc-check.md muc 0c).
# Luot AIP918 2.4.0 (29/10/2026) dung vi 1 ad_click tren may test va bo 20 dong do tay - user da dan chay het.
NHAC_NEXT_GEN = (
    "Nhanh checklist Next-Gen: CHAY HET va DO TAY HET moi dong DO_TAY theo sdk-check/WORKFLOW.md (luat 10-11), ghi "
    "--cham-tay ra Khop/Sai; chi bao xong khi report khong con dong Do tay. Duoc bam quang cao de do. Dong that su "
    "khong do duoc thi thu het cach roi ghi ro da thu gi va can dung thu gi. Moi dong do tay lam DU buoc trong "
    "`can_do_tay` (stdout rcr-sdk-check) va khai tung buoc bang --buoc; dong da Sai o luot cu cung build giu Sai tru "
    "khi chay lai buoc tai hien (--khong-tai-hien); report co muc 'Lech giua cac luot' thi neu ro trong cau bao "
    "(WORKFLOW.md muc 'Do tay ra cung ket qua moi luot').\n"
)
# Moi may QA deu la may test AdMob (user chot 29/10/2026): ad_click khong bao gio la ly do dung - luot AIP805
# 1.4.0 (14) dung o buoc check ID ads vi tuong may chua dang ky test device.
PROMPT = (
    "/rc-check {package} --serial {serial}{next_gen}{sdk}\n\n"
    "{nhac}Tra loi hoan toan bang tieng Viet. Luot nay do bot Discord goi, khong co nguoi ngoi truoc may. Gap diem can "
    "nguoi quyet (preflight LOI, man la) thi dung, khong tu chay tiep. ID ads lech sheet (audit-fanout) KHONG phai ly "
    "do dung: ghi vi tri lech vao cau bao roi CHAY NOT checklist / bo TC, cham dong ads vi tri lech theo unit that "
    "trong log (rc-check.md muc 3c). Moi may deu la may test AdMob "
    "(rc-check.md muc 0c): ad_click KHONG phai ly do dung - ghi vao report, chay lai case bi ad_click roi chay tiep. "
    "Khong commit/push.\n"
    "Truoc khi chay bo TC: trong out/ co file *.luot.json cung package + serial nay, \"xong\": false, "
    "`cap_nhat` trong 12 gio -> luot truoc bi tat giua chung (may tinh khoi dong lai): "
    "CHAY TIEP bang `rcr-check --tiep <file>`, KHONG chay lai tu dau cac case da co ket qua.\n"
    "Lenh nen (run_in_background) bi Claude Code cat o moc thoi gian toi da (status killed, 'background time limit'): "
    "luot CHUA xong - chay tiep ngay bang `rcr-check --tiep <file .luot.json cua luot do>` (lai chay nen), lap lai moi "
    "lan bi cat toi khi file luot \"xong\": true; KHONG chay lai tu dau, KHONG bao xong / dung khi con case chua chay.\n"
    "Workflow audit chay nen: CHO thong bao no xong roi lam tiep trong CUNG luot nay; KHONG ScheduleWakeup, KHONG "
    "ket thuc cau tra loi khi con viec nen hay chua chay checklist/case. KHONG tu viet vong lap sleep doc "
    "journal.jsonl / file output de cho: thong bao xong chi toi khi lenh Bash dang chay ket thuc, vong lap do giu may "
    "dung im toi het han (AIP872 04/11/2026 mat ~7 phut). Trong luc cho thi lam viec khong can may (doc TC, preflight).\n"
    "Phien `claude -p` KHONG co tool Artifact (khong nap, 09/11/2026): dung mat thoi gian thu publish. Check ID ads van "
    "lam DU buoc dung trang audit (audit-fanout muc 3: findings/notes + artifact_report_builder.py -> <pkg>-artifact.html "
    "trong out cua repo audit) - report rc-check lay tab Check ID ads tu file do; chi BO buoc publish + artifact_link. "
    "Repo audit da duoc --add-dir: chep script workflow bang `cat <repo audit>/.claude/workflows/audit-fanout.mjs > out/scratch-<ngay>/audit-fanout.mjs` (lenh `cp` tu duong dan .claude bi -p chan) roi goi Workflow. "
    "`link` = duong dan TUYET DOI report .html.\n"
    "Sua tool giua luot: chi chay test cua file vua sua (pytest tests/test_<file>.py), KHONG chay ca bo test - "
    "may dung im trong luc cho.\n"
    "Dong CUOI cung cua cau tra loi phai dung mau (mot dong JSON):\n"
    'KET_QUA: {{"trang_thai": "XONG|DUNG|LOI", "link": "<link artifact claude.ai neu publish duoc, khong thi duong dan TUYET DOI file report .html>", '
    '"tom_tat": "<tieng Viet, toi da 300 ky tu: so PASS/FAIL hoac ly do dung>", '
    '"bugs": [{{"case": "<ma case>", "tieu_de": "<tom tat bug>", "precondition": "<config/user state>", '
    '"buoc": "<buoc tai hien>", "expected": "<dong Expected>", "thuc_te": "<so do that>", '
    '"muc_do": "Highest|High|Medium|Low"}}]}}\n'
    "Moi chu trong `tom_tat` va `bugs` (bot dang len Discord) viet tieng Viet CO DAU day du. "
    "`bugs` chi gom FAIL da ra lai theo muc 5d (FAIL gia, loi tool thi khong dua vao); khong co thi []. "
    "KHONG hoi user, KHONG tu log Jira: bot dua danh sach nay len Discord cho QA tick.\n"
    "Co bug (`bugs` khac []) thi report phai dung xong truoc khi tra loi, ke ca khi dung giua luot (trang_thai DUNG) "
    "hay con dong chua do: dung report tam, ghi ro phan chua xong - bot dinh kem file report cho QA review bug."
)
# Luot verify bug dev da keo sang Reviewing: chi chay lai dung cac case, bot tu doi trang thai Jira theo verdict.
PROMPT_VERIFY = (
    "/rc-check {package} --serial {serial} --case \"{cases}\"\n\n"
    "Tra loi hoan toan bang tieng Viet. Luot nay do bot Discord goi de VERIFY bug dev bao da fix: chi chay dung cac case "
    "tren (bo TC mac dinh), bo muc 3c (check ID ads), van ra lai FAIL theo muc 5d. Khong co nguoi ngoi truoc may: gap diem "
    "can nguoi quyet thi dung. Khong commit/push. KHONG doc/sua/log Jira - bot tu lam theo verdict.\n"
    "Dong CUOI cung cua cau tra loi phai dung mau (mot dong JSON):\n"
    'KET_QUA: {{"trang_thai": "XONG|DUNG|LOI", "link": "<link artifact claude.ai neu publish duoc, khong thi duong dan TUYET DOI file report .html>", '
    '"tom_tat": "<tieng Viet co dau, toi da 300 ky tu>", '
    '"cases": [{{"case": "<ma case dung nhu tren>", "verdict": "PASS|FAIL|BLOCKED|NEEDS_HUMAN|KHONG_ON_DINH", '
    '"thuc_te": "<so do that, tieng Viet co dau>"}}]}}\n'
    "`verdict` FAIL chi khi da ra lai theo 5d va chac la bug that; FAIL gia / loi tool / chua chac thi NEEDS_HUMAN."
)
TIMEOUT_VERIFY = 40 * 60
# Verify dong checklist Next-Gen: chay ca checklist (rcr-sdk-check) roi do tay rieng cac ma can verify.
PROMPT_VERIFY_CHECKLIST = (
    "/rc-check {package} --serial {serial} --next-gen\n\n"
    "Tra loi hoan toan bang tieng Viet. Luot nay do bot Discord goi de VERIFY bug dev bao da fix, bug thuoc NHANH CHECKLIST "
    "Next-Gen. Chay checklist (rcr-sdk-check) cho app nhu thuong; dong nao ra DO_TAY thi CHI do tay (theo sdk-check/WORKFLOW.md) "
    "cac ma dong sau, khong do tay dong khac, bo muc 3c (check ID ads): {cases}\n"
    "Khong co nguoi ngoi truoc may: gap diem can nguoi quyet thi dung. Khong commit/push. KHONG doc/sua/log Jira - bot tu lam "
    "theo verdict.\n"
    "Dong CUOI cung cua cau tra loi phai dung mau (mot dong JSON), moi ma dong mot phan tu trong `cases`:\n"
    'KET_QUA: {{"trang_thai": "XONG|DUNG|LOI", "link": "<link artifact claude.ai neu publish duoc, khong thi duong dan TUYET DOI file report .html>", '
    '"tom_tat": "<tieng Viet co dau, toi da 300 ky tu>", '
    '"cases": [{{"case": "<ma dong dung nhu tren>", "verdict": "PASS|FAIL|NEEDS_HUMAN", '
    '"thuc_te": "<so do that, tieng Viet co dau>"}}]}}\n'
    "`verdict` theo ket cua dong do: KHOP -> PASS, SAI -> FAIL (chi khi chac la bug that), DO_TAY chua do duoc / KHONG_AP_DUNG / "
    "loi tool -> NEEDS_HUMAN."
)
TIMEOUT_VERIFY_CHECKLIST = 70 * 60
# Check sub Android (/check-sub): ca bo 45 TC, moi lan quay lai "chua mua" phai cho het mot chu ky test (~5 phut).
DUOI_KET_QUA = (
    "Dong CUOI cung cua cau tra loi phai dung mau (mot dong JSON):\n"
    'KET_QUA: {{"trang_thai": "XONG|DUNG|LOI", "link": "<link artifact claude.ai neu publish duoc, khong thi duong dan TUYET DOI file report .html>", '
    '"tom_tat": "<tieng Viet co dau, toi da 300 ky tu: so PASS/FAIL/CAN_TEST_TAY hoac ly do dung>", '
    '"bugs": [{{"case": "sub#<so TC>", "tieu_de": "<tom tat bug>", "precondition": "<trang thai tai khoan / app>", '
    '"buoc": "<buoc tai hien>", "expected": "<dong Expected>", "thuc_te": "<so do that>", '
    '"muc_do": "Highest|High|Medium|Low"}}], '
    '"cases": [{{"case": "sub#<so TC>", "verdict": "PASS|FAIL|BLOCKED|NEEDS_HUMAN|CAN_TEST_TAY", '
    '"thuc_te": "<tieng Viet co dau>"}}]}}\n'
    "`bugs` chi gom FAIL da chay lai xac nhan (luat muc 4 sub-check.md); khong co thi []. KHONG hoi user, KHONG log Jira."
)
PROMPT_SUB = (
    "/sub-check {package} --serial {serial} --version \"{version}\"\n\n"
    "Tra loi hoan toan bang tieng Viet. Luot nay do bot Discord goi (lenh /check-sub), khong co nguoi ngoi truoc may. "
    "Chay HET bo TC sub theo lich, may la tai khoan License Tester (khong hoi). Case thieu may / tai khoan -> CAN_TEST_TAY. "
    "Gap diem can nguoi quyet (popup khong phai giao dich test, khong tim duoc Paywall sau khi da thu het) thi dung. "
    "Truoc khi chay: co out/sub-{package}-{serial}.luot.json \"xong\": false, cap nhat trong 12 gio -> CHAY TIEP. "
    "Het luot phai cancel goi con Active. Khong commit/push. Co bug thi dung xong report truoc khi tra loi (phien khong co tool Artifact, bot dinh kem file).\n"
    + DUOI_KET_QUA
)
PROMPT_VERIFY_SUB = (
    "/sub-check {package} --serial {serial} --case {cases}\n\n"
    "Tra loi hoan toan bang tieng Viet. Luot nay do bot Discord goi de VERIFY bug dev bao da fix: chi chay dung cac TC sub "
    "tren, FAIL phai chay lai xac nhan. Khong co nguoi ngoi truoc may: gap diem can nguoi quyet thi dung. Het luot cancel goi "
    "con Active. Khong commit/push. KHONG doc/sua/log Jira - bot tu lam theo verdict.\n"
    + DUOI_KET_QUA
)
TIMEOUT_SUB = 240 * 60
TIMEOUT_VERIFY_SUB = 60 * 60
# /check tinh_nang: tab SDK rieng (rating / widget / daily checkin) trong bo TC chung. QA chon tab nao chay tab do:
# khong FO, khong checklist Next-Gen, khong check ID ads, khong chan theo plan tuan (user chot 11/11/2026).
TAB_TINH_NANG = ("rating", "widget", "daily checkin")
PROMPT_TINH_NANG = (
    "/rc-check {package} --serial {serial} {tab_arg}\n\n"
    "Tra loi hoan toan bang tieng Viet. Luot nay do bot Discord goi (lenh /check chon SDK tinh nang), khong co nguoi "
    "ngoi truoc may. CHI chay bo TC cua tab: {tabs} (bo TC chung mac dinh, moi tab mot lenh "
    "`rcr-check --tab \"<tab>\" --case all`, tab sau chay khi tab truoc xong). KHONG chay tab FO / base / delta, KHONG "
    "chay checklist Next-Gen, KHONG truyen --sdk, BO muc 3c (check ID ads). Preflight van chay nhung truyen "
    "--bo-qua-plan (lech plan tuan khong phai ly do dung). Tab khong co case nao chay duoc (app khong co key cua "
    "SDK do / tab trong) -> ghi ro trong tom_tat, khong phai loi. Moi may la may test AdMob, ad_click khong phai ly do "
    "dung. Gap diem can nguoi quyet (preflight LOI, man la) thi dung. Khong commit/push.\n"
    "Lenh nen bi cat (background time limit) -> chay tiep bang `rcr-check --tiep <file .luot.json>`, KHONG chay lai tu dau.\n"
    "Nhieu tab: dung MOT report gop bang `--gop` cac file luot (khong can may); gop khong duoc thi `link` = report tab "
    "dau, duong dan report tab con lai ghi trong `tom_tat`.\n"
    "Phien `claude -p` KHONG co tool Artifact: `link` = duong dan TUYET DOI report .html.\n"
    "Dong CUOI cung cua cau tra loi phai dung mau (mot dong JSON):\n"
    'KET_QUA: {{"trang_thai": "XONG|DUNG|LOI", "link": "<duong dan TUYET DOI file report .html>", '
    '"tom_tat": "<tieng Viet co dau, toi da 300 ky tu: so PASS/FAIL tung tab hoac ly do dung>", '
    '"bugs": [{{"case": "<tab>#<ma case>", "tieu_de": "<tom tat bug>", "precondition": "<config/user state>", '
    '"buoc": "<buoc tai hien>", "expected": "<dong Expected>", "thuc_te": "<so do that>", '
    '"muc_do": "Highest|High|Medium|Low"}}]}}\n'
    "`bugs` chi gom FAIL da ra lai theo muc 5d; khong co thi []. KHONG hoi user, KHONG tu log Jira."
)


def lenh(package: str, serial: str, cases: list[str] | None = None,
         next_gen: bool = False, sdk: str = "", sub_version: str = "",
         bo_qua_plan: bool = False, tabs: list[str] | None = None) -> tuple[list[str], str]:
    """(lenh, prompt dua vao stdin). Nhieu may cam cung luc -> luon chi dinh serial.
    `tabs`: luot /check tinh_nang - chi chay cac tab SDK rieng (gia tri trong TAB_TINH_NANG).
    Co `cases` -> prompt verify; case lay tu state nen van kiem mau truoc khi vao prompt.
    `next_gen`: bot da cai ban release vi tin build ghi next-gen -> `--next-gen` de rc-check chay checklist
    Next-Gen thay vi tu chon theo so SDK (chi 3.7.0) - AIP918 tutorial 3.7.1 bi chay nham bo TC, 29/10/2026.
    `sdk`: so tutorial trong tin build -> `--sdk`: tin build quyet nhanh + tab TC, khong theo so app in ra log
    (AIP882 4.3.0: tin build + plan tuan ghi 3.6.1 revert next-gen, app in 3.7.0 -> chay nham checklist, 30/10/2026)."""
    from .bot_verify_jira import loai_case

    if not PACKAGE_RE.match(package or ""):
        raise ValueError(f"package không hợp lệ: {package!r}")
    if not SERIAL_RE.fullmatch(serial or ""):
        raise ValueError(f"serial không hợp lệ: {serial!r}")
    if sdk and not SDK_RE.fullmatch(sdk):
        raise ValueError(f"bản SDK không hợp lệ: {sdk!r}")
    exe = shutil.which("claude") or "claude"
    cmd = [exe, "-p", "--output-format", "json"]
    audit = audit_tom_tat.repo_audit()
    if audit.is_dir():          # -p khong duyet duoc quyen ngoai cwd: thieu thi cp script workflow audit bi chan (AIP886)
        cmd += ["--add-dir", str(audit)]
    cmd += ["--allowedTools", *TOOLS]
    if tabs and not cases:                           # /check tinh_nang: chi tab SDK rieng
        sai = [t for t in tabs if t not in TAB_TINH_NANG]
        if sai:                                      # ten tab di vao prompt -> chi nhan dung danh sach co dinh
            raise ValueError(f"tab tính năng không hợp lệ: {sai!r}")
        return cmd, PROMPT_TINH_NANG.format(package=package, serial=serial, tabs=", ".join(tabs),
                                            tab_arg=" ".join(f'--tab "{t}"' for t in tabs))
    if sub_version and not cases:                    # /check-sub: ca bo TC sub
        if not VERSION_RE.fullmatch(sub_version):
            raise ValueError(f"version không hợp lệ: {sub_version!r}")
        return cmd, PROMPT_SUB.format(package=package, serial=serial, version=sub_version)
    if not cases:
        # --bo-qua-plan: QA bam "Chạy bỏ qua plan" sau luot dung vi build khac plan tuan.
        return cmd, PROMPT.format(package=package, serial=serial, next_gen=" --next-gen" if next_gen else "",
                                  sdk=(f" --sdk {sdk}" if sdk else "") + (" --bo-qua-plan" if bo_qua_plan else ""),
                                  nhac=NHAC_NEXT_GEN if next_gen else "")
    loai = {c: loai_case(c) for c in cases}
    sai = [c for c, lo in loai.items() if lo is None]
    if sai:
        raise ValueError(f"case không hợp lệ: {sai!r}")
    if len(set(loai.values())) > 1:                  # TC va checklist can hai luot khac nhau
        raise ValueError(f"không chạy lẫn case TC và checklist trong một lượt: {cases!r}")
    if set(loai.values()) == {"sub"}:
        return cmd, PROMPT_VERIFY_SUB.format(package=package, serial=serial,
                                             cases=",".join(c.split("#", 1)[1] for c in cases))
    if set(loai.values()) == {"checklist"}:
        return cmd, PROMPT_VERIFY_CHECKLIST.format(package=package, serial=serial, cases=", ".join(cases))
    return cmd, PROMPT_VERIFY.format(package=package, serial=serial, cases=",".join(cases))


def doc_ket_qua(stdout: str) -> dict:
    """Output JSON cua `claude -p` -> {trang_thai, link, tom_tat, bugs, chi_phi, phut}."""
    try:
        d = json.loads(stdout)
    except json.JSONDecodeError:
        return {"trang_thai": "LOI", "link": "", "tom_tat": (stdout or "")[-DUOI_LOG:]}
    text = d.get("result") or ""
    ra = {"trang_thai": "LOI" if d.get("is_error") else "XONG", "link": "", "tom_tat": text[-DUOI_LOG:],
          "bugs": [], "cases": []}
    m = None
    for m in KET_QUA_RE.finditer(text):
        pass                                     # lay dong KET_QUA cuoi cung
    if m:
        try:
            k = json.loads(m.group(1))
            ra.update({x: str(k.get(x, ra[x])) for x in ("trang_thai", "link", "tom_tat")})
            ra["bugs"] = doc_bugs(k.get("bugs"))
            ra["cases"] = doc_cases(k.get("cases"))
            if d.get("is_error"):              # luot loi thi KET_QUA cua model khong de len duoc
                ra["trang_thai"] = "LOI"
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


def doc_cases(cases) -> list[dict]:
    """Verdict tung case cua luot verify -> [{case, verdict, thuc_te}]; verdict la chuoi khac tap
    cho phep thi giu nguyen de bot coi la khong ket luan (khong doi trang thai Jira)."""
    if not isinstance(cases, list):
        return []
    return [{"case": str(c.get("case") or "").strip(), "verdict": str(c.get("verdict") or "").strip(),
             "thuc_te": str(c.get("thuc_te") or "").strip()[:MAX_TRUONG_BUG]}
            for c in cases if isinstance(c, dict) and str(c.get("case") or "").strip()][:MAX_BUG]


def moi_truong() -> dict[str, str]:
    """Env cua luot: tat webhook `rcr-notify` (DISCORD_NOTIFY=0) - bot da bao vao chinh tin
    cua build, webhook gui them la kenh nhan hai tin cho mot viec (user chot 27/10/2026).

    `claude -p` mac dinh chi cho viec nen 10 phut roi giet: AIP882 29/10/2026 workflow audit (~15 phut) bi giet,
    luot ket thuc chua chay case nao. Cho vo han - timeout cua luot (TIMEOUT_*) van chan tren."""
    return {**os.environ, "DISCORD_NOTIFY": "0", "CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS": "0"}


def chay(package: str, serial: str, repo: Path, timeout: int, log_dir: Path,
         cases: list[str] | None = None, next_gen: bool = False, sdk: str = "", sub_version: str = "",
         bo_qua_plan: bool = False, tabs: list[str] | None = None) -> dict:
    """Chay mot luot, log day du o `log_dir/bot-luot-<gio>.log`. Qua gio -> kill, trang_thai HET_GIO."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log = log_dir / f"bot-luot-{time.strftime('%Y%m%d-%H%M%S')}-{serial}.log"
    try:
        cmd, prompt = lenh(package, serial, cases, next_gen, sdk, sub_version, bo_qua_plan, tabs)
        # Theo serial: QA bam Dung -> bot_tien_trinh giet ca cay (claude + rcr-check + adb) -> BiDung.
        p = bot_tien_trinh.chay(cmd, serial, timeout, input=prompt, cwd=repo,
                                encoding="utf-8", errors="replace", env=moi_truong())
    except bot_tien_trinh.BiDung as exc:
        log.write_text(f"DA DUNG: {exc}", encoding="utf-8")
        raise
    except subprocess.TimeoutExpired as exc:
        log.write_text(f"HET GIO sau {timeout}s\n{exc.stdout or ''}\n{exc.stderr or ''}", encoding="utf-8")
        return {"trang_thai": "HET_GIO", "link": "", "tom_tat": f"quá {int(timeout // 60)} phút", "log": str(log)}
    log.write_text(f"exit={p.returncode}\n--- stdout\n{p.stdout}\n--- stderr\n{p.stderr}", encoding="utf-8")
    ra = doc_ket_qua(p.stdout)
    if p.returncode and ra["trang_thai"] == "XONG":
        ra["trang_thai"] = "LOI"
    ra["log"] = str(log)
    return ra
