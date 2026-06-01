from scribia.engine.analyzer import SemanticAnalyzer
from scribia.engine.models import ChangeSet, ChangeType, EntityType, FileChange


def _make_file_change(path: str, diff: str, additions: int = 10) -> FileChange:
    return FileChange(
        path=path,
        change_type=ChangeType.ADDED,
        additions=additions,
        deletions=0,
        diff_content=diff,
    )


def _make_changeset(*file_changes: FileChange) -> ChangeSet:
    return ChangeSet(
        from_commit="aaa",
        to_commit="bbb",
        timestamp="2026-01-01T00:00:00Z",
        file_changes=list(file_changes),
    )


class TestSemanticAnalyzer:
    analyzer = SemanticAnalyzer()

    def test_detects_python_class(self):
        fc = _make_file_change(
            "mymodule.py",
            "+class UserService:\n+    pass\n",
        )
        cs = self.analyzer.analyze(_make_changeset(fc))
        names = [e.name for e in cs.semantic_entities]
        assert "UserService" in names

    def test_detects_python_function(self):
        fc = _make_file_change(
            "api.py",
            "+def get_user(user_id: int):\n+    return db.get(user_id)\n",
        )
        cs = self.analyzer.analyze(_make_changeset(fc))
        names = [e.name for e in cs.semantic_entities]
        assert "get_user" in names

    def test_detects_flask_endpoint(self):
        fc = _make_file_change(
            "routes.py",
            '+@app.get("/users/<id>")\n+def user_detail(id):\n+    pass\n',
        )
        cs = self.analyzer.analyze(_make_changeset(fc))
        entity_types = [e.entity_type for e in cs.semantic_entities]
        assert EntityType.API_ENDPOINT in entity_types

    def test_skips_noise_only_diff(self):
        fc = _make_file_change(
            "module.py",
            "+  # just a comment\n+\n+  # another comment\n",
            additions=3,
        )
        cs = self.analyzer.analyze(_make_changeset(fc))
        assert cs.semantic_entities == []

    def test_skips_insignificant_changes(self):
        fc = FileChange(
            path="module.py",
            change_type=ChangeType.MODIFIED,
            additions=1,
            deletions=1,
            diff_content="+def foo():\n",
        )
        cs = self.analyzer.analyze(_make_changeset(fc))
        # additions + deletions = 2 < threshold of 3 → skipped
        assert cs.semantic_entities == []

    def test_deduplicates_entities(self):
        # Same entity matched by two patterns
        fc = _make_file_change(
            "models.py",
            "+class UserModel(BaseModel):\n+    name: str\n+class UserModel:\n+    pass\n",
        )
        cs = self.analyzer.analyze(_make_changeset(fc))
        names = [e.name for e in cs.semantic_entities if e.name == "UserModel"]
        assert len(names) == 1

    def test_refines_service_type(self):
        fc = _make_file_change(
            "services.py",
            "+class PaymentService:\n+    pass\n",
        )
        cs = self.analyzer.analyze(_make_changeset(fc))
        service_entities = [e for e in cs.semantic_entities if e.entity_type == EntityType.SERVICE]
        assert len(service_entities) >= 1

    def test_skips_deleted_files(self):
        fc = FileChange(
            path="old.py",
            change_type=ChangeType.DELETED,
            diff_content="-class OldClass:\n-    pass\n",
        )
        cs = self.analyzer.analyze(_make_changeset(fc))
        assert cs.semantic_entities == []
