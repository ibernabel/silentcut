# Phase 1.3: Prevent File Overwrite

SilentCut now prevents accidental overwriting of output files by automatically generating unique filenames if the target already exists.

## Technical Implementation

### Unique Path Utility

A new function `silentcut.utils.get_unique_path` was added. It checks if a file exists and, if it does, appends a counter in parentheses:

- `video_no_silence.mp4` -> `video_no_silence (1).mp4`
- `video_no_silence (1).mp4` -> `video_no_silence (2).mp4`

### Integration in Main

The `remove` command in `main.py` now passes the desired output path through this utility before processing starts.

> [!NOTE]
> This logic is bypassed in **Dry Run** mode to avoid confusion, as no file is actually created.

## Verification

Verified with a dedicated test script (`test_unique_logic.py`) that simulated multiple consecutive runs with the same filename.
