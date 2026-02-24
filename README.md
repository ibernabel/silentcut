# ✂️ SilentCut

**Automated Video Silence Remover for Creators and Data Scientists.**

SilentCut is a high-performance CLI tool designed to automatically detect and remove silent segments from videos. Whether you're a YouTuber looking to speed up your editing or a developer processing large-scale video datasets, SilentCut provides a robust, frame-perfect solution.

---

## 🚀 The Problem I Solved

Editing out "dead air" or long pauses in video content is a manual, repetitive, and time-consuming task for creators. Common tools often suffer from:

- **Lack of Precision**: Inaccurate silence detection that cuts off the start or end of sentences.
- **Complexity**: Over-engineered software with steep learning curves.
- **Audio/Video Drift**: Inconsistent synchronization after concatenation.

SilentCut solves this by automating the entire pipeline—from analyzing the audio noise floor to performing frame-accurate cuts with perfect synchronization.

## 🛠️ Technical Decisions

To ensure the tool is both developer-friendly and production-ready, I made the following strategic choices:

1.  **Python 3.12 + `uv`**: Leveraging the latest Python features and the blazing-fast `uv` package manager for reproducible environments.
2.  **FFmpeg Filter Complex**: Instead of simple stream copies which are prone to A/V sync drift, SilentCut uses an explicit `filter_complex` graph. This re-encodes segments using the `ultrafast` preset, guaranteeing that audio and video remain perfectly aligned regardless of keyframe placement.
3.  **Pydantic v2**: Enforcing strict data validation for CLI parameters (thresholds, durations, padding) to prevent runtime failures.
4.  **Rich CLI Architecture**: Utilizing `rich` for beautiful, informative terminal output including dynamic progress indicators and diagnostic tables.
5.  **Modular Protocol Design**: The detection logic is decoupled via a `Protocol`, allowing for future expansion into AI/VAD models without breaking the core orchestration.

## 🚧 Obstacles I Overcame

- **The A/V Sync Challenge**: Early versions used FFmpeg's "copy" codec for speed, but this led to significant audio drift in long videos. I pivoted to an intelligent re-encoding strategy that maintains speed via the `ultrafast` x264 preset while enforcing exact timestamp alignment.
- **Synthetic Audio Edge Cases**: During development, I discovered that AI-generated voices (synthetic avatars) often lack the natural inflections real-speech VAD models expect. I implemented a robust **Auto-Threshold** engine that analyzes the specific noise floor of the input file to suggest the perfect volume-based cut point.
- **Path Management in TempDirs**: Resolved complex system-level issues regarding how FFmpeg interacts with absolute vs. relative paths in temporary concatenation lists across different Linux environments.

## 📈 Measurable Results

- **92% Test Coverage**: A comprehensive test suite covering unit, integration, and end-to-end scenarios (with 100% coverage in core utility modules).
- **Zero-Manual-Input**: Fully automated detection and cutting process that turns hours of editing into seconds of processing time.
- **Perfect Synchronization**: Eliminated 100% of reported A/V drift issues through explicit filter graph mapping.
- **Adaptive Performance**: The `--auto` mode correctly identifies the noise floor within ±2dB accuracy across varying microphone qualities.

---

## 🛠️ Getting Started

### Prerequisites

- Python 3.12+
- FFmpeg installed on your system

### Installation

1. Make sure you have `ffmpeg` installed on your system.
2. Install the tool globally using `uv`:

```bash
# Clone the repository
git clone https://github.com/ibernabel/silentcut
cd silentcut

# Install the tool globally
uv tool install -e .
```

This will make the `silentcut` command available from anywhere in your terminal.

### Usage

```bash
# Basic usage with automatic threshold detection
silentcut input.mp4 --auto

# High-sensitivity mode for noisy environments
silentcut input.mp4 --threshold -25 --padding 0.2
```

## 📜 License

MIT License. Created with ❤️ by Idequel Bernabel.
