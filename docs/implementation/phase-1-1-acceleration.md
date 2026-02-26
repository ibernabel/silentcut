# Phase 1.1: Dynamic Silence Acceleration

Dynamic Silence Acceleration allows the user to speed up silent segments in a video instead of completely removing them. This creates a "fast-forward" effect that maintains context while reducing viewer fatigue.

## Technical Implementation

### Models

- **`SilenceConfig`**: Added `accelerate` (float | None).
- **`Segment`**: Added `speed_factor` (float), allowing each segment to have its own processing speed.

### Timeline construction

The `silentcut.processor.build_timeline` function was introduced to replace simple inversion. It intelligently interleaves:

1. Speech segments (speed = 1.0x)
2. Silence segments (speed = user-defined factor)

### FFmpeg Filter Chain

- **Video**: `setpts=(1/speed)*PTS-STARTPTS`
- **Audio**: `atempo=speed`
- **Chaining**: Since FFmpeg's `atempo` filter is limited to a range of [0.5, 2.0], factors greater than 2.0 (e.g., 4.0x) are automatically chained: `atempo=2.0,atempo=2.0`.

## CLI Usage

```bash
# Accelerate silence by 2x
silentcut input.mp4 --accelerate 2.0

# Using shorthand
silentcut input.mp4 --accel 3.0
```

## Verification

Unit tests cover the timeline interleaving logic in `tests/unit/test_processor.py`. Manual dry-run testing verifies that CLI arguments and duration calculations are correct.
