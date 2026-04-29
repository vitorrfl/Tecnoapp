// Sidebar navigation — matches preview/components-sidebar.html exactly

function Sidebar({ active, onNavigate }) {
  const gamerRef = React.useRef(null);

  // Gamer button gradient tracking
  React.useEffect(() => {
    const btn = gamerRef.current;
    if (!btn) return;
    let idleT = 0, mouseX = 0.5, targetX = 0.5;
    let isHovered = false, lastMoveTime = 0;
    let raf;

    function lerp(a, b, t) { return a + (b - a) * t; }
    function applyGradient(x, shift) {
      const angle = 80 + x * 40 + shift * 12;
      const s1 = Math.max(0, Math.min(60, x * 60 - shift * 8));
      const s2 = Math.min(100, 40 + x * 60 + shift * 8);
      btn.style.background = `linear-gradient(${angle}deg,#0eb3ff ${s1}%,#7000ff ${s2}%)`;
    }
    function tick(ts) {
      if (isHovered) {
        mouseX = lerp(mouseX, targetX, 0.08);
        const idle = (ts - lastMoveTime > 600) ? Math.sin(ts * 0.0008) * 0.25 : 0;
        applyGradient(mouseX, idle);
      } else {
        idleT += 0.0004;
        mouseX = lerp(mouseX, 0.5, 0.02);
        applyGradient(mouseX, Math.sin(idleT) * 0.15);
      }
      raf = requestAnimationFrame(tick);
    }
    const onEnter = () => { isHovered = true; };
    const onLeave = () => { isHovered = false; targetX = 0.5; };
    const onMove  = e => {
      targetX = (e.clientX - btn.getBoundingClientRect().left) / btn.offsetWidth;
      lastMoveTime = performance.now();
    };
    btn.addEventListener('mouseenter', onEnter);
    btn.addEventListener('mouseleave', onLeave);
    btn.addEventListener('mousemove',  onMove);
    raf = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf);
      btn.removeEventListener('mouseenter', onEnter);
      btn.removeEventListener('mouseleave', onLeave);
      btn.removeEventListener('mousemove',  onMove);
    };
  }, []);

  // Inline SVG icons — white/grey by default, class handles hover colour via CSS
  const icons = {
    home: <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#555" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>,
    limpeza: <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#555" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>,
    otimizacao: <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#555" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>,
    reparos: <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#555" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>,
    specs: <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#555" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>,
    gamer: <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="6" y1="12" x2="18" y2="12"/><line x1="12" y1="6" x2="12" y2="18"/><rect x="2" y="6" width="20" height="12" rx="2"/></svg>,
    shield: <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>,
    logout: <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>,
  };

  const menuItems = [
    { id: 'home',       label: 'HOME',          icon: icons.home },
    { id: 'limpeza',    label: 'LIMPEZA',        icon: icons.limpeza },
    { id: 'otimizacao', label: 'OTIMIZAÇÃO',     icon: icons.otimizacao },
    { id: 'reparos',    label: 'REPAROS',        icon: icons.reparos },
    { id: 'specs',      label: 'ESPECIFICAÇÕES', icon: icons.specs },
  ];

  return (
    <div style={{
      width: 220, minWidth: 220, height: '100%',
      background: 'rgba(3,4,7,0.97)',
      borderRight: '1px solid rgba(14,179,255,0.1)',
      display: 'flex', flexDirection: 'column',
      padding: '24px 15px 18px', gap: 10, boxSizing: 'border-box',
    }}>

      {/* Logo */}
      <div className="sb-logo" onClick={() => onNavigate('home')}>
        <img src="../../assets/logo.png" alt="Tecnosup" />
      </div>

      {/* Nav items */}
      {menuItems.map(item => (
        <button
          key={item.id}
          className={`sb-menu-btn${active === item.id ? ' sb-active' : ''}`}
          onClick={() => onNavigate(item.id)}
        >
          {item.icon}
          {item.label}
        </button>
      ))}

      {/* Gamer */}
      <button ref={gamerRef} className="sb-gamer-btn" onClick={() => onNavigate('gamer')}>
        {icons.gamer}
        MODO GAMER
      </button>

      <div style={{ flex: 1 }} />

      {/* Restore */}
      <button className="sb-restore-btn">
        {icons.shield}
        Criar Ponto de Restauração
      </button>

      <div style={{ height: 4 }} />

      {/* Exit */}
      <button className="sb-exit-btn">
        {icons.logout}
        SAIR
      </button>

      <div style={{ textAlign: 'center', color: '#2a3040', fontFamily: T.fontMono, fontSize: 9, marginTop: 4 }}>
        v 1.0 · Tecnosup
      </div>
    </div>
  );
}

Object.assign(window, { Sidebar });
