#!/usr/bin/env python3
"""Validate sample dataset metadata and audio files.

Usage:
    python scripts/validate_dataset.py data/sample/metadata.csv
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import wave


def validate(metadata_path: Path) -> int:
    required_columns = {"audio_path", "text", "lang"}
    errors = 0

    with metadata_path.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = required_columns - set(reader.fieldnames or [])
        if missing:
            print(f"[ERROR] Missing required columns: {', '.join(sorted(missing))}")
            return 1

        for idx, row in enumerate(reader, start=2):
            audio_rel = row["audio_path"].strip()
            text = row["text"].strip()
            lang = row["lang"].strip()

            if not audio_rel:
                print(f"[ERROR] Row {idx}: empty audio_path")
                errors += 1
                continue

            audio_path = (metadata_path.parent / audio_rel).resolve()
            if not audio_path.exists():
                print(f"[ERROR] Row {idx}: audio file not found at {audio_rel}")
                print(
                    "        Genera los audios con 'python scripts/generate_sample_dataset.py'"
                )
                errors += 1
                continue

            try:
                with wave.open(str(audio_path), "rb") as wav_file:
                    sample_width = wav_file.getsampwidth()
                    frame_rate = wav_file.getframerate()
                    n_frames = wav_file.getnframes()
                    duration = n_frames / frame_rate if frame_rate else 0
            except wave.Error as exc:  # pragma: no cover - diagnostic output
                print(f"[ERROR] Row {idx}: cannot open WAV file ({exc})")
                errors += 1
                continue

            if sample_width != 2:
                print(
                    f"[ERROR] Row {idx}: expected 16-bit PCM (2 bytes) but got {sample_width} bytes",
                )
                errors += 1

            if frame_rate != 16000:
                print(
                    f"[WARNING] Row {idx}: expected 16000 Hz sample rate but got {frame_rate} Hz",
                )

            if duration > 30:
                print(
                    f"[ERROR] Row {idx}: duration {duration:.2f}s exceeds 30s limit",
                )
                errors += 1

            if not text:
                print(f"[ERROR] Row {idx}: empty text field")
                errors += 1

            if not lang:
                print(f"[ERROR] Row {idx}: empty lang field")
                errors += 1

    if errors == 0:
        print("Validation passed ✅")
    else:
        print(f"Validation finished with {errors} error(s)")
    return 0 if errors == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate dataset metadata and audio files")
    parser.add_argument(
        "metadata",
        type=Path,
        help="Path to metadata CSV file (e.g., data/sample/metadata.csv)",
    )
    args = parser.parse_args()
    exit(validate(args.metadata))


if __name__ == "__main__":
    main()
