# -*- coding: utf-8 -*-
"""Move todas as conexoes de sinal para antes das chamadas de slot.

O bloco de polling do debloat (que chama getBloatware e agenda setTimeout)
ficava entre as conexoes; as de limpeza/reparo/otimizacao vinham depois e
nao eram efetivadas de forma confiavel.
"""
import io

P = r"C:\Projects\Tecnoapp\app\webview\app.js"
s = io.open(P, encoding="utf-8").read()

BLOCO_SINAIS = """    if (b.cleanStep && b.cleanStep.connect)               b.cleanStep.connect(onCleanStep);
    if (b.cleanCalculating && b.cleanCalculating.connect) b.cleanCalculating.connect(onCleanCalculating);
    if (b.cleanFinished && b.cleanFinished.connect)       b.cleanFinished.connect(onCleanFinished);

    if (b.repairStep && b.repairStep.connect)             b.repairStep.connect(onRepairStep);
    if (b.repairFinished && b.repairFinished.connect)     b.repairFinished.connect(onRepairFinished);
    if (b.repairStatus && b.repairStatus.connect)         b.repairStatus.connect(onRepairStatus);
    if (b.optimizeStep && b.optimizeStep.connect)         b.optimizeStep.connect(onOptimizeStep);
    if (b.optimizeFinished && b.optimizeFinished.connect) b.optimizeFinished.connect(onOptimizeFinished);

"""

# 1) remove o bloco de onde esta
if BLOCO_SINAIS not in s:
    raise SystemExit("bloco de sinais nao encontrado no formato esperado")
s = s.replace(BLOCO_SINAIS, "", 1)

# 2) reinsere logo apos a conexao de metricsUpdated, que comprovadamente funciona
ancora = """    if (b.metricsUpdated && b.metricsUpdated.connect) {
      b.metricsUpdated.connect(applySnapshot);
    }
"""
if ancora not in s:
    raise SystemExit("ancora metricsUpdated nao encontrada")
s = s.replace(ancora, ancora + "\n" + BLOCO_SINAIS, 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("app.js: conexoes de sinal movidas para junto de metricsUpdated")

# confere a ordem final
linhas = s.split("\n")
for i, l in enumerate(linhas, 1):
    if ".connect(" in l or "getBloatware(r =>" in l or "poll();" in l:
        nome = l.strip()[:70]
        print("  %4d  %s" % (i, nome))
