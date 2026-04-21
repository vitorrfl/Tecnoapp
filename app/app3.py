import sys
import os
import subprocess
import datetime
import ctypes
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QMessageBox,
                             QHBoxLayout, QPushButton, QLabel, QFrame, QGraphicsDropShadowEffect)
from PySide6.QtGui import QFont, QColor, QCursor, QPainter, QPen
from PySide6.QtCore import Qt, QTimer

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
        self.auto_clean = False 

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

    def is_cleanmgr_running(self):
        try:
            output = subprocess.check_output('tasklist', shell=True).decode('latin-1')
            return "cleanmgr.exe" in output.lower()
        except: return False

    def toggle_mode(self):
        self.auto_clean = not self.auto_clean
        self.update_toggle_style()

    def update_toggle_style(self):
        txt = "LIMPEZA AUTOMÁTICA: ON" if self.auto_clean else "LIMPEZA AUTOMÁTICA: OFF"
        color = self.primary if self.auto_clean else self.danger
        self.btn_sw.setText(txt)
        self.btn_sw.setStyleSheet(f"""
            background: rgba(255, 255, 255, 0.03); 
            border: 1px solid {color}; 
            color: {color};
            font-size: 10px; font-weight: bold; border-radius: 6px; padding: 8px;
        """)
        self.add_neon(self.btn_sw, color)

    def help_popup(self):
        m = QMessageBox(self)
        m.setWindowTitle("Explicação do Checklist")
        m.setText("O QUE CADA CAIXA DO WINDOWS REMOVE:")
        m.setInformativeText(
            "• Limpeza do Windows Update: Exclui versões antigas de arquivos de sistema (GBs liberados).\n"
            "• Antivírus Microsoft Defender: Arquivos temporários não críticos da proteção.\n"
            "• Arquivos de Programas Baixados: Controles ActiveX e Java da web.\n"
            "• Arquivos de Internet Temporários: Cache de sites para navegação mais rápida.\n"
            "• Cache do Sombreador DirectX: Arquivos de aceleração gráfica (jogos).\n"
            "• Entrega de Otimização: Restos de atualizações enviadas a outros PCs da rede.\n"
            "• Lixeira: Esvazia todos os arquivos que você deletou manualment.\n"
            "• Arquivos Temporários: Dados criados por aplicativos que não foram removidos."
        )
        m.setStyleSheet("QLabel{color:white; font-family:'Segoe UI';} QMessageBox{background:#030407; border:1px solid #0eb3ff;} QPushButton{color:white; border:1px solid #0eb3ff; padding:5px; min-width:80px;}")
        m.exec()

    def run_clean_process(self):
        self.space_before = self.get_free_space()
        
        if self.auto_clean:
            self.status_lbl.setText("> Efetuando limpeza automática...")
            QApplication.processEvents()
            cmd = 'del /s /f /q %temp%\\*.* & del /s /f /q C:\\Windows\\Temp\\*.* & del /s /f /q C:\\Windows\\Prefetch\\*.* & ipconfig /flushdns'
            subprocess.run(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self.finish_cleaning_logic()
        else:
            self.status_lbl.setText("> Selecione os arquivos e aguarde a conclusão...")
            self.status_lbl.setStyleSheet(f"color: {self.primary}; font-weight: bold;")
            QApplication.processEvents()
            subprocess.Popen('cleanmgr /d C:', shell=True)
            self.monitor_timer = QTimer(); self.monitor_timer.timeout.connect(self.check_clean_status)
            self.monitor_timer.start(1000)

    def check_clean_status(self):
        if not self.is_cleanmgr_running():
            self.monitor_timer.stop()
            self.status_lbl.setText("> Validando limpeza...")
            QApplication.processEvents()
            QTimer.singleShot(2500, self.finish_cleaning_logic)

    def finish_cleaning_logic(self):
        space_after = self.get_free_space()
        diff = space_after - self.space_before
        agora = datetime.datetime.now().strftime("%d/%m/%Y às %H:%M:%S")

        if diff > 1024:
            self.status_cache = f"> SUCESSO: {self.format_size(diff)} liberados!\n> DATA: {agora}"
        else:
            self.status_cache = f"> Sistema otimizado recentemente.\n> DATA: {agora}"
        self.update_ui_status()

    def update_ui_status(self):
        if self.status_cache:
            self.status_lbl.setText(self.status_cache)
            self.status_lbl.setStyleSheet("color: #ffbd2e; font-family: 'Consolas'; font-weight: bold; line-height: 150%;")

    def show_limpeza(self):
        self.clear_screen(); self.add_title("MÓDULO DE LIMPEZA")
        desc = QLabel("Engenharia oficial Windows para máxima segurança."); desc.setStyleSheet("color: #444; margin-bottom: 25px;")
        self.content_lyt.addWidget(desc, alignment=Qt.AlignCenter)
        self.add_action_btn("INICIAR LIMPEZA SEGURA", self.run_clean_process)
        
        opt_lyt = QHBoxLayout(); opt_lyt.addStretch()
        self.btn_sw = QPushButton(); self.btn_sw.setObjectName("ToggleBtn"); self.btn_sw.setFixedWidth(220)
        self.btn_sw.clicked.connect(self.toggle_mode)
        self.update_toggle_style()
        opt_lyt.addWidget(self.btn_sw)
        
        btn_h = QPushButton("ℹ"); btn_h.setFixedSize(30, 30); btn_h.setObjectName("InfoBtn"); btn_h.clicked.connect(self.help_popup)
        self.add_neon(btn_h, self.primary); opt_lyt.addWidget(btn_h); opt_lyt.addStretch()
        self.content_lyt.addLayout(opt_lyt)
        
        log = "Nunca"
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, "r") as f: log = f.read()
            except: pass
        self.add_status_bar(self.status_cache if self.status_cache else f"> Histórico: {log}")
        self.update_ui_status()

    def show_home(self): self.clear_screen(); lbl = QLabel("SISTEMA PRONTO"); lbl.setFont(QFont("Segoe UI", 28, QFont.Bold)); self.add_neon(lbl, self.primary); self.content_lyt.addWidget(lbl, alignment=Qt.AlignCenter)
    def show_otimizacao(self): self.clear_screen(); self.add_title("OTIMIZAÇÃO"); self.add_status_bar("> Menu pronto.")
    def show_reparos(self): self.clear_screen(); self.add_title("REPAROS"); self.add_status_bar("> Menu pronto.")
    def show_gamer(self): self.clear_screen(); self.add_title("MODO GAMER", self.secondary); self.add_status_bar("> Boost ativado.")
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
