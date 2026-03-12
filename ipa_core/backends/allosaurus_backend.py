"""Backend ASR basado en Allosaurus para reconocimiento fonético.

Allosaurus es un modelo de reconocimiento fonético multilingüe
que produce transcripciones IPA directamente desde audio.
"""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

import numpy as np

logger = logging.getLogger(__name__)

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
    read_recognizer: Any = None
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
        "ceb": "ceb",   # Cebuano
        "ilo": "ilo",   # Ilocano
        "war": "war",   # Waray-Waray
        # ── Tai-Kadai / Austro-Asiáticas ──────────────────────────────────────
        "th": "tha",    # Tailandés
        "lo": "lao",    # Laosiano
        "km": "khm",    # Jemer
        "vi": "vie",    # Vietnamita
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
        self._pm = None
        self._am = None
        self._lm = None
        self._ctc_decoder = None
        self._ctc_labels: list[str] = []
        self._active_mask = None
        self._active_lang: Optional[str] = None
        self._blank_index = 0
        self._ready = False
    
    async def setup(self) -> None:
        """Cargar el modelo de Allosaurus."""
        if not ALLOSAURUS_AVAILABLE:
            raise NotReadyError(
                "Allosaurus no instalado. Ejecuta: pip install allosaurus"
            )
        
        # Cargar modelo en un thread para no bloquear
        def load_model() -> Any:
            if read_recognizer is not None:
                return read_recognizer(self._model_name)
            return None
        
        loop = asyncio.get_running_loop()
        self._model = await loop.run_in_executor(None, load_model)
        self._pm = getattr(self._model, "pm", None)
        self._am = getattr(self._model, "am", None)
        self._lm = getattr(self._model, "lm", None)
        self._active_lang = self._resolve_lang(self._lang)
        self._ensure_decoder_and_mask(self._active_lang)
        self._ready = True
    
    async def teardown(self) -> None:
        """Liberar recursos del modelo."""
        self._model = None
        self._pm = None
        self._am = None
        self._lm = None
        self._ctc_decoder = None
        self._ctc_labels = []
        self._active_mask = None
        self._active_lang = None
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
        # Sin idioma → inventario universal produce fonemas de otros idiomas.
        # Usar fallback configurable para restringir el inventario.
        default = os.getenv("PRONUNCIAPA_DEFAULT_LANG", "es")
        logger.warning(
            "No se especificó idioma para Allosaurus; usando fallback '%s'. "
            "Configure PRONUNCIAPA_DEFAULT_LANG o pase lang= explícitamente.",
            default,
        )
        return self._LANG_MAP.get(default, default)
    
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
        self._ensure_decoder_and_mask(resolved_lang)

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

        decoder_used = "pyctcdecode" if self._ctc_decoder is not None else "greedy"
        try:
            tokens, raw_output, timestamps = await self._run_logits_pipeline(clean_path, resolved_lang)
            if not tokens:
                # Safety fallback: if custom path could not decode, keep legacy behavior.
                raw_output = await self._run_recognize(clean_path, resolved_lang)
                tokens, timestamps = self._parse_output(raw_output)
                decoder_used = "allosaurus-native"
        finally:
            if is_tmp:
                try:
                    os.unlink(clean_path)
                except OSError:
                    pass

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
                "decoder": decoder_used,
            },
        }

    def _ensure_decoder_and_mask(self, resolved_lang: Optional[str]) -> None:
        """Ensure language-specific mask and CTC decoder are ready."""
        if self._lm is None:
            return
        if self._active_lang == resolved_lang and self._active_mask is not None:
            return

        self._active_lang = resolved_lang
        self._active_mask = self._build_inventory_mask(resolved_lang)
        self._ctc_labels = self._extract_labels_from_inventory()
        if self._ctc_labels:
            self._blank_index = 0
            self._ctc_labels[0] = ""
        self._ctc_decoder = self._build_ctc_decoder(self._ctc_labels)

    def _build_inventory_mask(self, resolved_lang: Optional[str]) -> Any:
        """Build language mask from Allosaurus inventory internals."""
        if self._lm is None:
            return None
        inventory = getattr(self._lm, "inventory", None)
        if inventory is None or not hasattr(inventory, "get_mask"):
            return None
        try:
            return inventory.get_mask(resolved_lang, approximation=False)
        except TypeError:
            return inventory.get_mask(resolved_lang)
        except Exception:
            return None

    def _extract_labels_from_inventory(self) -> list[str]:
        """Extract CTC label list aligned with acoustic model vocabulary."""
        if self._lm is None:
            return []

        inventory = getattr(self._lm, "inventory", None)
        unit_obj = getattr(inventory, "unit", None)
        if unit_obj is None:
            return []

        id_to_unit = getattr(unit_obj, "id_to_unit", None)
        if not isinstance(id_to_unit, dict) or not id_to_unit:
            return []

        max_idx = max(int(k) for k in id_to_unit.keys())
        labels = [""] * (max_idx + 1)
        for idx, symbol in id_to_unit.items():
            try:
                labels[int(idx)] = str(symbol or "")
            except Exception:
                continue
        return labels

    def _build_ctc_decoder(self, labels: list[str]) -> Any:
        """Build pyctcdecode beam-search decoder if available."""
        if len(labels) < 2:
            return None
        try:
            from pyctcdecode import build_ctcdecoder  # type: ignore
        except Exception:
            logger.warning("pyctcdecode no disponible; usando decodificación greedy")
            return None

        try:
            return build_ctcdecoder(labels)
        except Exception as exc:
            logger.warning("No se pudo inicializar pyctcdecode: %s", exc)
            return None

    async def _run_logits_pipeline(
        self,
        audio_path: str,
        resolved_lang: Optional[str],
    ) -> tuple[list[str], str, Optional[list[tuple[float, float]]]]:
        """Run logits interception + masking + CTC decode pipeline."""
        logits = await self._extract_logits(audio_path, resolved_lang)
        if logits is None:
            return [], "", None

        masked_logits = self._apply_mask(logits)
        tokens = self._decode_with_ctc(masked_logits)
        raw_text = " ".join(tokens)
        return tokens, raw_text, None

    async def _extract_logits(self, audio_path: str, resolved_lang: Optional[str]) -> Optional[np.ndarray]:
        """Extract raw logits tensor (T x V).

        Tries direct AM forward pass first. If internals are not available,
        falls back to intercepting logits from lm.compute during recognize().
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._extract_logits_sync, audio_path, resolved_lang)

    def _extract_logits_sync(self, audio_path: str, resolved_lang: Optional[str]) -> Optional[np.ndarray]:
        if self._model is None:
            return None

        # Preferred path: direct forward pass over AM.
        direct = self._extract_logits_direct(audio_path)
        if direct is not None:
            return direct

        # Fallback path: intercept logits right before internal decode.
        return self._extract_logits_via_intercept(audio_path, resolved_lang)

    def _extract_logits_direct(self, audio_path: str) -> Optional[np.ndarray]:
        if self._pm is None or self._am is None:
            return None
        try:
            import torch  # type: ignore
            from allosaurus.audio import read_audio  # type: ignore

            sample_rate = 16000
            pm_cfg = getattr(self._pm, "config", None)
            if pm_cfg is not None:
                sample_rate = int(getattr(pm_cfg, "sample_rate", 16000))

            audio = read_audio(audio_path, sample_rate)
            feat = self._pm.compute(audio)
            if feat is None:
                return None

            feat_np = np.asarray(feat)
            if feat_np.ndim != 2:
                return None

            # Allosaurus AM expects (T, B, F) with lengths for packed sequence.
            feat_tensor = torch.from_numpy(feat_np).float().unsqueeze(1)
            feat_len = torch.tensor([feat_np.shape[0]], dtype=torch.long)

            with torch.no_grad():
                output = self._am(feat_tensor, feat_len)

            logits = np.asarray(output[0].cpu().numpy())
            return logits if logits.ndim == 2 else None
        except Exception:
            return None

    def _extract_logits_via_intercept(self, audio_path: str, resolved_lang: Optional[str]) -> Optional[np.ndarray]:
        if self._model is None or self._lm is None:
            return None

        compute_fn = getattr(self._lm, "compute", None)
        if compute_fn is None:
            return None

        captured: dict[str, np.ndarray] = {}

        def wrapped_compute(logits: Any, *args: Any, **kwargs: Any) -> Any:
            try:
                captured["logits"] = np.asarray(logits).copy()
            except Exception:
                pass
            return compute_fn(logits, *args, **kwargs)

        setattr(self._lm, "compute", wrapped_compute)
        try:
            if resolved_lang:
                self._model.recognize(audio_path, lang_id=resolved_lang, timestamp=self._emit_timestamps)
            else:
                self._model.recognize(audio_path, timestamp=self._emit_timestamps)
        except Exception:
            return None
        finally:
            setattr(self._lm, "compute", compute_fn)

        logits = captured.get("logits")
        return logits if isinstance(logits, np.ndarray) and logits.ndim == 2 else None

    def _apply_mask(self, logits: np.ndarray) -> np.ndarray:
        if self._active_mask is None:
            return logits
        try:
            return np.asarray(self._active_mask.mask_logits(logits.copy()))
        except Exception:
            return logits

    def _decode_with_ctc(self, logits: np.ndarray) -> list[str]:
        if logits.size == 0:
            return []

        if self._ctc_decoder is not None:
            try:
                decoded = self._ctc_decoder.decode(logits)
                tokens = [tok for tok in decoded.strip().split() if tok]
                if tokens:
                    return tokens
            except Exception as exc:
                logger.warning("CTC beam decoding falló, usando greedy: %s", exc)

        return self._decode_greedy_ctc(logits)

    def _decode_greedy_ctc(self, logits: np.ndarray) -> list[str]:
        labels = self._ctc_labels
        if not labels:
            return []
        ids = np.argmax(logits, axis=1)
        tokens: list[str] = []
        prev = -1
        for idx in ids:
            i = int(idx)
            if i == self._blank_index:
                prev = i
                continue
            if i == prev:
                continue
            prev = i
            if 0 <= i < len(labels):
                token = labels[i]
                if token:
                    tokens.append(token)
        return tokens

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
        def recognize() -> Any:
            if not self._model:
                raise NotReadyError()
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
        
        result: ASRResult = {
            "tokens": list(self._mock_tokens),  # copy — never expose mutable instance state
            "raw_text": " ".join(self._mock_tokens),
            "confidences": [1.0] * len(self._mock_tokens),
            "meta": {
                "backend": "allosaurus_stub",
                "model": "stub",
                "lang": lang,
                "confidence_avg": 1.0,
                "confidence_available": True,
            },
        }
        if self._mock_timestamps is not None:
            result["time_stamps"] = self._mock_timestamps
            
        return result


__all__ = [
    "AllosaurusBackend",
    "AllosaurusBackendStub",
    "ALLOSAURUS_AVAILABLE",
]
