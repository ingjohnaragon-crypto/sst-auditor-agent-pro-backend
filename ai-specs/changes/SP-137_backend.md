# Backend Implementation Plan: SP-137 Diseñar estructura de paquetes y rutas FastAPI

## 1. Overview

Establecer el esqueleto arquitectónico inicial del backend de **SST Auditor Agent
Pro** sobre FastAPI, aplicando el patrón de capas Domain-Driven Design
(`domain/`, `application/`, `presentation/`, `infrastructure/`) descrito en el stack
`python-fastapi`. El repositorio no contiene código de aplicación (`src/` no
existe), por lo que esta historia crea la base estructural — paquetes, punto de
entrada, router agregador, manejadores de excepción globales, configuración
tipada y documentación — sobre la cual se implementarán los dominios funcionales
(auditorías SG-SST, matriz de riesgos GTC 45, etc.) en tickets posteriores. No se
implementa lógica de negocio ni persistencia en esta historia.

Stack activo: **python-fastapi** (Python 3.12 + FastAPI).

## 2. Architecture Context

- Active stack: `python-fastapi` (`Python 3.12 + FastAPI`)
- Capas involucradas y archivos afectados por capa:
  - **Domain**: `src/domain/{models,repositories,exceptions}/` — solo la clase
    base `DomainException` (sin lógica de negocio de dominio todavía).
  - **Application**: `src/application/{services,dto,mappers}/` — paquetes vacíos,
    sin casos de uso todavía.
  - **Presentation**: `src/presentation/{routers,dependencies,exception_handlers}/`
    — router agregador, router de `health`, y los dos manejadores de excepción
    globales.
  - **Infrastructure**: `src/infrastructure/{repositories,database,config}/` —
    `Settings` tipado con Pydantic Settings; `database/` queda como placeholder
    vacío (el engine/sesión se implementa cuando exista el primer modelo
    persistente).
  - **Composition root**: `src/main.py` — instancia `FastAPI`, registra los
    exception handlers y monta el router agregador.
  - **Configuración de proyecto**: `pyproject.toml` (nuevo — no existe aún) y
    `requirements.txt` (modificar) para dependencias y umbral de cobertura.
  - **Documentación**: `README.md` — sección "Arquitectura del Backend".
  - **Tests**: `tests/presentation/test_health_router.py`,
    `tests/infrastructure/test_settings.py`.

### Subtask Mapping

| Subtask key | Summary | Implementation Step(s) |
|---|---|---|
| `SP-164` | Definir estructura de paquetes (routers, services, models, schemas) | Step 1, Step 2 |
| `SP-165` | Configurar enrutador principal e inclusión de subrouters | Step 3, Step 4, Step 5 |
| `SP-166` | Documentar convención de paquetes en README técnico | Step 8 |

## 3. Implementation Steps

#### Step 0: Create Feature Branch
- **Action**: Crear y cambiar a una nueva rama de feature
- **Branch**: `feature/SP-137-backend`
- **Commands**:
  ```bash
  git checkout main && git pull origin main
  git checkout -b feature/SP-137-backend
  ```

#### Step 1: Estructura de paquetes base (Domain / Application / Infrastructure)
- Files:
  - `src/__init__.py`
  - `src/domain/__init__.py`
  - `src/domain/models/__init__.py`
  - `src/domain/repositories/__init__.py`
  - `src/domain/exceptions/__init__.py`
  - `src/application/__init__.py`
  - `src/application/services/__init__.py`
  - `src/application/dto/__init__.py`
  - `src/application/mappers/__init__.py`
  - `src/infrastructure/__init__.py`
  - `src/infrastructure/config/__init__.py`
  - `src/infrastructure/database/__init__.py`
  - `src/infrastructure/repositories/__init__.py`
- Changes: crear todos los paquetes con `__init__.py` vacío o con docstring de
  una línea describiendo la responsabilidad del paquete. `database/` y
  `repositories/` de infraestructura quedan como placeholders sin
  implementación (se completan cuando exista el primer modelo persistente).
- Constraint: `domain/` y `application/` no deben importar `fastapi` ni
  `sqlalchemy` en ningún archivo.

#### Step 2: Excepción base de dominio
- File: `src/domain/exceptions/base.py`
- Content: clase `DomainException` (hereda de `Exception`) con atributos
  tipados `code: str`, `http_status: int`, `message: str`, y `__init__` que
  llama a `super().__init__(message)`. Sin dependencias de FastAPI.

#### Step 3: Configuración tipada (Infrastructure)
- File: `src/infrastructure/config/settings.py`
- Content: clase `Settings(BaseSettings)` de `pydantic-settings` con campos
  `app_name: str`, `app_version: str`, `api_prefix: str` (default `/api/v1`),
  `model_config = SettingsConfigDict(env_file=".env")`. Exponer una instancia
  única `settings = Settings()` para inyección en `main.py` y routers.

#### Step 4: Router agregador y router de health (Presentation)
- Files:
  - `src/presentation/__init__.py`
  - `src/presentation/routers/__init__.py`
  - `src/presentation/routers/health_router.py`
  - `src/presentation/dependencies/__init__.py`
