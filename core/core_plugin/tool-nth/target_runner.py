import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tool_nth

caminho_alvo = sys.argv[1]
porta = int(sys.argv[2])
argumentos = sys.argv[3:]

codigo = tool_nth.iniciar(
    caminho_alvo,
    argumentos,
    porta,
    os.path.dirname(os.path.abspath(__file__)),
)
sys.exit(codigo)
