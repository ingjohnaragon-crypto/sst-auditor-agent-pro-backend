#!/bin/sh
# .openspec-cli/lib/agent.sh
# Resolves the active AI agent from openspec/config.yaml
# and delivers prompts according to the agent's delivery method.
#
# delivery modes:
#   clipboard — copy prompt for manual paste (Copilot, Windsurf)
#   cli       — invoke Claude Code / Aider in the terminal
#   file      — write prompt to disk for Cursor Agent (no waits)

# ── Resolve active agent from config ─────────────────────────
os_load_agent() {
  PARSER="$HOME/.openspec/lib/parse_config.py"

  # Read active agent name
  OS_ACTIVE_AGENT=$(grep "^agent:" "$OS_CONFIG" | head -1 \
    | sed 's/^agent:[[:space:]]*//' | tr -d '"' | tr -d "'" | tr -d '\r')

  OS_ACTIVE_AGENT="${OS_ACTIVE_AGENT:-cursor}"

  # Parse agent fields using dedicated Python script
  _agent_result=$(py -X utf8 "$HOME/.openspec/lib/parse_agent.py" \
    "$OS_CONFIG" "$OS_ACTIVE_AGENT" 2>/dev/null || echo "")

  OS_AGENT_LABEL=$(echo "$_agent_result"    | grep "^label="    | cut -d= -f2-)
  OS_AGENT_DELIVERY=$(echo "$_agent_result" | grep "^delivery=" | cut -d= -f2-)
  OS_AGENT_COMMAND=$(echo "$_agent_result"  | grep "^command="  | cut -d= -f2-)
  OS_AGENT_ARGS=$(echo "$_agent_result"     | grep "^args="     | cut -d= -f2-)

  # Defaults
  OS_AGENT_DELIVERY="${OS_AGENT_DELIVERY:-file}"
  OS_AGENT_COMMAND="${OS_AGENT_COMMAND:-null}"

  export OS_ACTIVE_AGENT OS_AGENT_LABEL OS_AGENT_DELIVERY \
         OS_AGENT_COMMAND OS_AGENT_ARGS
}

# ── Shared: print Cursor / file-delivery instructions ────────
# Usage: os_print_file_delivery_hints <prompt_file> [output_file]
os_print_file_delivery_hints() {
  _PF="$1"
  _OF="${2:-}"

  os_divider
  os_success "Prompt listo para Cursor (delivery: file)"
  os_info    "Prompt : $_PF"
  if [ -n "$_OF" ]; then
    os_info  "Output : $_OF"
  fi
  os_divider
  os_label "  En Cursor Agent:"
  os_info "1. Abre o menciona: @$_PF"
  os_info "2. O escribe el comando os-* (la rule OpenSpec lo ejecuta)"
  if [ -n "$_OF" ]; then
    os_info "3. El agente debe escribir el resultado en: $_OF"
  fi
  os_divider
}

# ── Low-level: invoke the active CLI agent on a prompt ───────
# Usage: os_agent_run <prompt_file> [output_file]
os_agent_run() {
  _PROMPT_FILE="$1"
  _OUTPUT_FILE="${2:-}"

  if [ "$OS_AGENT_COMMAND" = "null" ] || [ -z "$OS_AGENT_COMMAND" ]; then
    os_error "No CLI command configured for agent: $OS_ACTIVE_AGENT"
    return 1
  fi

  if ! command -v "$OS_AGENT_COMMAND" > /dev/null 2>&1; then
    os_error "Agent command not found: $OS_AGENT_COMMAND"
    os_info  "Install $OS_AGENT_LABEL or switch agent: os-agent cursor"
    return 1
  fi

  case "$OS_ACTIVE_AGENT" in
    aider)
      _PROMPT_CONTENT=$(cat "$_PROMPT_FILE")
      if [ -n "$_OUTPUT_FILE" ]; then
        "$OS_AGENT_COMMAND" $OS_AGENT_ARGS "$_PROMPT_CONTENT" > "$_OUTPUT_FILE" 2>/dev/null
      else
        "$OS_AGENT_COMMAND" $OS_AGENT_ARGS "$_PROMPT_CONTENT"
      fi
      ;;
    *)
      if [ -n "$_OUTPUT_FILE" ]; then
        "$OS_AGENT_COMMAND" $OS_AGENT_ARGS < "$_PROMPT_FILE" > "$_OUTPUT_FILE" 2>/dev/null
      else
        "$OS_AGENT_COMMAND" $OS_AGENT_ARGS < "$_PROMPT_FILE"
      fi
      ;;
  esac
}

# ── Low-level: copy a file's content to the system clipboard ─
os_copy_to_clipboard() {
  _FILE="$1"
  if command -v clip.exe > /dev/null 2>&1; then
    cat "$_FILE" | clip.exe && return 0
  elif command -v pbcopy > /dev/null 2>&1; then
    cat "$_FILE" | pbcopy && return 0
  elif command -v xclip > /dev/null 2>&1; then
    cat "$_FILE" | xclip -selection clipboard && return 0
  elif command -v xsel > /dev/null 2>&1; then
    cat "$_FILE" | xsel --clipboard --input && return 0
  fi
  return 1
}

