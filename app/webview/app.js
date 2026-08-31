/* ───────────────────────────────────────────────────────────────
   Tecnosup — App logic (vanilla JS)
   Qt WebEngine: Python injeta dados via runJavaScript()
   ─────────────────────────────────────────────────────────────── */

(function () {
  'use strict';

  // -- Modal de confirmacao ------------------------------------
  // Substitui confirm(): o dialogo nativo mostra "Javascript Confirm" e o
  // caminho do arquivo, quebrando a identidade visual do app.
  function tecConfirm(opts, onYes) {
    const box = document.getElementById('tec-modal');
    if (!box) { if (onYes) onYes(); return; }

    const o = (typeof opts === 'string') ? { body: opts } : (opts || {});
    document.getElementById('tec-modal-title').textContent = o.title || 'Confirmar';
    document.getElementById('tec-modal-body').textContent = o.body || '';
    const yes = document.getElementById('tec-modal-yes');
    const no = document.getElementById('tec-modal-no');
    yes.textContent = o.yes || 'CONFIRMAR';

    const accent = document.getElementById('tec-modal-accent');
    if (accent) accent.style.background = o.danger ? '#e8a33d' : 'var(--cyan)';
    yes.style.background = o.danger ? '#e8a33d' : '';
    yes.style.color = o.danger ? '#0a0a12' : '';

    box.style.display = 'flex';
    yes.focus();

    function fechar() {
      box.style.display = 'none';
      yes.onclick = null;
      no.onclick = null;
      document.removeEventListener('keydown', tecla);
    }
    function tecla(e) {
      if (e.key === 'Escape') { fechar(); }
      else if (e.key === 'Enter') { fechar(); if (onYes) onYes(); }
    }

    yes.onclick = function () { fechar(); if (onYes) onYes(); };
    no.onclick = fechar;
    document.addEventListener('keydown', tecla);
  }
  window.tecConfirm = tecConfirm;


  // ── Navegação entre telas ──────────────────────────────────────
  function navigate(screenId) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.menu-btn').forEach(b => b.classList.remove('active'));

    const screen = document.getElementById('screen-' + screenId);
    if (screen) screen.classList.add('active');

    const btn = document.querySelector(`.menu-btn[data-screen="${screenId}"]`);
    if (btn) btn.classList.add('active');

    if (window.bridge && window.bridge.onNavigate) {
      window.bridge.onNavigate(screenId);
    }
  }
  window.navigate = navigate;

  // ── Anima barras de progresso ao entrar na tela ───────────────
  function animateProgressBars(container) {
    const bars = (container || document).querySelectorAll('.progress-fill[data-pct]');
    bars.forEach(bar => {
      const pct = parseFloat(bar.dataset.pct) || 0;
      bar.style.width = '0%';
      requestAnimationFrame(() => {
        setTimeout(() => { bar.style.width = pct + '%'; }, 60);
      });
    });
  }
  window.animateProgressBars = animateProgressBars;

  // ── Bridge: Python injeta valores ─────────────────────────────
  window.setMetric = function (id, value, unit) {
    const el = document.querySelector(`[data-metric="${id}"] .metric-value`);
    if (el) el.textContent = value;
    const unitEl = document.querySelector(`[data-metric="${id}"] .metric-unit`);
    if (unit !== undefined && unitEl) unitEl.textContent = ' ' + unit;
    const bar = document.querySelector(`[data-metric="${id}"] .progress-fill`);
    if (bar) {
      bar.dataset.pct = value;
      bar.style.width = value + '%';
      const pct = parseFloat(value);
      bar.classList.toggle('danger', pct > 90);
      bar.classList.toggle('warn',   pct > 75 && pct <= 90);
    }
  };

  window.setText = function (selector, text) {
    document.querySelectorAll(selector).forEach(el => el.textContent = text);
  };

  window.setStatus = function (text, kind) {
    const bar = document.querySelector('.screen.active .status-bar');
    if (!bar) return;
    bar.textContent = text;
    bar.classList.toggle('muted', kind === 'muted');
  };

  window.appendTerminalLine = function (text, kind) {
    const term = document.querySelector('.screen.active .terminal');
    if (!term) return;
    const line = document.createElement('div');
    line.className = 'terminal-line' + (kind ? ' ' + kind : '');
    line.textContent = text;
    term.appendChild(line);
    term.scrollTop = term.scrollHeight;
  };

  window.clearTerminal = function () {
    document.querySelectorAll('.terminal').forEach(t => t.innerHTML = '');
  };

  // ── Gamer mode ────────────────────────────────────────────────
  window.setGamerMode = function (active) {
    document.body.classList.toggle('gamer-active', !!active);
    const hero = document.getElementById('gamer-hero-status');
    if (hero) {
      hero.textContent = active ? '● ATIVO' : '● INATIVO';
      hero.style.color = active ? 'var(--state-on)' : 'var(--purple)';
      hero.style.textShadow = active
        ? '0 0 14px rgba(76,175,80,0.5)'
        : '0 0 14px rgba(112,0,255,0.5)';
    }
    const card = document.getElementById('gamer-hero-card');
    if (card) {
      card.classList.toggle('green', active);
      card.classList.toggle('purple', !active);
    }
    const sub = document.getElementById('gamer-hero-sub');
    if (sub) sub.textContent = active
      ? 'Tweaks aplicados — clique em Desativar para reverter'
      : 'Pronto para ativar — todos os tweaks são reversíveis';

    const btnGroup = document.getElementById('gamer-btn-group');
    if (btnGroup) {
      btnGroup.innerHTML = active
        ? '<button class="btn-revert" onclick="window.bridge?.onGamerDeactivate?.()">DESATIVAR</button>'
        : '<button class="btn-gamer" onclick="window.bridge?.onGamerActivate?.()">ATIVAR MODO GAMER</button>';
    }

    document.querySelectorAll('.tweak-dot').forEach(d => {
      const optIn = d.dataset.optin === 'true';
      const checked = d.parentElement.querySelector('input[type="checkbox"]')?.checked;
      const on = active && (!optIn || checked);
      d.style.background = on ? 'var(--state-on)' : '#333';
    });
  };

  // ── Toggle wiring ──────────────────────────────────────────────
  document.addEventListener('change', e => {
    if (e.target.matches('.toggle input')) {
      const id = e.target.dataset.id;
      if (window.bridge && window.bridge.onToggle) {
        window.bridge.onToggle(id, e.target.checked);
      }
    }
  });

  // ── Trigger animations ao trocar de tela ──────────────────────
  const observer = new MutationObserver(muts => {
    for (const m of muts) {
      if (m.attributeName === 'class' && m.target.classList.contains('active')) {
        animateProgressBars(m.target);
      }
    }
  });
  document.querySelectorAll('.screen').forEach(s => {
    observer.observe(s, { attributes: true });
  });

  // ── data-bind: preenche spans de texto ────────────────────────
  window.setBind = function (key, text) {
    document.querySelectorAll(`[data-bind="${key}"]`)
      .forEach(el => el.textContent = text);
  };

  // ── Formatadores ──────────────────────────────────────────────
  function fmtBytes(b) {
    if (!b || b <= 0) return '—';
    const gb = b / (1024 ** 3);
    if (gb >= 1) return gb.toFixed(1) + ' GB';
    return (b / (1024 ** 2)).toFixed(0) + ' MB';
  }

  // ── Aplica o snapshot vindo do Python ─────────────────────────
  function applySnapshot(s) {
    if (!s) return;

    // Cards do dashboard
    setMetric('cpu',  Math.round(s.cpu.pct));
    setMetric('ram',  Math.round(s.ram.pct));
    setMetric('disk', Math.round(s.disk.pct));

    // Processos: sem barra, so o numero
    const procEl = document.querySelector('[data-metric="proc"] .metric-value');
    if (procEl) procEl.textContent = s.proc;

    // Subtitulos dos cards
    setBind('cpu_sub',  `${s.cpu.threads} threads · ${s.cpu.freq}`);
    setBind('ram_sub',  `${fmtBytes(s.ram.used)} / ${fmtBytes(s.ram.total)}`);
    setBind('disk_sub', `${fmtBytes(s.disk.used)} / ${fmtBytes(s.disk.total)}`);

    // Header
    setBind('user',   s.os.user);
    setBind('os',     s.os.system);
    setBind('uptime', s.uptime);

    // Painel SISTEMA
    setBind('cpu_name', s.cpu.name);
    setBind('ram_info', `${fmtBytes(s.ram.used)} / ${fmtBytes(s.ram.total)} (${Math.round(s.ram.pct)}%)`);
    setBind('os_full',  `${s.os.system} · ${s.os.machine}`);

    // Espelha na tela de especificacoes
    setMetric('spec_cpu',  Math.round(s.cpu.pct));
    setMetric('spec_ram',  Math.round(s.ram.pct));
    setMetric('spec_disk', Math.round(s.disk.pct));
    setBind('spec_proc', s.proc);
    setBind('hw_cpu', s.cpu.name);
    setBind('hw_ram', `${fmtBytes(s.ram.total)} total`);
    setBind('hw_os',  `${s.os.system} (${s.os.version})`);
    setBind('hw_disk', `${fmtBytes(s.disk.used)} / ${fmtBytes(s.disk.total)}`);
  }
  window.applySnapshot = applySnapshot;

  // ── Hardware lento (GPU / placa-mae) ──────────────────────────
  function applyHardware(hw) {
    if (!hw) return;
    setBind('hw_gpu',  hw.gpu_name || '—');
    setBind('hw_mobo', `${hw.mobo_manufacturer || '—'} ${hw.mobo_model || ''}`.trim());
  }

  // ── Updater ───────────────────────────────────────────────────
  let updatePending = false;

  function showUpdateBanner(info) {
    if (!info) return;
    updatePending = true;
    const el = document.getElementById('update-banner');
    const tx = document.getElementById('update-text');
    if (tx) {
      const mb = info.size ? ` (${(info.size / (1024 * 1024)).toFixed(0)} MB)` : '';
      tx.textContent = `Nova versao ${info.version} disponivel${mb}`;
    }
    if (el) el.style.display = 'flex';
  }

  window.startUpdate = function () {
    if (!updatePending || !window.bridge) return;
    const btn = document.getElementById('update-btn');
    if (btn) { btn.disabled = true; btn.textContent = 'BAIXANDO...'; }
    window.bridge.downloadUpdate();
  };

  function onUpdateProgress(pct) {
    const el = document.getElementById('update-pct');
    if (el) el.textContent = pct + '%';
  }

  function onUpdateStatus(msg) {
    const tx = document.getElementById('update-text');
    if (tx) tx.textContent = msg;
    // Mensagens informativas (sem update) nao abrem o banner
  }

  // ── Debloat ───────────────────────────────────────────────────
  let bloatItems = [];
  const bloatChecked = new Set();

  function riskLabel(r) {
    return r === 'safe'
      ? '<span style="color:var(--state-on);font-size:9px;font-weight:700">SEGURO</span>'
      : '<span style="color:#e8a33d;font-size:9px;font-weight:700">ATENCAO</span>';
  }

  // Agrupa por fabricante: 5 itens Xbox soltos enchem a tela e forcam
  // scroll desnecessario. Agrupado, cada bloco colapsa em uma linha.
  function groupOf(it) {
    const n = (it.name + ' ' + (it.publisher || '')).toLowerCase();
    if (n.includes('xbox') || n.includes('gaming')) return 'Xbox / Games';
    if (n.includes('dell'))    return 'Dell';
    if (n.includes('lenovo'))  return 'Lenovo';
    if (n.includes('hp '))     return 'HP';
    if (n.includes('asus'))    return 'ASUS';
    if (n.includes('acer'))    return 'Acer';
    if (n.includes('microsoft') || n.includes('zune') || n.includes('bing')) return 'Apps do Windows';
    return 'Outros';
  }

  const collapsed = new Set();

  window.toggleGroup = function (name) {
    if (collapsed.has(name)) collapsed.delete(name); else collapsed.add(name);
    renderBloat();
  };

  window.toggleGroupCheck = function (ev, name) {
    ev.stopPropagation();
    const items = bloatItems.filter(i => groupOf(i) === name);
    const allOn = items.every(i => bloatChecked.has(i.name));
    items.forEach(i => allOn ? bloatChecked.delete(i.name) : bloatChecked.add(i.name));
    renderBloat();
  };

  function renderBloat() {
    const box = document.getElementById('debloat-list');
    if (!box) return;

    if (!bloatItems.length) {
      box.innerHTML = '<div style="padding:24px;text-align:center;color:var(--fg-muted);font-size:11px">'
        + 'Nenhum bloatware conhecido encontrado neste PC.</div>';
      return;
    }

    // Preserva a ordem de tamanho ja aplicada pelo scanner
    const groups = [];
    const byName = {};
    bloatItems.forEach(it => {
      const g = groupOf(it);
      if (!byName[g]) { byName[g] = []; groups.push(g); }
      byName[g].push(it);
    });

    box.innerHTML = groups.map(g => {
      const items = byName[g];
      const mb = items.reduce((a, i) => a + (i.size_mb || 0), 0);
      const nOn = items.filter(i => bloatChecked.has(i.name)).length;
      const isOpen = !collapsed.has(g);
      const allOn = nOn === items.length;

      const head = `
        <div onclick="window.toggleGroup('${g}')"
             style="display:flex;gap:10px;align-items:center;padding:9px 14px;cursor:pointer;
                    background:rgba(255,255,255,.02);border-bottom:1px solid var(--border-subtle);
                    position:sticky;top:0;z-index:2;backdrop-filter:blur(6px)">
          <input type="checkbox" ${allOn ? 'checked' : ''}
                 onclick="window.toggleGroupCheck(event, '${g}')"
                 style="flex-shrink:0;cursor:pointer">
          <span style="flex:1;font-size:11px;font-weight:700;color:var(--fg-primary)">
            ${g}
            <span style="font-weight:400;color:var(--fg-muted)">· ${items.length}${mb > 0 ? ' · ' + mb + ' MB' : ''}</span>
          </span>
          ${nOn ? `<span style="font-size:9px;color:var(--cyan);font-weight:700">${nOn} SEL.</span>` : ''}
          <span style="font-size:10px;color:var(--fg-muted);transition:transform .15s;
                       transform:rotate(${isOpen ? 90 : 0}deg);display:inline-block">&#9656;</span>
        </div>`;

      if (!isOpen) return head;

      const rows = items.map(it => {
        const idx = bloatItems.indexOf(it);
        const size = it.size_mb > 0 ? it.size_mb + ' MB' : '&mdash;';
        const on = bloatChecked.has(it.name) ? 'checked' : '';
        return `
          <label style="display:flex;gap:12px;align-items:flex-start;padding:9px 14px 9px 30px;
                        border-bottom:1px solid var(--border-subtle);cursor:pointer">
            <input type="checkbox" data-bloat="${idx}" ${on} style="margin-top:3px;flex-shrink:0">
            <span style="flex:1;min-width:0">
              <span style="display:flex;gap:8px;align-items:baseline">
                <span style="font-size:11px;color:var(--fg-primary);font-weight:600;
                             overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${it.name}</span>
                ${riskLabel(it.risk)}
              </span>
              <span style="display:block;font-size:10px;color:var(--fg-muted);margin-top:2px">${it.why || ''}</span>
            </span>
            <span class="mono" style="font-size:10px;color:var(--fg-secondary);flex-shrink:0">${size}</span>
          </label>`;
      }).join('');

      return head + rows;
    }).join('');

    box.querySelectorAll('input[data-bloat]').forEach(cb => {
      cb.addEventListener('change', e => {
        const it = bloatItems[parseInt(e.target.dataset.bloat, 10)];
        if (!it) return;
        if (e.target.checked) bloatChecked.add(it.name); else bloatChecked.delete(it.name);
        updateBloatButton();
      });
    });
    updateBloatButton();
  }

  function updateBloatButton() {
    const btn = document.getElementById('debloat-btn');
    if (!btn) return;
    const n = bloatChecked.size;
    const mb = bloatItems.filter(i => bloatChecked.has(i.name))
                         .reduce((a, i) => a + (i.size_mb || 0), 0);
    btn.disabled = n === 0;
    btn.style.opacity = n === 0 ? '.4' : '1';
    btn.style.cursor = n === 0 ? 'not-allowed' : 'pointer';
    btn.textContent = n === 0
      ? 'REMOVER SELECIONADOS'
      : `REMOVER ${n} ${n === 1 ? 'ITEM' : 'ITENS'}${mb > 0 ? ' (' + mb + ' MB)' : ''}`;
  }

  function onBloatScanned(res) {
    if (!res) return;
    bloatItems = res.items || [];
    bloatChecked.clear();
    const mb = res.total_mb || 0;
    setBind('debloat_summary', bloatItems.length
      ? `${bloatItems.length} programas encontrados${mb > 0 ? ' · ' + mb + ' MB' : ''}`
      : 'Nenhum bloatware conhecido encontrado');
    renderBloat();
  }

  window.debloatSelect = function (mode) {
    bloatChecked.clear();
    if (mode === 'safe') {
      bloatItems.filter(i => i.risk === 'safe').forEach(i => bloatChecked.add(i.name));
    }
    renderBloat();
  };

  window.debloatRemove = function () {
    if (!window.bridge || !bloatChecked.size) return;
    const n = bloatChecked.size;
    const msg = 'Remover ' + n + (n === 1 ? ' programa' : ' programas') + '?'
      + '\n\nUm ponto de restauracao sera criado antes.'
      + '\nDesinstalar nao pode ser desfeito pelo app.';
    tecConfirm({
      title: 'Remover ' + n + (n === 1 ? ' programa' : ' programas') + '?',
      body: 'Um ponto de restauracao sera criado antes.\n'
          + 'Desinstalar nao pode ser desfeito pelo app.',
      yes: 'REMOVER',
      danger: true
    }, function () {
      const btn = document.getElementById('debloat-btn');
      if (btn) { btn.disabled = true; btn.style.opacity = '.4'; }
      window.bridge.removeBloatware(Array.from(bloatChecked));
    });
  };

  function onBloatProgress(cur, total, name) {
    setBind('debloat_status', `Removendo ${cur}/${total}: ${name}`);
  }

  function onBloatFinished(sum) {
    if (!sum) return;
    const parts = [`${sum.removed} removido(s)`];
    if (sum.freed_mb > 0) parts.push(`${sum.freed_mb} MB liberados`);
    if (sum.failed > 0)   parts.push(`${sum.failed} falhou(ram)`);
    setBind('debloat_status', parts.join(' · '));
  }

  // ── Limpeza ───────────────────────────────────────────────────
  let cleanCats = [];
  const cleanChecked = new Set();

  function renderCleanConfig() {
    const box = document.getElementById('clean-config-list');
    if (!box) return;

    if (!cleanCats.length) {
      box.innerHTML = '<div style="padding:24px;text-align:center;color:var(--fg-muted);'
        + 'font-size:11px">Nao foi possivel carregar as categorias.</div>';
      return;
    }

    box.innerHTML = cleanCats.map((c, i) => {
      const on = cleanChecked.has(c.id) ? 'checked' : '';
      const warn = c.warning
        ? `<span style="display:block;font-size:10px;color:#e8a33d;margin-top:3px">&#9888; ${c.warning}</span>`
        : '';
      return `
        <label style="display:flex;gap:12px;align-items:flex-start;padding:11px 14px;
                      border-bottom:1px solid var(--border-subtle);cursor:pointer">
          <input type="checkbox" data-clean="${i}" ${on} style="margin-top:3px;flex-shrink:0">
          <span style="flex:1;min-width:0">
            <span style="display:flex;gap:8px;align-items:baseline;flex-wrap:wrap">
              <span style="font-size:11px;color:var(--fg-primary);font-weight:600">${c.label}</span>
              ${c.default ? '<span style="font-size:9px;color:var(--state-on);font-weight:700">RECOMENDADO</span>' : ''}
            </span>
            <span style="display:block;font-size:10px;color:var(--fg-muted);margin-top:2px;line-height:1.5">${c.desc || ''}</span>
            ${warn}
          </span>
          <span class="mono" style="font-size:10px;color:var(--fg-secondary);flex-shrink:0;white-space:nowrap">${c.impact || ''}</span>
        </label>`;
    }).join('');

    box.querySelectorAll('input[data-clean]').forEach(cb => {
      cb.addEventListener('change', e => {
        const c = cleanCats[parseInt(e.target.dataset.clean, 10)];
        if (!c) return;
        if (e.target.checked) cleanChecked.add(c.id); else cleanChecked.delete(c.id);
        persistClean();
        updateCleanCounts();
      });
    });
    updateCleanCounts();
  }

  function updateCleanCounts() {
    const n = cleanChecked.size, t = cleanCats.length;
    setBind('clean_active', String(n));
    setBind('clean_total', String(t));
    setBind('cfg_summary', `${n} de ${t} categorias ativas`);
  }

  function persistClean() {
    if (window.bridge && window.bridge.setCleanSelection) {
      window.bridge.setCleanSelection(Array.from(cleanChecked));
    }
  }

  function onCleanCategories(r) {
    if (!r || !r.categories) return;
    cleanCats = r.categories;
    cleanChecked.clear();
    cleanCats.forEach(c => { if (c.checked) cleanChecked.add(c.id); });
    if (r.last_clean) setBind('clean_status', 'Ultima limpeza: ' + r.last_clean);
    renderCleanConfig();
  }

  window.cleanSelect = function (mode) {
    cleanChecked.clear();
    if (mode === 'all')     cleanCats.forEach(c => cleanChecked.add(c.id));
    if (mode === 'default') cleanCats.filter(c => c.default).forEach(c => cleanChecked.add(c.id));
    persistClean();
    renderCleanConfig();
  };

  window.cleanStart = function () {
    if (!window.bridge) return;
    if (!cleanChecked.size) {
      setBind('cfg_status', 'Selecione ao menos uma categoria.');
      return;
    }
    persistClean();
    window.cleanRunQuick();
  };

  // ── Progresso da limpeza (inline, sem janela separada) ────────
  function cleanTerminal() {
    return document.getElementById('clean-terminal');
  }

  function cleanSetRunning(on) {
    document.querySelectorAll('#screen-limpeza .btn-primary, #screen-limpeza .btn-secondary,'
      + ' #screen-limpeza-config .btn-primary').forEach(b => {
      b.disabled = on;
      b.style.opacity = on ? '.5' : '1';
      b.style.cursor = on ? 'not-allowed' : 'pointer';
    });
  }

  function onCleanStep(label, freed) {
    const t = cleanTerminal();
    if (!t) return;
    t.style.display = 'block';
    const mb = freed > 0 ? ' — ' + (freed / (1024 * 1024)).toFixed(1) + ' MB' : '';
    const line = document.createElement('div');
    line.className = 'terminal-line';
    line.textContent = '> ' + label + mb;
    t.appendChild(line);
    t.scrollTop = t.scrollHeight;
  }

  function onCleanCalculating() {
    const t = cleanTerminal();
    if (!t) return;
    t.style.display = 'block';
    const line = document.createElement('div');
    line.className = 'terminal-line';
    line.textContent = '> calculando espaco liberado...';
    t.appendChild(line);
    t.scrollTop = t.scrollHeight;
  }

  function onCleanFinished(r) {
    cleanSetRunning(false);
    const t = cleanTerminal();
    if (t) {
      const line = document.createElement('div');
      line.className = 'terminal-line';
      line.style.color = 'var(--state-on)';
      line.textContent = r && r.ok
        ? '> concluido — ' + (r.human || '0 B') + ' liberados'
        : '> falha na limpeza';
      t.appendChild(line);
      t.scrollTop = t.scrollHeight;
    }
    if (r && r.ok) {
      setBind('clean_status', 'Ultima limpeza: agora — ' + (r.human || '') + ' liberados');
    }
    // Volta para a tela de limpeza se o usuario estava na configuracao
    const cfg = document.getElementById('screen-limpeza-config');
    if (cfg && cfg.classList.contains('active')) navigate('limpeza');
  }

  window.cleanRunQuick = function () {
    if (!window.bridge || !window.bridge.startCleanWith) return;
    const t = cleanTerminal();
    if (t) { t.innerHTML = ''; t.style.display = 'block'; }
    cleanSetRunning(true);
    navigate('limpeza');
    window.bridge.startCleanWith(Array.from(cleanChecked));
  };

  // -- Terminal generico inline --------------------------------
  function termLine(id, text, color) {
    const t = document.getElementById(id);
    if (!t) return;
    t.style.display = 'block';
    const d = document.createElement('div');
    d.className = 'terminal-line';
    if (color) d.style.color = color;
    d.textContent = text;
    t.appendChild(d);
    t.scrollTop = t.scrollHeight;
  }

  function termClear(id) {
    const t = document.getElementById(id);
    if (t) { t.innerHTML = ''; t.style.display = 'block'; }
  }

  // -- Reparos --------------------------------------------------
  let repairTools = [];
  let repairBusy = false;

  function onRepairTools(list) { repairTools = list || []; }

  window.runRepair = function (toolId) {
    if (!window.bridge || !window.bridge.onRunRepair || repairBusy) return;
    const tool = repairTools.find(function (t) { return t.id === toolId; });
    const label = tool ? tool.label : toolId;

    let msg = '';
    if (tool) {
      if (tool.duration) msg += 'Duracao estimada: ' + tool.duration + '\n\n';
      if (tool.warning)  msg += tool.warning + '\n\n';
      if (tool.reboot)   msg += 'Este reparo exige reiniciar o computador depois.';
    }
    tecConfirm({
      title: label,
      body: msg.trim(),
      yes: 'EXECUTAR',
      danger: !!(tool && (tool.reboot || tool.warning))
    }, function () {
      repairBusy = true;
      document.querySelectorAll('#screen-reparos .btn-apply').forEach(function (b) {
        b.disabled = true; b.style.opacity = '.5'; b.style.cursor = 'not-allowed';
      });
      termClear('repair-terminal');
      termLine('repair-terminal', '> iniciando: ' + label);
      setBind('repair_status', 'Reparo em andamento...');
      window.bridge.onRunRepair(toolId);
    });
  };

  function onRepairStep(label, ok, detail) {
    termLine('repair-terminal', (ok ? '> ' : '! ') + label + (detail ? ' - ' + detail : ''),
             ok ? null : '#e8a33d');
  }

  function onRepairFinished(r) {
    repairBusy = false;
    document.querySelectorAll('#screen-reparos .btn-apply').forEach(function (b) {
      b.disabled = false; b.style.opacity = '1'; b.style.cursor = 'pointer';
    });
    const ok = r && r.ok;
    termLine('repair-terminal', ok ? '> concluido' : '> concluido com falhas',
             ok ? 'var(--state-on)' : '#e8a33d');
    setBind('repair_status', (r && r.summary) || (ok ? 'Reparo concluido.' : 'Reparo falhou.'));
  }

  function onRepairStatus(msg) { setBind('repair_status', msg); }

  // -- Otimizacao -----------------------------------------------
  let optCats = [];
  const optChecked = new Set();

  function renderOpt() {
    const box = document.getElementById('opt-list');
    if (!box) return;
    if (!optCats.length) {
      box.innerHTML = '<div style="padding:24px;text-align:center;color:var(--fg-muted);'
        + 'font-size:11px">Nao foi possivel carregar as otimizacoes.</div>';
      return;
    }
    box.innerHTML = optCats.map(function (c, i) {
      const on = optChecked.has(c.id) ? 'checked' : '';
      const warn = c.warning
        ? '<span style="display:block;font-size:10px;color:#e8a33d;margin-top:3px">&#9888; ' + c.warning + '</span>'
        : '';
      const rec = c.default
        ? '<span style="font-size:9px;color:var(--state-on);font-weight:700">RECOMENDADO</span>'
        : '';
      return '<label style="display:flex;gap:12px;align-items:flex-start;padding:11px 14px;'
        + 'border-bottom:1px solid var(--border-subtle);cursor:pointer">'
        + '<input type="checkbox" data-opt="' + i + '" ' + on + ' style="margin-top:3px;flex-shrink:0">'
        + '<span style="flex:1;min-width:0">'
        + '<span style="display:flex;gap:8px;align-items:baseline;flex-wrap:wrap">'
        + '<span style="font-size:11px;color:var(--fg-primary);font-weight:600">' + c.label + '</span>'
        + rec + '</span>'
        + '<span style="display:block;font-size:10px;color:var(--fg-muted);margin-top:2px;line-height:1.5">'
        + (c.desc || '') + '</span>' + warn + '</span>'
        + '<span class="mono" style="font-size:10px;color:var(--fg-secondary);flex-shrink:0">'
        + (c.impact || '') + '</span></label>';
    }).join('');

    box.querySelectorAll('input[data-opt]').forEach(function (cb) {
      cb.addEventListener('change', function (e) {
        const c = optCats[parseInt(e.target.dataset.opt, 10)];
        if (!c) return;
        if (e.target.checked) optChecked.add(c.id); else optChecked.delete(c.id);
        if (window.bridge && window.bridge.setOptimizeSelection) {
          window.bridge.setOptimizeSelection(Array.from(optChecked));
        }
        updateOptCounts();
      });
    });
    updateOptCounts();
  }

  function updateOptCounts() {
    setBind('opt_active', String(optChecked.size));
    setBind('opt_total', String(optCats.length));
    setBind('opt_hint', optChecked.size ? '' : 'Selecione ao menos uma otimizacao.');
  }

  function onOptimizeCategories(r) {
    if (!r || !r.categories) return;
    optCats = r.categories;
    optChecked.clear();
    optCats.forEach(function (c) { if (c.checked) optChecked.add(c.id); });
    renderOpt();
  }

  window.optSelect = function (mode) {
    optChecked.clear();
    if (mode === 'all') {
      optCats.forEach(function (c) { optChecked.add(c.id); });
    }
    if (mode === 'default') {
      optCats.filter(function (c) { return c.default; })
             .forEach(function (c) { optChecked.add(c.id); });
    }
    if (window.bridge && window.bridge.setOptimizeSelection) {
      window.bridge.setOptimizeSelection(Array.from(optChecked));
    }
    renderOpt();
  };

  window.optRun = function () {
    if (!window.bridge || !window.bridge.startOptimize) return;
    if (!optChecked.size) { setBind('opt_hint', 'Selecione ao menos uma otimizacao.'); return; }
    const btn = document.getElementById('opt-btn');
    if (btn) { btn.disabled = true; btn.style.opacity = '.5'; btn.textContent = 'APLICANDO...'; }
    termClear('opt-terminal');
    termLine('opt-terminal', '> aplicando otimizacoes...');
    window.bridge.startOptimize(Array.from(optChecked), 'apply');
  };

  function onOptimizeStep(label, ok, detail) {
    termLine('opt-terminal', (ok ? '> ' : '! ') + label + (detail ? ' - ' + detail : ''),
             ok ? null : '#e8a33d');
  }

  function onOptimizeFinished(r) {
    const btn = document.getElementById('opt-btn');
    if (btn) { btn.disabled = false; btn.style.opacity = '1'; btn.textContent = 'APLICAR OTIMIZACOES'; }
    if (!r) return;
    const parts = [r.applied + ' aplicada(s)'];
    if (r.failed > 0) parts.push(r.failed + ' falhou(ram)');
    termLine('opt-terminal', '> concluido - ' + parts.join(' | '), 'var(--state-on)');
    setBind('opt_status', parts.join(' | '));
  }

  // -- Limpeza profunda (cleanmgr) ------------------------------
  let deepCats = [];
  const deepChecked = new Set();

  function renderDeep() {
    const box = document.getElementById('deep-list');
    if (!box) return;
    if (!deepCats.length) {
      box.innerHTML = '<div style="padding:24px;text-align:center;color:var(--fg-muted);'
        + 'font-size:11px">Nao foi possivel listar as categorias.</div>';
      return;
    }
    box.innerHTML = deepCats.map(function (c, i) {
      const on = deepChecked.has(c.id) ? 'checked' : '';
      const warn = c.warning
        ? '<span style="display:block;font-size:10px;color:#e8a33d;margin-top:3px">&#9888; '
          + c.warning + '</span>'
        : '';
      const rec = c.default
        ? '<span style="font-size:9px;color:var(--state-on);font-weight:700">RECOMENDADO</span>'
        : '';
      return '<label style="display:flex;gap:12px;align-items:flex-start;padding:11px 14px;'
        + 'border-bottom:1px solid var(--border-subtle);cursor:pointer">'
        + '<input type="checkbox" data-deep="' + i + '" ' + on + ' style="margin-top:3px;flex-shrink:0">'
        + '<span style="flex:1;min-width:0">'
        + '<span style="display:flex;gap:8px;align-items:baseline;flex-wrap:wrap">'
        + '<span style="font-size:11px;color:var(--fg-primary);font-weight:600">' + c.label + '</span>'
        + rec + '</span>'
        + '<span style="display:block;font-size:10px;color:var(--fg-muted);margin-top:2px;line-height:1.5">'
        + (c.desc || '') + '</span>' + warn + '</span></label>';
    }).join('');

    box.querySelectorAll('input[data-deep]').forEach(function (cb) {
      cb.addEventListener('change', function (e) {
        const c = deepCats[parseInt(e.target.dataset.deep, 10)];
        if (!c) return;
        if (e.target.checked) deepChecked.add(c.id); else deepChecked.delete(c.id);
        updateDeepCounts();
      });
    });
    updateDeepCounts();
  }

  function updateDeepCounts() {
    setBind('deep_summary', deepChecked.size + ' de ' + deepCats.length + ' categorias marcadas');
    // Alimenta tambem o card da tela de Limpeza
    setBind('deep_active', String(deepChecked.size));
    setBind('deep_total', String(deepCats.length));
  }

  // Roda a limpeza profunda direto do card, sem passar pela tela de
  // configuracao — mas mostrando o progresso la, que e onde esta o terminal.
  window.deepRunFromHome = function () {
    navigate('limpeza-profunda');
    setTimeout(function () { window.deepRun(); }, 120);
  };

  function onDeepCategories(r) {
    if (!r || !r.categories) return;
    deepCats = r.categories;
    deepChecked.clear();
    deepCats.forEach(function (c) { if (c.checked) deepChecked.add(c.id); });
    renderDeep();
  }

  window.deepSelect = function (mode) {
    deepChecked.clear();
    if (mode === 'default') {
      deepCats.filter(function (c) { return c.default; })
              .forEach(function (c) { deepChecked.add(c.id); });
    }
    renderDeep();
  };

  window.deepRun = function () {
    if (!window.bridge || !window.bridge.startDeepClean) return;
    if (!deepChecked.size) { setBind('deep_status', 'Selecione ao menos uma categoria.'); return; }

    const perigosos = deepCats.filter(function (c) {
      return deepChecked.has(c.id) && c.warning;
    });
    let msg = '';
    if (perigosos.length) {
      msg += 'Itens sem volta selecionados:\n';
      perigosos.forEach(function (c) { msg += '   - ' + c.label + '\n'; });
      msg += '\n';
    }
    msg += 'Pode levar varios minutos sem mostrar progresso detalhado.';
    tecConfirm({
      title: 'Iniciar limpeza profunda com ' + deepChecked.size + ' categorias?',
      body: msg,
      yes: 'INICIAR LIMPEZA',
      danger: perigosos.length > 0
    }, function () {
      const btn = document.getElementById('deep-btn');
      if (btn) { btn.disabled = true; btn.style.opacity = '.5'; btn.textContent = 'LIMPANDO...'; }
      termClear('deep-terminal');
      termLine('deep-terminal', '> iniciando limpeza profunda...');
      window.bridge.startDeepClean(Array.from(deepChecked));
    });
  };

  function onDeepStep(label) {
    termLine('deep-terminal', '> ' + label);
  }

  function onDeepFinished(r) {
    const btn = document.getElementById('deep-btn');
    if (btn) { btn.disabled = false; btn.style.opacity = '1'; btn.textContent = 'INICIAR LIMPEZA PROFUNDA'; }
    if (!r) return;
    termLine('deep-terminal', '> ' + (r.msg || (r.ok ? 'concluido' : 'falhou')),
             r.ok ? 'var(--state-on)' : '#e8a33d');
    setBind('deep_status', r.msg || '');
  }

  window.onDeepStep = onDeepStep;
  window.onDeepFinished = onDeepFinished;

  // Expostos em window: o Python empurra o progresso via runJavaScript
  // porque os sinais de progresso do QWebChannel nao chegavam ao JS.
  window.onCleanStep = onCleanStep;
  window.onCleanCalculating = onCleanCalculating;
  window.onCleanFinished = onCleanFinished;
  window.onRepairStep = onRepairStep;
  window.onRepairFinished = onRepairFinished;
  window.onOptimizeStep = onOptimizeStep;
  window.onOptimizeFinished = onOptimizeFinished;

  // ── Conecta a bridge Qt ───────────────────────────────────────
  function connectBridge() {
    const b = window.bridge;
    if (!b) return false;

    if (b.metricsUpdated && b.metricsUpdated.connect) {
      b.metricsUpdated.connect(applySnapshot);
    }

    if (b.cleanStep && b.cleanStep.connect)               b.cleanStep.connect(onCleanStep);
    if (b.cleanCalculating && b.cleanCalculating.connect) b.cleanCalculating.connect(onCleanCalculating);
    if (b.cleanFinished && b.cleanFinished.connect)       b.cleanFinished.connect(onCleanFinished);

    if (b.repairStep && b.repairStep.connect)             b.repairStep.connect(onRepairStep);
    if (b.repairFinished && b.repairFinished.connect)     b.repairFinished.connect(onRepairFinished);
    if (b.repairStatus && b.repairStatus.connect)         b.repairStatus.connect(onRepairStatus);
    if (b.optimizeStep && b.optimizeStep.connect)         b.optimizeStep.connect(onOptimizeStep);
    if (b.optimizeFinished && b.optimizeFinished.connect) b.optimizeFinished.connect(onOptimizeFinished);

    if (b.hardwareReady && b.hardwareReady.connect) {
      b.hardwareReady.connect(applyHardware);
    }
    // Snapshot imediato — nao espera o primeiro tick de 1s
    if (b.updateAvailable && b.updateAvailable.connect) {
      b.updateAvailable.connect(showUpdateBanner);
    }
    if (b.updateProgress && b.updateProgress.connect) {
      b.updateProgress.connect(onUpdateProgress);
    }
    if (b.updateStatus && b.updateStatus.connect) {
      b.updateStatus.connect(onUpdateStatus);
    }

    if (b.bloatScanned && b.bloatScanned.connect) {
      b.bloatScanned.connect(onBloatScanned);
    }
    if (b.bloatProgress && b.bloatProgress.connect) {
      b.bloatProgress.connect(onBloatProgress);
    }
    if (b.bloatFinished && b.bloatFinished.connect) {
      b.bloatFinished.connect(onBloatFinished);
    }
    // O scan comeca quando a Bridge nasce, antes de a pagina carregar.
    // Se ele terminou nesse meio tempo o sinal ja passou, entao buscamos
    // o resultado; se ainda estiver rodando, o sinal acima cobre. O
    // polling e a rede de seguranca para os dois casos.
    if (b.getBloatware) {
      let tries = 0;
      const poll = () => {
        b.getBloatware(r => {
          if (r && r.items) {
            onBloatScanned(r);
          } else if (++tries < 40) {
            setTimeout(poll, 400);
          } else {
            setBind('debloat_summary', 'Nao foi possivel analisar o sistema.');
            const box = document.getElementById('debloat-list');
            if (box) box.innerHTML = '<div style="padding:24px;text-align:center;'
              + 'color:var(--fg-muted);font-size:11px">Falha ao analisar. '
              + 'Reabra o app para tentar de novo.</div>';
          }
        });
      };
      poll();
    }

    if (b.getRepairTools)        b.getRepairTools(onRepairTools);
    if (b.getOptimizeCategories) b.getOptimizeCategories(onOptimizeCategories);
    if (b.getDeepCleanCategories) b.getDeepCleanCategories(onDeepCategories);
    if (b.getCleanCategories)    b.getCleanCategories(onCleanCategories);

    if (b.getInitialSnapshot) b.getInitialSnapshot(applySnapshot);
    if (b.getHardware)        b.getHardware(applyHardware);

    // Versao no rodape + checagem automatica no start
    if (b.getVersion) b.getVersion(v => setText('.version-tag', 'v ' + v + ' · Tecnosup'));
    if (b.checkForUpdates) b.checkForUpdates();

    return true;
  }

  // ── Init ───────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    navigate('home');
    animateProgressBars();

    // A bridge pode nao estar pronta no DOMContentLoaded (o callback do
    // QWebChannel e assincrono). Tenta ate conectar.
    if (!connectBridge()) {
      let tries = 0;
      const iv = setInterval(() => {
        if (connectBridge() || ++tries > 50) clearInterval(iv);
      }, 100);
    }
  });
})();
