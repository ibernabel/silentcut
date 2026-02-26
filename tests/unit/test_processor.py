from silentcut.processor import calculate_speech_segments, build_timeline
from silentcut.models import Segment, SilenceConfig


def test_calculate_speech_segments_basic():
    silent_segments = [Segment(start=2.0, end=4.0)]
    total_duration = 10.0
    config = SilenceConfig(padding=0.1)

    # 0.0 -> 2.1 (due to padding)
    # 3.9 -> 10.0
    speech = calculate_speech_segments(silent_segments, total_duration, config)

    assert len(speech) == 2
    assert speech[0].start == 0.0
    assert speech[0].end == 2.1
    assert speech[1].start == 3.9
    assert speech[1].end == 10.0


def test_calculate_speech_segments_overlapping_padding():
    # very close silences, padding makes speech sections overlap or very tiny
    silent_segments = [Segment(start=1.0, end=2.0),
                       Segment(start=2.1, end=3.0)]
    total_duration = 5.0
    config = SilenceConfig(padding=0.2)

    speech = calculate_speech_segments(silent_segments, total_duration, config)
    # expected bounds:
    # chunk1: 0 -> 1.2
    # chunk2: 1.8 -> 2.3  (from seg1 end(2.0-0.2) to seg2 start(2.1+0.2))
    # chunk3: 2.8 -> 5.0

    # Note: the processor consolidates chunks if they overlap:
    # 1.2 is < 1.8 so they don't overlap, we should have 3 segments
    assert len(speech) == 3
    import pytest
    assert speech[0].start == pytest.approx(0.0)
    assert speech[0].end == pytest.approx(1.2)
    assert speech[1].start == pytest.approx(1.8)
    assert speech[1].end == pytest.approx(2.3)
    assert speech[2].start == pytest.approx(2.8)
    assert speech[2].end == pytest.approx(5.0)


def test_build_timeline_no_accelerate():
    silent_segments = [Segment(start=2.0, end=4.0)]
    total_duration = 10.0
    config = SilenceConfig(padding=0.1, accelerate=None)

    timeline = build_timeline(silent_segments, total_duration, config)

    # Should only contain speech segments
    assert len(timeline) == 2
    assert all(s.speed_factor == 1.0 for s in timeline)


def test_build_timeline_accelerate():
    silent_segments = [Segment(start=2.0, end=4.0)]
    total_duration = 10.0
    config = SilenceConfig(padding=0.0, accelerate=2.0)

    # config.padding = 0 to simplify expected bounds
    # timeline should be:
    # 0.0 -> 2.0 (speech, 1.0)
    # 2.0 -> 4.0 (silence, 2.0)
    # 4.0 -> 10.0 (speech, 1.0)

    timeline = build_timeline(silent_segments, total_duration, config)

    assert len(timeline) == 3
    assert timeline[0].start == 0.0
    assert timeline[0].end == 2.0
    assert timeline[0].speed_factor == 1.0

    assert timeline[1].start == 2.0
    assert timeline[1].end == 4.0
    assert timeline[1].speed_factor == 2.0

    assert timeline[2].start == 4.0
    assert timeline[2].end == 10.0
    assert timeline[2].speed_factor == 1.0
