# OpenSpec Developer — Spec-Driven AI Development Platform

OpenSpec connects your project management tool (Jira), your codebase, and your AI agent
(Copilot, Claude Code, Cursor, etc.) into a single coherent workflow — driven by specs
and standards, not by improvisation.

> **This is the developer edition.** It ships with stacks for Java, Python, Node.js, Go,
> React, and Angular. For the Thought Machine Vault Smart Contracts stack, see the
> `spec-driven-project` repository.

---

## The Problem

Modern development teams using AI assistants face a recurring gap: the AI knows
how to code, but it doesn't know *your* project. It doesn't know your architecture,
your conventions, your Jira tickets, or your stack. Every prompt has to re-explain
context that already exists somewhere — scattered across Jira, README files,
and tribal knowledge.

The result: AI output that's generic, inconsistent, and requires heavy review
and rework before it fits your codebase.

---

## The Solution

OpenSpec acts as the bridge. It stores your project's architectural decisions,
stack conventions, and quality standards as structured spec files. A lightweight
CLI reads those specs, fetches context from Jira, and builds a complete,
context-rich prompt — then delivers it to whatever AI agent your team uses.

```
Jira Ticket
    +
Project Specs (architecture, standards, conventions)
    +
Active Stack (Java, Python, Node, Go, Angular, React)
    +
Active AI Agent (Copilot, Claude Code, Cursor, Aider)
    ↓
One CLI command
    ↓
Context-rich prompt → AI generates plan / implementation / review
```

---

## Core Concepts

### Spec-Driven Development
All architectural decisions live in `ai-specs/specs/`. Agents read these
before generating any output. The AI always works within your conventions —
not against them.

### Multi-Stack Support
One repo can support multiple technology stacks. Switch between them with
`os-stack <name>`. The active stack determines which agent file, standards,
and tooling commands are loaded.

### Multi-Agent Support
Works with any AI agent. Switch between them with `os-agent <name>`.
Clipboard agents (Copilot, Cursor, Windsurf) copy prompts for manual paste.
CLI agents (Claude Code, Aider) send prompts automatically via terminal.

### Jira Integration
Every command that generates a prompt starts by fetching the real ticket
from Jira — title, description, status, assignee. No copy-pasting context.

---

## Supported Stacks

| Stack | Technologies |
| --- | --- |
| `java-spring` | Java 17, Spring Boot, Spring Data JPA, Flyway, JUnit 5 |
| `python-fastapi` | Python 3.12, FastAPI, SQLAlchemy, Alembic, pytest |
| `node-express` | Node.js 20, Express, TypeScript, Prisma, Jest |
| `go-gin` | Go 1.22, Gin, GORM, golang-migrate, testify |
| `frontend-react` | React 18, Vite, TypeScript, TanStack Query, Vitest |
| `frontend-angular` | Angular 17, TypeScript, NgRx, Jest |

---

## Supported AI Agents

| Agent | Delivery |
| --- | --- |
| GitHub Copilot | Clipboard — paste in VS Code chat |
| Cursor | Clipboard — paste in Cursor chat |
| Windsurf | Clipboard — paste in Windsurf chat |
| Claude Code | CLI — automatic via `claude` terminal command |
| Aider | CLI — automatic via `aider` terminal command |

---

## CLI Commands

### Configuration

| Command | What it does |
| --- | --- |
| `os-stack [--list\|<name>]` | List or switch active tech stack |
| `os-agent [--list\|<name>]` | List or switch active AI agent |

### Jira

| Command | What it does |
| --- | --- |
| `os-tickets [status]` | List all project tickets, optionally filtered by status |
| `os-create-ticket --hu` | Create a ticket with an AI-generated user story |
| `os-create-ticket "<title>" <type>` | Create a ticket quickly (Task, Bug, Story…) |
| `--project <KEY>` (either command) | Target a different Jira project than `JIRA_PROJECT_KEY` in `.env` |
| `os-enrich <TICKET-ID>` | Enrich a ticket with technical detail |
| `os-enrich-apply <TICKET-ID>` | Upload enriched content to Jira |
| `os-transition <TICKET-ID> [--list\|<state>]` | List transitions or move ticket to a state |

