"""
Benchmark de desempenho.

Mede CPU, memoria, disco e GPU usando so o que o Windows e o Python ja
oferecem — sem binario externo. A alternativa seria o PresentMon (~2 MB)
para ler o FPS de jogos, mas ele usa ETW do kernel, a mesma tecnica de
cheats e overlays, o que aumentaria a chance de falso-positivo de
antivirus num instalador que ja nao e assinado.

O valor aqui nao esta no numero absoluto — que varia com o que a maquina
esta fazendo — e sim em comparar antes e depois das otimizacoes.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import time

import psutil
from PySide6.QtCore import QThread, Signal

_NO_WINDOW = subprocess.CREATE_NO_WINDOW

# Referencias para converter tempo em pontuacao. Sao arbitrarias, mas
# fixas: o que importa e a comparacao entre execucoes na mesma maquina.
# Calibradas contra medicoes reais para que as quatro notas fiquem na
# mesma escala — sem isso a CPU dava 15.000 e a memoria 200, numeros que
# nao se comparam entre si nem fazem sentido somados.
_REF_CPU_SINGLE_S = 0.08   # segundos
_REF_CPU_MULTI_S = 0.23    # segundos
_REF_DISCO_MBS = 600       # MB/s (media de escrita e leitura em SSD comum)
_REF_MEM_GBS = 1.7         # GB/s


def _pontos(valor: float, referencia: float, inverso: bool = False) -> int:
    """Converte uma medida em pontuacao, com 1000 = referencia."""
    if valor <= 0:
        return 0
    razao = (referencia / valor) if inverso else (valor / referencia)
    return max(0, int(razao * 1000))


def teste_cpu_single() -> tuple[float, int]:
    """
    Carga de inteiros e ponto flutuante em uma thread.

    Nao usa bibliotecas de calculo: o objetivo e medir a CPU, e uma
    biblioteca otimizada mediria a biblioteca.
    """
    t0 = time.perf_counter()
    x = 0
    for i in range(1, 900_000):
        x += (i * i) % 7
        if i % 3 == 0:
            x ^= i
    dur = time.perf_counter() - t0
    return dur, _pontos(dur, _REF_CPU_SINGLE_S, inverso=True)


def teste_cpu_multi() -> tuple[float, int]:
    """
    Mesma carga distribuida entre os nucleos.

    Usa threads, nao processos: em executavel empacotado o multiprocessing
    reabre o app inteiro. Com o GIL o ganho e menor, mas o teste continua
    comparativo entre execucoes.
    """
    import concurrent.futures as cf

    nucleos = psutil.cpu_count(logical=True) or 4
    def carga(_):
        x = 0
        for i in range(1, 300_000):
            x += (i * i) % 7
        return x

    t0 = time.perf_counter()
    with cf.ThreadPoolExecutor(max_workers=nucleos) as ex:
        list(ex.map(carga, range(nucleos)))
    dur = time.perf_counter() - t0
    return dur, _pontos(dur, _REF_CPU_MULTI_S, inverso=True)


def teste_memoria() -> tuple[float, int]:
    """Velocidade de copia em memoria, em GB/s."""
    tam = 48 * 1024 * 1024   # 48 MB: grande o bastante para sair do cache
    origem = bytearray(tam)
    t0 = time.perf_counter()
    for _ in range(4):
        destino = bytes(origem)
        del destino
    dur = time.perf_counter() - t0
    gbs = (tam * 4 / (1024 ** 3)) / dur if dur > 0 else 0
    return gbs, _pontos(gbs, _REF_MEM_GBS)


def teste_disco() -> tuple[float, float, int]:
    """
    Escrita e leitura sequencial em MB/s.

    Grava no temp do sistema e apaga em seguida — nao deixa residuo.
    """
    tam = 64 * 1024 * 1024
    bloco = os.urandom(1024 * 1024)
    caminho = os.path.join(tempfile.gettempdir(), "tecnoapp_bench.tmp")
    escrita = leitura = 0.0

    try:
        t0 = time.perf_counter()
        with open(caminho, "wb") as f:
            for _ in range(tam // len(bloco)):
                f.write(bloco)
            f.flush()
            os.fsync(f.fileno())   # sem isso mediria o cache, nao o disco
        dur = time.perf_counter() - t0
        escrita = (tam / (1024 ** 2)) / dur if dur > 0 else 0

        t0 = time.perf_counter()
        with open(caminho, "rb") as f:
            while f.read(1024 * 1024):
                pass
        dur = time.perf_counter() - t0
        leitura = (tam / (1024 ** 2)) / dur if dur > 0 else 0
    except Exception:
        pass
    finally:
        try:
            if os.path.exists(caminho):
                os.remove(caminho)
        except Exception:
            pass

    media = (escrita + leitura) / 2
    return escrita, leitura, _pontos(media, _REF_DISCO_MBS)


def uso_gpu() -> float:
    """
    Uso da GPU em 3D, pelos contadores que o Windows ja expoe.

    Nao e um teste de desempenho — e o estado atual, util para o usuario
    saber se ha algo disputando a GPU durante o benchmark.
    """
    contador = r"'\GPU Engine(*engtype_3D)\Utilization Percentage'"
    cmd = ("(Get-Counter " + contador + " -EA SilentlyContinue).CounterSamples | "
           "Measure-Object CookedValue -Sum | % { [math]::Round($_.Sum,1) }")
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
            capture_output=True, timeout=25, creationflags=_NO_WINDOW,
        )
        txt = (r.stdout or b"").decode("cp850", "replace").strip().replace(",", ".")
        return round(float(txt), 1) if txt else 0.0
    except Exception:
        return 0.0


class BenchmarkWorker(QThread):
    """
    Roda os testes em sequencia, reportando cada etapa.

    Em thread propria porque as cargas travariam a interface por segundos.
    """

    etapa = Signal(str, int)          # (descricao, progresso 0-100)
    concluido = Signal("QVariant")
    falhou = Signal(str)

    def __init__(self, completo: bool = True, parent=None):
        super().__init__(parent)
        self._completo = completo

    def run(self):
        try:
            r = {}

            self.etapa.emit("Processador — núcleo único", 10)
            dur, pts = teste_cpu_single()
            r["cpu_single"] = {"tempo": round(dur, 2), "pontos": pts}

            self.etapa.emit("Processador — todos os núcleos", 30)
            dur, pts = teste_cpu_multi()
            r["cpu_multi"] = {"tempo": round(dur, 2), "pontos": pts}

            if self._completo:
                self.etapa.emit("Memória", 50)
                gbs, pts = teste_memoria()
                r["memoria"] = {"gbs": round(gbs, 1), "pontos": pts}

                self.etapa.emit("Disco", 70)
                esc, lei, pts = teste_disco()
                r["disco"] = {
                    "escrita_mbs": round(esc),
                    "leitura_mbs": round(lei),
                    "pontos": pts,
                }

                self.etapa.emit("Placa de vídeo", 90)
                r["gpu"] = {"uso_pct": uso_gpu()}

            # Nota geral: media das pontuacoes obtidas
            notas = [v["pontos"] for v in r.values() if isinstance(v, dict) and "pontos" in v]
            r["total"] = int(sum(notas) / len(notas)) if notas else 0

            # Contexto: o resultado depende do que a maquina esta fazendo
            try:
                r["contexto"] = {
                    "cpu_pct": round(psutil.cpu_percent(interval=None)),
                    "ram_pct": round(psutil.virtual_memory().percent),
                    "processos": len(psutil.pids()),
                }
            except Exception:
                r["contexto"] = {}

            self.etapa.emit("Concluído", 100)
            self.concluido.emit(r)
        except Exception as e:
            self.falhou.emit(f"{type(e).__name__}")
