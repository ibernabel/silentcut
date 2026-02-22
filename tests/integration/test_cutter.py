import os
from pathlib import Path
from silentcut.cutter import cut_and_concat
from silentcut.models import Segment


def test_cut_and_concat(video_with_silence: Path, tmp_path: Path):
    output = tmp_path / "out.mp4"

    # fixture is 2s speech, 2s silence, 2s speech
    # we simulate passing the speech segments
    speech_segments = [
        Segment(start=0.0, end=2.0),
        Segment(start=4.0, end=6.0)
    ]

    cut_and_concat(str(video_with_silence), str(output), speech_segments)

    assert output.exists()
    assert os.path.getsize(output) > 0


def test_dry_run_no_file_written(video_with_silence: Path, tmp_path: Path):
    output = tmp_path / "out2.mp4"
    speech_segments = [Segment(start=0.0, end=2.0)]

    cut_and_concat(str(video_with_silence), str(
        output), speech_segments, dry_run=True)

    assert not output.exists()
