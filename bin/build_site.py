#!/usr/bin/env python3
"""渲染单页应用：条目池 + 自选简报。

设计系统：DESIGNmd / chef/violet-issue（MIT）
https://designmd.ai/chef/violet-issue

原则：机器不替人筛。
- 抓回来的全部条目原样呈现
- 提供筛选、搜索、排序、勾选，决定权在人
- 勾选结果在浏览器里保存，可导出 Markdown

数据源：data/items.json
输出：out/index.html（单文件，无外部依赖）
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "out"

E = html.escape

CSS = """
:root{
  --bg:#101014; --card:#1B1B25; --surface:#1F1F2E; --surface-2:#252536;
  --primary:#5E6AD2; --primary-hover:#4E5BBF; --primary-soft:rgba(94,106,210,.10);
  --primary-ring:rgba(94,106,210,.15);
  --text:#F1F1F4; --muted:#8A8F98; --border:#2C2C3A;
  --success:#3DD68C; --warning:#F0C000; --error:#EB5757;
  --sans:"Inter",-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
  --mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Consolas,monospace;
}
*{box-sizing:border-box}
html,body{margin:0}
body{background:var(--bg);color:var(--text);font:400 14px/1.5 var(--sans);
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
a{color:inherit;text-decoration:none}
button,input,select{font-family:inherit}

.topbar{position:sticky;top:0;z-index:20;background:var(--card);border-bottom:1px solid var(--border)}
.topbar .inner{max-width:1180px;margin:0 auto;padding:0 24px;height:48px;display:flex;align-items:center;gap:12px}
.logo{width:8px;height:8px;border-radius:9999px;background:var(--primary);flex:none;
  box-shadow:0 0 24px var(--primary-ring)}
.brand{font:500 13px/1 var(--sans)}
.brand span{color:var(--muted);font-weight:400}

.seg{margin-left:auto;display:flex;border:1px solid var(--border);border-radius:6px;overflow:hidden}
.seg button{height:28px;padding:0 12px;border:0;background:transparent;color:var(--muted);
  font:500 13px/1 var(--sans);cursor:pointer;transition:background .1s linear}
.seg button+button{border-left:1px solid var(--border)}
.seg button:hover{color:var(--text);background:var(--surface)}
.seg button.on{background:var(--primary-soft);color:var(--text)}
.seg button:focus-visible{outline:none;box-shadow:inset 0 0 0 2px var(--primary-ring)}
.seg .cnt{font:400 11px/1 var(--mono);color:var(--muted);margin-left:4px}

.strip{background:var(--bg);border-bottom:1px solid var(--border)}
.strip .inner{max-width:1180px;margin:0 auto;padding:12px 24px;display:flex;gap:24px;flex-wrap:wrap}
.stat{display:flex;align-items:baseline;gap:8px}
.stat .k{font:600 11px/1 var(--sans);letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}
.stat .v{font:500 13px/1 var(--mono);color:var(--text)}
.stat .v.dim{color:var(--muted)}
.stat .v.warn{color:var(--warning)}

.wrap{max-width:1180px;margin:0 auto;padding:0 24px}
.main{padding:24px 0 64px}

.bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:12px}
.inp,.sel{height:28px;padding:0 10px;background:var(--card);border:1px solid var(--border);
  border-radius:6px;color:var(--text);font:400 13px/1 var(--sans);outline:none}
.inp::placeholder{color:var(--muted)}
.inp:focus,.sel:focus{border-color:var(--primary);box-shadow:0 0 0 2px var(--primary-ring)}
.inp.q{width:240px}
.tog{height:28px;padding:0 12px;border:1px solid var(--border);border-radius:6px;background:transparent;
  color:var(--muted);font:500 13px/1 var(--sans);cursor:pointer;transition:background .1s linear}
.tog:hover{color:var(--text);background:var(--surface)}
.tog.on{background:var(--primary-soft);border-color:var(--primary);color:var(--text)}
.tog:focus-visible{outline:none;box-shadow:0 0 0 2px var(--primary-ring)}
.bar .sp{margin-left:auto}
.btn{height:28px;padding:0 12px;border:1px solid var(--border);border-radius:6px;background:transparent;
  color:var(--muted);font:500 13px/1 var(--sans);cursor:pointer;transition:background .1s linear}
