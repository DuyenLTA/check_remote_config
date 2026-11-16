"""Bo case co 'Tiep noi' thi tu bat che do chuoi (quen --chuoi: AIP892 16/11/2026 pm clear giua chuoi)."""

from rcr.run_batch import tu_bat_chuoi

R = {"rating#R01-06": {"precondition": "1. Clear data."},
     "rating#R01-07": {"precondition": "1. Tiếp nối RATING-R01-06 (cùng lượt, không clear data)."}}


def test_co_case_tiep_noi_thi_bat_chuoi():
    assert tu_bat_chuoi(R, "rating#R01-06,rating#R01-07")
    assert not tu_bat_chuoi(R, "rating#R01-06")
