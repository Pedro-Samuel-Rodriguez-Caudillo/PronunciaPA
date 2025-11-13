"""Comparador basado en distancia de Levenshtein."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ipa_core.ports.compare import Comparator
from ipa_core.types import CompareResult, CompareWeights, EditOp, Token, TokenSeq


@dataclass
class _Weights:
    sub: float = 1.0
    ins: float = 1.0
    del_: float = 1.0

    @classmethod
    def from_dict(cls, weights: Optional[CompareWeights]) -> "_Weights":
        if not weights:
            return cls()
        return cls(
            sub=float(weights.get("sub", 1.0)),
            ins=float(weights.get("ins", 1.0)),
            del_=float(weights.get("del_", 1.0)),
        )


class LevenshteinComparator(Comparator):
    """Calcula PER mediante distancia de Levenshtein con backtracking."""

    def compare(
        self,
        ref: TokenSeq,
        hyp: TokenSeq,
        *,
        weights: Optional[CompareWeights] = None,
        **kw,
    ) -> CompareResult:
        ref_tokens = list(ref)
        hyp_tokens = list(hyp)
        n, m = len(ref_tokens), len(hyp_tokens)
        w = _Weights.from_dict(weights)
        dp = [[0.0] * (m + 1) for _ in range(n + 1)]
        back: list[list[Optional[tuple[str, int, int]]]] = [[None] * (m + 1) for _ in range(n + 1)]

        for i in range(1, n + 1):
            dp[i][0] = i * w.del_
            back[i][0] = ("del", i - 1, 0)
        for j in range(1, m + 1):
            dp[0][j] = j * w.ins
            back[0][j] = ("ins", 0, j - 1)

        for i in range(1, n + 1):
            for j in range(1, m + 1):
                if ref_tokens[i - 1] == hyp_tokens[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                    back[i][j] = ("eq", i - 1, j - 1)
                    continue
                sub_cost = dp[i - 1][j - 1] + w.sub
                ins_cost = dp[i][j - 1] + w.ins
                del_cost = dp[i - 1][j] + w.del_
                best_cost = min(sub_cost, ins_cost, del_cost)
                if best_cost == sub_cost:
                    back[i][j] = ("sub", i - 1, j - 1)
                elif best_cost == ins_cost:
                    back[i][j] = ("ins", i, j - 1)
                else:
                    back[i][j] = ("del", i - 1, j)
                dp[i][j] = best_cost

        ops_reversed: list[EditOp] = []
        alignment_reversed: list[tuple[Optional[Token], Optional[Token]]] = []
        i, j = n, m
        errors = 0
        while i > 0 or j > 0:
            op_info = back[i][j]
            if op_info is None:
                break
            op, pi, pj = op_info
            if op == "eq":
                token_ref = ref_tokens[i - 1]
                token_hyp = hyp_tokens[j - 1]
                ops_reversed.append({"op": "eq", "ref": token_ref, "hyp": token_hyp})
                alignment_reversed.append((token_ref, token_hyp))
            elif op == "sub":
                token_ref = ref_tokens[i - 1]
                token_hyp = hyp_tokens[j - 1]
                ops_reversed.append({"op": "sub", "ref": token_ref, "hyp": token_hyp})
                alignment_reversed.append((token_ref, token_hyp))
                errors += 1
            elif op == "del":
                token_ref = ref_tokens[i - 1]
                ops_reversed.append({"op": "del", "ref": token_ref, "hyp": None})
                alignment_reversed.append((token_ref, None))
                errors += 1
            elif op == "ins":
                token_hyp = hyp_tokens[j - 1]
                ops_reversed.append({"op": "ins", "ref": None, "hyp": token_hyp})
                alignment_reversed.append((None, token_hyp))
                errors += 1
            i, j = pi, pj

        ops = list(reversed(ops_reversed))
        alignment = list(reversed(alignment_reversed))
        per = self._calculate_per(errors, len(ref_tokens), len(hyp_tokens))
        return {"per": per, "ops": ops, "alignment": alignment, "meta": {"distance": dp[n][m]}}

    @staticmethod
    def _calculate_per(errors: int, ref_len: int, hyp_len: int) -> float:
        if ref_len == 0:
            return 0.0 if hyp_len == 0 else 1.0
        return errors / ref_len


__all__ = ["LevenshteinComparator"]
