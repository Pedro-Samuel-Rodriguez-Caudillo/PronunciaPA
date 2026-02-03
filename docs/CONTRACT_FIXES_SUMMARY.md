# Contract/Interface Fixes - Implementation Summary

## Overview
Fixed critical bugs and inconsistencies in contracts and interfaces between microkernel layers:
- Core ports (ASR, TextRef, Comparator, Preprocessor, LLM, TTS)
- Backend implementations
- API server models
- Frontend TypeScript types

## Changes Implemented

### 1. Alignment Type Unification ✅

**Problem**: Mismatch between internal `tuple` type and API `List[List[...]]`

**Files Changed**:
- `ipa_server/models.py`: Changed `alignment` from `List[List[Optional[str]]]` to `List[Tuple[Optional[str], Optional[str]]]`
- `ipa_server/main.py`: Added conversion `[list(pair) for pair in res.get("alignment", [])]` for JSON serialization

**Impact**: API now correctly reflects internal types, preventing serialization errors

### 2. ComparisonResult.to_dict() Method ✅

**Problem**: Two parallel result types without conversion between them

**Files Changed**:
- `ipa_core/phonology/representation.py`: Added `to_dict()` method to `ComparisonResult`

**Implementation**:
```python
def to_dict(self) -> dict:
    """Convert to CompareResult-compatible dict for API responses."""
    return {
        "per": self.distance / max(len(self.target.segments), 1),
        "ops": self.operations,
        "alignment": [...],
        "meta": {...},
    }
```

**Impact**: Seamless conversion between rich `ComparisonResult` and simple `CompareResult` for JSON APIs

### 3. ASR Backend output_type Formalization ✅

**Problem**: `output_type` documented but not enforced in Protocol

**Files Changed**:
- `ipa_core/ports/asr.py`: Added `output_type: str` as class attribute in Protocol

**Impact**: Static type checking now verifies all ASR backends declare their output type

### 4. Optional lang Parameter ✅

**Problem**: Inconsistent `lang` requirements across TextRef implementations

**Files Changed**:
- `ipa_core/ports/textref.py`: Changed `lang: str` to `lang: Optional[str] = None`
- `ipa_core/textref/espeak.py`: Updated to accept `Optional[str]`
- `ipa_core/textref/simple.py`: Updated to accept `Optional[str]`
- `ipa_core/textref/epitran.py`: Updated to accept `Optional[str]`

**Behavior**: All implementations fall back to `default_lang` when `lang=None`

### 5. Extended Contract Tests ✅

**Files Changed**:
- `ipa_core/ports/tests/test_ports_contracts.py`: Added 3 new tests

**New Tests**:
1. `test_asr_backend_output_type()`: Verifies registered backends have valid `output_type`
2. `test_compare_result_types()`: Validates `CompareResult` structure and types
3. `test_comparison_result_to_dict()`: Tests `ComparisonResult.to_dict()` compatibility

**Results**: All 10 tests pass ✅

### 6. Type Synchronization Infrastructure ✅

**Files Created**:
- `scripts/sync_api_types.py`: Automated TypeScript generation from OpenAPI schema

**Files Modified**:
- `Makefile`: Added `make sync-types` target
- `frontend/package.json`: Added `openapi-typescript` dev dependency and `sync-types` script

**Usage**:
```bash
# Backend
make sync-types

# Frontend
npm run sync-types
```

**Impact**: Single source of truth (backend Pydantic models) auto-generates frontend types

### 7. CI Type Verification ✅

**Files Changed**:
- `.github/workflows/ci.yml`: Added `verify-api-types` job

**CI Workflow**:
1. Starts FastAPI server
2. Fetches OpenAPI schema
3. Generates TypeScript types
4. Fails if generated types differ from committed types

**Impact**: Prevents API/frontend type drift in PRs

## Testing

### Contract Tests
```bash
pytest ipa_core/ports/tests/test_ports_contracts.py -v
# Result: 10 passed in 21.85s ✅
```

### Manual Verification
- ✅ Alignment conversion: `tuple` → `list` for JSON
- ✅ ComparisonResult.to_dict() produces valid CompareResult
- ✅ Optional lang parameter with fallback
- ✅ Models validate correctly with Pydantic

## Migration Notes

### For Backend Developers
- All TextRef implementations must now accept `lang: Optional[str] = None`
- Use `lang or self._default_lang` pattern for fallback
- ASR backends should explicitly declare `output_type = "ipa"` as class attribute

### For API Consumers
- `alignment` field is now correctly typed as `Array<[string | null, string | null]>` in TypeScript
- Run `npm run sync-types` after pulling API changes to update frontend types

### For CI/CD
- New `verify-api-types` job ensures types stay synchronized
- PRs will fail if API changes without regenerating frontend types
- Fix: Run `make sync-types` and commit updated `api.ts`

## Architecture Impact

### Maintained Separation
✅ Both `CompareResult` (simple TypedDict) and `ComparisonResult` (rich dataclass) coexist
- `CompareResult`: JSON-serializable, used in HTTP APIs
- `ComparisonResult`: Rich domain model with PhonologicalRepresentation

### Enhanced Type Safety
✅ Protocol attributes now formally declared
✅ Runtime and static type checking aligned
✅ Frontend types auto-generated from single source of truth

## Future Recommendations

1. **Pre-commit Hook** (Optional): Auto-generate types locally before commit
   - Pro: Prevents forgetting to sync
   - Con: Adds friction to development workflow
   - **Decision**: CI-only verification (current implementation)

2. **Versioned API Contracts**: Consider API versioning strategy if breaking changes needed
   - Current: Single evolving contract
   - Future: `/v1/`, `/v2/` with separate type files

3. **OpenAPI Schema Validation**: Add pytest that validates server matches committed schema
   - Complements frontend type check
   - Catches schema drift before deployment

## Files Modified

**Core Contracts (5 files)**:
- ipa_core/ports/asr.py
- ipa_core/ports/textref.py
- ipa_core/phonology/representation.py
- ipa_core/types.py (docs only)

**Implementations (3 files)**:
- ipa_core/textref/espeak.py
- ipa_core/textref/simple.py
- ipa_core/textref/epitran.py

**API Layer (2 files)**:
- ipa_server/models.py
- ipa_server/main.py

**Testing (1 file)**:
- ipa_core/ports/tests/test_ports_contracts.py

**Infrastructure (4 files)**:
- scripts/sync_api_types.py (new)
- Makefile
- frontend/package.json
- .github/workflows/ci.yml

**Total**: 15 files modified, 1 new script

## Verification Commands

```bash
# Test contracts
pytest ipa_core/ports/tests/test_ports_contracts.py -v

# Sync types manually
make sync-types

# Verify models load
python -c "from ipa_server.models import CompareResponse; print(CompareResponse.model_fields['alignment'].annotation)"

# Check alignment conversion
python scripts/test_alignment_fix.py

# Check optional lang
python scripts/test_optional_lang.py
```

All verifications pass ✅
