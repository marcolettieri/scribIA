---
name: scribia
description: "Incremental AI documentation system. Detects semantic changes from git history, updates only impacted doc sections (API, architecture, changelog), and syncs optional knowledge backends (Graphify, LLM Wiki). Manual execution only — run /scribia when you want docs updated."
trigger: /scribia
---

# /scribia

Analyze repository changes and update only the documentation sections that were actually impacted — APIs, data models, configuration, changelog, and optional knowledge graphs. Never regenerates all docs unless explicitly forced.

## Usage

```
/scribia                          # analyze changes since last run, update docs
/scribia init                     # scaffold docs/ structure + set initial checkpoint
/scribia --dry-run                # show what WOULD be documented (no writes)
/scribia --force                  # reprocess even if already at latest checkpoint
/scribia --from-commit <sha>      # override starting commit
/scribia state show               # inspect last checkpoint
/scribia state reset              # move checkpoint to current HEAD
/scribia config                   # show effective configuration
/scribia backends                 # list available backends
/scribia -h                       # print this usage block
```

## What You Must Do When Invoked

### 0. Help flag
If invoked as `/scribia -h` or `/scribia --help`, print the Usage section above verbatim and stop.

---

### Step 1 — Verify installation
Run:
```bash
python3 -m scribia --help 2>/dev/null || scribia --help 2>/dev/null
```
If neither works, tell the user:
> scribia is not installed. Run `./install.sh` from the project root first, then `/scribia init`.
Stop here.

---

### Step 2 — Parse flags and build the CLI command
Map /scribia options to CLI flags:
- `/scribia --dry-run`          → `python3 -m scribia run --dry-run`
- `/scribia --force`            → `python3 -m scribia run --force`
- `/scribia --from-commit <sha>` → `python3 -m scribia run --from-commit <sha>`
- `/scribia init`               → `python3 -m scribia init`
- `/scribia state show`         → `python3 -m scribia state show`
- `/scribia state reset`        → `python3 -m scribia state reset`
- `/scribia config`             → `python3 -m scribia config`
- `/scribia backends`           → `python3 -m scribia backends`
- `/scribia` (no args)          → `python3 -m scribia run`

---

### Step 3 — Run the scribia pipeline
Execute the CLI command you built in Step 2. Show the full output to the user.

If the output ends with a line like:
```
[scribia] Graphify queued — run in Claude Code: /graphify . --update --wiki --no-viz
```
Then invoke the graphify skill now:
```
/graphify . --update --wiki --no-viz
```
This keeps the knowledge graph in sync without a separate manual step.

---

### Step 4 — Enrich documentation with semantic context (only on successful `run`)
After the CLI writes structural documentation, you have full access to the git diff and conversation context. Use that to add richer descriptions to the entities that were just documented.

For each file that was updated:
1. Read the current doc file (e.g., `docs/api/my_module.md`)
2. Identify entity rows/sections that have empty or placeholder descriptions
3. Read the relevant source file or diff to understand what the entity actually DOES
4. Update the description inline — one clear sentence per entity is enough

Only add descriptions where they are absent or clearly wrong. Do not reformat or reorganize what the Python tool already wrote.

---

### Step 5 — Report summary
Print a clean summary to the user:

```
✓ scribia completed

  Commits processed: <from>..<to>
  Files changed: N
  Entities documented: N

  Updated:
    docs/api/my_module.md
    docs/architecture/data-models.md
    CHANGELOG.md

  Knowledge backends:
    graphify: ✓ updated
    llm_wiki: ✓ updated
```

If nothing changed, say so clearly rather than outputting an empty report.

---

## Backend Plugin System

Backends are resolved in this order:
1. Built-in: `markdown`, `graphify`, `llm_wiki`
2. Custom: any `.py` file in `./plugins/` whose class has `name = "<backend_name>"`

To add a new backend, copy `plugins/example_custom_backend.py`, implement the four methods, and set `backend: your_name` in `scribia.yaml`. No core code changes needed.

All backends implement:
- `init(config)` — setup, called once per run
- `update(changeset)` → `list[str]` — write docs, return updated paths
- `persist()` — flush writes
- `query(question)` → `str` — optional, for future knowledge retrieval

---

## Checkpoint System

State is persisted in `.scribia/state.json`:
```json
{
  "last_commit": "abc1234...",
  "last_run": "2026-01-15T10:30:00Z",
  "last_summary": "12 files, 8 entities",
  "backend_config": { "backends": ["markdown"] },
  "run_count": 7,
  "schema_version": 1
}
```
Each run updates this file. The diff always starts from `last_commit`.

---

## Safe Write Contract

The Python tool NEVER:
- Deletes documentation files
- Overwrites content outside its named section markers
- Regenerates the full docs tree unless `--force` is used

Sections are bounded by HTML comments:
```
<!-- scribia:start:section-name -->
...managed content...
<!-- scribia:end:section-name -->
```
Content outside these markers is always preserved.

---

## Configuration reference

`scribia.yaml` (project root) or `~/.scribia.yaml` (user global):

```yaml
backend: markdown           # primary backend
knowledge_backends:         # optional additional backends
  - llm_wiki
docs_dir: docs              # where to write docs
changelog: CHANGELOG.md
language: auto              # auto | en | it | de | fr | ...
exclude_patterns:
  - "test_*"
  - "*.test.ts"
graphify:
  flags: "--update --wiki --no-viz"
  target_path: "."
llm_wiki:
  output_dir: wiki
```
