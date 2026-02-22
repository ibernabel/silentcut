import pytest
import subprocess
from unittest.mock import patch
from typer.testing import CliRunner

from silentcut.utils import handle_error, ensure_ffmpeg
from silentcut.main import app


def test_handle_error_exit(capsys):
    with pytest.raises(SystemExit) as excinfo:
        handle_error("Test Error")
    assert excinfo.value.code == 1


def test_handle_error_with_exception():
    err = subprocess.CalledProcessError(
        1, "cmd", output=b"out", stderr=b"err output")
    with pytest.raises(SystemExit):
        handle_error("Cmd Fail", err)


def test_ensure_ffmpeg_fail(mocker):
    mocker.patch("subprocess.run",
                 side_effect=FileNotFoundError("Mocked not found"))
    with pytest.raises(SystemExit):
        ensure_ffmpeg()


def test_main_validation_error(tmp_path):
    runner = CliRunner()
    test_file = tmp_path / "valid_file.mp4"
    test_file.touch()
    result = runner.invoke(
        app, [str(test_file), "--threshold", "50"])  # invalid obj
    assert result.exit_code == 1


def test_main_verbose_mode(mocker, tmp_path):
    mocker.patch("silentcut.main.ensure_ffmpeg")
    mocker.patch("silentcut.detector.FFmpegDetector.detect", return_value=[])
    mocker.patch("silentcut.main.get_video_duration", return_value=10.0)
    mocker.patch("silentcut.main.cut_and_concat")

    runner = CliRunner()
    test_file = tmp_path / "video.mp4"
    test_file.touch()

    result = runner.invoke(app, [str(test_file), "--verbose"])
    assert result.exit_code == 0
    assert "Speech segments calculated" in result.output


def test_main_no_speech_warning(mocker, tmp_path):
    mocker.patch("silentcut.main.ensure_ffmpeg")
    from silentcut.models import Segment
    mocker.patch("silentcut.detector.FFmpegDetector.detect",
                 return_value=[Segment(start=0.0, end=10.0)])
    mocker.patch("silentcut.main.get_video_duration", return_value=10.0)

    runner = CliRunner()
    test_file = tmp_path / "video3.mp4"
    test_file.touch()

    result = runner.invoke(app, [str(test_file), "--padding", "0.0"])
    assert result.exit_code == 0
    assert "No speech segments found" in result.output


def test_main_duration_fail(mocker, tmp_path):
    mocker.patch("silentcut.main.ensure_ffmpeg")
    mocker.patch("silentcut.detector.FFmpegDetector.detect", return_value=[])
    mocker.patch("silentcut.main.get_video_duration", return_value=0.0)

    runner = CliRunner()
    test_file = tmp_path / "video2.mp4"
    test_file.touch()

    result = runner.invoke(app, [str(test_file)], catch_exceptions=False)
    assert result.exit_code == 1
