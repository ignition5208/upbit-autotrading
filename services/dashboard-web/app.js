// ===== API HELPER =====
const API = {
  get:  (p)       => fetch(`/api${p}`).then(async r => ({ ok: r.ok, data: await r.json().catch(() => null) })),
  post: (p, body) => fetch(`/api${p}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(async r => ({ ok: r.ok, data: await r.json().catch(() => null) })),
  del:  (p)       => fetch(`/api${p}`, { method: 'DELETE' }).then(async r => ({ ok: r.ok, data: await r.json().catch(() => null) })),
};

// ===== CONSTANTS =====
const STRATEGIES = [
  { id: 'safety_first', label: 'SAFETY FIRST', risk_mode: 'SAFE',     icon: '🛡️', desc: '손실 최소화 우선.\n보수적 포지션 관리.' },
  { id: 'standard',     label: 'STANDARD',     risk_mode: 'STANDARD', icon: '⚖️', desc: '균형잡힌 리스크.\n표준 전략 운용.' },
  { id: 'profit_first', label: 'PROFIT FIRST', risk_mode: 'PROFIT',   icon: '📈', desc: '수익 극대화 추구.\n공격적 포지션.' },
  { id: 'crazy',        label: 'CRAZY',        risk_mode: 'CRAZY',    icon: '🚀', desc: '초고위험 고수익.\n최대 레버리지 추구.' },
  { id: 'ai_mode',      label: 'AI MODE',      risk_mode: 'STANDARD', icon: '🤖', desc: 'AI 자동 튜닝.\n레짐 적응형 최적화.' },
];

const CHART_COLORS = ['#60a5fa', '#34d399', '#fbbf24', '#a78bfa', '#fb7185', '#38bdf8', '#4ade80', '#f472b6'];

let _refreshTimer = null;

// ===== DOM HELPERS =====
const qs  = sel => document.querySelector(sel);
const qsa = sel => document.querySelectorAll(sel);
function el(tag, cls) { const e = document.createElement(tag); if (cls) e.className = cls; return e; }

function fmtTs(iso) {
  if (!iso) return '-';
  const d = new Date(iso.endsWith('Z') ? iso : iso + 'Z');
  return d.toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function fmtKrw(n) {
  if (n == null) return '—';
  return Number(n).toLocaleString('ko-KR') + ' KRW';
}

function pnlHtml(n) {
  if (n == null || n === 0) return '<span class="pnl-zero">—</span>';
  const pct = (n * 100).toFixed(2);
  return n > 0
    ? `<span class="pnl-pos">+${pct}%</span>`
    : `<span class="pnl-neg">${pct}%</span>`;
}

// ===== MODAL =====
function showModal({ title, body, confirmLabel = 'APPLY', danger = false, onConfirm }) {
  const backdrop = qs('#modal-backdrop');
  backdrop.innerHTML = '';

  const m = el('div', 'modal');
  const t = el('div', 'modal-title'); t.textContent = title;
  const b = el('div', 'modal-body');
  if (typeof body === 'string') {
    b.innerHTML = `<div class="modal-confirm-text">${body}</div>`;
  } else {
    b.append(body);
  }

  const acts = el('div', 'modal-actions');
  const cancel = el('button', 'btn'); cancel.textContent = 'CANCEL';
  cancel.onclick = () => backdrop.classList.add('hidden');

  const confirm = el('button', `btn ${danger ? 'btn-danger' : 'btn-primary'}`);
  confirm.textContent = confirmLabel;
  confirm.onclick = async () => {
    confirm.disabled = true;
    confirm.textContent = '...';
    try {
      await onConfirm();
      backdrop.classList.add('hidden');
    } catch (e) {
      confirm.disabled = false;
      confirm.textContent = confirmLabel;
      alert(String(e?.message || e));
    }
  };

  acts.append(cancel, confirm);
  m.append(t, b, acts);
  backdrop.append(m);
  backdrop.classList.remove('hidden');
}

// ===== PROFIT CHART (Canvas) =====
function drawChart(canvas, traders) {
  const dpr = window.devicePixelRatio || 1;
  const W   = canvas.offsetWidth || 800;
  const H   = 220;
  canvas.width  = W * dpr;
  canvas.height = H * dpr;
  canvas.style.height = H + 'px';
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);

  const PAD = { t: 20, r: 20, b: 36, l: 54 };
  const cw = W - PAD.l - PAD.r;
  const ch = H - PAD.t - PAD.b;

  // grid lines
  ctx.strokeStyle = '#1a2840';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = PAD.t + (ch / 4) * i;
    ctx.beginPath(); ctx.moveTo(PAD.l, y); ctx.lineTo(PAD.l + cw, y); ctx.stroke();
  }

  // axes
  ctx.strokeStyle = '#223052';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(PAD.l, PAD.t); ctx.lineTo(PAD.l, PAD.t + ch); ctx.lineTo(PAD.l + cw, PAD.t + ch);
  ctx.stroke();

  const hasData = traders.some(t => t.points && t.points.length > 1);
  if (!hasData) {
    // zero line (dashed)
    ctx.strokeStyle = '#223052'; ctx.setLineDash([4, 4]); ctx.lineWidth = 1;
    const zy = PAD.t + ch / 2;
    ctx.beginPath(); ctx.moveTo(PAD.l, zy); ctx.lineTo(PAD.l + cw, zy); ctx.stroke();
    ctx.setLineDash([]);
    // y labels
    ctx.fillStyle = '#4e6080'; ctx.font = '11px system-ui'; ctx.textAlign = 'right';
    ['+2%', '+1%', '0%', '-1%', '-2%'].forEach((lbl, i) => {
      ctx.fillText(lbl, PAD.l - 6, PAD.t + (ch / 4) * i + 4);
    });
    // placeholder text
    ctx.fillStyle = '#2d4060'; ctx.font = '13px system-ui'; ctx.textAlign = 'center';
    ctx.fillText('수익 데이터 없음', W / 2, H / 2 + 4);
    return;
  }

  // bounds
  let minY = Infinity, maxY = -Infinity, minX = Infinity, maxX = -Infinity;
  for (const t of traders) {
    for (const p of (t.points || [])) {
      if (p.pnl < minY) minY = p.pnl;
      if (p.pnl > maxY) maxY = p.pnl;
      if (p.ts < minX)  minX = p.ts;
      if (p.ts > maxX)  maxX = p.ts;
    }
  }
  const yPad = (maxY - minY) * 0.12 || 0.01;
  minY -= yPad; maxY += yPad;
  const xR = maxX - minX || 1;
  const yR = maxY - minY;

  // zero line
  if (minY < 0 && maxY > 0) {
    const zy = PAD.t + (maxY / yR) * ch;
    ctx.strokeStyle = '#334155'; ctx.setLineDash([4, 4]); ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(PAD.l, zy); ctx.lineTo(PAD.l + cw, zy); ctx.stroke();
    ctx.setLineDash([]);
  }

  // y labels
  ctx.fillStyle = '#4e6080'; ctx.font = '11px system-ui'; ctx.textAlign = 'right';
  for (let i = 0; i <= 4; i++) {
    const val = maxY - (yR / 4) * i;
    ctx.fillText((val * 100).toFixed(1) + '%', PAD.l - 6, PAD.t + (ch / 4) * i + 4);
  }

  // lines
  for (let i = 0; i < traders.length; i++) {
    const t = traders[i];
    if (!t.points || t.points.length < 2) continue;
    ctx.strokeStyle = CHART_COLORS[i % CHART_COLORS.length];
    ctx.lineWidth = 2; ctx.lineJoin = 'round';
    ctx.beginPath();
    t.points.forEach((p, j) => {
      const x = PAD.l + ((p.ts - minX) / xR) * cw;
      const y = PAD.t + ((maxY - p.pnl) / yR) * ch;
      j === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.stroke();
  }
}

// ===== DASHBOARD =====
async function renderDashboard() {
  const root = qs('#dashboard');
  root.innerHTML = '';

  // Stat cards
  const grid = el('div', 'stats-grid');
  grid.innerHTML = `
    <div class="stat-card">
      <div class="stat-label">CURRENT REGIME</div>
      <div class="stat-value v-regime" id="s-regime">—</div>
      <div class="stat-sub" id="s-regime-sub"></div>
    </div>
    <div class="stat-card">
      <div class="stat-label">TOTAL TRADER</div>
      <div class="stat-value" id="s-total">—</div>
      <div class="stat-sub">등록된 트레이더 수</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">PAPER TRADER</div>
      <div class="stat-value v-blue" id="s-paper">—</div>
      <div class="stat-sub">페이퍼 모드 실행 중</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">LIVE TRADER</div>
      <div class="stat-value v-green" id="s-live">—</div>
      <div class="stat-sub">라이브 모드 실행 중</div>
    </div>
  `;

  // Chart panel
  const chartPanel = el('div', 'panel');
  chartPanel.innerHTML = `
    <div class="panel-header">
      <span class="panel-title">PROFIT CHART</span>
      <div class="chart-legend" id="chart-legend"></div>
    </div>
    <div class="panel-body" style="padding-bottom:16px;">
      <canvas class="chart-canvas" id="profit-chart"></canvas>
    </div>
  `;

  // Log panel
  const logPanel = el('div', 'panel');
  logPanel.innerHTML = `
    <div class="panel-header">
      <span class="panel-title">TRADERS ACTION LOG</span>
      <button class="btn btn-sm" id="log-refresh">↻ 새로고침</button>
    </div>
    <div class="panel-body" style="padding:12px 16px;">
      <div class="log-list" id="log-list">
        <div class="empty"><div class="empty-icon">📋</div><div class="empty-text">로딩 중...</div></div>
      </div>
    </div>
  `;

  root.append(grid, chartPanel, logPanel);
  logPanel.querySelector('#log-refresh').onclick = loadDashboard;

  await loadDashboard();
}

async function loadDashboard() {
  // Fetch all in parallel
  const [ovRes, rgRes, evRes, trRes] = await Promise.all([
    API.get('/overview'),
    API.get('/regimes/snapshots?limit=1'),
    API.get('/events?limit=100'),
    API.get('/traders'),
  ]);

  // Regime
  const snap = rgRes.data?.items?.[0];
  const regimeEl    = qs('#s-regime');
  const regimeSubEl = qs('#s-regime-sub');
  if (regimeEl) {
    regimeEl.textContent    = snap ? snap.regime_label : '—';
    if (regimeSubEl) regimeSubEl.textContent = snap ? `신뢰도 ${(snap.confidence * 100).toFixed(0)}% · ${snap.market}` : '';
  }

  // Stats
  const ov = ovRes.data || {};
  const setTxt = (id, v) => { const e = qs(id); if (e) e.textContent = v ?? '—'; };
  setTxt('#s-total', ov.total_traders);
  setTxt('#s-paper', ov.paper_traders);
  setTxt('#s-live',  ov.live_traders);

  // Chart
  const canvas = qs('#profit-chart');
  const legendEl = qs('#chart-legend');
  if (canvas) {
    const traders = (trRes.data?.items || []).map((t, i) => ({ name: t.name, points: [] }));
    drawChart(canvas, traders);
    if (legendEl) {
      legendEl.innerHTML = '';
      (trRes.data?.items || []).forEach((t, i) => {
        const item = el('div', 'legend-item');
        const dot  = el('span', 'legend-dot');
        dot.style.background = CHART_COLORS[i % CHART_COLORS.length];
        item.append(dot, document.createTextNode(t.name));
        legendEl.append(item);
      });
    }
  }

  // Events log
  const logList = qs('#log-list');
  if (logList) {
    const events = evRes.data?.items || [];
    if (events.length === 0) {
      logList.innerHTML = '<div class="empty"><div class="empty-icon">📋</div><div class="empty-text">이벤트 없음</div></div>';
    } else {
      logList.innerHTML = '';
      for (const ev of events) {
        const row = el('div', 'log-row');
        row.innerHTML = `
          <span class="log-ts">${fmtTs(ev.ts)}</span>
          <span class="log-level ${ev.level || 'INFO'}">${ev.level || 'INFO'}</span>
          <span class="log-trader">${ev.trader_name || 'system'}</span>
          <span class="log-msg">${ev.message || ''}</span>
        `;
        logList.append(row);
      }
    }
  }
}

// ===== TRADERS =====
async function renderTraders() {
  const root = qs('#traders');
  root.innerHTML = '';

  const panel = el('div', 'table-panel');
  panel.innerHTML = `
    <div class="table-toolbar">
      <span class="toolbar-title">TRADERS</span>
      <div class="toolbar-right">
        <button class="btn btn-sm" id="t-refresh">↻ 새로고침</button>
        <button class="btn btn-sm btn-primary" id="t-add">+ TRADER ADD</button>
      </div>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>TRADER NAME</th>
            <th>TRADER SEED</th>
            <th>TRADER STRATEGY</th>
            <th>TRADER PROFIT</th>
            <th>TRADER RUN</th>
            <th>TRADER MANAGEMENT</th>
          </tr>
        </thead>
        <tbody id="t-tbody"></tbody>
      </table>
    </div>
  `;
  root.append(panel);

  async function loadTraders() {
    const tbody = qs('#t-tbody');
    if (!tbody) {
      console.error('[loadTraders] tbody element not found');
      return;
    }
    tbody.innerHTML = `<tr><td colspan="6"><div class="empty" style="padding:36px 0;"><div class="empty-icon">⏳</div><div class="empty-text">로딩 중...</div></div></td></tr>`;

    const res = await API.get('/traders');
    if (!res.ok) {
      console.error('[loadTraders] API error:', res.data);
      tbody.innerHTML = `<tr><td colspan="6" style="padding:20px;color:var(--danger2);">API 오류: ${JSON.stringify(res.data)}</td></tr>`;
      return;
    }

    console.log('[loadTraders] API response:', res.data);
    const items = res.data?.items || [];
    console.log('[loadTraders] Items count:', items.length);
    if (items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6"><div class="empty"><div class="empty-icon">🤖</div><div class="empty-text">트레이더 없음. TRADER ADD 버튼으로 추가하세요.</div></div></td></tr>`;
      return;
    }

    tbody.innerHTML = '';
    for (const t of items) {
      const strat = STRATEGIES.find(s => s.id === t.strategy);
      const stratLabel = strat ? strat.label : t.strategy;
      const tr = el('tr');

      // NAME
      const tdName = el('td');
      tdName.innerHTML = `<div class="td-name-main">${t.name}</div><div class="td-name-sub">${t.credential_name || '자격증명 없음'}</div>`;

      // SEED
      const tdSeed = el('td');
      tdSeed.innerHTML = `<span class="td-mono">${fmtKrw(t.seed_krw)}</span>`;

      // STRATEGY
      const tdStrat = el('td');
      tdStrat.innerHTML = `<div class="td-strat-main">${stratLabel}</div><div class="td-strat-sub">${t.risk_mode}</div>`;

      // PROFIT
      const tdProfit = el('td');
      tdProfit.innerHTML = pnlHtml(t.pnl ?? null);

      // RUN (mode select + APPLY + status badge)
      const tdRun = el('td');
      const mSel = el('select', 'mode-select');
      ['PAPER', 'LIVE'].forEach(v => {
        const o = el('option'); o.value = v; o.textContent = v;
        if (t.run_mode === v) o.selected = true;
        mSel.append(o);
      });
      const applyBtn = el('button', 'btn btn-sm btn-primary');
      applyBtn.textContent = 'APPLY';
      applyBtn.onclick = () => {
        const mode = mSel.value;
        showModal({
          title: 'RUN MODE 변경',
          body: `<strong>${t.name}</strong>의 모드를 <strong>${mode}</strong>로 변경하고 실행합니다.`,
          onConfirm: async () => {
            const r = await API.post(`/traders/${encodeURIComponent(t.name)}/run`, { run_mode: mode });
            if (!r.ok) throw new Error(JSON.stringify(r.data));
            await loadTraders();
          },
        });
      };
      const statusBadge = el('span', `badge badge-${t.status || 'STOP'}`);
      statusBadge.textContent = t.status || 'STOP';
      const runWrap = el('div', 'td-run');
      runWrap.append(mSel, applyBtn);
      tdRun.append(runWrap);
      tdRun.append(Object.assign(el('div'), { style: 'margin-top:6px;' })).append(statusBadge);

      // MANAGEMENT
      const tdMgmt = el('td');
      const mgmtWrap = el('div', 'td-mgmt');

      const runBtn = el('button', 'btn btn-sm');
      runBtn.textContent = 'RUN';
      runBtn.onclick = () => showModal({
        title: 'TRADER 실행',
        body: `<strong>${t.name}</strong>을 <strong>${t.run_mode}</strong> 모드로 실행합니다.`,
        onConfirm: async () => {
          const r = await API.post(`/traders/${encodeURIComponent(t.name)}/run`, { run_mode: t.run_mode });
          if (!r.ok) throw new Error(JSON.stringify(r.data));
          await loadTraders();
        },
      });

      const stopBtn = el('button', 'btn btn-sm');
      stopBtn.textContent = 'STOP';
      stopBtn.onclick = () => showModal({
        title: 'TRADER 중지',
        body: `<strong>${t.name}</strong>을 중지합니다.`,
        onConfirm: async () => {
          const r = await API.post(`/traders/${encodeURIComponent(t.name)}/stop`, {});
          if (!r.ok) throw new Error(JSON.stringify(r.data));
          await loadTraders();
        },
      });

      const rmBtn = el('button', 'btn btn-sm btn-danger');
      rmBtn.textContent = 'REMOVE';
      rmBtn.onclick = () => showModal({
        title: 'TRADER 삭제',
        body: `<strong>${t.name}</strong>을 완전히 삭제합니다. 이 작업은 되돌릴 수 없습니다.`,
        danger: true,
        onConfirm: async () => {
          const r = await API.del(`/traders/${encodeURIComponent(t.name)}`);
          if (!r.ok) throw new Error(JSON.stringify(r.data));
          await loadTraders();
        },
      });

      mgmtWrap.append(runBtn, stopBtn, rmBtn);
      tdMgmt.append(mgmtWrap);

      tr.append(tdName, tdSeed, tdStrat, tdProfit, tdRun, tdMgmt);
      tbody.append(tr);
    }
  }

  panel.querySelector('#t-refresh').onclick = loadTraders;

  panel.querySelector('#t-add').onclick = async () => {
    const credsRes = await API.get('/credentials');
    const creds = credsRes.data?.items || [];

    const form = el('div');
    const nameInput = el('input', 'input');
    nameInput.placeholder = 'trader-01';

    const stratSel = el('select', 'iselect');
    STRATEGIES.forEach(s => {
      const o = el('option'); o.value = s.id; o.textContent = s.label;
      stratSel.append(o);
    });
    // Pre-select from STRATEGY menu active state
    const savedStrat = localStorage.getItem('activeStrategy');
    if (savedStrat) stratSel.value = savedStrat;

    const seedInput = el('input', 'input');
    seedInput.type = 'number'; seedInput.placeholder = '1000000'; seedInput.min = '0';

    const credSel = el('select', 'iselect');
    const none = el('option'); none.value = ''; none.textContent = '(없음)'; credSel.append(none);
    creds.forEach(c => { const o = el('option'); o.value = c.name; o.textContent = c.name; credSel.append(o); });

    // Form fields
    const nameLabel = el('label'); nameLabel.textContent = 'NAME';
    const stratLabel = el('label'); stratLabel.textContent = 'STRATEGY';
    const seedLabel = el('label'); seedLabel.textContent = 'SEED MONEY (KRW)';
    const credLabel = el('label'); credLabel.textContent = 'CREDENTIAL';

    form.append(
      nameLabel, nameInput,
      stratLabel, stratSel,
      seedLabel, seedInput,
      credLabel, credSel,
    );

    showModal({
      title: 'TRADER ADD',
      body: form,
      confirmLabel: 'CREATE',
      onConfirm: async () => {
        const name = nameInput.value.trim();
        if (!name) throw new Error('NAME을 입력하세요.');
        const sel = STRATEGIES.find(s => s.id === stratSel.value) || STRATEGIES[1];
        const r = await API.post('/traders', {
          trader_name: name,
          strategy:    sel.id,
          risk_mode:   sel.risk_mode,
          run_mode:    'PAPER',
          seed_krw:    seedInput.value ? Number(seedInput.value) : null,
          credential_name: credSel.value || null,
        });
        if (!r.ok) throw new Error(JSON.stringify(r.data));
        await loadTraders();
      },
    });
  };

  await loadTraders();
}

