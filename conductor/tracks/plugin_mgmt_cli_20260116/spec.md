# Specification: Plugin Management CLI

## Overview
Implement a set of commands within the main `pronunciapa` CLI to manage phonetic plugins (ASR, TTS, etc.). This utilizes Python's `importlib.metadata` for discovery, allowing plugins to be installed as standard packages.

## Functional Requirements
- **Integration:** Commands must be subcommands of the main CLI (e.g., `pronunciapa plugins <command>`).
- **List Command (`list`):**
    - Retrieve and display all installed `pronunciapa` plugins.
    - Show Name, Version, Plugin Type, and Status (Enabled/Disabled).
- **Install Command (`install`):**
    - Accept a package name, local path, or Git URL.
    - Use `pip` programmatically or via subprocess to install the package.
- **Uninstall Command (`uninstall`):**
    - Remove the specified plugin package.
- **Info Command (`info`):**
    - Display detailed metadata: Description, Author, Requirements, and precise Entry Point configuration.
- **Status Management:**
    - Identify if a plugin is "Enabled" based on the project's configuration (e.g., `configs/local.yaml`).

## Non-Functional Requirements
- **Robustness:** Gracefully handle failed installations (e.g., network errors, missing dependencies).
- **Consistency:** Use the project's existing CLI framework (likely `click` or `argparse`, to be verified).
- **Feedback:** Provide clear progress messages during installation/uninstallation.

## Acceptance Criteria
- [ ] `pronunciapa plugins list` shows the "Allosaurus" plugin (if installed).
- [ ] `pronunciapa plugins install <path>` successfully installs a local dummy plugin.
- [ ] `pronunciapa plugins info <name>` displays the correct version and type.
- [ ] `pronunciapa plugins uninstall <name>` removes the plugin from the system.

## Out of Scope
- A central "Plugin Store" UI or search command.
- Automatic updates for plugins.
