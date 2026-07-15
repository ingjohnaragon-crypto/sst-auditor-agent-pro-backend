# SST Auditor Agent Pro — Backend

Backend en **Python 3.12 + FastAPI** del agente auditor de Seguridad y Salud en el
Trabajo (SST). Implementa la API que soporta la auditoría del SG-SST bajo la
normativa colombiana (Decreto 1072 de 2015, Resolución 312 de 2019, GTC 45:2012),
estructurada según el ciclo PHVA (Planear, Hacer, Verificar, Actuar).

> **Fuente de referencia normativa:** el conocimiento de dominio del agente
> (estándares mínimos, cálculo del nivel de riesgo GTC 45, jerarquía de
> controles, reglas normativas específicas) está documentado en
> [`.sst-agent-document.md`](./.sst-agent-document.md). Toda funcionalidad de
> negocio debe ser trazable a ese documento.

---

## Stack

| Componente | Tecnología |
| --- | --- |
| Lenguaje | Python 3.12 |
| Framework HTTP | FastAPI |
| Configuración | Pydantic Settings (variables de entorno / `.env`) |
| Dependencias | Poetry (grupos `main` y `dev`, lock versionado) |
| Tests | pytest + pytest-cov (gate de cobertura: 90%) |
| Calidad | ruff (lint + format) + mypy (modo estricto) + pre-commit |
| Persistencia | SQLAlchemy asíncrono (planificado — aún no implementado) |

Las versiones exactas están fijadas en [`poetry.lock`](./poetry.lock).
[`requirements.txt`](./requirements.txt) es un **artefacto generado** con
`poetry export` (lo consume el CI); la fuente de verdad es `poetry.lock`.

---

## Inicio rápido

```bash
# 0. Instalar Poetry (una sola vez, fuera del proyecto)
pipx install poetry

# 1. Instalar dependencias (crea .venv/ en el proyecto)
poetry install

# 2. Activar los hooks de calidad (una sola vez por clon)
poetry run pre-commit install

# 3. Configurar variables de entorno (opcional — hay defaults)
cp .env.example .env

# 4. Levantar la aplicación
poetry run uvicorn src.main:app --reload
# → http://127.0.0.1:8000/health       (prueba de vida)
# → http://127.0.0.1:8000/api/v1/ping  (conectividad con el frontend)
# → http://127.0.0.1:8000/docs         (Swagger UI)

# 5. Ejecutar la suite de tests
poetry run pytest
```

> Si se conserva el flujo con pip, `pip install -r requirements.txt` sigue
> funcionando; tras cambiar dependencias, regenerar el archivo con
> `poetry export -f requirements.txt -o requirements.txt --with dev --without-hashes`.

---

## Arquitectura del backend (`src/`)

El backend sigue Domain-Driven Design (DDD) con cuatro capas. Cada capa vive en
su propio paquete bajo `src/` y tiene una única dirección de dependencia
permitida: **de afuera hacia adentro**.

