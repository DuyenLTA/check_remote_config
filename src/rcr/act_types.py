"""Cac thao tac ma mot buoc Action co the tro thanh.

Tach khoi `act_resolver` de moi file duoi 200 dong: file nay noi mot thao tac
LA GI, `act_resolver` noi lam sao doc ra no tu mot cau tieng Viet.

`summary` la thu di thang vao report va vao JSON stdout - doi ten khoa trong do
la doi giao dien voi nguoi dung, khong phai doi chi tiet noi bo.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Tap:
    """`lan` > 1: bam lien tuc ("Tap button X nhanh lien tuc 4-5 lan")."""

    node_label: str
    x: int
    y: int
    matched: str
    lan: int = 1

    @property
    def summary(self) -> dict:
        ra = {"kind": "tap", "node": self.node_label, "x": self.x, "y": self.y,
              "matched": self.matched}
        return ra | {"lan": self.lan} if self.lan > 1 else ra


@dataclass(frozen=True, slots=True)
class Swipe:
    """Vuot mot chieu tren man. `matched` noi huong nay lay tu dau trong cau."""

    direction: str
    matched: str
    lan: int = 1

    @property
    def summary(self) -> dict:
        ra = {"kind": "swipe", "direction": self.direction, "matched": self.matched}
        return ra | {"lan": self.lan} if self.lan > 1 else ra


@dataclass(frozen=True, slots=True)
class Wait:
    seconds: float

    @property
    def summary(self) -> dict:
        return {"kind": "wait", "seconds": self.seconds}


@dataclass(frozen=True, slots=True)
class NoOp:
    reason: str

    @property
    def summary(self) -> dict:
        return {"kind": "noop", "reason": self.reason}


@dataclass(frozen=True, slots=True)
class GoTo:
    """Lai qua ca luong First Open toi mot man hinh, do `fo_flow` lo.

    `cho` la so giay phai dung yen SAU khi toi noi: buoc "Vao man OB2, cho het
    timeout load ad" vua la mot chuyen di vua la mot cu cho. Bo ve cho di thi
    cham ngay luc vua toi man, truoc khi ad kip fail.
    """

    target: str
    reason: str
    cho: float = 0.0

    @property
    def summary(self) -> dict:
        ra = {"kind": "goto", "target": self.target, "reason": self.reason}
        return ra | {"cho": self.cho} if self.cho else ra


@dataclass(frozen=True, slots=True)
class Net:
    """Bat/tat mang tren may. `on=False` la ngat wifi + data."""

    on: bool
    reason: str

    @property
    def summary(self) -> dict:
        return {"kind": "net", "on": self.on, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class NeedsHuman:
    reason: str

    @property
    def summary(self) -> dict:
        return {"kind": "needs_human", "reason": self.reason}


@dataclass(frozen=True, slots=True)
class Background:
    """Nhan Home, de app nam nen `seconds` giay. Buoc "Mo lai app" sau do moi
    dua app len lai - TC hoi ca luc o nen lan luc resume, nen khong gop lam mot."""

    seconds: float
    reason: str

    @property
    def summary(self) -> dict:
        return {"kind": "background", "seconds": self.seconds, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class Rotate:
    """Xoay man lan luot theo `orientations` ("ngang"/"doc"), xong tra lai che
    do xoay cua may nhu cu."""

    orientations: tuple[str, ...]
    reason: str

    @property
    def summary(self) -> dict:
        return {"kind": "rotate", "orientations": list(self.orientations),
                "reason": self.reason}


@dataclass(frozen=True, slots=True)
class Seq:
    """Nhieu thao tac trong mot cau: "Vuot phai ve OB2, roi vuot trai lai OB3"."""

    actions: tuple
    reason: str

    @property
    def summary(self) -> dict:
        return {"kind": "seq", "actions": [a.summary for a in self.actions],
                "reason": self.reason}


@dataclass(frozen=True, slots=True)
class Watch:
    """Dung yen va THEO DOI man trong mot khoang: dump lien tuc, ghi luc nut X /
    so dem nguoc hien. Thay cho buoc "bam gio" - nguoi bam dong ho de do timer,
    tool do bang moc gio cua log va cac khung dump."""

    reason: str

    @property
    def summary(self) -> dict:
        return {"kind": "watch", "reason": self.reason}


@dataclass(frozen=True, slots=True)
class TapId:
    """Cho node mang mot trong `ids` HIEN roi moi tap (nut X OB3 chi hien sau
    `timer_button_x` giay). Khong hien trong cua so theo doi -> ghi lai, khong tap."""

    ids: tuple[str, ...]
    reason: str
    lan: int = 1

    @property
    def summary(self) -> dict:
        ra = {"kind": "tap", "node": "/".join(self.ids), "reason": self.reason}
        return ra | {"lan": self.lan} if self.lan > 1 else ra


@dataclass(frozen=True, slots=True)
class MoLai:
    """Dua app dang nam nen len lai BANG ICON (intent LAUNCHER), ke ca khi TC ghi "mo lai tu Recent": nhieu may
    khong coi Recent la an app (user 29/10/2026), case resume khong ban request nao."""

    reason: str

    @property
    def summary(self) -> dict:
        return {"kind": "resume", "reason": self.reason}


@dataclass(frozen=True, slots=True)
class ThongBao:
    """Keo thanh thong bao xuong roi dong lai, KHONG tap thong bao nao (AIP936 RG08-03 03/11/2026: truoc day cau
    "Keo thanh notification xuong" bi dich thanh vuot man hinh app)."""

    seconds: float
    reason: str

    @property
    def summary(self) -> dict:
        return {"kind": "thong_bao", "seconds": self.seconds, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class ChonMotNgonNgu:
    """"Chon ngon ngu.", "Click 1 ngon ngu khac", "Tap chon 1 ngon ngu": bam mot dong ngon ngu CHON DUOC NGAY (co
    checkboxLanguageItem, khong co mui ten mo rong). `thu_tu` 0 = dong dau, 1 = dong khac dong dau (AIP936
    RG01-04/05 03/11/2026: truoc day tool tim chu "ngon ngu" tren man -> khong thay -> NEEDS_HUMAN)."""

    thu_tu: int
    reason: str

    @property
    def summary(self) -> dict:
        return {"kind": "chon_mot_ngon_ngu", "thu_tu": self.thu_tu, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class KillMoLai:
    """Tat han app (force-stop - tuong duong vuot khoi Recent) roi mo lai tu launcher (AIP936 RG08-05 03/11/2026:
    truoc day "Vuot app khoi Recent (kill)" bi dich thanh vuot man hinh app, app khong he bi kill)."""

    mo_lai: bool
    reason: str

    @property
    def summary(self) -> dict:
        return {"kind": "kill", "mo_lai": self.mo_lai, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class ChonNgonNgu:
    """"Chon Francais o LFO1": ngon ngu da duoc `fo_flow` chon khi lai qua LFO (xem `fo_ngon_ngu`); buoc nay chi
    lai qua LFO neu app con dung truoc do."""

    ten: str
    reason: str

    @property
    def summary(self) -> dict:
        return {"kind": "chon_ngon_ngu", "language": self.ten, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class XemTag:
    """"Xem logcat tag A va B": doc dong log cua dung cac tag (bat tester mode khi co FOR_TESTER_CONFIG)."""

    tags: tuple[str, ...]
    reason: str

    @property
    def summary(self) -> dict:
        return {"kind": "xem_tag", "tags": list(self.tags), "reason": self.reason}


Action = (Tap | Swipe | Wait | NoOp | GoTo | Net | NeedsHuman | Background | Rotate | Seq
          | Watch | TapId | MoLai | ChonNgonNgu | XemTag)
