import sys
import os
import subprocess
import ctypes
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QMessageBox,
                             QHBoxLayout, QPushButton, QLabel, QFrame, QGraphicsDropShadowEffect,
                             QCheckBox, QScrollArea)
from PySide6.QtGui import QFont, QColor, QCursor, QPainter, QPen
from PySide6.QtCore import Qt, QTimer, QThread, Signal

from gamer import build_engine, load_enabled_optins, save_enabled_optins
from gamer.tweaks import Category

_CLEAN_CATEGORIES = [
    {
        "id": "temp_user",
        "label": "Temporários do Usuário (%TEMP%)",
        "desc": "Arquivos criados por programas durante o uso — jogos, editores, browsers. "
                "Nunca são reusados após a execução.",
        "impact": "~100 MB – 2 GB",
        "default": True,
        "warning": "",
    },
    {
        "id": "temp_windows",
        "label": "Temporários do Windows",
        "desc": "Arquivos criados pelo sistema operacional para operações internas. "
                "Acumulam após instalações e atualizações.",
        "impact": "~50 MB – 500 MB",
        "default": True,
        "warning": "",
    },
    {
        "id": "prefetch",
        "label": "Prefetch do Windows",
        "desc": "Cache que acelera a abertura de programas. Após limpar, a primeira "
                "abertura de cada programa fica levemente mais lenta — isso é normal.",
        "impact": "~20 MB – 200 MB",
        "default": True,
        "warning": "",
    },
    {
        "id": "dns_cache",
        "label": "Cache DNS (Endereços de Sites)",
        "desc": "Tabela local de endereços de sites visitados. Limpar resolve problemas "
                "de conexão e sites que não abrem corretamente.",
        "impact": "Desprezível",
        "default": True,
        "warning": "",
    },
    {
        "id": "recycle_bin",
        "label": "Lixeira",
        "desc": "Arquivos que você deletou mas estão reservados na Lixeira. "
                "Esvaziar é permanente.",
        "impact": "Varia (pode ser GBs)",
        "default": True,
        "warning": "Não é possível recuperar arquivos após esvaziar.",
    },
    {
        "id": "thumbnail_cache",
        "label": "Cache de Miniaturas (Fotos/Vídeos)",
        "desc": "Pré-visualizações de imagens criadas pelo Windows Explorer. "
                "São recriadas automaticamente na próxima abertura da pasta.",
        "impact": "~50 MB – 300 MB",
        "default": True,
        "warning": "",
    },
    {
        "id": "update_cache",
        "label": "Cache do Windows Update",
        "desc": "Arquivos usados para instalar atualizações já concluídas. "
                "O Windows baixa novamente se precisar reinstalar.",
        "impact": "~200 MB – 5 GB",
        "default": False,
        "warning": "O Windows pode baixar esses arquivos novamente automaticamente se precisar.",
    },
    {
        "id": "event_logs",
        "label": "Logs de Eventos do Windows",
        "desc": "Histórico de atividades, erros e avisos do sistema. "
                "Técnicos usam para diagnosticar problemas.",
        "impact": "~10 MB – 100 MB",
        "default": False,
        "warning": "Apaga o histórico de erros — pode dificultar diagnóstico de problemas futuros.",
    },
    {
        "id": "minidumps",
        "label": "Relatórios de Travamento (Minidumps)",
        "desc": "Arquivos gerados automaticamente quando o Windows ou um programa trava. "
                "Técnicos usam esses arquivos para descobrir a causa do crash.",
        "impact": "~10 MB – 100 MB",
        "default": False,
        "warning": "Remove informações úteis para diagnosticar travamentos e BSODs futuros.",
    },
]

class GamerWorker(QThread):
    finished = Signal(object, str)

    def __init__(self, engine, action, enabled_optins=None):
        super().__init__()
        self.engine = engine
        self.action = action
        self.enabled_optins = enabled_optins or set()

    def run(self):
        if self.action == "activate":
            report = self.engine.activate(enabled_optins=self.enabled_optins)
        else:
            report = self.engine.deactivate()
        self.finished.emit(report, self.action)


