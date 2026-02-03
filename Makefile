.PHONY: test-unit test-int sync-types

test-unit:
	PRONUNCIAPA_ASR=stub PYTHONPATH=. pytest \
		ipa_core/audio/tests/test_files.py \
		ipa_core/compare/tests/test_levenshtein.py \
		ipa_core/pipeline/tests/test_runner.py \
		ipa_core/textref/tests/test_epitran_provider.py \
		ipa_core/textref/tests/test_espeak_provider.py \
		ipa_core/services/tests/test_transcription_service.py \
		tests/utils

test-int:
	PRONUNCIAPA_ASR=stub PYTHONPATH=. pytest \
		ipa_core/api/tests/test_http_transcription.py \
		scripts/tests/test_cli_transcribe_stub.py \
		scripts/tests/test_cli_transcribe_errors.py

sync-types:
	@echo "🔄 Synchronizing TypeScript API types from OpenAPI schema..."
	python scripts/sync_api_types.py
	@echo "✅ Type synchronization complete"
