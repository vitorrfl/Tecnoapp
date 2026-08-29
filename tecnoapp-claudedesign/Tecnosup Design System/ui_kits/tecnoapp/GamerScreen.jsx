// Modo Gamer screen

function GamerScreen() {
  const [active, setActive] = React.useState(false);
  const [running, setRunning] = React.useState(false);
  const [logLines, setLogLines] = React.useState([]);
  const [optIns, setOptIns] = React.useState({ empty_standby: false });

  const tweaks = [
    { cat:'CPU',   id:'cpu.ultimate_performance', label:'Plano Ultimate Performance', desc:'Duplica e ativa o power plan oculto do Windows.' },
    { cat:'CPU',   id:'cpu.core_parking_off',      label:'Core Parking OFF',          desc:'Desabilita estacionamento de núcleos da CPU.' },
    { cat:'CPU',   id:'cpu.mmcss_games',           label:'MMCSS Games Priority',      desc:'Prioriza o perfil "Games" no agendador multimídia.' },
    { cat:'GPU',   id:'gpu.hags',                  label:'HAGS (GPU Scheduling)',     desc:'Liga Hardware Accelerated GPU Scheduling.' },
    { cat:'GPU',   id:'gpu.fso_off',               label:'Fullscreen Opts. OFF',      desc:'Desliga otimizações de tela cheia.' },
    { cat:'GPU',   id:'gpu.gamedvr_off',           label:'Game DVR OFF',              desc:'Desliga gravação em background.' },
    { cat:'GPU',   id:'gpu.game_mode_on',          label:'Game Mode ON',              desc:'Liga o Game Mode do Windows.' },
    { cat:'GPU',   id:'gpu.tdr_delay',             label:'TDR Delay x10',             desc:'Estende o timeout de resposta da GPU.' },
    { cat:'REDE',  id:'network.nagle_off',         label:'Nagle OFF',                 desc:'Desliga o algoritmo Nagle (menor latência).' },
    { cat:'REDE',  id:'network.throttling_off',    label:'Throttling OFF',            desc:'Desativa limitação de rede em multimídia.' },
    { cat:'REDE',  id:'network.tcp_autotuning',    label:'TCP Autotuning Normal',     desc:'Define AutoTuningLevelLocal=Normal.' },
    { cat:'REDE',  id:'network.flush_dns',         label:'Flush DNS',                 desc:'Limpa cache DNS ao ativar.' },
    { cat:'SISTEMA', id:'system.kill_bloat',       label:'Kill Bloat',                desc:'Encerra processos em background (sem Discord/Steam).' },
    { cat:'SISTEMA', id:'system.visual_effects',   label:'Visual Effects → Perf',    desc:'Ajusta efeitos visuais para melhor desempenho.' },
    { cat:'SISTEMA', id:'system.toasts_off',       label:'Notificações OFF',          desc:'Desativa toasts para não tirar do fullscreen.' },
    { cat:'SISTEMA', id:'system.services_demand',  label:'Serviços → Demanda',       desc:'SysMain, DiagTrack, WSearch em modo demand.' },
    { cat:'SISTEMA', id:'system.empty_standby',    label:'Purgar Standby Memory',    desc:'Purga memória em standby via ntdll.', optIn:true, warn:'⚠ Opt-in — risco de BSOD em alguns sistemas.' },
  ];

  const categories = ['CPU', 'GPU', 'REDE', 'SISTEMA'];

  function simulate(action) {
    setRunning(true);
    const lines = [];
    tweaks.filter(t => !t.optIn || optIns.empty_standby).forEach((t, i) => {
      setTimeout(() => {
        lines.push(`${action === 'activate' ? '▶' : '◀'}  ${t.label} — OK`);
        setLogLines([...lines]);
        if (i === tweaks.length - 1 || (i === tweaks.filter(t=>!t.optIn||optIns.empty_standby).length - 1)) {
          setTimeout(() => {
            setActive(action === 'activate');
            setRunning(false);
          }, 400);
        }
      }, i * 120);
    });
  }

  const containerStyle = { padding:'24px 32px', height:'100%', boxSizing:'border-box', display:'flex', flexDirection:'column', gap:14, overflowY:'auto' };

  return (
    <div style={containerStyle}>
      <div>
        <div style={{fontFamily:T.fontBody,fontSize:22,fontWeight:700,color:T.fgPrimary}}>MODO GAMER</div>
        <div style={{fontFamily:T.fontBody,fontSize:12,color:T.fgMuted,marginTop:2}}>17 tweaks reversíveis de CPU, GPU, sistema e rede</div>
      </div>

      {/* Hero */}
      <div style={{...TS.card,borderTop:`3px solid ${active ? T.stateOn : T.purple}`,display:'flex',flexDirection:'column',gap:10,alignItems:'center'}}>
        <div style={{fontFamily:T.fontBody,fontSize:32,fontWeight:700,color:active?T.stateOn:T.purple,textShadow:active?`0 0 14px rgba(76,175,80,0.5)`:`0 0 14px rgba(112,0,255,0.5)`}}>
          {active ? '● ATIVO' : '● INATIVO'}
        </div>
        <div style={{fontFamily:T.fontBody,fontSize:11,color:T.fgMuted,textAlign:'center'}}>
          {active ? 'Tweaks aplicados — clique em Desativar para reverter' : 'Pronto para ativar — todos os tweaks são reversíveis'}
        </div>
        <div style={{display:'flex',gap:10}}>
          {!active ? (
            <button
              disabled={running}
              onClick={() => simulate('activate')}
              style={{background:'linear-gradient(90deg,#0eb3ff,#7000ff)',color:'#fff',fontWeight:700,border:'none',borderRadius:8,padding:'10px 32px',fontSize:14,cursor:'pointer',opacity:running?0.5:1}}
            >
              {running ? 'ATIVANDO...' : 'ATIVAR MODO GAMER'}
            </button>
          ) : (
            <button
              disabled={running}
              onClick={() => simulate('deactivate')}
              style={{background:'transparent',border:`1px solid ${T.stateOn}`,color:T.stateOn,fontWeight:700,borderRadius:8,padding:'10px 32px',fontSize:14,cursor:'pointer',opacity:running?0.5:1,fontFamily:T.fontBody}}
            >
              {running ? 'REVERTENDO...' : 'DESATIVAR'}
            </button>
          )}
        </div>
        {logLines.length > 0 && (
          <div style={{background:'#020305',borderRadius:6,padding:'10px 14px',width:'100%',maxHeight:120,overflowY:'auto'}}>
            <div style={{fontFamily:T.fontMono,fontSize:10,color:T.cyan,lineHeight:1.8}}>
              {logLines.map((l,i) => <div key={i}>{l}</div>)}
            </div>
          </div>
        )}
      </div>

      {/* Tweak list */}
      <div style={{display:'flex',flexDirection:'column',gap:8}}>
        {categories.map(cat => (
          <div key={cat}>
            <div style={{...TS.sectionLabel,marginBottom:6,color:cat==='SISTEMA'?T.stateWarn:T.cyan}}>{cat}</div>
            <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:6}}>
              {tweaks.filter(t=>t.cat===cat).map(t => (
                <div key={t.id} style={{background:T.bgCard,border:`1px solid ${t.optIn?'rgba(255,189,46,0.3)':'#1a2230'}`,borderRadius:6,padding:'8px 12px',display:'flex',alignItems:'flex-start',gap:8}}>
                  <div style={{width:8,height:8,borderRadius:4,background:active&&(!t.optIn||optIns.empty_standby)?T.stateOn:'#333',marginTop:4,flexShrink:0}} />
                  <div>
                    <div style={{color:'#fff',fontSize:11,fontWeight:600,fontFamily:T.fontBody}}>{t.label}</div>
                    <div style={{color:'#888',fontSize:10,marginTop:1,fontFamily:T.fontBody}}>{t.desc}</div>
                    {t.warn && <div style={{color:'#ff8a4b',fontSize:9,marginTop:2}}>{t.warn}</div>}
                    {t.optIn && (
                      <label style={{display:'flex',alignItems:'center',gap:4,marginTop:4,cursor:'pointer'}}>
                        <input type="checkbox" checked={optIns.empty_standby} onChange={e=>setOptIns(s=>({...s,empty_standby:e.target.checked}))} style={{accentColor:T.stateWarn}} />
                        <span style={{color:T.stateWarn,fontSize:9}}>Habilitar (opt-in)</span>
                      </label>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div style={{fontFamily:T.fontMono,fontSize:10,color:T.fgMuted}}>
        &gt; {active ? `Modo Gamer ativo — ${tweaks.filter(t=>!t.optIn||optIns.empty_standby).length} tweaks aplicados` : 'Modo Gamer inativo.'}
      </div>
    </div>
  );
}

Object.assign(window, { GamerScreen });
