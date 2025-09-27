from importlib import metadata

def load_plugin(group: str, name: str):
    for ep in metadata.entry_points().select(group=group):
        if ep.name == name:
            return ep.load()
    raise ValueError(f"Plugin no encontrado: {group}::{name}")

def list_plugins(group: str) -> list[str]:
    return sorted(ep.name for ep in metadata.entry_points().select(group=group))
