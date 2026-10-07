"""Chay lan luot nhieu case roi ghi report. Tach khoi cli_check de cli chi con
doc tham so va in JSON.

Doc lai baseline giua cac case khi can: `pm clear` sinh lai file config, ban cu
tro toi noi dung khong con nua - `run_case` tra ve baseline dang dung.
"""

from __future__ import annotations

from pathlib import Path

from . import (
    ad_positions,
    assert_ads,
    case_run,
    precond_guards,
    fo_flow,
    rc_guards,
    rc_patch,
    report_data,
    report_html,
    tc_select,
)
from .adb_parsers import AdbError, AdbTransportError
from .models import RcError


# Case ra ket qua lo lung (khong PASS/FAIL) -> chay lai toi da bay nhieu lan.
LAN_CHAY_LAI = 3


def _noop(_msg: str) -> None:
    pass


async def _try_restore(client, baseline, log_fn) -> None:
    """Case hong giua chung co the da ghi mot phan config - tra lai cho sach."""
    try:
        await rc_patch.restore(client, baseline)
    except Exception as exc:  # noqa: BLE001 - loi restore khong duoc che loi that
        log_fn(f"    (khong tra duoc config ve nguyen trang: {exc})")


async def run_cases(client, baseline, args, runnable, rows, tc_info, log_fn=_noop) -> list[dict]:
    """Chay lan luot cac case nguoi dung chi dinh (`--case a,b,c`)."""
    by_key = {r["key"]: r for r in rows}
    records = []
    for wanted in [k.strip() for k in args.case.split(",") if k.strip()]:
        key = wanted
        try:
            # Ten case sai cung phai xu nhu case hong: bao loi o day la mat sach
            # ket qua cua nhung case da chay xong truoc do.
            key = tc_select.pick(runnable, wanted)
            chosen = runnable[key]
            log_fn(f"--- case {key} ---")
            row = by_key.get(key, {})
            goto = "" if args.no_walk else fo_flow.target_for(
                f"{row.get('label', '')} {row.get('feature', '')} {chosen['precondition']}"
            )
            # Ma vi tri ads noi san key cua case nam o man nao. Buoc Action cua
            # TC van bao "Hoan thanh luong FO den Home", nhung doc log o dung
            # man do la du - di tiep chi ton thoi gian.
            #
            # Lay vi tri tu CA HAI nguon: key ma case dat, va ma trong dong
            # Expected. Chi doc dong Expected thi case tat mot loat unit
            # (case 17: 10 unit) khong ra vi tri nao va phai di het luong.
            tokens = set(assert_ads.vi_tri_cua_case(
                {k for luot in chosen["runs"] for k in luot}))
            trong_cau = assert_ads.case_position(chosen["expects"])
            if trong_cau:
                tokens.add(trong_cau)
            man_can = None if args.full_walk else fo_flow.man_sau_cung(tokens)
            # Precondition doi ad KHONG FILL: ep bang cach doi `id_*` sang mot
            # slot khong ton tai. Khong ep thi case chay duoi dung trang thai
            # tu nhien cua may, va ba case ta ba dieu kien khac nhau deu ra
            # cung mot ket qua (do 2026-09-28, case 22/23/24).
            ep = precond_guards.ep_duoc(chosen["precondition"])
            them = precond_guards.khoa_ep_fail(tokens, baseline.configs) if ep else {}
            if them:
                log_fn(f"  ép ad fail ({', '.join(ep)}): "
                       + ", ".join(f"{k}=…/{v.rsplit('/', 1)[-1]}" for k, v in them.items()))
            # Cong tac tong ads luon BAT lam nen (user chot 2026-10-03): sau
            # `pm clear` app fetch config moi co `enable_all_ads*=false` -> khong
            # ads nao chay, moi dong ve ads thanh "khong do duoc". Truoc do reset
            # mem giu cache cu (ads bat) nen khong ai thay. Key case tu ghi thi
            # case thang.
            nen = {k: "true" for k in rc_guards.NEN_ADS if k in baseline.configs}
            runs = [nen | dict(luot) | them for luot in chosen["runs"]]
            # Report chi duoc co PASS/FAIL (user chot 2026-10-06): ket qua lo
            # lung (doc file trung luc SDK ghi, ad chua fill...) -> tu chay lai.
            toi_da = LAN_CHAY_LAI + 1     # +1: cho lan xac nhan / phan xu FAIL
            lich_su: list[str] = []
            result = None
            for lan in range(1, toi_da + 1):
                try:
                    result, baseline = await case_run.run_case(
                        client, baseline, runs, chosen["precondition"],
                        () if args.no_actions else chosen["actions"], chosen["expects"], goto,
                        keep=args.keep, out_dir=args.out_dir, dex=not args.no_dex_check,
                        log_fn=log_fn, man_can=man_can, user_state=chosen.get("user_state", ""),
                        runtime=chosen.get("runtime", False),
                    )
                except (RcError, AdbError) as exc:
                    if lan >= LAN_CHAY_LAI or isinstance(exc, AdbTransportError):
                        raise
                    log_fn(f"    LOI (lan {lan}): {exc} -> chay lai case")
                    await _try_restore(client, baseline, log_fn)
                    continue
                v = result.get("verdict")
                lich_su.append(v)
                if v not in ("PASS", "FAIL", "KEY_NOT_USED"):
                    if lan >= LAN_CHAY_LAI:
                        break
                    log_fn(f"    lan {lan}: verdict {v} -> chay lai case")
                    continue
                # FAIL KHONG duoc len report khi chi thay mot lan (user chot
                # 2026-10-07): mot lan FAIL co the do config bi fetch de, ad
                # fill khac, tool nhin tre. Chay lai xac nhan; lech nhau thi
                # chay them mot lan phan xu va danh dau khong on dinh.
                if v == "FAIL" and lich_su.count("FAIL") < 2 and lan < toi_da:
                    log_fn(f"    lan {lan}: FAIL -> chay lai de xac nhan truoc khi bao")
                    continue
                if (v == "PASS" and "FAIL" in lich_su and lich_su.count("PASS") < 2
                        and lan < toi_da):
                    log_fn(f"    lan {lan}: PASS sau khi lan truoc FAIL -> chay them de phan xu")
                    continue
                break
            if result is not None:
                result["lich_su_verdict"] = lich_su
                if "FAIL" in lich_su and "PASS" in lich_su:
                    result["khong_on_dinh"] = True
                    log_fn(f"    KHONG ON DINH qua cac lan: {', '.join(lich_su)}")
        except AdbTransportError:
            raise  # mat ket noi may: chay tiep la vo nghia
        except (RcError, AdbError) as exc:
            # MOT case hong khong duoc phep giet ca luot: 53 case chay 50 phut,
            # chet o case thu 14 la mat sach cong cua 13 case truoc.
            log_fn(f"    LOI: {exc}")
            await _try_restore(client, baseline, log_fn)
            records.append(report_data.error_record(key, by_key.get(key, {}), str(exc)))
            continue
        # Precondition doi mot dieu kien may nay khong tao duoc (throttle bang
        # thong, mediation test mode): case KHONG duoc ra PASS im lang - no
        # chua he chay dung nhanh ma TC mo ta.
        thieu = precond_guards.khong_ep_duoc(chosen["precondition"])
        if ep:
            # Dieu kien dat hay khong la do TRANG THAI THAT: kiem bang log, du
            # da ep hay khong. Ep roi ma ad van fill thi ep hong.
            don_vi = list(((result.get("runs") or [{}])[0].get("ads") or {})
                          .get("units", {}).values())
            vi = ", ".join(sorted(tokens)) or "vị trí của case"
            thuoc = [u for u in don_vi
                     if any(ad_positions._khop_vi_tri(u, t) for t in tokens)]
            if not thuoc:
                thieu = thieu + [f"{', '.join(ep)} — log không có request nào của {vi}, "
                                 "chưa biết ad có fill hay không"]
            elif not precond_guards.da_khong_fill(don_vi, tokens,
                                                  ad_positions._khop_vi_tri):
                thieu = thieu + [f"{', '.join(ep)} — lượt chạy này ad vẫn fill"]
            elif them:
                result["ep_ad_fail"] = f"ép fail bằng cách đổi `id_*` của {vi} sang slot trống"
            else:
                result["ep_ad_fail"] = ("không ép được (remote config không khai `id_*` cho "
                                        f"{vi}) — nhưng log cho thấy ad tự không fill, "
                                        "đúng trạng thái case cần")
        if thieu and result.get("verdict") == "PASS":
            result["verdict"] = "BLOCKED"
            result["precondition_thieu"] = thieu
            log_fn("    precondition chua tao duoc: " + "; ".join(thieu) + " -> BLOCKED")
        log_fn(f"    verdict: {result['verdict']}")
        records.append(report_data.case_record(key, by_key.get(key, {}), result))

    if args.report:
        page = report_html.build(
            report_data.page_data(baseline, tc_info, records, args.app_label)
        )
        path = Path(args.report)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(page, encoding="utf-8")
        log_fn(f"Report: {path} ({len(page) // 1024}KB)")
    return records


