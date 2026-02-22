import os
from pathlib import Path
from typer.testing import CliRunner
from silentcut.main import app

runner = CliRunner()


def test_remove_command_success(video_with_silence: Path, tmp_path: Path):
    output = tmp_path / "out_e2e.mp4"
    result = runner.invoke(
        app, [str(video_with_silence), "-o", str(output), "-t", "-30"])

    assert result.exit_code == 0
    assert output.exists()
    assert os.path.getsize(output) > 0


def test_dry_run_success(video_with_silence: Path, tmp_path: Path):
    output = tmp_path / "out_dry.mp4"
    result = runner.invoke(
        app, [str(video_with_silence), "-o", str(output), "--dry-run"])

    assert result.exit_code == 0
    assert not output.exists()
    assert "Dry Run Complete" in result.output


def test_invalid_input():
    result = runner.invoke(app, ["nonexistent_file_39841.mp4"])
    # Typer throws a validation error for non-existent files
    assert result.exit_code != 0
