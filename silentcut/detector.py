import re
import ffmpeg  # type: ignore
from typing import Protocol
from silentcut.models import Segment, SilenceConfig


class BaseDetector(Protocol):
    def detect(self, input_path: str,
               config: SilenceConfig) -> list[Segment]: ...


class FFmpegDetector:
    def detect(self, input_path: str, config: SilenceConfig) -> list[Segment]:
        """Run FFmpeg silencedetect and extract silent segments."""
        try:
            _, stderr = (
                ffmpeg
                .input(input_path)
                .filter('silencedetect', noise=f"{config.threshold}dB", d=config.min_duration)
                .output('pipe:', format='null')
                .run(capture_stdout=True, capture_stderr=True)
            )
            return self._parse_silence_stderr(stderr.decode('utf-8'))
        except ffmpeg.Error as e:
            from silentcut.utils import handle_error
            handle_error("Failed during silence detection phase", e)
            return []

    def detect_mean_volume(self, input_path: str) -> float:
        """Detect the mean volume of the audio stream in dB."""
        try:
            _, stderr = (
                ffmpeg
                .input(input_path)
                .filter('volumedetect')
                .output('pipe:', format='null')
                .run(capture_stdout=True, capture_stderr=True)
            )
            output = stderr.decode('utf-8')
            match = re.search(r'mean_volume:\s+(-?[\d\.]+)\s+dB', output)
            if match:
                return float(match.group(1))
            return -20.0  # Safe fallback if parsing fails
        except ffmpeg.Error:
            return -20.0

    def _parse_silence_stderr(self, stderr: str) -> list[Segment]:
        """Extract silence start and end times from FFmpeg stderr logging."""
        segments: list[Segment] = []

        # Matches: silencedetect: silence_start: 1.50
        start_pattern = re.compile(r'silence_start:\s+([\d\.]+)')
        # Matches: silencedetect: silence_end: 3.20 | silence_duration: 1.70
        end_pattern = re.compile(r'silence_end:\s+([\d\.]+)')

        current_start: float | None = None

        for line in stderr.splitlines():
            if 'silencedetect' in line:
                start_match = start_pattern.search(line)
                end_match = end_pattern.search(line)

                if start_match:
                    current_start = float(start_match.group(1))
                elif end_match and current_start is not None:
                    end_time = float(end_match.group(1))
                    segments.append(Segment(start=current_start, end=end_time))
                    current_start = None

        return segments
