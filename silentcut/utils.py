import sys
import subprocess
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

console = Console()


def format_time(seconds: float) -> str:
    """Format seconds into HH:MM:SS.mmm string."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:05.3f}"


def handle_error(message: str, error: Exception | None = None) -> None:
    """Print error in a Rich panel and exit."""
    content = message
    if error:
        if isinstance(error, subprocess.CalledProcessError):
            stderr = error.stderr.decode(
                'utf-8') if error.stderr else str(error)
            content += f"\n\n[dim]{stderr}[/dim]"
        else:
            content += f"\n\n[dim]{str(error)}[/dim]"

    console.print(Panel(content, title="Error", style="bold red"))
    sys.exit(1)


def ensure_ffmpeg() -> None:
    """Ensure ffmpeg is installed and available in PATH."""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        handle_error(
            "FFmpeg not found. Please install FFmpeg and ensure it's in your PATH.")
