// Especificações (Hardware Specs) — wired to bridge

function _specsFmtSize(bytes) {
  if (!bytes || bytes <= 0) return '—';
  const u = ['B','KB','MB','GB','TB'];
  let i = 0, v = bytes;
  while (v >= 1024 && i < u.length - 1) { v /= 1024; i++; }
  return `${v.toFixed(v >= 100 ? 0 : 1)} ${u[i]}`;
}

function SpecsAnimatedBar({ pct, color }) {
  const [width, setWidth] = React.useState(0);
  React.useEffect(() => { setWidth(pct); }, [pct]);
  return (
    <div style={{background:'#04060a',border:'1px solid #1a2230',borderRadius:4,height:6,width:'100%',overflow:'hidden'}}>
      <div style={{width:`${Math.max(0,Math.min(100,width))}%`,height:'100%',background:color,borderRadius:3,transition:'width 0.75s cubic-bezier(0.4,0,0.2,1)'}} />
    </div>
  );
}

function SpecsScreen() {
  const tel = (window.useTelemetry ? window.useTelemetry() : window.__telemetry) || {};
  const hw  = (window.useHardware  ? window.useHardware()  : window.__hardware)  || null;

  const [disks, setDisks] = React.useState([]);
  const [procStats, setProcStats] = React.useState(null);

  React.useEffect(() => {
    if (!window.bridge) return;
    if (window.bridge.getDisks) {
      window.bridge.getDisks(d => { if (d) setDisks(d); });
    }
    function pollStats() {
      if (window.bridge.getProcessStats) {
        window.bridge.getProcessStats(s => { if (s) setProcStats(s); });
      }
    }
    pollStats();
    const t = setInterval(pollStats, 4000);
    return () => clearInterval(t);
  }, []);

  const fmtSize = _specsFmtSize;
  const AnimatedBar = SpecsAnimatedBar;

  const cpu  = tel.cpu  || { pct:0, name:'—', threads:0, freq:'—' };
  const ram  = tel.ram  || { pct:0, used:0, total:0 };
  const disk = tel.disk || { pct:0, used:0, total:0 };
  const os_  = tel.os   || { system:'—', version:'—' };

  const diskC = disks.find(d => (d.drive || '').toUpperCase().startsWith('C')) || null;

  const specs = [
    { label:'Sistema Operacional', value: os_.system || '—',           sub: os_.version ? `Build ${os_.version}` : '' },
    { label:'Processador',         value: cpu.name || '—',             sub: `${cpu.freq || '—'} · ${cpu.threads || 0} threads` },
    { label:'Memória RAM',         value: fmtSize(ram.total),          sub: `${(ram.pct||0).toFixed(0)}% em uso` },
    { label:'GPU',                 value: hw ? (hw.gpu_name || '—') : '...detectando',
                                   sub:   hw ? `${fmtSize(hw.gpu_vram || 0)} · Driver ${hw.gpu_driver || '—'}` : '' },
    { label:'Disco C:',            value: diskC ? `${fmtSize(diskC.total)} ${diskC.fs || ''}`.trim() : fmtSize(disk.total),
                                   sub:   diskC ? `${fmtSize(diskC.free)} livres` : '' },
    { label:'Placa-mãe',           value: hw ? `${(hw.mobo_manufacturer||'').trim()} ${(hw.mobo_model||'').trim()}`.trim() || '—' : '...detectando',
                                   sub:   hw && hw.bios_version ? `BIOS ${hw.bios_version}` : '' },
  ];

  const liveMetrics = [
    { label:'CPU', pct: Math.round(cpu.pct||0),  color:'#0eb3ff' },
    { label:'RAM', pct: Math.round(ram.pct||0),  color:'#0eb3ff' },
    { label:'Disco C:', pct: Math.round(disk.pct||0), color:'#0eb3ff' },
  ];

  const containerStyle = { padding:'24px 32px', height:'100%', boxSizing:'border-box', display:'flex', flexDirection:'column', gap:14, overflowY:'auto' };

  const ps = procStats || { total: tel.proc || 0, cpu_high: 0, ram_high: 0, uptime: tel.uptime || '—' };

  return (
    <div style={containerStyle}>
      <div>
        <div style={{fontFamily:T.fontBody,fontSize:22,fontWeight:700,color:T.fgPrimary}}>ESPECIFICAÇÕES</div>
        <div style={{fontFamily:T.fontBody,fontSize:12,color:T.fgMuted,marginTop:2}}>Hardware e sistema detectados automaticamente</div>
      </div>

      <div style={{display:'flex',gap:10}}>
        {liveMetrics.map(m => (
          <div key={m.label} style={{...TS.card,flex:1,display:'flex',flexDirection:'column',gap:8,alignItems:'center'}}>
            <div style={TS.sectionLabel}>{m.label}</div>
            <div style={{fontFamily:T.fontBody,fontSize:28,fontWeight:700,color:m.pct>80?T.stateDanger:m.pct>70?T.stateWarn:T.fgPrimary}}>
              {m.pct}<span style={{fontSize:12,color:T.fgMuted}}>%</span>
            </div>
            <AnimatedBar pct={m.pct} color={m.pct>80?T.stateDanger:m.pct>70?T.stateWarn:m.color} />
          </div>
        ))}
      </div>

      <div style={TS.card}>
        <div style={TS.sectionLabel}>HARDWARE</div>
        <div style={{display:'flex',flexDirection:'column',gap:0,marginTop:8}}>
          {specs.map((s,i) => (
            <div key={i} style={{display:'flex',alignItems:'baseline',gap:16,padding:'7px 0',borderBottom:'1px solid #1a2230'}}>
              <span style={{color:T.fgMuted,fontFamily:T.fontMono,fontSize:10,minWidth:160,flexShrink:0}}>{s.label}</span>
              <span style={{color:T.fgPrimary,fontFamily:T.fontMono,fontSize:11,fontWeight:600}}>{s.value}</span>
              <span style={{color:T.fgSubtle,fontFamily:T.fontMono,fontSize:10}}>{s.sub}</span>
            </div>
          ))}
        </div>
      </div>

      {disks.length > 1 && (
        <div style={TS.card}>
          <div style={TS.sectionLabel}>DISCOS</div>
          <div style={{display:'flex',flexDirection:'column',gap:6,marginTop:8}}>
            {disks.map((d,i) => (
              <div key={i} style={{display:'flex',gap:12,alignItems:'center'}}>
                <span style={{color:T.fgPrimary,fontFamily:T.fontMono,fontSize:11,fontWeight:700,minWidth:48}}>{d.drive}</span>
                <span style={{color:T.fgMuted,fontFamily:T.fontMono,fontSize:10,minWidth:48}}>{d.fs || '—'}</span>
                <div style={{flex:1}}>
                  <AnimatedBar pct={Math.round(d.pct||0)} color={d.pct>90?T.stateDanger:d.pct>75?T.stateWarn:T.cyan} />
                </div>
                <span style={{color:T.fgMuted,fontFamily:T.fontMono,fontSize:10,minWidth:160,textAlign:'right'}}>
                  {fmtSize(d.used)} / {fmtSize(d.total)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={TS.card}>
        <div style={TS.sectionLabel}>PROCESSOS ATIVOS</div>
        <div style={{display:'flex',gap:24,marginTop:8}}>
          {[
            ['Total', String(ps.total)],
            ['CPU > 5%', String(ps.cpu_high)],
            ['RAM > 500 MB', String(ps.ram_high)],
            ['Uptime', ps.uptime || '—'],
          ].map(([k,v])=>(
            <div key={k} style={{textAlign:'center'}}>
              <div style={{fontFamily:T.fontBody,fontSize:20,fontWeight:700,color:T.fgPrimary}}>{v}</div>
              <div style={{fontFamily:T.fontBody,fontSize:10,color:T.fgMuted,marginTop:2}}>{k}</div>
            </div>
          ))}
        </div>
      </div>

      <div style={{fontFamily:T.fontMono,fontSize:10,color:T.cyan}}>
        &gt; {hw ? 'Hardware detectado com sucesso.' : 'Detectando hardware…'}
      </div>
    </div>
  );
}

Object.assign(window, { SpecsScreen });
