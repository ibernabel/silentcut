import os
from pathlib import Path
import typer
from pydantic import ValidationError
from rich.table import Table

from silentcut.models import SilenceConfig
from silentcut.utils import console, format_time, ensure_ffmpeg, handle_error, get_unique_path
from silentcut.detector import FFmpegDetector
from silentcut.processor import get_video_duration, build_timeline
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
    accelerate: float = typer.Option(
        None,
        "--accelerate", "--accel",
        help="Accelerate silence instead of removing it (e.g., 2.0, 3.0)."
    ),
    fluid: bool = typer.Option(
        False,
        "--fluid", "-f",
        help="Enable smooth transitions and motion blur for speed changes."
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

    # Ensure unique output path to prevent overwriting
    if not dry_run:
        output_path = get_unique_path(output_path)

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
            padding=padding,
            accelerate=accelerate,
            fluid=fluid
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
    table.add_row(
        "Accelerate", f"{config.accelerate}x" if config.accelerate else "Disabled (Remove)")
    table.add_row("Fluid Mode", "Enabled 🌊" if config.fluid else "Disabled")
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

    # Process timeline construction
    segments_to_process = build_timeline(
        silent_segments, total_duration, config)

    if verbose:
        console.print("[dim]Segments to process calculated:[/dim]")
        for i, seg in enumerate(segments_to_process, 1):
            speed_info = f" (@{seg.speed_factor}x)" if seg.speed_factor != 1.0 else ""
            console.print(
                f"[dim]  {i}: {format_time(seg.start)} -> {format_time(seg.end)} ({format_time(seg.duration)}s){speed_info}[/dim]")

    if not segments_to_process:
        console.print(
            "[yellow]Warning: No segments found to process. Exiting.[/yellow]")
        return

    # Calculate final stats
    if config.accelerate:
        final_duration = 0.0
        for seg in segments_to_process:
            final_duration += seg.duration / seg.speed_factor
        removed_duration = total_duration - final_duration
    else:
        final_duration = sum(seg.duration for seg in segments_to_process)
        removed_duration = total_duration - final_duration

    # Phase 2: Cutting
    with console.status(f"[bold blue]Processing {len(segments_to_process)} segments (Phase 2/2)...") as status:
        cut_and_concat(str(input_file), str(output_path),
                       segments_to_process, fluid=config.fluid, dry_run=dry_run)

    # Summary
    if not dry_run:
        size_mb = os.path.getsize(
            output_path) / (1024 * 1024) if os.path.exists(output_path) else 0.0
        console.print(
            f"\n[bold green]Success![/bold green] Output written to [bold]{output_path}[/bold]")

        action = "Removed" if not config.accelerate else "Saved"
        console.print(
            f"{action} {format_time(removed_duration)} by {'removing' if not config.accelerate else 'accelerating'} silence. Final duration: {format_time(final_duration)}.")
        console.print(f"Output size: {size_mb:.2f} MB")
    else:
        console.print(f"\n[bold green]Dry Run Complete![/bold green]")
        action = "Would have removed" if not config.accelerate else "Would have saved"
        console.print(
            f"{action} {format_time(removed_duration)}. Final duration: {format_time(final_duration)}.")


if __name__ == "__main__":
    app()
