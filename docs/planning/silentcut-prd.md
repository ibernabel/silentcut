# SilentCut — Video Silence Remover CLI
### Product Requirements Document · v1.2 · 2026

**Author:** Idequel Bernabel
**Stack:** Python · ffmpeg-python · Typer · Rich · Pydantic
**Principles:** SOLID · KISS · DRY
**Status:** Draft

---

## Table of Contents

1. [Overview](#1-overview)
2. [Goals](#2-goals)
3. [Non-Goals](#3-non-goals)
4. [Technology Stack](#4-technology-stack)
5. [Architecture & Project Structure](#5-architecture--project-structure)
6. [CLI Design](#6-cli-design-typer--rich)
7. [Core Processing Flow](#7-core-processing-flow)
8. [Data Models & Pydantic](#8-data-models--pydantic)
9. [Static Typing](#9-static-typing)
10. [Error Handling](#10-error-handling)
11. [Testing](#11-testing)
12. [Acceptance Criteria](#12-acceptance-criteria)
13. [Out of Scope](#13-out-of-scope-for-v10)
14. [Dependencies](#14-dependencies)

---

## 1. Overview

SilentCut is a command-line tool that automatically detects and removes silent segments from `.mp4` video files using FFmpeg. It targets content creators, educators, and developers who need a fast, scriptable solution without a GUI dependency.

---

## 2. Goals

- Remove silence from `.mp4` files with a single command.
- Expose tunable parameters (threshold, min duration, padding) via CLI flags.
- Provide clear, real-time progress feedback using Rich.
- Keep codebase small, readable, and extensible (SOLID + KISS + DRY).
- Zero external GUI dependencies — runs headless on any OS with Python 3.10+.

---

## 3. Non-Goals

- No GUI or web interface.
- No support for formats other than `.mp4` in v1.0.
- No automatic transcription or subtitle generation.
- No cloud upload or batch queue management.

---

## 4. Technology Stack

| Layer | Library / Tool | Purpose |
|---|---|---|
| Video processing | ffmpeg-python | Silence detection & segment cutting via FFmpeg |
| CLI framework | Typer | Commands, flags, help text, autocompletion |
| Terminal UI | Rich | Progress bars, colored output, error panels |
| Data validation | Pydantic v2 | Model validation, type coercion, settings management |
| Static typing | mypy | Type checking enforced across the entire codebase |
| Runtime | Python 3.10+ | Main language |
| System dep. | FFmpeg binary | Underlying AV engine (must be in PATH) |

---

## 5. Architecture & Project Structure

The project follows a single-responsibility layout where each module owns one concern.

```
silentcut/
├── main.py            # Typer app entry point (CLI layer only)
├── processor.py       # Core logic: detect & cut silence
├── detector.py        # FFmpeg silencedetect wrapper
├── cutter.py          # FFmpeg segment concat wrapper
├── models.py          # Pydantic models: SilenceConfig, Segment
├── console.py         # Rich console singleton
└── utils.py           # Pure helpers (time formatting, etc.)
```

### 5.1 SOLID Mapping

| Principle | Rule | How it applies |
|---|---|---|
| **S** | Single Responsibility | `detector.py` only detects; `cutter.py` only cuts; `main.py` only parses CLI. |
| **O** | Open / Closed | New formats or strategies extend `processor.py` without modifying it. |
| **L** | Liskov Substitution | Any detector implements a common `BaseDetector` protocol. |
| **I** | Interface Segregation | CLI layer never imports FFmpeg directly; uses processor interface. |
| **D** | Dependency Inversion | Processor depends on abstractions, not concrete FFmpeg calls. |

---

## 6. CLI Design (Typer + Rich)

### 6.1 Main Command

```
silentcut remove INPUT [OPTIONS]
```

| Flag | Type | Default | Description |
|---|---|---|---|
| `--output / -o` | Path | `input_no_silence.mp4` | Output file path |
| `--threshold / -t` | float | `-40.0` | Silence threshold in dB |
| `--min-duration / -d` | float | `0.5` | Min silence duration to cut (seconds) |
| `--padding / -p` | float | `0.1` | Padding kept around speech (seconds) |
| `--verbose / -v` | bool | `False` | Show per-segment debug info |
| `--dry-run` | bool | `False` | Detect only, do not write output |

### 6.2 Rich UI Behavior

- **Startup panel:** shows resolved parameters in a Rich Table.
- **Progress bar:** tracks detection phase and cutting phase independently.
- **Summary panel:** displays total removed time, output size, and output path on success.
- **Error panel:** prints a red panel with the FFmpeg stderr excerpt on failure.

---

## 7. Core Processing Flow

The pipeline runs in three sequential steps, each handled by a dedicated module:

| # | Step | Details |
|---|---|---|
| 1 | **Detect** | Run `ffmpeg silencedetect` filter. Parse stderr to extract `(start, end)` silent ranges. |
| 2 | **Invert** | Subtract silent ranges from total duration to get speech segments. Apply padding. |
| 3 | **Concat** | Write an FFmpeg concat list; cut and join segments with stream copy (no re-encode). |

> No re-encoding means near-lossless output and very fast processing even for large files.

---

## 8. Data Models & Pydantic

All models are defined with **Pydantic v2**, replacing plain dataclasses. This gives us automatic validation, type coercion, and clear error messages at the boundary between user input and processing logic.

```python
# models.py
from pydantic import BaseModel, Field, field_validator
from pathlib import Path

class SilenceConfig(BaseModel):
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
    start: float = Field(ge=0)
    end: float = Field(gt=0)

    @property
    def duration(self) -> float:
        return self.end - self.start

    model_config = {"frozen": True}  # immutable after creation
```

**Why Pydantic over dataclasses:**

| Concern | `@dataclass` | `pydantic.BaseModel` |
|---|---|---|
| Type coercion | No | Yes — `"0.5"` → `0.5` |
| Field validation | Manual | Declarative via `Field()` |
| Error messages | Generic | Structured, user-friendly |
| Immutability | `frozen=True` | `model_config frozen` |
| JSON serialization | Manual | `.model_dump()` built-in |

---

## 9. Static Typing

The entire codebase is typed with **Python type hints** and checked with **mypy** in strict mode. No `Any` is allowed except at FFmpeg boundary points where it must be explicitly annotated.

### 9.1 mypy Configuration

```toml
# pyproject.toml
[tool.mypy]
python_version = "3.10"
strict = true
warn_return_any = true
warn_unused_ignores = true
plugins = ["pydantic.mypy"]
```

### 9.2 Typing Rules

- All function signatures must declare parameter and return types.
- Use `list[Segment]` not `List[Segment]` (Python 3.10+ built-in generics).
- Use `X | Y` union syntax instead of `Optional[X]` or `Union[X, Y]`.
- Protocols (`typing.Protocol`) are used for `BaseDetector` and `BaseCutter` abstractions (supports SOLID/D).

### 9.3 Example

```python
# detector.py
from typing import Protocol
from silentcut.models import Segment, SilenceConfig

class BaseDetector(Protocol):
    def detect(self, input_path: str, config: SilenceConfig) -> list[Segment]: ...

def parse_silence_stderr(stderr: str) -> list[Segment]:
    segments: list[Segment] = []
    # ...
    return segments
```

### 9.4 CI Enforcement

```bash
mypy silentcut/ --strict
```

This runs as a separate step in CI before tests. A mypy error blocks the pipeline.

---

## 10. Error Handling

- FFmpeg not found in PATH → Rich error panel + exit code 1.
- Invalid input file → Typer validation error before processing starts.
- No speech segments found → Warning panel, no output written.
- FFmpeg non-zero exit → Capture stderr, display in Rich panel, clean up temp files.
- All errors bubble up through a single `handle_error()` utility (DRY).

---

## 11. Testing

### 11.1 Strategy

Testing is split into three levels following the classic pyramid: a wide base of fast unit tests, a mid layer of integration tests against real FFmpeg, and a thin top layer of end-to-end CLI tests.

```
         [E2E CLI]         ← few, slow, full pipeline
       [Integration]       ← real FFmpeg, temp files
    [Unit Tests (wide)]    ← pure logic, fully mocked
```

**Framework:** `pytest` + `pytest-mock` + `typer.testing.CliRunner`

### 11.2 Unit Tests

Target: pure logic with no I/O. FFmpeg subprocess calls are fully mocked.

| Module | What to test |
|---|---|
| `models.py` | `Segment.duration` calculation; `SilenceConfig` defaults. |
| `detector.py` | Correct parsing of FFmpeg stderr output into `Segment` list. Edge cases: no silence, back-to-back silences, silence at start/end. |
| `cutter.py` | Correct generation of concat list content from a `Segment` list. |
| `processor.py` | Inversion logic (silence → speech segments); padding applied correctly; empty result when no speech found. |
| `utils.py` | Time formatting helpers; path resolution. |

**Example:**

```python
# tests/unit/test_detector.py
def test_parse_silence_ranges():
    stderr = (
        "silencedetect: silence_start: 1.50\n"
        "silencedetect: silence_end: 3.20 | silence_duration: 1.70\n"
    )
    segments = parse_silence_stderr(stderr)
    assert segments == [Segment(start=1.50, end=3.20)]

def test_no_silence_returns_empty():
    assert parse_silence_stderr("") == []
```

### 11.3 Integration Tests

Target: real FFmpeg subprocess calls using small synthetic test fixtures.

**Fixtures:** generate minimal `.mp4` files with known silent/speech patterns using FFmpeg itself in `conftest.py`.

```python
# tests/conftest.py
@pytest.fixture(scope="session")
def video_with_silence(tmp_path_factory):
    """2s speech + 2s silence + 2s speech at -40dB threshold."""
    out = tmp_path_factory.mktemp("fixtures") / "test.mp4"
    subprocess.run([
        "ffmpeg", "-f", "lavfi",
        "-i", "sine=frequency=440:duration=2",
        "-f", "lavfi",
        "-i", "anullsrc=duration=2",
        "-f", "lavfi",
        "-i", "sine=frequency=440:duration=2",
        "-filter_complex", "[0][1][2]concat=n=3:v=0:a=1",
        str(out)
    ], check=True)
    return out
```

| Test | Expected outcome |
|---|---|
| `test_detector_finds_silence` | Detects the 2s silent segment within ±0.1s tolerance. |
| `test_cutter_produces_output` | Output file exists and is a valid `.mp4`. |
| `test_output_shorter_than_input` | Output duration < input duration. |
| `test_padding_respected` | With `padding=0.3`, output is ≈0.6s longer than zero-padding result. |
| `test_dry_run_no_file_written` | `--dry-run` flag produces no output file. |

### 11.4 End-to-End CLI Tests

Target: full pipeline via `typer.testing.CliRunner` — no mocks.

```python
# tests/e2e/test_cli.py
from typer.testing import CliRunner
from silentcut.main import app

runner = CliRunner()

def test_remove_command_success(video_with_silence, tmp_path):
    output = tmp_path / "out.mp4"
    result = runner.invoke(app, ["remove", str(video_with_silence), "-o", str(output)])
    assert result.exit_code == 0
    assert output.exists()

def test_invalid_input_exits_with_error():
    result = runner.invoke(app, ["remove", "nonexistent.mp4"])
    assert result.exit_code != 0
    assert "Error" in result.output

def test_dry_run_no_output(video_with_silence, tmp_path):
    output = tmp_path / "out.mp4"
    result = runner.invoke(app, ["remove", str(video_with_silence), "-o", str(output), "--dry-run"])
    assert result.exit_code == 0
    assert not output.exists()
```

### 11.5 Coverage & CI

| Item | Target |
|---|---|
| Unit test coverage | ≥ 90% on `models`, `detector`, `processor`, `utils` |
| Integration coverage | All public functions in `cutter.py` |
| CI trigger | On every push / PR to `main` |
| Coverage tool | `pytest-cov` + report in terminal |

**Run all tests:**

```bash
pytest tests/ -v --cov=silentcut --cov-report=term-missing
```

---

## 12. Acceptance Criteria

| # | Criterion | How to verify |
|---|---|---|
| AC-01 | CLI accepts `INPUT` and all listed flags without error. | Run `--help` and execute with each flag. |
| AC-02 | Output file contains no silent gaps >= `min_duration`. | Inspect waveform in Audacity. |
| AC-03 | Video quality is identical to source (stream copy). | Compare `ffprobe` codec data. |
| AC-04 | Progress bar appears and completes for both phases. | Visual inspection. |
| AC-05 | `--dry-run` produces no output file. | Check filesystem after run. |
| AC-06 | Error messages appear in Rich panel, not raw tracebacks. | Pass invalid file as `INPUT`. |
| AC-07 | All unit tests pass with ≥ 90% coverage. | Run `pytest --cov`. |
| AC-08 | `mypy silentcut/ --strict` exits with 0 errors. | Run mypy in CI. |
| AC-09 | Invalid `SilenceConfig` values raise Pydantic `ValidationError`. | Pass `threshold=5` and assert error. |

---

## 13. Out of Scope for v1.0

- Batch processing of multiple files (planned for v1.1).
- Support for `.mkv`, `.mov`, `.webm` formats.
- Auto-detection of optimal threshold per file.

---

## 14. Dependencies

| Package | Version | Install |
|---|---|---|
| ffmpeg-python | >=0.2.0 | `pip install ffmpeg-python` |
| typer | >=0.12.0 | `pip install typer` |
| rich | >=13.0.0 | `pip install rich` |
| pydantic | >=2.0.0 | `pip install pydantic` |
| mypy | >=1.10.0 | `pip install mypy` |
| pytest | >=8.0.0 | `pip install pytest` |
| pytest-mock | >=3.14.0 | `pip install pytest-mock` |
| pytest-cov | >=5.0.0 | `pip install pytest-cov` |
| ffmpeg binary | >=6.0 | `sudo apt install ffmpeg` |

---

*SilentCut PRD v1.2 · Idequel Bernabel · 2026*