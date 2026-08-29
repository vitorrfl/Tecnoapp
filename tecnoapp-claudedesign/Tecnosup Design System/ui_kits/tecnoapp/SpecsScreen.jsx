// Especificações (Hardware Specs) screen

function SpecsScreen() {
  function AnimatedBar({ pct, color }) {
    const [width, setWidth] = React.useState(0);
    React.useEffect(() => {
      const t = setTimeout(() => setWidth(pct), 60);
      return () => clearTimeout(t);
    }, [pct]);
    return (
      <div style={{background:'#04060a',border:'1px solid #1a2230',borderRadius:4,height:6,width:'100%',overflow:'hidden'}}>
        <div style={{width:`${width}%`,height:'100%',background:color,borderRadius:3,transition:'width 0.75s cubic-bezier(0.4,0,0.2,1)'}} />
      </div>
    );
  }
  const specs = {
    os:      { label:'Sistema Operacional', value:'Windows 11 Pro',    sub:'Build 26100.3915' },
    cpu:     { label:'Processador',         value:'Intel Core i7-12700K', sub:'3.60 GHz · 12 cores · 20 threads' },
    ram:     { label:'Memória RAM',         value:'32 GB',              sub:'DDR5-5200 · 2 × 16 GB' },
    gpu:     { label:'GPU',                 value:'NVIDIA RTX 4070',    sub:'12 GB GDDR6X · Driver 572.83' },
    diskC:   { label:'Disco C:',            value:'931 GB SSD',         sub:'NVMe PCIe 4.0 · Saúde: OK' },
    mobo:    { label:'Placa-mãe',           value:'ASUS ROG STRIX Z690-F', sub:'BIOS 3004' },
    net:     { label:'Rede',                value:'Intel I225-V 2.5Gbps', sub:'192.168.1.105 · Conectado' },
  };

  const liveMetrics = [
    { label:'CPU', pct:38, color:'#0eb3ff' },
    { label:'RAM', pct:61, color:'#0eb3ff' },
    { label:'GPU', pct:24, color:'#7000ff' },
    { label:'Disco C:', pct:72, color:'#0eb3ff' },
  ];

  const containerStyle = { padding:'24px 32px', height:'100%', boxSizing:'border-box', display:'flex', flexDirection:'column', gap:14, overflowY:'auto' };

  return (
    <div style={containerStyle}>
      <div>
        <div style={{fontFamily:T.fontBody,fontSize:22,fontWeight:700,color:T.fgPrimary}}>ESPECIFICAÇÕES</div>
        <div style={{fontFamily:T.fontBody,fontSize:12,color:T.fgMuted,marginTop:2}}>Hardware e sistema detectados automaticamente</div>
      </div>

      {/* Live metrics */}
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

      {/* Spec table */}
      <div style={TS.card}>
        <div style={TS.sectionLabel}>HARDWARE</div>
        <div style={{display:'flex',flexDirection:'column',gap:0,marginTop:8}}>
          {Object.values(specs).map((s,i) => (
            <div key={i} style={{display:'flex',alignItems:'baseline',gap:16,padding:'7px 0',borderBottom:'1px solid #1a2230'}}>
              <span style={{color:T.fgMuted,fontFamily:T.fontMono,fontSize:10,minWidth:160,flexShrink:0}}>{s.label}</span>
              <span style={{color:T.fgPrimary,fontFamily:T.fontMono,fontSize:11,fontWeight:600}}>{s.value}</span>
              <span style={{color:T.fgSubtle,fontFamily:T.fontMono,fontSize:10}}>{s.sub}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Process info */}
      <div style={TS.card}>
        <div style={TS.sectionLabel}>PROCESSOS ATIVOS</div>
        <div style={{display:'flex',gap:24,marginTop:8}}>
          {[['Total','187'],['CPU > 5%','4'],['RAM > 500 MB','8'],['Uptime','2h 41min']].map(([k,v])=>(
            <div key={k} style={{textAlign:'center'}}>
              <div style={{fontFamily:T.fontBody,fontSize:20,fontWeight:700,color:T.fgPrimary}}>{v}</div>
              <div style={{fontFamily:T.fontBody,fontSize:10,color:T.fgMuted,marginTop:2}}>{k}</div>
            </div>
          ))}
        </div>
      </div>

      <div style={{fontFamily:T.fontMono,fontSize:10,color:T.cyan}}>&gt; Hardware detectado com sucesso.</div>
    </div>
  );
}

Object.assign(window, { SpecsScreen });
