from scribia.updater.safe_write import SafeWriter


class TestSafeWriter:
    def test_write_new_creates_file(self, tmp_path):
        p = tmp_path / "doc.md"
        SafeWriter.write_new(p, "# Hello\n")
        assert p.read_text() == "# Hello\n"

    def test_write_new_creates_parent_dirs(self, tmp_path):
        p = tmp_path / "deep" / "nested" / "doc.md"
        SafeWriter.write_new(p, "content")
        assert p.exists()

    def test_update_section_replaces_content(self, tmp_path):
        p = tmp_path / "doc.md"
        p.write_text(
            "# Heading\n\n"
            "<!-- scribia:start:api -->\nold content\n<!-- scribia:end:api -->\n\n"
            "preserved footer\n"
        )
        result = SafeWriter.update_section(p, "api", "new content")
        assert result is True
        text = p.read_text()
        assert "new content" in text
        assert "old content" not in text
        assert "preserved footer" in text

    def test_update_section_returns_false_when_section_missing(self, tmp_path):
        p = tmp_path / "doc.md"
        p.write_text("# No markers here\n")
        result = SafeWriter.update_section(p, "api", "new content")
        assert result is False

    def test_update_section_returns_false_for_missing_file(self, tmp_path):
        p = tmp_path / "nonexistent.md"
        result = SafeWriter.update_section(p, "api", "content")
        assert result is False

    def test_append_section_adds_markers(self, tmp_path):
        p = tmp_path / "doc.md"
        p.write_text("# Doc\n")
        SafeWriter.append_section(p, "features", "## Feature A\nDescription")
        text = p.read_text()
        assert "<!-- scribia:start:features -->" in text
        assert "<!-- scribia:end:features -->" in text
        assert "Feature A" in text
        assert "# Doc" in text  # original content preserved

    def test_append_section_creates_file_if_missing(self, tmp_path):
        p = tmp_path / "new.md"
        SafeWriter.append_section(p, "section", "content")
        assert p.exists()
        assert "scribia:start:section" in p.read_text()

    def test_prepend_to_changelog_creates_file(self, tmp_path):
        p = tmp_path / "CHANGELOG.md"
        SafeWriter.prepend_to_changelog(p, "## [1.0.0]\n- Initial release")
        assert p.exists()
        assert "1.0.0" in p.read_text()

    def test_prepend_to_changelog_preserves_existing(self, tmp_path):
        p = tmp_path / "CHANGELOG.md"
        p.write_text("# Changelog\n\n## [0.1.0]\n- First\n")
        SafeWriter.prepend_to_changelog(p, "## [0.2.0]\n- Second")
        text = p.read_text()
        assert "0.1.0" in text
        assert "0.2.0" in text
        # New entry should appear before old one
        assert text.index("0.2.0") < text.index("0.1.0")
