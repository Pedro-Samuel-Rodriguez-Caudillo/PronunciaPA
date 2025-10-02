"""Comparador basado en algoritmo de Levenshtein/Needleman-Wunsch."""

from typing import Callable, Dict, List, Optional

from .base import AlignmentOp, CompareResult, Comparator, PhonemeStats

Operation = str

MATCH: Operation = "match"
SUBSTITUTION: Operation = "substitution"
INSERTION: Operation = "insertion"
DELETION: Operation = "deletion"


def _default_token_normalizer(token: str) -> str:
    """Normaliza tokens IPA removiendo espacios extra."""

    return token.strip()


def _default_tokenizer(text: str) -> List[str]:
    if text is None:
        return []
    tokens = [t for t in text.strip().split() if t]
    return [_default_token_normalizer(t) for t in tokens]


class LevenshteinComparator(Comparator):
    """Implementación del comparador clásico de distancia de edición."""

    def __init__(
        self,
        tokenizer: Optional[Callable[[str], List[str]]] = None,
        normalizer: Optional[Callable[[str], str]] = None,
    ) -> None:
        self._tokenizer = tokenizer or _default_tokenizer
        self._normalizer = normalizer or _default_token_normalizer

    def compare(self, ref_ipa: str, hyp_ipa: str) -> CompareResult:
        ref_tokens = [self._normalizer(tok) for tok in self._tokenizer(ref_ipa)]
        hyp_tokens = [self._normalizer(tok) for tok in self._tokenizer(hyp_ipa)]

        ops = self._align(ref_tokens, hyp_tokens)
        return self._build_result(ref_tokens, ops)

    def _align(self, ref_tokens: List[str], hyp_tokens: List[str]) -> List[AlignmentOp]:
        n = len(ref_tokens)
        m = len(hyp_tokens)
        dp: List[List[int]] = [[0] * (m + 1) for _ in range(n + 1)]
        backtrack: List[List[Optional[str]]] = [[None] * (m + 1) for _ in range(n + 1)]

        for i in range(1, n + 1):
            dp[i][0] = i
            backtrack[i][0] = DELETION
        for j in range(1, m + 1):
            dp[0][j] = j
            backtrack[0][j] = INSERTION

        for i in range(1, n + 1):
            for j in range(1, m + 1):
                if ref_tokens[i - 1] == hyp_tokens[j - 1]:
                    cost_sub = dp[i - 1][j - 1]
                else:
                    cost_sub = dp[i - 1][j - 1] + 1
                cost_del = dp[i - 1][j] + 1
                cost_ins = dp[i][j - 1] + 1

                min_cost = min(cost_sub, cost_del, cost_ins)
                dp[i][j] = min_cost
                if min_cost == cost_sub:
                    backtrack[i][j] = MATCH if ref_tokens[i - 1] == hyp_tokens[j - 1] else SUBSTITUTION
                elif min_cost == cost_del:
                    backtrack[i][j] = DELETION
                else:
                    backtrack[i][j] = INSERTION

        ops: List[AlignmentOp] = []
        i, j = n, m
        while i > 0 or j > 0:
            action = backtrack[i][j]
            if action in (MATCH, SUBSTITUTION):
                ref_tok = ref_tokens[i - 1] if i > 0 else ""
                hyp_tok = hyp_tokens[j - 1] if j > 0 else ""
                ops.append((action, ref_tok, hyp_tok))
                i -= 1
                j -= 1
            elif action == DELETION:
                ref_tok = ref_tokens[i - 1] if i > 0 else ""
                ops.append((DELETION, ref_tok, ""))
                i -= 1
            elif action == INSERTION:
                hyp_tok = hyp_tokens[j - 1] if j > 0 else ""
                ops.append((INSERTION, "", hyp_tok))
                j -= 1
            else:
                # Only possible when both i and j are zero.
                break

        ops.reverse()
        return ops

    def _build_result(self, ref_tokens: List[str], ops: List[AlignmentOp]) -> CompareResult:
        total_ref = len(ref_tokens)
        matches = sum(1 for op, _, _ in ops if op == MATCH)
        substitutions = sum(1 for op, _, _ in ops if op == SUBSTITUTION)
        insertions = sum(1 for op, _, _ in ops if op == INSERTION)
        deletions = sum(1 for op, _, _ in ops if op == DELETION)

        per = 0.0 if total_ref == 0 else (substitutions + insertions + deletions) / total_ref

        per_class: Dict[str, PhonemeStats] = {}
        for op, ref_tok, hyp_tok in ops:
            if op == INSERTION:
                key = f"+{hyp_tok}" if hyp_tok else "<ins>"
            else:
                key = ref_tok if ref_tok else "<eps>"
            stats = per_class.setdefault(key, PhonemeStats())
            if op == MATCH:
                stats.matches += 1
            elif op == SUBSTITUTION:
                stats.substitutions += 1
            elif op == INSERTION:
                stats.insertions += 1
            elif op == DELETION:
                stats.deletions += 1

        return CompareResult(
            per=per,
            ops=ops,
            total_ref_tokens=total_ref,
            matches=matches,
            substitutions=substitutions,
            insertions=insertions,
            deletions=deletions,
            per_class=per_class,
        )


__all__ = [
    "LevenshteinComparator",
    "MATCH",
    "SUBSTITUTION",
    "INSERTION",
    "DELETION",
]
