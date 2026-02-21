const API = {
  get: (p) => fetch(`/api${p}`).then(async r => ({ok:r.ok, status:r.status, data: await r.json().catch(()=>null)})),
  post: (p, body) => fetch(`/api${p}`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)}).then(async r => ({ok:r.ok, status:r.status, data: await r.json().catch(()=>null)})),
  del: (p) => fetch(`/api${p}`, {method:'DELETE'}).then(async r => ({ok:r.ok, status:r.status, data: await r.json().catch(()=>null)})),
};

function qs(sel){return document.querySelector(sel)}
function el(tag, cls){const e=document.createElement(tag); if(cls) e.className=cls; return e;}
function fmtTs(iso){ if(!iso) return '-'; const d=new Date(iso); return d.toLocaleString(); }

function setActiveTab(name){
  document.querySelectorAll('.tab').forEach(t=>{
    t.classList.toggle('active', t.dataset.tab===name);
  });
  document.querySelectorAll('.view').forEach(v=>v.classList.add('hidden'));
  const target = qs('#'+name);
  if(target) target.classList.remove('hidden');
}

function modal(title, contentEl, onOk){
  const backdrop = qs('#modal-backdrop');
  backdrop.innerHTML = '';
  const m = el('div','modal');
  const h = el('h3'); h.textContent = title;
  const actions = el('div','actions');
  const cancel = el('button','btn'); cancel.textContent='Cancel';
  cancel.onclick=()=>backdrop.classList.add('hidden');
  const ok = el('button','btn primary'); ok.textContent='Save';
  ok.onclick=async ()=>{
    await onOk();
    backdrop.classList.add('hidden');
  };
  actions.append(cancel, ok);
  m.append(h, contentEl, actions);
  backdrop.append(m);
  backdrop.classList.remove('hidden');
}

async function renderOverview(){
  const root = qs('#overview');
  root.innerHTML = '';
  const card = el('div','card');
  card.innerHTML = `<h2>Overview</h2><div class="pre" id="ov-pre">Loading...</div>`;
  root.append(card);
  const res = await API.get('/overview');
  qs('#ov-pre').textContent = JSON.stringify(res.data, null, 2);
}

async function renderRegime(){
  const root = qs('#regime');
  root.innerHTML = '';
  const card = el('div','card');
  card.innerHTML = `<h2>Regime</h2><div class="pre" id="rg-pre">Loading...</div>`;
  root.append(card);
  const list = await API.get('/regimes/snapshots?limit=50');
  qs('#rg-pre').textContent = JSON.stringify(list.data, null, 2);
}

async function renderLogs(){
  const root = qs('#logs');
  root.innerHTML = '';
  const card = el('div','card');
  card.innerHTML = `<h2>Action Logs</h2><div class="pre" id="lg-pre">Loading...</div>`;
  root.append(card);
  const res = await API.get('/events?limit=200');
  qs('#lg-pre').textContent = JSON.stringify(res.data, null, 2);
}

