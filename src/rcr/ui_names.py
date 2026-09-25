"""Ten goi trong file TC -> node tren cay UI.

TC viet bang ngon ngu cua nguoi ("icon SWIPE", "vung ad"), cay node mang ten
cua lap trinh vien (`ob2Bb2SwipeLottie`). Khong noi hai cai lai thi moi dong ta
UI deu ra "phai nhin mat", du anh va dump da nam san trong tay.

Bang de o `data/ui_names.yaml` - them ten moi thi sua file, khong sua code.
"""

from __future__ import annotations

from pathlib import Path

DATA = Path(__file__).parent / "data" / "ui_names.yaml"


def elements() -> list[dict]:
    import yaml

    return (yaml.safe_load(DATA.read_text(encoding="utf-8")) or {}).get("elements") or []


def find_in(text: str) -> dict | None:
    """Phan tu UI ma cau nay dang noi toi. Khop ten dai truoc ten ngan."""
    low = (text or "").casefold()
    best = None
    for element in elements():
        for alias in [element["name"], *element.get("aliases", [])]:
            if alias.casefold() in low and (best is None or len(alias) > best[0]):
                best = (len(alias), element)
    return best[1] if best else None


def seen_in(element: dict, dumps: list[str]) -> str:
    """Dau vet cua phan tu trong cac dump da chup, "" neu khong thay.

    Khop id theo dang `:id/<ten>` va text theo dang `text="<chu>"` de khong an
    nham mot chuoi bat ky trong XML.
    """
    for dump in dumps:
        for node_id in element.get("ids", []):
            if f":id/{node_id}" in dump:
                return node_id
        for text in element.get("texts", []):
            if f'text="{text}"' in dump:
                return text
    return ""
