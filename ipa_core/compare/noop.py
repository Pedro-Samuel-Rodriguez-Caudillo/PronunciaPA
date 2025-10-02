from ipa_core.compare.base import Comparator, CompareResult


class NoopComparator(Comparator):
    def compare(self, ref_ipa: str, hyp_ipa: str) -> CompareResult:
        # Stub: sin cálculo, PER=0 y sin ops
        return CompareResult(
            per=0.0,
            ops=[],
            total_ref_tokens=0,
            matches=0,
            substitutions=0,
            insertions=0,
            deletions=0,
            per_class={},
        )
