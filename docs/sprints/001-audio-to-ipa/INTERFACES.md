# Interfaces

Entradas
- AudioInput: {path, sample_rate, channels}
- lang: es|en|...

Salidas
- tokens: list[str] (IPA)
- cadena IPA: ' '.join(tokens)

Errores comunes
- FileNotFound, UnsupportedFormat (ver ipa_core/errors.py)
