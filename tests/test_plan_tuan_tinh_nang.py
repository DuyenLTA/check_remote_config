from rcr import plan_tuan


def test_tinh_nang_lay_tu_scope_plan(monkeypatch):
    monkeypatch.setenv(plan_tuan.ENV, "https://docs.google.com/spreadsheets/d/x/edit")
    monkeypatch.setattr(plan_tuan, "tai", lambda link, out: "plan.xlsx")
    monkeypatch.setattr(plan_tuan, "yeu_cau", lambda f, ma, ngay: {"pham_vi": [
        "- Apply IAA\n- SDK Widget\n- SDK Rating\n- SDK Daily Checkin\n- Luồng gen ngầm\n- Uninstall",
        "- Apply SDK 3.7.2"]})
    assert plan_tuan.tinh_nang("AIP944", "out") == ["iaa", "widget", "rating", "daily checkin", "gen-ngam"]


def test_tinh_nang_plan_hong_hoac_chua_cau_hinh_tra_rong(monkeypatch):
    monkeypatch.delenv(plan_tuan.ENV, raising=False)
    assert plan_tuan.tinh_nang("AIP944", "out") == []
    monkeypatch.setenv(plan_tuan.ENV, "x")

    def hong(link, out):
        raise RuntimeError("mat mang")
    monkeypatch.setattr(plan_tuan, "tai", hong)
    assert plan_tuan.tinh_nang("AIP944", "out") == []
    monkeypatch.setattr(plan_tuan, "tai", lambda link, out: "p")
    monkeypatch.setattr(plan_tuan, "yeu_cau", lambda f, ma, ngay: None)
    assert plan_tuan.tinh_nang("AIP944", "out") == []
