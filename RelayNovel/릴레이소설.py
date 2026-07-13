# -*- coding: utf-8 -*-
"""
릴레이 소설 — 단일 실행 파일 (HTML 내장, 추가 설치 없음)

- 실행하면 기본 브라우저에 UI 가 열립니다. (시작하기.vbs 로 더블클릭하면 검은 창 없음)
- [작성하기] 로 입력한 내용은 같은 폴더의 '소설.txt' 에 자동 저장됩니다.
- 각 줄의 [✕] 로 삭제할 수 있습니다(확인 팝업 표시).
- [▶ 이야기 실행] 으로 전체화면 타이핑 연출 재생.
- 브라우저 탭을 닫으면 서버는 잠시 후 스스로 종료됩니다.

파일 구성:  릴레이소설.py(이 파일) · 시작하기.vbs(실행) · 소설.txt(데이터)
"""
import os
import sys
import json
import time
import threading
import webbrowser
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = os.path.dirname(os.path.abspath(__file__))
STORY_FILE = os.environ.get("RELAY_STORY") or os.path.join(BASE, "소설.txt")

_state = {"last_ping": time.time(), "start": time.time()}

# ───────────────────────── 화면(HTML) 내장 ─────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="ko" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>릴레이 소설</title>
<script>
  /* FOUC 방지: CSS 적용 전에 테마부터 결정 (DESIGN.md §2.2) */
  (function(){
    try {
      var t = localStorage.getItem('relay:theme');
      document.documentElement.setAttribute('data-theme', (t === 'light') ? 'light' : 'dark');
    } catch(e) { document.documentElement.setAttribute('data-theme','dark'); }
  })();
