# Testing guide for Sprint 01

## Preprocessor (Pedro)
- python scripts/tests/test_preprocessor_basic.py  # Expect: ["a","b","c"]

## Audio I/O (Ricardo)
- python scripts/record_wav.py --out inputs/rec.wav --seconds 2
- python scripts/tests/test_audio_io_sniff.py inputs/rec.wav  # Expect: OK and printed AudioInput

## Transcribe pipeline (CWesternBurger)
- python scripts/tests/test_transcribe_stub.py  # Requires inputs/rec.wav
- Expect: TOKENS: ["h","o","l","a"] and joined string

## CLI stub (CWesternBurger)
- python scripts/tests/test_cli_transcribe_stub.py  # Expect: cli_transcribe present
