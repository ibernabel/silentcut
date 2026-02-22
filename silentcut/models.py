from pydantic import BaseModel, Field, field_validator

class SilenceConfig(BaseModel):
    """Configuration for silence detection and processing."""
    threshold: float = Field(default=-40.0, le=0, description="Silence threshold in dB")
    min_duration: float = Field(default=0.5, gt=0, description="Min silence duration in seconds")
    padding: float = Field(default=0.1, ge=0, description="Padding around speech in seconds")

    @field_validator("threshold")
    @classmethod
    def threshold_must_be_negative(cls, v: float) -> float:
        if v >= 0:
            raise ValueError("threshold must be negative (dB)")
        return v

class Segment(BaseModel):
    """Immutable representation of a video/audio segment."""
    start: float = Field(ge=0)
    end: float = Field(gt=0)

    @property
    def duration(self) -> float:
        return self.end - self.start

    model_config = {"frozen": True}
