"""Dong bo spec SDK Tutorial tu Confluence ve `data/specs/` (text) + manifest version.

Tap spec theo doi: trang "SDK Tutorial - Ver 6.4.0" (goc cua bo TC) va moi trang
"visionlab:tutorial:X.Y.Z" tu 3.0.1 tro di, KE CA trang moi them sau nay va trang
con cua chung - quet lai cay duoi trang cha "SDK Tutorial" moi lan chay.

Chay: `python -m rcr.spec_sync` -> in trang moi / da sua (so version Confluence),
tai lai dung nhung trang do. Can env CONFLUENCE_BASE_URL + CONFLUENCE_TOKEN
(Personal Access Token); nginx cua confluence.apero.vn chan User-Agent mac dinh
cua urllib/curl nen luon gui UA trinh duyet.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT_ID = "168689676"  # trang cha "SDK Tutorial" trong space VL
PINNED = {"233111805"}  # SDK Tutorial - Ver 6.4.0 - 020725
MIN_VERSION = (3, 0, 1)
TITLE_VER = re.compile(r"visionlab:tutorial:(\d+)\.(\d+)\.(\d+)", re.I)
SPEC_DIR = Path(__file__).parent / "data" / "specs"
MANIFEST = SPEC_DIR / "manifest.json"
UA = "Mozilla/5.0"


def _get(path: str, **params) -> dict:
    base = os.environ["CONFLUENCE_BASE_URL"].rstrip("/")
    url = f"{base}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {os.environ['CONFLUENCE_TOKEN']}", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def is_spec_title(title: str) -> bool:
    """Trang spec goc: visionlab:tutorial >= 3.0.1, bo ban nhap 'Copy of ...'."""
    if title.lower().startswith("copy of"):
        return False
    m = TITLE_VER.search(title)
    return bool(m) and tuple(map(int, m.groups())) >= MIN_VERSION


def list_pages() -> list[dict]:
    """Trang spec + trang con cua chung (id, title, version, when, parent_spec)."""
    pages, start = [], 0
    while True:
        d = _get("/rest/api/content/search", cql=f"type=page AND ancestor={ROOT_ID}",
                 limit=100, start=start, expand="version,ancestors")
        pages += d.get("results", [])
        if d.get("size", 0) < 100:
            break
        start += 100
    specs = {p["id"] for p in pages if p["id"] in PINNED or is_spec_title(p["title"])}
    out = []
    for p in pages:
        anc = [a["id"] for a in p.get("ancestors", [])]
        owner = p["id"] if p["id"] in specs else next((a for a in reversed(anc) if a in specs), None)
        if owner and not p["title"].lower().startswith("copy of"):
            out.append({"id": p["id"], "title": p["title"], "version": p["version"]["number"],
                        "when": p["version"]["when"], "spec": owner})
    return sorted(out, key=lambda x: x["title"])


class _Text(HTMLParser):
    """Storage-format -> text doc duoc: heading '#', hang bang 'a | b', list '-'."""

    BLOCK = {"p", "div", "br", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "li", "ac:task"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("ac:placeholder", "style", "script"):
            self.skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")
            if tag[0] == "h" and tag[1:].isdigit():
                self.parts.append("#" * int(tag[1]) + " ")
            elif tag == "li":
                self.parts.append("- ")
        elif tag in ("td", "th"):
            self.parts.append(" | ")
        elif tag == "ri:attachment":
            self.parts.append(f"[file:{a.get('ri:filename', '')}]")
        elif tag == "ri:page":
            self.parts.append(f"[page:{a.get('ri:content-title', '')}]")
        elif tag == "a" and a.get("href"):
            self.parts.append(f"[{a['href']}] ")

    def handle_endtag(self, tag):
        if tag in ("ac:placeholder", "style", "script"):
            self.skip = max(0, self.skip - 1)

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)

    def text(self) -> str:
        raw = "".join(self.parts).replace("\xa0", " ")
        lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in raw.splitlines()]
        lines = [ln for ln in lines if ln not in ("-", "|")]  # li / o bang rong
        return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip() + "\n"


def to_text(storage_html: str) -> str:
    p = _Text()
    p.feed(storage_html)
    return p.text()


def slug(title: str) -> str:
    """Ten file ngan, on dinh: 'tutorial-3.0.1', 'sdk-tutorial-ver-6.4.0-020725'."""
    m = TITLE_VER.search(title)
    if m and title.upper().startswith("SDK TUTORIAL VISIONLAB"):
        return "tutorial-" + ".".join(m.groups())
    return re.sub(r"[^a-z0-9.]+", "-", title.lower()).strip("-")[:120]


def sync(write: bool = True) -> dict[str, list[dict]]:
    """So cay Confluence voi manifest; tai lai trang moi / doi version."""
    old = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    now = list_pages()
    diff = {"new": [], "changed": [], "removed": []}
    for p in now:
        prev = old.get(p["id"])
        if prev is None:
            diff["new"].append(p)
        elif prev["version"] != p["version"]:
            diff["changed"].append({**p, "prev_version": prev["version"]})
    ids = {p["id"] for p in now}
    diff["removed"] = [v | {"id": k} for k, v in old.items() if k not in ids]
    if write:
        SPEC_DIR.mkdir(parents=True, exist_ok=True)
        for p in diff["new"] + diff["changed"]:
            body = _get(f"/rest/api/content/{p['id']}", expand="body.storage")["body"]["storage"]["value"]
            p["file"] = f"{slug(p['title'])}.txt"
            dst = SPEC_DIR / p["file"]
            if dst.exists():  # giu ban cu de doc dung phan spec vua sua (diff .prev.txt)
                dst.replace(dst.with_suffix(".prev.txt"))
            head = f"# {p['title']}\n# id={p['id']} version={p['version']} when={p['when']}\n\n"
            dst.write_text(head + to_text(body), encoding="utf-8")
        manifest = {p["id"]: {k: p.get(k) or old.get(p["id"], {}).get(k)
                              for k in ("title", "version", "when", "spec", "file")} for p in now}
        MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return diff


def main() -> int:
    diff = sync(write="--check" not in sys.argv)
    for kind in ("new", "changed", "removed"):
        for p in diff[kind]:
            extra = f" (v{p['prev_version']} -> v{p['version']})" if kind == "changed" else ""
            print(f"{kind.upper():8} {p['id']} {p['title']}{extra}")
    if not any(diff.values()):
        print("Spec khong doi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
