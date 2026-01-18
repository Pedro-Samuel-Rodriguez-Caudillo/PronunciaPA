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

Plugins are discovered via Python **entry points** in the `pronunciapa.plugins` group.

Example `pyproject.toml` for a plugin:

```toml
[project.entry-points."pronunciapa.plugins"]
"asr.my_plugin" = "my_module.plugin:MyASRClass"
```

The name must follow the format `category.name`. Supported categories:
- `asr`
- `textref`
- `comparator`
- `preprocessor`
- `tts`
- `llm`
