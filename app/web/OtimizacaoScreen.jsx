// Otimização screen

function OtimizacaoScreen() {
  const [applied, setApplied] = React.useState({ power_ultimate: false, disk_optimize: false, hibernate_off: false, telemetry_disable: false });
  const [running, setRunning] = React.useState(null);

  const cats = [
    { id:'power_ultimate',   label:'Plano de Energia: Desempenho Máximo', desc:'Ativa o plano oculto "Ultimate Performance". Ideal para desktops.', impact:'Responsividade da CPU', reboot:false, warn:'' },
    { id:'disk_optimize',    label:'Otimizar Disco (TRIM ou Defrag)',      desc:'TRIM para SSD ou desfragmentação para HDD automático.',              impact:'Saúde do disco',       reboot:false, warn:'' },
    { id:'hibernate_off',    label:'Desativar Hibernação',                 desc:'Apaga hiberfil.sys — libera o tamanho da RAM em disco.',             impact:'4–16 GB em disco',    reboot:false, warn:'Em notebooks, hibernação permite retomar após bateria esgotar.' },
    { id:'telemetry_disable',label:'Desativar Telemetria do Windows',      desc:'Para DiagTrack e dmwappushservice. Reduz CPU/rede em background.',   impact:'CPU/rede background', reboot:false, warn:'Pode ser revertido em Restaurar padrões.' },
  ];

  function toggle(id) {
    if (window.bridge && window.bridge.runOtimizacao) window.bridge.runOtimizacao();
    setRunning(id);
    setTimeout(() => {
      setApplied(s => ({ ...s, [id]: !s[id] }));
      setRunning(null);
    }, 800);
  }

  const appliedCount = Object.values(applied).filter(Boolean).length;

  const containerStyle = { padding:'24px 32px', height:'100%', boxSizing:'border-box', display:'flex', flexDirection:'column', gap:14, overflowY:'auto' };

  return (
    <div style={containerStyle}>
      <div>
        <div style={{fontFamily:T.fontBody,fontSize:22,fontWeight:700,color:T.fgPrimary}}>OTIMIZAÇÃO</div>
        <div style={{fontFamily:T.fontBody,fontSize:12,color:T.fgMuted,marginTop:2}}>Tweaks persistentes — revertidos individualmente ou todos de uma vez</div>
      </div>

      <div style={{...TS.card,borderTop:`3px solid ${T.cyan}`,textAlign:'center',display:'flex',flexDirection:'column',gap:6,alignItems:'center'}}>
        <div style={TS.sectionLabel}>ESTADO ATUAL</div>
        <div style={{fontFamily:T.fontBody,fontSize:32,fontWeight:700,color:T.fgPrimary}}>
          {appliedCount} <span style={{fontSize:14,color:T.fgMuted,fontWeight:400}}>de {cats.length}</span>
        </div>
        <div style={{fontFamily:T.fontBody,fontSize:11,color:T.fgMuted}}>otimizações aplicadas</div>
      </div>

      <div style={{display:'flex',flexDirection:'column',gap:8}}>
        {cats.map(cat => {
          const on = applied[cat.id];
          const busy = running === cat.id;
          return (
            <div key={cat.id} style={{...TS.card,display:'flex',alignItems:'flex-start',gap:14,border:`1px solid ${on?'rgba(76,175,80,0.3)':'#1a2230'}`}}>
              <div style={{flex:1}}>
                <div style={{display:'flex',alignItems:'center',gap:8}}>
                  <span style={{color:'#fff',fontSize:12,fontWeight:600,fontFamily:T.fontBody}}>{cat.label}</span>
                  {on && <span style={{fontSize:9,fontWeight:700,borderRadius:10,padding:'1px 8px',border:'1px solid #4caf50',color:'#4caf50',background:'rgba(76,175,80,0.12)'}}>APLICADO</span>}
                </div>
                <div style={{color:'#888',fontSize:10,marginTop:3,fontFamily:T.fontBody,lineHeight:1.5}}>{cat.desc}</div>
                <div style={{color:T.cyan,fontFamily:T.fontMono,fontSize:9,marginTop:3}}>Impacto: {cat.impact}</div>
                {cat.warn && <div style={{color:'#ff8a4b',fontSize:9,marginTop:2}}>⚠ {cat.warn}</div>}
              </div>
              <button
                onClick={() => toggle(cat.id)}
                disabled={busy}
                style={{
                  background: on ? 'transparent' : T.cyan,
                  border: on ? `1px solid ${T.stateOn}` : 'none',
                  color: on ? T.stateOn : '#000',
                  borderRadius:6, padding:'6px 14px', cursor:'pointer',
                  fontWeight:700, fontSize:11, flexShrink:0, opacity:busy?0.5:1,
                  fontFamily:T.fontBody,
                }}
              >
                {busy ? '...' : on ? 'Reverter' : 'Aplicar'}
              </button>
            </div>
          );
        })}
      </div>

      <div style={{fontFamily:T.fontMono,fontSize:10,color:T.cyan}}>
        &gt; {appliedCount > 0 ? `${appliedCount} otimização${appliedCount>1?'s':''} aplicada${appliedCount>1?'s':''}.` : 'Nenhuma otimização aplicada ainda.'}
      </div>
    </div>
  );
}

Object.assign(window, { OtimizacaoScreen });