async function renderTraders(){
  const root = qs('#traders');
  root.innerHTML = '';

  const grid = el('div','grid');
  const left = el('div','card');
  left.innerHTML = `<div class="row" style="justify-content:space-between">
    <h2 style="margin:0">Traders</h2>
    <div class="row"><button class="btn primary" id="add">ADD</button><button class="btn" id="refresh">Refresh</button></div>
  </div>
  <table><thead><tr>
    <th>Name</th><th>Status</th><th>Mode</th><th>Strategy</th><th>Risk</th><th>Credential</th><th>Heartbeat</th><th>Actions</th>
  </tr></thead><tbody id="tbody"></tbody></table>`;
  const tbody = left.querySelector('#tbody');

  async function loadTraders(){
    tbody.innerHTML = `<tr><td colspan="8" class="small">Loading...</td></tr>`;
    const res = await API.get('/traders');
    if(!res.ok){ tbody.innerHTML = `<tr><td colspan="8" class="small">Error: ${JSON.stringify(res.data)}</td></tr>`; return; }
    const items = res.data?.items || [];
    if(items.length===0){
      tbody.innerHTML = `<tr><td colspan="8" class="small">No traders yet. Click ADD.</td></tr>`;
      return;
    }
    tbody.innerHTML = '';
    for(const t of items){
      const tr = el('tr');
      const hb = t.last_heartbeat_at ? fmtTs(t.last_heartbeat_at) : '-';
      const st = t.status || 'STOP';
      const badgeCls = st==='RUN' ? 'ok' : (st==='ERROR' ? 'danger' : 'warn');
      tr.innerHTML = `<td>${t.name}</td>
        <td><span class="badge ${badgeCls}">${st}</span></td>
        <td>${t.run_mode}</td><td>${t.strategy}</td><td>${t.risk_mode}</td><td>${t.credential_name || '-'}</td><td>${hb}</td><td></td>`;
      const tdAct = tr.querySelector('td:last-child');

      const runPaper = el('button','btn'); runPaper.textContent='RUN(PAPER)';
      runPaper.onclick=async()=>{ await API.post(`/traders/${encodeURIComponent(t.name)}/run`, {run_mode:'PAPER'}); await loadTraders(); };

      const runLive = el('button','btn'); runLive.textContent='RUN(LIVE)';
      runLive.onclick=async()=>{ await API.post(`/traders/${encodeURIComponent(t.name)}/run`, {run_mode:'LIVE'}); await loadTraders(); };

      const stop = el('button','btn'); stop.textContent='STOP';
      stop.onclick=async()=>{ await API.post(`/traders/${encodeURIComponent(t.name)}/stop`, {}); await loadTraders(); };

      const remove = el('button','btn danger'); remove.textContent='REMOVE';
      remove.onclick=async()=>{ if(confirm('Remove trader?')){ await API.del(`/traders/${encodeURIComponent(t.name)}`); await loadTraders(); } };

      tdAct.append(runPaper, runLive, stop, remove);
      tbody.append(tr);
    }
  }

  async function loadCreds(){
    const r = await API.get('/credentials');
    return r.data?.items || [];
  }

  left.querySelector('#add').onclick = async ()=>{
    const creds = await loadCreds();
    const form = el('div');

    const name = el('input','input'); name.placeholder='trader name';
    const strategy = el('input','input'); strategy.placeholder='strategy (e.g., challenge1)';
    const risk = el('select'); risk.className='input';
    ['SAFE','STANDARD','PROFIT','CRAZY'].forEach(v=>{ const o=el('option'); o.value=v; o.textContent=v; risk.append(o); });
    const credSel = el('select'); credSel.className='input';
    const o0 = el('option'); o0.value=''; o0.textContent='(none)'; credSel.append(o0);
    for(const c of creds){ const o=el('option'); o.value=c.name; o.textContent=c.name; credSel.append(o); }
    const runMode = el('select'); runMode.className='input';
    ['PAPER','LIVE'].forEach(v=>{ const o=el('option'); o.value=v; o.textContent=v; runMode.append(o); });

    form.append(
      Object.assign(el('label'),{textContent:'Trader Name'}), name,
      Object.assign(el('label'),{textContent:'Strategy'}), strategy,
      Object.assign(el('label'),{textContent:'Risk Mode'}), risk,
      Object.assign(el('label'),{textContent:'Credential'}), credSel,
      Object.assign(el('label'),{textContent:'Default Run Mode'}), runMode
    );

    modal('Create Trader', form, async ()=>{
      const payload = {
        trader_name: name.value.trim(),
        strategy: strategy.value.trim() || 'challenge1',
        risk_mode: risk.value,
        run_mode: runMode.value,
        seed_krw: null,
        credential_name: credSel.value || null,
      };
      if(!payload.trader_name) throw new Error('Trader name required');
      const r = await API.post('/traders', payload);
      if(!r.ok) throw new Error(JSON.stringify(r.data));
      await loadTraders();
    });
  };

  left.querySelector('#refresh').onclick = loadTraders;

  // right column
  const right = el('div');
  right.style.display='flex';
  right.style.flexDirection='column';
  right.style.gap='16px';

  const credCard = el('div','card');
  credCard.innerHTML = `<h2>Credentials</h2>
    <label>Name</label><input class="input" id="cname" placeholder="credential name">
    <label>Access Key</label><input class="input" id="access" placeholder="upbit access key">
    <label>Secret Key</label><input class="input" id="secret" placeholder="upbit secret key">
    <div class="row" style="margin-top:12px"><button class="btn primary" id="savecred">Save Credential</button></div>
    <div class="small" style="margin-top:10px">Keys are encrypted in DB (CRYPTO_MASTER_KEY).</div>
    <div id="credlist" class="small" style="margin-top:10px">Loading...</div>`;
  const cname = credCard.querySelector('#cname');
  const access = credCard.querySelector('#access');
  const secret = credCard.querySelector('#secret');
  const credlist = credCard.querySelector('#credlist');

  async function refreshCredList(){
    const r = await API.get('/credentials');
    if(!r.ok){ credlist.textContent = 'Error: '+JSON.stringify(r.data); return; }
    const items = r.data?.items || [];
    if(items.length===0){ credlist.textContent='No credentials yet.'; return; }
    credlist.innerHTML='';
    for(const c of items){
      const row = el('div','row');
      const b = el('span','badge'); b.textContent=c.name;
      const del = el('button','btn danger'); del.textContent='Delete';
      del.onclick=async()=>{ if(confirm('Delete credential?')){ await API.del(`/credentials/${encodeURIComponent(c.name)}`); await refreshCredList(); } };
      row.append(b, del);
      credlist.append(row);
    }
  }

  credCard.querySelector('#savecred').onclick = async ()=>{
    const payload = {name:cname.value.trim(), access_key:access.value.trim(), secret_key:secret.value.trim()};
    if(!payload.name || !payload.access_key || !payload.secret_key){ alert('Fill all fields'); return; }
    const r = await API.post('/credentials', payload);
    if(!r.ok){ alert(JSON.stringify(r.data)); return; }
    cname.value=''; access.value=''; secret.value='';
    await refreshCredList();
  };

  const hint = el('div','card');
  hint.innerHTML = `<h2>Tips</h2><div class="small">
  - RUN 버튼은 trader 컨테이너(ats-trader-*)를 생성합니다.<br>
  - 먼저 <code>make trader-image</code> 실행 후 RUN 하세요.
  </div>`;

  right.append(credCard, hint);

  grid.append(left, right);
  root.append(grid);

  await refreshCredList();
  await loadTraders();
}

function initNav(){
  document.querySelectorAll('.tab').forEach(t=>{
    t.onclick=(e)=>{e.preventDefault(); setActiveTab(t.dataset.tab);};
  });
  const hash = location.hash.replace('#','') || 'overview';
  setActiveTab(hash);
  window.addEventListener('hashchange', ()=>{
    const h = location.hash.replace('#','') || 'overview';
    setActiveTab(h);
  });
}

async function boot(){
  initNav();
  await renderOverview();
  await renderTraders();
  await renderRegime();
  await renderLogs();

  document.querySelectorAll('.tab').forEach(t=>{
    t.addEventListener('click', async ()=>{
      const name=t.dataset.tab;
      if(name==='overview') await renderOverview();
      if(name==='traders') await renderTraders();
      if(name==='regime') await renderRegime();
      if(name==='logs') await renderLogs();
    });
  });
}

boot().catch(e=>{ console.error(e); alert(String(e)); });
