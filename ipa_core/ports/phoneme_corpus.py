"""Puerto PhonemeCorpus — corpus de fonemas pregrabados por pack.

Define el contrato para servir muestras de audio de fonemas individuales
o sílabas de práctica.  Cada pack de idioma puede incluir un corpus de
~3 MB de audio pre-grabado por un hablante nativo o generado por TTS.

Motivación
----------
Los drills de pronunciación son más efectivos cuando el alumno puede
escuchar el fonema objetivo producido correctamente antes y después de
su propio intento.  El corpus de fonemas pregrabados evita llamadas
a TTS en tiempo real y funciona completamente offline.

Estructura del corpus en disco
------------------------------
::

    data/phoneme_corpora/<lang_code>/
        meta.json          # metadatos: speaker, accent, format, sample_rate
        phones/
            a.wav          # fonema /a/
            e.wav          # fonema /e/
            ...
        syllables/         # opcional: sílabas frecuentes pre-grabadas
            pa.wav
            ta.wav
            ...

El formato de audio preferido es WAV PCM 16-bit mono 22050 Hz.
Los ficheros OGG/Opus también son aceptados para ahorrar espacio.

Implementaciones
----------------
- ``DiskPhonemeCorpus`` — lee ficheros del disco (por defecto).
- ``NullPhonemeCorpus`` — siempre retorna None (offline, sin corpus).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

from ipa_core.types import AudioInput, Token


@runtime_checkable
class PhonemeCorpusPort(Protocol):
    """Contrato para el corpus de fonemas pregrabados."""

    async def setup(self) -> None:
        """Configuración inicial (conectar a disco, cargar índice)."""
        ...

    async def teardown(self) -> None:
        """Limpieza de recursos."""
        ...

    async def get_phone_audio(
        self,
        phone: Token,
        *,
        lang: str,
    ) -> Optional[AudioInput]:
        """Obtener audio de referencia para un fonema.

        Parámetros
        ----------
        phone : Token
            Símbolo IPA del fonema (p.ej. ``"ʃ"``, ``"a"``).
        lang : str
            Código de idioma (p.ej. ``"es"``, ``"en"``).

        Retorna
        -------
        AudioInput | None
            Descriptor de audio o None si el fonema no está en el corpus.
        """
        ...

    async def get_syllable_audio(
        self,
        syllable: str,
        *,
        lang: str,
    ) -> Optional[AudioInput]:
        """Obtener audio de referencia para una sílaba pre-grabada.

        Parámetros
        ----------
        syllable : str
            Transcripción IPA de la sílaba (p.ej. ``"pa"``, ``"ʃa"``).
        lang : str
            Código de idioma.

        Retorna
        -------
        AudioInput | None
            Descriptor de audio o None si la sílaba no está disponible.
        """
        ...

    async def list_available_phones(self, *, lang: str) -> list[Token]:
        """Listar los fonemas disponibles en el corpus para un idioma."""
        ...


class DiskPhonemeCorpus:
    """Corpus de fonemas en disco.  Lee ficheros WAV/OGG del directorio del pack.

    Parámetros
    ----------
    corpus_root : Path | str
        Directorio raíz que contiene subdirectorios por idioma.
        Por defecto: ``data/phoneme_corpora``.
    """

    def __init__(
        self,
        corpus_root: str | Path = "data/phoneme_corpora",
    ) -> None:
        self._root = Path(corpus_root)
        self._index: dict[str, dict[str, Path]] = {}  # lang → {phone → path}

    async def setup(self) -> None:
        """Construir índice de ficheros disponibles."""
        self._index.clear()
        if not self._root.exists():
            return
        for lang_dir in self._root.iterdir():
            if not lang_dir.is_dir():
                continue
            lang = lang_dir.name
            phones: dict[str, Path] = {}
            phones_dir = lang_dir / "phones"
            if phones_dir.exists():
                for audio_file in phones_dir.iterdir():
                    if audio_file.suffix.lower() in {".wav", ".ogg", ".opus", ".mp3"}:
                        phone_key = audio_file.stem  # nombre del archivo = IPA
                        phones[phone_key] = audio_file
            self._index[lang] = phones

    async def teardown(self) -> None:
        self._index.clear()

    async def get_phone_audio(
        self,
        phone: Token,
        *,
        lang: str,
    ) -> Optional[AudioInput]:
        lang_index = self._index.get(lang) or self._index.get(lang.split("-")[0])
        if not lang_index:
            return None
        path = lang_index.get(phone)
        if path is None:
            return None
        return AudioInput(path=str(path), sample_rate=22050, channels=1)

    async def get_syllable_audio(
        self,
        syllable: str,
        *,
        lang: str,
    ) -> Optional[AudioInput]:
        lang_dir = self._root / lang
        if not lang_dir.exists():
            lang_dir = self._root / lang.split("-")[0]
        sylls_dir = lang_dir / "syllables"
        if not sylls_dir.exists():
            return None
        for ext in (".wav", ".ogg", ".opus", ".mp3"):
            path = sylls_dir / f"{syllable}{ext}"
            if path.exists():
                return AudioInput(path=str(path), sample_rate=22050, channels=1)
        return None

    async def list_available_phones(self, *, lang: str) -> list[Token]:
        lang_index = self._index.get(lang) or self._index.get(lang.split("-")[0]) or {}
        return sorted(lang_index.keys())


class NullPhonemeCorpus:
    """Corpus vacío (no-op).  Sempre retorna None / lista vacía.

    Úsalo como fallback cuando no hay corpus instalado.
    """

    async def setup(self) -> None:
        pass

    async def teardown(self) -> None:
        pass

    async def get_phone_audio(
        self, phone: Token, *, lang: str
    ) -> Optional[AudioInput]:
        return None

    async def get_syllable_audio(
        self, syllable: str, *, lang: str
    ) -> Optional[AudioInput]:
        return None

    async def list_available_phones(self, *, lang: str) -> list[Token]:
        return []


__all__ = [
    "PhonemeCorpusPort",
    "DiskPhonemeCorpus",
    "NullPhonemeCorpus",
]
