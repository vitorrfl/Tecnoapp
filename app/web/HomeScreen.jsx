// Home / Dashboard screen — wired to Python bridge via window.useTelemetry()

function HomeScreen() {
  const tel = (window.useTelemetry ? window.useTelemetry() : window.__telemetry) || {};
  const cpu  = tel.cpu  || { pct: 0, name: '—', threads: 0, freq: '—' };
  const ram  = tel.ram  || { pct: 0, used: 0, total: 0 };
  const disk = tel.disk || { pct: 0, used: 0, total: 0 };
  const proc = tel.proc != null ? tel.proc : 0;
  const os_  = tel.os   || { system: '—', user: '—', version: '—' };

  function fmtSize(bytes) {
    if (!bytes || bytes <= 0) return '—';
    const u = ['B','KB','MB','GB','TB'];
    let i = 0, v = bytes;
    while (v >= 1024 && i < u.length - 1) { v /= 1024; i++; }
    return `${v.toFixed(v >= 100 ? 0 : 1)} ${u[i]}`;
  }

  function AnimatedBar({ pct, color }) {
    const [width, setWidth] = React.useState(0);
    React.useEffect(() => {
      const t = setTimeout(() => setWidth(pct), 80);
      return () => clearTimeout(t);
    }, [pct]);
    return (
      <div style={{background:'#04060a',border:'1px solid #1a2230',borderRadius:4,height:8,overflow:'hidden'}}>
        <div style={{width:`${width}%`,height:'100%',background:color,borderRadius:3,transition:'width 0.7s cubic-bezier(0.4,0,0.2,1)'}} />
      </div>
    );
  }

  const containerStyle = {
    padding: '22px 32px',
    display: 'flex',
    flexDirection: 'column',
    gap: 14,
    height: '100%',
    boxSizing: 'border-box',
    overflowY: 'auto',
  };

  function MetricCard({ label, value, unit, pct, color }) {
    return (
      <div style={{...TS.card, flex:1, display:'flex', flexDirection:'column', gap:10}}>
        <div style={TS.sectionLabel}>{label}</div>
        <div style={{textAlign:'center'}}>
          <span style={{fontFamily:T.fontBody,fontSize:28,fontWeight:700,color:T.fgPrimary}}>{value}</span>
          <span style={{fontFamily:T.fontBody,fontSize:12,color:T.fgMuted}}> {unit}</span>
        </div>
        {pct != null && <AnimatedBar pct={pct} color={color||T.cyan} />}
      </div>
    );
  }

  function navigate(target) {
    window.dispatchEvent(new CustomEvent('navigate', { detail: target }));
  }

  function ModuleCard({ label, desc, color, btnLabel, btnClass, btnRef, onNav }) {
    return (
      <div style={{...TS.card, flex:1, display:'flex', flexDirection:'column', gap:10, borderTop:`3px solid ${color}`}}>
        <div style={{...TS.sectionLabel, color}}>{label}</div>
        <div style={TS.bodyText}>{desc}</div>
        <button
          ref={btnRef}
          className={btnClass || 'mod-btn'}
          onClick={onNav}
        >
          {btnLabel} →
        </button>
      </div>
    );
  }

  const gamerBtnRef = React.useRef(null);

  React.useEffect(() => {
    const btn = gamerBtnRef.current;
    if (!btn) return;
    let idleT = 0, mouseX = 0.5, targetX = 0.5;
    let isHovered = false, lastMoveTime = 0, raf;
    const lerp = (a,b,t) => a+(b-a)*t;
    function applyGradient(x, shift) {
      const angle = 80 + x*40 + shift*12;
      const s1 = Math.max(0,Math.min(60,x*60-shift*8));
      const s2 = Math.min(100,40+x*60+shift*8);
      btn.style.background = `linear-gradient(${angle}deg,#0eb3ff ${s1}%,#7000ff ${s2}%)`;
    }
    function tick(ts) {
      if (isHovered) {
        mouseX = lerp(mouseX, targetX, 0.08);
        const idle = (ts - lastMoveTime > 600) ? Math.sin(ts*0.0008)*0.25 : 0;
        applyGradient(mouseX, idle);
      } else {
        idleT += 0.0004;
        mouseX = lerp(mouseX, 0.5, 0.02);
        applyGradient(mouseX, Math.sin(idleT)*0.15);
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

  const ramValue  = ram.used  > 0 ? (ram.used  / (1024**3)).toFixed(1) : '—';
  const userName  = os_.user && os_.user !== '—' ? os_.user : 'Usuário';
  const osLine    = `${os_.system || '—'}${os_.version ? ' · Build ' + os_.version : ''}`;

  return (
    <div style={containerStyle}>
      <div>
        <div style={{fontFamily:T.fontBody,fontSize:22,fontWeight:700,color:T.fgPrimary}}>Olá, {userName}</div>
        <div style={{fontFamily:T.fontBody,fontSize:12,color:T.fgMuted,marginTop:2}}>{osLine}</div>
      </div>

      <div style={{display:'flex',gap:12}}>
        <MetricCard label="CPU"       value={Math.round(cpu.pct)}  unit="%"  pct={cpu.pct}  color={cpu.pct  > 80 ? T.stateDanger : T.cyan} />
        <MetricCard label="RAM"       value={ramValue}             unit="GB" pct={ram.pct}  color={ram.pct  > 80 ? T.stateDanger : T.cyan} />
        <MetricCard label="DISCO C:"  value={Math.round(disk.pct)} unit="%"  pct={disk.pct} color={disk.pct > 90 ? T.stateDanger : disk.pct > 75 ? T.stateWarn : T.cyan} />
        <MetricCard label="PROCESSOS" value={proc} unit="" />
      </div>

      <div style={{display:'flex',gap:12}}>
        <ModuleCard label="LIMPEZA"     desc="Remova arquivos temporários e libere espaço em disco." color={T.cyan}   btnLabel="Limpar agora" onNav={() => navigate('limpeza')} />
        <ModuleCard label="OTIMIZAÇÃO"  desc="Ative tweaks de desempenho e plano de energia."        color={T.cyan}   btnLabel="Otimizar"     onNav={() => navigate('otimizacao')} />
        <ModuleCard label="REPAROS"     desc="Repare arquivos do sistema, rede e Windows Update."    color={T.cyan}   btnLabel="Reparar"      onNav={() => navigate('reparos')} />
        <ModuleCard label="MODO GAMER"  desc="17 tweaks reversíveis para mais FPS e menos latência." color={T.purple} btnLabel="Ativar" btnClass="mod-btn-gamer" btnRef={gamerBtnRef} onNav={() => navigate('gamer')} />
      </div>

      <div style={{...TS.card}}>
        <div style={TS.sectionLabel}>SISTEMA</div>
        <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'4px 24px',marginTop:6}}>
          {[
            ['Processador', cpu.name || '—'],
            ['Memória RAM', fmtSize(ram.total)],
            ['Sistema',     os_.system || '—'],
            ['Uptime',      tel.uptime || '—'],
          ].map(([k,v]) => (
            <div key={k} style={{display:'flex',gap:8,padding:'4px 0',borderBottom:'1px solid #1a2230'}}>
              <span style={{color:T.fgMuted,fontFamily:T.fontMono,fontSize:10,minWidth:100}}>{k}</span>
              <span style={{color:T.fgBody,fontFamily:T.fontMono,fontSize:10}}>{v}</span>
            </div>
          ))}
        </div>
      </div>

      <div style={{fontFamily:T.fontMono,fontSize:10,color:T.cyan,paddingTop:4}}>
        &gt; Sistema verificado — nenhuma ação pendente.
      </div>
    </div>
  );
}

Object.assign(window, { HomeScreen });
