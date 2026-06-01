import pytest
from pathlib import Path
from scribia.config import _deep_merge, DEFAULT_CONFIG


class TestDeepMerge:
    def test_merge_flat_override(self):
        result = _deep_merge({"a": 1, "b": 2}, {"b": 99})
        assert result["a"] == 1
        assert result["b"] == 99

    def test_merge_nested_dict(self):
        base = {"graphify": {"flags": "--update", "target": "."}}
        override = {"graphify": {"flags": "--no-viz"}}
        result = _deep_merge(base, override)
        assert result["graphify"]["flags"] == "--no-viz"
        assert result["graphify"]["target"] == "."  # preserved

    def test_merge_does_not_mutate_base(self):
        base = {"a": {"b": 1}}
        _deep_merge(base, {"a": {"b": 2}})
        assert base["a"]["b"] == 1

    def test_defaults_include_required_keys(self):
        for key in ("backend", "docs_dir", "changelog", "graphify", "llm_wiki"):
            assert key in DEFAULT_CONFIG
