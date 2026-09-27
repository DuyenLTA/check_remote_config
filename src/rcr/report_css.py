"""CSS cua report. Tach khoi report_html de moi file duoi 200 dong.

Bo cuc BANG TEST CASE (tester chot 2026-09-27): mot case mot HANG, cac cot
Case / Mo ta / Precondition / Step / Expected / Actual / Status nam canh nhau.
Doc ngang mot hang la thay du "dang le phai the nao" va "thuc te ra sao" - khong
phai bam mo tung case roi tu ghep lai trong dau.

Mau theo vai tro, moi verdict mot mau co dinh - nhin quen mat roi thi khong
phai doc chu. Verdict la tren mot muc "khong do duoc" deu dung mau trung tinh.
"""

CSS = """
:root{
  --ground:#f2f4f7; --paper:#fff; --ink:#17202b; --muted:#5a6677; --faint:#8791a1;
  --rule:#dfe3ea; --hover:#f6f8fb; --accent:#2c5fb8; --code:#eef1f6;
  --pass:#1d7a4c; --pass-bg:#e2f3e9; --fail:#b3261e; --fail-bg:#fbe6e4;
  --human:#6b3fb5; --human-bg:#efe8fb; --na:#4b5563; --na-bg:#e8ebef;
  --warn:#8a5a00; --warn-bg:#fcf0d6;
  --shadow:0 1px 2px rgba(20,26,44,.06),0 8px 24px -14px rgba(20,26,44,.14);
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    color-scheme:dark;
    --ground:#0c1017; --paper:#151b24; --ink:#e3e8ef; --muted:#97a2b2; --faint:#6b7687;
    --rule:#29313c; --hover:#1c232d; --accent:#80a8ee; --code:#222a35;
    --pass:#6fd19e; --pass-bg:#15301f; --fail:#f28b82; --fail-bg:#3a1b19;
    --human:#c3a6f5; --human-bg:#2c2240; --na:#b6bfcb; --na-bg:#262d37;
    --warn:#f2c46b; --warn-bg:#352a12;
    --shadow:0 1px 2px rgba(0,0,0,.3),0 12px 32px -16px rgba(0,0,0,.6);
  }
}
:root[data-theme="dark"]{
  color-scheme:dark;
  --ground:#0c1017; --paper:#151b24; --ink:#e3e8ef; --muted:#97a2b2; --faint:#6b7687;
  --rule:#29313c; --hover:#1c232d; --accent:#80a8ee; --code:#222a35;
  --pass:#6fd19e; --pass-bg:#15301f; --fail:#f28b82; --fail-bg:#3a1b19;
  --human:#c3a6f5; --human-bg:#2c2240; --na:#b6bfcb; --na-bg:#262d37;
  --warn:#f2c46b; --warn-bg:#352a12;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 12px 32px -16px rgba(0,0,0,.6);
}
*{box-sizing:border-box}
body{background:var(--ground);color:var(--ink);margin:0;
  font:14px/1.55 "IBM Plex Sans",system-ui,-apple-system,sans-serif;
  padding:26px 16px 60px;-webkit-font-smoothing:antialiased}
.wrap{max-width:1420px;margin:0 auto;display:flex;flex-direction:column;gap:18px}
h1{margin:0;font-size:25px;font-weight:600;letter-spacing:-.01em;text-wrap:balance}
p{margin:0}
code,.mono{font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace;font-size:.86em}
code{background:var(--code);padding:1px 5px;border-radius:4px;overflow-wrap:anywhere}
.eyebrow{font:500 11.5px/1 "IBM Plex Mono",monospace;letter-spacing:.1em;
  text-transform:uppercase;color:var(--accent)}
header{display:flex;flex-wrap:wrap;gap:16px;align-items:flex-end;
  justify-content:space-between;border-bottom:1px solid var(--rule);padding-bottom:14px}
.htxt{display:flex;flex-direction:column;gap:6px}
.sub{color:var(--muted);font-size:13px;max-width:70ch}
.meta{display:flex;flex-wrap:wrap;gap:3px 18px;color:var(--muted);font-size:12.5px}
.meta b{color:var(--ink);font-weight:500;overflow-wrap:anywhere}
.warn{background:var(--warn-bg);color:var(--ink);border-left:3px solid var(--warn);
  border-radius:0 8px 8px 0;padding:11px 14px;font-size:13px}
.warn b:first-child{color:var(--warn)}
.warn ul{margin:7px 0 0;padding-left:18px;display:flex;flex-direction:column;gap:6px;max-width:100ch}
.tally{display:flex;flex-wrap:wrap;gap:8px}
.tile{background:var(--paper);border:1px solid var(--rule);border-radius:10px;
  padding:9px 15px;min-width:86px;text-align:center;box-shadow:var(--shadow);
  cursor:pointer;font:inherit;color:inherit}
.tile .num{font:600 20px/1.2 "IBM Plex Mono",monospace;font-variant-numeric:tabular-nums;display:block}
.tile .lab{font-size:10.5px;text-transform:uppercase;letter-spacing:.07em;color:var(--faint)}
.tile[aria-pressed="true"]{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent)}
.tile.PASS .num{color:var(--pass)} .tile.FAIL .num{color:var(--fail)}
.tile.NEEDS_HUMAN .num{color:var(--human)} .tile.NOT_VERIFIABLE .num{color:var(--na)}
.bar{display:flex;flex-wrap:wrap;gap:9px;align-items:center;background:var(--paper);
  border:1px solid var(--rule);border-radius:10px;padding:9px 11px;box-shadow:var(--shadow)}
.bar input,.bar select{background:var(--ground);border:1px solid var(--rule);border-radius:8px;
  padding:7px 11px;color:var(--ink);font:inherit;font-size:13px}
.bar input{flex:1 1 220px;min-width:160px}
.bar .count{margin-left:auto;font:12px "IBM Plex Mono",monospace;color:var(--faint)}
.linkbtn{background:none;border:1px solid var(--rule);border-radius:8px;padding:7px 11px;
  color:var(--accent);font:inherit;font-size:13px;cursor:pointer}
.tablewrap{background:var(--paper);border:1px solid var(--rule);border-radius:12px;
  box-shadow:var(--shadow);overflow-x:auto}
table{border-collapse:collapse;width:100%;min-width:1180px}
thead th{position:sticky;top:0;z-index:1;background:var(--hover);text-align:left;
  font:600 10.5px/1.4 "IBM Plex Sans",sans-serif;text-transform:uppercase;letter-spacing:.07em;
  color:var(--faint);padding:10px 13px;border-bottom:1px solid var(--rule);white-space:nowrap}
tbody td{padding:13px;border-bottom:1px solid var(--rule);vertical-align:top;font-size:12.8px}
tbody tr:last-child td{border-bottom:none}
tbody tr:hover{background:var(--hover)}
tbody tr.FAIL td:first-child{box-shadow:inset 3px 0 0 var(--fail)}
tr.ghead td{background:var(--code);font:600 11px/1.4 "IBM Plex Sans",sans-serif;
  text-transform:uppercase;letter-spacing:.07em;color:var(--muted);padding:8px 13px}
.c-case{width:110px}
.code{display:block;font:600 12.5px "IBM Plex Mono",monospace;color:var(--accent)}
.feat{display:block;margin-top:3px;font-size:10.5px;letter-spacing:.05em;color:var(--faint)}
.c-desc{width:200px} .c-pre{width:180px;color:var(--muted)}
.c-step{width:210px} .c-exp{width:230px} .c-act{width:330px} .c-st{width:92px;text-align:center}
.lab{font-weight:600;display:block;margin-bottom:4px}
.cfg{display:flex;flex-direction:column;gap:2px;margin-top:6px}
.pre{white-space:pre-wrap;font-size:12px}
ol.steps{margin:0;padding-left:17px;display:flex;flex-direction:column;gap:6px;color:var(--muted)}
ol.steps li::marker{font-family:"IBM Plex Mono",monospace;color:var(--accent)}
ol.steps li.needs_human{color:var(--human)}
.k{font:500 9.5px "IBM Plex Mono",monospace;padding:2px 5px;border-radius:4px;
  background:var(--code);color:var(--faint);margin-left:5px;white-space:nowrap}
.k.needs_human{background:var(--human-bg);color:var(--human)}
.k.blocked{background:var(--warn-bg);color:var(--warn)}
ol.acts{margin:0;padding-left:17px;display:flex;flex-direction:column;gap:8px}
ol.acts li::marker{font-family:"IBM Plex Mono",monospace;color:var(--faint)}
.why{color:var(--muted);font-size:12px;display:block;margin-top:2px}
.pill{display:inline-block;font:600 10px/1 "IBM Plex Mono",monospace;padding:4px 7px;
  border-radius:999px;background:var(--na-bg);color:var(--na);border:1px solid transparent;
  white-space:nowrap}
.pill.PASS{background:var(--pass-bg);color:var(--pass)}
.pill.FAIL{background:var(--fail-bg);color:var(--fail)}
.pill.NEEDS_HUMAN{background:var(--human-bg);color:var(--human)}
.pill.CONFIG_OK,.pill.KEY_NOT_USED,.pill.BLOCKED{background:var(--warn-bg);color:var(--warn)}
.reason{margin-top:9px;background:var(--fail-bg);border:1px solid var(--fail);border-radius:8px;
  padding:8px 10px;font-size:12px}
.reason .rl{display:block;font:600 9.5px "IBM Plex Mono",monospace;letter-spacing:.07em;
  text-transform:uppercase;color:var(--fail);margin-bottom:3px}
table.ads{min-width:0;width:100%;margin-top:9px;font-size:11.5px;border:1px solid var(--rule);
  border-radius:6px;overflow:hidden}
table.ads th,table.ads td{padding:4px 7px;border-bottom:1px solid var(--rule);white-space:nowrap}
table.ads th{position:static;background:var(--code);font-size:9.5px}
table.ads td.n{text-align:right;font-family:"IBM Plex Mono",monospace}
.shots{display:flex;flex-wrap:wrap;gap:7px;margin-top:9px}
.shot{display:flex;flex-direction:column;gap:3px;color:var(--muted);font-size:10px;
  max-width:74px;cursor:zoom-in}
.shot img{width:74px;border:1px solid var(--rule);border-radius:5px;display:block}
.shot img.blocked{outline:2px solid var(--warn);outline-offset:-2px}
.shot:has(input:checked){max-width:none;cursor:zoom-out}
.shot input:checked ~ img{width:min(320px,78vw)}
details.find{background:var(--paper);border:1px solid var(--rule);border-radius:10px;padding:12px 15px}
details.find summary{cursor:pointer;font-weight:500}
details.find ul{margin:9px 0 0;padding-left:18px;display:flex;flex-direction:column;gap:7px;
  color:var(--muted);font-size:13px;max-width:100ch}
.foot{color:var(--faint);font:12px "IBM Plex Mono",monospace;text-align:center}
@media (max-width:640px){body{padding:18px 12px 48px}header{flex-direction:column;align-items:flex-start}}
"""
