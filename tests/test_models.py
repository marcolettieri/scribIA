import json

from scribia.engine.models import ChangeSet, ChangeType, EntityType, FileChange, SemanticEntity


def _make_changeset(**kwargs) -> ChangeSet:
    defaults = dict(from_commit="abc1234", to_commit="def5678", timestamp="2026-01-01T00:00:00Z")
    return ChangeSet(**{**defaults, **kwargs})


class TestFileChange:
    def test_is_significant_above_threshold(self):
        fc = FileChange(path="a.py", change_type=ChangeType.ADDED, additions=3, deletions=0)
        assert fc.is_significant()

    def test_is_significant_below_threshold(self):
        fc = FileChange(path="a.py", change_type=ChangeType.MODIFIED, additions=1, deletions=1)
        assert not fc.is_significant()

    def test_to_dict_contains_required_keys(self):
        fc = FileChange(path="a.py", change_type=ChangeType.MODIFIED, additions=5, deletions=2)
        d = fc.to_dict()
        assert d["path"] == "a.py"
        assert d["change_type"] == "modified"
        assert d["additions"] == 5
        assert d["deletions"] == 2
        assert d["old_path"] is None


class TestSemanticEntity:
    def test_to_dict_all_fields(self):
        e = SemanticEntity(
            name="MyClass",
            entity_type=EntityType.CLASS,
            change_type=ChangeType.ADDED,
            file_path="src/mymodule.py",
            description="A test class",
            metadata={"matched_line": "class MyClass:"},
        )
        d = e.to_dict()
        assert d["name"] == "MyClass"
        assert d["entity_type"] == "class"
        assert d["change_type"] == "added"
        assert d["description"] == "A test class"


class TestChangeSet:
    def test_has_changes_empty(self):
        cs = _make_changeset()
        assert not cs.has_changes()

    def test_has_changes_with_files(self):
        fc = FileChange(path="a.py", change_type=ChangeType.ADDED, additions=10)
        cs = _make_changeset(file_changes=[fc])
        assert cs.has_changes()

    def test_significant_changes_filters_noise(self):
        small = FileChange(path="a.py", change_type=ChangeType.MODIFIED, additions=1, deletions=1)
        big = FileChange(path="b.py", change_type=ChangeType.MODIFIED, additions=10, deletions=2)
        cs = _make_changeset(file_changes=[small, big])
        sig = cs.significant_changes()
        assert len(sig) == 1
        assert sig[0].path == "b.py"

    def test_to_json_is_valid(self):
        fc = FileChange(path="a.py", change_type=ChangeType.ADDED, additions=5)
        cs = _make_changeset(file_changes=[fc])
        parsed = json.loads(cs.to_json())
        assert parsed["from_commit"] == "abc1234"
        assert len(parsed["file_changes"]) == 1

    def test_to_dict_round_trips_entities(self):
        e = SemanticEntity(
            name="get_user",
            entity_type=EntityType.FUNCTION,
            change_type=ChangeType.ADDED,
            file_path="api.py",
        )
        cs = _make_changeset(semantic_entities=[e])
        d = cs.to_dict()
        assert d["semantic_entities"][0]["name"] == "get_user"
