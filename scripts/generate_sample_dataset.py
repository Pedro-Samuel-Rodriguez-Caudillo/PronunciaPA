#!/usr/bin/env python3
"""Generate synthetic WAV files for the sample dataset.

This script reads ``data/sample/metadata.csv`` and generates short sine wave
clips for each entry so that the validation pipeline can run without shipping
binary assets in the repository.
"""

from __future__ import annotations

import argparse
import csv
import math
import struct
from pathlib import Path
import wave

# Default configuration for each audio file declared in the metadata. Frequencies
# are chosen to roughly match the textual descriptions in ``metadata.csv``.
TONE_CONFIG = {
    "sample_01.wav": {"frequency": 440.0, "duration": 2.0},
    "sample_02.wav": {"frequency": 554.37, "duration": 2.0},
    "sample_03.wav": {"frequency": 659.25, "duration": 2.0},
}

SAMPLE_RATE = 16_000
SAMPLE_WIDTH = 2  # bytes, PCM 16-bit
AMPLITUDE = 0.3  # scale for the sine wave (-1.0..1.0)


def _synthesize_tone(path: Path, frequency: float, duration: float, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        print(f"[SKIP] {path.name} already exists (use --overwrite to regenerate)")
        return

    total_frames = int(duration * SAMPLE_RATE)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(SAMPLE_WIDTH)
        wav_file.setframerate(SAMPLE_RATE)

        frames = bytearray()
        for n in range(total_frames):
            sample = math.sin(2 * math.pi * frequency * n / SAMPLE_RATE)
            value = int(max(min(sample * AMPLITUDE, 1.0), -1.0) * 32767)
            frames.extend(struct.pack("<h", value))

        wav_file.writeframes(frames)

    print(f"[OK] Generated {path.name} ({duration:.1f}s @ {frequency:.2f} Hz)")


def _load_metadata(metadata_path: Path) -> list[str]:
    with metadata_path.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames or "audio_path" not in reader.fieldnames:
            raise ValueError("metadata is missing the required 'audio_path' column")
        return [row["audio_path"].strip() for row in reader]


def generate(metadata_path: Path, overwrite: bool) -> None:
    audio_files = _load_metadata(metadata_path)
    base_dir = metadata_path.parent

    for relative_name in audio_files:
        if not relative_name:
            print("[WARN] Encountered empty audio_path entry; skipping")
            continue

        config = TONE_CONFIG.get(relative_name)
        if config is None:
            raise KeyError(
                f"No tone configuration available for {relative_name}. "
                "Please add an entry to TONE_CONFIG."
            )

        output_path = base_dir / relative_name
        output_path.parent.mkdir(parents=True, exist_ok=True)
        _synthesize_tone(
            output_path,
            frequency=config["frequency"],
            duration=config["duration"],
            overwrite=overwrite,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate WAV files for the sample dataset")
    parser.add_argument(
        "metadata",
        type=Path,
        nargs="?",
        default=Path("data/sample/metadata.csv"),
        help="Metadata CSV to read (defaults to data/sample/metadata.csv)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Regenerate audio files even if they already exist",
    )
    args = parser.parse_args()

    generate(args.metadata, overwrite=args.overwrite)


if __name__ == "__main__":
    main()
