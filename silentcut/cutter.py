import subprocess
from pathlib import Path
import math
from silentcut.models import Segment


def cut_and_concat(
    input_path: str,
    output_path: str,
    speech_segments: list[Segment],
    fluid: bool = False,
    dry_run: bool = False
) -> None:
    """
    Slices and concatenates speech segments from the input video.
    Uses FFmpeg concat demuxer for lossless zero-reencode processing.
    """
    if not speech_segments:
        return

    if dry_run:
        from silentcut.utils import console
        console.print(
            f"[dim]Dry run: Would cut {len(speech_segments)} segments...[/dim]")
        return

    try:
        # Build the filter complex string
        v_segments = []
        a_segments = []

        for i, seg in enumerate(speech_segments):
            # Speed adjustments
            v_speed = 1.0 / seg.speed_factor

            # atempo filter has a limit of [0.5, 2.0]
            # We chain multiple atempo filters if factor > 2.0
            a_speed_filters = []
            temp_factor = seg.speed_factor
            while temp_factor > 2.0:
                a_speed_filters.append("atempo=2.0")
                temp_factor /= 2.0
            if temp_factor != 1.0:
                a_speed_filters.append(f"atempo={temp_factor:.2f}")

            a_filter_str = ",".join(a_speed_filters) if a_speed_filters else ""
            if a_filter_str:
                a_filter_str = "," + a_filter_str

            # Video filters
            v_filters = [
                f"trim=start={seg.start}:end={seg.end}", f"setpts={v_speed:.4f}*PTS-STARTPTS"]
            if fluid and seg.speed_factor > 1.05:
                # Add motion blur via frame blending
                # tmix merges 'frames' consecutive frames. 3 is a good balance.
                v_filters.append("tmix=frames=3:weights='1 1 1'")

            v_filter_str = ",".join(v_filters)

            # Video segment
            v_segments.append(
                f"[0:v]{v_filter_str}[v{i}];")

            # Audio segment
            a_segments.append(
                f"[0:a]atrim=start={seg.start}:end={seg.end},asetpts=PTS-STARTPTS{a_filter_str}[a{i}];")

        concat_inputs = "".join(
            [f"[v{i}][a{i}]" for i in range(len(speech_segments))])
        concat_filter = f"{concat_inputs}concat=n={len(speech_segments)}:v=1:a=1[outv][outa]"

        filter_complex = "".join(v_segments) + \
            "".join(a_segments) + concat_filter

        # Run FFmpeg with filter_complex
        # We use ultrafast preset to keep it as fast as possible.
        # CRF 20 provides high quality (better than default 23).
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i", input_path,
                "-filter_complex", filter_complex,
                "-map", "[outv]",
                "-map", "[outa]",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "20",
                "-c:a", "aac",
                "-b:a", "192k",
                output_path
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=True
        )
    except subprocess.CalledProcessError as e:
        from silentcut.utils import handle_error
        handle_error("Failed during video cutting and concatenation phase", e)