# ── Deliver prompt to the active agent (fire-and-forget) ─────
# Usage: os_deliver_prompt <prompt_file> [next_step_hint]
os_deliver_prompt() {
  PROMPT_FILE="$1"
  NEXT_HINT="${2:-}"

  if [ ! -f "$PROMPT_FILE" ]; then
    os_error "Prompt file not found: $PROMPT_FILE"
    exit 1
  fi

  case "$OS_AGENT_DELIVERY" in

    file)
      os_print_file_delivery_hints "$PROMPT_FILE"
      if [ -n "$NEXT_HINT" ]; then
        os_label "  Next steps:"
        echo "$NEXT_HINT" | while IFS= read -r line; do
          os_info "$line"
        done
        os_divider
      fi
      ;;

    clipboard)
      os_divider
      if os_copy_to_clipboard "$PROMPT_FILE"; then
        os_success "Prompt copied to clipboard!"
        os_info    "Paste into $OS_AGENT_LABEL chat (Ctrl+V / Cmd+V)"
      else
        os_warn "Clipboard not available — copy manually:"
        os_info "  cat $PROMPT_FILE | clip"
      fi

      if [ -n "$NEXT_HINT" ]; then
        os_divider
        os_label "  Next steps:"
        echo "$NEXT_HINT" | while IFS= read -r line; do
          os_info "$line"
        done
      fi
      os_divider
      ;;

    cli)
      os_divider
      os_step "Sending prompt to $OS_AGENT_LABEL..."
      os_divider
      os_agent_run "$PROMPT_FILE" || exit 1
      os_divider
      os_success "Done — $OS_AGENT_LABEL completed the task."
      os_divider
      ;;

    *)
      os_error "Unknown delivery method: $OS_AGENT_DELIVERY"
      os_info  "Valid options: file, clipboard, cli"
      exit 1
      ;;
  esac
}

# ── Deliver a prompt to an agent that acts autonomously ──────
# Usage: os_deliver_prompt_autonomous <prompt_file> [wait_message]
# Sets OS_AGENT_HANDOFF=1 when file delivery handed off to Cursor
# (caller must NOT run follow-up steps until the agent finishes).
os_deliver_prompt_autonomous() {
  PROMPT_FILE="$1"
  WAIT_MESSAGE="${2:-}"
  OS_AGENT_HANDOFF=0

  case "${OS_AGENT_DELIVERY:-file}" in
    cli)
      os_step "Sending prompt to $OS_AGENT_LABEL..."
      os_info "The agent will work autonomously — review the results when it finishes."
      os_agent_run "$PROMPT_FILE"
      ;;
    file)
      os_print_file_delivery_hints "$PROMPT_FILE"
      if [ -n "$WAIT_MESSAGE" ]; then
        os_info "Cuando el agente termine: $WAIT_MESSAGE"
        os_divider
      fi
      OS_AGENT_HANDOFF=1
      ;;
    *)
      if os_copy_to_clipboard "$PROMPT_FILE"; then
        os_success "Prompt copied to clipboard!"
      else
        os_warn "Clipboard not available — copy manually:"
        os_info "  cat $PROMPT_FILE | clip"
      fi
      os_info "1. Paste in $OS_AGENT_LABEL"
      os_info "2. Let it complete the task"
      if [ -n "$WAIT_MESSAGE" ]; then
        os_info "3. $WAIT_MESSAGE"
        read -r _dummy
      fi
      ;;
  esac
  export OS_AGENT_HANDOFF
}

# ── Deliver a prompt and capture the agent's text response ───
# Usage: os_deliver_prompt_capture <prompt_file> <output_file>
# file mode: no interactive wait — sets OS_AGENT_HANDOFF=1 if output
# is still missing so the caller can exit cleanly for Cursor.
os_deliver_prompt_capture() {
  PROMPT_FILE="$1"
  OUTPUT_FILE="$2"
  OS_AGENT_HANDOFF=0

  case "${OS_AGENT_DELIVERY:-file}" in
    cli)
      os_step "Sending prompt to $OS_AGENT_LABEL..."
      os_agent_run "$PROMPT_FILE" "$OUTPUT_FILE"
      ;;
    file)
      os_print_file_delivery_hints "$PROMPT_FILE" "$OUTPUT_FILE"
      if [ -s "$OUTPUT_FILE" ]; then
        os_success "Output ya presente — continuando."
      else
        OS_AGENT_HANDOFF=1
        os_info "Sin output aún. Ejecuta el prompt en Cursor y vuelve a correr el comando,"
        os_info "o deja el artefacto escrito y continúa con el paso apply."
      fi
      ;;
    *)
      if os_copy_to_clipboard "$PROMPT_FILE"; then
        os_success "Prompt copied to clipboard!"
      else
        os_warn "Clipboard not available — copy manually:"
        os_info "  cat $PROMPT_FILE | clip"
      fi
      os_info "1. Paste in $OS_AGENT_LABEL"
      os_info "2. Copy the AI output"
      os_info "3. Press Enter here when ready..."
      read -r _dummy
      os_step "Paste the response (CTRL+Z + Enter to finish on Windows, CTRL+D on Unix):"
      OUTPUT=""
      while IFS= read -r line; do
        OUTPUT="${OUTPUT}${line}
"
      done
      printf '%s' "$OUTPUT" > "$OUTPUT_FILE"
      ;;
  esac
  export OS_AGENT_HANDOFF
}

# ── Print agent summary ───────────────────────────────────────
os_print_agent() {
  os_info "Agent     : $OS_ACTIVE_AGENT ($OS_AGENT_LABEL)"
  os_info "Delivery  : $OS_AGENT_DELIVERY"
  [ "$OS_AGENT_COMMAND" != "null" ] && \
    os_info "Command   : $OS_AGENT_COMMAND $OS_AGENT_ARGS" || true
}
