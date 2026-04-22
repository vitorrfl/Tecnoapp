# TecnoApp

Ferramenta de otimização e limpeza para Windows 10/11 com interface Qt.
O carro-chefe é o **Modo Gamer**: um toggle reversível que aplica um
conjunto de tweaks reais de CPU, GPU, sistema e rede para ganhar FPS e
reduzir latência durante sessões de jogo.

> **Status:** em desenvolvimento ativo na branch `feature/modo-gamer`.
> Identidade visual (neon ciano `#0eb3ff` + roxo `#7000ff` sobre `#030407`)
> é preservada — não refatorar a UI sem alinhamento.

---

## Stack

- Python 3.11+
- PySide6 (Qt6) para GUI
- APIs Windows: `winreg`, `ctypes` (ntdll), `subprocess` chamando
  `powercfg`, `sc`, `netsh`, `taskkill` e cmdlets PowerShell
  (`Get-NetTCPSetting` etc. — usados quando a saída do `netsh` é
  localizada e varia por idioma)

## Rodando

```bash
cd app
python app3.py
```

O app se auto-eleva via `ShellExecuteW runas` quando não está como admin —
necessário porque quase todos os tweaks exigem privilégio (HKLM, serviços,
powercfg, etc).

Estado persistente (snapshots e preferências) fica em
`%APPDATA%\TecnoApp\`.

## Restore standalone

Se o usuário desinstalar o app com o Modo Gamer ativo, os tweaks
continuam aplicados. Use o CLI para reverter sem UI:

```bash
python -m tools.restore_gamer           # reverte tudo
python -m tools.restore_gamer --check   # só status
```

Auto-eleva se não estiver como admin.

---

## Modo Gamer — Arquitetura

```
app/gamer/
├── engine.py          # GamerEngine: register/activate/deactivate
├── facade.py          # build_engine() registra todos os tweaks
├── snapshot.py        # persistência em %APPDATA%\TecnoApp\
├── prefs.py           # preferências opt-in do usuário
├── tweaks/
│   ├── base.py        # Tweak (ABC), Category, RiskLevel, TweakResult
│   ├── cpu.py
│   ├── gpu.py
│   ├── system.py
│   └── network.py
└── utils/
    ├── registry.py    # wrapper winreg (snapshot/restore)
    ├── powercfg.py
    ├── netsh.py
    └── services.py
