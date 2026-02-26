# IPA Tokenization Conventions

This document defines how PronunciaPA tokenizes IPA strings into sequences of `Token`
objects (single phoneme strings) throughout the codebase.  It is the authoritative
reference for contributors adding new comparators, backends, or language packs.

---

## 1. What is a token?

A **token** (`ipa_core.types.Token = str`) is the smallest phonological unit recognised
by PronunciaPA.  At phonemic level it corresponds to a single IPA segment; at phonetic
level it may include diacritics or suprasegmentals attached to a base symbol.

```
TokenSeq = list[Token]   # e.g. ["p", "a", "l", "a", "β", "ɾ", "a"]
```

---

## 2. Base tokenization rules

| Rule | Detail |
|------|--------|
| **One segment = one token** | Each base IPA letter plus its directly attached modifiers is a single token. |
| **Tie bar ligatures** | Affricates written with tie bars (t͡ʃ, d͡ʒ) are kept as a single token. The tie bar character U+0361 or U+035C is stripped during normalization and the canonical form is used (see §4). |
| **Diacritics** | Diacritics (nasalization ̃, voicelessness ̥, aspiration ʰ, etc.) attach to their base symbol and are part of the same token when operating in `phonetic` mode. In `phonemic` mode they are usually stripped. |
| **Suprasegmentals** | Stress marks (ˈˌ), length (ː), tone numbers, and syllable boundaries (.) are **removed** before comparison unless the comparator is explicitly configured to retain them. |
| **Whitespace** | Spaces in an IPA string are treated as token delimiters and are themselves discarded. |
| **Unknown symbols** | Any symbol not in the language pack inventory is handled per the OOV policy (`ipa_core/compare/oov_handler.py`): collapse-by-class, mark as `?`, or skip with penalty. |

---

## 3. String → TokenSeq conversion

The primary utility is `ipa_core.normalization`:

```python
from ipa_core.normalization import normalize_ipa, tokenize_ipa

tokens: list[str] = tokenize_ipa("palˈabɾa")
# → ["p", "a", "l", "a", "β", "ɾ", "a"]  (after normalize + split)
```

`tokenize_ipa` applies:
1. Unicode normalization (NFC → NFD where needed).
2. Canonical alias substitution (e.g. `ʦ → ts`, `ʧ → tʃ`).
3. Tie-bar stripping.
4. Suprasegmental removal (configurable).
5. Split on whitespace; non-whitespace multi-codepoint sequences that are valid
   IPA segments are kept intact.

---

## 4. Canonical segment table (frequently confused forms)

| Surface form | Canonical token | Notes |
|---|---|---|
| `t͡ʃ` `tʃ` `ʧ` | `tʃ` | Palato-alveolar affricate |
| `d͡ʒ` `dʒ` `ʤ` | `dʒ` | Voiced palato-alveolar affricate |
| `t͡s` `ts` `ʦ` | `ts` | Alveolar affricate |
| `d͡z` `dz` `ʣ` | `dz` | Voiced alveolar affricate |
| `ɹ` | `ɹ` | English approximant (not `r`) |
| `r` | `r` | Spanish alveolar trill |
| `ɾ` | `ɾ` | Spanish alveolar tap |
| `ʝ` | `ʝ` | Voiced palatal fricative (Spanish /ll/ allophone) |
| `β` | `β` | Voiced bilabial fricative (Spanish /b/ allophone) |
| `ð` | `ð` | Voiced dental fricative |
| `ɣ` | `ɣ` | Voiced velar fricative |

---

## 5. Phonemic vs phonetic level

`mode` controls which inventory is active:

| `mode` | Level | Effect |
|--------|-------|--------|
| `Casual` / `phonemic` | Abstract phonemes | Allophones collapsed (β→b, ð→d, ɣ→g). Diacritics stripped. |
| `Objetivo` / `phonetic` | Allophones allowed | β, ð, ɣ, ɾ/r distinction kept. Aspiration/nasalization diacritics optionally kept. |
| `Fonético` | Full phonetic | All diacritics and allophones preserved as separate tokens. |

The active inventory is provided by the **Language Pack** (`ipa_core/packs/`).  The pack
exposes `canonical_inventory: set[str]` — tokens not in this set are OOV.

---

## 6. Alignment convention

After tokenization, the `Comparator` aligns `ref_tokens` vs `hyp_tokens` using
dynamic programming (`ipa_core/compare/levenshtein.py`).

Each position in the alignment is an `EditOp`:

```python
class EditOp(TypedDict):
    op: Literal["eq", "sub", "ins", "del"]
    ref: Optional[str]   # reference token (None for insertions)
    hyp: Optional[str]   # hypothesis token (None for deletions)
    cost: float          # 0.0 for eq; articulatory distance for sub
```

`alignment: list[tuple[Optional[Token], Optional[Token]]]` mirrors the sequence of
`(ref, hyp)` pairs where `None` represents a gap.

---

## 7. PER definition

$$
\text{PER} = \frac{S + I + D}{N}
$$

Where $S$ = substitutions, $I$ = insertions, $D$ = deletions, $N$ = length of the
reference sequence.  `PER ∈ [0, 1]`; score = $(1 - \text{PER}) \times 100$.

When articulatory weighting is enabled, each substitution cost $c_{sub}$ is the
normalized articulatory distance $d(r, h) \in [0, 1]$ (via `panphon`), so PER
becomes a weighted sum rather than a simple integer count.

---

## 8. OOV handling

See `ipa_core/compare/oov_handler.py` for the full policy.  Short summary:

| Policy | Behaviour |
|--------|-----------|
| `collapse` | Map OOV symbol to nearest in-vocabulary symbol by articulatory distance. |
| `mark` | Keep OOV symbol but colour it gray in the display layer. |
| `skip` | Drop OOV symbol; add a fixed penalty (`oov_penalty`) to the error count. |

The active policy is set per-session via `AppConfig.oov_policy`.

---

## 9. Adding a new language pack

When adding a language/dialect pack (`data/model_packs/` or `ipa_core/packs/`):

1. Define `canonical_inventory` — the set of valid tokens for that language.
2. Provide `alias_map` — surface → canonical normalizations.
3. Provide `allophone_map` — allophone → phoneme collapses for phonemic mode.
4. Run the contract tests in `ipa_core/testing/contracts/` to verify compliance.

---

*Last updated: 2026-02-26*
