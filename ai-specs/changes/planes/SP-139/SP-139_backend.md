# Backend Implementation Plan: SP-139 Configuración de Entornos Base (Python + Angular)

## 1. Overview

Dejar operativa la infraestructura base del backend **SST Auditor Agent Pro** para que
el frontend Angular (repositorio `sst-auditor-agent-pro-frontend`, puerto 4200) pueda
comunicarse con el API sin fricción:

1. **CORS**: campo `origenes_cors: list[str]` en `Settings` (default
   `["http://localhost:4200"]`, sobreescribible vía `ORIGENES_CORS`) y registro de
   `CORSMiddleware` en `src/main.py`.
2. **Endpoint de conectividad**: `GET /api/v1/ping` → `200 {"mensaje": "pong"}`,
   modelado con DTO Pydantic `RespuestaPing`, tag `Salud`.
3. **Calidad automatizada**: `.pre-commit-config.yaml` con Ruff (lint + format), mypy
   y hooks de higiene; documentación del flujo Gitflow en `README.md`.
4. **Gestión de dependencias con Poetry**: formalizar `pyproject.toml` (grupos `main`
   y `dev`), generar `poetry.lock` versionado y actualizar `README.md` e integración CI.

**Estado actual (SP-137/SP-138 — no rehacer):** app FastAPI en `src/main.py` con DDD,
`GET /health` operativo, manejadores globales con contrato único `RespuestaError`
(`exito`, `codigo`, `mensaje`, `detalle`), `Settings` tipado (`app_name`, `app_version`,
`api_prefix`, `log_level`), pytest con cobertura ≥ 90 %, Ruff y mypy `strict` en
`pyproject.toml`.

**Fuera de alcance en este repositorio:** la inicialización del proyecto Angular +
Tailwind (SP-172) vive en el repo frontend; aquí solo se garantiza que el backend
acepte su origen por CORS.

Stack activo: `python-fastapi` (Python 3.12 + FastAPI).

## 2. Architecture Context

- Active stack: `python-fastapi` (`Python 3.12 + FastAPI`)
- Sin cambios de dominio ni de base de datos: el ticket toca configuración
  (Infrastructure), un DTO (Application), un router (Presentation) y tooling.

| Capa | Archivos afectados |
|---|---|
| Application | `src/application/dto/respuesta_ping.py` (crear), `src/application/dto/__init__.py` (modificar) |
| Presentation | `src/presentation/routers/ping_router.py` (crear), `src/presentation/routers/__init__.py` (modificar), `src/main.py` (modificar — composición: `CORSMiddleware`) |
| Infrastructure | `src/infrastructure/config/settings.py` (modificar — `origenes_cors`) |
| Tooling | `.pre-commit-config.yaml` (crear), `pyproject.toml` (modificar — Poetry), `poetry.lock` (crear), `requirements.txt` (regenerar vía `poetry export`), `.env.example` (modificar), `.github/workflows/ci.yml` (verificar/ajustar) |
| Tests | `tests/presentation/test_ping_router.py` (crear), `tests/presentation/test_cors.py` (crear), `tests/infrastructure/test_settings.py` (modificar) |
| Docs | `README.md` (modificar), `ai-specs/specs/api-spec.yml` (modificar) |

### Subtask Mapping

| Subtask key | Summary | Implementation Step(s) |
|---|---|---|
| `SP-170` | Configurar Gitflow y hooks de linter pre-commit | Step 7, Step 9 (README) |
| `SP-171` | Configurar entorno virtual Python con Poetry | Step 6, Step 9 (README, CI) |
| `SP-172` | Inicializar proyecto Angular con Tailwind CSS | Fuera de alcance aquí — repo frontend; el backend solo habilita su origen (Step 2, Step 3) |
| `SP-173` | Validar conectividad ping/pong backend-frontend (CORS) | Step 2, Step 3, Step 4, Step 5, Step 8, Step 9 |

## 3. Implementation Steps

> Enfoque TDD: en cada paso funcional, escribir primero la prueba que falla y luego
> el código que la hace pasar. Los casos se detallan en el Step 8 pero se ejecutan
> intercalados con cada paso.

#### Step 0: Create Feature Branch
- **Action**: Crear y cambiar a la rama feature (la rama `feature/SP-139-backend` según Gitflow)
- **Branch**: `feature/SP-139-backend`
- **Commands**:
  ```bash
  git checkout main && git pull origin main
  git checkout -b feature/SP-139-backend
  ```