```

**Padrão de cada tweak:** subclasse de `Tweak` que implementa
`is_supported`, `read_current` (para snapshot), `apply` e
`revert(previous_state)`. Todo tweak é idempotente. Falhas parciais no
`activate()` não disparam rollback automático — o usuário clica em
"Desativar" para obter revert limpo usando o snapshot salvo.

**Opt-in:** tweaks com `opt_in = True` são pulados no one-click e só
rodam se o usuário habilitar na tela Avançado. Use para operações de
risco (APIs de kernel, drivers).

---

## Lista de tweaks (17 total)

### CPU (3)

| ID | Ação | Fonte |
|---|---|---|
| `cpu.ultimate_performance` | Duplica e ativa o power plan "Ultimate Performance" (GUID `e9a42b02-...`). | [MS Docs — powercfg](https://learn.microsoft.com/windows-hardware/customize/power-settings/configure-power-settings) |
| `cpu.core_parking_off` | Desabilita core parking via `CPMINCORES=100` em AC/DC. Usa `unhide_attribute` porque o setting é oculto por padrão. | [MS Docs — Processor power management options](https://learn.microsoft.com/windows-hardware/design/device-experiences/modern-standby-device-power-states) |
| `cpu.mmcss_games` | Prioriza o perfil "Games" do MMCSS (`GPU Priority=8`, `Priority=6`, `Scheduling Category=High`, `SFIO Priority=High`). | [MS Docs — Multimedia Class Scheduler Service](https://learn.microsoft.com/windows/win32/procthread/multimedia-class-scheduler-service) |

### GPU (5)

| ID | Ação | Fonte |
|---|---|---|
| `gpu.hags` | Liga HAGS (Hardware Accelerated GPU Scheduling) — `HwSchMode=2`. Gated para build ≥ 19041. Requer reboot. | [DirectX Dev Blog — GPU scheduling](https://devblogs.microsoft.com/directx/hardware-accelerated-gpu-scheduling/) |
| `gpu.fso_off` | Desliga Fullscreen Optimizations (4 valores em `HKCU\System\GameConfigStore`). | MS knowledge base — `GameConfigStore` |
| `gpu.gamedvr_off` | Desliga Game DVR (gravação em background). | Windows Game Bar docs |
| `gpu.game_mode_on` | Liga Game Mode. | [Game Mode](https://support.microsoft.com/windows/game-mode-in-windows-5b4b73bc-d3cf-4ec5-d3b5-fe9bca59a6b9) |
| `gpu.tdr_delay` | Estende o TDR de GPU (`TdrDelay=10`). Requer reboot. | [MS Docs — TDR registry keys](https://learn.microsoft.com/windows-hardware/drivers/display/tdr-registry-keys) |

### Sistema (5)

| ID | Ação | Fonte |
|---|---|---|
| `system.kill_bloat` | Encerra processos em background (OneDrive, Teams, Spotify, YourPhone, GameBar…). **Discord e Steam nunca entram nessa lista.** Whitelist only. | taskkill |
| `system.empty_standby` ⚠ **opt-in** | Purga standby memory via `NtSetSystemInformation(SystemMemoryListInformation)` com `RtlAdjustPrivilege(SeProfileSingleProcessPrivilege)`. Causou BSOD em 2026-04-21 — desativado por padrão. | ntdll (semi-documentado; ver RAMMap) |
| `system.visual_effects_perf` | `VisualFXSetting=2` (ajustar para melhor desempenho). | `HKCU\...\Explorer\VisualEffects` |
| `system.toasts_off` | `ToastEnabled=0` — evita notificações tirarem o jogo do fullscreen. | `HKCU\...\PushNotifications` |
| `system.services_demand` | Coloca `SysMain`, `DiagTrack`, `WSearch` em modo demand. **Serviços críticos nunca são tocados** (Audiosrv, RpcSs, CryptSvc, WinDefend, BITS). | `sc config` |

### Rede (4)

| ID | Ação | Fonte |
|---|---|---|
| `network.tcp_autotuning` | Define AutoTuningLevelLocal=Normal. Lê via `Get-NetTCPSetting` (PowerShell) porque `netsh int tcp show global` tem saída localizada. | [MS Docs — NetTCPSetting](https://learn.microsoft.com/powershell/module/nettcpip/get-nettcpsetting) |
| `network.nagle_off` | Desliga Nagle em todas as interfaces ativas (`TcpAckFrequency=1`, `TCPNoDelay=1`, `TcpDelAckTicks=0`). | `HKLM\...\Tcpip\Parameters\Interfaces\{GUID}` |
| `network.throttling_off` | `NetworkThrottlingIndex=0xFFFFFFFF` — desativa throttling em multimídia. | [MS Docs — Multimedia network throttling](https://learn.microsoft.com/windows-hardware/drivers/network/using-registry-values-to-enable-and-disable-task-offloading) |
| `network.flush_dns` | `ipconfig /flushdns`. | — |

---

## Regras de produto

- **Nunca** encerrar Discord ou Steam no `system.kill_bloat`.
- **Nunca** auto-reboot. Tweaks com `requires_reboot` mostram modal de
  aviso; a decisão é do usuário.
- **Nunca** tocar em serviços críticos (WinDefend, Audiosrv, RpcSs,
  CryptSvc, BITS).
- **Identidade visual intocável.** Alterações de UI devem preservar as
  cores e a vibe neon/cyber.

## Incidentes conhecidos

- **2026-04-21 — BSOD em `system.empty_standby`**: primeira ativação real
  do Modo Gamer gerou BSOD (kernel / MEMORY_MANAGEMENT). `NtSetSystemInformation`
  pode colidir com drivers em certos sistemas. Tweak marcado como `opt_in`
  e só roda se habilitado na tela Avançado.
