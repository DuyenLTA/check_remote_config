"""Doc/ghi file SharedPreferences XML cua Android. THUAN CHUOI - khong parse cay.

VI SAO KHONG DUNG xml.etree: file do Android ghi, co thu tu va format rieng.
Parse roi render lai la doi format -> rui ro app khong doc duoc, hoac mat node
la. O day chi thay dung 1 gia tri tai cho, moi byte khac giu nguyen.

Hai dang node trong prefs:
    <boolean name="k" value="true" />        <- value nam trong thuoc tinh
    <string name="k">noi dung</string>       <- value nam trong noi dung
"""

from __future__ import annotations

import re

from .models import MirrorNode

# Node dang thuoc tinh: boolean/long/int/float
_ATTR_RE = re.compile(
    r'<(?P<kind>boolean|long|int|float)\s+name="(?P<key>[^"]+)"\s+value="(?P<val>[^"]*)"\s*/>'
)
# Node dang noi dung: string (co the rong <string name="k" />)
_TEXT_RE = re.compile(
    r'<(?P<kind>string)\s+name="(?P<key>[^"]+)"\s*(?:/>|>(?P<val>.*?)</string>)',
    re.DOTALL,
)

ATTR_KINDS = frozenset({"boolean", "long", "int", "float"})


def parse_nodes(xml: str) -> dict[str, MirrorNode]:
    """Bóc moi node thanh {key: MirrorNode}. Bo qua <set>, <map> long nhau."""
    out: dict[str, MirrorNode] = {}
    for m in _ATTR_RE.finditer(xml):
        out[m.group("key")] = MirrorNode(m.group("key"), m.group("kind"), m.group("val"))
    for m in _TEXT_RE.finditer(xml):
        out[m.group("key")] = MirrorNode(
            m.group("key"), m.group("kind"), unescape(m.group("val") or "")
        )
    return out


def escape(value: str) -> str:
    """Escape cho noi dung <string>. Thu tu quan trong: & truoc tien."""
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def unescape(value: str) -> str:
    return (
        value.replace("&quot;", '"')
        .replace("&apos;", "'")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&amp;", "&")
    )


def coerce(kind: str, rc_value: str) -> str:
    """Doi gia tri RC (luon la string) sang dang dung cho kieu XML cua mirror.

    RC luu 'true'/'false'/'3'/'[...]' het duoi dang string. Mirror thi co kieu.
    Sai kieu la app doc ra ClassCastException -> phai fail RO thay vi ghi bua.
    """
    v = rc_value.strip()
    if kind == "boolean":
        return _as_boolean(v)
    if kind in ("long", "int"):
        try:
            return str(int(v))
        except ValueError:
            raise ValueError(f"kieu {kind} nhung gia tri khong phai so: {rc_value!r}") from None
    if kind == "float":
        try:
            return str(float(v))
        except ValueError:
            raise ValueError(f"kieu float nhung gia tri khong phai so: {rc_value!r}") from None
    # string: giu NGUYEN VAN, ke ca khoang trang dau/cuoi - RC luu dung tung ky tu
    # (JSON hong `{"image_url": ` co dau cach cuoi; strip la verify bao lech gia)
    return rc_value


# Luat doc boolean cua Firebase Remote Config (FirebaseRemoteConfigValue).
# RC luu MOI gia tri duoi dang string; SDK doi sang boolean theo dung hai tap nay.
_TRUE = frozenset({"1", "true", "t", "yes", "y", "on"})
_FALSE = frozenset({"0", "false", "f", "no", "n", "off", ""})


def _as_boolean(v: str) -> str:
    """Gia tri RC -> 'true'/'false' cho node boolean cua mirror.

    TC co nhung case co tinh dat gia tri KHONG hop le (`null`, chuoi rong) de
    xem app xu ly sao. Firebase cho phep dat, va SDK doc ra `false` - chuoi la
    khong parse duoc thi getBoolean tra ve mac dinh. Mirror phai ghi dung cai
    app se doc, neu khong thi bo luon case do (truoc day 18/53 case chet o day).
    """
    low = v.lower()
    if low in _TRUE:
        return "true"
    if low in _FALSE:
        return "false"
    return "false"


def set_value(xml: str, node: MirrorNode, rc_value: str) -> str:
    """Thay gia tri cua 1 key, GIU NGUYEN kieu XML san co. Tra XML moi.

    Khong tim thay node -> raise: khong tu them node moi vao prefs cua app
    (them node la la doan, SDK se tu sync).
    """
    new_val = coerce(node.kind, rc_value)
    if node.kind in ATTR_KINDS:
        pat = re.compile(
            rf'(<{node.kind}\s+name="{re.escape(node.key)}"\s+value=")[^"]*(")'
        )
        out, n = pat.subn(lambda m: m.group(1) + new_val + m.group(2), xml, count=1)
    else:
        pat = re.compile(
            rf'(<string\s+name="{re.escape(node.key)}"\s*)(?:/>|>.*?</string>)',
            re.DOTALL,
        )
        out, n = pat.subn(
            lambda m: f"{m.group(1)}>{escape(new_val)}</string>", xml, count=1
        )
    if n != 1:
        raise ValueError(f"khong tim thay node {node.key!r} kieu {node.kind!r} trong prefs")
    return out


def read_long(xml: str, key: str) -> int | None:
    m = re.search(rf'<long\s+name="{re.escape(key)}"\s+value="(-?\d+)"', xml)
    return int(m.group(1)) if m else None


def set_long(xml: str, key: str, value: int) -> str:
    """Dat 1 <long>. Dung cho last_fetch_time_in_millis o settings.xml."""
    pat = re.compile(rf'(<long\s+name="{re.escape(key)}"\s+value=")-?\d+(")')
    out, n = pat.subn(lambda m: m.group(1) + str(value) + m.group(2), xml, count=1)
    if n != 1:
        raise ValueError(f"khong tim thay <long name={key!r}> trong settings prefs")
    return out
