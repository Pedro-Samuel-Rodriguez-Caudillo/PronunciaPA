# PronunciaPA Plugin System

PronunciaPA features a modular architecture that allows extending its functionality through plugins. This includes ASR backends, Text-to-IPA providers, Comparators, and more.

## Plugin Management CLI

You can manage plugins directly from the command line using the `plugin` group of commands.

### List Installed Plugins

To see all currently installed plugins and their status:

```bash
python -m ipa_core.interfaces.cli plugin list
```

The list includes:
- **Category:** The type of plugin (ASR, TEXTREF, etc.)
- **Name:** The unique identifier for the plugin.
- **Version:** The installed version.
- **Status:** `Enabled` if it's the active plugin in your configuration, `Installed` otherwise.

### Get Plugin Details

To see detailed information about a specific plugin:

```bash
python -m ipa_core.interfaces.cli plugin info <category> <name>
```

### Install a Plugin

You can install plugins from PyPI, a local directory, or a Git repository:

```bash
# From PyPI
python -m ipa_core.interfaces.cli plugin install pronunciapa-plugin-allosaurus

# From a local directory
python -m ipa_core.interfaces.cli plugin install ./my-custom-plugin

# From Git
python -m ipa_core.interfaces.cli plugin install git+https://github.com/user/plugin.git
```

### Uninstall a Plugin

To remove a plugin package:

```bash
python -m ipa_core.interfaces.cli plugin uninstall <package-name>
```

*Note: Core packages like `ipa-core` are protected and cannot be uninstalled via this command.*

## Configuration

To enable an installed plugin, update your `configs/local.yaml` (or the config file you are using):

```yaml
backend:
  name: my_new_asr_plugin
  params:
    some_option: value
```

## Developing Plugins

### Architecture Overview

PronunciaPA uses a **microkernel architecture**:
- **Kernel**: Orchestrates the pipeline and validates plugin contracts
- **Plugins**: Extend functionality via entry points

### Plugin Categories and Output Types

| Category | Purpose | Required Output |
|----------|---------|-----------------|
| `asr` | Audio → IPA/Phonemes | **Must declare `output_type`** |
| `textref` | Text → IPA (G2P) | IPA tokens |
| `comparator` | Compare IPA sequences | Error report |
| `preprocessor` | Audio preprocessing | Processed audio |
| `tts` | Text → Speech | Audio |
| `llm` | Exercise generation & feedback | Text (NOT ASR) |

### ASR Plugin Requirements (CRITICAL)

**ASR plugins MUST produce IPA directly, not text.** The kernel validates this.

#### Declaring Output Type

```python
from ipa_core.plugins.base import BasePlugin
from ipa_core.ports.asr import ASRBackend

class MyIPABackend(BasePlugin, ASRBackend):
    """Your ASR backend that produces IPA."""
    
    # REQUIRED: Declare output type
    output_type = "ipa"  # or "text" if legacy/unavoidable
    
    async def transcribe(self, audio: AudioInput, lang: str | None) -> ASRResult:
        # Your implementation here
        # Must return IPA tokens like: ["k", "a", "s", "a"]
        pass
```

#### Output Type Values

- `"ipa"`: Plugin produces IPA/phoneme tokens directly ✅ **RECOMMENDED**
- `"text"`: Plugin produces text (requires G2P, loses allophonic info) ⚠️ **NOT RECOMMENDED**
- `"none"`: Default for non-ASR plugins

#### Kernel Validation

The kernel checks `output_type` when creating the pipeline:

```python
# If your plugin declares output_type="text", the kernel will reject it:
# ValueError: Backend ASR 'my_plugin' produce 'text', no IPA.
#            PronunciaPA requiere backends que produzcan IPA directo.
```

To bypass (NOT recommended), set in config:

```yaml
backend:
  name: my_text_backend
  require_ipa: false  # Disables validation (loses phonetic precision)
```

### Model Acceptance Criteria

| Criterion | Required |
|-----------|----------|
| ASR output | IPA/phoneme tokens (not text) |
| Multilingual | Support multiple languages with one model OR be easily extensible |
| No post-processing | No manual G2P required |
| Offline capable | Run without internet after download |
| Plugin-ready | Integrate via `pronunciapa.plugins` entry point |

### Recommended ASR Models

| Model | Output | Status |
|-------|--------|--------|
| **Allosaurus uni2005** | IPA | ✅ Default, 2000+ languages |
| facebook/wav2vec2-large-xlsr-53-ipa | IPA | ✅ Gated (requires HF token) |
| Custom ONNX IPA models | IPA | ✅ If trained for IPA |
| Wav2Vec2 text variants | Text | ⚠️ NOT recommended |
| Vosk | Text | ⚠️ NOT recommended |
| Whisper | Text | ⚠️ NOT recommended |

### Example Plugin Registration

Plugins are discovered via Python **entry points** in the `pronunciapa.plugins` group.

Example `pyproject.toml` for a plugin:

```toml
[project.entry-points."pronunciapa.plugins"]
"asr.my_ipa_plugin" = "my_module.plugin:MyIPABackend"
"textref.my_g2p" = "my_module.g2p:MyG2PProvider"
"llm.my_llm" = "my_module.llm:MyLLMAdapter"
```

The name must follow the format `category.name`. Supported categories:
- `asr` (MUST declare `output_type = "ipa"`)
- `textref`
- `comparator`
- `preprocessor`
- `tts`
- `llm` (for exercises/feedback, NOT ASR)

### LLM Plugins (TinyLlama, Phi-3)

LLM plugins are for:
1. **Exercise generation**: Generate practice phrases with phonetic variants
2. **Feedback generation**: Provide pedagogical explanations based on error reports

**LLM plugins are NOT used for ASR.** They consume the output of ASR (IPA tokens) and generate text feedback.

Example:

```python
from ipa_core.ports.llm import LLMAdapter

class TinyLlamaAdapter(BasePlugin, LLMAdapter):
    """TinyLlama for exercise generation and feedback."""
    
    async def generate(self, prompt: str) -> str:
        # Call Ollama or local LLM
        return generated_text
```
