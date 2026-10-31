"""Lai app qua tung buoc Action cua case, sau khi config da duoc dat.

Moi buoc: chup UI -> dich thanh thao tac -> lam -> ghi lai. Dung NGAY khi gap
buoc khong dich duoc: di tiep voi man hinh sai thi moi thu sau do deu vo nghia.

Buoc noi "di toi mot man hinh" (`GoTo`) khong tu bam mo: giao cho `fo_flow`
lai theo luat o `data/fo_flow.yaml`. Truoc day moi buoc dang nay deu la
NEEDS_HUMAN, trong khi bo luat da biet duong di - case dung lai o buoc 2 du
tool thua suc di tiep.

Buoc VUOT khong bi chan khi quang cao che man: vuot khong bam trung thu gi nen
khong the bam nham vao quang cao, va dung cai dang duoc test (icon SWIPE thay
cho vung ad) lai nam o man co quang cao.

HAI CHO TU CHOI THAO TAC, co y:
  - quang cao dang che man hinh -> khong tu tim nut X giua cac buoc (chi sau buoc
    cuoi moi dong, va chi bam dung nut dong cua ad - `fo_flow.dong_ad_dang_che`). Nut dong quang cao nho,
    lech vai pixel la bam vao chinh quang cao (mo trinh duyet, co khi mua hang).
  - man hinh khong phai cua app dich (app khac bung len) -> dung, bao nguoi.

Dump sau moi buoc duoc giu lai de phase 5 cham - khong phai chup lai lan nua.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time

from . import (act_compound, act_exec, act_resolver, chup_man, device_app, drive_probes, fo_flow,
               fo_screens,
               fo_steps, mau_chu, quan_sat, screencap, tag_logcat, ui_dump, ui_names)

log = logging.getLogger(__name__)

AD_HINTS = ("adactivity", "com.google.android.gms.ads")
# App con dung truoc / o LFO: buoc "Chon <ngon ngu>" phai lai qua LFO (fo_flow chon dung ngon ngu cua case).
CHUA_QUA_LFO = ("Splash", "Language", "AdActivity")


def _noop(_msg: str) -> None:
    pass


def _di_qua(man_can: str | None, target: str) -> bool:
    """Buoc nay lai QUA man ma case can quan sat?

    `man_can` None nghia la khong biet case noi ve man nao -> di het nhu TC bao.
    """
    # "!OnboardingActivity" (Hoan thanh OB4) khong co trong THU_TU -> thu_tu xep cuoi; khong duoc coi la "di qua"
    # roi bo buoc (AIP886 R01-05: bo "Hoan thanh OB4" vi key case o OB3, man Question khong bao gio toi).
    return man_can is not None and not target.startswith("!") and fo_flow.thu_tu(target) > fo_flow.thu_tu(man_can)


CON_TRONG_LUONG = ("Splash", "Language", "OnboardingActivity")
_NGOAC_RE = re.compile(r"[\"“”'‘’]([^\"“”'‘’]{1,60})[\"“”'‘’]")


async def _lai_toi_chu(client, serial: str, package: str, step: str, mau_can, log_fn) -> dict | None:
    """Lai luong FO toi khi chu trong ngoac cua buoc hien, hoac toi man Question co o lua chon (nut cta chi hien
    sau khi chon). -> {xml, activity, chup} hoac None neu khong toi."""
    chu = _NGOAC_RE.search(step).group(1).strip().casefold()
    o = set(ui_names.chon_item_ids())

    def thay(nodes) -> bool:
        return any((n.text or "").strip().casefold() == chu for n in nodes) or any(n.resource_id in o for n in nodes)

    chup, da_chup = chup_man.tao(client, serial, package, mau_can)
    walk = await fo_flow.walk_to(client, serial, package, "MainActivity", log_fn=log_fn, chup=chup, dung_khi=thay)
    if not walk["reached"]:
        return None
    _, activity = await device_app.focus(client, serial)
    return {"xml": await ui_dump.dump(client, serial), "activity": activity, "chup": da_chup}


def _da_qua_man(activity: str, xml: str, target: str) -> bool:
    """App dang o man nam SAU `target` trong luong FO? Khong biet chac (OB3 khong co cham trang, khong co dump)
    -> False, de buoc van lai nhu cu."""
    if not activity or target.startswith("!"):
        return False
    if "OnboardingActivity" in activity:
        trang = fo_steps.onboarding_page(ui_dump.app_nodes(ui_dump.parse_dump(xml))) if xml else 0
        if not trang:
            # OB3 native full khong co cham trang: van chac la da qua LFO va it nhat o OB1 (R01-03 "LFO2.").
            return fo_flow.thu_tu(target) <= fo_flow.thu_tu("OnboardingActivity#1")
        dang_o = f"OnboardingActivity#{trang}"
    else:
        # Chi man CHAC CHAN thuoc luong FO: MainActivity co app la man mo dau, khong suy "da qua" tu ten do.
        dang_o = next((t for t in ("QuestionActivity", "BillingActivity") if t in activity), "")
        if not dang_o:
            return False
    return fo_flow.thu_tu(dang_o) > fo_flow.thu_tu(target)


def blocking_screen(package: str, pkg: str, activity: str) -> str:
    """Man hinh hien tai co can nguoi xu ly truoc khong -> ly do, "" neu on."""
    if any(h in activity.casefold() for h in AD_HINTS):
        return (
            f"quang cao dang che man hinh ({activity}) - tool khong tu bam nut dong "
            "(bam lech la vao chinh quang cao). Dong quang cao roi chay lai"
        )
    if pkg and pkg != package:
        return f"man hinh dang o {pkg}, khong phai {package}"
    if not pkg:
        return "khong doc duoc man hinh dang hien (may khoa?)"
    return ""


# Nhin tiep bay nhieu giay sau cu bam X tool tu lam: du thay trang roi di + man ke.
SAU_TU_BAM_X = 6.0
# Cho nut dong cua inter con che sau buoc cuoi (nut bam duoc sau ~5s, nhu luat AdActivity).
CHO_NUT_DONG_AD = 25.0   # doi quang cao chay het dem nguoc (fo_flow.TRAN_DEM_NGUOC 20s) roi moi dong


async def drive(client, serial: str, package: str, steps, log_fn=_noop,
                man_can: str | None = None, thu_vuot: bool = False,
                da_toi: str | None = None, do_anim: bool = False,
                man_dau: str = "", cua_so: float = act_exec.CUA_SO_MAC_DINH,
                ghi_khung: bool = False, thu_bam_x: bool = False, mau_can=(), man_xa: str = "") -> dict:
    """Chay lan luot cac buoc. Tra nhat ky tung buoc + dump de phase 5 cham.

    Man hinh bi che CHI chan buoc phai cham vao man hinh. Buoc quan sat va buoc
    cho van di tiep: case ads cham bang log request/load, va inter thuong de len
    truoc khi kip nhin thay banner - dung o day la bao hong mot case dang chay dung.

    Moc "Tai t0+Ns": t0 la luc vua toi man cua case (dau luot lai, hoac sau
    buoc di toi man gan nhat) - CHUA phai luc ad show, viec do can do log rieng.

    Toi uu thoi gian (do 2026-10-06, 1 case OB2 = 112s, 35s nam o 2 buoc Action):
      - `do_anim`: chi chup 10 khung do animation khi case co dong Expected hoi
        animation. Truoc day man nao co lottie la chup, moi buoc ~10s.
      - man CHUA DOI ke tu lan chup truoc (buoc truoc khong thao tac gi, hoac
        `man_dau` = dump vua chup sau buoc lai theo precondition) -> dung lai
        dump do, khong dump + chup lai (~5s).
    """
    done: list[dict] = []
    blocked_steps: list[int] = []
    tag_log: dict[str, list[str]] = {}       # buoc "Xem logcat tag ..." (tag_logcat)
    ctx, dump_cu = act_exec.ctx_moi(package, cua_so, ghi_khung), ""
    t0 = time.monotonic()
    man_cu = man_dau          # dump con dung duoc vi man chua doi ("" = phai chup moi)
    da_do = None              # dump cua man da do animation (khong do lai cung mot man)
    for index, raw in enumerate(steps, 1):
        moc = act_compound.moc_t0(raw)
        step = moc[1] if moc else raw
        if moc:
            await asyncio.sleep(max(0.0, t0 + moc[0] - time.monotonic()))
        pkg, activity = await device_app.focus(client, serial)
        blocked = blocking_screen(package, pkg, activity)
        action = act_resolver.resolve(step, [])
        nhin_ngay = isinstance(action, act_resolver.Watch) or (
            isinstance(action, act_resolver.GoTo) and action.target == da_toi)
        if nhin_ngay or (moc and not isinstance(action, (act_resolver.Tap, act_resolver.NeedsHuman))):
            # Buoc co moc gio / buoc theo doi, KHONG can cay node: lam ngay,
            # khong dump/chup truoc (mat 2-5s). Timer OB3 3s ma chup truoc thi
            # trang da tu chuyen truoc khi kip nhin (do 2026-10-06, OB3X-013).
            record = {"n": index, "step": raw, "action": action.summary, "activity": activity}
        else:
            dung_lai = bool(man_cu) and not moc
            if dung_lai:
                # Anh da co o buoc truoc - khong nhan doi anh trong report.
                xml, shot = man_cu, {"thumb": "", "warning": ""}
            else:
                xml = await ui_dump.dump(client, serial)
                # Chup cung luc voi dump -> anh va cay node ta CUNG mot man hinh.
                shot = await screencap.capture(client, serial, giu_png=bool(mau_can))
            nodes = ui_dump.app_nodes(ui_dump.parse_dump(xml), package)
            # Dung lai dump van PHAI do animation neu man nay chua do lan nao:
            # bo do theo dump la dong "icon la animation lap" roi sang luat khac
            # ma khong ai hay (do 2026-10-06, case OB2-001).
            can_do = do_anim and not moc and not (dung_lai and da_do == xml)
            anim = await drive_probes._do_animation(client, serial, nodes) if can_do else {}
            if can_do:
                da_do = xml
            trang = fo_steps.onboarding_page(nodes)
            if trang:                      # doc duoc thi lay lam moc, bo so dem cu
                ctx["trang_cu"], ctx["vuot_sau"] = trang, 0
            dump_cu = xml
            action = act_resolver.resolve(step, nodes)
            if (isinstance(action, act_resolver.NeedsHuman) and not blocked
                    and _NGOAC_RE.search(step) and any(m in activity for m in CON_TRONG_LUONG)):
                # "Bam 'FR - Go'" ma app con o splash / LFO / OB: lai tiep toi khi chu do (hoac o lua chon cua man
                # Question) hien roi moi bam (AIP886 R01-06).
                lai = await _lai_toi_chu(client, serial, package, step, mau_can, log_fn)
                if lai:
                    done.extend(chup_man.danh_so(lai["chup"], len(done) + 1))
                    xml, activity = lai["xml"], lai["activity"]
                    nodes = ui_dump.app_nodes(ui_dump.parse_dump(xml), package)
                    dump_cu = xml
                    action = act_resolver.resolve(step, nodes)
            record = {"n": index, "step": raw, "action": action.summary,
                      "activity": activity, "dump": xml,
                      "shot": shot["thumb"], "shot_warning": shot["warning"]}
            if anim:
                record["anim"] = anim
            if mau_can and shot.get("png") and not blocked:
                # Do mau chu NGAY tren anh goc cung luc voi dump (dong "dung mau #HEX").
                record["mau"] = await mau_chu.do_nhieu_khung(client, serial, package, activity, nodes,
                                                             list(mau_can), shot["png"])
        if moc:
            record["moc"] = {"t0_cong": moc[0], "lam_luc": round(time.monotonic() - t0, 1),
                             "ghi_chu": "t0 = lúc vừa tới màn, chưa đo lúc ad show"}
        if blocked:
            # Ghi lai de phase 5 biet dump nay KHONG phai UI cua app.
            record["screen_blocked"] = blocked
            blocked_steps.append(index)

        if isinstance(action, (act_resolver.Tap, act_resolver.TapId)) and blocked:
            record["action"] = {"kind": "needs_human", "reason": blocked}
            log_fn(f"    buoc {index}: DUNG - {blocked}")
            done.append(record)
            return {"steps": done, "status": "NEEDS_HUMAN", "stopped_at": index,
                    "blocked_steps": blocked_steps, "khung": ctx["khung"],
                    "thao_tac": ctx["thao_tac"]}

        # Buoc khong thao tac gi -> man buoc sau van y nhu dump nay.
        man_cu = record.get("dump", "") if isinstance(action, act_resolver.NoOp) else ""
        log_fn(f"    buoc {index}: {raw!r} -> {action.summary['kind']}"
               + (f" (man hinh bi che: {activity})" if blocked else ""))
        done.append(record)

        if isinstance(action, act_resolver.GoTo) and action.target == da_toi:
            # Buoc lai theo Precondition da dua app toi DUNG man nay roi. Lai lai
            # tu cho dang dung la hong: OB3 khong co cham chi trang, lan lai thu
            # hai khong suy duoc trang va vuot tiep toi Home (do 2026-10-02).
            record["action"] = {"kind": "noop", "target": action.target,
                                "reason": f"đã ở {action.target} từ bước lái theo precondition"}
            da_toi = None
            man_cu = record.get("dump", "")
            t0 = time.monotonic()
            if ctx["ghi_khung"] and thu_bam_x:
                # Dong Expected "bam X hoat dong / chuyen man ngay" ma TC khong co
                # buoc bam: tool tu bam X MOT lan ngay khi no hien (giong dong "user
                # vuot sang man ke" duoc cham bang mot cu vuot that), roi nhin tiep.
                thu_bam_x = False
                tam = await quan_sat.cho_nut_x(client, serial, package,
                                               max(action.cho, ctx["cua_so"]), ctx["khung"])
                if tam:
                    await act_exec._tap_ghi_luc(client, serial, tam, act_resolver.TapId(
                        quan_sat.VAI_NUT_X, "tool tự bấm X để chấm dòng 'bấm X'"), record, ctx)
                    record["tu_bam_x"] = True
                    await quan_sat.theo_doi(client, serial, package, SAU_TU_BAM_X, ctx["khung"])
            elif ctx["ghi_khung"]:
                # "Vao OB3, quan sat ..." ma app da o OB3: nhin lien tuc ngay tu
                # luc nay, khong ngu - dong Expected ve nut X can khung tren OB3.
                await quan_sat.theo_doi(client, serial, package, max(action.cho, ctx["cua_so"]),
                                        ctx["khung"])
            elif action.cho:
                await asyncio.sleep(action.cho)
            continue
        if isinstance(action, act_resolver.ChonNgonNgu):
            # Ngon ngu da dat cho ca case (fo_ngon_ngu.CHON): moi lan qua LFO fo_flow deu chon no.
            if not any(m in activity for m in CHUA_QUA_LFO):
                record["action"] = {"kind": "noop", "language": action.ten,
                                    "reason": f"đã chọn {action.ten} khi lái qua LFO"}
                man_cu = record.get("dump", "")
                continue
            dich = (man_can if man_can and fo_flow.thu_tu(man_can) > fo_flow.thu_tu("Language")
                    else "OnboardingActivity#1")
            action = act_resolver.GoTo(dich, action.reason)
        if (isinstance(action, act_resolver.GoTo) and action.reason.startswith(act_resolver.DI_QUA)
                and man_xa and fo_flow.thu_tu(man_xa) > fo_flow.thu_tu(action.target)):
            # "Di tiep qua OB2" ma Expected con noi OB4: lai toi OB4, chup moi trang di qua.
            action = act_resolver.GoTo(man_xa, action.reason)
        if isinstance(action, act_resolver.GoTo) and _da_qua_man(activity, record.get("dump", ""), action.target):
            # "LFO2.", "Bam tick.", "OB3." sau khi da lai toi OB4: man do o phia sau roi - lai tiep la di toi Home
            # roi bao "khong toi duoc" (AIP886 R01-03 31/10/2026).
            record["action"] = {"kind": "noop", "target": action.target,
                                "reason": f"đã qua {action.target} (đang ở {activity.split('.')[-1]})"}
            man_cu = record.get("dump", "")
            continue
        if (isinstance(action, act_resolver.GoTo) and _di_qua(man_can, action.target)
                and not action.reason.startswith(act_resolver.DI_QUA)):
            # "Di qua OB1 → OB4" la buoc QUAN SAT moi trang (dong "khong dung khoi 'en'" can thay het OB1-OB4):
            # khong bo vi key case nam o OB3 (AIP886 R03-03 31/10/2026 - chi thay OB1 ma ra PASS).
            # Buoc TC bao di tiep, nhung key cua case nam o man truoc do roi:
            # doc log o day la du. 16 thao tac de toi Home ton ~90 giay va
            # khong them mot so do nao cho case nay.
            record["action"] = {"kind": "noop", "target": action.target,
                                "reason": f"key của case nằm ở {man_can or 'splash'}, "
                                          f"không cần đi tiếp tới {action.target}"}
            log_fn(f"    buoc {index}: dung o {man_can or 'splash'}, bo buoc di toi {action.target}")
            man_cu = record.get("dump", "")
            continue
        if isinstance(action, act_resolver.GoTo):
            # Quang cao dang che van lai duoc: `fo_flow` co luat rieng cho
            # AdActivity (cho ad chay xong roi dong), khong phai tu mo nut X.
            chup, da_chup = chup_man.tao(client, serial, package, mau_can)
            walk = await fo_flow.walk_to(client, serial, package, action.target, log_fn=log_fn,
                                         qua_lfo_nhanh=fo_screens.can_qua_lfo_nhanh(step), chup=chup)
            done.extend(chup_man.danh_so(da_chup, len(done) + 1))
            if not walk["reached"]:
                # Lai hut thi phai noi ket o dau: "khong dich duoc buoc" se lam
                # nguoi doc di sua cau TC, trong khi loi nam o bo luat fo_flow.
                record["action"] = {
                    "kind": "needs_human",
                    "reason": f"không lái tới được {action.target}, dừng ở {walk['activity']}",
                }
                return {"steps": done, "status": "NEEDS_HUMAN", "stopped_at": index,
                        "blocked_steps": blocked_steps, "khung": ctx["khung"],
                    "thao_tac": ctx["thao_tac"]}
            record["action"] = {"kind": "goto", "target": action.target,
                                "activity": walk["activity"], "reason": action.reason}
            t0 = time.monotonic()
            if action.cho:
                await asyncio.sleep(action.cho)
            continue
        if isinstance(action, act_resolver.NeedsHuman):
            return {"steps": done, "status": "NEEDS_HUMAN", "stopped_at": index,
                    "blocked_steps": blocked_steps, "khung": ctx["khung"],
                    "thao_tac": ctx["thao_tac"], "tag_log": tag_log}
        if isinstance(action, act_resolver.XemTag):
            kq = await tag_logcat.xem(client, serial, package, list(action.tags))
            for tag, dongs in kq["tags"].items():
                tag_log.setdefault(tag, []).extend(d for d in dongs if d not in tag_log.get(tag, []))
            record["action"] = {**action.summary, "lam": kq["lam"],
                                "so_dong": {t: len(d) for t, d in kq["tags"].items()}}
            log_fn(f"    {kq['lam'] or 'đọc tag'}: " + ", ".join(f"{t} {len(d)} dòng" for t, d in kq["tags"].items()))
            continue
        if await act_exec.resume_neu_o_nen(client, serial, package, step, record, ctx):
            continue
        await act_exec.lam(client, serial, action, record, ctx, log_fn)
    cuoi = await drive_probes._chup_ket(client, serial, package, len(done) + 1,
                           ctx["trang_cu"], ctx["vuot_sau"], dump_cu)
    done.append(cuoi)
    ra = {"steps": done, "status": "DONE", "stopped_at": 0,
          "blocked_steps": blocked_steps, "final": cuoi, "khung": ctx["khung"],
          "thao_tac": ctx["thao_tac"], "tag_log": tag_log}
    # Anh cuoi da chup dung man case quan sat; inter con che thi dong ngay,
    # de no nam do toi luc force-stop la co ad_click (do 2026-10-24).
    dong = await fo_flow.dong_ad_dang_che(client, serial, CHO_NUT_DONG_AD)
    if dong:
        ra["dong_ad"] = dong
        log_fn(f"    {dong}")
    if thu_vuot:
        ra["thu_vuot"] = await drive_probes._thu_vuot(client, serial, package, cuoi, len(done) + 1)
        done.append(ra["thu_vuot"]["anh"])
    return ra