#### Step 1: [Schema Migration — no aplica]
- Sin cambios de base de datos. No se crean migraciones Alembic.

#### Step 2: [Infrastructure — `Settings.origenes_cors`]
- **File**: `src/infrastructure/config/settings.py`
- **Changes**: agregar a `Settings` el campo:
  ```python
  origenes_cors: list[str] = ["http://localhost:4200"]
  ```
  - pydantic-settings mapea automáticamente la variable de entorno `ORIGENES_CORS`
    y, por ser tipo complejo (`list[str]`), la parsea como **JSON**:
    `ORIGENES_CORS='["http://localhost:4200"]'`.
  - Nota mypy strict: el default mutable en un `BaseSettings` de Pydantic v2 es
    seguro (Pydantic hace deep-copy por instancia); no requiere `Field(default_factory=...)`,
    aunque puede usarse si Ruff (regla B) lo objetara.
- **File**: `.env.example` — documentar en la sección `── Aplicación ──`:
  ```bash
  # Orígenes permitidos por CORS (JSON array). El frontend Angular corre en 4200.
  # ORIGENES_CORS='["http://localhost:4200"]'
  ```

#### Step 3: [Composición — `CORSMiddleware` en `src/main.py`]
- **File**: `src/main.py`
- **Changes**: registrar el middleware inmediatamente después de crear `app` y antes
  de `include_router`:
  ```python
  from fastapi.middleware.cors import CORSMiddleware

  app.add_middleware(
      CORSMiddleware,
      allow_origins=settings.origenes_cors,
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```
- **Restricción de seguridad**: los orígenes provienen exclusivamente de `Settings`;
  **prohibido** `allow_origins=["*"]` combinado con `allow_credentials=True`
  (Starlette lo degradaría y es una mala práctica de seguridad).

#### Step 4: [DTO — `RespuestaPing`]
- **File (crear)**: `src/application/dto/respuesta_ping.py`
  ```python
  class RespuestaPing(BaseModel):
      """Respuesta del endpoint de conectividad ping/pong."""

      mensaje: str = Field(examples=["pong"])
  ```
  (Pydantic v2; el ejemplo queda reflejado en el esquema OpenAPI de `/docs`.)
- **File (modificar)**: `src/application/dto/__init__.py` — exportar `RespuestaPing`
  junto a `RespuestaError` (import + `__all__`).

#### Step 5: [Router — `GET /api/v1/ping`]
- **File (crear)**: `src/presentation/routers/ping_router.py`
  - `router = APIRouter(tags=["Salud"])`
  - Endpoint:
    ```python
    @router.get("/ping", status_code=http_status.HTTP_200_OK, response_model=RespuestaPing)
    async def ping() -> RespuestaPing:
        """Endpoint de conectividad para validar la comunicación con el frontend."""
        return RespuestaPing(mensaje="pong")
    ```
  - Sin I/O ni acceso a base de datos (latencia < 10 ms local); no necesita `Depends`.
- **File (modificar)**: `src/presentation/routers/__init__.py`
  - Montar el nuevo router bajo el prefijo de configuración, siguiendo la plantilla
    documentada en el propio módulo:
    ```python
    from src.infrastructure.config.settings import get_settings
    from src.presentation.routers.ping_router import router as ping_router

    settings = get_settings()
    api_router.include_router(ping_router, prefix=settings.api_prefix)
    ```
  - Ruta final: `/api/v1/ping`. `/health` permanece sin prefijo (sin cambios).
  - `GET /ping` (sin prefijo) debe responder `404` con esquema `RespuestaError`
    (ya cubierto por el `http_handler` de SP-138) y `POST /api/v1/ping` un `405`.

#### Step 6: [Tooling — Poetry (SP-171)]
- **File**: `pyproject.toml` — **conservar intactas** las secciones existentes de
  pytest, coverage, Ruff y mypy. Completar:
  - `[project]`: mantener metadatos actuales, declarar dependencias principales:
    `fastapi`, `uvicorn[standard]`, `pydantic-settings` (versiones compatibles con
    las hoy fijadas en `requirements.txt`).
  - Grupo dev (`[tool.poetry.group.dev.dependencies]`): `pytest`, `pytest-asyncio`,
    `pytest-cov`, `httpx`, `ruff`, `mypy`, `pre-commit`.
  - Build backend:
    ```toml
    [build-system]
    requires = ["poetry-core>=1.9"]
    build-backend = "poetry.core.masonry.api"
    ```
    (Poetry ≥ 1.8/2.x soporta la tabla `[project]` estándar; si la versión instalada
    lo exige, añadir `[tool.poetry]` con `package-mode = false` para un proyecto
    no publicable.)
