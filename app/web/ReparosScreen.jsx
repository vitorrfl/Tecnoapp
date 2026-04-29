// Reparos screen

function ReparosScreen() {
  const [activeToolId, setActiveToolId] = React.useState(null);
  const [running, setRunning] = React.useState(false);
  const [logLines, setLogLines] = React.useState([]);
  const [done, setDone] = React.useState(false);

  const tools = [
    { id:'sfc_dism',      label:'Reparar Arquivos do Sistema (DISM + SFC)', desc:'DISM → SFC. Valida e restaura arquivos corrompidos do Windows.', duration:'~30 – 50 min', reboot:false, cat:'essential', steps:['Executando DISM (RestoreHealth)… pode levar 20-30 min','DISM concluído — imagem reparada','Executando SFC (scannow)… pode levar 10-20 min','SFC concluído — arquivos validados'] },
    { id:'network_reset', label:'Reparar Conexão de Rede',                  desc:'Reset completo: Winsock, TCP/IP, IP release/renew, flush DNS.',   duration:'~1 min',       reboot:true,  cat:'essential', steps:['Resetando Winsock','Resetando pilha TCP/IP','Liberando IP','Renovando IP','Limpando cache DNS'] },
    { id:'wu_reset',      label:'Reparar Windows Update',                   desc:'Para serviços, limpa SoftwareDistribution e catroot2, reinicia.', duration:'~3 min',       reboot:false, cat:'essential', steps:['Parando wuauserv','Parando bits','Limpando SoftwareDistribution…','Limpando catroot2…','Reiniciando serviços'] },
    { id:'store_reset',   label:'Reparar Microsoft Store',                  desc:'Executa wsreset — corrige apps UWP que não abrem.',               duration:'~1 min',       reboot:false, cat:'advanced',  steps:['Executando wsreset…','wsreset concluído'] },
    { id:'printer_reset', label:'Reparar Fila de Impressão',                desc:'Para spooler, limpa fila travada, reinicia serviço.',             duration:'~1 min',       reboot:false, cat:'advanced',  steps:['Parando Spooler','Limpando fila travada','Reiniciando Spooler'] },
  ];

  function runTool(tool) {
    setActiveToolId(tool.id);
    setRunning(true);
    setDone(false);
    setLogLines([]);
    const lines = [];
    tool.steps.forEach((step, i) => {
      setTimeout(() => {
        lines.push(`✓  ${step}`);
        setLogLines([...lines]);
        if (i === tool.steps.length - 1) {
          setTimeout(() => { setRunning(false); setDone(true); }, 500);
        }
      }, (i + 1) * 500);
    });
  }

  const essential = tools.filter(t => t.cat === 'essential');
  const advanced  = tools.filter(t => t.cat === 'advanced');

  const containerStyle = { padding:'24px 32px', height:'100%', boxSizing:'border-box', display:'flex', flexDirection:'column', gap:14, overflowY:'auto' };

  function ToolCard({ tool }) {
    const isActive = activeToolId === tool.id;
    return (
      <div style={{...TS.card,border:`1px solid ${isActive?T.cyan:'#1a2230'}`,display:'flex',gap:12,alignItems:'flex-start'}}>
        <div style={{flex:1}}>
          <div style={{display:'flex',alignItems:'center',gap:8}}>
            <span style={{color:'#fff',fontSize:12,fontWeight:600,fontFamily:T.fontBody}}>{tool.label}</span>
            {tool.reboot && <span style={{fontSize:9,border:'1px solid #ffbd2e',color:'#ffbd2e',borderRadius:10,padding:'1px 6px',background:'rgba(255,189,46,0.1)'}}>REBOOT</span>}
          </div>
          <div style={{color:'#888',fontSize:10,marginTop:3,fontFamily:T.fontBody,lineHeight:1.5}}>{tool.desc}</div>
          <div style={{color:T.fgSubtle,fontFamily:T.fontMono,fontSize:9,marginTop:3}}>{tool.duration}</div>
          {isActive && logLines.length > 0 && (
            <div style={{background:'#020305',borderRadius:4,padding:'8px 10px',marginTop:8,fontFamily:T.fontMono,fontSize:10,color:T.cyan,lineHeight:1.8}}>
              {logLines.map((l,i)=><div key={i}>{l}</div>)}
              {done && <div style={{color:T.stateOn,marginTop:4}}>✓ Concluído.</div>}
            </div>
          )}
        </div>
        <button
          onClick={() => runTool(tool)}
          disabled={running}
          style={{background:T.cyan,color:'#000',fontWeight:700,border:'none',borderRadius:6,padding:'7px 16px',cursor:'pointer',fontSize:11,flexShrink:0,opacity:running?0.4:1,fontFamily:T.fontBody}}
        >
          {isActive && running ? '...' : 'Executar'}
        </button>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <div>
        <div style={{fontFamily:T.fontBody,fontSize:22,fontWeight:700,color:T.fgPrimary}}>REPAROS</div>
        <div style={{fontFamily:T.fontBody,fontSize:12,color:T.fgMuted,marginTop:2}}>Ferramentas de diagnóstico e restauração do Windows</div>
      </div>
      <div style={{...TS.sectionLabel}}>ESSENCIAL</div>
      {essential.map(t => <ToolCard key={t.id} tool={t} />)}
      <div style={{...TS.sectionLabel,marginTop:4}}>AVANÇADO</div>
      {advanced.map(t => <ToolCard key={t.id} tool={t} />)}
      <div style={{fontFamily:T.fontMono,fontSize:10,color:T.cyan}}>&gt; Nenhum reparo executado ainda.</div>
    </div>
  );
}

Object.assign(window, { ReparosScreen });