### Development workflow

| Command | What it does |
| --- | --- |
| `os-plan <TICKET-ID>` | Generate an implementation plan from a Jira ticket |
| `os-develop <TICKET-ID>` | Create feature branch + implementation prompt |
| `os-commit <TICKET-ID>` | Commit, push and open PR → develop |
| `os-review <PR>` | Generate a structured AI code review for a PR |
| `os-review-apply <PR>` | Publish the review to GitHub and apply verdict |
| `os-review-fix <PR>` | Auto-fix REQUEST CHANGES feedback, re-review and re-publish |

---

## Project Structure

```
open-spec-developer/
├── .openspec-cli/           # CLI commands and libraries
│   ├── commands/            # Executable commands (os-plan, os-commit, etc.)
│   ├── lib/                 # Shared shell and Python helpers
│   │   ├── colors.sh        # Terminal colour helpers
│   │   ├── config.sh        # Stack + env config loader
│   │   ├── jira.sh          # Jira API helpers
│   │   └── agent.sh         # Agent delivery helpers
│   └── install.sh           # Global installer
├── ai-specs/
│   ├── .agents/
│   │   └── stacks/          # Stack-specific agent files (role + conventions)
│   ├── .commands/           # Prompt templates for each workflow step
│   ├── changes/             # Generated implementation plans (per ticket)
│   └── specs/
│       ├── stacks/          # Stack-specific standards files
│       ├── base-standards.mdc
│       ├── api-spec.yml
│       ├── data-model.md
│       └── documentation-standards.mdc
├── openspec/
│   └── config.yaml          # Active stack, active agent, stack registry
├── src/                     # Application source code
├── tests/                   # Test suite
├── pyproject.toml           # pytest/coverage, ruff and mypy config
├── .env.example             # Environment variable template
└── README.md                # This file
```

---

## Arquitectura del backend (`src/`)

El backend de **SST Auditor Agent Pro** sigue Domain-Driven Design (DDD) con
cuatro capas. Cada capa vive en su propio paquete bajo `src/` y tiene una
única dirección de dependencia permitida: **de afuera hacia adentro**.

```
src/
├── domain/                  # Reglas de negocio puras — sin FastAPI ni SQLAlchemy
│   ├── models/               # Entidades y value objects (dataclasses)
│   ├── repositories/         # Interfaces abstractas de persistencia (ABC)
│   └── exceptions/            # Excepciones de negocio (DomainException y subclases)
├── application/              # Casos de uso — orquestan dominio + repositorios
│   ├── services/              # Servicios de aplicación (un caso de uso por método)
│   ├── dto/                   # Esquemas Pydantic de entrada/salida (Request/Response)
│   └── mappers/                # Transformaciones modelo de dominio <-> DTO
├── presentation/              # Capa HTTP — FastAPI
│   ├── routers/                # APIRouter por dominio + router agregador (api_router)
│   ├── dependencies/            # Fábricas de Depends() para inyección de dependencias
│   └── exception_handlers/      # Manejadores globales de excepciones registrados en `app`
├── infrastructure/            # Implementaciones concretas de las interfaces del dominio
│   ├── repositories/            # Repositorios SQLAlchemy que implementan domain/repositories
│   ├── database/                 # Engine asíncrono y fábrica de sesiones de SQLAlchemy
│   └── config/                    # Configuración tipada (Settings, Pydantic BaseSettings)
└── main.py                     # Composition root — instancia FastAPI, registra handlers y monta el router raíz
```

### Reglas de dependencia entre capas

- **`domain/`** no importa nada de `application/`, `presentation/` ni
  `infrastructure/`, y tampoco depende de FastAPI ni de SQLAlchemy. Es Python
  puro.
