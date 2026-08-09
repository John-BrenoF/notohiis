from core.core_plugin.terminal_plugin import TerminalPlugin

def setup(ctx):
    plugin = TerminalPlugin(ctx)
    ctx.external_plugins.append(plugin)
