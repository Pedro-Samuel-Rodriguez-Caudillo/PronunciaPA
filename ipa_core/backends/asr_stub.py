"""Backend ASR de ejemplo para el MVP.

Genera tokens IPA variados a partir de las características del audio.
No realiza inferencia real de fonemas, pero produce resultados distintos
para cada grabación, permitiendo validar el pipeline de extremo a extremo.
"""
from __future__ import annotations

import hashlib
import logging
import random
import struct
import wave
from typing import Optional, Any, List
from pathlib import Path

from ipa_core.plugins.base import BasePlugin
from ipa_core.types import ASRResult, AudioInput, Token

logger = logging.getLogger(__name__)

# ── Inventario de fonemas por idioma para generación variada ──────────
_PHONEME_POOLS: dict[str, List[str]] = {
    "es": [
        "a", "e", "i", "o", "u",
        "p", "b", "t", "d", "k", "ɡ",
        "f", "s", "x", "tʃ",
        "m", "n", "ɲ",
        "l", "ʎ", "ɾ", "r",
    ],
    "en": [
        "æ", "ɑ", "ɪ", "iː", "ʊ", "uː", "ɛ", "ə", "ʌ",
        "p", "b", "t", "d", "k", "ɡ",
        "f", "v", "θ", "ð", "s", "z", "ʃ", "ʒ", "h",
        "m", "n", "ŋ", "l", "ɹ", "w", "j",
    ],
}
_DEFAULT_POOL = _PHONEME_POOLS["es"]

# ── Patrones silábicos comunes en español ────────────────────────────
_VOWELS_ES = {"a", "e", "i", "o", "u"}


class StubASR(BasePlugin):
    """ASR de desarrollo que genera tokens IPA basándose en el audio real.

    Comportamiento:
      1. Lee el archivo de audio y extrae duración + patrón de energía.
      2. Usa un hash del contenido como semilla para generar fonemas variados.
      3. La cantidad de fonemas es proporcional a la duración (~10 fonemas/seg).

    Params (dict):
      - stub_tokens: list[str] opcional → fuerza tokens fijos (modo legacy).
      - model_path: ruta al modelo (simulado).
      - phonemes_per_sec: float (default 10.0) — densidad de fonemas.
    """

    output_type = "ipa"  # Stub produces IPA tokens

    def __init__(self, params: Optional[dict[str, Any]] = None) -> None:
        super().__init__()
        params = params or {}
        self._fixed_tokens: Optional[list[Token]] = None
        if isinstance(params.get("stub_tokens"), list):
            self._fixed_tokens = [str(t) for t in params["stub_tokens"]]

        self._model_path = Path(params.get("model_path", "data/models/stub_model.bin"))
        self._download_stub = bool(params.get("download_stub"))
        self._phonemes_per_sec = float(params.get("phonemes_per_sec", 10.0))

    async def setup(self) -> None:
        """Simula la verificación/descarga de activos."""
        if not self._download_stub:
            return
        await self.model_manager.ensure_model(
            name="Stub Model",
            local_path=self._model_path,
            download_url="https://example.com/models/stub.bin",
        )

    # ── helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _audio_fingerprint(path: str) -> tuple[float, bytes]:
        """Return (duration_seconds, sha256_digest) from a WAV file."""
        try:
            with wave.open(path, "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                raw = wf.readframes(frames)
                duration = frames / max(rate, 1)
                digest = hashlib.sha256(raw).digest()
                return (duration, digest)
        except Exception:
            # Fallback: read raw bytes for non-WAV files
            try:
                data = Path(path).read_bytes()
                # Estimate ~16 kHz, 16-bit mono → 32000 bytes/sec
                duration = max(len(data) / 32000.0, 0.3)
                digest = hashlib.sha256(data).digest()
                return (duration, digest)
            except Exception:
                # Absolute fallback
                return (1.0, hashlib.sha256(b"fallback").digest())

    def _generate_tokens(
        self, duration: float, digest: bytes, lang: str
    ) -> list[Token]:
        """Generate a phoneme sequence seeded by the audio fingerprint."""
        pool = _PHONEME_POOLS.get(lang, _DEFAULT_POOL)
        vowels = _VOWELS_ES if lang == "es" else {p for p in pool if p in "aeiouæɑɪɛəʌʊ"}

        # Seed from audio hash → deterministic per recording
        seed = struct.unpack(">I", digest[:4])[0]
        rng = random.Random(seed)

        n_phonemes = max(2, int(duration * self._phonemes_per_sec))
        # Cap at reasonable max
        n_phonemes = min(n_phonemes, 80)

        tokens: list[Token] = []
        for i in range(n_phonemes):
            if i > 0 and tokens[-1] not in vowels and rng.random() < 0.55:
                # After consonant, bias toward vowel (natural syllable structure)
                candidates = [p for p in pool if p in vowels]
                tokens.append(rng.choice(candidates) if candidates else rng.choice(pool))
            else:
                tokens.append(rng.choice(pool))
        return tokens

    # ── main entry ───────────────────────────────────────────────────

    async def transcribe(self, audio: AudioInput, *, lang: Optional[str] = None, **kw) -> ASRResult:  # noqa: D401
        # Legacy mode: fixed tokens override
        if self._fixed_tokens is not None:
            return {
                "tokens": list(self._fixed_tokens),
                "meta": {"backend": "stub", "mode": "fixed", "lang": lang or ""},
            }

        # Audio-aware mode: read file and generate varied output
        effective_lang = lang or "es"
        audio_path = audio.get("path", "") if isinstance(audio, dict) else ""
        if audio_path and Path(audio_path).exists():
            duration, digest = self._audio_fingerprint(audio_path)
            tokens = self._generate_tokens(duration, digest, effective_lang)
            logger.debug(
                "StubASR: generated %d tokens from %.1fs audio (seed=%s)",
                len(tokens), duration, digest[:4].hex(),
            )
        else:
            # No audio file available — return a short default
            tokens = ["o", "l", "a"]
            logger.warning("StubASR: no audio file found, returning default tokens")

        return {
            "tokens": tokens,
            "meta": {"backend": "stub", "mode": "audio_aware", "lang": effective_lang},
        }
