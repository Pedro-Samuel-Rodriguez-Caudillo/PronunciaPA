"""
Simple recorder to WAV mono 16kHz for local testing.

Dependencies (optional):
  pip install sounddevice soundfile

Usage:
  python scripts/record_wav.py --out inputs/rec.wav --seconds 5
"""
from __future__ import annotations

import argparse


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    p.add_argument("--seconds", type=float, default=5.0)
    p.add_argument("--samplerate", type=int, default=16000)
    p.add_argument("--channels", type=int, default=1)
    args = p.parse_args()

    try:
        import sounddevice as sd  # type: ignore
        import soundfile as sf  # type: ignore
    except Exception as e:  # pragma: no cover
        raise SystemExit(
            "Missing dependencies. Install: pip install sounddevice soundfile"
        ) from e

    print(f"Recording {args.seconds}s @ {args.samplerate}Hz, {args.channels}ch → {args.out}")
    data = sd.rec(int(args.seconds * args.samplerate), samplerate=args.samplerate, channels=args.channels)
    sd.wait()
    sf.write(args.out, data, args.samplerate)
    print("Done.")


if __name__ == "__main__":
    main()

