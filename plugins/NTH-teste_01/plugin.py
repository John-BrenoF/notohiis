class BlocoDeExemplo:
    def __init__(self, ctx):
        self.ctx = ctx


def setup(ctx):
    print("[BLOCO] NTH-teste_01 (Python) carregado")
    ctx.external_plugins.append(BlocoDeExemplo(ctx))
