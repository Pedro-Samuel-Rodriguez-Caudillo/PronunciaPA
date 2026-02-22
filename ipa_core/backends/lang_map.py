"""Mapeo canónico ISO 639-1 (2 letras) → ISO 639-3 (3 letras) para Allosaurus.

Allosaurus usa códigos ISO 639-3. Este módulo centraliza la conversión para
que todos los backends que usan Allosaurus sean consistentes.

Cubre los ~184 idiomas con código oficial ISO 639-1, más variantes regionales
BCP-47 comunes (ej: "es-mx" → "spa", "zh-cn" → "cmn").
"""
from __future__ import annotations

# Mapeo completo ISO 639-1 → ISO 639-3
# Fuente: ISO 639-1/639-3 registration authority
ALLOSAURUS_LANG_MAP: dict[str, str] = {
    # A
    "aa": "aar",  # Afar
    "ab": "abk",  # Abjasio
    "ae": "ave",  # Avéstico
    "af": "afr",  # Afrikáans
    "ak": "aka",  # Akan
    "am": "amh",  # Amhárico
    "an": "arg",  # Aragonés
    "ar": "ara",  # Árabe
    "as": "asm",  # Asamés
    "av": "ava",  # Avar
    "ay": "aym",  # Aimara
    "az": "aze",  # Azerbaiyano
    # B
    "ba": "bak",  # Bashkir
    "be": "bel",  # Bielorruso
    "bg": "bul",  # Búlgaro
    "bh": "bih",  # Bihari
    "bi": "bis",  # Bislama
    "bm": "bam",  # Bambara
    "bn": "ben",  # Bengalí
    "bo": "bod",  # Tibetano
    "br": "bre",  # Bretón
    "bs": "bos",  # Bosnio
    # C
    "ca": "cat",  # Catalán
    "ce": "che",  # Checheno
    "ch": "cha",  # Chamorro
    "co": "cos",  # Corso
    "cr": "cre",  # Cree
    "cs": "ces",  # Checo
    "cu": "chu",  # Eslavo eclesiástico
    "cv": "chv",  # Chuvasio
    "cy": "cym",  # Galés
    # D
    "da": "dan",  # Danés
    "de": "deu",  # Alemán
    "dv": "div",  # Maldivio
    "dz": "dzo",  # Dzongkha
    # E
    "ee": "ewe",  # Ewe
    "el": "ell",  # Griego
    "en": "eng",  # Inglés
    "eo": "epo",  # Esperanto
    "es": "spa",  # Español
    "et": "est",  # Estonio
    "eu": "eus",  # Vasco/Euskera
    # F
    "fa": "fas",  # Persa/Farsi
    "ff": "ful",  # Fula
    "fi": "fin",  # Finés
    "fj": "fij",  # Fiyiano
    "fo": "fao",  # Feroés
    "fr": "fra",  # Francés
    "fy": "fry",  # Frisón occidental
    # G
    "ga": "gle",  # Irlandés
    "gd": "gla",  # Gaélico escocés
    "gl": "glg",  # Gallego
    "gn": "grn",  # Guaraní
    "gu": "guj",  # Gujarati
    "gv": "glv",  # Manés
    # H
    "ha": "hau",  # Hausa
    "he": "heb",  # Hebreo
    "hi": "hin",  # Hindi
    "ho": "hmo",  # Hiri Motu
    "hr": "hrv",  # Croata
    "ht": "hat",  # Criollo haitiano
    "hu": "hun",  # Húngaro
    "hy": "hye",  # Armenio
    "hz": "her",  # Herero
    # I
    "ia": "ina",  # Interlingua
    "id": "ind",  # Indonesio
    "ie": "ile",  # Interlingue
    "ig": "ibo",  # Igbo
    "ii": "iii",  # Yi de Sichuan
    "ik": "ipk",  # Inupiaq
    "io": "ido",  # Ido
    "is": "isl",  # Islandés
    "it": "ita",  # Italiano
    "iu": "iku",  # Inuktitut
    # J
    "ja": "jpn",  # Japonés
    "jv": "jav",  # Javanés
    # K
    "ka": "kat",  # Georgiano
    "kg": "kon",  # Kongo
    "ki": "kik",  # Kikuyu
    "kj": "kua",  # Kuanyama
    "kk": "kaz",  # Kazajo
    "kl": "kal",  # Groenlandés
    "km": "khm",  # Jemer
    "kn": "kan",  # Canarés
    "ko": "kor",  # Coreano
    "kr": "kau",  # Kanuri
    "ks": "kas",  # Cachemiro
    "ku": "kur",  # Kurdo
    "kv": "kom",  # Komi
    "kw": "cor",  # Córnico
    "ky": "kir",  # Kirguís
    # L
    "la": "lat",  # Latín
    "lb": "ltz",  # Luxemburgués
    "lg": "lug",  # Ganda
    "li": "lim",  # Limburgués
    "ln": "lin",  # Lingala
    "lo": "lao",  # Lao
    "lt": "lit",  # Lituano
    "lu": "lub",  # Luba-katanga
    "lv": "lav",  # Letón
    # M
    "mg": "mlg",  # Malgache
    "mh": "mah",  # Marshalés
    "mi": "mri",  # Maorí
    "mk": "mkd",  # Macedonio
    "ml": "mal",  # Malayálam
    "mn": "mon",  # Mongol
    "mr": "mar",  # Maratí
    "ms": "msa",  # Malayo
    "mt": "mlt",  # Maltés
    "my": "mya",  # Birmano
    # N
    "na": "nau",  # Nauruano
    "nb": "nob",  # Noruego Bokmål
    "nd": "nde",  # Ndebele septentrional
    "ne": "nep",  # Nepalí
    "ng": "ndo",  # Ndonga
    "nl": "nld",  # Neerlandés
    "nn": "nno",  # Noruego Nynorsk
    "no": "nor",  # Noruego
    "nr": "nbl",  # Ndebele meridional
    "nv": "nav",  # Navajo
    "ny": "nya",  # Chichewa
    # O
    "oc": "oci",  # Occitano
    "oj": "oji",  # Ojibwe
    "om": "orm",  # Oromo
    "or": "ori",  # Oriya
    "os": "oss",  # Osetio
    # P
    "pa": "pan",  # Panyabí
    "pi": "pli",  # Pali
    "pl": "pol",  # Polaco
    "ps": "pus",  # Pastún
    "pt": "por",  # Portugués
    # Q
    "qu": "que",  # Quechua
    # R
    "rm": "roh",  # Romanche
    "rn": "run",  # Kirundi
    "ro": "ron",  # Rumano
    "ru": "rus",  # Ruso
    "rw": "kin",  # Kinyarwanda
    # S
    "sa": "san",  # Sánscrito
    "sc": "srd",  # Sardo
    "sd": "snd",  # Sindi
    "se": "sme",  # Sami septentrional
    "sg": "sag",  # Sango
    "si": "sin",  # Cingalés
    "sk": "slk",  # Eslovaco
    "sl": "slv",  # Esloveno
    "sm": "smo",  # Samoano
    "sn": "sna",  # Shona
    "so": "som",  # Somalí
    "sq": "sqi",  # Albanés
    "sr": "srp",  # Serbio
    "ss": "ssw",  # Suati
    "st": "sot",  # Sotho meridional
    "su": "sun",  # Sondanés
    "sv": "swe",  # Sueco
    "sw": "swa",  # Swahili
    # T
    "ta": "tam",  # Tamil
    "te": "tel",  # Telugu
    "tg": "tgk",  # Tayiko
    "th": "tha",  # Tailandés
    "ti": "tir",  # Tigriña
    "tk": "tuk",  # Turcomano
    "tl": "tgl",  # Tagalo
    "tn": "tsn",  # Tswana
    "to": "ton",  # Tongano
    "tr": "tur",  # Turco
    "ts": "tso",  # Tsonga
    "tt": "tat",  # Tártaro
    "tw": "twi",  # Twi
    "ty": "tah",  # Tahitiano
    # U
    "ug": "uig",  # Uigur
    "uk": "ukr",  # Ucraniano
    "ur": "urd",  # Urdu
    "uz": "uzb",  # Uzbeko
    # V
    "va": "val",  # Valenciano (alias ca)
    "ve": "ven",  # Venda
    "vi": "vie",  # Vietnamita
    "vo": "vol",  # Volapük
    # W
    "wa": "wln",  # Valón
    "wo": "wol",  # Wolof
    # X
    "xh": "xho",  # Xhosa
    # Y
    "yi": "yid",  # Yidis
    "yo": "yor",  # Yoruba
    # Z
    "za": "zha",  # Zhuang
    "zh": "cmn",  # Chino mandarín
    "zu": "zul",  # Zulú
}


