import os
from pathlib import Path
import typer
from pydantic import ValidationError
from rich.table import Table

from silentcut.models import SilenceConfig
from silentcut.utils import console, format_time, ensure_ffmpeg, handle_error
from silentcut.detector import FFmpegDetector
from silentcut.processor import get_video_duration, calculate_speech_segments
from silentcut.cutter import cut_and_concat
app = typer.Typer(
    help="SilentCut — Video Silence Remover CLI",
    add_completion=False,
    no_args_is_help=True
)


@app.command()
def remove(
    input_file: Path = typer.Argument(
        ...,
        exists=True,
        dir_okay=False,
        readable=True,
        help="Input video file path to process."
    ),
    output: str = typer.Option(
        None,
        "--output", "-o",
        help="Output file path (default: input_no_silence.mp4)."
    ),
    threshold: float = typer.Option(
        -40.0,
        "--threshold", "-t",
        help="Silence threshold in dB."
    ),
    min_duration: float = typer.Option(
        0.5,
        "--min-duration", "-d",
        help="Min silence duration to cut (seconds)."
    ),
    padding: float = typer.Option(
        0.1,
        "--padding", "-p",
        help="Padding kept around speech (seconds)."
    ),
    auto_threshold: bool = typer.Option(
        False,
        "--auto", "-a",
        help="Automatically detect silence threshold based on noise floor."
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Show per-segment debug info."
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Detect only, do not write output."
    )
) -> None:
    """Remove silence from an mp4 file."""
    ensure_ffmpeg()

    # Determine default output if not provided
    if not output:
        output_path = input_file.parent / \
            f"{input_file.stem}_no_silence{input_file.suffix}"
    else:
        output_path = Path(output)

    # Auto threshold detection
    resolved_threshold = threshold
    if auto_threshold:
        with console.status("[bold magenta]Analyzing noise floor...") as status:
            d = FFmpegDetector()
            mean_vol = d.detect_mean_volume(str(input_file))
            # Heuristic: set threshold slightly above mean volume (noise floor)
            # Typically, silence is around mean_volume, speech is significantly above.
            resolved_threshold = round(mean_vol + 2.0, 1)
            if resolved_threshold >= 0:
                resolved_threshold = -1.0
            console.print(
                f"[magenta]ℹ[/magenta] Detected noise floor at {mean_vol} dB. Auto-setting threshold to [bold]{resolved_threshold} dB[/bold].")

    try:
        config = SilenceConfig(
            threshold=resolved_threshold,
            min_duration=min_duration,
            padding=padding
        )
    except ValidationError as e:
        handle_error("Invalid configuration parameters provided.", e)
        return

    # Print startup panel
    table = Table(title="SilentCut Configuration",
                  show_header=True, header_style="bold magenta")
    table.add_column("Parameter")
    table.add_column("Value")
    table.add_row("Input", str(input_file))
    table.add_row("Output", str(output_path))
    table.add_row("Threshold", f"{config.threshold} dB")
    table.add_row("Min Duration", f"{config.min_duration} s")
    table.add_row("Padding", f"{config.padding} s")
    table.add_row("Dry Run", str(dry_run))
    console.print(table)
    console.print()

    # Phase 1: Detection
    with console.status("[bold green]Detecting silence (Phase 1/2)...") as status:
        detector = FFmpegDetector()
        silent_segments = detector.detect(str(input_file), config)
        total_duration = get_video_duration(str(input_file))

        if total_duration <= 0:
            handle_error("Could not determine total video duration.")

    console.print(
        f"[green]✓[/green] Found {len(silent_segments)} silent segments in a {format_time(total_duration)} video.")

    if len(silent_segments) == 0:
        console.print(
            "[yellow]⚠ No silence detected. Try increasing the threshold (e.g. -t -25) or using --auto.[/yellow]")

    # Process inversion mathematically
    speech_segments = calculate_speech_segments(
        silent_segments, total_duration, config)

    if verbose:
        console.print("[dim]Speech segments calculated:[/dim]")
        for i, seg in enumerate(speech_segments, 1):
            console.print(
                f"[dim]  {i}: {format_time(seg.start)} -> {format_time(seg.end)} ({format_time(seg.duration)}s)[/dim]")

    if not speech_segments:
        console.print(
            "[yellow]Warning: No speech segments found. Exiting.[/yellow]")
        return

    kept_duration = sum(seg.duration for seg in speech_segments)
    removed_duration = total_duration - kept_duration

    # Phase 2: Cutting
    with console.status(f"[bold blue]Processing {len(speech_segments)} segments (Phase 2/2)...") as status:
        cut_and_concat(str(input_file), str(output_path),
                       speech_segments, dry_run=dry_run)

    # Summary
    if not dry_run:
        size_mb = os.path.getsize(
            output_path) / (1024 * 1024) if os.path.exists(output_path) else 0.0
        console.print(
            f"\n[bold green]Success![/bold green] Output written to [bold]{output_path}[/bold]")
        console.print(
            f"Removed {format_time(removed_duration)} of silence. Final duration: {format_time(kept_duration)}.")
        console.print(f"Output size: {size_mb:.2f} MB")
    else:
        console.print(f"\n[bold green]Dry Run Complete![/bold green]")
        console.print(
            f"Would have removed {format_time(removed_duration)} of silence. Final duration: {format_time(kept_duration)}.")


if __name__ == "__main__":
    app()
