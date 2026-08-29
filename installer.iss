; ─────────────────────────────────────────────────────────────────────
;  TecnoApp — script do instalador (Inno Setup 6)
;
;  Compilar:
;      1. .venv\Scripts\pyinstaller.exe tecnoapp.spec --noconfirm
;      2. ISCC.exe installer.iss
;
;  Gera:  installer_output\TecnoApp-Setup-<versao>.exe
;
;  A versao vem de app\version.py — nao editar aqui.
; ─────────────────────────────────────────────────────────────────────

#define AppName        "TecnoApp"
#define AppPublisher   "Tecnosup Solucoes Digitais"
#define AppExeName     "TecnoApp.exe"
#define AppURL         "https://github.com/vitorrfl/Tecnoapp"

; Versao: injetada pelo build.py a partir de app/version.py.
; Compilando na mao? Passe /DAppVersion=x.y.z para o ISCC.
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{8F3A2B10-7C4D-4E91-A6F2-1D5E9B0C3A87}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
LicenseFile=
OutputDir=installer_output
OutputBaseFilename=TecnoApp-Setup-{#AppVersion}
SetupIconFile=app\assets\tecnoapp.ico
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

; O app mexe em HKLM, servicos e powercfg — exige admin.
PrivilegesRequired=admin

; 465MB de payload: nao cabe em 32-bit
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible

; Fecha o app antes de atualizar (o updater passa /CLOSEAPPLICATIONS)
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na area de trabalho"; \
    GroupDescription: "Atalhos:"

[Files]
; Todo o dist do PyInstaller (modo onedir)
Source: "dist\TecnoApp\*"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}";              Filename: "{app}\{#AppExeName}"
Name: "{group}\Desinstalar {#AppName}";  Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}";        Filename: "{app}\{#AppExeName}"; \
    Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; \
    Description: "Executar o {#AppName} agora"; \
    Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Estado do app (snapshots do Modo Gamer, preferencias).
; NAO removido por padrao — se o usuario reinstalar, mantem os snapshots
; para conseguir reverter tweaks aplicados. Descomente para limpar tudo:
; Type: filesandordirs; Name: "{userappdata}\TecnoApp"
Type: filesandordirs; Name: "{app}\_internal\__pycache__"