class CleanWorker(QThread):
    step_done = Signal(str, int)   # (label, bytes_freed)
    finished  = Signal(int)        # total bytes freed

    _STEPS = [
        ("temp_user",       "Temporários do usuário",
         ['del /s /f /q "%TEMP%\\*.*"'], []),
        ("temp_windows",    "Temporários do Windows",
         ['del /s /f /q "C:\\Windows\\Temp\\*.*"'], []),
        ("prefetch",        "Prefetch do Windows",
         ['del /s /f /q "C:\\Windows\\Prefetch\\*.*"'], []),
        ("dns_cache",       "Cache DNS",
         ["ipconfig /flushdns"], []),
        ("recycle_bin",     "Lixeira",
         [], ["Clear-RecycleBin -Force -ErrorAction SilentlyContinue"]),
        ("thumbnail_cache", "Cache de miniaturas",
         ['del /f /q "%LocalAppData%\\Microsoft\\Windows\\Explorer\\thumbcache_*.db"'], []),
        # Sem parar o serviço — Remove-Item tenta deletar o que não estiver bloqueado
        ("update_cache",    "Cache do Windows Update",
         [], ["Get-ChildItem 'C:\\Windows\\SoftwareDistribution\\Download' "
              "-ErrorAction SilentlyContinue | "
              "Remove-Item -Force -Recurse -ErrorAction SilentlyContinue"]),
        # Security omitido: requer SeAuditPrivilege além de admin
        ("event_logs",      "Logs de eventos",
         [], ['wevtutil cl "System" 2>$null',
              'wevtutil cl "Application" 2>$null',
              'wevtutil cl "Setup" 2>$null']),
        ("minidumps",       "Relatórios de travamento",
         ['del /s /f /q "C:\\Windows\\Minidump\\*.*"'], []),
    ]

    def __init__(self, selected_ids: set):
        super().__init__()
        self.selected_ids = selected_ids

    def _free_bytes(self) -> int:
        free = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(
            ctypes.c_wchar_p("C:\\"), None, None, ctypes.pointer(free)
        )
        return free.value

    def run(self):
        try:
            space_before = self._free_bytes()
            for step_id, label, shell_cmds, ps_cmds in self._STEPS:
                if step_id not in self.selected_ids:
                    continue
                before = self._free_bytes()
                try:
                    if shell_cmds:
                        subprocess.run(
                            " & ".join(shell_cmds),
                            shell=True,
                            creationflags=subprocess.CREATE_NO_WINDOW,
                            timeout=120,
                        )
                    if ps_cmds:
                        subprocess.run(
                            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
                             "; ".join(ps_cmds)],
                            creationflags=subprocess.CREATE_NO_WINDOW,
                            timeout=120,
                        )
                except Exception:
                    pass
                try:
                    freed = max(0, self._free_bytes() - before)
                except Exception:
                    freed = 0
                self.step_done.emit(label, freed)
            try:
                total = max(0, self._free_bytes() - space_before)
            except Exception:
                total = 0
        except Exception:
            total = 0
        self.finished.emit(total)


def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

class TecnoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Garante que as funções de registro e sistema funcionem
        if not is_admin():
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
            sys.exit()

        self.setWindowTitle("TECNOAPP OTIMIZAÇÃO - Pro Edition")
        self.setFixedSize(850, 600)

        # Cores da Identidade Visual
        self.primary = "#0eb3ff"    
        self.secondary = "#7000ff"  
        self.danger = "#ff4b4b"
        self.bg_dark = "#030407"    
        self.log_file = os.path.join(os.environ.get('TEMP'), 'tecnosup_clean_log.txt')
        
        self.status_cache = ""
        self._clean_checkboxes: dict = {}
        self._clean_worker: CleanWorker | None = None
        self._clean_log_lines: list = []
        self.gamer_engine = build_engine()
        self._gamer_worker = None

        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {self.bg_dark}; }}
            #Sidebar {{ background-color: rgba(3, 4, 7, 245); border-right: 1px solid rgba(14, 179, 255, 0.1); }}
            QLabel {{ color: #ffffff; background: transparent; }}
            
            QPushButton#MenuBtn {{
                background: transparent; border: 2px solid {self.primary};
                color: {self.primary}; font-family: 'Segoe UI'; font-size: 11px;
                font-weight: bold; border-radius: 10px; padding: 8px;
            }}
            QPushButton#MenuBtn:hover {{ background: {self.primary}; color: black; }}
            
            QPushButton#ActionBtn {{
                background-color: {self.primary}; color: black; font-weight: bold;
                border-radius: 8px; padding: 12px; border: none; font-size: 14px;
            }}
            QPushButton#ActionBtn:hover {{ background-color: white; }}

            QPushButton#InfoBtn {{
                background: rgba(14, 179, 255, 0.1); border: 1px solid {self.primary}; 
                color: {self.primary}; font-size: 14px; border-radius: 15px; font-weight: bold;
            }}
            QPushButton#InfoBtn:hover {{ background: {self.primary}; color: black; }}

            QPushButton#GamerNav {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {self.primary}, stop:1 {self.secondary});
                color: white; font-weight: bold; border-radius: 15px; padding: 10px; border: 1px solid transparent;
            }}
            QPushButton#ExitBtn {{
                background: transparent; border: 1px solid #ff4b4b; color: #ff4b4b; border-radius: 8px; font-weight: bold;
            }}
            QPushButton#ExitBtn:hover {{ background: #ff4b4b; color: white; }}
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        sidebar = QFrame(); sidebar.setObjectName("Sidebar"); sidebar.setFixedWidth(220)
        side_lyt = QVBoxLayout(sidebar); side_lyt.setContentsMargins(15, 30, 15, 30); side_lyt.setSpacing(10)
        
        logo = QLabel("TECNOSUP"); logo.setFont(QFont("Segoe UI", 22, QFont.Bold))
        self.add_neon(logo, self.primary); side_lyt.addWidget(logo, alignment=Qt.AlignCenter)
        side_lyt.addSpacing(20)
        
        side_lyt.addWidget(self.create_menu_btn("🧹 LIMPEZA", self.show_limpeza))
        side_lyt.addWidget(self.create_menu_btn("⚡ OTIMIZAÇÃO", self.show_otimizacao))
        side_lyt.addWidget(self.create_menu_btn("🔧 REPAROS", self.show_reparos))
        
        self.btn_gamer_nav = QPushButton("🎮 MODO GAMER")
        self.btn_gamer_nav.setObjectName("GamerNav")
        self.btn_gamer_nav.clicked.connect(self.show_gamer)
        self.add_neon(self.btn_gamer_nav, self.secondary)
        side_lyt.addWidget(self.btn_gamer_nav)

        side_lyt.addStretch()
        btn_sair = QPushButton("SAIR"); btn_sair.setObjectName("ExitBtn"); btn_sair.setFixedSize(180, 35)
        btn_sair.clicked.connect(self.finalizar_app); side_lyt.addWidget(btn_sair, alignment=Qt.AlignCenter)

        main_layout.addWidget(sidebar)

        self.content_container = QWidget()
        self.content_container.paintEvent = self.paint_grid 
        self.content_lyt = QVBoxLayout(self.content_container)
        self.content_lyt.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.content_container)

        self.show_home()

    def get_free_space(self):
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p("C:\\"), None, None, ctypes.pointer(free_bytes))
        return free_bytes.value

    def format_size(self, size):
        if size < 1024*1024: return f"{(size/1024):.2f} KB"
        return f"{(size/(1024*1024)):.2f} MB" if size < 1024*1024*1024 else f"{(size/(1024*1024*1024)):.2f} GB"

    def run_clean_process(self, selected_ids=None):
        if not isinstance(selected_ids, set):
            selected_ids = {c["id"] for c in _CLEAN_CATEGORIES if c["default"]}
        if self._clean_worker is not None:
            return
        self._clean_log_lines = []
        self.show_limpeza_progresso()
        self._clean_worker = CleanWorker(selected_ids)
        self._clean_worker.step_done.connect(self._on_clean_step)
        self._clean_worker.finished.connect(self._on_clean_done)
        self._clean_worker.start()

    def update_ui_status(self):
        if self.status_cache:
            self.status_lbl.setText(self.status_cache)
            self.status_lbl.setStyleSheet("color: #ffbd2e; font-family: 'Consolas'; font-weight: bold; line-height: 150%;")

    def show_limpeza(self):
        self.clear_screen()
        self.add_title("MÓDULO DE LIMPEZA")
        desc = QLabel("Limpeza segura com ferramentas nativas do Windows.")
        desc.setStyleSheet("color: #444; margin-bottom: 25px;")
        self.content_lyt.addWidget(desc, alignment=Qt.AlignCenter)

        self.add_action_btn("LIMPEZA RÁPIDA", lambda: self.run_clean_process())

        btn_adv = QPushButton("CONFIGURAR LIMPEZA")
        btn_adv.setFixedWidth(400)
        btn_adv.setFixedHeight(42)
        btn_adv.setStyleSheet(
            f"background: transparent; border: 1px solid {self.primary}; color: {self.primary};"
            "font-weight: bold; border-radius: 8px; font-size: 13px;"
        )
        btn_adv.clicked.connect(self.show_limpeza_avancada)
        self.content_lyt.addWidget(btn_adv, alignment=Qt.AlignCenter)

        log = "Nunca"
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, "r") as f: log = f.read()
            except: pass
        self.add_status_bar(self.status_cache if self.status_cache else f"> Histórico: {log}")
        self.update_ui_status()

    def show_limpeza_avancada(self):
        self.clear_screen()
        self.add_title("CONFIGURAR LIMPEZA")
        sub = QLabel("Selecione o que deseja limpar. Os marcados por padrão são seguros para todos.")
        sub.setStyleSheet("color: #555; font-size: 11px; margin-bottom: 8px;")
        sub.setWordWrap(True)
        sub.setAlignment(Qt.AlignCenter)
        self.content_lyt.addWidget(sub)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
            "QScrollBar:vertical { width: 6px; background: #111; border-radius: 3px; }"
            "QScrollBar::handle:vertical { background: #0eb3ff; border-radius: 3px; }"
        )
        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        inner_lyt = QVBoxLayout(inner)
        inner_lyt.setSpacing(6)
        inner_lyt.setContentsMargins(4, 4, 4, 4)

        self._clean_checkboxes = {}

        safe_cats = [c for c in _CLEAN_CATEGORIES if c["default"]]
        opt_cats = [c for c in _CLEAN_CATEGORIES if not c["default"]]

        safe_hdr = QLabel("── SEGURO (sempre recomendado)")
        safe_hdr.setStyleSheet(f"color: {self.primary}; font-weight: bold; font-size: 11px; margin-top: 4px;")
        inner_lyt.addWidget(safe_hdr)

        for cat in safe_cats:
            inner_lyt.addWidget(self._build_clean_row(cat, checked=True))

        opt_hdr = QLabel("── OPCIONAL (revise antes de ativar)")
        opt_hdr.setStyleSheet("color: #ffbd2e; font-weight: bold; font-size: 11px; margin-top: 10px;")
        inner_lyt.addWidget(opt_hdr)

        for cat in opt_cats:
            inner_lyt.addWidget(self._build_clean_row(cat, checked=False))

        inner_lyt.addStretch()
        scroll.setWidget(inner)
        self.content_lyt.addWidget(scroll, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        back = QPushButton("Voltar")
        back.setFixedWidth(100)
        back.setStyleSheet(
            "background: transparent; border: 1px solid #333; color: #666;"
            "font-weight: bold; border-radius: 6px; padding: 8px;"
        )
        back.clicked.connect(self.show_limpeza)

        run = QPushButton("Iniciar limpeza selecionada")
        run.setFixedWidth(220)
        run.setStyleSheet(
            f"background: {self.primary}; color: #030407; border: none;"
            "border-radius: 6px; padding: 8px; font-family: 'Segoe UI'; font-weight: bold;"
        )
        run.clicked.connect(self._run_limpeza_avancada)

        btn_row.addWidget(back)
        btn_row.addSpacing(10)
        btn_row.addWidget(run)
        btn_row.addStretch(1)
        self.content_lyt.addLayout(btn_row)

        self.add_status_bar("> Escolha o que limpar e clique em Iniciar.")

    def _build_clean_row(self, cat, checked):
        row = QFrame()
        row.setStyleSheet(
            "QFrame { background: #0a0d14; border: 1px solid #1a1f2b; border-radius: 6px; }"
        )
        lyt = QVBoxLayout(row)
        lyt.setContentsMargins(10, 8, 10, 8)
        lyt.setSpacing(2)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)

        cb = QCheckBox(cat["label"])
        cb.setChecked(checked)
        cb.setStyleSheet(
            "QCheckBox { color: white; font-family: 'Segoe UI'; font-size: 12px; }"
            "QCheckBox::indicator { width: 14px; height: 14px; }"
        )
        self._clean_checkboxes[cat["id"]] = cb
        top.addWidget(cb, 1)

        impact = QLabel(cat["impact"])
        impact.setStyleSheet("color: #0eb3ff; font-family: 'Consolas'; font-size: 10px;")
        top.addWidget(impact)
        lyt.addLayout(top)

        desc = QLabel(cat["desc"])
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #888; font-family: 'Segoe UI'; font-size: 10px; padding-left: 22px;")
        lyt.addWidget(desc)

        if cat.get("warning"):
            warn = QLabel("⚠ " + cat["warning"])
            warn.setWordWrap(True)
            warn.setStyleSheet("color: #ff8a4b; font-family: 'Segoe UI'; font-size: 10px; padding-left: 22px;")
            lyt.addWidget(warn)

        return row

    def _run_limpeza_avancada(self):
        selected = {cid for cid, cb in self._clean_checkboxes.items() if cb.isChecked()}
        self.run_clean_process(selected_ids=selected)

    def show_limpeza_progresso(self):
        self.clear_screen()
        self.add_title("LIMPEZA EM ANDAMENTO")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { border: 1px solid #1a1f2b; background: #0a0d14; border-radius: 8px; }"
            "QScrollBar:vertical { width: 6px; background: #111; border-radius: 3px; }"
            "QScrollBar::handle:vertical { background: #0eb3ff; border-radius: 3px; }"
        )
        log_inner = QWidget()
        log_inner.setStyleSheet("background: transparent;")
        log_lyt = QVBoxLayout(log_inner)
        log_lyt.setAlignment(Qt.AlignTop)
        log_lyt.setContentsMargins(14, 12, 14, 12)

        self._clean_log_label = QLabel("> Iniciando limpeza...")
        self._clean_log_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._clean_log_label.setStyleSheet(
            f"color: {self.primary}; font-family: 'Consolas'; font-size: 12px; line-height: 180%;"
        )
        self._clean_log_label.setWordWrap(True)
        log_lyt.addWidget(self._clean_log_label)
        scroll.setWidget(log_inner)
        self.content_lyt.addWidget(scroll, 1)

        self._clean_total_label = QLabel("")
        self._clean_total_label.setFont(QFont("Segoe UI", 20, QFont.Bold))
        self._clean_total_label.setAlignment(Qt.AlignCenter)
        self._clean_total_label.setStyleSheet(f"color: {self.primary}; margin-top: 8px;")
        self._clean_total_label.hide()
        self.content_lyt.addWidget(self._clean_total_label)

        self._clean_btn_voltar = QPushButton("VOLTAR")
        self._clean_btn_voltar.setFixedWidth(200)
        self._clean_btn_voltar.setEnabled(False)
        self._clean_btn_voltar.setStyleSheet(
            "background: transparent; border: 1px solid #333; color: #444;"
            "font-weight: bold; border-radius: 8px; padding: 10px;"
        )
        self._clean_btn_voltar.clicked.connect(self.show_limpeza)
        self.content_lyt.addWidget(self._clean_btn_voltar, alignment=Qt.AlignCenter)

    def _on_clean_step(self, label: str, freed: int):
        size_str = f"   +{self.format_size(freed)}" if freed > 1024 else ""
        self._clean_log_lines.append(f"✓  {label}{size_str}")
        self._clean_log_label.setText("\n".join(self._clean_log_lines))

    def _on_clean_done(self, total: int):
        if self._clean_worker is not None:
            self._clean_worker.wait()       # garante que a thread encerrou no lado Qt
            self._clean_worker.deleteLater()  # agenda destruição segura do objeto C++
            self._clean_worker = None
        if total > 102_400:
            msg = f"✓  {self.format_size(total)} liberados"
        else:
            msg = "✓  Sistema já estava otimizado"
        self._clean_total_label.setText(msg)
        self._clean_total_label.show()
        self.add_neon(self._clean_total_label, self.primary)
        self._clean_btn_voltar.setEnabled(True)
        self._clean_btn_voltar.setStyleSheet(
            f"background: transparent; border: 1px solid {self.primary}; color: {self.primary};"
            "font-weight: bold; border-radius: 8px; padding: 10px;"
        )
        self.status_cache = msg

    def show_home(self): self.clear_screen(); lbl = QLabel("SISTEMA PRONTO"); lbl.setFont(QFont("Segoe UI", 28, QFont.Bold)); self.add_neon(lbl, self.primary); self.content_lyt.addWidget(lbl, alignment=Qt.AlignCenter)
    def show_otimizacao(self): self.clear_screen(); self.add_title("OTIMIZAÇÃO"); self.add_status_bar("> Menu pronto.")
    def show_reparos(self): self.clear_screen(); self.add_title("REPAROS"); self.add_status_bar("> Menu pronto.")
    def show_gamer(self):
        self.clear_screen()
        self.add_title("MODO GAMER", self.secondary)

        active = self.gamer_engine.is_active()
        snapshot = self.gamer_engine.active_snapshot() if active else None

        if active and snapshot:
            status_txt = f"● ATIVO desde {snapshot.created_at}"
            status_color = self.primary
        else:
            status_txt = "● INATIVO"
            status_color = "#666"

        self.gamer_status = QLabel(status_txt)
        self.gamer_status.setStyleSheet(
            f"color: {status_color}; font-family: 'Consolas'; font-size: 13px; font-weight: bold;"
        )
        self.content_lyt.addWidget(self.gamer_status, alignment=Qt.AlignCenter)
        self.content_lyt.addSpacing(15)

        if active:
            self.add_danger_btn("DESATIVAR MODO GAMER", self.run_gamer_deactivate)
        else:
            self.add_action_btn("ATIVAR MODO GAMER", self.run_gamer_activate)

        self.content_lyt.addSpacing(10)

        adv = QPushButton("Avançado (granular)")
        adv.setFixedWidth(260)
        adv.setCursor(QCursor(Qt.PointingHandCursor))
        adv.setStyleSheet(
            "background:transparent; color:#7000ff; border:1px solid #7000ff;"
            "border-radius:6px; padding:6px; font-family:'Segoe UI'; font-size:11px;"
        )
        adv.clicked.connect(self.show_gamer_advanced)
        self.content_lyt.addWidget(adv, alignment=Qt.AlignCenter)

        self.content_lyt.addSpacing(15)
        grouped = self.gamer_engine.tweaks_by_category()
        counts = (
            f"CPU: {len(grouped[Category.CPU])}    "
            f"GPU: {len(grouped[Category.GPU])}    "
            f"Sistema: {len(grouped[Category.SYSTEM])}    "
            f"Rede: {len(grouped[Category.NETWORK])}"
        )
        detail = QLabel(counts)
        detail.setStyleSheet("color: #555; font-family: 'Segoe UI'; font-size: 11px;")
        self.content_lyt.addWidget(detail, alignment=Qt.AlignCenter)

        enabled = load_enabled_optins()
        if enabled:
            opt_lbl = QLabel(f"opt-in ativos: {', '.join(sorted(enabled))}")
            opt_lbl.setStyleSheet("color: #7000ff; font-family: 'Consolas'; font-size: 10px;")
            self.content_lyt.addWidget(opt_lbl, alignment=Qt.AlignCenter)

        self.add_status_bar("> Pronto.")

    def show_gamer_advanced(self):
        self.clear_screen()
        self.add_title("MODO GAMER — AVANÇADO", self.secondary)

        intro = QLabel(
            "Escolha quais tweaks rodam no one-click.\n"
            "Os essenciais sempre rodam. Os marcados como opt-in só rodam se você habilitar aqui."
        )
        intro.setAlignment(Qt.AlignCenter)
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#aaa; font-family:'Segoe UI'; font-size:12px;")
        self.content_lyt.addWidget(intro)
        self.content_lyt.addSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none; background:transparent;}")
        inner = QWidget()
        inner_lyt = QVBoxLayout(inner)
        inner_lyt.setContentsMargins(10, 0, 10, 0)
        inner_lyt.setSpacing(8)

        enabled = load_enabled_optins()
        self._advanced_checks = {}

        grouped = self.gamer_engine.tweaks_by_category()
        cat_labels = {
            Category.CPU: "CPU",
            Category.GPU: "GPU",
            Category.SYSTEM: "Sistema",
            Category.NETWORK: "Rede",
        }
        for cat, tweaks in grouped.items():
            if not tweaks:
                continue
            header = QLabel(cat_labels[cat])
            header.setStyleSheet(
                f"color:{self.primary}; font-family:'Consolas'; font-weight:bold; font-size:12px;"
            )
            inner_lyt.addWidget(header)
            for tw in tweaks:
                row = self._build_advanced_row(tw, tw.id in enabled)
                inner_lyt.addWidget(row)
            inner_lyt.addSpacing(6)

        inner_lyt.addStretch(1)
        scroll.setWidget(inner)
        self.content_lyt.addWidget(scroll, stretch=1)

        btn_row = QHBoxLayout()
        back = QPushButton("← Voltar")
        back.setFixedWidth(120)
        back.setStyleSheet(
            "background:transparent; color:#888; border:1px solid #444;"
            "border-radius:6px; padding:8px; font-family:'Segoe UI';"
        )
        back.clicked.connect(self.show_gamer)
        save = QPushButton("Salvar preferências")
        save.setFixedWidth(200)
        save.setStyleSheet(
            f"background:{self.primary}; color:#030407; border:none; border-radius:6px;"
            "padding:8px; font-family:'Segoe UI'; font-weight:bold;"
        )
        save.clicked.connect(self._save_advanced_prefs)
        btn_row.addStretch(1)
        btn_row.addWidget(back)
        btn_row.addSpacing(10)
        btn_row.addWidget(save)
        btn_row.addStretch(1)
        self.content_lyt.addLayout(btn_row)

        self.add_status_bar("> Ajustes não aplicam imediatamente — salvar e ativar o Modo Gamer.")

    def _build_advanced_row(self, tweak, checked):
        row = QFrame()
        row.setStyleSheet(
            "QFrame{background:#0a0d14; border:1px solid #1a1f2b; border-radius:6px;}"
        )
        lyt = QVBoxLayout(row)
        lyt.setContentsMargins(10, 8, 10, 8)
        lyt.setSpacing(2)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        cb = QCheckBox(tweak.label)
        cb.setStyleSheet(
            "QCheckBox{color:white; font-family:'Segoe UI'; font-size:12px;}"
            "QCheckBox::indicator{width:14px; height:14px;}"
        )
        if tweak.opt_in:
            cb.setChecked(checked)
            cb.setEnabled(True)
            self._advanced_checks[tweak.id] = cb
        else:
            cb.setChecked(True)
            cb.setEnabled(False)
            cb.setToolTip("Tweak essencial — sempre ativo no one-click")
        top.addWidget(cb)
        top.addStretch(1)

        tag_parts = [tweak.risk.value.upper()]
        if tweak.requires_reboot:
            tag_parts.append("REBOOT")
        if tweak.opt_in:
            tag_parts.append("OPT-IN")
        tag = QLabel(" · ".join(tag_parts))
        color = {"low": "#4caf50", "medium": "#ffb300", "high": "#ff4b4b"}.get(tweak.risk.value, "#888")
        tag.setStyleSheet(f"color:{color}; font-family:'Consolas'; font-size:10px;")
        top.addWidget(tag)
        lyt.addLayout(top)

        if tweak.description:
            desc = QLabel(tweak.description)
            desc.setWordWrap(True)
            desc.setStyleSheet("color:#888; font-family:'Segoe UI'; font-size:10px;")
            lyt.addWidget(desc)

        if tweak.warning:
            warn = QLabel("⚠ " + tweak.warning)
            warn.setWordWrap(True)
            warn.setStyleSheet("color:#ff8a4b; font-family:'Segoe UI'; font-size:10px;")
            lyt.addWidget(warn)

        return row

    def _save_advanced_prefs(self):
        selected = {tid for tid, cb in self._advanced_checks.items() if cb.isChecked()}
        save_enabled_optins(selected)
        self.status_cache = f"> Preferências salvas ({len(selected)} opt-in ativos)."
        self.show_gamer()

    def add_danger_btn(self, text, func):
        b = QPushButton(text); b.setFixedWidth(400)
        b.setStyleSheet(f"""
            background-color: {self.danger}; color: white; font-weight: bold;
            border-radius: 8px; padding: 12px; border: none; font-size: 14px;
        """)
        b.clicked.connect(func)
        self.content_lyt.addWidget(b, alignment=Qt.AlignCenter)
        self.add_neon(b, self.danger)

    def run_gamer_activate(self):
        self._run_gamer_task("activate")

    def run_gamer_deactivate(self):
        self._run_gamer_task("deactivate")

    def _run_gamer_task(self, action):
        if self._gamer_worker is not None:
            return
        self.status_lbl.setText("> Aplicando Modo Gamer... aguarde." if action == "activate" else "> Desativando Modo Gamer...")
        self.status_lbl.setStyleSheet(f"color: {self.primary}; font-family: 'Consolas'; font-weight: bold;")
        QApplication.processEvents()

        optins = load_enabled_optins() if action == "activate" else set()
        self._gamer_worker = GamerWorker(self.gamer_engine, action, enabled_optins=optins)
        self._gamer_worker.finished.connect(self._on_gamer_done)
        self._gamer_worker.start()

    def _on_gamer_done(self, report, action):
        self._gamer_worker = None
        verb = "aplicado" if action == "activate" else "desativado"
        msg = (
            f"> Modo Gamer {verb}.\n"
            f"> Aplicados: {len(report.applied)} | Pulados: {len(report.skipped)} | Falhas: {len(report.failed)}"
        )
        self.status_cache = msg
        self.show_gamer()
        if action == "activate" and report.reboot_required:
            self.show_reboot_modal(report)

    def show_reboot_modal(self, report):
        reboot_tweaks = [r.tweak_id for r in report.applied
                         if self.gamer_engine._tweaks.get(r.tweak_id) and self.gamer_engine._tweaks[r.tweak_id].requires_reboot]
        m = QMessageBox(self)
        m.setWindowTitle("Reinicialização recomendada")
        m.setText("Alguns tweaks exigem reboot para entrar em efeito.")
        m.setInformativeText(
            "Para ter ganho completo, reinicie o PC quando for conveniente.\n"
            "Os tweaks já estão salvos e sobrevivem ao reboot.\n\n"
            f"Tweaks afetados:\n• " + "\n• ".join(reboot_tweaks)
        )
        m.setStandardButtons(QMessageBox.Ok)
        m.setStyleSheet(
            "QLabel{color:white; font-family:'Segoe UI';} "
            "QMessageBox{background:#030407; border:1px solid #0eb3ff;} "
            "QPushButton{color:white; border:1px solid #0eb3ff; padding:5px; min-width:80px;}"
        )
        m.exec()
    def add_title(self, text, color=None): t = QLabel(text); t.setFont(QFont("Segoe UI", 24, QFont.Bold)); t.setStyleSheet(f"color: {color};") if color else None; self.content_lyt.addWidget(t, alignment=Qt.AlignCenter); self.content_lyt.addSpacing(10)
    def add_status_bar(self, msg): self.content_lyt.addSpacing(25); self.status_lbl = QLabel(msg); self.status_lbl.setStyleSheet("color: #444; font-family: 'Consolas';"); self.content_lyt.addWidget(self.status_lbl, alignment=Qt.AlignCenter)
    def add_action_btn(self, text, func): b = QPushButton(text); b.setObjectName("ActionBtn"); b.setFixedWidth(400); b.clicked.connect(func); self.content_lyt.addWidget(b, alignment=Qt.AlignCenter); self.add_neon(b, self.primary)
    def paint_grid(self, event):
        p = QPainter(self.content_container); p.setPen(QPen(QColor(14, 179, 255, 12)))
        for x in range(0, self.content_container.width(), 40): p.drawLine(x, 0, x, self.content_container.height())
        for y in range(0, self.content_container.height(), 40): p.drawLine(0, y, self.content_container.width(), y)
    def add_neon(self, w, c): g = QGraphicsDropShadowEffect(); g.setBlurRadius(20); g.setColor(QColor(c)); g.setOffset(0); w.setGraphicsEffect(g)
    def create_menu_btn(self, t, f): b = QPushButton(t); b.setObjectName("MenuBtn"); b.setFixedSize(190, 40); b.clicked.connect(f); return b
    def clear_screen(self):
        while self.content_lyt.count():
            i = self.content_lyt.takeAt(0)
            if i.widget(): i.widget().deleteLater()
            elif i.layout():
                while i.layout().count():
                    c = i.layout().takeAt(0); c.widget().deleteLater() if c.widget() else None
    def finalizar_app(self): self.clear_screen(); l = QLabel("TECNOAPP ENCERRADO"); l.setFont(QFont("Segoe UI", 18, QFont.Bold)); self.add_neon(l, "#ff4b4b"); self.content_lyt.addWidget(l, alignment=Qt.AlignCenter); QTimer.singleShot(1000, self.close)

if __name__ == "__main__":
    app = QApplication(sys.argv); window = TecnoApp(); window.show(); sys.exit(app.exec())
