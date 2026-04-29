// Limpeza (Clean) module screen

function AnimatedBar({ pct, color }) {
  const [width, setWidth] = React.useState(0);
  React.useEffect(() => {
    const t = setTimeout(() => setWidth(pct), 60);
    return () => clearTimeout(t);
  }, [pct]);
  return (
    <div style={{background:'#04060a',border:'1px solid #1a2230',borderRadius:4,height:8,margin:'4px 0',overflow:'hidden'}}>
      <div style={{width:`${width}%`,height:'100%',background:color,borderRadius:3,transition:'width 0.7s cubic-bezier(0.4,0,0.2,1)'}} />
    </div>
  );
}

function LimpezaScreen() {
  const [view, setView] = React.useState('main'); // 'main' | 'config' | 'running' | 'done'
  const [selections, setSelections] = React.useState({
    temp_user: true, temp_windows: true, prefetch: true, dns_cache: true,
    recycle_bin: true, thumbnail_cache: true, update_cache: false,
    event_logs: false, minidumps: false,
  });
  const [logLines, setLogLines] = React.useState([]);
  const [totalFreed, setTotalFreed] = React.useState('');

  const categories = [
    { id:'temp_user',       label:'Temporários do Usuário (%TEMP%)',       impact:'~100 MB – 2 GB',   safe:true,  desc:'Arquivos criados por programas durante o uso.' },
    { id:'temp_windows',    label:'Temporários do Windows',                 impact:'~50 MB – 500 MB',  safe:true,  desc:'Arquivos criados pelo sistema operacional.' },
    { id:'prefetch',        label:'Prefetch do Windows',                    impact:'~20 MB – 200 MB',  safe:true,  desc:'Cache de inicialização de programas.' },
    { id:'dns_cache',       label:'Cache DNS',                              impact:'Desprezível',       safe:true,  desc:'Tabela local de endereços de sites.' },
    { id:'recycle_bin',     label:'Lixeira',                               impact:'Varia (pode ser GBs)',safe:true, desc:'Arquivos deletados reservados na Lixeira.', warn:'Não é possível recuperar arquivos após esvaziar.' },
    { id:'thumbnail_cache', label:'Cache de Miniaturas',                    impact:'~50 MB – 300 MB',  safe:true,  desc:'Pré-visualizações de imagens do Explorer.' },
    { id:'update_cache',    label:'Cache do Windows Update',                impact:'~200 MB – 5 GB',   safe:false, desc:'Arquivos de instalações já concluídas.', warn:'O Windows pode baixar esses arquivos novamente.' },
    { id:'event_logs',      label:'Logs de Eventos do Windows',             impact:'~10 MB – 100 MB',  safe:false, desc:'Histórico de atividades e erros do sistema.', warn:'Apaga histórico — pode dificultar diagnóstico.' },
    { id:'minidumps',       label:'Relatórios de Travamento',               impact:'~10 MB – 100 MB',  safe:false, desc:'Arquivos gerados quando o Windows trava.', warn:'Remove informações úteis para diagnóstico.' },
  ];

  const selectedCount = Object.values(selections).filter(Boolean).length;

  function simulateRun() {
    setView('running');
    const lines = [];
    const steps = categories.filter(c => selections[c.id]);
    let i = 0;
    function step() {
      if (i < steps.length) {
        lines.push(`✓  ${steps[i].label}   +${Math.floor(Math.random()*400+10)} MB`);
        setLogLines([...lines]);
        i++;
        setTimeout(step, 350);
      } else {
        lines.push('');
        lines.push('Calculando resultado···');
        setLogLines([...lines]);
        setTimeout(() => {
          setTotalFreed('✓  2.4 GB liberados');
          setView('done');
        }, 900);
      }
    }
    setTimeout(step, 300);
  }

  const containerStyle = { padding:'24px 32px', height:'100%', boxSizing:'border-box', display:'flex', flexDirection:'column', gap:14, overflowY:'auto' };

  if (view === 'running' || view === 'done') {
    return (
      <div style={containerStyle}>
        <div style={{fontFamily:T.fontBody,fontSize:22,fontWeight:700,color:T.fgPrimary}}>{view==='done' ? 'LIMPEZA CONCLUÍDA' : 'LIMPEZA EM ANDAMENTO'}</div>
        <div style={{...TS.card,flex:1,overflow:'auto',minHeight:200}}>
          <div style={{fontFamily:T.fontMono,fontSize:12,color:T.cyan,lineHeight:1.8,whiteSpace:'pre-wrap'}}>
            {logLines.join('\n') || '> Iniciando limpeza...'}
          </div>
        </div>
        {view === 'done' && (
          <div style={{textAlign:'center',fontFamily:T.fontBody,fontSize:20,fontWeight:700,color:T.cyan,textShadow:'0 0 14px rgba(14,179,255,0.5)'}}>{totalFreed}</div>
        )}
        <button
          disabled={view==='running'}
          onClick={() => { setView('main'); setLogLines([]); setTotalFreed(''); }}
          style={{...TS.btnPrimary,opacity:view==='running'?0.35:1,width:200,alignSelf:'center'}}
        >
          VOLTAR
        </button>
      </div>
    );
  }

  if (view === 'config') {
    return (
      <div style={containerStyle}>
        <div style={{fontFamily:T.fontBody,fontSize:22,fontWeight:700,color:T.fgPrimary}}>CONFIGURAR LIMPEZA</div>
        <div style={{fontFamily:T.fontBody,fontSize:12,color:T.fgMuted}}>Selecione o que deseja limpar.</div>
        <div style={{flex:1,overflowY:'auto',display:'flex',flexDirection:'column',gap:6}}>
          <div style={{color:T.cyan,fontWeight:700,fontSize:11,marginBottom:2}}>── SEGURO (sempre recomendado)</div>
          {categories.filter(c=>c.safe).map(cat => (
            <div key={cat.id} style={{background:T.bgCard,border:'1px solid #1a2230',borderRadius:6,padding:'10px 14px'}}>
              <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
                <label style={{display:'flex',gap:8,alignItems:'center',cursor:'pointer'}}>
                  <input type="checkbox" checked={selections[cat.id]} onChange={e => setSelections(s=>({...s,[cat.id]:e.target.checked}))} />
                  <span style={{color:'#fff',fontSize:12,fontFamily:T.fontBody}}>{cat.label}</span>
                </label>
                <span style={{color:T.cyan,fontFamily:T.fontMono,fontSize:10}}>{cat.impact}</span>
              </div>
              <div style={{color:'#888',fontSize:10,paddingLeft:22,marginTop:2}}>{cat.desc}</div>
              {cat.warn && <div style={{color:'#ff8a4b',fontSize:10,paddingLeft:22,marginTop:2}}>⚠ {cat.warn}</div>}
            </div>
          ))}
          <div style={{color:T.stateWarn,fontWeight:700,fontSize:11,marginTop:8,marginBottom:2}}>── OPCIONAL (revise antes de ativar)</div>
          {categories.filter(c=>!c.safe).map(cat => (
            <div key={cat.id} style={{background:T.bgCard,border:'1px solid #1a2230',borderRadius:6,padding:'10px 14px'}}>
              <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
                <label style={{display:'flex',gap:8,alignItems:'center',cursor:'pointer'}}>
                  <input type="checkbox" checked={selections[cat.id]} onChange={e => setSelections(s=>({...s,[cat.id]:e.target.checked}))} />
                  <span style={{color:'#fff',fontSize:12,fontFamily:T.fontBody}}>{cat.label}</span>
                </label>
                <span style={{color:T.cyan,fontFamily:T.fontMono,fontSize:10}}>{cat.impact}</span>
              </div>
              <div style={{color:'#888',fontSize:10,paddingLeft:22,marginTop:2}}>{cat.desc}</div>
              {cat.warn && <div style={{color:'#ff8a4b',fontSize:10,paddingLeft:22,marginTop:2}}>⚠ {cat.warn}</div>}
            </div>
          ))}
        </div>
        <div style={{display:'flex',gap:10,justifyContent:'center'}}>
          <button onClick={()=>setView('main')} style={{background:'transparent',border:'1px solid #333',color:'#666',borderRadius:6,padding:'8px 20px',cursor:'pointer',fontFamily:T.fontBody,fontWeight:700}}>Voltar</button>
          <button onClick={()=>setView('main')} style={{...TS.btnPrimary,width:200,padding:'8px 0'}}>Salvar alterações</button>
        </div>
      </div>
    );
  }

  // Main view
  return (
    <div style={containerStyle}>
      <div>
        <div style={{fontFamily:T.fontBody,fontSize:22,fontWeight:700,color:T.fgPrimary}}>LIMPEZA</div>
        <div style={{fontFamily:T.fontBody,fontSize:12,color:T.fgMuted,marginTop:2}}>Limpeza segura com ferramentas nativas do Windows</div>
      </div>
      {/* Disk card */}
      <div style={TS.card}>
        <div style={TS.sectionLabel}>DISCOS</div>
        {[{drive:'C:\\',fs:'NTFS',pct:72,used:'670 GB',free:'260 GB',total:'931 GB'},{drive:'D:\\',fs:'NTFS',pct:88,used:'440 GB',free:'60 GB',total:'500 GB'}].map(d=>(
          <div key={d.drive} style={{marginTop:10}}>
            <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
              <span style={{color:'#fff',fontFamily:T.fontMono,fontSize:12,fontWeight:700}}>{d.drive}</span>
              <span style={{color:d.pct>90?T.stateDanger:d.pct>75?T.stateWarn:T.cyan,fontFamily:T.fontMono,fontSize:12,fontWeight:700}}>{d.pct}%</span>
            </div>
            <AnimatedBar pct={d.pct} color={d.pct>90?T.stateDanger:d.pct>75?T.stateWarn:T.cyan} />
            <div style={{color:'#888',fontFamily:T.fontMono,fontSize:10}}>{d.used} usados · {d.free} livres · {d.total} total</div>
          </div>
        ))}
      </div>
      {/* Hero card */}
      <div style={{...TS.card,borderTop:`3px solid ${T.cyan}`,display:'flex',flexDirection:'column',gap:10,alignItems:'center'}}>
        <div style={{...TS.sectionLabel,textAlign:'center'}}>LIMPEZA RÁPIDA</div>
        <div style={{fontFamily:T.fontBody,fontSize:32,fontWeight:700,color:T.fgPrimary}}>
          {selectedCount} <span style={{fontSize:14,fontWeight:400,color:T.fgMuted}}>de {categories.length}</span>
        </div>
        <div style={{fontFamily:T.fontBody,fontSize:11,color:T.fgMuted}}>categorias ativas</div>
        <button onClick={simulateRun} style={{...TS.btnPrimary,width:360}}>INICIAR LIMPEZA</button>
        <button onClick={()=>setView('config')} style={{background:'transparent',border:`1px solid ${T.cyan}`,color:T.cyan,borderRadius:6,padding:'6px 0',cursor:'pointer',fontWeight:700,fontSize:11,width:240,fontFamily:T.fontBody}}>
          Configurar o que é limpo →
        </button>
      </div>
      <div style={{fontFamily:T.fontMono,fontSize:10,color:T.cyan}}>&gt; Nenhuma limpeza realizada ainda.</div>
    </div>
  );
}

Object.assign(window, { LimpezaScreen });