- Changes:
  - `health_router.py`: `APIRouter()` con `GET /health` que responde `200 OK`
    con `{"status": "ok", "app": settings.app_name, "version": settings.app_version}`.
  - `routers/__init__.py`: define `api_router = APIRouter()` e incluye
    `health_router` (`api_router.include_router(health_router, prefix="/health", tags=["Health"])`
    o equivalente — decisión sobre si `health` vive dentro o fuera de
    `settings.api_prefix` debe documentarse en el propio archivo). Añadir un
    nuevo dominio en el futuro requiere solo una línea `include_router()` aquí.

#### Step 5: Manejadores de excepción globales y composition root
- Files:
  - `src/presentation/exception_handlers/__init__.py`
  - `src/presentation/exception_handlers/domain_handler.py`
  - `src/presentation/exception_handlers/validation_handler.py`
  - `src/main.py`
- Changes:
  - `domain_handler.py`: handler `DomainException` → `JSONResponse` con
    `status_code=exc.http_status`, body
    `{"success": False, "code": exc.code, "message": exc.message}`.
  - `validation_handler.py`: handler `RequestValidationError` → `JSONResponse`
    con `status_code=422`, body
    `{"success": False, "code": "VALIDATION_ERROR", "details": exc.errors()}`.
  - `main.py`: crea `app = FastAPI(title=settings.app_name, version=settings.app_version)`,
    registra ambos handlers vía `app.exception_handler(...)`, monta
    `app.include_router(api_router, prefix=settings.api_prefix)`. `main.py` no
    debe contener llamadas directas a `include_router` de routers de dominio
    individuales — solo monta `api_router`.

#### Step 6: [Repository Interface] — no aplica
No hay entidades de dominio ni interfaces de repositorio en esta historia
(fuera de la carpeta placeholder creada en el Step 1). Se omite este paso.

#### Step 7: [DTOs] — no aplica
No hay DTOs de request/response de negocio en esta historia — el único
endpoint (`/health`) devuelve un `dict` literal, no un DTO Pydantic. Se omite
este paso.

#### Step 8: Documentación técnica del README
- File: `README.md`
- Content: nueva sección "Arquitectura del Backend" con:
  - Árbol de carpetas bajo `src/` y una línea de propósito por paquete.
  - Reglas de dependencia entre capas (dominio no depende de FastAPI ni
    SQLAlchemy; infraestructura implementa las interfaces del dominio;
    presentación es la única capa que conoce FastAPI).
  - Guía paso a paso "Cómo agregar un nuevo dominio", enlazando los archivos
    concretos a crear/modificar (coincide con la tabla de archivos de esta
    historia: modelo de dominio, interfaz de repositorio, servicio de
    aplicación, DTOs, router y su registro en
    `presentation/routers/__init__.py`).
  - Comando para levantar el servidor local
    (`uvicorn src.main:app --reload`) y URLs de `/docs` y `/redoc`.
  - Enlace a `ai-specs/specs/stacks/python-fastapi-standards.mdc` como
    referencia normativa completa, en vez de duplicar su contenido.

#### Step 9: Configuración de build, lint y cobertura
- Files:
  - `pyproject.toml` (crear — no existe en el repo)
  - `requirements.txt` (modificar)
- Changes:
  - `requirements.txt`: agregar `fastapi`, `uvicorn[standard]`,
    `pydantic-settings`, `httpx` (además de `pytest`/`pytest-cov` ya
    presentes).
  - `pyproject.toml`: sección `[tool.pytest.ini_options]` con
    `addopts = "--cov=src --cov-fail-under=90"` (o configuración equivalente
    de `--cov-report`), `[tool.ruff]` apuntando a `src/`, `[tool.mypy]` con
    `strict = true` sobre `src/`. Revisar si `pytest.ini` existente debe
    migrarse a `pyproject.toml` o coexistir sin conflicto — preferir
    consolidar en `pyproject.toml` y eliminar `pytest.ini` para evitar
    configuración duplicada.

#### Step 10: Unit Tests
- Test files:
  - `tests/presentation/__init__.py` (nuevo paquete de test)
  - `tests/presentation/test_health_router.py`
  - `tests/infrastructure/__init__.py` (nuevo paquete de test)
  - `tests/infrastructure/test_settings.py`
- Cases to cover:
  - **Happy path**: `GET /health` responde `200` con `status: "ok"` y los
    campos `app`/`version` provenientes de `Settings`.
  - **Registro de routers**: `api_router` incluye el router de `health` bajo
    el prefijo esperado — verificado inspeccionando `app.routes`.
  - **Manejador de excepción de dominio**: una ruta de prueba que levanta una
    `DomainException` personalizada devuelve
    `{"success": false, "code": ..., "message": ...}` con el `http_status`
    configurado en la excepción.
  - **Manejador de validación**: un request con payload inválido a una ruta
    de prueba devuelve `422` con
    `{"success": false, "code": "VALIDATION_ERROR", "details": [...]}`.
  - **Configuración**: `Settings()` carga valores por defecto y los
    sobrescribe correctamente desde variables de entorno
    (`monkeypatch.setenv`).
  - **Edge case**: la aplicación arranca (`TestClient(app)`) sin lanzar
    excepciones aunque no exista ningún router de dominio adicional
    registrado todavía.

