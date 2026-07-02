# Development Guide

This guide covers setting up **OpenSpec Developer** itself — the CLI, the active
stack, and the Jira → plan → implement workflow. It is stack-agnostic: this repo
ships as a scaffold with no application source code of its own. Once you pick a
stack (`os-stack <name>`) and start implementing tickets with `os-develop`, your
application code follows that stack's conventions — see
`ai-specs/specs/stacks/<stack>-standards.mdc` for the exact layout, build tool,
and test framework.

## Repository layout

| Path | Purpose |
|------|---------|
| `ai-specs/` | Specs, per-stack agent definitions/standards, and prompt templates (`.commands/`) |
| `openspec/` | `config.yaml` — active stack, active agent, active language, tooling commands |
| `.openspec-cli/` | The CLI itself (`commands/os-*`, shared `lib/`, `install.sh`) |
| `.github/` | CI workflow — syntax/compile validation for the CLI scripts |
| `tests/` | Placeholder tests for this framework's own CI, not your application's tests |

Application source code (`src/`, `app/`, etc.) doesn't exist yet in a fresh clone —
it's created as you implement tickets, following the path conventions of whichever
stack is active.

---

## 🛠️ Prerequisites

Required regardless of stack (the CLI itself depends on these):

| Tool | Check |
|---|---|
| **Git** | `git --version` |
| **Python 3** (`py`, `python3`, or `python`) | `python3 --version` |
| **curl** | `curl --version` |
| **GitHub CLI** (`gh`) — needed for `os-commit`/`os-review`/`os-review-apply` | `gh --version` |

Additional runtime for your **active stack**:

| Stack | Runtime |
|---|---|
| `java-spring` | Java (JDK) 17+ |
| `node-express` | Node.js LTS |
| `python-fastapi` | Python 3.12 |
| `go-gin` | Go |
| `frontend-react` | Node.js LTS |
| `frontend-angular` | Node.js LTS |

Most stacks also expect Docker if your application needs a local database —
follow the setup section of the active stack's standards file for specifics.

---

## 🚀 Setup Instructions

### 1. Clone the repository

```bash
git clone git@github.com:your-org/your-repo.git
cd your-repo
```

### 2. Install the OpenSpec CLI

```bash
sh .openspec-cli/install.sh
source ~/.bashrc   # or ~/.zshrc
```

This installs every `os-*` command to `~/.openspec/bin` and adds it to your `PATH`.
Re-run this after pulling changes to anything under `.openspec-cli/` — the CLI runs
from the installed copy, not directly from the repo.

### 3. Configure environment variables

```bash
cp .env.example .env
```

Fill in `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_TOKEN`, and `JIRA_PROJECT_KEY`
(a default project — override per command with `--project <KEY>` if you work
across multiple Jira projects). **Never commit `.env`.**

### 4. Choose your stack, agent, and language

```bash
os-stack --list && os-stack python-fastapi   # or java-spring, node-express, go-gin, frontend-react, frontend-angular
os-agent --list && os-agent claude-code
os-language --list && os-language en          # or es
```

### 5. Authenticate GitHub CLI

```bash
gh auth login
```

### 6. Verify everything works

```bash
os-tickets
```

This should list your Jira project's tickets. If it fails, check `.env` and that
`os_load_config` resolves `openspec/config.yaml` correctly (run any `os-*` command —
it prints the active stack/agent/language at the top).

---

## Working on a ticket

```bash
os-create-ticket --hu              # or os-tickets to pick an existing one
os-enrich KAN-XX && os-enrich-apply KAN-XX
os-plan KAN-XX
os-develop KAN-XX
os-commit KAN-XX
os-review <PR-NUMBER> && os-review-apply <PR-NUMBER>
```

See `README.md` for the full command reference and `CLAUDE.md` for the complete
workflow description.

---

## 🧪 Testing & Coverage

Every stack enforces a **90% coverage threshold**, checked via the stack's resolved
`test_command` / `coverage_command` in `openspec/config.yaml`. Test framework,
test types (unit/integration/controller-slice), and exact coverage tooling are
stack-specific — see `ai-specs/specs/stacks/<stack>-standards.mdc` for the active
stack's conventions before writing tests.

```bash
os-plan KAN-XX   # printed "Tooling Reference" section shows the resolved commands
```

---

## Database Migrations

Migration tooling is stack-specific (e.g. Flyway for `java-spring`, Alembic for
`python-fastapi`) — see the active stack's standards file for the exact commands
and file-naming convention. The rule that holds across every stack:

- **Never modify an already-applied migration** — always create a new one.
- Test migrations locally before committing.

---

## 🧹 Common Issues

| Problem | Solution |
|---|---|
| `os-*: command not found` | Re-run `sh .openspec-cli/install.sh`, then reload your shell (`source ~/.bashrc` / `~/.zshrc`) |
| A change to `.openspec-cli/` isn't taking effect | The CLI runs from `~/.openspec`, not the repo directly — re-run the installer |
| `os-commit` / `os-review` fail with a `gh` error | Run `gh auth login` |
| Wrong stack's commands showing up | `os-stack --list` to confirm the active stack, `os-stack <name>` to switch |
| `os-tickets` / `os-enrich` fail with a Jira error | Check `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_TOKEN` in `.env`; confirm the token hasn't expired |
| Working across multiple Jira projects | Use `--project <KEY>` on `os-tickets` / `os-create-ticket` instead of editing `.env` each time |
| Build/test/coverage command fails | Confirm it matches what's actually available locally (e.g. `./gradlew`, `pytest`, `npm test`) — commands are resolved from `openspec/config.yaml`, not hardcoded in the CLI |
