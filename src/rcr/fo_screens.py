"""Ten man hinh trong luong First Open: doc tu chu, va thu tu truoc/sau.

Tach khoi `fo_flow` de moi file duoi 200 dong: `fo_flow` lai may, file nay chi
tra loi "cau nay noi ve man nao" va "man nao nam sau man nao".
"""

from __future__ import annotations

# Case noi ve man nao -> lai toi activity nao. Doc tu nhan/Precondition cua
# case, vi bo TC khong co cot nao khai man hinh.
# `#N` la trang thu N trong cung mot activity (cac trang OB dung chung activity).
SCREEN_WORDS = (
    ("onb2", "OnboardingActivity#2"), ("onb3", "OnboardingActivity#3"),
    ("onb4", "OnboardingActivity#4"), ("onb1", "OnboardingActivity#1"),
    ("ob1", "OnboardingActivity#1"), ("ob2", "OnboardingActivity#2"),
    ("ob3", "OnboardingActivity#3"), ("ob4", "OnboardingActivity#4"),
    ("onboarding 2", "OnboardingActivity#2"), ("onboarding 3", "OnboardingActivity#3"),
    ("onboarding", "OnboardingActivity"), ("onb", "OnboardingActivity"),
    ("question", "QuestionActivity"), ("language", "Language"),
    # Ten lop that la `VslTemplate4Language14Activity` / `...Language24Activity`,
    # KHONG chua chuoi "LanguageActivity". `walk_to` so bang `target in activity`
    # nen de "LanguageActivity" la khong bao gio khop: case ve man Language lai
    # het ca luong roi bao "KHONG toi duoc" (do 2026-09-28, case 3 va 4).
    ("lfo", "Language"), ("paywall", "BillingActivity"),
    ("home", "MainActivity"),
    # Xep CUOI: "hoan thanh luong" khong neu ten man nao, nhung het luong First
    # Open la Home. De truoc thi no cuop mat cau co ten man ro rang
    # ("Hoan thanh luong FO den OB3").
    ("hoàn thành luồng", "MainActivity"), ("hoan thanh luong", "MainActivity"),
)


# Ma vi tri ads da noi san man hinh no nam o: 101/102/105/106 o splash, 201 o
# Language 1, 30x o onboarding. Case ve mot vi tri chi can di TOI man do la do
# duoc - buoc Action cua TC van bao "Hoan thanh luong FO den Home", nhung di
# tiep chi ton thoi gian: 16 thao tac thay vi 0 (do 2026-09-28, case 102 mat
# ~2 phut trong khi doc log o splash la xong).
MAN_THEO_MA = {
    "101": "", "102": "", "105": "", "106": "",      # splash: app tu o do sau khi mo
    "201": "Language",
    "202": "Language",
    "301": "OnboardingActivity#1", "302": "OnboardingActivity#2",
    "303": "OnboardingActivity#3", "304": "OnboardingActivity#4",
    "305": "OnboardingActivity#5", "306": "OnboardingActivity#5",
}
# Thu tu cac man trong luong FO, de biet man nao nam SAU man nao.
THU_TU = ("", "Language", "OnboardingActivity#1", "OnboardingActivity#2",
          "OnboardingActivity#3", "OnboardingActivity#4", "OnboardingActivity#5",
          "OnboardingActivity", "QuestionActivity", "BillingActivity", "MainActivity")


def man_cua_ma(token: str) -> str | None:
    """Man ma vi tri `102_spl_n_inter_high1` nam o. None neu ma khong biet."""
    ma = (token or "")[:3]
    return MAN_THEO_MA.get(ma) if ma in MAN_THEO_MA else None


def thu_tu(target: str) -> int:
    """Man nay o buoc thu may cua luong. Khong biet -> xep cuoi (di het)."""
    return THU_TU.index(target) if target in THU_TU else len(THU_TU)


def target_for(text: str) -> str:
    """Man can lai toi, "" neu case chi noi ve splash (app tu o do sau khi mo)."""
    low = (text or "").casefold()
    if "splash" in low or "spl" in low:
        return ""
    for word, activity in SCREEN_WORDS:
        if word in low:
            return activity
    return ""
