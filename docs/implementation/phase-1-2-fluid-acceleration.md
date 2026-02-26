# Phase 1.2: Fluid Acceleration (InShot Style)

Fluid Acceleration solves the issue of "choppy" transitions when using dynamic silence acceleration. It mimics the behavior of high-end mobile editing apps like InShot.

## Technical Implementation

### Speed Ramping (Ease-in/out)

Instead of jumping from 1.0x to 3.0x instantly, `silentcut.processor.build_timeline` now handles fluid transitions:

- **Ramp Duration**: 0.1s.
- **Mid-Speed**: Calculated as `(1.0 + target_speed) / 2.0`.
- **Logic**: If a silence is long enough, it inserts a 0.1s mid-speed segment at the beginning and end of the silence.

### Motion Blur (Frame Blending)

Accelerated video often looks like a series of still frames because of the high shutter speed feel.

- **Filter**: `tmix=frames=3:weights='1 1 1'`.
- **Effect**: Merges 3 consecutive frames during accelerated segments, creating a natural-looking motion blur that smooths out the fast-forward effect.
- **Optimization**: Only applied to segments with `speed_factor > 1.05` to save processing time on normal speech.

## CLI Usage

```bash
# Basic fluid acceleration
silentcut input.mp4 --accelerate 3.0 --fluid

# Recommended for maximum quality (with auto-threshold)
silentcut input.mp4 --auto --accel 3.0 -f
```

## Verification

- **Unit Tests**: `tests/unit/test_processor.py` verifies the generation of transition segments.
- **VIsual Analysis**: Comparing `--accel 3.0` vs `--accel 3.0 --fluid` shows a significant reduction in visual "stuttering" and more professional-looking transitions.