```text
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
| `LOG_LEVEL` | Nivel de log del backend | `INFO` |
| `ORIGENES_CORS` | Orígenes permitidos por CORS (JSON array) | `["http://localhost:4200"]` |

Se accede vía inyección de dependencias con
`Depends(get_settings)` (ver `src/presentation/routers/health_router.py`
como plantilla de referencia).

---

## Calidad y tests

Toda la configuración de tooling vive en [`pyproject.toml`](./pyproject.toml):

- **pytest** con cobertura obligatoria ≥ 90% (`--cov-fail-under=90`).
- **ruff** para linting y formato (reemplaza a Flake8 + isort + black).
- **mypy** en modo estricto.
- Convención de tests: patrón AAA y nombres `test_should_..._when_...` /
  `test_deberia_..._cuando_...`.

```bash
poetry run pytest                    # suite + cobertura
poetry run ruff check .              # lint
poetry run mypy                      # tipado estricto
poetry run pre-commit run --all-files  # todos los hooks sobre el repo
```

### Hooks de pre-commit

[`.pre-commit-config.yaml`](./.pre-commit-config.yaml) ejecuta en cada commit:
higiene básica (espacios finales, fin de archivo, YAML, marcas de merge),
**ruff** (lint con `--fix` + format) y **mypy** (hook local con el entorno del
proyecto). Se activan una sola vez por clon con `poetry run pre-commit install`;
un commit que viole las reglas es rechazado localmente.

El CI (`.github/workflows/ci.yml`) ejecuta la suite en cada push/PR hacia
`main` y `develop`.

---

## Flujo Gitflow

- **`main`** es la rama base y siempre debe estar desplegable.
- Cada ticket se desarrolla en una rama **`feature/SP-XX-backend`** creada desde
  `main`.
- La integración se hace exclusivamente vía **Pull Request hacia `main`** con
  review; no se hace push directo a `main`.
- Commits convencionales (`feat`, `fix`, `chore`, `test`, …) en español.

---

## Validación de conectividad con el frontend (ping/pong)

El endpoint `GET /api/v1/ping` responde `{"mensaje": "pong"}` y existe para que
el frontend Angular ([`sst-auditor-agent-pro-frontend`](https://github.com/ingjohnaragon-crypto/sst-auditor-agent-pro-frontend),
puerto 4200) valide la comunicación cross-origin (**SP-173**).

### Checklist E2E (SP-173)

1. Backend: `poetry run uvicorn src.main:app --reload --port 8000`.
2. Frontend: `ng serve` (puerto 4200).
3. Abrir `http://localhost:4200`: el root debe mostrar «pong» y la consola no debe
   registrar errores CORS (`ServicioSalud` → `GET http://localhost:8000/api/v1/ping`).
4. Prueba negativa: servir el frontend en otro origen (p. ej. `ng serve --port 4300`)
   con el default `ORIGENES_CORS` → el navegador bloquea la petición (sin
   `access-control-allow-origin` igual a `http://localhost:4300`).
5. Override: exportar `ORIGENES_CORS='["http://localhost:4300"]'`, reiniciar el
   backend y repetir el paso 4; entonces el origen 4300 debe ser aceptado.

La política CORS se configura con `ORIGENES_CORS` (ver tabla de `Settings`);
solo los orígenes listados reciben la cabecera `access-control-allow-origin`.
Verificación rápida sin frontend:

```bash
# Happy path
curl -i http://localhost:8000/api/v1/ping

# Preflight permitido → responde con access-control-allow-origin
curl -i -X OPTIONS http://localhost:8000/api/v1/ping \
  -H "Origin: http://localhost:4200" -H "Access-Control-Request-Method: GET"

# Origen no permitido → la cabecera no se emite
curl -i -X OPTIONS http://localhost:8000/api/v1/ping \
  -H "Origin: http://malicioso.example" -H "Access-Control-Request-Method: GET"
```

---

## Estructura del repositorio

```text
├── src/                      # Código fuente de la aplicación (DDD, ver arriba)
├── tests/                    # Suite de tests (espeja la estructura de src/)
├── .sst-agent-document.md    # Referencia normativa del dominio SST (PHVA, GTC 45)
├── ai-specs/                 # Specs y estándares para el flujo OpenSpec
├── openspec/                 # Configuración y documentación del framework OpenSpec
├── .openspec-cli/            # CLI del framework OpenSpec (comandos os-*)
├── pyproject.toml            # Metadatos Poetry + configuración de pytest, coverage, ruff y mypy
├── poetry.lock               # Versiones exactas resueltas por Poetry (fuente de verdad)
├── requirements.txt          # Artefacto generado con `poetry export` (lo consume el CI)
├── .pre-commit-config.yaml   # Hooks de calidad (ruff, mypy, higiene básica)
└── .env.example              # Plantilla de variables de entorno
```

---

## Flujo de desarrollo con OpenSpec

Este repositorio se desarrolla con **OpenSpec Developer**, un framework
spec-driven que conecta Jira, el código y el agente de IA mediante los comandos
`os-*` (`os-plan`, `os-develop`, `os-commit`, `os-review`, …).

Toda la documentación del framework — conceptos, comandos, stacks, agentes e
instalación — está en [`openspec/README.md`](./openspec/README.md).

```bash
# Ciclo típico de un ticket
os-enrich SP-XXX      # enriquecer ticket con detalle técnico
os-plan SP-XXX        # generar plan de implementación
os-develop SP-XXX     # crear rama + implementar
os-commit SP-XXX      # commit + push + PR
os-review <PR>        # code review con IA
os-review-apply <PR>  # publicar review en GitHub
```

---

## Licencia

ISC
