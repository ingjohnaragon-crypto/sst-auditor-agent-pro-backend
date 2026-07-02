# OpenSpec Developer — Contexto del proyecto para Claude Code

Este archivo es leído automáticamente por Claude Code al abrir este repositorio.
Contiene todo el contexto necesario para continuar el desarrollo sin re-explicar nada.

---

## Qué es este proyecto

**OpenSpec Developer** es la edición de OpenSpec orientada a stacks de desarrollo
generales: Java, Python, Node.js, Go, React y Angular.

El framework conecta Jira, el repositorio y el agente de IA en un flujo de desarrollo
unificado. Almacena el contexto del proyecto (arquitectura, convenciones, estándares)
como specs estructurados y los entrega automáticamente al agente en cada comando.

> **Nota**: El stack Vault Smart Contracts (Thought Machine) no forma parte de esta
> edición. Se mantiene en el repositorio `spec-driven-project`.

---

## Stack y estructura del repo

```
open-spec-developer/
├── openspec/config.yaml              # Stack activo + agente activo
├── ai-specs/
│   ├── .agents/stacks/
│   │   ├── java-spring.md
│   │   ├── python-fastapi.md
│   │   ├── node-express.md
│   │   ├── go-gin.md
│   │   ├── frontend-react.md
│   │   └── frontend-angular.md
│   ├── specs/stacks/
│   │   ├── java-spring-standards.mdc
│   │   ├── python-fastapi-standards.mdc
│   │   ├── node-express-standards.mdc
│   │   ├── go-gin-standards.mdc
│   │   ├── frontend-react-standards.mdc
│   │   └── frontend-angular-standards.mdc
│   ├── .commands/                    # Plantillas de prompt
│   └── changes/                      # Planes generados por ticket
├── .openspec-cli/
│   ├── install.sh                    # sh .openspec-cli/install.sh
│   ├── lib/
│   │   ├── config.sh
│   │   ├── agent.sh
│   │   ├── jira.sh
│   │   ├── parse_config.py
│   │   ├── parse_agent.py
│   │   └── parse_stack.py
│   └── commands/                     # 13 comandos os-*
└── .github/workflows/ci.yml          # CI de validación
```

---

## 13 Comandos CLI

### Configuración
```bash
os-stack --list                        # listar stacks disponibles
os-stack python-fastapi                # activar stack
os-agent --list                        # listar agentes
os-agent claude-code                   # activar agente
```

### Gestión de Jira
```bash
os-tickets                             # ver todos los tickets del proyecto
os-tickets "Por hacer"                 # filtrar por estado
os-tickets --project OTRO              # ver tickets de otro proyecto Jira
os-create-ticket --hu                  # crear ticket con HU generada por IA
os-create-ticket "titulo" Task         # crear ticket rápido
os-create-ticket --project OTRO "titulo" Task  # crear en otro proyecto
os-transition KAN-XX --list            # ver transiciones disponibles
os-transition KAN-XX "En curso"        # mover ticket de estado
```

### Workflow principal
```bash
os-enrich KAN-XX                       # enriquecer ticket con contexto técnico
os-enrich-apply KAN-XX                 # subir enriquecimiento a Jira
os-plan KAN-XX                         # generar plan → ai-specs/changes/KAN-XX_backend.md
os-develop KAN-XX                      # crear rama feature/KAN-XX-backend + implementar
os-commit KAN-XX                       # commit + push + PR → develop
os-review PR_NUMBER                    # generar code review del PR
os-review-apply PR_NUMBER              # publicar review en GitHub
os-review-fix PR_NUMBER                # fix automático si REQUEST CHANGES + re-review
```

---

## Flujo completo para un ticket

```bash
os-stack python-fastapi
os-agent claude-code

os-create-ticket --hu

os-enrich KAN-XX
os-enrich-apply KAN-XX

os-plan KAN-XX

os-develop KAN-XX

os-commit KAN-XX

os-review PR_NUMBER
os-review-apply PR_NUMBER

# Si REQUEST CHANGES:
os-review-fix PR_NUMBER

os-transition KAN-XX "Done"
```

---

## Stacks soportados

```yaml
java-spring             # Java 17 + Spring Boot
python-fastapi          # Python 3.12 + FastAPI (stack activo por defecto)
node-express            # Node.js + Express
go-gin                  # Go + Gin
frontend-react          # React + Vite
frontend-angular        # Angular
```

---

## Agentes soportados

| Agente | Entrega | Notas |
|---|---|---|
| `copilot` | Portapapeles | Pegar manualmente en VS Code Copilot Chat |
| `claude-code` | CLI directo | Totalmente automático sin copy-paste |
| `cursor` | Portapapeles | Pegar manualmente en Cursor |
| `windsurf` | Portapapeles | Pegar manualmente en Windsurf |
| `aider` | CLI directo | Automático via terminal |

---

## Variables de entorno (.env)

```bash
# Jira
JIRA_BASE_URL=https://<your-workspace>.atlassian.net
JIRA_EMAIL=<your-email>
JIRA_TOKEN=<your-jira-api-token>
JIRA_PROJECT_KEY=<your-project-key>
```

---

## Cómo preguntarme desde Claude Code

```bash
"genera un endpoint REST para listar usuarios con paginación"
"crea los tests para src/services/user_service.py"
"qué patrón usar para autenticación JWT en FastAPI"
"planifica el ticket KAN-5 para Python FastAPI"
"revisa src/models/user.py y detecta violaciones de DDD"
"explica la diferencia entre Repository y Service en esta arquitectura"
```

El contexto del proyecto, los stacks y el estado actual están cargados.
No necesitas re-explicar nada.
