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

import contextlib
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
# Check ID ads (rc-check.md muc 3c) trong phien `claude -p`: dung chung cho luot SDK va luot chi tinh nang.
NHAC_AUDIT = (
    "Phien `claude -p` KHONG co tool Artifact (khong nap, 09/11/2026): dung mat thoi gian thu publish. Check ID ads van "
    "lam DU buoc dung trang audit (audit-fanout muc 3: findings/notes + artifact_report_builder.py -> <pkg>-artifact.html "
    "trong out cua repo audit) - report rc-check lay tab Check ID ads tu file do; chi BO buoc publish + artifact_link. "
    "Repo audit da duoc --add-dir: chep script workflow bang `cat <repo audit>/.claude/workflows/audit-fanout.mjs > out/scratch-<ngay>/audit-fanout.mjs` (lenh `cp` tu duong dan .claude bi -p chan) roi goi Workflow. "
    "Workflow audit chay nen: CHO thong bao no xong roi moi chay case trong CUNG luot nay; KHONG ScheduleWakeup.\n"
)
# App moi lan dau chay ra hang loat do tay vi tool chua co cong thuc lai cua app (AIP921 16/11/2026: IAA 17 FAIL gia,
# rating dung o buoc gen). Do xong phai luu cong thuc vao data/ de lan sau cung app tool tu chay (user chot 16/11/2026).
# AIP892 16/11/2026: phien bot ket thuc de lai ~50 dong NEEDS_HUMAN / NOT_VERIFIABLE (dong "phai nhin mat", case dung
# giua chung) va chi bao 2 bug -> QA phai chay lai ca buoi toi. Bot phai tu cham het truoc khi ket thuc (user chot).
NHAC_CHAM_HET = (
    "TRUOC dong KET_QUA: doc lai file luot cuoi cung cua MOI bo; KHONG duoc con dong NEEDS_HUMAN / NOT_VERIFIABLE. "
    "Dong 'phai nhin mat' (design/mau/popup hien hay khong) -> mo anh `shot` trong `steps` cua CHINH case do (va log "
    "event cung luot) roi cham bang `rcr-check --cham-tay <file luot> --case <key> --dong <so> --ket PASS|FAIL "
    "--ly-do '<so do>'`; dong do tool lai hut / case noi tiep bi dut -> chay lai dung case do (`--gop`) hoac do tay "
    "tren may; FAIL phai lap >=2 lan cung dieu kien. Case can man ma may nay khong chup duoc (vd Result tren Android "
    "< 13) -> ghi ro trong tom_tat can may nao, khong bo trong. `tom_tat` ghi so dong da cham tay.\n"
)


