#!/bin/sh
# .openspec-cli/lib/commit.sh
# Helpers for os-commit: Python pre-format and richer PR summaries.

# ── Resolve ruff executable (PATH, python -m, or local venv) ───
os_find_ruff() {
  if command -v ruff > /dev/null 2>&1; then
    echo "ruff"
    return 0
  fi
  if [ -n "${OS_PYTHON:-}" ]; then
    if "$OS_PYTHON" -m ruff --version > /dev/null 2>&1; then
      echo "$OS_PYTHON -m ruff"
      return 0
    fi
  fi
  if [ -x "$OS_REPO_ROOT/.venv/Scripts/ruff.exe" ]; then
    echo "$OS_REPO_ROOT/.venv/Scripts/ruff.exe"
    return 0
  fi
  if [ -x "$OS_REPO_ROOT/.venv/bin/ruff" ]; then
    echo "$OS_REPO_ROOT/.venv/bin/ruff"
    return 0
  fi
  if [ -x "$OS_REPO_ROOT/venv/Scripts/ruff.exe" ]; then
    echo "$OS_REPO_ROOT/venv/Scripts/ruff.exe"
    return 0
  fi
  if [ -x "$OS_REPO_ROOT/venv/bin/ruff" ]; then
    echo "$OS_REPO_ROOT/venv/bin/ruff"
    return 0
  fi
  return 1
}

# ── True when active stack is Python-based ────────────────────
os_is_python_stack() {
  case "${OS_ACTIVE_STACK:-}" in
    python-*|*-fastapi|*-django|*-flask) return 0 ;;
    *) return 1 ;;
  esac
}

# ── Run ruff format on staged .py files before commit ─────────
# Avoids husky/pre-commit "ruff format Failed — files were modified".
os_preformat_python_staged() {
  if ! os_is_python_stack; then
    return 0
  fi

  _py_files=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.py$' || true)
  if [ -z "$_py_files" ]; then
    return 0
  fi

  _ruff_cmd=$(os_find_ruff) || {
    os_warn "Stack Python detectado pero ruff no está en PATH/.venv — omitiendo pre-format."
    os_warn "Si el hook ruff-format falla, ejecuta: ruff format && git add -u"
    return 0
  }

  os_step "Pre-format Python con ruff (evita fallo del hook)..."
  # shellcheck disable=SC2086
  if ! $_ruff_cmd format $_py_files; then
    os_warn "ruff format devolvió error — el commit puede fallar en el hook."
    return 0
  fi

  # Re-stage formatted files so the commit includes the hook's expected style
  echo "$_py_files" | while IFS= read -r _f; do
    [ -n "$_f" ] && git add -- "$_f"
  done
  os_success "ruff format aplicado a archivos .py en staging."
  unset _py_files _ruff_cmd _f
}

# ── Locate plan markdown for a ticket (backend or frontend) ───
os_commit_plan_file() {
  _tid="$1"
  [ -z "$_tid" ] && return 1
  _side="${OS_SIDE:-}"
  if [ -z "$_side" ]; then
    case "${OS_ACTIVE_STACK:-}" in
      frontend-*) _side="frontend" ;;
      *)          _side="backend" ;;
    esac
  fi
  _preferred="$OS_REPO_ROOT/ai-specs/changes/planes/${_tid}/${_tid}_${_side}.md"
  if [ -f "$_preferred" ]; then
    echo "$_preferred"
    return 0
  fi
  for _alt in backend frontend; do
    _p="$OS_REPO_ROOT/ai-specs/changes/planes/${_tid}/${_tid}_${_alt}.md"
    if [ -f "$_p" ]; then
      echo "$_p"
      return 0
    fi
  done
  return 1
}

