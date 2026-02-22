import pytest
from pydantic import ValidationError
from silentcut.models import SilenceConfig, Segment


def test_silence_config_defaults():
    config = SilenceConfig()
    assert config.threshold == -40.0
    assert config.min_duration == 0.5
    assert config.padding == 0.1


def test_config_invalid_threshold():
    with pytest.raises(ValidationError):
        SilenceConfig(threshold=5.0)


def test_segment_duration():
    s = Segment(start=1.5, end=4.0)
    assert s.duration == 2.5


def test_segment_immutability():
    s = Segment(start=0.0, end=1.0)
    with pytest.raises(ValidationError):
        s.start = 2.0