NHAC_LUU_CONG_THUC = (
    "App tool chua co cong thuc / khuon lai (bao 'chua co cong thuc', 'khong khop khuon nao', tool dung o buoc lai): "
    "do tay xong PHAI khai cong thuc cua app vao dung file src/rcr/data/ (iaa_duong_lai.yaml, rating_gen.yaml, "
    "checkin_cong_thuc.yaml, gen_ngam_cong_thuc.yaml, fo_flow.yaml), sua code lai thi kem test, roi chay lai DUNG cac "
    "case do bang cong thuc moi de chung minh. Ghi ten file da sua vao `tom_tat` (khong commit - user commit).\n"
)
# Tab rating viet theo app gen anh/video. App KHONG gen anh/video (khong co man Result gen) -> moi case can man Result
# gen anh / video bo qua: khong test, khong lay man khac thay, khong vao report (AIP921 fitness 16/11/2026, user chot).
NHAC_RATING_KHONG_GEN = (
    "Tab rating: app KHONG phai app gen anh/video (khong co man Result gen anh/video) -> moi case / dong can man Result "
    "gen anh, gen video (Result — gen anh/video, chon sao / bam X / Feedback / 1-5 sao tai Result...) BO QUA: KHONG "
    "test, KHONG lay man khac (vd ket qua scan) thay vao; ghi `rcr-check --cham-tay <file luot> --case <ma> --dong "
    "<cac dong> --ket KHONG_AP_DUNG --ly-do \"app khong gen anh/video, khong co man Result\"` - report tu bo han "
    "case / dong do. Chi test vi tri app co (Home, Exit click, App Shortcut...).\n"
    "Nut 'Rate on Google Play' mo trang app tren store CO SAN cua may (vd vivo App Store khi may chua cai Google Play) "
    "la DUNG, khong phai bug (user chot 16/11/2026); BACK trong store ben thu ba do store xu ly -> KHONG_AP_DUNG.\n"
)
# Dong hien thi ads: da request + load ok dung unit ma khong show -> DAT (user chot 17/11/2026, AIP935 IAA-02-01).
NHAC_LOAD_KHONG_SHOW = (
    "Dong ads 'hien thi / show / khoang cach giua cac ad': ad DA request + load ok dung unit ma khong show -> PASS "
    "(ghi so request/load), KHONG FAIL, khong dua vao bugs. Chi FAIL khi khong request, request sai unit, hoac show sai "
    "cho / sai luc.\n"
    "Dong reward 'xem chua het / thoat giua chung thi khong thuong': ad reward test khong dong som duoc -> thoat bang "
    "force-stop app luc ad dang chay (~2-3s) roi mo lai, xem bo dem + event ad_reward; KHONG ghi BLOCKED. Luong "
    "Uninstall: man Thank You chi hien ~3s sau khi dong inter 'Go cai dat' roi moi mo Cai dat - theo doi man tung giay "
    "sau khi dong inter, khong ket luan 'khong co man Thank You' (user chot 17/11/2026, AIP935).\n"
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
    "Khong commit/push.\n{tinh_nang}"
    "Truoc khi chay bo TC: trong out/ co file *.luot.json cung package + serial nay, \"xong\": false, "
    "`cap_nhat` trong 12 gio -> luot truoc bi tat giua chung (may tinh khoi dong lai): "
    "CHAY TIEP bang `rcr-check --tiep <file>`, KHONG chay lai tu dau cac case da co ket qua.\n"
    "Lenh nen (run_in_background) bi Claude Code cat o moc thoi gian toi da (status killed, 'background time limit'): "
    "luot CHUA xong - chay tiep ngay bang `rcr-check --tiep <file .luot.json cua luot do>` (lai chay nen), lap lai moi "
    "lan bi cat toi khi file luot \"xong\": true; KHONG chay lai tu dau, KHONG bao xong / dung khi con case chua chay.\n"
    "Thu tu: chay HET bo case truoc (toi \"xong\": true), roi moi chay lai case chua PASS - toi da 2 vong `--gop`; sau "
    "vong 2 case nao chua PASS thi do tay / doc log tu cham, khong mo vong 3. Sua tool giua luot: KHONG dung luot dang "
    "chay (tru khi tool dang kep lap cung mot buoc > 5 phut); de luot chay het roi chay lai DUNG cac case bi loi tool "
    "do trong vong `--gop` ke tiep. Cham xong bo TC thi sang checklist Next-Gen ngay (SDK 3.7.x).\n"
    "Workflow audit chay nen: CHO thong bao no xong roi lam tiep trong CUNG luot nay; KHONG ScheduleWakeup, KHONG "
    "ket thuc cau tra loi khi con viec nen hay chua chay checklist/case. KHONG tu viet vong lap sleep doc "
    "journal.jsonl / file output de cho: thong bao xong chi toi khi lenh Bash dang chay ket thuc, vong lap do giu may "
    "dung im toi het han (AIP872 04/11/2026 mat ~7 phut). Trong luc cho thi lam viec khong can may (doc TC, preflight).\n"
    + NHAC_AUDIT + NHAC_LUU_CONG_THUC + NHAC_CHAM_HET + NHAC_RATING_KHONG_GEN + NHAC_LOAD_KHONG_SHOW +
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
# Verify khong gioi han thoi gian (user chot 17/11/2026): luot IAA AIP892 bi cat o 40 phut giua luc do tay,
# 5 bug khong ra ket luan. Luot treo thi QA bam Dung.
TIMEOUT_VERIFY = KHONG_GIOI_HAN
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
TIMEOUT_VERIFY_CHECKLIST = KHONG_GIOI_HAN
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
TIMEOUT_VERIFY_SUB = KHONG_GIOI_HAN
# /check tinh_nang: tab SDK rieng (rating / widget / daily checkin) trong bo TC chung. QA chon tab nao chay tab do:
# khong FO, khong checklist Next-Gen, khong chan theo plan tuan (user chot 11/11/2026). Van check ID ads (audit-fanout)
# truoc bo dau tien nhu moi luot chay app (user chot 16/11/2026, bo luat 11/11 "khong check ID ads").
TAB_TINH_NANG = ("rating", "widget", "daily checkin")
# Bo TC tinh nang KHONG nam trong sheet chung: rcr-check tu dung tu sheet goc moi lenh (`--tc <nguon>`):
# iaa = muc "3. ID ads inapp" cua tab app o sheet KT, gen-ngam = sheet checklist gen ngam (user chot 12/11/2026).
NGUON_TINH_NANG = ("iaa", "gen-ngam")
PROMPT_TINH_NANG = (
    "/rc-check {package} --serial {serial} {tab_arg}\n\n"
    "Tra loi hoan toan bang tieng Viet. Luot nay do bot Discord goi (lenh /check chon SDK tinh nang), khong co nguoi "
    "ngoi truoc may. CHI chay bo TC: {tabs} (moi bo mot lenh: {lenh_bo}; bo sau chay khi bo truoc xong). "
    "Bo `--tc iaa` / `--tc gen-ngam` rcr-check tu dung tu sheet goc; dong tool khong tu cham duoc thi cham tay theo "
    "muc 5b, dieu kien khong tao duoc (nho dev gia lap...) thi BLOCKED kem ly do. KHONG chay tab FO / base / delta, KHONG "
    "chay checklist Next-Gen, KHONG truyen --sdk. Sau preflight, TRUOC bo dau tien phai lam muc 3c (check ID ads "
    "bang audit-fanout) nhu moi luot chay app; ID ads lech sheet KHONG phai ly do dung: ghi vi tri lech vao tom_tat "
    "roi chay tiep, dong ads vi tri lech cham theo unit that trong log. Preflight van chay nhung truyen "
    "--bo-qua-plan (lech plan tuan khong phai ly do dung). Tab khong co case nao chay duoc (app khong co key cua "
    "SDK do / tab trong) -> ghi ro trong tom_tat, khong phai loi. Moi may la may test AdMob, ad_click khong phai ly do "
    "dung. Gap diem can nguoi quyet (preflight LOI, man la) thi dung. Khong commit/push.\n"
    "Lenh nen bi cat (background time limit) -> chay tiep bang `rcr-check --tiep <file .luot.json>`, KHONG chay lai tu dau.\n"
    "{policy}"
    "Nhieu tab: dung MOT report gop bang `--gop` cac file luot (khong can may); gop khong duoc thi `link` = report tab "
    "dau, duong dan report tab con lai ghi trong `tom_tat`.\n"
    + NHAC_AUDIT + NHAC_LUU_CONG_THUC + NHAC_CHAM_HET + NHAC_RATING_KHONG_GEN + NHAC_LOAD_KHONG_SHOW +
    "`link` = duong dan TUYET DOI report .html.\n"
    "Dong CUOI cung cua cau tra loi phai dung mau (mot dong JSON):\n"
    'KET_QUA: {{"trang_thai": "XONG|DUNG|LOI", "link": "<duong dan TUYET DOI file report .html>", '
    '"tom_tat": "<tieng Viet co dau, toi da 300 ky tu: so PASS/FAIL tung tab hoac ly do dung>", '
    '"bugs": [{{"case": "<tab>#<ma case>", "tieu_de": "<tom tat bug>", "precondition": "<config/user state>", '
    '"buoc": "<buoc tai hien>", "expected": "<dong Expected>", "thuc_te": "<so do that>", '
    '"muc_do": "Highest|High|Medium|Low"}}]}}\n'
    "`bugs` chi gom FAIL da ra lai theo muc 5d; khong co thi []. KHONG hoi user, KHONG tu log Jira."
)


# Tin build ghi ca SDK lan tinh nang ("sdk 3.5.4 - Apply IAA - SDK Widget - ..."): check het tinh nang da dong goi,
# khong chi SDK - chay lan luot trong CUNG luot, gop mot report (user chot 14/11/2026).
NHAC_TINH_NANG = (
    "Tin build con ghi tinh nang: {tabs}. Xong HET phan SDK (bo TC + vong chay lai; checklist Next-Gen neu co) thi "
    "chay LAN LUOT tung bo tinh nang trong CUNG luot nay, moi bo mot lenh: {lenh_bo} (bo sau chay khi bo truoc "
    "\"xong\": true). Bo tinh nang KHONG check ID ads lai, KHONG truyen --sdk, moi case tool tu lai vao Home. Dong tool "
    "khong tu cham duoc thi cham tay theo muc 5b; dieu kien khong tao duoc thi BLOCKED kem ly do; bo khong co case chay "
    "duoc (app khong co key / sheet trong) thi ghi ro trong tom_tat, khong phai loi. Bi cat giua chung thi `--tiep`.\n"
    "Cuoi luot dung MOT report gop: `rcr-check --package {package} --gop <file luot bo TC SDK> --gop <file luot tung bo "
    "tinh nang>...` (khong can may) -> `link` = report gop. Nhanh chi checklist Next-Gen (khong co file luot bo TC): gop "
    "cac bo tinh nang, `link` = report gop do, link report checklist ghi trong `tom_tat`. Gop khong duoc thi `link` = "
    "report bo TC SDK, duong dan report con lai ghi trong `tom_tat`. `tom_tat` ghi so PASS/FAIL tung phan (SDK, tung "
    "tinh nang); `bugs` gom ca SDK lan tinh nang, case tinh nang ghi `<bo>#<ma case>`.\n"
)


# Luot co bo IAA bat buoc check them policy ADS (user chot 16/11/2026; ngoai le cua luat 11/11 "policy tach rieng").
# Chi ads, khong sub: `--chi-ads` -> khong mua sub, bo rule tab Sub_VN. Van chay SAU CUNG vi policy pm clear app.
NHAC_POLICY = (
    "Luot nay co bo IAA -> BAT BUOC check policy ADS (khong check sub, khong mua sub) lam buoc CUOI: xong HET cac bo "
    "(ke ca vong chay lai, do tay, --gop) va da tra config ve nguyen trang thi doc TOAN BO "
    "`<repo audit>/.claude/commands/policy-check.md` va lam dung no voi `{package} --serial {serial} --chi-ads` (cung may). Moi rule phai chot PASS/FAIL (N/A chi khi app khong co thu "
    "rule noi toi, ghi can cu); con BLOCKED thi evidence_followup roi tu lai may. Policy khong chan ket qua bo TC. "
    "`tom_tat` them so PASS/FAIL policy + duong dan TUYET DOI report policy; moi rule FAIL them vao `bugs` voi "
    "`case` = `policy#<ma rule>`. Policy loi / khong thay repo audit -> ghi ly do vao `tom_tat`, khong phai loi luot.\n"
)


def _nhac_policy(package: str, serial: str, tabs: list[str] | None) -> str:
    """Nhac chay policy khi danh sach bo co IAA, khong thi chuoi rong."""
    return NHAC_POLICY.format(package=package, serial=serial) if tabs and "iaa" in tabs else ""


def _lenh_tinh_nang(tabs: list[str]) -> tuple[list[str], str]:
    """Tham so rcr-check cua tung bo tinh nang -> (['--tc iaa', '--tab "rating"'], chuoi lenh cho prompt).
    Ten bo di vao prompt -> chi nhan dung danh sach co dinh."""
    sai = [t for t in tabs if t not in TAB_TINH_NANG + NGUON_TINH_NANG]
    if sai:
        raise ValueError(f"tab tính năng không hợp lệ: {sai!r}")
    co = [f"--tc {t}" if t in NGUON_TINH_NANG else f'--tab "{t}"' for t in tabs]
    # Gen ngam da dong goi (16/11/2026): tu lai + tu cham theo nhom config, khong lai tung case qua rcr-check.
    # IAA: dung khung bang --khung (vai giay, khong dung may) roi rcr-iaa tu lai theo 4 bien the - `--no-actions` van
    # dat config + clear data + lai FO tung case (AIP892 16/11: 20+ phut chi de dung khung).
    lenh = {"--tc gen-ngam": "`rcr-gen-ngam chay --package <pkg> --serial <serial>`",
            "--tc iaa": "`rcr-check --tc iaa --case all --khung` rồi `rcr-iaa chay --luot <file .luot.json vừa dựng>`"}
    return co, ", ".join(lenh.get(c) or f"`rcr-check {c} --case all`" for c in co)


def lenh(package: str, serial: str, cases: list[str] | None = None,
         next_gen: bool = False, sdk: str = "", sub_version: str = "",
         bo_qua_plan: bool = False, tabs: list[str] | None = None,
         them_tinh_nang: list[str] | None = None) -> tuple[list[str], str]:
    """(lenh, prompt dua vao stdin). Nhieu may cam cung luc -> luon chi dinh serial.
    `tabs`: luot /check tinh_nang - chi chay cac tab SDK rieng (TAB_TINH_NANG) / bo dung tu sheet goc (NGUON_TINH_NANG).
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
        co, lenh_bo = _lenh_tinh_nang(tabs)
        return cmd, PROMPT_TINH_NANG.format(package=package, serial=serial, tabs=", ".join(tabs),
                                            tab_arg=" ".join(co), lenh_bo=lenh_bo,
                                            policy=_nhac_policy(package, serial, tabs))
    if sub_version and not cases:                    # /check-sub: ca bo TC sub
        if not VERSION_RE.fullmatch(sub_version):
            raise ValueError(f"version không hợp lệ: {sub_version!r}")
        return cmd, PROMPT_SUB.format(package=package, serial=serial, version=sub_version)
    if not cases:
        # --bo-qua-plan: QA bam "Chạy bỏ qua plan" sau luot dung vi build khac plan tuan.
        tn = ""
        if them_tinh_nang:
            tn = NHAC_TINH_NANG.format(package=package, tabs=", ".join(them_tinh_nang),
                                       lenh_bo=_lenh_tinh_nang(them_tinh_nang)[1])
            tn += _nhac_policy(package, serial, them_tinh_nang)
        return cmd, PROMPT.format(package=package, serial=serial, next_gen=" --next-gen" if next_gen else "",
                                  sdk=(f" --sdk {sdk}" if sdk else "") + (" --bo-qua-plan" if bo_qua_plan else ""),
                                  nhac=NHAC_NEXT_GEN if next_gen else "", tinh_nang=tn)
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


def thu_muc_luot(repo: Path, package: str, serial: str) -> Path:
    """Thu muc rieng cua MOT luot bot: out/scratch-<yymmdd>/<package>-<serial>-<hhmmss>/. Dem 16/11/2026 nhieu luot
    cung ghi /tmp/rc, out/manual, out/scratch-<ngay> -> log lan nhau (uni.log cua lan do nao, m1.log cua may nao)."""
    d = Path(repo) / "out" / f"scratch-{time.strftime('%y%m%d')}" / f"{package}-{serial}-{time.strftime('%H%M%S')}"
    d.mkdir(parents=True, exist_ok=True)
    return d


LUOT_DO_GIO = 12 * 3600


def luot_do(repo: Path, package: str, serial: str, bay_gio: float | None = None) -> list[Path]:
    """File luot chua xong (`xong`: false) cua package + may nay trong LUOT_DO_GIO gan day - luot bi cat giua chung
    (bot restart / Dung / het gio)."""
    now = time.time() if bay_gio is None else bay_gio
    ra = []
    for f in sorted((Path(repo) / "out").glob(f"*{package}*{serial}*.luot.json"), key=lambda x: -x.stat().st_mtime):
        if now - f.stat().st_mtime > LUOT_DO_GIO:
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not d.get("xong") and d.get("records"):
            ra.append(f)
    return ra[:6]


def nhac_luot_do(repo: Path, package: str, serial: str) -> str:
    """Luot truoc bi cat giua chung -> chay TIEP bang --tiep thay vi chay lai tu dau (16/11/2026: restart bot cat luot
    AIP893, phien moi chay lai ca 5 tab ~3 tieng)."""
    ds = luot_do(repo, package, serial)
    if not ds:
        return ""
    return ("Luot truoc cua app nay tren may nay bi cat giua chung, con file luot CHUA xong: "
            + ", ".join(f"`{f}`" for f in ds) + ". Bo nao co file do (dung tab / bo TC, sheet khong doi) thi chay "
            "TIEP bang `rcr-check --tiep <file>` (rcr-iaa / rcr-gen-ngam: `--luot <file> --tiep` neu co), KHONG chay "
            "lai tu dau; case da co ket qua giu nguyen. Truong `code` trong file ghi commit da chay case cu.\n")


def nhac_thu_muc_luot(d: Path) -> str:
    return (f"\nThu muc rieng cua luot nay: `{d}` (env RCR_THU_MUC_LUOT). MOI file tam / log logcat / anh do tay / "
            "script phu cua luot ghi vao day - KHONG dung /tmp/rc, out/manual hay out/scratch-<ngay> chung (luot khac "
            "dung chung, log lan nhau).\n")


@contextlib.contextmanager
def _khoa_job(repo: Path, serial: str):
    """Giu khoa may cho ca luot bot -> env cho tien trinh con; khoa dang bi giu thi {} (lenh con tu khoa nhu cu)."""
    from . import bot_hang_doi
    cm = bot_hang_doi.giu_may(bot_hang_doi.khoa_may(Path(repo) / "out", serial))
    try:
        cm.__enter__()
    except BlockingIOError:
        yield {}
        return
    try:
        yield {bot_hang_doi.ENV_CHA_GIU: serial}
    finally:
        cm.__exit__(None, None, None)


def chay(package: str, serial: str, repo: Path, timeout: int, log_dir: Path,
         cases: list[str] | None = None, next_gen: bool = False, sdk: str = "", sub_version: str = "",
         bo_qua_plan: bool = False, tabs: list[str] | None = None,
         them_tinh_nang: list[str] | None = None) -> dict:
    """Chay mot luot, log day du o `log_dir/bot-luot-<gio>.log`. Qua gio -> kill, trang_thai HET_GIO.
    `them_tinh_nang`: bo tinh nang chay sau phan SDK trong cung luot (tin build ghi ca hai)."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log = log_dir / f"bot-luot-{time.strftime('%Y%m%d-%H%M%S')}-{serial}.log"
    try:
        cmd, prompt = lenh(package, serial, cases, next_gen, sdk, sub_version, bo_qua_plan, tabs, them_tinh_nang)
        thu_muc = thu_muc_luot(repo, package, serial)
        prompt += nhac_thu_muc_luot(thu_muc) + nhac_luot_do(repo, package, serial)
        # Theo serial: QA bam Dung -> bot_tien_trinh giet ca cay (claude + rcr-check + adb) -> BiDung.
        # Giu khoa may CA job (khong chi tung lenh rcr-check): giua hai lenh may khong con trong nhu ranh cho luot khac
        # chen vao. Lenh con biet cha da giu qua env RCR_GIU_MAY. May dang bi luot tay giu -> chay nhu cu (khoa tung lenh).
        with _khoa_job(repo, serial) as env_khoa:
            p = bot_tien_trinh.chay(cmd, serial, timeout, input=prompt, cwd=repo, encoding="utf-8", errors="replace",
                                    env=moi_truong() | env_khoa | {"RCR_THU_MUC_LUOT": str(thu_muc)})
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
