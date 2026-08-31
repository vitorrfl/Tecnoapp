/* ───────────────────────────────────────────────────────────────
   Tecnosup — App logic (vanilla JS)
   Qt WebEngine: Python injeta dados via runJavaScript()
   ─────────────────────────────────────────────────────────────── */

(function () {
  'use strict';

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

  function renderBloat() {
    const box = document.getElementById('debloat-list');
    if (!box) return;

    if (!bloatItems.length) {
      box.innerHTML = '<div style="padding:24px;text-align:center;color:var(--fg-muted);font-size:11px">'
        + 'Nenhum bloatware conhecido encontrado neste PC.</div>';
      return;
    }

    box.innerHTML = bloatItems.map((it, idx) => {
      const size = it.size_mb > 0 ? it.size_mb + ' MB' : '—';
      const on = bloatChecked.has(it.name) ? 'checked' : '';
      return `
        <label style="display:flex;gap:12px;align-items:flex-start;padding:9px 14px;
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
    if (!confirm(`Remover ${n} ${n === 1 ? 'programa' : 'programas'}?

`
      + 'Um ponto de restauracao sera criado antes.
'
      + 'Desinstalar nao pode ser desfeito pelo app.')) return;

    const btn = document.getElementById('debloat-btn');
    if (btn) { btn.disabled = true; btn.style.opacity = '.4'; }
    window.bridge.removeBloatware(Array.from(bloatChecked));
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

  // ── Conecta a bridge Qt ───────────────────────────────────────
  function connectBridge() {
    const b = window.bridge;
    if (!b) return false;

    if (b.metricsUpdated && b.metricsUpdated.connect) {
      b.metricsUpdated.connect(applySnapshot);
    }
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
    if (b.getBloatware) b.getBloatware(onBloatScanned);

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
