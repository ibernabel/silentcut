import subprocess
from pathlib import Path
from silentcut.models import Segment


def cut_and_concat(
    input_path: str,
    output_path: str,
    speech_segments: list[Segment],
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
        # We use trim/atrim for each segment and then concat them.
        # This requires re-encoding but guarantees perfect A/V sync.

        v_segments = []
        a_segments = []

        for i, seg in enumerate(speech_segments):
            # Video segment
            v_segments.append(
                f"[0:v]trim=start={seg.start}:end={seg.end},setpts=PTS-STARTPTS[v{i}];")
            # Audio segment
            a_segments.append(
                f"[0:a]atrim=start={seg.start}:end={seg.end},asetpts=PTS-STARTPTS[a{i}];")

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
