from silentcut.detector import FFmpegDetector
from silentcut.models import Segment


def test_parse_silence_stderr():
    stderr = (
        "silencedetect: silence_start: 1.50\n"
        "silencedetect: silence_end: 3.20 | silence_duration: 1.70\n"
        "silencedetect: silence_start: 5.0\n"
        "silencedetect: silence_end: 6.5 | silence_duration: 1.5\n"
    )
    detector = FFmpegDetector()
    segments = detector._parse_silence_stderr(stderr)

    assert len(segments) == 2
    assert segments[0] == Segment(start=1.5, end=3.2)
    assert segments[1] == Segment(start=5.0, end=6.5)


def test_no_silence_returns_empty():
    detector = FFmpegDetector()
    assert detector._parse_silence_stderr(
        "Random info without silence tags") == []
