import importlib.util
import os

CAMINHO_PLUGIN = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "core",
    "core_plugin",
    "tool-nth",
    "plugin.py",
)

def setup(ctx):
    if not os.path.isfile(CAMINHO_PLUGIN):
        print("[TOOL-NTH] pasta do depurador ausente — recurso ignorado.")
        return None
    try:
        especimo = importlib.util.spec_from_file_location("tool_nth_plugin", CAMINHO_PLUGIN)
        modulo = importlib.util.module_from_spec(especimo)
        especimo.loader.exec_module(modulo)
        return modulo.setup(ctx)
    except ModuleNotFoundError as erro:
        print(
            "[TOOL-NTH] extensão não compilada — rode: "
            f"bash core/core_plugin/tool-nth/build.sh ({erro})"
        )
        return None
