import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTES = os.path.dirname(os.path.abspath(__file__))

for caminho in (RAIZ, TESTES):
    if caminho not in sys.path:
        sys.path.insert(0, caminho)

try:
    import notohiis_core
except ModuleNotFoundError as erro:
    sys.stderr.write(f"[CORE] extensão nativa indisponível: {erro}\n")
else:
    notohiis_core.set_project_root(RAIZ)
