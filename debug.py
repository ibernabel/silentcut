from typer.testing import CliRunner
from silentcut.main import app
from pathlib import Path
from unittest.mock import patch

test_file = Path("test.mp4")
test_file.touch()

runner = CliRunner()

with patch("silentcut.main.ensure_ffmpeg"), \
     patch("silentcut.detector.FFmpegDetector.detect", return_value=[]), \
     patch("silentcut.processor.get_video_duration", return_value=10.0), \
     patch("silentcut.cutter.cut_and_concat"):
    result = runner.invoke(app, [str(test_file), "--verbose"])
    print("EXIT CODE:", result.exit_code)
    print("OUTPUT:", result.output)
    if result.exception:
        print("EXCEPTION:", result.exception)
