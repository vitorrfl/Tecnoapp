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

  // ── Init ───────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    navigate('home');
    animateProgressBars();
  });
})();
