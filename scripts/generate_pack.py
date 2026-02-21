#!/usr/bin/env python3
"""Generador de Language Packs para PronunciaPA.

Pipeline
--------
1. **PHOIBLE** → Descargar inventario fonológico del idioma.
2. **Wiktionary API** → Extraer pronunciaciones IPA de las palabras más
   frecuentes (Wiktionary tiene entradas de muchos idiomas).
3. **eSpeak G2P** → Validar / completar el léxico con el backend offline.
4. Ensamblar el draft YAML listo para revisión manual.

Uso
---
    python scripts/generate_pack.py --lang es --dialect mx
    python scripts/generate_pack.py --lang fr --words 300
    python scripts/generate_pack.py --lang pt --no-wiktionary
    python scripts/generate_pack.py --lang en --output configs/ipa/pack_en-us.yaml

Dependencias opcionales
-----------------------
- ``requests`` — para Wiktionary API y PHOIBLE (con --phoible)
- ``espeak-ng`` / ``espeak`` binario en PATH
- ``pyyaml`` — para serializar el YAML de salida
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Optional
from urllib.parse import quote
from urllib.request import urlopen, Request
from urllib.error import URLError

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

WIKTIONARY_API = "https://en.wiktionary.org/w/api.php"
PHOIBLE_CSV_URL = (
    "https://raw.githubusercontent.com/phoible-dev/phoible/master/data/phoible.csv"
)

# Palabras frecuentes por idioma (base curada — fallback cuando Wiktionary falla)
FREQUENT_WORDS: dict[str, list[str]] = {
    "es": [
        "de", "la", "que", "el", "en", "y", "a", "los", "del", "se",
        "las", "un", "por", "con", "no", "una", "su", "para", "es", "al",
        "lo", "como", "más", "pero", "sus", "le", "ya", "o", "este", "sí",
        "porque", "esta", "entre", "cuando", "muy", "sin", "sobre", "también",
        "me", "hasta", "hay", "donde", "quien", "desde", "todo", "nos",
        "durante", "todos", "uno", "les", "ni", "contra", "otros", "ese",
        "eso", "ante", "ellos", "e", "esto", "mí", "antes", "algunos",
        "qué", "unos", "yo", "otro", "otras", "él", "tanto", "esa",
        "estos", "mucho", "quienes", "nada", "muchos", "cual", "poco",
        "ella", "estar", "estas", "alguno", "alguna", "algo", "nosotros",
        "mi", "mis", "tú", "te", "ti", "tu", "tus", "ellas", "nosotras",
        "vuestros", "vuestras", "os", "mío", "mía", "míos", "mías",
        "hola", "gracias", "por favor", "bien", "mal",
        "agua", "comida", "casa", "trabajo", "tiempo",
        "persona", "hombre", "mujer", "niño", "niña",
        "día", "año", "mes", "semana", "hora",
        "uno", "dos", "tres", "cuatro", "cinco",
    ],
    "en": [
        "the", "be", "to", "of", "and", "a", "in", "that", "have", "it",
        "for", "not", "on", "with", "he", "as", "you", "do", "at", "this",
        "but", "his", "by", "from", "they", "we", "say", "her", "she", "or",
        "an", "will", "my", "one", "all", "would", "there", "their", "what",
        "so", "up", "out", "if", "about", "who", "get", "which", "go", "me",
        "hello", "please", "thank", "good", "bad", "yes", "no",
        "water", "food", "house", "work", "time",
    ],
    "fr": [
        "le", "la", "les", "de", "du", "des", "un", "une", "en", "et",
        "à", "au", "aux", "je", "tu", "il", "elle", "nous", "vous", "ils",
        "que", "qui", "ne", "pas", "sur", "par", "pour", "avec", "dans",
        "bonjour", "merci", "s'il vous plaît", "oui", "non",
        "eau", "nourriture", "maison", "travail", "temps",
    ],
    "pt": [
        "de", "a", "o", "e", "do", "da", "em", "um", "para", "é",
        "com", "uma", "os", "no", "se", "na", "por", "mais", "as", "dos",
        "como", "mas", "foi", "ao", "ele", "das", "tem", "à", "seu", "sua",
        "olá", "obrigado", "por favor", "sim", "não",
        "água", "comida", "casa", "trabalho", "tempo",
    ],
}


# ---------------------------------------------------------------------------
# Helpers de normalización
# ---------------------------------------------------------------------------

_PUNCT_RE = re.compile(r"[^\w\s'-]", re.UNICODE)


def normalize_word(word: str) -> str:
    nfd = unicodedata.normalize("NFD", word)
    return _PUNCT_RE.sub("", nfd.lower()).strip()


def clean_ipa(raw: str) -> str:
    """Limpiar una cadena IPA eliminando marcadores no estándar."""
    # Eliminar / / y [ ]
    raw = re.sub(r"[/\[\]]", "", raw)
    # Eliminar diacríticos de tono de Wiktionary que no usamos
    raw = re.sub(r"[˥˦˧˨˩↗↘]", "", raw)
    return raw.strip()


# ---------------------------------------------------------------------------
# PHOIBLE
# ---------------------------------------------------------------------------

def fetch_phoible_inventory(lang_iso: str) -> list[str]:
    """Obtener inventario fonológico desde PHOIBLE CSV (online).

    Parámetros
    ----------
    lang_iso:
        Código ISO 639-3 del idioma (e.g., "spa" para español, "eng" para inglés).

    Retorna
    -------
    list[str]
        Lista de fonemas del inventario.  Vacía si falla o no se encuentra.
    """
    print(f"  Descargando inventario PHOIBLE para {lang_iso} ...")
    try:
        req = Request(PHOIBLE_CSV_URL, headers={"User-Agent": "PronunciaPA/1.0"})
        with urlopen(req, timeout=30) as resp:
            content = resp.read().decode("utf-8")

        # Parsear CSV simple (evitar dependencia de pandas/csv complejo)
        lines = content.splitlines()
        header = lines[0].split(",")
        try:
            iso_col = header.index("ISO6393")
            phoneme_col = header.index("Phoneme")
        except ValueError:
            print("  [WARN] Formato PHOIBLE CSV inesperado")
            return []

        phonemes: set[str] = set()
        for line in lines[1:]:
            parts = line.split(",")
            if len(parts) <= max(iso_col, phoneme_col):
                continue
            if parts[iso_col].strip('"') == lang_iso:
                ph = parts[phoneme_col].strip().strip('"')
                if ph:
                    phonemes.add(ph)

        result = sorted(phonemes)
        print(f"  [OK] PHOIBLE: {len(result)} fonemas encontrados para {lang_iso}")
        return result

    except (URLError, Exception) as e:
        print(f"  [WARN] No se pudo obtener inventario PHOIBLE: {e}")
        return []


# ---------------------------------------------------------------------------
# Wiktionary API
# ---------------------------------------------------------------------------

def fetch_wiktionary_ipa(word: str, lang_code: str) -> Optional[str]:
    """Obtener transcripción IPA de una palabra desde Wiktionary.

    Usa la API de MediaWiki para obtener el wikitext y extraer el IPA
    con expresiones regulares.

    Parámetros
    ----------
    word:
        Palabra a buscar.
    lang_code:
        Código de idioma de Wiktionary (e.g., "Spanish", "English", "French").

    Retorna
    -------
    str | None
        Cadena IPA limpia, o None si no se encontró.
    """
    params = {
        "action": "query",
        "prop": "revisions",
        "titles": word,
        "rvprop": "content",
        "rvslots": "main",
        "format": "json",
        "formatversion": "2",
    }
    query_str = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
    url = f"{WIKTIONARY_API}?{query_str}"

    try:
        req = Request(url, headers={"User-Agent": "PronunciaPA/1.0"})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        pages = data.get("query", {}).get("pages", [])
        if not pages:
            return None

        content = pages[0].get("revisions", [{}])[0].get("slots", {}).get("main", {}).get("content", "")

        # Buscar sección del idioma correcto
        lang_section_re = re.compile(
            r"==\s*" + re.escape(lang_code) + r"\s*==.*?(?===\s*\w|\Z)",
            re.DOTALL,
        )
        m = lang_section_re.search(content)
        section = m.group(0) if m else content

        # Extraer IPA del template {{IPA|...}} o {{IPAchar|...}}
        ipa_re = re.compile(r"\{\{IPA(?:char)?\|([^}|]+)")
        matches = ipa_re.findall(section)
        if matches:
            return clean_ipa(matches[0])

        # Intento alternativo: buscar /.../ directamente
        slash_re = re.compile(r"/([^/\n]{1,40})/")
        m2 = slash_re.search(section)
        if m2:
            return clean_ipa(m2.group(1))

        return None

    except Exception:
        return None


# ---------------------------------------------------------------------------
# eSpeak G2P
# ---------------------------------------------------------------------------

def espeak_to_ipa(word: str, lang: str) -> Optional[str]:
    """Obtener IPA de una palabra usando eSpeak-NG.

    Parámetros
    ----------
    word:
        Palabra a transcribir.
    lang:
        Código de idioma para eSpeak (e.g., "es", "en", "fr").

    Retorna
    -------
    str | None
        Cadena IPA, o None si eSpeak no está disponible.
    """
    binary = shutil.which("espeak-ng") or shutil.which("espeak")
    if not binary:
        return None

    try:
        result = subprocess.run(
            [binary, "-q", "-v", lang, "--ipa=3", word],
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = result.stdout.strip()
        if output:
            return clean_ipa(output)
    except (subprocess.TimeoutExpired, OSError):
        pass

    return None


# ---------------------------------------------------------------------------
# Builder de léxico
# ---------------------------------------------------------------------------

def build_lexicon(
    words: list[str],
    lang: str,
    lang_name_wiki: str,
    *,
    use_wiktionary: bool = True,
    use_espeak: bool = True,
    verbose: bool = False,
) -> dict[str, str]:
    """Construir léxico {palabra: IPA} usando Wiktionary + eSpeak.

    Estrategia por palabra:
    1. Wiktionary (curado por humanos).
    2. eSpeak G2P (fallback automático).
    3. Si ninguno funciona → omitir.

    Parámetros
    ----------
    words:
        Lista de palabras a transcribir.
    lang:
        Código de idioma para eSpeak.
    lang_name_wiki:
        Nombre del idioma en Wiktionary (e.g., "Spanish", "English").
    use_wiktionary:
        Si buscar en Wiktionary.
    use_espeak:
        Si usar eSpeak como fallback.
    verbose:
        Mostrar progreso por palabra.

    Retorna
    -------
    dict[str, str]
        Diccionario {palabra_normalizada: IPA}.
    """
    lexicon: dict[str, str] = {}
    total = len(words)

    for i, word in enumerate(words, 1):
        key = normalize_word(word)
        if not key or key in lexicon:
            continue

        ipa: Optional[str] = None
        source = "none"

        if use_wiktionary:
            ipa = fetch_wiktionary_ipa(word, lang_name_wiki)
            if ipa:
                source = "wiktionary"

        if not ipa and use_espeak:
            ipa = espeak_to_ipa(word, lang)
            if ipa:
                source = "espeak"

        if ipa:
            lexicon[key] = ipa
            if verbose:
                print(f"  [{i}/{total}] {key!r} → {ipa!r}  ({source})")
        else:
            if verbose:
                print(f"  [{i}/{total}] {key!r} → (no encontrado)")

        # Progreso silencioso
        if not verbose and i % 50 == 0:
            print(f"  Procesadas {i}/{total} palabras ({len(lexicon)} con IPA)...")

    return lexicon


# ---------------------------------------------------------------------------
# Serializador YAML manual (evitar dependencia de ruamel.yaml/PyYAML)
# ---------------------------------------------------------------------------

def _yaml_str(s: str) -> str:
    """Serializar string YAML escapando caracteres especiales."""
    if any(c in s for c in (':', '#', '[', ']', '{', '}', '&', '*', '!', '|', '>', "'", '"', '\n')):
        escaped = s.replace('"', '\\"')
        return f'"{escaped}"'
    return s


def dict_to_yaml_block(d: dict, indent: int = 0) -> str:
    """Serializar dict a bloque YAML con indentación."""
    lines = []
    prefix = "  " * indent
    for k, v in d.items():
        if isinstance(v, dict):
            lines.append(f"{prefix}{_yaml_str(str(k))}:")
            lines.append(dict_to_yaml_block(v, indent + 1))
        elif isinstance(v, list):
            lines.append(f"{prefix}{_yaml_str(str(k))}:")
            for item in v:
                lines.append(f"{prefix}  - {_yaml_str(str(item))}")
        elif isinstance(v, str):
            lines.append(f"{prefix}{_yaml_str(str(k))}: {_yaml_str(v)}")
        else:
            lines.append(f"{prefix}{_yaml_str(str(k))}: {v}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Función principal de generación
# ---------------------------------------------------------------------------

def generate_pack(
    lang: str,
    dialect: Optional[str],
    words: list[str],
    phoible_inventory: list[str],
    *,
    use_wiktionary: bool,
    use_espeak: bool,
    verbose: bool,
) -> str:
    """Generar el YAML del pack completo."""
    lang_name_map = {
        "es": "Spanish",
        "en": "English",
        "fr": "French",
        "pt": "Portuguese",
        "de": "German",
        "it": "Italian",
        "ja": "Japanese",
        "zh": "Chinese",
    }
    lang_name_wiki = lang_name_map.get(lang, lang.capitalize())

    print(f"\n  Construyendo léxico para {lang_name_wiki} ({len(words)} palabras) ...")
    lexicon = build_lexicon(
        words,
        lang,
        lang_name_wiki,
        use_wiktionary=use_wiktionary,
        use_espeak=use_espeak,
        verbose=verbose,
    )
    print(f"  Léxico generado: {len(lexicon)} entradas con IPA.")

    dialect_str = dialect or ""
    pack_id = f"{lang}-{dialect_str}-v1" if dialect_str else f"{lang}-v1"

    # Inventario: usar PHOIBLE si está disponible, sino placeholder
    if phoible_inventory:
        consonants = [p for p in phoible_inventory if p.isascii() or len(p) == 1]
        vowels = [p for p in phoible_inventory if p not in consonants]
    else:
        consonants = []
        vowels = []

    lines = [
        f"# Language Pack generado por PronunciaPA generate_pack.py",
        f"# Idioma: {lang_name_wiki}  Dialecto: {dialect_str or 'estándar'}",
        f"# REVISAR antes de usar en producción.",
        f"",
        f"schema_version: 1",
        f"id: {pack_id}",
        f'version: "1.0.0"',
        f"language: {lang}",
    ]
    if dialect_str:
        lines.append(f"dialect: {dialect_str}")
    lines += [
        f"description: >",
        f"  Pack generado automáticamente para {lang_name_wiki}.",
        f"  Léxico: {len(lexicon)} palabras. Revisar pronunciaciones antes de publicar.",
        f"license: CC-BY-4.0",
        f"",
        f"sources:",
        f"  - name: Wiktionary",
        f"    url: https://en.wiktionary.org",
        f"    license: CC-BY-SA-4.0",
        f"  - name: eSpeak-NG",
        f"    url: https://github.com/espeak-ng/espeak-ng",
        f"    license: GPL-3.0",
    ]
    if phoible_inventory:
        lines += [
            f"  - name: PHOIBLE",
            f"    url: https://phoible.org",
            f"    license: CC-BY-4.0",
        ]
    lines += [
        f"",
        f"inventory:",
        f"  path: inventory_{lang}-{dialect_str or 'default'}.yaml",
        f"  format: yaml",
        f"  required: false",
        f"",
        f"lexicon:",
        f"  path: lexicon_{lang}-{dialect_str or 'default'}.yaml",
        f"  format: yaml",
        f"  required: false",
        f"",
        f"error_weights:",
        f"  semantic: 1.0",
        f"  frequency: 1.0",
        f"  articulatory: 1.0",
        f"",
        f"# Léxico inline generado ({len(lexicon)} entradas)",
        f"inline_lexicon:",
    ]

    for word, ipa in sorted(lexicon.items()):
        lines.append(f"  {_yaml_str(word)}: {_yaml_str(ipa)}")

    lines += [
        f"",
        f"modes:",
        f"  - id: casual",
        f"    description: Modo permisivo",
        f"    allow_variants: true",
        f"    scoring_profile: casual",
        f"  - id: objective",
        f"    description: Modo equilibrado",
        f"    allow_variants: true",
        f"    scoring_profile: objective",
        f"  - id: phonetic",
        f"    description: Modo estricto",
        f"    allow_variants: false",
        f"    scoring_profile: phonetic",
    ]

    if phoible_inventory:
        lines += [
            f"",
            f"# Inventario PHOIBLE (referencia)",
            f"# consonants: {consonants[:10]}{'...' if len(consonants) > 10 else ''}",
            f"# vowels: {vowels[:10]}{'...' if len(vowels) > 10 else ''}",
        ]

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generador de Language Packs para PronunciaPA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--lang", default="es", help="Código ISO 639-1 del idioma (default: es)")
    parser.add_argument("--dialect", default=None, help="Código de dialecto (e.g., mx, us)")
    parser.add_argument(
        "--words", type=int, default=200,
        help="Número de palabras frecuentes a incluir (default: 200)",
    )
    parser.add_argument("--no-wiktionary", action="store_true", help="No usar Wiktionary API")
    parser.add_argument("--no-espeak", action="store_true", help="No usar eSpeak como fallback")
    parser.add_argument("--phoible", action="store_true", help="Intentar obtener inventario de PHOIBLE")
    parser.add_argument(
        "--output", default=None,
        help="Ruta de salida del YAML (default: configs/ipa/pack_{lang}-{dialect}.yaml)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Mostrar progreso por palabra")
    args = parser.parse_args()

    print("=" * 70)
    print("  PronunciaPA — Generador de Language Packs")
    print("=" * 70)
    print(f"  Idioma: {args.lang}  Dialecto: {args.dialect or 'default'}")
    print(f"  Palabras: {args.words}")
    print(f"  Wiktionary: {'no' if args.no_wiktionary else 'sí'}")
    print(f"  eSpeak: {'no' if args.no_espeak else 'sí'}")

    # Palabras base
    base_words = FREQUENT_WORDS.get(args.lang, [])
    if len(base_words) < args.words:
        # Rellenar con palabras genéricas numeradas si no hay suficientes
        print(f"  [WARN] Solo hay {len(base_words)} palabras frecuentes precargadas para '{args.lang}'.")
    words = base_words[: args.words]

    # Inventario PHOIBLE (opcional)
    phoible_inv: list[str] = []
    if args.phoible:
        iso3_map = {"es": "spa", "en": "eng", "fr": "fra", "pt": "por", "de": "deu"}
        iso3 = iso3_map.get(args.lang, args.lang)
        phoible_inv = fetch_phoible_inventory(iso3)

    # Generar pack
    yaml_content = generate_pack(
        args.lang,
        args.dialect,
        words,
        phoible_inv,
        use_wiktionary=not args.no_wiktionary,
        use_espeak=not args.no_espeak,
        verbose=args.verbose,
    )

    # Determinar salida
    if args.output:
        out_path = Path(args.output)
    else:
        suffix = f"-{args.dialect}" if args.dialect else ""
        out_path = ROOT / "configs" / "ipa" / f"pack_{args.lang}{suffix}.yaml"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(yaml_content, encoding="utf-8")

    print(f"\n  [OK] Pack generado: {out_path}")
    print(f"  Revisa el archivo antes de usarlo en producción.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