- **Commands**:
  ```bash
  pipx install poetry
  poetry config virtualenvs.in-project true   # venv en .venv/ (ya en .gitignore)
  poetry lock
  poetry install
  poetry check
  poetry run pytest
  poetry run uvicorn src.main:app --reload    # verificación de arranque
  ```
- **File**: `poetry.lock` — versionar el archivo generado.
- **File**: `requirements.txt` — el CI actual (`.github/workflows/ci.yml`, paso
  `pip install -r requirements.txt`) lo consume, y hoy mezcla dependencias de runtime
  y de test. Decisión: **mantenerlo exportado** para no acoplar este ticket a una
  migración del CI:
  ```bash
  poetry export -f requirements.txt -o requirements.txt --with dev --without-hashes
  ```
  (En Poetry 2.x `export` requiere el plugin: `pipx inject poetry poetry-plugin-export`.)
  Documentar en `README.md` que `requirements.txt` es un artefacto generado — la
  fuente de verdad es `poetry.lock`. Alternativa aceptada por el ticket: migrar el
  paso del CI a `pipx install poetry && poetry install` y eliminar `requirements.txt`;
  si se opta por ella, hacerlo en este mismo cambio y verificar el CI en verde.

#### Step 7: [Tooling — pre-commit (SP-170)]
- **File (crear)**: `.pre-commit-config.yaml` en la raíz:
  ```yaml
  repos:
    - repo: https://github.com/pre-commit/pre-commit-hooks
      rev: v5.0.0            # fijar a la última versión estable disponible
      hooks:
        - id: trailing-whitespace
        - id: end-of-file-fixer
        - id: check-yaml
        - id: check-merge-conflict
    - repo: https://github.com/astral-sh/ruff-pre-commit
      rev: v0.15.20          # alinear con la versión de ruff del grupo dev
      hooks:
        - id: ruff
          args: [--fix]
        - id: ruff-format
    - repo: local
      hooks:
        - id: mypy
          name: mypy (strict, config del proyecto)
          entry: poetry run mypy
          language: system
          types: [python]
          pass_filenames: false
  ```
  - **Decisión**: mypy como hook `local` (no `mirrors-mypy`) para ejecutar con el
    entorno del proyecto — así usa la configuración `strict` de `pyproject.toml` y
    ve las dependencias reales (pydantic, fastapi); el mirror corre en un venv
    aislado y produce falsos positivos por stubs ausentes.
  - **Decisión (del ticket)**: **no** se instala Flake8 — Ruff ya cubre las reglas
    E/F y más; dos linters divergirían. ESLint pertenece al repo frontend (SP-172).
  - NFR: los hooks deben ejecutar en < ~10 s por commit (Ruff es casi instantáneo;
    mypy con `pass_filenames: false` analiza `src/` según su config y usa caché).
- **Commands**:
  ```bash
  poetry run pre-commit install
  poetry run pre-commit run --all-files   # corregir cualquier hallazgo
  ```
- **Verificación manual (documentar en el PR)**: un commit con código que viola Ruff
  (p. ej. import sin usar) debe ser rechazado localmente por el hook.

#### Step 8: [Unit Tests]
Todos con pytest + httpx (patrón AAA, convención `test_deberia_..._cuando_...` /
`test_should_..._when_...` ya usada en el repo). Para los tests HTTP puede usarse
`TestClient` (como en `tests/presentation/test_health_router.py`) o
`httpx.AsyncClient` con `ASGITransport` — mantener el patrón existente del repo.

- **File (crear)**: `tests/presentation/test_ping_router.py`
  - `test_deberia_responder_pong_cuando_se_consulta_ping` — `GET /api/v1/ping` →
    `200` y cuerpo **exacto** `{"mensaje": "pong"}`.
  - `test_deberia_responder_404_cuando_falta_el_prefijo` — `GET /ping` → `404` con
    esquema `RespuestaError` (`exito == False`, `codigo == "ERROR_HTTP"`).
  - `test_deberia_responder_405_cuando_metodo_no_soportado` — `POST /api/v1/ping` →
    `405` con esquema `RespuestaError`.
  - `test_deberia_documentar_ping_bajo_tag_salud` — el esquema OpenAPI de la app
    (`app.openapi()`) registra `/api/v1/ping` con tag `Salud`.
