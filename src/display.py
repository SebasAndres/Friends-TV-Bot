from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


def print_response(name: str, emoji: str, color: str, text: str) -> None:
    """
    Print a character response panel in the terminal.

    Parameters
    ----------
    name : str
        Display name of the character.
    emoji : str
        Emoji rendered in the panel title.
    color : str
        Rich color style used for the character name in the title.
    text : str
        Message body rendered inside the panel.

    Returns
    -------
    None
        The function writes a formatted panel to the console.
    """

    panel = Panel(
        Text(text, style="white"),
        title=f" {emoji} [{color}]{name}[/{color}] ",
        title_align="left",
        border_style="dim",
        padding=(0, 1),
    )
    console.print(panel)
