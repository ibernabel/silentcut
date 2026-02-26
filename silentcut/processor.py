import ffmpeg  # type: ignore
from silentcut.models import Segment, SilenceConfig


def get_video_duration(input_path: str) -> float:
    """Extract total duration of the video in seconds."""
    try:
        probe = ffmpeg.probe(input_path)
        # Attempt to get precise duration from format
        duration = float(probe['format']['duration'])
        return duration
    except (ffmpeg.Error, KeyError, ValueError) as e:
        from silentcut.utils import handle_error
        handle_error(f"Cannot probe duration for {input_path}", e)
        return 0.0


def calculate_speech_segments(
    silent_segments: list[Segment],
    total_duration: float,
    config: SilenceConfig
) -> list[Segment]:
    """
    Invert silent segments to obtain the speech parts.
    Applies padding and ensures boundaries are kept.
    """
    speech_segments: list[Segment] = []
    current_time = 0.0

    for silence in silent_segments:
        # Determine the safe bounds for the speech chunk preceding this silence
        speech_start = max(0.0, current_time - config.padding)
        speech_end = min(total_duration, silence.start + config.padding)

        if speech_start < speech_end:
            speech_segments.append(Segment(start=speech_start, end=speech_end))

        current_time = silence.end

    # Handle the final chunk after the last silence
    final_start = max(0.0, current_time - config.padding)
    final_end = total_duration

    if final_start < final_end:
        # Check if the final chunk is practically empty
        if final_end - final_start > 0.05:
            speech_segments.append(Segment(start=final_start, end=final_end))

    # Remove overlapping overlaps if large padding is causing it
    # We consolidate overlapping segments
    consolidated: list[Segment] = []
    for s in speech_segments:
        if not consolidated:
            consolidated.append(s)
        else:
            prev = consolidated[-1]
            if s.start <= prev.end:
                consolidated[-1] = Segment(start=prev.start,
                                           end=max(prev.end, s.end))
            else:
                consolidated.append(s)

    return consolidated


def build_timeline(
    silent_segments: list[Segment],
    total_duration: float,
    config: SilenceConfig
) -> list[Segment]:
    """
    Constructs the sequence of segments for the output video.
    If config.accelerate is set, includes silence segments with a speed factor.
    Otherwise, only includes speech segments (removing silence).
    """
    speech_segments = calculate_speech_segments(
        silent_segments, total_duration, config)

    if not config.accelerate:
        return speech_segments

    # Interleave speech and accelerated silence
    timeline: list[Segment] = []
    current_time = 0.0

    # Ensure speech segments are sorted (calculate_speech_segments already returns them sorted)
    for speech in speech_segments:
        # Gap before speech (silence)
        if speech.start > current_time + 0.01:
            timeline.append(Segment(
                start=current_time,
                end=speech.start,
                speed_factor=config.accelerate
            ))

        # The speech itself
        timeline.append(speech)
        current_time = speech.end

    # Handle final gap
    if total_duration > current_time + 0.01:
        timeline.append(Segment(
            start=current_time,
            end=total_duration,
            speed_factor=config.accelerate
        ))

    return timeline