- **File (crear)**: `tests/presentation/test_cors.py`
  - Usar la app real (`src.main.app`) para probar el middleware registrado.
  - `test_deberia_permitir_origen_configurado_cuando_preflight` —
    `OPTIONS /api/v1/ping` con cabeceras `Origin: http://localhost:4200` y
    `Access-Control-Request-Method: GET` → respuesta con
    `access-control-allow-origin: http://localhost:4200`.
  - `test_deberia_omitir_cabecera_cors_cuando_origen_no_permitido` — preflight con
    `Origin: http://malicioso.example` → la cabecera `access-control-allow-origin`
    **no** está presente.
  - `test_deberia_incluir_cabecera_cors_cuando_get_con_origen_permitido` — `GET`
    simple con `Origin: http://localhost:4200` → `200` y cabecera de origen presente
    (`access-control-allow-credentials: true`).
- **File (modificar)**: `tests/infrastructure/test_settings.py`
  - `test_deberia_usar_origen_localhost_4200_por_defecto` — `Settings(_env_file=None)`
    → `origenes_cors == ["http://localhost:4200"]`.
  - `test_deberia_leer_origenes_cors_desde_entorno` — con
    `monkeypatch.setenv("ORIGENES_CORS", '["https://app.example.com"]')` →
    `origenes_cors == ["https://app.example.com"]`. Si el caso necesita la instancia
    cacheada, limpiar el `lru_cache` con `get_settings.cache_clear()` (y restaurar
    al final para no contaminar otros tests).
- **Regresión**: `tests/presentation/test_health_router.py`,
  `tests/presentation/test_exception_handlers.py` y `tests/test_main.py` deben
  seguir pasando sin cambios de contrato.
- Ejecutar la suite completa: `poetry run pytest` (cobertura ≥ 90 % vía
  `--cov-fail-under=90` ya configurado), más `poetry run ruff check .` y
  `poetry run mypy`.

#### Step 9: Update Technical Documentation
- **File**: `ai-specs/specs/api-spec.yml` (la spec del proyecto usa extensión `.yml`)
  - Agregar `paths./api/v1/ping.get`: tag `Salud`, respuesta `200` con esquema
    `RespuestaPing` (`mensaje: string`, ejemplo `"pong"`) y `default` →
    `$ref: "#/components/responses/ErrorPorDefecto"`.
  - Agregar `components.schemas.RespuestaPing`.
- **File**: `README.md`
  - Instalación con Poetry (`pipx install poetry`, `poetry install`).
  - Ejecución local: `poetry run uvicorn src.main:app --reload` (puerto 8000).
  - Tests: `poetry run pytest`.
  - Activación de hooks: `poetry run pre-commit install`.
  - Flujo Gitflow: rama base `main`, ramas `feature/SP-XX-backend`, merge vía Pull
    Request con review.
  - Validación de conectividad ping/pong con el frontend (backend en 8000,
    `ng serve` en 4200; el componente raíz muestra «pong» sin errores CORS en consola).
  - Nota sobre `requirements.txt` como artefacto exportado (si se conserva).
- **File**: `ai-specs/specs/data-model.md` — no cambia (sin cambios de esquema de datos).
- **Validación end-to-end manual (SP-173, documentar en el PR con evidencia)**:
  1. `poetry run uvicorn src.main:app --reload` (8000) + `ng serve` (4200) →
     el navegador muestra «pong», consola sin errores CORS.
  2. Prueba negativa: servir el frontend en otro puerto (p. ej. 4300) → el navegador
     bloquea la petición por CORS.
  3. Si el repo frontend (SP-172) aún no existe al momento del PR, dejar la
     evidencia con `curl` (preflight permitido/no permitido) y marcar la validación
     navegador→API como pendiente de SP-172/SP-173.

## 4. Implementation Order

1. **Step 0** — Crear rama `feature/SP-139-backend`.
2. **Step 6** — Migrar a Poetry (`pyproject.toml`, `poetry.lock`, `poetry install`) y
   decidir/ejecutar el destino de `requirements.txt` + CI. Primero, para que el resto
   del trabajo ya corra sobre el entorno definitivo.
