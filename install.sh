#!/usr/bin/env bash
# scribia installer
# Run from the project root: ./install.sh

set -euo pipefail

SKILL_DIR="${HOME}/.claude/skills/scribia"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ─── colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}!${NC} $*"; }
info() { echo -e "${CYAN}→${NC} $*"; }
fail() { echo -e "${RED}✗${NC} $*" >&2; exit 1; }

echo -e "\n${CYAN}Scribia — AI Documentation System${NC}\n"

# ─── prerequisites ────────────────────────────────────────────────────────────
command -v python3 >/dev/null || fail "python3 is required"
command -v git >/dev/null    || fail "git is required"

PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MAJOR=$(echo "$PYTHON_VER" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VER" | cut -d. -f2)
if [[ "$PYTHON_MAJOR" -lt 3 || ("$PYTHON_MAJOR" -eq 3 && "$PYTHON_MINOR" -lt 11) ]]; then
  fail "Python 3.11+ required (found $PYTHON_VER)"
fi
ok "Python $PYTHON_VER"

# ─── 1. Documentation backend ─────────────────────────────────────────────────
echo ""
echo "1) Default documentation backend:"
echo "   [1] Markdown  (no dependencies, always works)"
echo "   [2] LLM Wiki  (structured wiki per module)"
echo "   [3] Graphify  (knowledge graph — requires graphify skill)"
echo "   [4] Custom    (you implement plugins/your_backend.py)"
echo ""
read -rp "   Choice [1]: " backend_choice
backend_choice="${backend_choice:-1}"

case "$backend_choice" in
  1) BACKEND="markdown" ;;
  2) BACKEND="llm_wiki" ;;
  3) BACKEND="graphify" ;;
  4)
    read -rp "   Backend name (must match your plugins/*.py class name): " BACKEND
    BACKEND="${BACKEND:-custom}"
    ;;
  *) warn "Invalid choice, defaulting to markdown"; BACKEND="markdown" ;;
esac
ok "Primary backend: $BACKEND"

# ─── 2. Knowledge backends ────────────────────────────────────────────────────
echo ""
echo "2) Knowledge backends (optional, can select multiple):"
echo "   [g] Graphify  — knowledge graph"
echo "   [w] LLM Wiki  — document-centric store"
echo "   [n] None"
echo ""
read -rp "   Choice (comma-separated, e.g. g,w) [n]: " kb_choice
kb_choice="${kb_choice:-n}"

KNOWLEDGE_BACKENDS="[]"
if [[ "$kb_choice" == *"g"* && "$kb_choice" == *"w"* ]]; then
  KNOWLEDGE_BACKENDS='["graphify", "llm_wiki"]'
elif [[ "$kb_choice" == *"g"* ]]; then
  KNOWLEDGE_BACKENDS='["graphify"]'
elif [[ "$kb_choice" == *"w"* ]]; then
  KNOWLEDGE_BACKENDS='["llm_wiki"]'
fi
ok "Knowledge backends: $KNOWLEDGE_BACKENDS"

# ─── 3. Update mode ──────────────────────────────────────────────────────────
echo ""
echo "3) Update mode:"
echo "   [1] Manual only (default) — run /scribia or scribia run when you decide"
echo "   [2] Auto after Claude response — installs a Stop hook in Claude Code"
echo "       (runs scribia automatically each time Claude finishes responding)"
echo "   [3] Auto after each file edit — installs a PostToolUse hook"
echo "       (more granular, triggers after every Edit/Write by Claude)"
echo ""
read -rp "   Choice [1]: " update_mode_choice
update_mode_choice="${update_mode_choice:-1}"

UPDATE_MODE="manual"
HOOK_TRIGGER=""
case "$update_mode_choice" in
  1) UPDATE_MODE="manual" ;;
  2) UPDATE_MODE="auto"; HOOK_TRIGGER="stop" ;;
  3) UPDATE_MODE="auto"; HOOK_TRIGGER="post-edit" ;;
  *) warn "Invalid choice, defaulting to manual"; UPDATE_MODE="manual" ;;
esac
ok "Update mode: $UPDATE_MODE${HOOK_TRIGGER:+ ($HOOK_TRIGGER trigger)}"

# ─── 4. Python package install ───────────────────────────────────────────────
echo ""
info "Installing Python package..."
if python3 -m pip install -e "${SCRIPT_DIR}[dev]" --quiet; then
  ok "scribia Python package installed"
else
  fail "pip install failed"
fi

# ─── 5. Generate scribia.yaml ─────────────────────────────────────────────────
if [[ -f "scribia.yaml" ]]; then
  warn "scribia.yaml already exists — skipping"
else
  info "Writing scribia.yaml..."
  cat > scribia.yaml << YAML
backend: ${BACKEND}
knowledge_backends: ${KNOWLEDGE_BACKENDS}
docs_dir: docs
changelog: CHANGELOG.md
language: auto
update_mode: ${UPDATE_MODE}
exclude_patterns:
  - "test_*"
  - "*.test.ts"
  - "*.spec.*"
graphify:
  flags: "--update --wiki --no-viz"
  target_path: "."
llm_wiki:
  output_dir: wiki
YAML
  ok "scribia.yaml created"
fi

# ─── 6. Install Claude Code skill ─────────────────────────────────────────────
if [[ -d "${HOME}/.claude/skills" ]]; then
  info "Installing Claude Code skill..."
  if [[ -L "${SKILL_DIR}" || -d "${SKILL_DIR}" ]]; then
    warn "Skill already installed at ${SKILL_DIR}"
  else
    ln -s "${SCRIPT_DIR}" "${SKILL_DIR}"
    ok "Skill linked: ${SKILL_DIR} → ${SCRIPT_DIR}"
  fi
else
  warn "Claude Code skills directory not found — skill not linked"
  warn "To install manually: ln -s ${SCRIPT_DIR} ~/.claude/skills/scribia"
fi

# ─── 7. Initialize state ──────────────────────────────────────────────────────
if git rev-parse --git-dir >/dev/null 2>&1; then
  info "Initializing checkpoint..."
  scribia init
else
  warn "Not inside a git repository — run 'scribia init' after git init"
fi

# ─── 8. Install hook (if auto mode selected) ──────────────────────────────────
if [[ -n "$HOOK_TRIGGER" ]] && [[ -d "${HOME}/.claude" ]]; then
  info "Installing Claude Code hook (${HOOK_TRIGGER})..."
  scribia hook install --trigger "${HOOK_TRIGGER}"
fi

echo ""
echo -e "${GREEN}Installation complete.${NC}"
echo ""
echo "  In Claude Code:    /scribia"
echo "  In terminal:       scribia run"
if [[ -n "$HOOK_TRIGGER" ]]; then
  echo "  Auto mode:         scribia runs after each Claude response (${HOOK_TRIGGER})"
  echo "  To disable:        scribia hook remove"
fi
echo ""
