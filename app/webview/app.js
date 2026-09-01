/* ───────────────────────────────────────────────────────────────
   Tecnosup — App logic (vanilla JS)
   Qt WebEngine: Python injeta dados via runJavaScript()
   ─────────────────────────────────────────────────────────────── */

(function () {
  'use strict';

  // Limites do card de memoria. Ficam no topo porque applySnapshot roda a
  // cada segundo e chama atualizarCardMemoria: declarados mais abaixo,
  // caiam na zona morta temporal do const e o card nunca aparecia.
  const MEM_LIMITE = 75;       // % de RAM a partir do qual vale oferecer
  const MEM_COOLDOWN = 120000; // 2 min — rodar em sequencia nao rende nada
  let memUltimaVez = 0;

  // -- Seletor de processos -------------------------------------
  // Substitui a digitacao do nome do .exe: ninguem sabe que o processo do
  // Valorant chama VALORANT-Win64-Shipping.exe, e um nome digitado errado
  // era salvo sem aviso e nunca funcionava.
  let procAll = [];
  let procFilter = '';
  const procSel = new Set();

  window.openProcessPicker = function () {
    if (!window.bridge || !window.bridge.getAllProcesses) return;
    procSel.clear();
    gameTargets.forEach(function (t) { procSel.add(t); });
    procFilter = '';
    const campo = document.getElementById('proc-filter');
    if (campo) campo.value = '';
    document.getElementById('proc-picker').style.display = 'flex';
    document.getElementById('proc-picker-list').innerHTML =
      '<div style="padding:16px;color:var(--fg-muted);font-size:11px">Lendo processos...</div>';
    window.bridge.getAllProcesses(function (r) {
      procAll = (r && r.processes) || [];
      renderPicker();
    });
  };

  window.closeProcessPicker = function () {
    document.getElementById('proc-picker').style.display = 'none';
  };

  window.filterPicker = function (txt) {
    procFilter = (txt || '').trim().toLowerCase();
    renderPicker();
  };

  function renderPicker() {
    const box = document.getElementById('proc-picker-list');
    if (!box) return;

    const vis = procFilter
      ? procAll.filter(function (p) { return p.name.toLowerCase().indexOf(procFilter) >= 0; })
      : procAll;

    if (!vis.length) {
      box.innerHTML = '<div style="padding:16px;color:var(--fg-muted);font-size:11px">'
        + 'Nenhum processo com esse nome.</div>';
      return;
    }

    box.innerHTML = vis.map(function (p) {
      const i = procAll.indexOf(p);
      const on = procSel.has(p.name) ? 'checked' : '';
      const selo = p.likely_game
        ? '<span style="font-size:9px;color:var(--state-on);font-weight:700">PROVAVEL JOGO</span>'
        : (p.is_system
          ? '<span style="font-size:9px;color:var(--fg-muted)">sistema</span>' : '');
      const inst = p.instances > 1
        ? '<span style="font-size:9px;color:var(--fg-muted)">x' + p.instances + '</span>' : '';
      return '<label style="display:flex;gap:10px;align-items:center;padding:8px 12px;'
        + 'border-bottom:1px solid var(--border-subtle);cursor:pointer">'
        + '<input type="checkbox" data-proc="' + i + '" ' + on + ' style="flex-shrink:0">'
        + '<span style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;'
        + 'white-space:nowrap;font-size:11px;color:var(--fg-primary);font-family:var(--font-mono)">'
        + p.name + '</span>' + inst + selo
        + '<span class="mono" style="font-size:10px;color:var(--fg-secondary);flex-shrink:0;'
        + 'min-width:56px;text-align:right">' + p.mem_mb + ' MB</span></label>';
    }).join('');

    box.querySelectorAll('input[data-proc]').forEach(function (cb) {
      cb.addEventListener('change', function (e) {
        const p = procAll[parseInt(e.target.dataset.proc, 10)];
        if (!p) return;
        if (e.target.checked) procSel.add(p.name); else procSel.delete(p.name);
      });
    });
  }

  window.confirmProcessPicker = function () {
    gameTargets.clear();
    procSel.forEach(function (n) { gameTargets.add(n); });

    // Os escolhidos entram na lista principal, mesmo os que nao vieram da
    // deteccao automatica.
    procSel.forEach(function (nome) {
      const existe = gameCands.some(function (c) {
        return c.name.toLowerCase() === nome.toLowerCase();
      });
      if (!existe) {
        const p = procAll.filter(function (x) { return x.name === nome; })[0];
        gameCands.unshift(p || {
          name: nome, mem_mb: 0, priority: 'nao esta aberto',
          likely_game: false, is_boosted: false
        });
      }
    });

    if (window.bridge && window.bridge.setGameTargets) {
      window.bridge.setGameTargets(Array.from(gameTargets));
    }
    window.closeProcessPicker();
    renderGames();
    atualizarPrioStatus();
  };

  // -- Prioridade de jogo ---------------------------------------
  let gameCands = [];
  const gameTargets = new Set();

  let gameFilter = '';

  function atualizarPrioStatus() {
    setBind('prio_status', gameTargets.size
      ? gameTargets.size + ' processo(s) receberao prioridade alta no Modo Gamer'
      : 'Nenhum processo escolhido.');
  }

  function renderGames() {
    const box = document.getElementById('game-list');
    if (!box) return;

    const visiveis = gameFilter
      ? gameCands.filter(function (c) { return c.name.toLowerCase().indexOf(gameFilter) >= 0; })
      : gameCands;

    if (!visiveis.length) {
      const msg = gameFilter
        ? 'Nenhum processo com esse nome. Clique em ADICIONAR para incluir '
          + '"' + gameFilter + '" mesmo assim.'
        : 'Nenhum processo candidato. Abra o jogo e clique em ATUALIZAR, '
          + 'ou digite o nome do .exe acima.';
      box.innerHTML = '<div style="padding:14px;color:var(--fg-muted);font-size:11px;'
        + 'line-height:1.55">' + msg + '</div>';
      return;
    }

    box.innerHTML = visiveis.map(function (c) {
      const i = gameCands.indexOf(c);
      const on = gameTargets.has(c.name) ? 'checked' : '';
      const selo = c.manual
        ? '<span style="font-size:9px;color:var(--purple);font-weight:700">MANUAL</span>'
        : (c.likely_game
          ? '<span style="font-size:9px;color:var(--state-on);font-weight:700">PROVAVEL JOGO</span>'
          : '');
      const prio = c.is_boosted
        ? '<span style="font-size:9px;color:var(--cyan);font-weight:700">' + c.priority + '</span>'
        : '<span style="font-size:9px;color:var(--fg-muted)">' + c.priority + '</span>';
      const mem = c.mem_mb > 0 ? c.mem_mb + ' MB' : '—';
      return '<label style="display:flex;gap:10px;align-items:center;padding:8px 12px;'
        + 'border-bottom:1px solid var(--border-subtle);cursor:pointer;text-align:left">'
        + '<input type="checkbox" data-game="' + i + '" ' + on + ' style="flex-shrink:0">'
        + '<span style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;'
        + 'white-space:nowrap;font-size:11px;color:var(--fg-primary)">' + c.name + '</span>'
        + selo + prio
        + '<span class="mono" style="font-size:10px;color:var(--fg-secondary);flex-shrink:0;'
        + 'min-width:52px;text-align:right">' + mem + '</span></label>';
    }).join('');

    box.querySelectorAll('input[data-game]').forEach(function (cb) {
      cb.addEventListener('change', function (e) {
        const c = gameCands[parseInt(e.target.dataset.game, 10)];
        if (!c) return;
        if (e.target.checked) gameTargets.add(c.name); else gameTargets.delete(c.name);
        if (window.bridge && window.bridge.setGameTargets) {
          window.bridge.setGameTargets(Array.from(gameTargets));
        }
        atualizarPrioStatus();
      });
    });
  }

  function onGameCandidates(r) {
    if (!r) return;
    gameCands = r.candidates || [];
    gameTargets.clear();
    (r.targets || []).forEach(function (t) { gameTargets.add(t); });

    // Alvos salvos que nao estao rodando agora continuam na lista, senao
    // sumiriam da tela e o usuario nao teria como desmarca-los.
    gameTargets.forEach(function (nome) {
      const existe = gameCands.some(function (c) {
        return c.name.toLowerCase() === nome.toLowerCase();
      });
      if (!existe) {
        gameCands.unshift({
          name: nome, mem_mb: 0, priority: 'nao esta aberto',
          likely_game: false, is_boosted: false, manual: true
        });
      }
    });
    renderGames();
    atualizarPrioStatus();
  }
  window.onGameCandidates = onGameCandidates;

  window.refreshGames = function () {
    if (window.bridge && window.bridge.getGameCandidates) {
      window.bridge.getGameCandidates(onGameCandidates);
    }
  };

  // -- Modal de reboot ------------------------------------------
  window.onAskReboot = function (tweaks) {
    const lista = (tweaks && tweaks.length)
      ? '\n\nTweaks que dependem do reboot:\n   - ' + tweaks.join('\n   - ')
      : '';
    tecConfirm({
      title: 'Reiniciar para aplicar tudo?',
      body: 'Alguns tweaks so entram em efeito depois de reiniciar.\n'
          + 'Os tweaks ja estao salvos e sobrevivem ao reboot.'
          + lista
          + '\n\nSe reiniciar agora, o TecnoApp abre sozinho no Modo Gamer.',
      yes: 'REINICIAR AGORA',
      no: 'DEPOIS'
    }, function () {
      if (window.bridge && window.bridge.rebootNow) window.bridge.rebootNow();
    }, function () {
      if (window.bridge && window.bridge.cancelReboot) window.bridge.cancelReboot();
    });
  };

  window.onRebootFailed = function () {
    tecConfirm({
      title: 'Nao foi possivel reiniciar',
      body: 'Reinicie o computador manualmente quando for conveniente. '
          + 'Os tweaks ja estao salvos.',
      yes: 'ENTENDI'
    });
  };

  // -- Splash de carregamento -----------------------------------
  // As etapas sao reais: cada uma e marcada quando o dado correspondente
  // chega do Python. Uma barra de progresso seria falsa, porque a duracao
  // de cada etapa varia muito por maquina.
  const bootEtapas = {
    bridge: false,   // canal Python<->JS pronto
    metricas: false, // primeiro snapshot de CPU/RAM/disco
    hardware: false, // GPU, placa-mae (consulta WMI, 2-5s)
    programas: false // varredura de bloatware (1-5s)
  };
  let bootFechado = false;

  function bootStep(texto) {
    const el = document.getElementById('boot-step');
    if (el) el.textContent = texto;
  }

  function bootMarcar(etapa, texto) {
    if (bootEtapas[etapa]) return;
    bootEtapas[etapa] = true;
    if (texto) bootStep(texto);
    bootTalvezFechar();
  }

  function bootTalvezFechar() {
    if (bootFechado) return;
    // Hardware e programas sao os lentos; metricas e bridge chegam rapido.
    if (!bootEtapas.bridge || !bootEtapas.metricas) return;
    if (!bootEtapas.hardware || !bootEtapas.programas) return;
    bootFechar();
  }

  function bootFechar() {
    if (bootFechado) return;
    bootFechado = true;
    bootStep('pronto');
    const el = document.getElementById('boot-splash');
    if (!el) return;
    setTimeout(function () {
      el.classList.add('hidden');
      setTimeout(function () { el.style.display = 'none'; }, 500);
    }, 260);
  }

  // Rede de seguranca: se alguma etapa falhar (sem rede, WMI travado), o
  // splash nao pode prender o app para sempre.
  setTimeout(function () { if (!bootFechado) bootFechar(); }, 20000);

  window.bootStep = bootStep;
  window.bootMarcar = bootMarcar;

  // -- Despedida ------------------------------------------------
  window.sairComSplash = function () {
    const bye = document.getElementById('bye-splash');
    if (!bye) {
      if (window.bridge && window.bridge.onExit) window.bridge.onExit();
      return;
    }

    function fechar(ms) {
      setTimeout(function () {
        if (window.bridge && window.bridge.onExit) window.bridge.onExit();
      }, ms);
    }

    bye.style.display = 'flex';

    if (!window.bridge || !window.bridge.getFarewellSummary) {
      fechar(700);
      return;
    }

    window.bridge.getFarewellSummary(function (r) {
      let temResumo = false;

      if (r && r.acoes && r.acoes.length) {
        temResumo = true;
        const box = document.getElementById('bye-actions');
        box.innerHTML = r.acoes.map(function (a) {
          return '<div style="display:flex;gap:10px;align-items:baseline;'
            + 'padding:5px 0;font-size:11px">'
            + '<span style="color:#4caf50;flex-shrink:0">&#10003;</span>'
            + '<span style="color:#8b93a1;min-width:82px;flex-shrink:0">' + a.modulo + '</span>'
            + '<span style="color:#e8ecf1;flex:1">' + a.texto + '</span>'
            + '</div>';
        }).join('');
        box.style.display = 'block';
        document.getElementById('bye-sub').textContent =
          r.acoes.length === 1 ? 'O que foi feito agora' : 'O que foi feito nesta sessao';
      }

      if (r && (r.ram || r.disco)) {
        const partes = [];
        if (r.ram) partes.push('memoria ' + r.ram);
        if (r.disco) partes.push('disco ' + r.disco);
        document.getElementById('bye-state').textContent = partes.join('  ·  ');
      }

      // Aviso que importa: sair com o Modo Gamer ativo deixa os tweaks
      // aplicados, e o usuario precisa saber disso.
      if (r && r.gamer) {
        const g = document.getElementById('bye-gamer');
        g.textContent = '● MODO GAMER CONTINUA ATIVO';
        g.style.display = 'block';
      }

      // Com resumo na tela vale um tempo maior para dar para ler.
      fechar(temResumo ? 2200 : 900);
    });
  };

  // -- Modal de confirmacao ------------------------------------
  // Substitui confirm(): o dialogo nativo mostra "Javascript Confirm" e o
  // caminho do arquivo, quebrando a identidade visual do app.
  function tecConfirm(opts, onYes, onNo) {
    const box = document.getElementById('tec-modal');
    if (!box) { if (onYes) onYes(); return; }

    const o = (typeof opts === 'string') ? { body: opts } : (opts || {});
    document.getElementById('tec-modal-title').textContent = o.title || 'Confirmar';
    document.getElementById('tec-modal-body').textContent = o.body || '';
    const yes = document.getElementById('tec-modal-yes');
    const no = document.getElementById('tec-modal-no');
    yes.textContent = o.yes || 'CONFIRMAR';
    no.textContent = o.no || 'CANCELAR';

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
    no.onclick = function () { fechar(); if (onNo) onNo(); };
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
    bootMarcar('metricas', 'lendo memoria e disco...');

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

    aplicarDiagnostico(s);
    if (s.ram) atualizarCardMemoria(s.ram.pct);
  }
  window.applySnapshot = applySnapshot;



  // -- Liberar memoria ------------------------------------------
  // O card so aparece sob pressao de RAM, e no lugar do de Otimizacao.

  function atualizarCardMemoria(pct) {
    const cardMem = document.getElementById('card-memoria');
    const cardOpt = document.getElementById('card-otimizacao');
    if (!cardMem || !cardOpt) return;

    const emCooldown = (Date.now() - memUltimaVez) < MEM_COOLDOWN;
    const mostrar = pct >= MEM_LIMITE;

    if (mostrar) {
      cardMem.style.display = 'flex';
      cardOpt.style.display = 'none';

      const btn = document.getElementById('mem-free-btn');
      if (btn && !btn.dataset.ocupado) {
        if (emCooldown) {
          const resta = Math.ceil((MEM_COOLDOWN - (Date.now() - memUltimaVez)) / 1000);
          btn.disabled = true;
          btn.style.opacity = '.45';
          btn.style.cursor = 'not-allowed';
          btn.textContent = 'aguarde ' + resta + 's';
          setBind('mem_card_txt',
            'Memória liberada há pouco. O que os programas reservam de novo '
            + 'leva algum tempo para valer outra liberação.');
        } else {
          btn.disabled = false;
          btn.style.opacity = '1';
          btn.style.cursor = 'pointer';
          btn.textContent = 'Liberar memória →';
          setBind('mem_card_txt',
            'A memória está em ' + Math.round(pct) + '%. Libere o que os '
            + 'programas reservaram e não usam.');
        }
      }
    } else {
      cardMem.style.display = 'none';
      cardOpt.style.display = 'flex';
    }
  }

  window.atualizarCardMemoria = atualizarCardMemoria;

  window.liberarMemoria = function () {
    if (!window.bridge || !window.bridge.liberarMemoria) return;
    const btn = document.getElementById('mem-free-btn');
    if (btn && btn.disabled) return;

    if (btn) {
      btn.dataset.ocupado = '1';
      btn.disabled = true;
      btn.style.opacity = '.55';
      btn.style.cursor = 'wait';
      btn.textContent = 'liberando...';
    }

    window.bridge.liberarMemoria(function (r) {
      memUltimaVez = Date.now();
      if (!btn) return;

      if (r && r.ok) {
        const ganho = r.antes_pct - r.depois_pct;
        btn.textContent = ganho >= 1 ? '\u2713 ' + r.humano + ' liberados'
                                     : '\u2713 já estava enxuta';
        btn.style.color = 'var(--state-on)';
        btn.style.borderColor = 'rgba(76,175,80,.45)';
        setBind('mem_card_txt', ganho >= 1
          ? 'Memória caiu de ' + r.antes_pct + '% para ' + r.depois_pct + '%.'
          : 'Não havia memória ociosa para devolver.');
      } else {
        btn.textContent = 'não foi possível';
        btn.style.color = '#e8a33d';
      }

      // Libera o botao para o ciclo normal (que respeitara o cooldown).
      setTimeout(function () {
        delete btn.dataset.ocupado;
        btn.style.color = '#e8a33d';
        btn.style.borderColor = '#e8a33d';
      }, 4000);
    });
  };

  // -- Diagnostico da Home --------------------------------------
  function corDeUso(p) {
    if (p > 85) return 'var(--state-danger)';
    if (p > 60) return '#e8a33d';
    return 'var(--cyan)';
  }

  function aplicarDiagnostico(s) {
    // Nucleos: uma barra por core. A media de CPU esconde o caso em que
    // um nucleo esta a 100% e os outros ociosos.
    const box = document.getElementById('core-bars');
    if (box && s.cores && s.cores.length) {
      if (box.children.length !== s.cores.length) {
        box.innerHTML = s.cores.map(function () {
          return '<div style="flex:1;background:rgba(255,255,255,.05);height:100%;'
            + 'border-radius:2px;display:flex;align-items:flex-end;overflow:hidden">'
            + '<div class="core-bar" style="width:100%;height:0%;transition:height .4s ease"></div></div>';
        }).join('');
      }
      const barras = box.querySelectorAll('.core-bar');
      let maxCore = 0;
      s.cores.forEach(function (v, i) {
        if (barras[i]) {
          barras[i].style.height = Math.max(2, v) + '%';
          barras[i].style.background = corDeUso(v);
        }
        if (v > maxCore) maxCore = v;
      });
      setBind('cores_info', s.cores.length + ' núcleos · pico ' + Math.round(maxCore) + '%');
    }

    // Frequencia
    if (s.freq && s.freq.max) {
      setBind('freq_now', String(s.freq.current));
      const fb = document.getElementById('freq-bar');
      if (fb) {
        fb.style.width = s.freq.pct + '%';
        fb.style.background = s.freq.pct < 60 ? '#e8a33d' : 'var(--cyan)';
      }
      setBind('freq_info', 'máximo ' + s.freq.max + ' MHz');
    }

    // Paginacao
    if (s.swap) {
      setBind('swap_pct', String(s.swap.pct));
      const sb = document.getElementById('swap-bar');
      if (sb) {
        sb.style.width = s.swap.pct + '%';
        sb.style.background = corDeUso(s.swap.pct);
      }
      const gb = function (b) { return (b / (1024 * 1024 * 1024)).toFixed(1); };
      setBind('swap_info', s.swap.total
        ? gb(s.swap.used) + ' GB de ' + gb(s.swap.total) + ' GB'
        : 'sem arquivo de paginação');
    }

    // Bateria: some em desktop
    const bbox = document.getElementById('battery-box');
    if (bbox && s.battery) {
      if (s.battery.has) {
        bbox.style.display = 'block';
        setBind('bat_pct', String(s.battery.pct));
        const bb = document.getElementById('bat-bar');
        if (bb) {
          bb.style.width = s.battery.pct + '%';
          bb.style.background = s.battery.pct < 20 && !s.battery.plugged
            ? 'var(--state-danger)' : 'var(--state-on)';
        }
        setBind('bat_info', s.battery.plugged ? 'ligado na tomada' : 'usando bateria');
      } else {
        bbox.style.display = 'none';
      }
    }

    // Alerta: junta os sinais que explicam lentidao real
    const avisos = [];
    if (s.swap && s.swap.pct > 40 && s.ram && s.ram.pct > 85) {
      avisos.push('A memória está no limite e o sistema já usa o disco como '
        + 'memória (paginação). É a causa mais comum de travamentos.');
    }
    if (s.battery && s.battery.has && !s.battery.plugged) {
      avisos.push('Na bateria o Windows reduz o desempenho — ligue na tomada '
        + 'antes de usar o Modo Gamer.');
    }
    if (s.freq && s.freq.max && s.freq.pct < 55) {
      avisos.push('A CPU está bem abaixo da frequência máxima, o que indica '
        + 'limitação por energia ou temperatura.');
    }
    const al = document.getElementById('diag-alerta');
    if (al) {
      if (avisos.length) {
        al.innerHTML = avisos.map(function (a) { return '⚠ ' + a; }).join('<br>');
        al.style.display = 'block';
      } else {
        al.style.display = 'none';
      }
    }
  }

  // ── Hardware lento (GPU / placa-mae) ──────────────────────────
  function applyHardware(hw) {
    bootMarcar('hardware', 'identificando hardware...');
    if (!hw) return;
    setBind('hw_gpu',  hw.gpu_name || '—');
    setBind('hw_mobo', `${hw.mobo_manufacturer || '—'} ${hw.mobo_model || ''}`.trim());
  }

  // ── Updater ───────────────────────────────────────────────────
  let updatePending = false;
  let updateInfo = null;

  // Modal com as notas da versao, aberto pelo botao da sidebar.
  window.openUpdateModal = function () {
    if (!updateInfo) return;
    const mb = updateInfo.size
      ? ' (' + (updateInfo.size / (1024 * 1024)).toFixed(0) + ' MB)' : '';
    let corpo = 'Uma versao nova do TecnoApp esta disponivel' + mb + '.';
    if (updateInfo.notes) {
      const n = String(updateInfo.notes).replace(/[#>*`]/g, '').trim();
      corpo += '\n\n' + n.slice(0, 600) + (n.length > 600 ? '\n...' : '');
    }
    corpo += '\n\nO download comeca agora e o app fecha para instalar.';
    tecConfirm({
      title: 'Atualizar para a v' + updateInfo.version + '?',
      body: corpo,
      yes: 'BAIXAR E INSTALAR'
    }, function () { window.startUpdate(); });
  };

  function showUpdateBanner(info) {
    if (!info) return;
    updatePending = true;
    updateInfo = info;

    // Botao fixo na sidebar: o banner do topo pode ser fechado, e ai o
    // usuario perderia a atualizacao de vista.
    const sb = document.getElementById('sidebar-update');
    const sbv = document.getElementById('sidebar-update-ver');
    if (sb) sb.style.display = 'block';
    if (sbv) {
      const mb = info.size ? ' · ' + (info.size / (1024 * 1024)).toFixed(0) + ' MB' : '';
      sbv.textContent = 'v' + info.version + mb;
    }
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
    bootMarcar('programas', 'analisando programas instalados...');
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
      termClear('debloat-terminal');
      termLine('debloat-terminal', '> criando ponto de restauracao...');
      window.bridge.removeBloatware(Array.from(bloatChecked));
    });
  };

  function onBloatProgress(cur, total, name) {
    setBind('debloat_status', 'Removendo ' + cur + '/' + total + ': ' + name);
    termLine('debloat-terminal', '> [' + cur + '/' + total + '] ' + name);
  }

  // Resultado de cada item: o remover reporta sucesso ou o motivo da falha.
  function onBloatItem(name, ok, err) {
    if (!ok) {
      termLine('debloat-terminal', '! falhou: ' + name + (err ? ' - ' + err : ''), '#e8a33d');
    }
  }

  function onBloatFinished(sum) {
    if (!sum) return;
    const parts = [sum.removed + ' removido(s)'];
    if (sum.freed_mb > 0) parts.push(sum.freed_mb + ' MB liberados');
    if (sum.failed > 0)   parts.push(sum.failed + ' falhou(ram)');
    const resumo = parts.join(' | ');

    termLine('debloat-terminal', '> concluido - ' + resumo,
             sum.failed > 0 ? '#e8a33d' : 'var(--state-on)');
    setBind('debloat_status', resumo);

    // Reabilita o botao: sem isso a tela ficava travada apos a remocao.
    const btn = document.getElementById('debloat-btn');
    if (btn) { btn.disabled = false; btn.style.opacity = '1'; btn.style.cursor = 'pointer'; }
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
  // Abre um terminal e marca a tela, para o CSS encolher a lista acima.
  function termShow(t) {
    if (!t) return false;
    const primeira = t.style.display !== 'block';
    t.style.display = 'block';
    const tela = t.closest('.screen');
    if (tela) tela.classList.add('has-terminal');
    if (primeira && t.scrollIntoView) {
      try { t.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); } catch (e) {}
    }
    return primeira;
  }
  window.termShow = termShow;

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
    termShow(t);
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
    termShow(t);
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
    if (t) { t.innerHTML = ''; termShow(t); }
    cleanSetRunning(true);
    navigate('limpeza');
    window.bridge.startCleanWith(Array.from(cleanChecked));
  };

  // -- Terminal generico inline --------------------------------
  function termLine(id, text, color) {
    const t = document.getElementById(id);
    if (!t) return;
    termShow(t);
    const d = document.createElement('div');
    d.className = 'terminal-line';
    if (color) d.style.color = color;
    d.textContent = text;
    t.appendChild(d);
    t.scrollTop = t.scrollHeight;
  }

  function termClear(id) {
    const t = document.getElementById(id);
    if (!t) return;
    t.innerHTML = '';
    termShow(t);
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
      // Selo de estado real: o usuario precisa ver o que ja esta ativo,
      // senao reaplica indefinidamente sem retorno.
      const sel = c.applied === true
        ? '<span style="font-size:9px;color:var(--state-on);font-weight:700;'
          + 'border:1px solid var(--state-on);border-radius:3px;padding:1px 5px">&#10003; ATIVO</span>'
        : '';
      return '<label style="display:flex;gap:12px;align-items:flex-start;padding:11px 14px;'
        + 'border-bottom:1px solid var(--border-subtle);cursor:pointer">'
        + '<input type="checkbox" data-opt="' + i + '" ' + on + ' style="margin-top:3px;flex-shrink:0">'
        + '<span style="flex:1;min-width:0">'
        + '<span style="display:flex;gap:8px;align-items:baseline;flex-wrap:wrap">'
        + '<span style="font-size:11px;color:var(--fg-primary);font-weight:600">' + c.label + '</span>'
        + rec + sel + '</span>'
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

  let optApplied = 0, optCheckable = 0;

  function updateOptCounts() {
    // O card mostra o que esta REALMENTE ativo no sistema; o botao fala
    // do que esta marcado para aplicar.
    setBind('opt_active', String(optApplied));
    setBind('opt_total', String(optCheckable));

    const btn = document.getElementById('opt-btn');
    if (!btn) return;

    // Quantas das marcadas ainda nao estao aplicadas
    const pendentes = optCats.filter(function (c) {
      return optChecked.has(c.id) && c.applied !== true;
    }).length;

    if (!optChecked.size) {
      btn.disabled = true; btn.style.opacity = '.5'; btn.style.cursor = 'not-allowed';
      btn.textContent = 'SELECIONE UMA OTIMIZACAO';
      setBind('opt_hint', 'Nenhuma otimizacao marcada.');
    } else if (pendentes === 0) {
      btn.disabled = true; btn.style.opacity = '.5'; btn.style.cursor = 'not-allowed';
      btn.textContent = 'TUDO JA APLICADO';
      setBind('opt_hint', 'As otimizacoes marcadas ja estao ativas no sistema.');
    } else {
      btn.disabled = false; btn.style.opacity = '1'; btn.style.cursor = 'pointer';
      btn.textContent = 'APLICAR ' + pendentes + (pendentes === 1 ? ' OTIMIZACAO' : ' OTIMIZACOES');
      setBind('opt_hint', '');
    }
  }

  function onOptimizeCategories(r) {
    if (!r || !r.categories) return;
    optCats = r.categories;
    optApplied = r.applied || 0;
    optCheckable = r.checkable || optCats.length;
    optChecked.clear();
    optCats.forEach(function (c) { if (c.checked) optChecked.add(c.id); });
    renderOpt();
  }
  window.onOptimizeCategories = onOptimizeCategories;

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
    // A mensagem ja aparece no terminal; repeti-la no rodape duplicava o texto.
    setBind('deep_status', '');
  }

  window.onDeepStep = onDeepStep;
  window.onDeepFinished = onDeepFinished;

  // Expostos em window: o Python empurra o progresso via runJavaScript
  // porque os sinais de progresso do QWebChannel nao chegavam ao JS.
  window.onUpdateAvailable = showUpdateBanner;
  window.onUpdateProgress = onUpdateProgress;
  window.onUpdateStatus = onUpdateStatus;
  window.onBloatProgress = onBloatProgress;
  window.onBloatItem = onBloatItem;
  window.onBloatFinished = onBloatFinished;
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

    bootMarcar('bridge', 'conectando ao sistema...');

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
    if (b.getGameCandidates) b.getGameCandidates(onGameCandidates);
    if (b.getDeepCleanCategories) b.getDeepCleanCategories(onDeepCategories);
    if (b.getCleanCategories)    b.getCleanCategories(onCleanCategories);

    if (b.getInitialSnapshot) b.getInitialSnapshot(applySnapshot);
    if (b.getHardware)        b.getHardware(applyHardware);

    // Versao no rodape + checagem automatica no start
    if (b.getVersion) b.getVersion(function (v) {
      setText('.version-tag', 'v ' + v + ' · Tecnosup');
      const bv = document.getElementById('boot-version');
      if (bv) bv.textContent = 'v' + v + ' · ';
    });
    if (b.checkForUpdates) b.checkForUpdates();
    // A checagem roda em thread e pode terminar antes do JS assinar; busca
    // o resultado depois para nao perder a notificacao.
    if (b.getUpdateInfo) {
      setTimeout(function () {
        b.getUpdateInfo(function (info) { if (info) showUpdateBanner(info); });
      }, 4000);
    }

    return true;
  }

  // ── Init ───────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    navigate('home');

    // Reaberto pelo RunOnce apos o reboot: vai direto ao Modo Gamer,
    // que foi o motivo de reiniciar.
    if (window.bridge && window.bridge.getPostRebootFlag) {
      window.bridge.getPostRebootFlag(function (flag) {
        if (flag === 'gamer') {
          navigate('gamer');
          setBind('gamer_status', 'PC reiniciado — tweaks de reboot agora ativos.');
        }
      });
    }
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