</script>
<style>
  /* ===== 토큰 (DESIGN.md 부록 A) ===== */
  :root{
    --radius-1:6px; --radius-2:10px;
    --space-1:4px; --space-2:8px; --space-3:12px; --space-4:16px; --space-5:24px; --space-6:36px;
    --topbar-h:52px;
    --font:"Pretendard","Noto Sans KR","Apple SD Gothic Neo","맑은 고딕","Segoe UI",system-ui,sans-serif;
  }
  :root,[data-theme="dark"]{
    --bg-0:#010409; --bg-1:#0d1117; --bg-2:#161b22; --bg-3:#21262d;
    --border-1:#30363d; --border-2:#3d444d;
    --text-1:#f0f6fc; --text-2:#9198a1; --text-3:#656c76;
    --accent:#2f81f7; --accent-2:#58a6ff; --accent-dim:rgba(47,129,247,0.15);
    --primary:#238636; --primary-hover:#2ea043; --primary-text:#ffffff;
    --danger:#f85149; --warn:#d29922; --info:#58a6ff;
    --shadow-1:0 2px 10px rgba(1,4,9,0.6);
    --shadow-2:0 12px 40px rgba(1,4,9,0.7);
  }
  [data-theme="light"]{
    --bg-0:#eceef2; --bg-1:#f5f6f8; --bg-2:#ffffff; --bg-3:#f0f2f5;
    --border-1:#e3e7ee; --border-2:#d2d9e3;
    --text-1:#1f2733; --text-2:#5a6573; --text-3:#8c97a5;
    --accent:#2f6fed; --accent-2:#1f5fd6; --accent-dim:#e7f0ff;
    --primary:#2f6fed; --primary-hover:#1f5fd6; --primary-text:#ffffff;
    --danger:#d64545; --warn:#e8890c; --info:#2f6fed;
    --shadow-1:0 1px 3px rgba(20,30,50,0.08), 0 6px 20px rgba(20,30,50,0.05);
    --shadow-2:0 4px 12px rgba(20,30,50,0.12), 0 16px 48px rgba(20,30,50,0.10);
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg-1);color:var(--text-1);font-family:var(--font);
    font-size:14px;line-height:1.5;-webkit-font-smoothing:antialiased;}
  .topbar{position:fixed;top:0;left:0;right:0;height:var(--topbar-h);display:flex;align-items:center;gap:8px;
    padding:0 18px;background:var(--bg-2);border-bottom:1px solid var(--border-1);z-index:50;}
  /* 브랜드가 남는 공간을 먹고 줄어들도록 → 우측 버튼은 항상 보임 */
  .brand{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
    font-size:16px;font-weight:600;color:var(--text-1);}
  .btn{background:var(--bg-2);color:var(--text-1);border:1px solid var(--border-1);border-radius:var(--radius-1);
    padding:8px 14px;font:inherit;font-size:13px;font-weight:500;cursor:pointer;transition:.12s;white-space:nowrap;
    display:inline-flex;align-items:center;gap:6px;flex:0 0 auto;}
  .btn:hover{background:var(--bg-3);border-color:var(--border-2);}
  .btn.primary{background:var(--primary);border-color:var(--primary);color:var(--primary-text);font-weight:600;}
  .btn.primary:hover{background:var(--primary-hover);border-color:var(--primary-hover);}
  .btn.accent{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:600;}
  .btn.accent:hover{background:var(--accent-2);border-color:var(--accent-2);}
  .btn.ghost{background:transparent;border-color:transparent;color:var(--text-2);}
  .btn.ghost:hover{background:var(--bg-3);color:var(--text-1);}
  .btn.danger{background:transparent;border-color:var(--danger);color:var(--danger);}
  .btn.danger:hover{background:var(--danger);border-color:var(--danger);color:#fff;}
  /* 본문 폭 80% */
  .wrap{width:80%;max-width:1600px;margin:0 auto;padding:calc(var(--topbar-h) + 28px) 0 60px;}
  .card{background:var(--bg-2);border:1px solid var(--border-1);border-radius:var(--radius-2);box-shadow:var(--shadow-1);overflow:hidden;}
  .card-head{padding:22px 26px 10px;}
  .kicker{font-size:11px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:var(--text-3);}
  .card-h1{margin:6px 0 4px;font-size:24px;font-weight:700;color:var(--text-1);}
  .card-desc{margin:0;font-size:13px;color:var(--text-2);}
  .list{display:flex;flex-direction:column;gap:8px;padding:14px 26px;max-height:54vh;overflow:auto;}
  .entry{display:flex;gap:12px;align-items:baseline;padding:13px 14px;background:var(--bg-1);
    border:1px solid var(--border-1);border-radius:var(--radius-1);transition:.12s;}
  .entry:hover{background:var(--bg-3);border-color:var(--border-2);}
  .chip{flex:0 0 auto;background:var(--accent-dim);border:1px solid var(--accent);color:var(--accent-2);
    border-radius:12px;padding:2px 10px;font-size:12px;font-weight:600;}
  .txt{flex:1;font-size:15px;line-height:1.6;color:var(--text-1);word-break:break-word;}
  .del{flex:0 0 auto;align-self:center;width:28px;height:28px;display:flex;align-items:center;justify-content:center;
    background:transparent;border:1px solid transparent;border-radius:var(--radius-1);color:var(--text-3);
    font-size:14px;cursor:pointer;transition:.12s;}
  .entry:hover .del{color:var(--text-2);}
  .del:hover{color:#fff;background:var(--danger);border-color:var(--danger);}
  .empty{color:var(--text-2);font-size:14px;padding:30px 6px;text-align:center;}
  .bar{display:flex;align-items:center;gap:10px;padding:14px 26px 20px;border-top:1px solid var(--border-1);}
  input[type=text]{background:var(--bg-2);color:var(--text-1);border:1px solid var(--border-1);
    border-radius:var(--radius-1);padding:9px 12px;font:inherit;font-size:14px;outline:none;transition:.12s;}
  input[type=text]::placeholder{color:var(--text-3);}
  input[type=text]:focus{border-color:var(--accent);box-shadow:0 0 0 2px var(--accent-dim);}
  .overlay{position:fixed;inset:0;background:rgba(0,0,0,0.6);display:none;align-items:center;justify-content:center;padding:20px;z-index:100;}
  .overlay.on{display:flex;}
  .modal-box{background:var(--bg-1);border:1px solid var(--border-1);border-radius:var(--radius-2);box-shadow:var(--shadow-2);
    width:min(1000px,90vw);max-height:85vh;display:flex;flex-direction:column;overflow:hidden;
    transform:translateY(8px);opacity:0;transition:.15s;}
  .overlay.on .modal-box{transform:none;opacity:1;}
  .modal-box.sm{width:min(520px,92vw);}
  .modal-header{padding:var(--space-4) var(--space-5);border-bottom:1px solid var(--border-1);}
  .modal-header h2{margin:0;font-size:18px;font-weight:600;color:var(--text-1);}
  .modal-header .sub{margin:6px 0 0;font-size:13px;color:var(--text-2);}
  .modal-body{padding:var(--space-5);display:flex;flex-direction:column;gap:14px;}
  .modal-footer{padding:var(--space-3) var(--space-5);border-top:1px solid var(--border-1);display:flex;justify-content:flex-end;gap:var(--space-2);}
  .row{display:flex;align-items:center;gap:12px;}
  .lab{width:48px;font-size:13px;font-weight:600;color:var(--text-2);flex:0 0 auto;}
  #content{flex:1;}
  #charname{width:240px;flex:0 0 auto;}
  .count{font-size:12px;color:var(--text-3);flex:0 0 auto;}
  .count.warn{color:var(--warn);}
  .preview{font-size:12px;color:var(--text-3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
  .confirm-line{display:flex;gap:10px;align-items:baseline;background:var(--bg-2);border:1px solid var(--border-1);
    border-radius:var(--radius-1);padding:12px 14px;}
  .confirm-line .txt{font-size:15px;color:var(--text-1);}
  .switch{position:relative;display:inline-block;width:44px;height:24px;flex:0 0 auto;margin:0;}
  .switch input{opacity:0;width:0;height:0;}
  .slider{position:absolute;inset:0;background:var(--border-2);border-radius:999px;transition:.18s;cursor:pointer;}
  .slider::before{content:"";position:absolute;width:18px;height:18px;left:3px;top:3px;background:#fff;
    border-radius:50%;transition:.18s;box-shadow:0 1px 2px rgba(0,0,0,.3);}
  .switch input:checked + .slider{background:var(--accent);}
  .switch input:checked + .slider::before{transform:translateX(20px);}
  .toggle-label{font-size:14px;font-weight:600;color:var(--text-1);flex:0 0 auto;cursor:pointer;}
  .toasts{position:fixed;right:24px;bottom:24px;display:flex;flex-direction:column;gap:8px;z-index:200;}
  .toast{background:var(--bg-2);color:var(--text-1);border:1px solid var(--border-1);border-left:3px solid var(--info);
    border-radius:var(--radius-1);box-shadow:var(--shadow-1);padding:10px 14px;font-size:13px;min-width:220px;max-width:380px;transition:opacity .2s;}
  .toast.success{border-left-color:var(--accent);}
  .toast.error{border-left-color:var(--danger);}
  .toast.warn{border-left-color:var(--warn);}
  .play{position:fixed;inset:0;background:var(--bg-0);display:none;flex-direction:column;z-index:120;}
  .play.on{display:flex;}
  .play-top{display:flex;align-items:center;justify-content:space-between;padding:14px 20px;}
  .play-kicker{font-size:11px;letter-spacing:2px;text-transform:uppercase;color:var(--text-3);}
  .play-body{flex:1;overflow:auto;width:100%;max-width:920px;margin:0 auto;padding:6vh 28px 14vh;
    display:flex;flex-direction:column;gap:20px;cursor:pointer;}
  .play-line{font-size:28px;line-height:1.7;color:var(--text-1);}
  .play-name{color:var(--accent-2);font-weight:600;margin-right:12px;}
  .play-cursor{display:inline-block;width:3px;height:1.05em;background:var(--accent-2);margin-left:3px;
    vertical-align:-2px;animation:blink 1s step-end infinite;}
  .play-end{font-size:18px;color:var(--text-3);text-align:center;margin-top:28px;letter-spacing:3px;}
  .play-hint{position:fixed;left:0;right:0;bottom:18px;text-align:center;color:var(--text-3);font-size:13px;}
  @keyframes blink{50%{opacity:0;}}
</style>
</head>
<body>
  <header class="topbar">
    <div class="brand">📖 릴레이 소설</div>
    <button class="btn accent" id="runBtn">▶ 이야기 실행</button>
    <button class="btn ghost" id="themeBtn">☀ 라이트</button>
  </header>

  <main class="wrap">
    <div class="card">
      <div class="card-head">
        <div class="kicker">relay novel</div>
        <h1 class="card-h1">지금까지의 이야기</h1>
        <p class="card-desc">여러 명이 한 줄씩 이어 쓰고, Commit → Push 로 공유합니다.</p>
      </div>
      <div class="list" id="list"></div>
      <div class="bar">
        <button class="btn primary" id="openBtn">✍️ 작성하기</button>
        <button class="btn" id="reloadBtn">🔄 다시 불러오기</button>
      </div>
    </div>
  </main>

  <div class="overlay" id="overlay">
    <div class="modal-box">
      <div class="modal-header">
        <h2>✍️ 한 줄 작성하기</h2>
        <p class="sub">이어질 한 줄을 입력하세요. (원하면 캐릭터 이름을 붙일 수 있어요)</p>
      </div>
      <div class="modal-body">
        <div class="row">
          <label class="switch"><input type="checkbox" id="nameToggle"><span class="slider"></span></label>
          <span class="toggle-label" id="toggleLabel">캐릭터 이름 입력</span>
          <input type="text" id="charname" maxlength="10" placeholder="캐릭터 이름" style="display:none;">
        </div>
        <div class="row">
          <label class="lab" for="content">내용</label>
          <input type="text" id="content" maxlength="50" placeholder="이어질 한 줄을 입력하세요">
          <span class="count" id="count">0/50자</span>
        </div>
        <div class="preview" id="preview"></div>
      </div>
      <div class="modal-footer">
        <button class="btn ghost" id="cancelBtn">취소</button>
        <button class="btn primary" id="saveBtn">💾 저장</button>
      </div>
    </div>
  </div>

  <div class="overlay" id="confirmOverlay">
    <div class="modal-box sm">
      <div class="modal-header">
        <h2>줄 삭제</h2>
        <p class="sub">이 줄을 삭제할까요? 되돌릴 수 없습니다.</p>
      </div>
      <div class="modal-body">
        <div class="confirm-line" id="confirmLine"></div>
      </div>
      <div class="modal-footer">
        <button class="btn ghost" id="confirmCancel">취소</button>
        <button class="btn danger" id="confirmDelete">🗑 삭제</button>
      </div>
    </div>
  </div>

  <div class="play" id="play">
    <div class="play-top">
      <span class="play-kicker">이야기 실행</span>
      <button class="btn ghost" id="playClose">✕ 닫기</button>
    </div>
    <div class="play-body" id="playBody"></div>
    <div class="play-hint">클릭 또는 Space : 빨리감기 · Esc : 닫기</div>
  </div>

  <div class="toasts" id="toasts"></div>

<script>
const $ = s => document.querySelector(s);
const listEl = $('#list'), overlay = $('#overlay'), contentEl = $('#content');
const nameToggleEl = $('#nameToggle'), charnameEl = $('#charname');
const countEl = $('#count'), previewEl = $('#preview'), toastsEl = $('#toasts');
const playEl = $('#play'), playBody = $('#playBody'), themeBtn = $('#themeBtn');
const confirmOverlay = $('#confirmOverlay');
let currentEntries = [], pendingDelete = -1;

function applyThemeLabel(){
  themeBtn.textContent = document.documentElement.getAttribute('data-theme') === 'dark' ? '☀ 라이트' : '🌙 다크';
}
themeBtn.onclick = ()=>{
  const t = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', t);
  try { localStorage.setItem('relay:theme', t); } catch(e){}
  applyThemeLabel();
};
applyThemeLabel();

function toast(msg, type){
  const el = document.createElement('div');
  el.className = 'toast' + (type ? ' ' + type : '');
  el.textContent = msg;
  toastsEl.appendChild(el);
  setTimeout(()=>{ el.style.opacity = '0'; setTimeout(()=>el.remove(), 200); }, type === 'error' ? 6000 : 3000);
}

function esc(s){return (s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
function render(entries){
  currentEntries = entries;
  if(!entries.length){
    listEl.innerHTML = '<div class="empty">아직 아무도 쓰지 않았어요. [작성하기]를 눌러 첫 문장을 써 보세요.</div>';
    return;
  }
  listEl.innerHTML = entries.map((e,i)=>{
    const chip = e.name ? `<span class="chip">${esc(e.name)}</span>` : '';
    return `<div class="entry">${chip}<span class="txt">${esc(e.content)}</span>`
         + `<button class="del" data-i="${i}" title="삭제" aria-label="삭제">✕</button></div>`;
  }).join('');
  listEl.scrollTop = listEl.scrollHeight;
}
async function load(quiet){
  const r = await fetch('/api/story');
  render(await r.json());
  if(!quiet) toast('최신 내용을 불러왔어요.', 'success');
}

/* ----- 작성 ----- */
function useName(){ return nameToggleEl.checked && charnameEl.value.trim(); }
function openModal(){
  overlay.classList.add('on'); updateMeta();
  (nameToggleEl.checked && !charnameEl.value ? charnameEl : contentEl).focus();
}
function closeModal(){ overlay.classList.remove('on'); contentEl.value=''; updateMeta(); }
function updateMeta(){
  const n = contentEl.value.length;
  countEl.textContent = n + '/50자';
  countEl.classList.toggle('warn', n>=50);
  const c = contentEl.value.trim() || '내용';
  previewEl.textContent = '미리보기:  ' + (useName() ? '['+charnameEl.value.trim()+'] ' : '') + c;
}
function onToggle(){
  charnameEl.style.display = nameToggleEl.checked ? '' : 'none';
  if(nameToggleEl.checked) charnameEl.focus();
  updateMeta();
}
async function save(){
  const content = contentEl.value.trim();
  const name = nameToggleEl.checked ? charnameEl.value.trim() : '';
  if(!content){ contentEl.focus(); toast('내용을 입력해 주세요.', 'error'); return; }
  const r = await fetch('/api/story',{method:'POST',headers:{'Content-Type':'application/json'},
    body: JSON.stringify({name, content})});
  render(await r.json());
  closeModal();
  toast('저장 완료! 이제 GitHub Desktop에서 Commit → Push 하세요.', 'success');
}

/* ----- 삭제 (확인 팝업) ----- */
function askDelete(i){
  const e = currentEntries[i]; if(!e) return;
  pendingDelete = i;
  const chip = e.name ? `<span class="chip">${esc(e.name)}</span>` : '';
  $('#confirmLine').innerHTML = chip + `<span class="txt">${esc(e.content)}</span>`;
  confirmOverlay.classList.add('on');
}
function closeConfirm(){ confirmOverlay.classList.remove('on'); pendingDelete = -1; }
async function doDelete(){
  if(pendingDelete < 0) return;
  const r = await fetch('/api/delete',{method:'POST',headers:{'Content-Type':'application/json'},
    body: JSON.stringify({index: pendingDelete})});
  render(await r.json());
  closeConfirm();
  toast('한 줄을 삭제했어요. GitHub Desktop에서 Commit → Push 하세요.', 'success');
}

/* ----- 이야기 실행 (타이핑 연출) ----- */
const play = { active:false, skip:false, timer:null, cancel:null };
function wait(ms){ return new Promise(res=>{ play.timer = setTimeout(res, ms); play.cancel = res; }); }
function scrollPlay(){ playBody.scrollTop = playBody.scrollHeight; }
function closeStory(){
  play.active = false; play.skip = true;
  clearTimeout(play.timer); if(play.cancel) play.cancel();
  playEl.classList.remove('on');
}
async function typeLine(e){
  const line = document.createElement('div'); line.className = 'play-line';
  if(e.name){ const nm = document.createElement('span'); nm.className='play-name'; nm.textContent = e.name; line.appendChild(nm); }
  const txt = document.createElement('span'); txt.className='play-text'; line.appendChild(txt);
  const cur = document.createElement('span'); cur.className='play-cursor'; line.appendChild(cur);
  playBody.appendChild(line); scrollPlay();
  play.skip = false;
  for(let i=1;i<=e.content.length;i++){
    if(!play.active) { cur.remove(); return; }
    if(play.skip){ break; }
    txt.textContent = e.content.slice(0,i); scrollPlay();
    await wait(38);
  }
  txt.textContent = e.content; cur.remove(); scrollPlay();
}
async function runStory(){
  const r = await fetch('/api/story'); const entries = await r.json();
  if(!entries.length){ toast('아직 이야기가 없어요. 먼저 한 줄 작성해 보세요.', 'warn'); return; }
  playBody.innerHTML = ''; playEl.classList.add('on'); play.active = true;
  for(const e of entries){
    if(!play.active) break;
    await typeLine(e);
    if(!play.active) break;
    await wait(550);
  }
  if(play.active){
    const end = document.createElement('div'); end.className='play-end'; end.textContent='— 끝 —';
    playBody.appendChild(end); scrollPlay();
  }
}

/* ----- 이벤트 ----- */
$('#runBtn').onclick = runStory;
$('#playClose').onclick = closeStory;
playBody.onclick = ()=>{ play.skip = true; };
$('#openBtn').onclick = openModal;
$('#cancelBtn').onclick = closeModal;
$('#saveBtn').onclick = save;
$('#reloadBtn').onclick = ()=>load(false);
$('#confirmCancel').onclick = closeConfirm;
$('#confirmDelete').onclick = doDelete;
$('#toggleLabel').onclick = ()=>{ nameToggleEl.checked = !nameToggleEl.checked; onToggle(); };
nameToggleEl.addEventListener('change', onToggle);
charnameEl.oninput = updateMeta;
contentEl.oninput = updateMeta;
charnameEl.addEventListener('keydown', e=>{ if(e.key==='Enter') contentEl.focus(); });
contentEl.addEventListener('keydown', e=>{ if(e.key==='Enter') save(); });
listEl.addEventListener('click', e=>{ const b = e.target.closest('.del'); if(b) askDelete(parseInt(b.dataset.i, 10)); });
overlay.addEventListener('click', e=>{ if(e.target===overlay) closeModal(); });
confirmOverlay.addEventListener('click', e=>{ if(e.target===confirmOverlay) closeConfirm(); });
document.addEventListener('keydown', e=>{
  if(playEl.classList.contains('on')){
    if(e.key==='Escape') closeStory();
    else if(e.key===' '){ e.preventDefault(); play.skip = true; }
    return;
  }
  if(e.key==='Escape'){
    if(confirmOverlay.classList.contains('on')) closeConfirm();
    else if(overlay.classList.contains('on')) closeModal();
  }
});

setInterval(()=>fetch('/api/ping').catch(()=>{}), 1500);
window.addEventListener('beforeunload', ()=>{ navigator.sendBeacon('/api/bye'); });

load(true);
</script>
</body>
</html>
"""
# ──────────────────────────────────────────────────────────────────


def read_lines():
    if not os.path.exists(STORY_FILE):
        return []
    with open(STORY_FILE, "r", encoding="utf-8") as f:
        return [ln.rstrip("\n") for ln in f if ln.strip() != ""]


def read_entries():
    out = []
    for line in read_lines():
        if line.startswith("[") and "]" in line:
            i = line.index("]")
            out.append({"name": line[1:i].strip(), "content": line[i + 1:].strip()})
        else:
            out.append({"name": "", "content": line})
    return out


def append_line(text):
    with open(STORY_FILE, "a", encoding="utf-8") as f:
        f.write(text + "\n")


def delete_index(idx):
    """idx 번째(0부터) 줄을 삭제하고 파일을 다시 씀."""
    if not isinstance(idx, int):
        return
    lines = read_lines()
    if 0 <= idx < len(lines):
        del lines[idx]
        with open(STORY_FILE, "w", encoding="utf-8") as f:
            for ln in lines:
                f.write(ln + "\n")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, (bytes, bytearray)) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionAbortedError):
            pass

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._send(200, HTML, "text/html; charset=utf-8")
        elif path == "/api/story":
            self._send(200, json.dumps(read_entries(), ensure_ascii=False))
        elif path == "/api/ping":
            _state["last_ping"] = time.time()
            self._send(200, "{}")
        else:
            self._send(404, "{}")

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            data = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            data = {}
        if path == "/api/story":
            name = (data.get("name") or "").strip()[:10]
            content = (data.get("content") or "").strip()[:50]
            if content:
                append_line(f"[{name}] {content}" if name else content)
            self._send(200, json.dumps(read_entries(), ensure_ascii=False))
        elif path == "/api/delete":
            delete_index(data.get("index"))
            self._send(200, json.dumps(read_entries(), ensure_ascii=False))
        elif path == "/api/bye":
            _state["last_ping"] = 0
            self._send(200, "{}")
        else:
            self._send(404, "{}")


def watchdog(httpd):
    while True:
        time.sleep(2)
        now = time.time()
        if now - _state["start"] > 12 and now - _state["last_ping"] > 8:
            httpd.shutdown()
            return


def main():
    test = "--test" in sys.argv
    port = 0
    for a in sys.argv[1:]:
        if a.isdigit():
            port = int(a)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{httpd.server_address[1]}/"
    if test:
        print(url)
        httpd.serve_forever()
        return
    threading.Thread(target=watchdog, args=(httpd,), daemon=True).start()
    webbrowser.open(url)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
