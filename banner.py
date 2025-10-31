import os
from rich.console import Console
from rich.panel import Panel

console = Console()

def banner():
    console.clear()
    banner_text = """[bold white]
██╗██████╗      ██████╗██╗  ██╗ █████╗ ███╗   ██╗ ██████╗ ███████╗██████╗
██║██╔══██╗    ██╔════╝██║  ██║██╔══██╗████╗  ██║██╔════╝ ██╔════╝██╔══██╗
██║██████╔╝    ██║     ███████║███████║██╔██╗ ██║██║  ███╗█████╗  ██████╔╝
██║██╔═══╝     ██║     ██╔══██║██╔══██║██║╚██╗██║██║   ██║██╔══╝  ██╔══██╗
██║██║         ╚██████╗██║  ██║██║  ██║██║ ╚████║╚██████╔╝███████╗██║  ██║
╚═╝╚═╝          ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝
                                                                          [/bold white]

[bold cyan]           Advance IP Changer | V2.0 | Secure | Anonymous[/bold cyan]
"""
    console.print(Panel(
        banner_text,
        expand=False,
        padding=(1, 3),
        border_style="magenta",
        title="[bold yellow]ADVANCE IP CHANGER[/bold yellow]",
        subtitle="[green]Fast • Secure • Tor Enabled[/green]"
    ))

if __name__ == "__main__":
    banner()
