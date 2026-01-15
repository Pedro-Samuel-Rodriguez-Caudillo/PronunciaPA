"""LLM runtime adapters."""

from ipa_core.llm.llama_cpp import LlamaCppAdapter
from ipa_core.llm.onnx import OnnxLLMAdapter

__all__ = ["LlamaCppAdapter", "OnnxLLMAdapter"]
