from textual.widgets import Footer
from notohiis_core import AppContext

class StatusBar(Footer):
    """Footer do terminal para atalhos e status."""
    def on_mount(self):
        AppContext().set_status_bar(self)

    def update_status(self, line: int, column: int, file_path: str = "Novo Arquivo"):
        # O Footer do Textual exibe os bindings.
        pass