#### Step N: Update Technical Documentation
- `README.md` — ya cubierto en Step 8 (sección "Arquitectura del Backend").
- `ai-specs/specs/data-model.md` — no aplica, no hay cambios de esquema en
  esta historia.
- `ai-specs/specs/api-spec.yml` — no existe en el repo todavía; si se crea en
  un ticket posterior, añadir ahí el contrato de `GET /health`. No bloquea
  esta historia.
- `ai-specs/specs/stacks/python-fastapi-standards.mdc` — sin cambios; el
  README solo debe enlazarlo, no duplicarlo (ver Step 8).

## 4. Implementation Order

1. Step 0 — Crear rama `feature/SP-137-backend`
2. Step 1 — Estructura de paquetes base
3. Step 2 — Excepción base de dominio (`DomainException`)
4. Step 3 — Configuración tipada (`Settings`)
5. Step 4 — Router agregador y router de `health`
6. Step 5 — Manejadores de excepción globales y `main.py`
7. Step 9 — Configuración de `pyproject.toml` / `requirements.txt`
8. Step 10 — Unit tests
9. Step 8 — Documentación técnica del README

## 5. Testing Checklist

- [ ] `pytest` pasa con 0 fallos
- [ ] `pytest --cov --cov-report=html` muestra >= 90% sobre `src/`
- [ ] `GET /health` probado manualmente (`uvicorn src.main:app --reload` +
      `curl http://localhost:8000/health`)
- [ ] `/docs` y `/redoc` cargan sin errores
- [ ] Tests existentes (`tests/test_example.py`) no se rompen

## 6. Tooling Reference

| Purpose | Command |
|---|---|
| Build | `pip install -r requirements.txt` |
| Test | `pytest` |
| Run | `uvicorn main:app --reload` (ver Nota en sección 9 sobre el path real `src.main:app`) |
| Coverage | `pytest --cov --cov-report=html` |

## 7. Error Response Format

```json
{
  "success": false,
  "code": "ERROR_CODE",
  "message": "Human-readable description",
  "details": ["field: validation message"]
}
```
HTTP mapping: 400 VALIDATION_ERROR | 404 NOT_FOUND | 409 CONFLICT | 422 BUSINESS_RULE_VIOLATION | 500 INTERNAL_ERROR

## 8. Dependencies

Nuevas dependencias a agregar en `requirements.txt`:
- `fastapi` — framework web
- `uvicorn[standard]` — servidor ASGI para desarrollo local
- `pydantic-settings` — configuración tipada vía `BaseSettings`
- `httpx` — cliente HTTP requerido por `TestClient`/`AsyncClient` en tests de
  integración

Instalación: `pip install -r requirements.txt`

## 9. Notes

- Esta historia **no** implementa lógica de negocio ni persistencia —
  únicamente el armazón estructural, el mecanismo de registro de rutas y su
  documentación.
- El comando `run_command` documentado en `openspec/config.yaml`
  (`uvicorn main:app --reload`) asume un módulo `main` en la raíz; dado que
  el punto de entrada real queda en `src/main.py`, el comando correcto para
  levantar la app es `uvicorn src.main:app --reload`. Señalar esta
  discrepancia en el README (Step 8) para evitar confusión en el onboarding.
- Decisión pendiente a documentar en `health_router.py`/README: si `/health`
  se expone bajo `settings.api_prefix` (`/api/v1/health`) o fuera del
  versionado (`/health` a secas) como es convención común para liveness
  probes. El plan no prescribe la respuesta — debe decidirse y documentarse
  explícitamente durante la implementación (Step 4).
- No existe `pyproject.toml` en el repo actualmente; este ticket lo crea
  desde cero (Step 9) en vez de "modificarlo".
- `domain/` y `application/` deben permanecer libres de imports de `fastapi`
  y `sqlalchemy` — verificable con `ruff` o una búsqueda estática simple
  (`grep -r "^import fastapi\|^from fastapi\|^import sqlalchemy\|^from sqlalchemy" src/domain src/application`).

## 10. Implementation Verification Checklist

- [ ] Code quality: sin errores de compilación, `ruff check` sin
      advertencias sobre `src/`, `mypy --strict` sin errores
- [ ] Domain: `DomainException` expone `code`, `http_status`, `message`
      tipados; sin dependencias de FastAPI/SQLAlchemy
- [ ] Application: paquetes creados (`services`, `dto`, `mappers`) sin lógica
      de negocio todavía — placeholders válidos
- [ ] Presentation: `health_router.py` es un router delgado; `main.py` no
      conoce routers de dominio individuales, solo `api_router`
- [ ] Migrations: no aplica — sin cambios de esquema en esta historia
- [ ] Tests: todos en verde, cobertura >= 90%, casos happy path / excepción
      de dominio / validación / configuración / arranque sin routers extra
      cubiertos
- [ ] Documentation: `README.md` actualizado con la sección "Arquitectura
      del Backend" y guía "Cómo agregar un nuevo dominio"
