"""Report gop nhieu tab tinh nang (widget + rating + daily checkin cua cung app): ten cac tab len tieu de,
case xep theo tab truoc - khong tron CHECKIN-R03 canh RATING-R03 (AIP893 2.6.0 13/11/2026)."""

from rcr import report_data, report_html

from tests.test_report_html import RESULT, FakeBaseline


def _rec(tab, so, feature):
    row = {"key": f"{tab}#{so}", "tab": f"TC SDK {tab}", "label": f"{so} nhãn", "feature": feature}
    return report_data.case_record(row["key"], row, RESULT)


def _data(recs):
    return report_data.page_data(FakeBaseline(), {"total": len(recs), "runnable": len(recs), "sdk": ""},
                                 recs, app_label="AI Photo 2.6.0")


def test_gop_nhieu_tab_ten_tab_len_tieu_de_va_xep_theo_tab():
    recs = [_rec("widget", "WIDGET-R03-01", "R03 — x"), _rec("rating", "RATING-R03-01", "R03 — x"),
            _rec("daily checkin", "CHECKIN-R03-01", "R03 — x")]
    data = _data(recs)
    assert data["title"] == "Lượt chấm AI Photo 2.6.0 · Daily checkin, Rating, Widget"
    html = report_html.build(data)
    i = [html.index(f'"key": "{k}"') for k in ("daily checkin#CHECKIN-R03-01", "rating#RATING-R03-01",
                                               "widget#WIDGET-R03-01")]
    assert i == sorted(i)
    assert '"tab": "rating"' in html and "tabhead" in html


def test_mot_tab_giu_tieu_de_cu():
    data = _data([_rec("widget", "WIDGET-R01-01", "R01")])
    assert data["title"] == "Lượt chấm AI Photo 2.6.0"
