"""Backend ASR basado en Allosaurus para reconocimiento fonético.

Allosaurus es un modelo de reconocimiento fonético multilingüe
que produce transcripciones IPA directamente desde audio.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

from ipa_core.errors import NotReadyError, ValidationError
from ipa_core.plugins.base import BasePlugin
from ipa_core.types import ASRResult, AudioInput

if TYPE_CHECKING:
    pass


# Carga diferida de Allosaurus
# Nota: panphon (dependencia) puede fallar en Python < 3.10 con TypeError
try:
    from allosaurus.app import read_recognizer
    ALLOSAURUS_AVAILABLE = True
except (ImportError, TypeError) as e:
    ALLOSAURUS_AVAILABLE = False
    read_recognizer = None  # type: ignore
    _ALLOSAURUS_ERROR = str(e)


class AllosaurusBackend(BasePlugin):
    """Backend ASR usando Allosaurus para transcripción fonética.
    
    Allosaurus es un reconocedor fonético universal que produce
    tokens IPA directamente sin necesidad de G2P intermedio.
    
    Parámetros
    ----------
    model_name : str
        Nombre del modelo a usar. Default: "uni2005" (universal).
    lang : str | None
        Código de idioma para restringir el inventario fonético.
        Si es None, usa el inventario universal.
    device : str
        Dispositivo de inferencia: "cpu" o "cuda".
    emit_timestamps : bool
        Si True, intenta obtener timestamps por token.
    """
    
    # Declara que este backend produce IPA directo
    output_type = "ipa"
    
    # Mapeo de códigos ISO 639-1 (2 letras) / BCP-47 a códigos Allosaurus (ISO 639-3).
    # Allosaurus usa códigos ISO 639-3 de Phoible para restringir el inventario.
    # Fuente: https://github.com/xinjli/allosaurus — lista completa de lenguas soportadas.
    # Cubre las ~200 lenguas más habladas y muchas lenguas documentadas en Phoible.
    _LANG_MAP: dict[str, str] = {
        # ── Indo-europeas ──────────────────────────────────────────────────────
        "en": "eng",    # Inglés
        "de": "deu",    # Alemán
        "fr": "fra",    # Francés
        "es": "spa",    # Español
        "it": "ita",    # Italiano
        "pt": "por",    # Portugués
        "nl": "nld",    # Neerlandés
        "pl": "pol",    # Polaco
        "cs": "ces",    # Checo
        "sk": "slk",    # Eslovaco
        "sl": "slv",    # Esloveno
        "hr": "hrv",    # Croata
        "sr": "srp",    # Serbio
        "bs": "bos",    # Bosnio
        "bg": "bul",    # Búlgaro
        "mk": "mkd",    # Macedonio
        "ro": "ron",    # Rumano
        "uk": "ukr",    # Ucraniano
        "ru": "rus",    # Ruso
        "be": "bel",    # Bielorruso
        "lt": "lit",    # Lituano
        "lv": "lav",    # Letón
        "et": "est",    # Estonio (rama urálica, no IE; incluido aquí por proximidad)
        "sv": "swe",    # Sueco
        "no": "nob",    # Noruego Bokmål
        "nb": "nob",    # Noruego Bokmål (alias)
        "nn": "nno",    # Noruego Nynorsk
        "da": "dan",    # Danés
        "is": "isl",    # Islandés
        "fo": "fao",    # Feroés
        "ga": "gle",    # Irlandés
        "cy": "cym",    # Galés
        "br": "bre",    # Bretón
        "ca": "cat",    # Catalán
        "gl": "glg",    # Gallego
        "oc": "oci",    # Occitano
        "la": "lat",    # Latín
        "el": "ell",    # Griego moderno
        "grc": "grc",   # Griego antiguo
        "hy": "hye",    # Armenio
        "sq": "sqi",    # Albanés
        "fa": "pes",    # Persa (Farsi)
        "ps": "pus",    # Pashto
        "ku": "kmr",    # Kurdo sorani
        "ckb": "ckb",   # Kurdo central
        "ur": "urd",    # Urdu
        "hi": "hin",    # Hindi
        "bn": "ben",    # Bengalí
        "pa": "pan",    # Punjabi
        "gu": "guj",    # Gujarati
        "mr": "mar",    # Marathi
        "ne": "nep",    # Nepalés
        "si": "sin",    # Cingalés
        "or": "ori",    # Oriya
        "as": "asm",    # Asamés
        "sd": "snd",    # Sindhi
        # ── Dravídicas ────────────────────────────────────────────────────────
        "ta": "tam",    # Tamil
        "te": "tel",    # Telugu
        "kn": "kan",    # Kannada
        "ml": "mal",    # Malayalam
        # ── Sino-tibetanas ────────────────────────────────────────────────────
        "zh": "cmn",    # Chino mandarín
        "zh-cn": "cmn", # Mandarín (China)
        "zh-tw": "cmn", # Mandarín (Taiwán)
        "yue": "yue",   # Cantonés
        "wuu": "wuu",   # Chino wu (shanghainés)
        "nan": "nan",   # Min Nan (hokkien)
        "my": "mya",    # Birmano
        "bo": "bod",    # Tibetano
        "dz": "dzo",    # Dzongkha
        # ── Japonesa y coreana ────────────────────────────────────────────────
        "ja": "jpn",    # Japonés
        "ko": "kor",    # Coreano
        # ── Urálicas ──────────────────────────────────────────────────────────
        "fi": "fin",    # Finés
        "hu": "hun",    # Húngaro
        "et": "est",    # Estonio (también urálica)
        "kpv": "kpv",   # Komi-Zyryan
        "koi": "koi",   # Komi-Permyak
        "mhr": "mhr",   # Mari del este
        "udm": "udm",   # Udmurto
        "myv": "myv",   # Erzya (Mordvino)
        "mdf": "mdf",   # Moksha
        "smn": "smn",   # Sami inari
        "sme": "sme",   # Sami del norte
        # ── Turco-altaicas ────────────────────────────────────────────────────
        "tr": "tur",    # Turco
        "az": "azj",    # Azerbaiyano
        "kk": "kaz",    # Kazajo
        "ky": "kir",    # Kirguís
        "uz": "uzb",    # Uzbeko
        "tk": "tuk",    # Turkmeno
        "tt": "tat",    # Tártaro
        "ba": "bak",    # Bashkiro
        "cv": "chv",    # Chuvasio
        "ug": "uig",    # Uigur
        "sah": "sah",   # Yakuto
        "mn": "khk",    # Mongol (Jalkha)
        # ── Semíticas / Afro-asiáticas ────────────────────────────────────────
        "ar": "ara",    # Árabe estándar moderno
        "arb": "arb",   # Árabe estándar (alias)
        "he": "heb",    # Hebreo
        "mt": "mlt",    # Maltés
        "am": "amh",    # Amhárico
        "ti": "tir",    # Tigriña
        "so": "som",    # Somalí
        "ha": "hau",    # Hausa
        "om": "orm",    # Oromo
        "aa": "aar",    # Afar
        # ── Nilo-Saharianas / Niger-Congo ─────────────────────────────────────
        "sw": "swh",    # Swahili
        "yo": "yor",    # Yoruba
        "ig": "ibo",    # Igbo
        "zu": "zul",    # Zulú
        "xh": "xho",    # Xhosa
        "af": "afr",    # Afrikaans
        "sn": "sna",    # Shona
        "ny": "nya",    # Chichewa / Nyanja
        "rw": "kin",    # Kinyarwanda
        "rn": "run",    # Kirundí
        "ln": "lin",    # Lingala
        "kg": "kon",    # Kongo
        "lu": "lub",    # Luba
        "wo": "wol",    # Wolof
        "ff": "ful",    # Fula / Fulani
        "bm": "bam",    # Bambara
        "ak": "aka",    # Akan (Twi/Fante)
        "ee": "ewe",    # Ewe
        "tw": "twi",    # Twi
        "st": "sot",    # Sotho del sur
        "tn": "tsn",    # Tswana
        "ss": "ssw",    # Swazi
        "ts": "tso",    # Tsonga
        "ve": "ven",    # Venda
        "nr": "nbl",    # Ndebele del sur
        "nd": "nde",    # Ndebele del norte
        "sg": "sag",    # Sango
        "mg": "mlg",    # Malgache
        # ── Austronesias ──────────────────────────────────────────────────────
        "id": "ind",    # Indonesio
        "ms": "zsm",    # Malayo
        "tl": "tgl",    # Tagalo / Filipino
        "jv": "jav",    # Javanés
        "su": "sun",    # Sundanés
        "mi": "mri",    # Maorí
        "fj": "fij",    # Fiyiano
        "sm": "smo",    # Samoano
        "to": "ton",    # Tongano
        "haw": "haw",   # Hawaiano
        "mg": "mlg",    # Malgache (también Austronesia)
        "ceb": "ceb",   # Cebuano
        "ilo": "ilo",   # Ilocano
        "war": "war",   # Waray-Waray
        # ── Tai-Kadai / Austro-Asiáticas ──────────────────────────────────────
        "th": "tha",    # Tailandés
        "lo": "lao",    # Laosiano
        "km": "khm",    # Jemer
        "vi": "vie",    # Vietnamita
        "mn": "khk",    # Mongol
        # ── Caucásicas ────────────────────────────────────────────────────────
        "ka": "kat",    # Georgiano
        "ab": "abk",    # Abjasio
        "ce": "che",    # Checheno
        "av": "ava",    # Avar
        "lbe": "lbe",   # Laki
        "ady": "ady",   # Adyghe
        "inh": "inh",   # Ingush
        # ── Lenguas de signos y otras ─────────────────────────────────────────
        "eu": "eus",    # Euskera (aislada)
        "ka": "kat",    # Georgiano
        "mn": "khk",    # Mongol
        "hy": "hye",    # Armenio (también IE pero incluido aquí para agrupación)
        # ── Lenguas indígenas americanas ──────────────────────────────────────
        "qu": "que",    # Quechua
        "ay": "aym",    # Aimara
        "gn": "grn",    # Guaraní
        "nah": "nah",   # Náhuatl (varios dialectos)
        "mam": "mam",   # Mam (maya)
        "kek": "kek",   # Q'eqchi' (maya)
        "oto": "ote",   # Otomí
        "zap": "zai",   # Zapoteca
        "mix": "mix",   # Mixteca
        "tzh": "tze",   # Tzeltal
        "tzo": "tzo",   # Tzotzil
        "chk": "chk",   # Chuukés
        # ── Variedades / regionales ───────────────────────────────────────────
        "pt-br": "por",  # Portugués brasileño → por
        "pt-pt": "por",  # Portugués europeo → por
        "es-mx": "spa",  # Español mexicano → spa
        "es-es": "spa",  # Español castellano → spa
        "es-ar": "spa",  # Español argentino → spa
        "fr-ca": "fra",  # Francés canadiense → fra
        "en-gb": "eng",  # Inglés británico → eng
        "en-us": "eng",  # Inglés americano → eng
        "en-au": "eng",  # Inglés australiano → eng
        "zh-yue": "yue", # Cantonés
    }
    
    def __init__(
        self,
        *,
        model_name: str = "uni2005",
        lang: Optional[str] = None,
        device: str = "cpu",
        emit_timestamps: bool = False,
    ) -> None:
        super().__init__()
        self._model_name = model_name
        self._lang = lang
        self._device = device
        self._emit_timestamps = emit_timestamps
        self._model = None
        self._ready = False
    
    async def setup(self) -> None:
        """Cargar el modelo de Allosaurus."""
        if not ALLOSAURUS_AVAILABLE:
            raise NotReadyError(
                "Allosaurus no instalado. Ejecuta: pip install allosaurus"
            )
        
        # Cargar modelo en un thread para no bloquear
        def load_model():
            return read_recognizer(self._model_name)
        
        loop = asyncio.get_running_loop()
        self._model = await loop.run_in_executor(None, load_model)
        self._ready = True
    
    async def teardown(self) -> None:
        """Liberar recursos del modelo."""
        self._model = None
        self._ready = False
    
    def _resolve_lang(self, lang: Optional[str]) -> Optional[str]:
        """Resolver código de idioma a formato Allosaurus.

        SIEMPRE aplica _LANG_MAP independientemente de si ``lang`` llega de
        la llamada o del default de instancia.  Sin esto, self._lang="es"
        se pasa directamente a Allosaurus que espera "spa", lo que provoca
        fallback silencioso al inventario universal.
        """
        resolved = lang if lang is not None else self._lang
        if resolved:
            return self._LANG_MAP.get(resolved, resolved)
        return None
    
    async def transcribe(
        self,
        audio: AudioInput,
        *,
        lang: Optional[str] = None,
        **kw: Any,
    ) -> ASRResult:
        """Transcribir audio a tokens IPA.

        Garantiza WAV PCM 16 kHz mono antes de pasarlo a Allosaurus.
        El AudioProcessingChain del pipeline ya hace esta conversión, pero
        si falla silenciosamente o el backend se usa directamente, sin esta
        garantía Allosaurus recibe audio mal formateado y produce tokens
        basura o un string vacío.

        Parámetros
        ----------
        audio : AudioInput
            Diccionario con path, sample_rate y channels.
        lang : str | None
            Código de idioma para restringir inventario.

        Retorna
        -------
        ASRResult
            Tokens IPA y metadatos.
        """
        if not self._ready or self._model is None:
            raise NotReadyError("AllosaurusBackend no inicializado. Llama setup() primero.")

        audio_path = Path(audio["path"])
        if not audio_path.exists():
            raise ValidationError(f"Archivo de audio no existe: {audio_path}")

        resolved_lang = self._resolve_lang(lang)

        # Garantizar WAV PCM 16 kHz mono antes de invocar Allosaurus.
        # Allosaurus internamente usa wave.open() y asume 16 kHz; cualquier
        # otra frecuencia produce transcripciones incorrectas.
        from ipa_core.audio.files import ensure_wav
        import os
        clean_path, is_tmp = ensure_wav(str(audio_path), target_sample_rate=16000, target_channels=1)

        # Rellenar con silencio si el audio es demasiado corto.
        # Allosaurus usa ventanas de contexto de ~250 ms; clips < 700 ms producen
        # tokens "alucinados" porque el modelo no tiene suficiente contexto temporal.
        # Se añaden 150 ms de silencio al inicio Y al final (= +300 ms total).
        clean_path, is_tmp = self._pad_audio_if_short(clean_path, is_tmp, min_ms=700, pad_ms=150)

        try:
            raw_output = await self._run_recognize(clean_path, resolved_lang)
        finally:
            if is_tmp:
                try:
                    os.unlink(clean_path)
                except OSError:
                    pass

        # Parsear salida
        tokens, timestamps = self._parse_output(raw_output)

        return {
            "tokens": tokens,
            "raw_text": raw_output if isinstance(raw_output, str) else " ".join(tokens),
            "time_stamps": timestamps,
            "meta": {
                "backend": "allosaurus",
                "model": self._model_name,
                "lang": resolved_lang,
                "device": self._device,
                "confidence_available": False,
            },
        }

    @staticmethod
    def _pad_audio_if_short(
        path: str,
        is_tmp: bool,
        *,
        min_ms: int = 700,
        pad_ms: int = 150,
    ) -> tuple[str, bool]:
        """Añadir silencio al inicio y final si el audio es más corto que ``min_ms``.

        Parámetros
        ----------
        path : str
            Ruta al archivo WAV 16-bit PCM.
        is_tmp : bool
            True si ``path`` es un temporal (se puede eliminar después de padear).
        min_ms : int
            Umbral mínimo en ms. Si la duración >= min_ms, no se hace nada.
        pad_ms : int
            Milisegundos de silencio a añadir ANTES y DESPUÉS del audio.

        Retorna
        -------
        (new_path, new_is_tmp) : tuple[str, bool]
        """
        import os
        import struct
        import tempfile
        import wave

        try:
            with wave.open(path, "rb") as wf:
                sr = wf.getframerate()
                sw = wf.getsampwidth()
                nc = wf.getnchannels()
                n_frames = wf.getnframes()
                data = wf.readframes(n_frames)

            duration_ms = int(n_frames * 1000 / sr) if sr > 0 else 0
            if duration_ms >= min_ms:
                return path, is_tmp  # ya es suficientemente largo

            # Crear bloque de silencio (ceros)
            pad_frames = int(pad_ms * sr / 1000)
            bytes_per_frame = sw * nc
            silence = bytes(pad_frames * bytes_per_frame)
            padded_data = silence + data + silence

            with tempfile.NamedTemporaryFile(
                prefix="pronunciapa_pad_", suffix=".wav", delete=False
            ) as tmp:
                tmp_path = tmp.name

            with wave.open(tmp_path, "wb") as out_wf:
                out_wf.setnchannels(nc)
                out_wf.setsampwidth(sw)
                out_wf.setframerate(sr)
                out_wf.writeframes(padded_data)

            # Eliminar el temporal anterior si ya no se necesita
            if is_tmp:
                try:
                    os.unlink(path)
                except OSError:
                    pass

            logger.debug(
                "AllosaurusBackend: audio padded %d ms → %d ms (pad=%d ms cada lado)",
                duration_ms,
                duration_ms + 2 * pad_ms,
                pad_ms,
            )
            return tmp_path, True

        except Exception as exc:
            logger.warning("_pad_audio_if_short falló, continuando sin padding: %s", exc)
            return path, is_tmp

    async def _run_recognize(self, audio_path: str, resolved_lang: Optional[str]) -> Any:
        """Ejecutar reconocimiento en thread separado (no bloquea el event loop)."""
        def recognize():
            if resolved_lang:
                return self._model.recognize(
                    audio_path,
                    lang_id=resolved_lang,
                    timestamp=self._emit_timestamps,
                )
            else:
                return self._model.recognize(
                    audio_path,
                    timestamp=self._emit_timestamps,
                )

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, recognize)
    
    def _parse_output(
        self,
        output: Any,
    ) -> tuple[list[str], Optional[list[tuple[float, float]]]]:
        """Parsear la salida de Allosaurus.
        
        Allosaurus puede retornar:
        - str: "p a l a b r a" (tokens separados por espacio)
        - list: [(start, end, phone), ...] si timestamp=True
        """
        if isinstance(output, str):
            # Formato simple: tokens separados por espacio
            tokens = [t.strip() for t in output.split() if t.strip()]
            return tokens, None
        
        if isinstance(output, list):
            # Formato con timestamps
            tokens = []
            timestamps = []
            for item in output:
                if len(item) >= 3:
                    start, end, phone = item[0], item[1], item[2]
                    tokens.append(str(phone).strip())
                    timestamps.append((float(start), float(end)))
            return tokens, timestamps if timestamps else None
        
        # Fallback
        return [], None


class AllosaurusBackendStub(BasePlugin):
    """Stub de Allosaurus para testing sin modelo real.
    
    Retorna tokens predefinidos para pruebas unitarias.
    """
    output_type = "ipa"
    
    def __init__(
        self,
        *,
        mock_tokens: Optional[list[str]] = None,
        mock_timestamps: Optional[list[tuple[float, float]]] = None,
    ) -> None:
        self._mock_tokens = mock_tokens or ["h", "ɛ", "l", "oʊ"]
        self._mock_timestamps = mock_timestamps
        self._ready = False
    
    async def setup(self) -> None:
        """Simular carga de modelo."""
        self._ready = True
    
    async def teardown(self) -> None:
        """Simular liberación de recursos."""
        self._ready = False
    
    async def transcribe(
        self,
        audio: AudioInput,
        *,
        lang: Optional[str] = None,
        **kw: Any,
    ) -> ASRResult:
        """Retornar tokens mock."""
        if not self._ready:
            raise NotReadyError("Stub no inicializado.")
        
        return {
            "tokens": list(self._mock_tokens),  # copy — never expose mutable instance state
            "raw_text": " ".join(self._mock_tokens),
            "time_stamps": self._mock_timestamps,
            "confidences": [1.0] * len(self._mock_tokens),
            "meta": {
                "backend": "allosaurus_stub",
                "model": "stub",
                "lang": lang,
                "confidence_avg": 1.0,
                "confidence_available": True,
            },
        }


__all__ = [
    "AllosaurusBackend",
    "AllosaurusBackendStub",
    "ALLOSAURUS_AVAILABLE",
]