# ── One-line plan title / first summary paragraph ─────────────
os_commit_plan_blurb() {
  _plan="$1"
  [ -f "$_plan" ] || return 0
  # Prefer "# Plan..." / first H1, else first non-empty non-heading line after Resumen
  _title=$(grep -m1 -E '^# ' "$_plan" 2>/dev/null | sed 's/^#[[:space:]]*//' || true)
  _resumen=$(awk '
    BEGIN { in_res=0 }
    /^##[[:space:]]*1\.[[:space:]]*Resumen/ { in_res=1; next }
    /^##[[:space:]]*Resumen/ { in_res=1; next }
    /^## / { if (in_res) exit }
    in_res && NF && $0 !~ /^[[:space:]]*</ && $0 !~ /^```/ {
      gsub(/\r/,""); print; exit
    }
  ' "$_plan" 2>/dev/null || true)
  if [ -n "$_title" ]; then
    echo "$_title"
  fi
  if [ -n "$_resumen" ]; then
    echo "$_resumen"
  fi
  unset _plan _title _resumen
}

# ── Group staged paths into narrative bullets ─────────────────
os_commit_grouped_bullets() {
  _files="$1"
  _src=$(echo "$_files" | grep -E '^src/' || true)
  _tests=$(echo "$_files" | grep -E '^tests/' || true)
  _ci=$(echo "$_files" | grep -E '^\.github/|^\.husky/|pyproject|requirements|package\.json|angular\.json' || true)
  _docs=$(echo "$_files" | grep -E '\.md$|ai-specs/|docs/' || true)
  _other=$(echo "$_files" | grep -vE '^src/|^tests/|\.md$|ai-specs/|docs/|^\.github/|^\.husky/|pyproject|requirements|package\.json|angular\.json' || true)

  if [ "$OS_ACTIVE_LANGUAGE" = "es" ]; then
    [ -n "$_src" ]   && echo "### Código / dominio" && echo "$_src"   | sed 's/^/- /'
    [ -n "$_tests" ] && echo "### Pruebas" && echo "$_tests" | sed 's/^/- /'
    [ -n "$_ci" ]    && echo "### CI / tooling" && echo "$_ci"    | sed 's/^/- /'
    [ -n "$_docs" ]  && echo "### Docs / specs" && echo "$_docs"  | sed 's/^/- /'
    [ -n "$_other" ] && echo "### Otros" && echo "$_other" | sed 's/^/- /'
  else
    [ -n "$_src" ]   && echo "### Code / domain" && echo "$_src"   | sed 's/^/- /'
    [ -n "$_tests" ] && echo "### Tests" && echo "$_tests" | sed 's/^/- /'
    [ -n "$_ci" ]    && echo "### CI / tooling" && echo "$_ci"    | sed 's/^/- /'
    [ -n "$_docs" ]  && echo "### Docs / specs" && echo "$_docs"  | sed 's/^/- /'
    [ -n "$_other" ] && echo "### Other" && echo "$_other" | sed 's/^/- /'
  fi
  unset _files _src _tests _ci _docs _other
}

# ── Build commit body text (short) ────────────────────────────
os_build_commit_body() {
  _ticket="$1"
  _branch="$2"
  _subject_hint="$3"
  _file_count="$4"
  _staged="$5"
  _stat=$(git diff --cached --stat 2>/dev/null | tail -n 1 | tr -d '\r' || true)

  _areas=""
  echo "$_staged" | grep -qE '^src/'            && _areas="${_areas}código, "
  echo "$_staged" | grep -qE '^tests/'          && _areas="${_areas}pruebas, "
  echo "$_staged" | grep -qE '\.md$|ai-specs/'  && _areas="${_areas}docs, "
  echo "$_staged" | grep -qE '^\.github/'       && _areas="${_areas}CI, "
  _areas=$(echo "$_areas" | sed 's/, $//')

  if [ "$OS_ACTIVE_LANGUAGE" = "es" ]; then
    if [ -n "$_ticket" ]; then
      echo "- Implementa ${_ticket}: ${_subject_hint}"
      [ -n "$_areas" ] && echo "- Áreas tocadas: ${_areas}"
      echo "- ${_file_count} archivo(s)${_stat:+ — ${_stat}}"
      echo "- Stack: ${OS_ACTIVE_STACK} · Rama: ${_branch}"
    else
      echo "- ${_subject_hint}"
      [ -n "$_areas" ] && echo "- Áreas tocadas: ${_areas}"
      echo "- ${_file_count} archivo(s)${_stat:+ — ${_stat}}"
      echo "- Stack: ${OS_ACTIVE_STACK}"
    fi
  else
    if [ -n "$_ticket" ]; then
      echo "- Implements ${_ticket}: ${_subject_hint}"
      [ -n "$_areas" ] && echo "- Areas: ${_areas}"
      echo "- ${_file_count} file(s)${_stat:+ — ${_stat}}"
      echo "- Stack: ${OS_ACTIVE_STACK} · Branch: ${_branch}"
    else
      echo "- ${_subject_hint}"
      [ -n "$_areas" ] && echo "- Areas: ${_areas}"
      echo "- ${_file_count} file(s)${_stat:+ — ${_stat}}"
      echo "- Stack: ${OS_ACTIVE_STACK}"
    fi
  fi
  unset _ticket _branch _subject_hint _file_count _staged _stat _areas
}

# ── Build full PR markdown body ───────────────────────────────
# Usage: os_build_pr_body <ticket> <branch> <subject> <staged_files>
os_build_pr_body() {
  _ticket="$1"
  _branch="$2"
  _subject="$3"
  _staged="$4"
  _stat=$(git diff --cached --stat 2>/dev/null || true)
  _plan_blurb=""
  _plan_file=""
  if [ -n "$_ticket" ]; then
    _plan_file=$(os_commit_plan_file "$_ticket" 2>/dev/null || true)
    if [ -n "$_plan_file" ]; then
      _plan_blurb=$(os_commit_plan_blurb "$_plan_file")
    fi
  fi
  _grouped=$(os_commit_grouped_bullets "$_staged")

  if [ "$OS_ACTIVE_LANGUAGE" = "es" ]; then
    echo "## Resumen"
    if [ -n "$_ticket" ]; then
      echo "Implementa **${_ticket}** en el stack \`${OS_ACTIVE_STACK}\` (${OS_STACK_LABEL})."
    else
      echo "Cambios en \`${_branch}\` · stack \`${OS_ACTIVE_STACK}\` (${OS_STACK_LABEL})."
    fi
    echo ""
    echo "${_subject}"
    if [ -n "$_plan_blurb" ]; then
      echo ""
      echo "$_plan_blurb" | sed 's/^/> /'
    fi
    echo ""
    echo "## Qué cambió"
    echo "$_grouped"
    echo ""
    echo "## Estadísticas del diff"
    echo '```'
    echo "$_stat"
    echo '```'
    echo ""
    echo "## Checklist"
    echo "- [ ] Tests pasan (\`${OS_TEST_CMD}\`)"
    echo "- [ ] Cobertura >= 90% (\`${OS_COVERAGE_CMD}\`)"
    echo "- [ ] Lint / format OK"
    echo "- [ ] Documentación actualizada"
  else
    echo "## Summary"
    if [ -n "$_ticket" ]; then
      echo "Implements **${_ticket}** on stack \`${OS_ACTIVE_STACK}\` (${OS_STACK_LABEL})."
    else
      echo "Changes on \`${_branch}\` · stack \`${OS_ACTIVE_STACK}\` (${OS_STACK_LABEL})."
    fi
    echo ""
    echo "${_subject}"
    if [ -n "$_plan_blurb" ]; then
      echo ""
      echo "$_plan_blurb" | sed 's/^/> /'
    fi
    echo ""
    echo "## What changed"
    echo "$_grouped"
    echo ""
    echo "## Diff stats"
    echo '```'
    echo "$_stat"
    echo '```'
    echo ""
    echo "## Checklist"
    echo "- [ ] Tests pass (\`${OS_TEST_CMD}\`)"
    echo "- [ ] Coverage >= 90% (\`${OS_COVERAGE_CMD}\`)"
    echo "- [ ] Lint / format OK"
    echo "- [ ] Documentation updated"
  fi
  unset _ticket _branch _subject _staged _stat _plan_blurb _plan_file _grouped
}