def resolve_lang(lang_code: str) -> str:
    """Resolver código de idioma al formato ISO 639-3 que usa Allosaurus.

    Soporta:
    - Códigos ISO 639-1 (2 letras): "es" → "spa"
    - Variantes regionales BCP-47: "es-mx" → "spa", "zh-cn" → "cmn"
    - Códigos ISO 639-3 ya correctos (3+ letras): "spa" → "spa" (pasa tal cual)

    Si el código no se reconoce, se devuelve tal cual — Allosaurus aceptará
    el código directamente si ya es 639-3 válido.
    """
    if not lang_code:
        return lang_code

    # Intentar con el código normalizado tal cual (puede ser 639-3 ya)
    normalized = lang_code.lower()
    if normalized in ALLOSAURUS_LANG_MAP:
        return ALLOSAURUS_LANG_MAP[normalized]

    # Extraer prefijo de 2 letras de variantes BCP-47 (ej: "es-mx" → "es")
    prefix = normalized.split("-")[0].split("_")[0]
    if prefix != normalized and prefix in ALLOSAURUS_LANG_MAP:
        return ALLOSAURUS_LANG_MAP[prefix]

    # Devolver tal cual — puede ser ya un código 639-3 válido para Allosaurus
    return lang_code


__all__ = ["ALLOSAURUS_LANG_MAP", "resolve_lang"]
