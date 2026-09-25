"""CSS cua report. Tach khoi report_html de moi file duoi 200 dong.

Bo cuc de LUOT nhanh khi nhieu case: moi case la MOT DONG thu gon, bung ra moi
hien chi tiet. Mau theo vai tro, moi verdict mot mau co dinh - nhin quen mat
roi thi khong phai doc chu.
"""

CSS = """
:root{
  --ground:#f2f4f7; --paper:#fff; --ink:#17202b; --muted:#5a6677; --rule:#dfe3ea; --hover:#f6f8fb;
  --accent:#2c5fb8; --code:#eef1f6;
  --pass:#1d7a4c; --pass-bg:#e2f3e9; --fail:#b3261e; --fail-bg:#fbe6e4;
  --human:#6b3fb5; --human-bg:#efe8fb; --na:#4b5563; --na-bg:#e8ebef;
  --warn:#8a5a00; --warn-bg:#fcf0d6;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    color-scheme:dark;
    --ground:#10141a; --paper:#171d25; --ink:#e3e8ef; --muted:#97a2b2; --rule:#29313c; --hover:#1d242e;
    --accent:#80a8ee; --code:#222a35;
    --pass:#6fd19e; --pass-bg:#15301f; --fail:#f28b82; --fail-bg:#3a1b19;
    --human:#c3a6f5; --human-bg:#2c2240; --na:#b6bfcb; --na-bg:#262d37;
    --warn:#f2c46b; --warn-bg:#352a12;
  }
}
:root[data-theme="dark"]{
  color-scheme:dark;
  --ground:#10141a; --paper:#171d25; --ink:#e3e8ef; --muted:#97a2b2; --rule:#29313c; --hover:#1d242e;
  --accent:#80a8ee; --code:#222a35;
  --pass:#6fd19e; --pass-bg:#15301f; --fail:#f28b82; --fail-bg:#3a1b19;
  --human:#c3a6f5; --human-bg:#2c2240; --na:#b6bfcb; --na-bg:#262d37;
  --warn:#f2c46b; --warn-bg:#352a12;
}
*{box-sizing:border-box}
body{background:var(--ground);color:var(--ink);
  font:15px/1.55 "IBM Plex Sans",system-ui,-apple-system,sans-serif;padding:24px 16px 64px}
.wrap{max-width:1040px;margin:0 auto;display:flex;flex-direction:column;gap:20px}
h1,h2,h3{margin:0;text-wrap:balance;font-weight:600}
h1{font-size:26px;letter-spacing:-.01em} h2{font-size:17px} p{margin:0}
code,.mono{font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace;font-size:.86em}
code{background:var(--code);padding:1px 5px;border-radius:4px}
.eyebrow{font:500 12px/1 "IBM Plex Mono",monospace;letter-spacing:.08em;
  text-transform:uppercase;color:var(--muted)}
.meta{display:flex;flex-wrap:wrap;gap:4px 18px;color:var(--muted);font-size:13px}
.meta b{color:var(--ink);font-weight:500}
.warn{background:var(--warn-bg);color:var(--warn);padding:8px 12px;border-radius:6px;font-size:13.5px}
.card{background:var(--paper);border:1px solid var(--rule);border-radius:10px;padding:16px}
.tally{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
.tile{border:1px solid var(--rule);border-radius:10px;background:var(--paper);padding:12px 14px;
  text-align:left;cursor:pointer;font:inherit;color:inherit;display:flex;flex-direction:column;gap:2px}
.tile:hover{background:var(--hover)}
.tile[aria-pressed="true"]{outline:2px solid var(--accent);outline-offset:-2px}
.tile .num{font:600 28px/1.1 "IBM Plex Mono",monospace;font-variant-numeric:tabular-nums}
.tile .lab{font-size:13px;color:var(--muted)}
.tile.PASS .num{color:var(--pass)} .tile.FAIL .num{color:var(--fail)}
.tile.NEEDS_HUMAN .num{color:var(--human)} .tile.NOT_VERIFIABLE .num{color:var(--na)}
@media (max-width:620px){.tally{grid-template-columns:repeat(2,1fr)}}
.bar{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:var(--ground);
  padding:10px 0;display:flex;flex-wrap:wrap;gap:8px;align-items:center;border-bottom:1px solid var(--rule)}
.chip{font:500 13px "IBM Plex Sans",sans-serif;border:1px solid var(--rule);background:var(--paper);
  color:var(--ink);border-radius:999px;padding:5px 12px;cursor:pointer}
.chip[aria-pressed="true"]{background:var(--ink);color:var(--paper);border-color:var(--ink)}
.search{flex:1;min-width:180px;font:inherit;border:1px solid var(--rule);background:var(--paper);
  color:var(--ink);border-radius:8px;padding:6px 10px}
.bar .count{font-size:13px;color:var(--muted);margin-left:auto}
.linkbtn{font:500 13px "IBM Plex Sans",sans-serif;background:none;border:0;color:var(--accent);
  cursor:pointer;padding:4px 2px}
.group{background:var(--paper);border:1px solid var(--rule);border-radius:10px;overflow:hidden}
.ghead{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;align-items:baseline;padding:12px 16px}
.gcount{display:flex;gap:6px;flex-wrap:wrap}
.row{border-top:1px solid var(--rule);scroll-margin-top:72px}
.rowbtn{all:unset;box-sizing:border-box;width:100%;cursor:pointer;display:grid;
  grid-template-columns:88px 132px 1fr 14px;gap:10px;align-items:start;padding:10px 16px}
.rowbtn:hover{background:var(--hover)}
.rowbtn:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}
.n{font:500 13px "IBM Plex Mono",monospace;color:var(--muted);padding-top:3px}
.t{display:flex;flex-direction:column;gap:2px;min-width:0}
.t b{font-weight:500}
.t span{color:var(--muted);font-size:13.5px;overflow:hidden;text-overflow:ellipsis;
  display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical}
.chev{color:var(--muted);transition:transform .15s;padding-top:2px}
.row.open .chev{transform:rotate(90deg)} .row.open .t span{-webkit-line-clamp:unset}
@media (max-width:620px){.rowbtn{grid-template-columns:1fr 14px}
  .detail{padding-left:16px}
  .rowbtn .pill{grid-column:2;justify-self:start;order:-1}}
.pill{display:inline-block;font:500 11px/1 "IBM Plex Mono",monospace;padding:5px 7px;
  border-radius:999px;white-space:nowrap;text-align:center}
.pill.PASS{background:var(--pass-bg);color:var(--pass)}
.pill.FAIL{background:var(--fail-bg);color:var(--fail)}
.pill.NEEDS_HUMAN{background:var(--human-bg);color:var(--human)}
.pill.NOT_VERIFIABLE{background:var(--na-bg);color:var(--na)}
.pill.CONFIG_OK,.pill.KEY_NOT_USED,.pill.BLOCKED{background:var(--warn-bg);color:var(--warn)}
.detail{display:none;padding:4px 16px 16px 110px;gap:14px;grid-template-columns:1fr 1fr}
.row.open .detail{display:grid}
@media (max-width:760px){.detail{grid-template-columns:1fr;padding-left:16px}}
.detail h4{margin:0 0 4px;font:500 11.5px "IBM Plex Mono",monospace;letter-spacing:.06em;
  text-transform:uppercase;color:var(--muted)}
.detail .box{font-size:14px}
.detail .pre{white-space:pre-wrap;font:12.5px/1.5 "IBM Plex Mono",monospace;background:var(--code);
  border-radius:6px;padding:8px 10px;max-height:180px;overflow:auto}
.detail .full{grid-column:1/-1}
.exp{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:6px;font-size:14px}
.exp li{display:grid;grid-template-columns:132px 1fr;gap:8px;align-items:start}
.exp .why{color:var(--muted);font-size:13px;display:block;margin-top:2px}
.shots{display:flex;gap:12px;overflow-x:auto;padding-bottom:4px}
figure{margin:0;display:flex;flex-direction:column;gap:6px;flex:0 0 auto;width:168px}
figure img{width:100%;height:auto;border:1px solid var(--rule);border-radius:6px;display:block}
figure.blocked img{outline:2px solid var(--warn);outline-offset:-2px}
figcaption{color:var(--muted);font-size:12.5px;line-height:1.35}
figcaption .k{color:var(--accent);text-transform:uppercase;letter-spacing:.05em;font-size:11px}
.ads{width:100%;border-collapse:collapse}
.ads th,.ads td{text-align:left;padding:4px 12px 4px 0;font-size:12.5px;
  border-bottom:1px solid var(--rule);white-space:nowrap}
.ads th{font:500 11px "IBM Plex Mono",monospace;text-transform:uppercase;
  letter-spacing:.06em;color:var(--muted)}
.num2{font-variant-numeric:tabular-nums}
.tag{font:500 11px "IBM Plex Mono",monospace;color:var(--muted);border:1px dashed var(--rule);padding:3px 6px;border-radius:5px;white-space:nowrap}
.empty{padding:16px;color:var(--muted)}
details.find{background:var(--paper);border:1px solid var(--rule);border-radius:10px;padding:12px 16px}
details.find summary{cursor:pointer;font-weight:600}
details.find ul{margin:10px 0 0;padding-left:18px;display:flex;flex-direction:column;
  gap:8px;font-size:14px;max-width:80ch}
"""
