// Home / Dashboard screen

function HomeScreen() {
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
  const [cpuPct] = React.useState(38);
  const [ramPct] = React.useState(61);
  const [diskPct] = React.useState(72);

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

  // Gamer card button — same gradient tracking as sidebar
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

  const osInfo = { os: 'Windows 11 Pro', build: '26100.3915', cpu: 'Intel Core i7-12700K', ram: '32 GB DDR5' };

  return (
    <div style={containerStyle}>
      <div>
        <div style={{fontFamily:T.fontBody,fontSize:22,fontWeight:700,color:T.fgPrimary}}>Olá, Usuário</div>
        <div style={{fontFamily:T.fontBody,fontSize:12,color:T.fgMuted,marginTop:2}}>{osInfo.os} · Build {osInfo.build}</div>
      </div>

      {/* Metrics row */}
      <div style={{display:'flex',gap:12}}>
        <MetricCard label="CPU" value={cpuPct} unit="%" pct={cpuPct} color={T.cyan} />
        <MetricCard label="RAM" value="19.6" unit="GB" pct={ramPct} color={cpuPct > 80 ? T.stateDanger : T.cyan} />
        <MetricCard label="DISCO C:" value={diskPct} unit="%" pct={diskPct} color={diskPct > 90 ? T.stateDanger : diskPct > 75 ? T.stateWarn : T.cyan} />
        <MetricCard label="PROCESSOS" value="187" unit="" />
      </div>

      {/* Modules row */}
      <div style={{display:'flex',gap:12}}>
        <ModuleCard label="LIMPEZA"     desc="Remova arquivos temporários e libere espaço em disco." color={T.cyan}   btnLabel="Limpar agora" />
        <ModuleCard label="OTIMIZAÇÃO"  desc="Ative tweaks de desempenho e plano de energia."        color={T.cyan}   btnLabel="Otimizar" />
        <ModuleCard label="REPAROS"     desc="Repare arquivos do sistema, rede e Windows Update."    color={T.cyan}   btnLabel="Reparar" />
        <ModuleCard label="MODO GAMER"  desc="17 tweaks reversíveis para mais FPS e menos latência." color={T.purple} btnLabel="Ativar" btnClass="mod-btn-gamer" btnRef={gamerBtnRef} />
      </div>

      {/* System info */}
      <div style={{...TS.card}}>
        <div style={TS.sectionLabel}>SISTEMA</div>
        <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'4px 24px',marginTop:6}}>
          {[['Processador', osInfo.cpu],['Memória RAM', osInfo.ram],['Sistema', osInfo.os],['Uptime','2h 41min']].map(([k,v]) => (
            <div key={k} style={{display:'flex',gap:8,padding:'4px 0',borderBottom:'1px solid #1a2230'}}>
              <span style={{color:T.fgMuted,fontFamily:T.fontMono,fontSize:10,minWidth:100}}>{k}</span>
              <span style={{color:T.fgBody,fontFamily:T.fontMono,fontSize:10}}>{v}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Status bar */}
      <div style={{fontFamily:T.fontMono,fontSize:10,color:T.cyan,paddingTop:4}}>
        &gt; Sistema verificado — nenhuma ação pendente.
      </div>
    </div>
  );
}

Object.assign(window, { HomeScreen });