3. **Step 2** — `Settings.origenes_cors` + `.env.example` (+ tests de settings).
4. **Step 4** — DTO `RespuestaPing` + export en `dto/__init__.py`.
5. **Step 5** — `ping_router.py` + montaje bajo `settings.api_prefix` (+ tests de ping).
6. **Step 3** — `CORSMiddleware` en `src/main.py` (+ tests de CORS).
7. **Step 7** — `.pre-commit-config.yaml`, `pre-commit install`, `pre-commit run --all-files`.
8. **Step 8** — Suite completa: `pytest` (cobertura ≥ 90 %), `ruff check .`, `mypy`.
9. **Step 9** — `api-spec.yml`, `README.md` y validación manual documentada.

## 5. Testing Checklist

- [ ] `poetry run pytest` pasa con 0 fallos
- [ ] `pytest --cov --cov-report=html` muestra ≥ 90 %
- [ ] `ruff check .` y `mypy` (strict) pasan sin errores
- [ ] `pre-commit run --all-files` pasa sin errores
- [ ] `GET /api/v1/ping` → `200 {"mensaje": "pong"}` y visible en `/docs` bajo tag `Salud`
- [ ] Preflight con `Origin: http://localhost:4200` → cabecera `access-control-allow-origin` presente; con origen no permitido → ausente
- [ ] `GET /ping` (sin prefijo) → `404` y `POST /api/v1/ping` → `405`, ambos con esquema `RespuestaError`
- [ ] `ORIGENES_CORS` desde entorno sobreescribe el default
- [ ] `/health` sigue respondiendo `200` con su contrato actual (sin regresión)
- [ ] CI (`.github/workflows/ci.yml`) en verde con la nueva gestión de dependencias
- [ ] Validación manual navegador→API (o `curl` si el frontend aún no existe) documentada en el PR

## 6. Tooling Reference

| Purpose | Command |
|---|---|
| Build | `poetry install` (antes: `pip install -r requirements.txt`) |
| Test | `poetry run pytest` |
| Run | `poetry run uvicorn src.main:app --reload` |
| Lint | `poetry run ruff check .` / `poetry run mypy` |
| Coverage | `poetry run pytest --cov --cov-report=html` |

## 7. Error Response Format

Contrato único vigente desde SP-138 (DTO `RespuestaError`) — este ticket **no** lo
modifica; `/api/v1/ping` hereda los manejadores globales:

```json
{
  "exito": false,
  "codigo": "CODIGO_ERROR",
  "mensaje": "Descripción legible en español",
  "detalle": null
}
```

| Caso | Status HTTP | `codigo` |
|---|---|---|
| `GET /ping` sin prefijo (ruta inexistente) | 404 | `ERROR_HTTP` |
| `POST /api/v1/ping` (método no soportado) | 405 | `ERROR_HTTP` |
| Excepción no controlada | 500 | `ERROR_INTERNO` |

## 8. Dependencies

| Dependencia | Grupo | Motivo |
|---|---|---|
| `pre-commit` | dev | Framework de hooks de calidad (SP-170) |
| Poetry ≥ 1.8 (herramienta, no dependencia del proyecto) | — | `pipx install poetry`; gestor de entorno y lock (SP-171) |
| `poetry-plugin-export` (solo si Poetry 2.x y se conserva `requirements.txt`) | — | `pipx inject poetry poetry-plugin-export` |

Sin dependencias nuevas de runtime: `CORSMiddleware` es el de
`fastapi.middleware.cors` (Starlette), ya incluido con FastAPI.

## 9. Notes

- **Seguridad CORS**: nunca `allow_origins=["*"]` con `allow_credentials=True`; la
  lista de orígenes proviene exclusivamente de `Settings`. Ningún secreto en el repo
  (`.env` fuera de git; `.env.example` como plantilla).
- **`ORIGENES_CORS` es un JSON array**: pydantic-settings parsea los tipos complejos
  como JSON — el valor debe ir con comillas dobles internas:
  `ORIGENES_CORS='["http://localhost:4200"]'`. Un valor mal formado hará fallar el
  arranque con `ValidationError` (comportamiento aceptado: fail-fast de configuración).
- **Orden de registro del middleware**: `app.add_middleware(CORSMiddleware, ...)` debe
  ejecutarse antes de que la app reciba tráfico; mantenerlo junto a la creación de
  `app` en `src/main.py`, antes de `include_router` por legibilidad.
- **No instalar Flake8** (decisión del ticket): Ruff cubre E/F y más; dos linters
  divergirían. ESLint corresponde al repo frontend (SP-172).
