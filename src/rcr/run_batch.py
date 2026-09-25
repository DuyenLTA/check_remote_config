"""Chay lan luot nhieu case roi ghi report. Tach khoi cli_check de cli chi con
doc tham so va in JSON.

Doc lai baseline giua cac case khi can: `pm clear` sinh lai file config, ban cu
tro toi noi dung khong con nua - `run_case` tra ve baseline dang dung.
"""

from __future__ import annotations

from pathlib import Path

from . import case_run, fo_flow, rc_patch, report_data, report_html, tc_select
from .adb_parsers import AdbError, AdbTransportError
from .models import RcError


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
            result, baseline = await case_run.run_case(
                client, baseline, chosen["runs"], chosen["precondition"],
                () if args.no_actions else chosen["actions"], chosen["expects"], goto,
                keep=args.keep, out_dir=args.out_dir, dex=not args.no_dex_check, log_fn=log_fn,
            )
        except AdbTransportError:
            raise  # mat ket noi may: chay tiep la vo nghia
        except (RcError, AdbError) as exc:
            # MOT case hong khong duoc phep giet ca luot: 53 case chay 50 phut,
            # chet o case thu 14 la mat sach cong cua 13 case truoc.
            log_fn(f"    LOI: {exc}")
            await _try_restore(client, baseline, log_fn)
            records.append(report_data.error_record(key, by_key.get(key, {}), str(exc)))
            continue
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


