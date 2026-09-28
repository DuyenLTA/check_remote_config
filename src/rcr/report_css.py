"""CSS cua trang report. Tach rieng de sua bo cuc khong dung toi logic.

Bo cuc theo mau tester chot 2026-09-28: the tong ket bam de loc, khoi "can xu
ly" o dau trang, danh sach case gap/mo theo nhom - KHONG phai bang ngang.
Bang ngang bat nguoi doc keo ngang de doc het mot case; danh sach gap cho thay
toan canh truoc, chi tiet khi can.

Mau va bien theo `prefers-color-scheme` lan `[data-theme]`: report duoc mo tren
may nguoi khac, khong the gia dinh ho dung theme sang.
"""

CSS = """
:root{
  --ground:#f2f4f7; --paper:#fff; --ink:#17202b; --muted:#5a6677; --rule:#dfe3ea; --hover:#f6f8fb;
  --accent:#2c5fb8; --code:#eef1f6;
  --pass:#1d7a4c; --pass-bg:#e2f3e9; --fail:#b3261e; --fail-bg:#fbe6e4;
  --block:#8a5a00; --block-bg:#fcf0d6; --na:#4b5563; --na-bg:#e8ebef; --fix:#6b3fb5; --fix-bg:#efe8fb;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    color-scheme:dark;
    --ground:#10141a; --paper:#171d25; --ink:#e3e8ef; --muted:#97a2b2; --rule:#29313c; --hover:#1d242e;
    --accent:#80a8ee; --code:#222a35;
    --pass:#6fd19e; --pass-bg:#15301f; --fail:#f28b82; --fail-bg:#3a1b19;
    --block:#f2c46b; --block-bg:#352a12; --na:#b6bfcb; --na-bg:#262d37; --fix:#c3a6f5; --fix-bg:#2c2240;
  }
}
:root[data-theme="dark"]{
  color-scheme:dark;
  --ground:#10141a; --paper:#171d25; --ink:#e3e8ef; --muted:#97a2b2; --rule:#29313c; --hover:#1d242e;
  --accent:#80a8ee; --code:#222a35;
  --pass:#6fd19e; --pass-bg:#15301f; --fail:#f28b82; --fail-bg:#3a1b19;
  --block:#f2c46b; --block-bg:#352a12; --na:#b6bfcb; --na-bg:#262d37; --fix:#c3a6f5; --fix-bg:#2c2240;
}
*{box-sizing:border-box}
body{background:var(--ground);color:var(--ink);font:15px/1.55 "IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;padding:24px 16px 64px}
.wrap{max-width:1040px;margin:0 auto;display:flex;flex-direction:column;gap:20px}
h1,h2,h3{margin:0;text-wrap:balance;font-weight:600}
h1{font-size:26px;letter-spacing:-.01em}
h2{font-size:17px}
p{margin:0}
code,.mono{font-family:"IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace;font-size:.86em}
code{background:var(--code);padding:1px 5px;border-radius:4px}
.eyebrow{font:500 12px/1 "IBM Plex Mono",monospace;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.meta{display:flex;flex-wrap:wrap;gap:4px 18px;color:var(--muted);font-size:13px}
.meta b{color:var(--ink);font-weight:500}
.warn{background:var(--block-bg);color:var(--block);padding:8px 12px;border-radius:6px;font-size:13.5px}
.card{background:var(--paper);border:1px solid var(--rule);border-radius:10px;padding:16px}
.tally{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
.tile{border:1px solid var(--rule);border-radius:10px;background:var(--paper);padding:12px 14px;text-align:left;cursor:pointer;font:inherit;color:inherit;display:flex;flex-direction:column;gap:2px}
.tile:hover{background:var(--hover)}
.tile[aria-pressed="true"]{outline:2px solid var(--accent);outline-offset:-2px}
.tile .num{font:600 28px/1.1 "IBM Plex Mono",monospace;font-variant-numeric:tabular-nums}
.tile .lab{font-size:13px;color:var(--muted)}
.tile.PASS .num{color:var(--pass)} .tile.FAIL .num{color:var(--fail)}
.tile.BLOCKED .num{color:var(--block)} .tile.NA .num{color:var(--na)}
@media (max-width:620px){.tally{grid-template-columns:repeat(2,1fr)}}
.todo{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}
.todo h3{font-size:14px;margin-bottom:6px}
.todo ul{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:6px}
.todo li{font-size:14px;display:flex;gap:8px;align-items:baseline}
.todo .none{color:var(--muted);font-size:13.5px}
.jump{font:500 12.5px "IBM Plex Mono",monospace;color:var(--accent);background:none;border:0;padding:0;cursor:pointer;white-space:nowrap}
.jump:hover{text-decoration:underline}
.bar{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:var(--ground);padding:10px 0;display:flex;flex-wrap:wrap;gap:8px;align-items:center;border-bottom:1px solid var(--rule)}
.chip{font:500 13px "IBM Plex Sans",sans-serif;border:1px solid var(--rule);background:var(--paper);color:var(--ink);border-radius:999px;padding:5px 12px;cursor:pointer}
.chip[aria-pressed="true"]{background:var(--ink);color:var(--paper);border-color:var(--ink)}
.search{flex:1;min-width:180px;font:inherit;border:1px solid var(--rule);background:var(--paper);color:var(--ink);border-radius:8px;padding:6px 10px}
.bar .count{font-size:13px;color:var(--muted);margin-left:auto}
.linkbtn{font:500 13px "IBM Plex Sans",sans-serif;background:none;border:0;color:var(--accent);cursor:pointer;padding:4px 2px}
.group{display:flex;flex-direction:column;gap:0;background:var(--paper);border:1px solid var(--rule);border-radius:10px;overflow:hidden}
.ghead{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;align-items:baseline;padding:12px 16px}
.gcount{display:flex;gap:6px;flex-wrap:wrap}
.row{border-top:1px solid var(--rule);scroll-margin-top:72px}
.rowbtn{all:unset;box-sizing:border-box;width:100%;cursor:pointer;display:grid;grid-template-columns:44px 92px 1fr 16px;gap:10px;align-items:start;padding:10px 16px}
.rowbtn:hover{background:var(--hover)}
.rowbtn:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}
.n{font:500 13px "IBM Plex Mono",monospace;color:var(--muted);padding-top:2px}
.t{display:flex;flex-direction:column;gap:2px;min-width:0}
.t b{font-weight:500}
.t span{color:var(--muted);font-size:13.5px;overflow:hidden;text-overflow:ellipsis;display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical}
.chev{color:var(--muted);transition:transform .15s;padding-top:2px}
.row.open .chev{transform:rotate(90deg)}
.row.open .t span{-webkit-line-clamp:unset}
@media (max-width:560px){.rowbtn{grid-template-columns:36px 1fr 14px}.rowbtn .pill{grid-column:2;justify-self:start;order:-1}}
.pill{display:inline-block;font:500 12px/1 "IBM Plex Mono",monospace;padding:5px 8px;border-radius:999px;white-space:nowrap;text-align:center}
.pill.PASS{background:var(--pass-bg);color:var(--pass)} .pill.FAIL{background:var(--fail-bg);color:var(--fail)}
.pill.BLOCKED{background:var(--block-bg);color:var(--block)} .pill.NA{background:var(--na-bg);color:var(--na)}
.pill.FIX{background:var(--fix-bg);color:var(--fix)}
.detail{display:none;padding:4px 16px 16px 70px;gap:14px;grid-template-columns:1fr 1fr}
.row.open .detail{display:grid}
@media (max-width:760px){.detail{grid-template-columns:1fr;padding-left:16px}}
.detail h4{margin:0 0 4px;font:500 11.5px "IBM Plex Mono",monospace;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.detail ol{margin:0;padding-left:20px;display:flex;flex-direction:column;gap:8px;font-size:14px}
.detail .box{font-size:14px}
.detail .pre{white-space:pre-wrap;font:12.5px/1.5 "IBM Plex Mono",monospace;background:var(--code);border-radius:6px;padding:8px 10px;max-height:200px;overflow:auto}
.detail .full{grid-column:1/-1}
.why{display:block;color:var(--muted);font-size:13px;margin-top:2px}
.exp{display:flex;flex-direction:column;gap:3px}
.exp .pill{align-self:flex-start}
table.ads{width:100%;border-collapse:collapse;font-size:13px}
table.ads th,table.ads td{text-align:left;padding:4px 8px;border-bottom:1px solid var(--rule)}
table.ads td.num{font-family:"IBM Plex Mono",monospace;font-variant-numeric:tabular-nums;text-align:right}
table.ads th{color:var(--muted);font-weight:500}
.shots{display:flex;gap:10px;overflow-x:auto;padding-bottom:4px}
figure{margin:0;display:flex;flex-direction:column;gap:6px}
figure img{max-width:100%;height:auto;border:1px solid var(--rule);border-radius:6px}
figcaption{color:var(--muted);font-size:13px}
.shots figure{flex:0 0 132px}
.shots img{width:132px}
.empty{padding:16px;color:var(--muted)}
details.find{background:var(--paper);border:1px solid var(--rule);border-radius:10px;padding:12px 16px}
details.find summary{cursor:pointer;font-weight:600}
details.find ul{margin:10px 0 0;padding-left:18px;display:flex;flex-direction:column;gap:8px;font-size:14px;max-width:80ch}
.foot{color:var(--muted);font-size:13px;text-align:center}
"""