- **Conservar la configuración existente de `pyproject.toml`**: las secciones de
  pytest (incluido `--cov-fail-under=90`), coverage, Ruff (con sus `ignore` B008/N818
  justificados) y mypy strict no se tocan al introducir Poetry.
- **CI**: el workflow actual instala con `pip install -r requirements.txt`; si se
  conserva ese paso, el `requirements.txt` exportado debe incluir el grupo dev
  (`--with dev`) porque el CI ejecuta pytest. Si se migra el CI a Poetry, hacerlo en
  este mismo cambio y dejar el pipeline en verde antes del merge.
- **Prefijo desde configuración**: el montaje de `ping_router` usa
  `settings.api_prefix` (no el literal `/api/v1`), coherente con la plantilla
  documentada en `src/presentation/routers/__init__.py`.
- **Trazabilidad**: commits convencionales (`feat`, `chore`, `test`) en
  `feature/SP-139-backend`; PR hacia `main`.
- Este ticket no toca conceptos del dominio SST (peligros, riesgos, auditorías), por
  lo que no requiere validación contra `.sst-agent-document.md`.

## 10. Implementation Verification Checklist

- [ ] Code quality: `ruff check .` y `mypy` (strict) sin errores; type hints en todas las firmas nuevas
- [ ] Domain: sin cambios — capa de dominio permanece pura
- [ ] Application: `RespuestaPing` (Pydantic v2) exportado en `dto/__init__.py`
- [ ] Presentation: router delgado, `response_model=RespuestaPing`, montado bajo `settings.api_prefix`; middleware CORS registrado en composición (`src/main.py`)
- [ ] Migrations: no aplica (sin cambios de esquema de datos)
- [ ] Tests: todos en verde, cobertura ≥ 90 %, cubiertos 200, 404, 405 y preflight permitido/no permitido
- [ ] Tooling: `.pre-commit-config.yaml` operativo (`pre-commit run --all-files` verde), `poetry.lock` versionado, `poetry check` pasa, CI en verde
- [ ] Documentation: `api-spec.yml` incorpora `/api/v1/ping` + `RespuestaPing`; `README.md` documenta Poetry, pre-commit, Gitflow y validación ping/pong; `.env.example` documenta `ORIGENES_CORS`

<!--
## Validación manual de endpoints (Step 5 — ejecutada el 2026-07-14)

App levantada con: poetry run uvicorn src.main:app --port 8000

# Happy path (200)
curl -i http://localhost:8000/api/v1/ping
#   → HTTP/1.1 200 OK  {"mensaje":"pong"}

# Ruta sin prefijo (404, esquema RespuestaError)
curl -i http://localhost:8000/ping
#   → HTTP/1.1 404 Not Found  {"exito":false,"codigo":"ERROR_HTTP","mensaje":"Not Found","detalle":null}

# Método no soportado (405, esquema RespuestaError)
curl -i -X POST http://localhost:8000/api/v1/ping
#   → HTTP/1.1 405 Method Not Allowed  {"exito":false,"codigo":"ERROR_HTTP","mensaje":"Method Not Allowed","detalle":null}

# Preflight CORS — origen permitido
curl -i -X OPTIONS http://localhost:8000/api/v1/ping \
  -H "Origin: http://localhost:4200" -H "Access-Control-Request-Method: GET"
#   → HTTP/1.1 200 OK
#     access-control-allow-origin: http://localhost:4200
#     access-control-allow-credentials: true

# Preflight CORS — origen NO permitido (la cabecera no se emite)
curl -i -X OPTIONS http://localhost:8000/api/v1/ping \
  -H "Origin: http://malicioso.example" -H "Access-Control-Request-Method: GET"
#   → sin cabecera access-control-allow-origin

# GET simple con Origin permitido
curl -i http://localhost:8000/api/v1/ping -H "Origin: http://localhost:4200"
#   → HTTP/1.1 200 OK + access-control-allow-origin + access-control-allow-credentials: true

# Regresión
curl -i http://localhost:8000/health
#   → HTTP/1.1 200 OK  {"status":"ok","app":"SST Auditor Agent Pro","version":"0.1.0"}

Nota: la validación navegador→API desde Angular (http://localhost:4200) queda
pendiente de SP-172/SP-173 (el repo frontend aún no está inicializado); la
evidencia curl anterior cubre el preflight permitido/no permitido.
-->
