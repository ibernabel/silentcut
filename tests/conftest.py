import subprocess
import pytest


@pytest.fixture(scope="session")
def video_with_silence(tmp_path_factory):
    """2s speech + 2s silence + 2s speech at -40dB threshold."""
    out = tmp_path_factory.mktemp("fixtures") / "test.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "sine=frequency=440:duration=2",
        "-f", "lavfi",
        "-i", "anullsrc=duration=2",
        "-f", "lavfi",
        "-i", "sine=frequency=440:duration=2",
        "-filter_complex", "[0][1][2]concat=n=3:v=0:a=1",
        str(out)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out