// ===== STRATEGY =====
function renderStrategy() {
  const root = qs('#strategy');
  root.innerHTML = '';

  const notice = el('div', 'strategy-notice');
  notice.textContent = '⚠  전략 프로파일 수정은 이 메뉴에서만 가능합니다.';

  const grid = el('div', 'strategy-grid');
  const saved = localStorage.getItem('activeStrategy') || 'standard';

  STRATEGIES.forEach(s => {
    const card = el('div', 'strategy-card');
    if (s.id === saved) card.classList.add('active');
    card.innerHTML = `
      <div class="s-icon">${s.icon}</div>
      <div class="s-name">${s.label}</div>
      <div class="s-desc">${s.desc.replace(/\n/g, '<br>')}</div>
      <div class="s-badge">${s.risk_mode}</div>
    `;
    card.onclick = () => {
      localStorage.setItem('activeStrategy', s.id);
      qsa('.strategy-card').forEach(c => c.classList.remove('active'));
      card.classList.add('active');
    };
    grid.append(card);
  });

  root.append(notice, grid);
}

// ===== CONFIG =====
async function renderConfig() {
  const root = qs('#config');
  root.innerHTML = '';

  const panel = el('div', 'table-panel');
  panel.innerHTML = `
    <div class="table-toolbar">
      <span class="toolbar-title">CREDENTIALS</span>
      <div class="toolbar-right">
        <button class="btn btn-sm btn-primary" id="cred-add">+ ADD</button>
      </div>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr><th>NAME</th><th>등록일</th><th>ACTIONS</th></tr>
        </thead>
        <tbody id="cred-tbody"></tbody>
      </table>
    </div>
  `;
  root.append(panel);

  async function loadCreds() {
    const tbody = qs('#cred-tbody');
    tbody.innerHTML = `<tr><td colspan="3"><div class="empty" style="padding:36px 0;"><div class="empty-icon">⏳</div><div class="empty-text">로딩 중...</div></div></td></tr>`;

    const res = await API.get('/credentials');
    if (!res.ok) {
      tbody.innerHTML = `<tr><td colspan="3" style="padding:20px;color:var(--danger2);">API 오류</td></tr>`;
      return;
    }

    const items = res.data?.items || [];
    if (items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="3"><div class="empty"><div class="empty-icon">🔑</div><div class="empty-text">등록된 자격증명 없음</div></div></td></tr>`;
      return;
    }

    tbody.innerHTML = '';
    for (const c of items) {
      const tr = el('tr');
      const tdName = el('td');
      tdName.innerHTML = `<span style="font-weight:700;font-family:ui-monospace,monospace;">${c.name}</span>`;
      const tdDate = el('td'); tdDate.textContent = fmtTs(c.created_at);
      const tdAct  = el('td');
      const delBtn = el('button', 'btn btn-sm btn-danger'); delBtn.textContent = 'DELETE';
      delBtn.onclick = () => showModal({
        title: 'CREDENTIAL 삭제',
        body: `<strong>${c.name}</strong> 자격증명을 삭제합니다.`,
        danger: true,
        onConfirm: async () => {
          const r = await API.del(`/credentials/${encodeURIComponent(c.name)}`);
          if (!r.ok) throw new Error(JSON.stringify(r.data));
          await loadCreds();
        },
      });
      tdAct.append(delBtn);
      tr.append(tdName, tdDate, tdAct);
      tbody.append(tr);
    }
  }

  panel.querySelector('#cred-add').onclick = () => {
    const form = el('div');
    const nameIn   = el('input', 'input'); nameIn.placeholder = 'my-upbit-key';
    const accessIn = el('input', 'input'); accessIn.placeholder = 'Upbit Access Key';
    const secretIn = el('input', 'input'); secretIn.type = 'password'; secretIn.placeholder = 'Upbit Secret Key';
    
    const nameLabel = el('label'); nameLabel.textContent = 'NAME';
    const accessLabel = el('label'); accessLabel.textContent = 'ACCESS KEY';
    const secretLabel = el('label'); secretLabel.textContent = 'SECRET KEY';
    
    form.append(
      nameLabel, nameIn,
      accessLabel, accessIn,
      secretLabel, secretIn,
    );
    showModal({
      title: 'CREDENTIAL ADD',
      body: form,
      onConfirm: async () => {
        if (!nameIn.value.trim() || !accessIn.value.trim() || !secretIn.value.trim())
          throw new Error('모든 필드를 입력하세요.');
        const r = await API.post('/credentials', {
          name: nameIn.value.trim(),
          access_key: accessIn.value.trim(),
          secret_key: secretIn.value.trim(),
        });
        if (!r.ok) throw new Error(JSON.stringify(r.data));
        await loadCreds();
      },
    });
  };

  await loadCreds();
}

// ===== NAVIGATION =====
async function setTab(name) {
  if (_refreshTimer) { clearInterval(_refreshTimer); _refreshTimer = null; }

  qsa('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === name));
  qsa('.view').forEach(v => v.classList.add('hidden'));
  const view = qs('#' + name);
  if (view) view.classList.remove('hidden');

  if (name === 'dashboard') {
    await renderDashboard();
    _refreshTimer = setInterval(loadDashboard, 10000);
  } else if (name === 'traders') {
    await renderTraders();
  } else if (name === 'strategy') {
    renderStrategy();
  } else if (name === 'config') {
    await renderConfig();
  }
}

// ===== API HEALTH =====
async function checkHealth() {
  try {
    const r = await fetch('/health');
    const dot = qs('#api-status');
    if (dot) dot.className = 'api-status ' + (r.ok ? 'ok' : 'err');
  } catch {
    const dot = qs('#api-status');
    if (dot) dot.className = 'api-status err';
  }
}

// ===== BOOT =====
async function boot() {
  qsa('.tab').forEach(t => {
    t.onclick = e => { e.preventDefault(); setTab(t.dataset.tab); };
  });

  await checkHealth();
  setInterval(checkHealth, 30000);

  const hash = location.hash.replace('#', '') || 'dashboard';
  await setTab(hash);

  window.addEventListener('hashchange', () => {
    setTab(location.hash.replace('#', '') || 'dashboard');
  });
}

boot().catch(e => console.error('[ATS boot]', e));
