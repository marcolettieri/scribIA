from __future__ import annotations

from pathlib import Path

try:
    import yaml  # pyyaml

    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

DEFAULT_CONFIG: dict = {
    "backend": "markdown",
    "knowledge_backends": [],
    "docs_dir": "docs",
    "changelog": "CHANGELOG.md",
    "language": "en",
    "update_mode": "manual",
    "exclude_patterns": ["test_*", "*.test.ts", "*.spec.*"],
    "graphify": {
        "enabled": False,
        "flags": "--update --wiki --no-viz",
        "target_path": ".",
    },
    "llm_wiki": {
        "enabled": False,
        "output_dir": "wiki",
    },
}

_SEARCH_PATHS = [
    Path("scribia.yaml"),
    Path("scribia.yml"),
    Path(".scribia/config.yaml"),
    Path.home() / ".scribia.yaml",
    Path("autodoc.yaml"),  # legacy name
]


def load_config() -> dict:
    for path in _SEARCH_PATHS:
        if path.exists():
            user = _read_yaml(path)
            return _deep_merge(DEFAULT_CONFIG, user)
    return dict(DEFAULT_CONFIG)


def _read_yaml(path: Path) -> dict:
    if not _HAS_YAML:
        raise RuntimeError("pyyaml is required to read autodoc.yaml. Run: pip install pyyaml")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