.btn:hover{color:var(--text);background:var(--surface);border-color:var(--muted)}
.btn:focus-visible{outline:none;box-shadow:0 0 0 2px var(--primary-ring)}
.btn.primary{background:var(--primary);border-color:var(--primary);color:#fff}
.btn.primary:hover{background:var(--primary-hover);border-color:var(--primary-hover);color:#fff}
.btn:disabled{opacity:.4;cursor:default}

.list{border:1px solid var(--border);border-radius:8px;overflow:hidden;background:var(--card)}
.row{display:grid;grid-template-columns:24px 92px 1fr 84px 20px;gap:12px;align-items:start;
  padding:10px 16px;border-bottom:1px solid rgba(44,44,58,.5);transition:background .1s linear}
.row:last-child{border-bottom:none}
.row:hover{background:var(--surface)}
.row.sel{background:var(--primary-soft);box-shadow:inset 2px 0 0 var(--primary)}
.ck{width:16px;height:16px;margin-top:2px;border:1.5px solid var(--muted);border-radius:9999px;
  background:transparent;cursor:pointer;padding:0;display:flex;align-items:center;justify-content:center;
  transition:background .1s linear,border-color .1s linear;flex:none}
.ck:hover{border-color:var(--text)}
.ck.on{background:var(--primary);border-color:var(--primary)}
.ck.on::after{content:"";width:5px;height:8px;border:solid #fff;border-width:0 1.5px 1.5px 0;
  transform:rotate(45deg) translate(-1px,-1px)}
.ck:focus-visible{outline:none;box-shadow:0 0 0 2px var(--primary-ring)}
.src{font:400 11px/1.5 var(--sans);color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.src.official{color:var(--success)}
.src.aggregator{color:var(--primary)}
.t{min-width:0}
.t .ti{font:500 14px/1.4 var(--sans);color:var(--text)}
.t .ti:hover{color:var(--primary)}
.t .sm{font:400 12px/1.5 var(--sans);color:var(--muted);margin-top:2px;
  display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical;overflow:hidden}
.d{font:400 11px/1.5 var(--mono);color:var(--muted);text-align:right;white-space:nowrap}
.d.none{color:var(--warning)}
.ext{color:var(--border);font-size:13px;line-height:1.5}
.ext:hover{color:var(--primary)}
.empty{padding:40px;text-align:center;color:var(--muted);font:400 13px/1.6 var(--sans)}

.stage{display:grid;grid-template-columns:220px 1fr;gap:24px}
.side{position:sticky;top:96px;align-self:start}
.side-h{font:600 11px/1 var(--sans);letter-spacing:.05em;text-transform:uppercase;
  color:var(--muted);padding:0 8px;margin-bottom:8px}
.navitem{display:grid;grid-template-columns:20px 1fr;gap:8px;align-items:start;
  padding:8px 8px 8px 10px;border-radius:8px;border-left:2px solid transparent;
  cursor:pointer;margin-bottom:2px;transition:background .1s linear}
.navitem:hover{background:var(--surface)}
.navitem.active{background:var(--primary-soft);border-left-color:var(--primary)}
.navitem .n{font:400 11px/1.6 var(--mono);color:var(--muted)}
.navitem.active .n{color:var(--primary)}
.navitem .nt{font:400 13px/1.4 var(--sans);color:var(--muted);
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.navitem.active .nt{color:var(--text);font-weight:500}

.panel{background:var(--card);border:1px solid var(--border);border-radius:8px;
  min-height:420px;display:flex;flex-direction:column}
.slide{display:none;padding:32px;flex:1}
.slide.active{display:block;animation:in .12s ease-out}
@keyframes in{from{opacity:0}to{opacity:1}}
.smeta{display:flex;align-items:center;gap:8px;margin-bottom:16px}
.chip{height:20px;display:inline-flex;align-items:center;padding:0 8px;border-radius:4px;
  font:500 11px/1 var(--sans)}
.chip.official{color:var(--success);background:rgba(61,214,140,.20)}
.chip.media{color:var(--warning);background:rgba(240,192,0,.20)}
.chip.aggregator{color:var(--primary);background:rgba(94,106,210,.20)}
.status{margin-left:auto;font:400 12px/1 var(--sans);color:var(--muted)}
.slide h1{font:600 20px/1.35 var(--sans);letter-spacing:-.03em;margin:0 0 20px}
.blk .k{font:600 11px/1 var(--sans);letter-spacing:.05em;text-transform:uppercase;
  color:var(--muted);margin-bottom:6px}
.blk .v{font:400 14px/1.7 var(--sans);color:#C9CCD6}
.srcs{display:flex;flex-wrap:wrap;gap:8px 16px;margin-top:24px;padding-top:16px;
  border-top:1px solid var(--border)}
.srcs a{font:400 12px/1 var(--sans);color:var(--primary)}
.srcs a:hover{color:var(--primary-hover);text-decoration:underline}
.pager{display:flex;align-items:center;gap:8px;padding:12px 16px;border-top:1px solid var(--border)}
.pos{margin-left:auto;font:400 11px/1 var(--mono);color:var(--muted)}

footer{border-top:1px solid var(--border);padding:16px 0 40px}
footer .inner{max-width:1180px;margin:0 auto;padding:0 24px;display:flex;gap:16px;flex-wrap:wrap;
  font:400 12px/1.6 var(--sans);color:var(--muted)}
footer a{color:var(--primary)}

.hide{display:none!important}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
@media (max-width:900px){
  .wrap,.topbar .inner,.strip .inner,footer .inner{padding-left:16px;padding-right:16px}
  .stage{grid-template-columns:1fr}
  .side{position:static;display:flex;gap:4px;overflow-x:auto;padding-bottom:4px}
  .side-h{display:none}
  .navitem{grid-template-columns:1fr;min-width:150px;margin:0}
  .navitem .n{display:none}
  .row{grid-template-columns:24px 1fr;row-gap:4px}
  .row .src,.row .d,.row .ext{display:none}
  .inp.q{width:100%}
  .slide{padding:20px}
  .slide h1{font-size:16px}
}
"""

JS = r"""
var ALL = window.__ITEMS__ || [];
var KEY = 'aiintel.sel.v1';
var sel = new Set();
try { sel = new Set(JSON.parse(localStorage.getItem(KEY) || '[]')); } catch (e) {}

var state = { q: '', src: 'all', official: false, dated: false, sort: 'time', mode: 'pool', cur: 0 };

function save() {
  try { localStorage.setItem(KEY, JSON.stringify([].concat(Array.from(sel)))); } catch (e) {}
}
function key(it) { return it.url; }
function fmtDate(s) { return s ? s.slice(0, 10) : '无日期'; }
// 源的层级不是二分的：官方一手 > 媒体采写 > 聚合转述。
// 聚合源（AIHOT、橘鸦）是对别人的再筛选，只能当线索，不能当事实依据。
function tierName(t, short) {
  if (t === 'official') return short ? '官方' : '官方源';
  if (t === 'aggregator') return short ? '聚合' : '聚合源';
  return short ? '媒体' : '媒体源';
}
function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
  });
}

function visible() {
  var q = state.q.trim().toLowerCase();
  var out = ALL.filter(function (it) {
    if (state.official && it.tier !== 'official') return false;
    if (state.dated && !it.published) return false;
    if (state.src !== 'all' && it.source_id !== state.src) return false;
    if (q) {
      var hay = (it.title + ' ' + (it.summary || '') + ' ' + it.source_name).toLowerCase();
      if (hay.indexOf(q) === -1) return false;
    }
    return true;
  });
  if (state.sort === 'time') {
    out.sort(function (a, b) {
      if (!a.published && !b.published) return 0;
      if (!a.published) return 1;
      if (!b.published) return -1;
      return a.published < b.published ? 1 : -1;
    });
  } else if (state.sort === 'source') {
    out.sort(function (a, b) { return a.source_name.localeCompare(b.source_name, 'zh'); });
  }
  return out;
}

function renderPool() {
  var list = document.getElementById('list');
  var rows = visible();
  document.getElementById('shown').textContent = rows.length;
  document.getElementById('total').textContent = ALL.length;
  if (!rows.length) {
    list.innerHTML = '<div class="empty">没有匹配的条目。换个关键词，或关掉筛选条件。</div>';
    return;
  }
  list.innerHTML = rows.map(function (it) {
    var on = sel.has(key(it));
    return '<div class="row' + (on ? ' sel' : '') + '" data-k="' + esc(key(it)) + '">' +
      '<button class="ck' + (on ? ' on' : '') + '" role="checkbox" aria-checked="' + on +
        '" aria-label="选中：' + esc(it.title) + '"></button>' +
      '<div class="src ' + esc(it.tier) + '" title="' + esc(it.source_name) + '">' +
        esc(it.source_name) + '</div>' +
      '<div class="t"><a class="ti" href="' + esc(it.url) + '" target="_blank" rel="noopener">' +
        esc(it.title) + '</a>' +
        (it.summary ? '<div class="sm">' + esc(it.summary) + '</div>' : '') + '</div>' +
      '<div class="d' + (it.published ? '' : ' none') + '">' + fmtDate(it.published) + '</div>' +
      '<a class="ext" href="' + esc(it.url) + '" target="_blank" rel="noopener" aria-label="打开原文">↗</a>' +
      '</div>';
  }).join('');
}

function selectedItems() {
  return ALL.filter(function (it) { return sel.has(key(it)); });
}

function renderBrief() {
  var items = selectedItems();
  var side = document.getElementById('side');
  var panel = document.getElementById('panel');
  document.getElementById('selCount').textContent = items.length;
  document.getElementById('selStat').textContent = items.length;

  if (!items.length) {
    side.innerHTML = '<div class="side-h">你的简报</div>';
    panel.innerHTML = '<div class="empty">还没有选任何条目。<br>回到「条目池」，勾选你想留下的内容。</div>' +
      '<div class="pager"><span class="pos">0 / 0</span></div>';
    return;
  }
  if (state.cur >= items.length) state.cur = 0;

  side.innerHTML = '<div class="side-h">你的简报</div>' + items.map(function (it, k) {
    return '<a class="navitem' + (k === state.cur ? ' active' : '') + '" tabindex="0">' +
      '<span class="n">' + String(k + 1).padStart(2, '0') + '</span>' +
      '<span class="nt">' + esc(it.title) + '</span></a>';
  }).join('');

  panel.innerHTML = items.map(function (it, k) {
    return '<article class="slide' + (k === state.cur ? ' active' : '') + '">' +
      '<div class="smeta"><span class="chip ' + esc(it.tier) + '">' +
        tierName(it.tier) + '</span>' +
        '<span class="status">' + esc(it.source_name) + ' · ' + fmtDate(it.published) + '</span></div>' +
      '<h1>' + esc(it.title) + '</h1>' +
      '<div class="blk"><div class="k">摘要</div><div class="v">' +
        esc(it.summary || '该源未提供摘要，点下方链接看原文。') + '</div></div>' +
      '<div class="srcs"><a href="' + esc(it.url) + '" target="_blank" rel="noopener">打开原文 ↗</a>' +
        '<a href="#" data-unsel="' + esc(key(it)) + '">从简报移除</a></div>' +
      '</article>';
  }).join('') +
    '<div class="pager">' +
      '<button class="btn" id="prev"' + (state.cur === 0 ? ' disabled' : '') + '>← 上一条</button>' +
      '<button class="btn" id="next"' + (state.cur === items.length - 1 ? ' disabled' : '') + '>下一条 →</button>' +
      '<span class="pos" id="pos">' + String(state.cur).padStart(2, '0') + ' / ' +
        String(items.length - 1).padStart(2, '0') + '</span>' +
    '</div>';

  document.getElementById('prev').onclick = function () { state.cur--; renderBrief(); };
  document.getElementById('next').onclick = function () { state.cur++; renderBrief(); };
  var us = panel.querySelector('[data-unsel]');
  if (us) us.onclick = function (e) {
    e.preventDefault();
    sel.delete(us.getAttribute('data-unsel'));
    save(); renderBrief(); renderPool(); updateModeCount();
  };
}

function updateModeCount() {
  document.getElementById('selCount').textContent = sel.size;
  document.getElementById('selStat').textContent = sel.size;
}

function setMode(m) {
  state.mode = m;
  document.getElementById('poolView').classList.toggle('hide', m !== 'pool');
  document.getElementById('briefView').classList.toggle('hide', m !== 'brief');
  document.getElementById('mPool').classList.toggle('on', m === 'pool');
  document.getElementById('mBrief').classList.toggle('on', m === 'brief');
  if (m === 'pool') renderPool(); else renderBrief();
}

function exportMd() {
  var items = selectedItems();
  if (!items.length) { alert('还没有选任何条目'); return; }
  var lines = ['# AI 情报简报（自选 ' + items.length + ' 条）', '',
    '> 由 ai-intel 生成，筛选由人完成。', ''];
  items.forEach(function (it, k) {
    lines.push('## ' + (k + 1) + '. ' + it.title, '');
    lines.push('- 来源：' + it.source_name + '（' + tierName(it.tier, true) + '）');
    lines.push('- 时间：' + fmtDate(it.published));
    lines.push('- 链接：' + it.url);
    if (it.summary) lines.push('', it.summary);
    lines.push('');
  });
  var blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' });
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'briefing-' + new Date().toISOString().slice(0, 10) + '.md';
  a.click();
  URL.revokeObjectURL(a.href);
}

document.addEventListener('click', function (e) {
  var ck = e.target.closest('.ck');
  if (ck) {
    var row = ck.closest('.row');
    var k = row.getAttribute('data-k');
    if (sel.has(k)) sel.delete(k); else sel.add(k);
    save();
    ck.classList.toggle('on', sel.has(k));
    ck.setAttribute('aria-checked', sel.has(k));
    row.classList.toggle('sel', sel.has(k));
    updateModeCount();
    return;
  }
  var ni = e.target.closest('.navitem');
  if (ni) {
    var all = Array.prototype.slice.call(document.querySelectorAll('.navitem'));
    state.cur = all.indexOf(ni);
    renderBrief();
  }
});

document.getElementById('q').addEventListener('input', function (e) {
  state.q = e.target.value; renderPool();
});
document.getElementById('src').addEventListener('change', function (e) {
  state.src = e.target.value; renderPool();
});
document.getElementById('sort').addEventListener('change', function (e) {
  state.sort = e.target.value; renderPool();
});
document.getElementById('fOfficial').addEventListener('click', function (e) {
  state.official = !state.official;
  e.currentTarget.classList.toggle('on', state.official);
  e.currentTarget.setAttribute('aria-pressed', state.official);
  renderPool();
});
document.getElementById('fDated').addEventListener('click', function (e) {
  state.dated = !state.dated;
  e.currentTarget.classList.toggle('on', state.dated);
  e.currentTarget.setAttribute('aria-pressed', state.dated);
  renderPool();
});
document.getElementById('allVis').addEventListener('click', function () {
  visible().forEach(function (it) { sel.add(key(it)); });
  save(); renderPool(); updateModeCount();
});
document.getElementById('clear').addEventListener('click', function () {
  sel.clear(); save(); renderPool(); updateModeCount();
});
document.getElementById('mPool').addEventListener('click', function () { setMode('pool'); });
document.getElementById('mBrief').addEventListener('click', function () { setMode('brief'); });
document.getElementById('exp').addEventListener('click', exportMd);

document.addEventListener('keydown', function (e) {
  if (state.mode !== 'brief') return;
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
  var items = selectedItems();
  if (!items.length) return;
  if (e.key === 'ArrowRight' || e.key === 'j') { e.preventDefault(); if (state.cur < items.length - 1) { state.cur++; renderBrief(); } }
  if (e.key === 'ArrowLeft' || e.key === 'k') { e.preventDefault(); if (state.cur > 0) { state.cur--; renderBrief(); } }
});

renderPool();
updateModeCount();
"""


def build() -> Path:
    payload = json.loads((DATA / "items.json").read_text(encoding="utf-8"))
    items = payload["items"]
    stats = payload["stats"]

    slim = [
        {
            "title": it["title"],
            "url": it["url"],
            "published": it["published"],
            "source_id": it["source_id"],
            "source_name": it["source_name"],
            "tier": it["tier"],
            "summary": it.get("summary", ""),
        }
        for it in items
    ]

    sources = sorted({(it["source_id"], it["source_name"]) for it in items})
    opts = "".join(f'<option value="{E(sid)}">{E(name)}</option>' for sid, name in sources)

    page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark">
<title>ai-intel · 条目池</title>
<link rel="alternate" type="application/rss+xml" title="AI 情报池" href="feed.xml">
<style>{CSS}</style>
</head>
<body>

<div class="topbar"><div class="inner">
  <div class="logo"></div>
  <span class="brand">ai-intel <span>/ 条目池</span></span>
  <div class="seg">
    <button id="mPool" class="on" aria-pressed="true">条目池 <span class="cnt" id="total">{len(items)}</span></button>
    <button id="mBrief" aria-pressed="false">我的简报 <span class="cnt" id="selCount">0</span></button>
  </div>
</div></div>

<div class="strip"><div class="inner">
  <div class="stat"><span class="k">源</span><span class="v">{stats["sources_ok"]}/{stats["sources_total"]}</span></div>
  <div class="stat"><span class="k">抓取</span><span class="v">{stats["raw_items"]}</span></div>
  <div class="stat"><span class="k">当前显示</span><span class="v" id="shown">{len(items)}</span></div>
  <div class="stat"><span class="k">已选</span><span class="v" id="selStat">0</span></div>
  <div class="stat" style="margin-left:auto"><span class="k">窗口</span><span class="v dim">{payload["window_days"]} 天</span></div>
</div></div>

<div class="wrap main">

  <div id="poolView">
    <div class="bar">
      <input class="inp q" id="q" type="search" placeholder="搜标题、摘要、来源…" aria-label="搜索条目">
      <select class="sel" id="src" aria-label="按来源筛选">
        <option value="all">全部来源</option>{opts}
      </select>
      <select class="sel" id="sort" aria-label="排序方式">
        <option value="time">按时间</option>
        <option value="source">按来源</option>
      </select>
      <button class="tog" id="fOfficial" aria-pressed="false">只看官方源</button>
      <button class="tog" id="fDated" aria-pressed="false">只看有日期</button>
      <span class="sp"></span>
      <button class="btn" id="allVis">全选当前</button>
      <button class="btn" id="clear">清空</button>
      <button class="btn primary" id="exp">导出 Markdown</button>
    </div>
    <div class="list" id="list"></div>
  </div>

  <div id="briefView" class="hide">
    <div class="stage">
      <nav class="side" id="side" aria-label="已选条目"></nav>
      <section class="panel" id="panel" aria-live="polite"></section>
    </div>
  </div>

</div>

<footer><div class="inner">
  <span>机器不替你筛：全部 {len(items)} 条原样呈现，取舍由你决定</span>
  <span>设计系统：Violet Issue（DESIGNmd / MIT）</span>
  <span>改源 sources.toml · 重新抓取 python bin/fetch.py</span>
</div></footer>

<script>window.__ITEMS__ = {json.dumps(slim, ensure_ascii=False)};</script>
<script>{JS}</script>
</body>
</html>
"""
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "index.html"
    path.write_text(page, encoding="utf-8")
    print(f"渲染完成：{path}")
    print(f"条目池 {len(items)} 条 · 源 {len(sources)} 个 · {path.stat().st_size // 1024} KB")
    return path


if __name__ == "__main__":
    build()
