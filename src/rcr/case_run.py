"""Chay mot case: chan bang DEX -> reset -> patch -> mo lai app -> verify -> restore.

Tach khoi cli_check de cli_check chi con doc tham so va in JSON. Tien do bao ra
ngoai qua `log` (cli truyen ham in stderr), module nay khong tu in.

THU TU KHONG DUOC DOI:
  1. soi DEX  - app khong doc key thi dung luon, khong ton mot luot mo app
  2. reset    - `pm clear` xoa luon file vua ghi, nen reset PHAI truoc patch
  3. patch -> mo lai -> verify -> restore

DIEM DE SAI: giu patch (`keep=True`) thi PHAI luu snapshot config goc ngay luc
do. Luot sau doc baseline se ra ban DA PATCH, luc do khong con duong nao biet
gia tri that nua.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import replace
from pathlib import Path

from . import (
    act_compound,
    apk_tai_nguyen,
    assert_ad_screen,
    assert_splash_media,
    case_cham_them,
    chup_man,
    fo_screens,
    ad_log,
    case_evidence,
    fa_log,
    fo_flow,
    fo_ngon_ngu,
    screencap,
    assert_check,
    assert_timing,
    crash_log,
    case_drive,
    device_app,
    mau_chu,
    device_reset,
    dex_check,
    net_ctl,
    rc_baseline,
    rc_guards,
    rc_patch,
    rc_snapshot,
    rc_verify,
    runtime_steps,
    sdk_probe,
    splash_media,
    ui_dump,
    ui_names,
)
from .models import RcBaseline, RcError

log = logging.getLogger(__name__)


def _noop(_msg: str) -> None:
    pass


async def apply_case(
    client, baseline: RcBaseline, overrides: dict[str, str], keep: bool, out_dir,
    steps=(), expects=(), goto: str = "", log_fn=_noop, man_can=None,
    precondition: str = "", user_state: str = "",
) -> dict:
    """patch -> tat han app -> mo lai -> verify -> lai cac buoc -> restore.

    Ban release (`baseline.firebase`): patch = publish RC tren server, sau do moi reset (pm clear, old_user lai FO)
    - nguoc thu tu ban debug vi app chi nhan RC moi o lan mo dau sau pm clear.

    Lai buoc TRUOC khi restore: restore xong la config da ve cu, luc do bam gi
    tren app cung khong con dinh dang gi toi case nua.
    """
    snapshot = rc_snapshot.save(baseline, out_dir) if keep and not baseline.firebase else None
    patched = await rc_patch.patch(client, baseline, overrides)
    reset = (await device_reset.prepare_firebase(client, baseline, user_state, log_fn)
             if baseline.firebase else None)

    # Xoa log TRUOC khi mo app: khong thi nhat log ads/crash cua luot truoc.
    await ad_log.clear(client, baseline.serial)
    await crash_log.clear(client, baseline.serial)
    # Property doc luc process START -> bat TRUOC khi mo lai app, khong thi
    # ca luot chay khong co dong FA nao de doi chieu.
    await fa_log.bat(client, baseline.serial)
    # Case "mo app khi mat mang": phai ngat mang TRUOC `restart`. Ngat sau do la
    # app da fetch xong roi - do mot thu khac han cai case hoi.
    # KHONG dung viec ngat mang de gia lap "ad khong fill": do tren may that
    # 2026-09-28, ngat mang thi log KHONG CO unit nao ca - SDK khong gui noi
    # request. No-fill that la "co request, kho khong tra ad", hai trang thai
    # khac han nhau.
    mat_mang = net_ctl.tat_truoc_khi_mo(precondition, steps)
    net = await net_ctl.tat(client, baseline.serial) if mat_mang else None
    if net:
        log_fn("    da ngat mang truoc khi mo app"
               + ("" if not net["thong"] else " - NHUNG may van ra duoc internet"))
    try:
        launch = await device_app.restart(client, baseline.serial, baseline.package)
    except Exception:
        # Mo app hong ma de may mat mang la hong ca nhung luot sau.
        if mat_mang:
            await net_ctl.bat(client, baseline.serial)
        raise
    # Nen splash (anh / GIF theo media_url): chup lien tuc NGAY tu luc mo app, song song voi verify + lai buoc -
    # splash chi song vai giay.
    nen_splash = splash_media.cau_hinh(overrides) if any(
        assert_splash_media.NEN_RE.search(e or "") for e in expects) else {}
    la_gif = str(nen_splash.get("type")).lower() == "gif"
    chup_splash = (asyncio.create_task(splash_media.chup(client, baseline.serial))
                   if nen_splash and not la_gif else None)
    result = await rc_verify.verify(client, baseline, overrides)

    out = {
        "overrides": overrides,
        "patched": list(patched.written),
        "launch": launch,
        "verify": result.summary,
        # Chi noi ve CONFIG, khong phai ve app: PASS/FAIL la viec cua nguoi mo app.
        "verdict": "CONFIG_OK" if result.ok else "BLOCKED",
        "restored": False,
    }
    if net:
        out["net"] = net
    if reset:
        out["reset"] = reset
    # Case noi ve man khac splash -> lai toi do TRUOC khi cham, khong thi moi
    # dong ta UI cua man ay deu ra "chua lai toi noi".
    # Case co dong Expected ve nut X / so dem -> phai nhin NGAY khi toi trang:
    # khong dump xac nhan, khong chup bang chung truoc (chup sau khi nhin xong).
    nhin_ngay = assert_timing.cach_quan_sat(overrides, expects)[1]
    # Ban dich chuoi + color/primary cua APK: dong "text 'Swipe to next'" khi case chon Francais, dong "dung mau
    # primary". Doc mot lan moi versionCode (cache).
    tai = (await apk_tai_nguyen.doc(client, baseline.serial, baseline.package, out_dir)
           if case_cham_them.can_tai_nguyen(expects) else {})
    ban_dich = case_cham_them.ban_dich_cho(expects, tai)
    primary = tai.get("primary", "") if any(case_cham_them.PRIMARY_RE.search(e or "") for e in expects) else ""
    mau_can = tuple(sorted({f"#{h}".upper() for e in expects for h in mau_chu.HEX_RE.findall(e or "")}
                           | ({primary} if primary else set())))
    # Man xa nhat Expected nhac ("OB4: ..."): buoc di tiep / dung som khong duoc dung truoc man do.
    man_xa = case_cham_them.man_xa(expects)
    if man_can is not None and man_xa and fo_flow.thu_tu(man_xa) > fo_flow.thu_tu(man_can):
        man_can = man_xa
    chup, da_chup = chup_man.tao(client, baseline.serial, baseline.package, mau_can)
    if goto and result.ok:
        log_fn(f"    lai toi {goto}...")
        out["walk"] = await fo_flow.walk_to(
            client, baseline.serial, baseline.package, goto, log_fn=log_fn,
            vao_la_tra=nhin_ngay,
            qua_lfo_nhanh=fo_screens.can_qua_lfo_nhanh(precondition, *steps),
            chup=None if nhin_ngay else chup,
        )
        log_fn(f"    {'da toi' if out['walk']['reached'] else 'KHONG toi duoc'} "
               f"{out['walk']['activity'].split('.')[-1]}")
        if out["walk"]["reached"] and not nhin_ngay:
            out["drive"] = await case_evidence._snapshot(client, baseline, out["walk"]["activity"])
        if da_chup:
            # Man di qua truoc man dich (OB1, OB2...) - dong Expected cua chung cham tren cac dump nay.
            out.setdefault("drive", {"steps": []})
            out["drive"]["steps"] = chup_man.danh_so(da_chup, 1) + (out["drive"].get("steps") or [])
    if steps and result.ok:
        # Dong "user co the vuot sang man ke" doi mot cu vuot that de chung
        # minh - bao case_drive lam sau khi moi dong khac da co bang chung.
        thu_vuot = any(assert_check.DOI_VUOT_RE.search(assert_check.QUOTED_RE.sub("", e or "")) for e in expects)
        thu_bam_x = (any(assert_timing.BAM_X_RE.search(e or "") for e in expects)
                     and not any(act_compound.TAP_X_RE.search(st or "") for st in steps))
        da_toi = goto if (out.get("walk") or {}).get("reached") else None
        driven = await case_drive.drive(
            client, baseline.serial, baseline.package, steps, log_fn, man_can, thu_vuot,
            da_toi=da_toi,
            do_anim=any(assert_check.ANIM_RE.search(e or "") for e in expects),
            man_dau=((out.get("drive") or {}).get("steps") or [{}])[-1].get("dump", ""),
            **dict(zip(("cua_so", "ghi_khung"), assert_timing.cach_quan_sat(overrides, expects))),
            thu_bam_x=thu_bam_x,
            mau_can=mau_can, man_xa=man_xa,
        )
        # Giu lai anh/dump cua chuyen lai: no la bang chung da toi dung man.
        driven["steps"] = (out.get("drive") or {}).get("steps", []) + driven["steps"]
        driven["walked"] = bool((out.get("walk") or {}).get("reached"))
        out["drive"] = driven
    if result.ok and out.get("drive"):
        await _hien_cta_neu_can(client, baseline, out["drive"], expects, mau_can, log_fn)
    if result.ok and case_cham_them.can_ve_home(expects, out.get("drive")):
        await _lai_not_toi_home(client, baseline, out["drive"], mau_can, log_fn)
    # Mo lai app sinh them log ads -> chi lam khi case khong co dong nao ve ads.
    if nen_splash and la_gif and result.ok and not any(splash_media.DONG_ADS_RE.search(e or "") for e in expects):
        # GIF: quay raw-frames o lan mo lai (lan mo dau GIF bi inter splash che truoc khi het mot vong).
        try:
            # Ban release: them ID inter splash -> slot trong (chi tren testvsl, restore go het) roi pm clear + mo
            # lan dau de app nhan config; lan mo lai splash khong bi inter che, giu du lau de GIF het vong.
            giu = splash_media.id_inter_splash_trong(baseline.configs) if baseline.firebase else {}
            if giu:
                await rc_patch.patch(client, baseline, dict(overrides) | giu)
                for lenh in (("am", "force-stop", baseline.package), ("pm", "clear", baseline.package),
                             ("pm", "grant", baseline.package, "android.permission.POST_NOTIFICATIONS")):
                    await client.shell(baseline.serial, *lenh)
                await device_app.launch(client, baseline.serial, baseline.package)
                await asyncio.sleep(splash_media.CHO_LAN_DAU)
            da = await splash_media.quay_lan_mo_lai(client, baseline.serial, baseline.package)
            sm = splash_media.phan_tich(nen_splash, da | {"xml": ""}, baseline.package, Path(out_dir) / "media")
            sm["lan_mo_lai"] = True
            sm["giu_splash"] = bool(giu)
        except Exception as exc:  # noqa: BLE001 - do nen hong khong duoc lam hong ca case
            sm = {"loi": f"quay GIF lỗi: {exc}"}
        log_fn("    do GIF lan mo lai: " + (sm.get("loi") or " ".join(
            f"{d['t']:.1f}:{d['khung']}" for d in (sm.get("splash") or [])[::4])))
        out.setdefault("drive", {"steps": []})["splash_media"] = sm
    if chup_splash:
        da, buoc_mau = await chup_splash, None
        da["xml"] = splash_media.dump_splash(out.get("drive"))
        try:
            sm = splash_media.phan_tich(nen_splash, da, baseline.package, Path(out_dir) / "media")
            if mau_can and da.get("xml"):
                nodes = ui_dump.app_nodes(ui_dump.parse_dump(da["xml"]), baseline.package)
                do = [m for png in splash_media.khung_do_mau(da, sm) for m in mau_chu.do(nodes, png, list(mau_can))]
                if do:
                    buoc_mau = {"step": "(chụp liên tục splash)", "activity": "SplashActivity", "mau": do,
                                "action": {"kind": "noop", "reason": "đo màu chữ trên các khung splash đã khớp media"}}
        except Exception as exc:  # noqa: BLE001 - do nen hong khong duoc lam hong ca case
            sm = {"loi": f"đo nền splash lỗi: {exc}"}
        dv = out.setdefault("drive", {"steps": []})
        dv["splash_media"] = sm
        if buoc_mau:
            dv.setdefault("steps", []).append(buoc_mau | {"n": len(dv["steps"]) + 1})
    if out.get("drive"):
        out["drive"]["ban_dich"] = ban_dich
        mp = case_cham_them.mau_primary(expects, out["drive"], primary, ban_dich)
        if mp:
            out["drive"]["mau_primary"] = mp
    # Cham case ads bang LOG, khong bang mat: inter load nhanh hon banner nen no
    # de len truoc khi kip nhin thay banner.
    if out.get("drive"):
        out["drive"]["timeline"] = await case_evidence._dong_thoi_gian(client, baseline, out["drive"])
        # Dong "cach mep banner 12-16dp": bounds trong dump la px, can dpi de doi.
        out["drive"]["density"] = await device_app.density(client, baseline.serial)
    out["ads"] = await case_evidence._read_ads(client, baseline, overrides)
    out["crash"] = await crash_log.read(client, baseline.serial, baseline.package)
    out["events"] = await fa_log.doc(client, baseline.serial)
    qua_nhanh = fo_screens.can_qua_lfo_nhanh(precondition, *steps)
    da_show = (assert_ad_screen.ad_man_nha_da_show(
        out["events"], list(((out.get("ads") or {}).get("units") or {}).values()), "lfo2")
        if qua_nhanh else [])
    if expects:
        out["assert"] = assert_check.check_all(
            expects, out["ads"], out.get("drive") or {}, out["crash"],
            tuple(baseline.configs), overrides, out["events"],
        )
        # Config khong song thi chua test duoc gi - dung ket luan tu dong Expected.
        out["verdict"] = out["verdict"] if not result.ok else out["assert"]["verdict"]
    if da_show:
        # Case doi ad LFO2 CHUA show luc roi LFO2 ma log cho thay da show ngay o
        # LFO2 -> luot nay chay sai nhanh, khong duoc ra PASS/FAIL. run_batch chay
        # lai (lan sau fo_flow da hoc toa do, qua LFO kip).
        out["verdict"] = "BLOCKED"
        out["precondition_thieu"] = [f"ad LFO2 ({', '.join(da_show)}) đã show ngay ở LFO2 — chưa tạo "
                                     "được điều kiện 'chưa kịp show ở LFO2'"]
        log_fn("    ad LFO2 da show o LFO2 -> chua tao duoc precondition, BLOCKED")
    out["ad_click"], out["ad_click_tu_ban"] = fa_log.chia_click(
        out["events"], await fa_log.doc_input(client, baseline.serial))
    if out["ad_click_tu_ban"]:
        log_fn(f"    {out['ad_click_tu_ban']} ad_click khong co thao tac nao cua tool truoc do "
               "-> app/ad tu ban, ghi lai de bao dev, khong dung luot")
    if out["ad_click"]:
        # Click vao ad la app roi luong (mo browser/store): ket qua luot nay khong
        # dung duoc. May QA deu la may test AdMob nen run_batch chay lai case, khong dung luot.
        out["verdict"] = "BLOCKED"
        out["precondition_thieu"] = (out.get("precondition_thieu") or []) + [
            f"log có {out['ad_click']} lần ad_click trong lượt — tool chỉ được đóng ad, "
            "không được bấm vào; kết quả lần này không dùng được (app rời luồng)"]
        log_fn(f"    CO {out['ad_click']} ad_click trong luot -> BLOCKED lan nay")
    # Doc lai config SAU KHI cham: app fetch Firebase luc mo, lan fetch that
    # (khong phai doc cache) kich hoat lai gia tri server va de mat patch - verify
    # o tren doc qua som (foreground +0,8s, fetch xong sau do) nen van ra OK. Do
    # 2026-10-07: 3/3 luot fetch that ~450-510ms thi ad da tat van chay, 8/8 luot
    # doc cache ~280ms thi khong. Lech -> BLOCKED de run_batch chay lai, khong
    # duoc de verdict tren config cua server len report.
    if result.ok:
        try:
            cuoi = await rc_verify.verify(client, baseline, overrides)
        except RcError as exc:
            cuoi = None
            out["verify_cuoi"] = {"ok": None, "loi": str(exc)}
        if cuoi is not None:
            out["verify_cuoi"] = cuoi.summary
            if not cuoi.ok:
                out["verdict"] = "BLOCKED"
                out["config_bi_de"] = [m.summary for m in cuoi.mismatches]
                log_fn("    config bi app fetch de giua luot ("
                       + ", ".join(f"{m.key}={m.got!r}" for m in cuoi.mismatches[:4])
                       + ") -> BLOCKED, chay lai")
    if mat_mang:
        # May phai duoc tra ve co mang du buoc nao trong case da bat lai: luot
        # sau chay tren may mat mang la hong het ma khong ai biet vi sao.
        out["net_cuoi"] = await net_ctl.bat(client, baseline.serial)
        log_fn(f"    tra mang ve: {'thong' if out['net_cuoi']['thong'] else 'VAN CHUA THONG'}")
    if keep:
        out["snapshot"] = str(snapshot)
    else:
        await rc_patch.restore(client, baseline)
        out["restored"] = True
    return out


async def _hien_cta_neu_can(client, baseline, drive: dict, expects, mau_can, log_fn) -> None:
    """Man cuoi la Question ma Expected con chu chua thay (cta 'EN - Go' chi hien SAU khi chon mot o) -> tool thu
    chon o dau roi chup lai (nhu buoc "thu vuot"). AIP886 R02-03 31/10/2026: buoc TC chi "Quan sat" -> FAIL gia."""
    cuoi = (drive.get("final") or {}).get("activity") or ""
    thieu = case_cham_them.chu_chua_thay(expects, drive)
    if "QuestionActivity" not in cuoi or not thieu:
        return
    nodes = ui_dump.app_nodes(ui_dump.parse_dump(await ui_dump.dump(client, baseline.serial)), baseline.package)
    o = [n for n in nodes if n.resource_id in set(ui_names.chon_item_ids()) and n.visible and not n.bounds.empty]
    if not o:
        return
    n = min(o, key=lambda n: (n.bounds.top, n.bounds.left))
    await device_app.tap(client, baseline.serial, *n.bounds.center)
    log_fn(f"    chưa thấy {', '.join(repr(t) for t in thieu)} ở màn Question -> thử chọn 1 ô để hiện nút cta")
    chup, da_chup = chup_man.tao(client, baseline.serial, baseline.package, mau_can, nhan="thử chọn 1 ô")
    import asyncio
    await asyncio.sleep(1.0)
    await chup(cuoi, await ui_dump.dump(client, baseline.serial))
    drive["steps"] = (drive.get("steps") or []) + chup_man.danh_so(da_chup, len(drive.get("steps") or []) + 1)


async def _lai_not_toi_home(client, baseline, drive: dict, mau_can, log_fn) -> None:
    """Expected doi "vao thang Home" ma buoc cuoi con o inter / paywall: lai tiep (fo_flow dong ad khi het dem
    nguoc, dong paywall), giu dump moi man di qua de dong "khong hien man Question" doi chieu duoc."""
    log_fn("    Expected đòi vào Home, màn cuối còn là "
           f"{drive['final'].get('activity', '').split('.')[-1]} -> lái tiếp tới Home")
    chup, da_chup = chup_man.tao(client, baseline.serial, baseline.package, mau_can, nhan="lái tiếp tới Home")
    walk = await fo_flow.walk_to(client, baseline.serial, baseline.package, "MainActivity", log_fn=log_fn,
                                 chup=chup)
    drive["steps"] = (drive.get("steps") or []) + chup_man.danh_so(da_chup, len(drive.get("steps") or []) + 1)
    drive.setdefault("trails", []).append(walk.get("trail") or [])
    if walk["reached"]:
        drive["final"] = {**drive.get("final", {}), "activity": walk["activity"], "page": 0,
                          "lai_tiep": "lái tiếp tới Home sau bước cuối"}


async def run_case(
    client, baseline: RcBaseline, runs, precondition: str = "", steps=(), expects=(),
    goto: str = "", *, keep=False, out_dir=".", dex=True, log_fn=_noop, man_can=None,
    user_state: str = "", runtime: bool = False, ngon_ngu: tuple[str, str] | None = None,
) -> tuple[dict, RcBaseline]:
    """Chay tron mot case. Tra (ket qua, baseline dang dung).

    Baseline tra ve co the KHAC cai truyen vao: `pm clear` sinh lai file config,
    ban cu tro toi noi dung khong con nua.
    """
    # Key nen (cong tac tong ads) la moi truong, khong soi DEX - xem rc_guards.
    keys = sorted({k for r in runs for k in r} - set(rc_guards.NEN_ADS))
    unused: list[str] = []
    if dex:
        log_fn(f"Soi {len(keys)} key trong DEX cua app...")
        used = await dex_check.check(client, baseline.serial, baseline.package, keys, out_dir)
        unused = [k for k, ok in used.items() if not ok]
        if unused and len(unused) == len(keys):
            # Key co trong config Firebase KHAC voi app doc key do: template dung
            # chung nhieu app. Chay tiep la cham mot thu app chang he doc.
            log_fn("  app KHONG doc: " + ", ".join(unused) + " -> KEY_NOT_USED, khong mo app")
            return {"verdict": "KEY_NOT_USED", "keys_not_used": unused, "runs": []}, baseline
        if unused:
            # Bo TC dat ca bo config (50+ key) moi case; mot key phu app khong doc
            # khong duoc chan ca case - truoc day 13/13 case R01 cua TC 3.5.4 ra
            # KEY_NOT_USED chi vi `show_native_full_button_skip`. Bo rieng key do,
            # ghi lai `keys_not_used` de report noi ro dong nao dua vao key app khong doc.
            log_fn("  app KHONG doc: " + ", ".join(unused) + " -> bo key nay, chay tiep cac key con lai")
            runs = [{k: v for k, v in r.items() if k not in unused} for r in runs]
        else:
            log_fn("  app co doc het cac key nay")

    # Ngon ngu case doi chon o LFO ("Chon Francais o LFO1", "ngon ngu da chon = Francais"): dat TRUOC reset -
    # user cu lai luong FO luc reset cung phai chon dung ngon ngu do.
    ngon_ngu = ngon_ngu or fo_ngon_ngu.tim(precondition, steps)
    if ngon_ngu:
        log_fn(f"  ngôn ngữ của case: {ngon_ngu[1]} (lái qua LFO sẽ chọn ngôn ngữ này)")
    token = fo_ngon_ngu.CHON.set(ngon_ngu)
    try:
        if baseline.firebase:                    # reset lam trong tung luot, SAU khi publish RC (apply_case)
            reset = {"mode": "firebase", "matched": user_state or "", "baseline_stale": False}
        else:
            reset = await device_reset.prepare(client, baseline, precondition, user_state, log_fn)
        log_fn(f"Reset: {reset['mode']}" + (f" (khop '{reset['matched']}')" if reset["matched"] else ""))
        if reset["baseline_stale"]:
            log_fn("  app da bi xoa data -> doc lai baseline")
            # Doc lai tu may thi mat dex_keys (chi do duoc bang soi APK) -> mang sang.
            baseline = replace(await rc_baseline.read(client, baseline.serial, baseline.package),
                               dex_keys=baseline.dex_keys)

        out = await _apply_runs(client, baseline, runs, keep, out_dir, steps, expects, goto,
                                log_fn, man_can, precondition, runtime, user_state)
    finally:
        fo_ngon_ngu.CHON.reset(token)
    if unused:
        out["keys_not_used"] = unused
    return out | {"reset": reset}, baseline


async def _apply_runs(client, baseline, runs, keep, out_dir, steps, expects, goto,
                      log_fn, man_can=None, precondition: str = "", runtime=False, user_state: str = "") -> dict:
    """Case co gia tri lua chon -> nhieu luot. Verdict case = luot xau nhat.

    `runtime`: luot i chi lai buoc + cham dong Expected cua luot i (`runtime_steps`).
    """
    done: list[dict] = []
    n = len(runs)
    buoc = runtime_steps.chia_buoc(steps, n) if runtime else [steps] * n
    mong = runtime_steps.chia_expected(expects, n) if runtime else [expects] * n
    for index, overrides in enumerate(runs, 1):
        steps, expects = buoc[index - 1], mong[index - 1]
        head = f"  luot {index}/{len(runs)}: " if len(runs) > 1 else "  "
        log_fn(head + ", ".join(f"{k}={v}" for k, v in overrides.items()))
        out = await apply_case(
            client, baseline, overrides, keep, out_dir, steps, expects, goto,
            log_fn, man_can, precondition, user_state,
        )
        log_fn(f"    foreground sau {out['launch']['waited_s']}s · verify: "
               f"{'CONFIG_OK' if out['verify']['ok'] else 'BLOCKED'} · verdict: {out['verdict']}")
        done.append(out)
        if out.get("ad_click"):
            break  # luot sau cung di qua ad do -> them click
    if keep:
        log_fn(f"  GIU patch tren may. Tra ve: rcr-check --package {baseline.package} --restore")
    else:
        log_fn("  da tra config ve nguyen trang")
    # Verdict cua case = luot xau nhat (cung thang bac voi tung dong Expected).
    return {"runs": done, "verdict": assert_check.worst(r["verdict"] for r in done),
            "ad_click": sum(r.get("ad_click", 0) for r in done),
            "ad_click_tu_ban": sum(r.get("ad_click_tu_ban", 0) for r in done)}


async def restore_saved(client, package: str, serial: str, out_dir) -> dict:
    """Tra config ve ban da luu o luot `--keep` truoc do, roi xoa snapshot.

    Xoa sau khi ghi thanh cong: de lai file la luot sau restore nham ve mot ban
    khong con dung voi may nua.
    """
    path = rc_snapshot.path_for(out_dir, package, serial)
    baseline = rc_snapshot.load(path)
    res = await rc_patch.restore(client, baseline)
    path.unlink(missing_ok=True)
    return {"restored": True, "written": list(res.written), "snapshot": str(path)}
