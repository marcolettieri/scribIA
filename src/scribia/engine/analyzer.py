from __future__ import annotations

import re

from .models import ChangeSet, ChangeType, EntityType, FileChange, SemanticEntity

NOISE_RATIO_THRESHOLD = 0.80

# Maps entity types to patterns that detect them in unified diff output (+/- lines).
# Each pattern must capture the entity name in group 1 (or group 2 for endpoints).
DETECTION_PATTERNS: dict[EntityType, list[re.Pattern[str]]] = {
    EntityType.CLASS: [
        re.compile(r"^\+\s*class\s+(\w+)", re.MULTILINE),
        re.compile(
            r"^\+\s*(?:public|private|protected|abstract|sealed)[\w\s]*class\s+(\w+)", re.MULTILINE
        ),
        re.compile(r"^\+\s*(?:export\s+)?(?:abstract\s+)?class\s+(\w+)", re.MULTILINE),
    ],
    EntityType.FUNCTION: [
        re.compile(r"^\+\s*(?:async\s+)?def\s+(\w+)", re.MULTILINE),  # Python
        re.compile(r"^\+\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)", re.MULTILINE),  # JS/TS
        re.compile(r"^\+\s*(?:pub(?:\(crate\))?\s+)?(?:async\s+)?fn\s+(\w+)", re.MULTILINE),  # Rust
        re.compile(
            r"^\+\s*(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(", re.MULTILINE
        ),  # Arrow fn
    ],
    EntityType.API_ENDPOINT: [
        re.compile(
            r"""^\+.*@(?:app|router|blueprint)\.(?:get|post|put|patch|delete)\(['"]([\w/{}:]+)""",
            re.MULTILINE,
        ),
        re.compile(
            r"""^\+.*router\.(?:get|post|put|patch|delete)\(['"]([\w/{}:]+)""", re.MULTILINE
        ),
        re.compile(
            r"""^\+.*@(?:Get|Post|Put|Patch|Delete|RequestMapping)\(['"]([\w/{}:]+)""", re.MULTILINE
        ),
        re.compile(
            r"""^\+.*app\.(get|post|put|patch|delete)\(['"]([\w/{}:]+)""", re.MULTILINE
        ),  # Express
    ],
    EntityType.DATA_MODEL: [
        re.compile(
            r"^\+\s*class\s+(\w+)\s*\([^)]*(?:Model|Schema|Entity|Base|BaseModel)[^)]*\)",
            re.MULTILINE,
        ),
        re.compile(r"^\+\s*@(?:dataclass|strawberry\.type|strawberry\.input)", re.MULTILINE),
        re.compile(
            r"^\+\s*(?:export\s+)?(?:interface|type)\s+(\w+)\s*(?:extends|=|{)", re.MULTILINE
        ),
    ],
    EntityType.CONFIGURATION: [
        re.compile(r"^\+\s*(\w+)\s*=\s*os\.(?:getenv|environ\.get)", re.MULTILINE),
        re.compile(
            r"""^\+\s*(\w+)\s*:\s*(?:str|int|bool|float|Optional)\s*=\s*Field""", re.MULTILINE
        ),
    ],
}

# Files likely to contain config/settings — lower the detection bar for CONFIGURATION type
CONFIG_FILE_PATTERNS = re.compile(r"(?:config|settings|env|\.env|constants)", re.IGNORECASE)


class SemanticAnalyzer:
    def analyze(self, changeset: ChangeSet) -> ChangeSet:
        entities: list[SemanticEntity] = []
        for fc in changeset.file_changes:
            if fc.change_type == ChangeType.DELETED:
                continue
            if not fc.is_significant():
                continue
            if self._is_noise_only(fc):
                continue
            entities.extend(self._extract_entities(fc))

        changeset.semantic_entities = self._deduplicate(entities)
        return changeset

    def _is_noise_only(self, fc: FileChange) -> bool:
        lines = fc.diff_content.splitlines()
        changed = [line for line in lines if line.startswith("+") or line.startswith("-")]
        if not changed:
            return True
        noise = sum(
            1
            for line in changed
            if re.match(r"^[+-]\s*$", line)
            or re.match(r"^[+-]\s*#", line)
            or re.match(r"^[+-]\s*//", line)
            or re.match(r"^[+-]\s*/\*", line)
        )
        return (noise / len(changed)) > NOISE_RATIO_THRESHOLD

    def _extract_entities(self, fc: FileChange) -> list[SemanticEntity]:
        entities: list[SemanticEntity] = []
        is_config_file = bool(CONFIG_FILE_PATTERNS.search(fc.path))

        for entity_type, patterns in DETECTION_PATTERNS.items():
            for pattern in patterns:
                for match in pattern.finditer(fc.diff_content):
                    # Some patterns capture the route in group 2 (e.g. Express)
                    name = (
                        match.group(2)
                        if match.lastindex and match.lastindex >= 2
                        else match.group(1)
                        if match.lastindex
                        else match.group(0)
                    )
                    name = name.strip()
                    if not name or len(name) < 2:
                        continue

                    refined = self._refine_type(name, entity_type, fc, is_config_file)
                    entities.append(
                        SemanticEntity(
                            name=name,
                            entity_type=refined,
                            change_type=fc.change_type,
                            file_path=fc.path,
                            metadata={"matched_line": match.group(0).strip()[:120]},
                        )
                    )

        return entities

    def _refine_type(
        self,
        name: str,
        detected: EntityType,
        fc: FileChange,
        is_config_file: bool,
    ) -> EntityType:
        name_lower = name.lower()
        path_lower = fc.path.lower()

        if any(w in name_lower for w in ("model", "schema", "entity", "dto", "record")):
            return EntityType.DATA_MODEL
        if any(
            w in name_lower for w in ("service", "manager", "handler", "controller", "repository")
        ):
            return EntityType.SERVICE
        if is_config_file or "config" in path_lower or "setting" in path_lower:
            return EntityType.CONFIGURATION

        return detected

    @staticmethod
    def _deduplicate(entities: list[SemanticEntity]) -> list[SemanticEntity]:
        seen: set[tuple[str, str, str]] = set()
        unique: list[SemanticEntity] = []
        for e in entities:
            key = (e.name, e.entity_type.value, e.file_path)
            if key not in seen:
                seen.add(key)
                unique.append(e)
        return unique