- **`application/`** depende solo de `domain/` (a través de las interfaces de
  repositorio) y de Pydantic para los DTO. No importa FastAPI ni SQLAlchemy.
- **`presentation/`** depende de `application/` (servicios) y usa FastAPI para
  exponer HTTP. Los routers son delgados: validan con Pydantic, llaman al
  servicio y devuelven la respuesta.
- **`infrastructure/`** implementa las interfaces definidas en `domain/`
  (por ejemplo, un repositorio SQLAlchemy que hereda de una ABC de
  `domain/repositories/`) y provee la configuración y el acceso a datos.

### Cómo agregar un nuevo dominio (por ejemplo, `audits`)

1. Crear el modelo de dominio en `src/domain/models/audit.py` y, si aplica,
   la interfaz de repositorio en `src/domain/repositories/audit_repository.py`.
2. Crear el servicio de aplicación en
   `src/application/services/audit_service.py` y sus DTO en
   `src/application/dto/audit_dto.py`.
3. Crear `src/presentation/routers/audits_router.py` con su propio
   `APIRouter`.
4. Registrarlo en el router agregador
   (`src/presentation/routers/__init__.py`) con una sola línea:

   ```python
   from src.presentation.routers.audits_router import router as audits_router

   api_router.include_router(
       audits_router, prefix=f"{settings.api_prefix}/audits", tags=["Audits"]
   )
   ```

   No es necesario tocar `src/main.py`.
5. Si el dominio requiere persistencia, implementar el repositorio SQLAlchemy
   en `src/infrastructure/repositories/` y el modelo ORM en
   `src/infrastructure/database/`.

### Configuración (`Settings`)

`src/infrastructure/config/settings.py` expone una clase `Settings`
(Pydantic `BaseSettings`) cargada desde variables de entorno o desde `.env`:

| Variable | Descripción | Valor por defecto |
| --- | --- | --- |
| `APP_NAME` | Nombre de la aplicación | `SST Auditor Agent Pro` |
| `APP_VERSION` | Versión de la aplicación | `0.1.0` |
| `API_PREFIX` | Prefijo de los endpoints de dominio | `/api/v1` |

Se accede vía inyección de dependencias con
`Depends(get_settings)` (ver `src/presentation/routers/health_router.py`
como plantilla de referencia).

---

## Quick Start

```bash
# 1. Install the CLI
sh .openspec-cli/install.sh
source ~/.bashrc

# 2. Configure credentials
cp .env.example .env
# Edit .env: JIRA_BASE_URL, JIRA_EMAIL, JIRA_TOKEN
gh auth login

# 3. Select your stack and agent
os-stack --list
os-stack python-fastapi
os-agent --list
os-agent copilot

# 4. Start with a ticket
os-enrich KAN-1          # enrich ticket with technical detail
os-plan KAN-1            # generate implementation plan
os-develop KAN-1         # create branch + implementation
os-commit KAN-1          # commit + PR
os-review 1              # AI code review
os-review-apply 1        # publish review to GitHub
```

---

## Architecture Principles

OpenSpec enforces these principles across all stacks:

- **Domain-Driven Design (DDD)** — Domain, Application, Presentation layers
- **Test-Driven Development (TDD)** — tests before implementation, always
- **90% coverage threshold** — enforced per stack
- **English only** — all code, comments, docs, and commits
- **Conventional commits** — `feat`, `fix`, `test`, `docs`, `chore`
- **No secrets in code** — environment variables only

---

## Contributing

1. Pick a ticket from Jira
2. Run `os-enrich <TICKET-ID>` to add technical detail
3. Run `os-plan <TICKET-ID>` to generate the implementation plan
4. Run `os-develop <TICKET-ID>` to implement
5. Run `os-commit <TICKET-ID>` to open a PR
6. Request review — `os-review <PR>` generates an AI code review

---

## License

ISC
