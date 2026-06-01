from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path

from .base import BackendPlugin

BUILTIN_BACKENDS: dict[str, str] = {
    "markdown": "scribia.backends.markdown.MarkdownBackend",
    "graphify": "scribia.backends.graphify.GraphifyBackend",
    "llm_wiki": "scribia.backends.llm_wiki.LLMWikiBackend",
}

_DEFAULT_PLUGIN_DIR = Path("plugins")


def load_backend(name: str, plugin_dirs: list[Path] | None = None) -> BackendPlugin:
    """
    Resolve a backend by name.

    Resolution order:
      1. Built-in backends (see BUILTIN_BACKENDS)
      2. Python files in plugin_dirs (default: ./plugins/)
    """
    if name in BUILTIN_BACKENDS:
        module_path, class_name = BUILTIN_BACKENDS[name].rsplit(".", 1)
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        return cls()

    search_dirs = plugin_dirs or [_DEFAULT_PLUGIN_DIR]
    for plugin_dir in search_dirs:
        for candidate in plugin_dir.glob("*.py"):
            if candidate.stem.startswith("_"):
                continue
            spec = importlib.util.spec_from_file_location(f"_plugin_{candidate.stem}", candidate)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore[union-attr]
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BackendPlugin)
                    and attr is not BackendPlugin
                    and getattr(attr, "name", None) == name
                ):
                    return attr()

    available = list(BUILTIN_BACKENDS.keys())
    raise ValueError(
        f"Backend '{name}' not found. Built-ins: {available}. "
        "Add a plugin file to plugins/ with a class whose `name` attribute matches."
    )


def list_available(plugin_dirs: list[Path] | None = None) -> dict[str, str]:
    """Return {name: source} for all discoverable backends."""
    result: dict[str, str] = {n: "built-in" for n in BUILTIN_BACKENDS}
    for plugin_dir in (plugin_dirs or [_DEFAULT_PLUGIN_DIR]):
        if not plugin_dir.exists():
            continue
        for candidate in plugin_dir.glob("*.py"):
            if candidate.stem.startswith("_"):
                continue
            result[candidate.stem] = str(candidate)
    return result
