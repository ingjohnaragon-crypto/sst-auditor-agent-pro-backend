# Backend Implementation Plan: SP-138 Middleware global de control de errores

## 1. Overview

Unificar y completar el control global de errores del backend **SST Auditor Agent Pro**:
toda respuesta fallida del API (4xx y 5xx) debe emitir un único esquema JSON
(`{"exito": false, "codigo": str, "mensaje": str, "detalle": list | dict | null}`),
formalizado en un DTO Pydantic `RespuestaError`.

El ticket SP-137 dejó una base parcial que este ticket completa:

- `src/domain/exceptions/base.py` — `DomainException` (`code="DOMAIN_ERROR"`, `http_status=400`, `message`).
- `src/presentation/exception_handlers/domain_handler.py` — responde `{"success": false, "code", "message"}`.
- `src/presentation/exception_handlers/validation_handler.py` — responde `{"success": false, "code": "VALIDATION_ERROR", "details"}`.
- `src/main.py` — registra ambos manejadores directamente sobre `app` (líneas 18–19).

Problemas a resolver:

1. **Esquema inconsistente** entre manejadores (uno emite `message` sin `details`, el otro `details` sin `message`); no existe DTO que formalice el contrato.
2. **Cobertura incompleta**: `StarletteHTTPException` (404 de ruta, 405 de método) y `Exception` no controlada devuelven hoy el formato por defecto de FastAPI.
3. **Sin observabilidad**: los 500 no dejan traza en el log.

Solución: DTO `RespuestaError`, dos manejadores nuevos (`http_handler`,
`no_controlado_handler`), registro centralizado con
`registrar_manejadores_excepciones(app)`, y logging estándar configurable vía
`Settings.log_level` (`LOG_LEVEL`, por defecto `INFO`).

**Fuera de alcance**: middlewares ASGI personalizados (los exception handlers de
FastAPI son suficientes), integración APM/Sentry, persistencia de errores en BD.

Stack activo: `python-fastapi` (Python 3.12 + FastAPI).

## 2. Architecture Context

- Active stack: `python-fastapi` (`Python 3.12 + FastAPI`)
- Arquitectura DDD por capas; este ticket no crea endpoints nuevos: define el contrato transversal de error.

| Capa | Archivos afectados |
|---|---|
| Domain | `src/domain/exceptions/base.py` (modificar código por defecto) |
| Application | `src/application/dto/respuesta_error.py` (crear), `src/application/dto/__init__.py` (modificar) |
| Presentation | `src/presentation/exception_handlers/domain_handler.py` (modificar), `validation_handler.py` (modificar), `http_handler.py` (crear), `no_controlado_handler.py` (crear), `__init__.py` (modificar), `src/main.py` (modificar) |
| Infrastructure | `src/infrastructure/config/configuracion_logging.py` (crear), `src/infrastructure/config/settings.py` (modificar) |
| Tests | `tests/presentation/test_exception_handlers.py` (modificar), `tests/infrastructure/test_configuracion_logging.py` (crear), `tests/infrastructure/test_settings.py` (modificar) |
| Docs | `ai-specs/specs/api-spec.yml` (componente `RespuestaError`), `.env.example` (`LOG_LEVEL`) |

### Subtask Mapping

| Subtask key | Summary | Implementation Step(s) |
|---|---|---|
| `SP-167` | Crear middleware de manejo global de excepciones | Step 4, Step 5, Step 6 |
| `SP-168` | Estandarizar formato de respuesta de error (JSON) | Step 1, Step 2, Step 3, Step 9 |
| `SP-169` | Agregar logging de errores no controlados | Step 7, Step 8 |

## 3. Implementation Steps

> Enfoque TDD: en cada paso, escribir/adaptar primero la prueba que falla y luego
> el código que la hace pasar. Los pasos de prueba se detallan en el Step 8, pero
> se ejecutan intercalados con cada paso de implementación.

#### Step 0: Create Feature Branch
- **Action**: Crear y cambiar a la rama feature
- **Branch**: `feature/SP-138-backend`
- **Commands**:
  ```bash
  git checkout main && git pull origin main
  git checkout -b feature/SP-138-backend
  ```

#### Step 1: [Schema Migration — no aplica]
- No hay cambios de base de datos en este ticket. No se crean migraciones Alembic.

#### Step 2: [Domain — código por defecto en español]
- **File**: `src/domain/exceptions/base.py`
- **Changes**: cambiar el atributo de clase `code: str = "DOMAIN_ERROR"` por
  `code: str = "ERROR_DOMINIO"`. Actualizar el docstring si menciona el valor.
- La clase permanece pura: sin imports de FastAPI, Starlette ni Pydantic.
- Actualizar cualquier aserción existente en `tests/domain/test_domain_exception.py`
  que dependa del valor `"DOMAIN_ERROR"`.

#### Step 3: [DTO — `RespuestaError`]
- **File (crear)**: `src/application/dto/respuesta_error.py`
- **Content**: clase `RespuestaError(BaseModel)` (Pydantic v2):
  ```python
  class RespuestaError(BaseModel):
      """Contrato único de toda respuesta de error del API."""

      exito: bool = False
      codigo: str
      mensaje: str
      detalle: list[dict[str, object]] | dict[str, object] | None = None
  ```
- **File (modificar)**: `src/application/dto/__init__.py` — exportar `RespuestaError`
  (`from src.application.dto.respuesta_error import RespuestaError` + `__all__`).
- Los manejadores construirán la respuesta con `RespuestaError(...).model_dump()`.

#### Step 4: [Manejadores nuevos — HTTP genérico y error no controlado]
- **File (crear)**: `src/presentation/exception_handlers/http_handler.py`
  - Firma: `async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse`
  - Importar `HTTPException` desde `starlette.exceptions` (captura también los
    404/405 generados por el propio enrutador, no solo los lanzados a mano).
  - Respuesta: `status_code=exc.status_code`, cuerpo
    `RespuestaError(codigo="ERROR_HTTP", mensaje=str(exc.detail), detalle=None).model_dump()`.
  - Log `WARNING` (sin traza) con código, método y ruta.
- **File (crear)**: `src/presentation/exception_handlers/no_controlado_handler.py`
  - Firma: `async def excepcion_no_controlada_handler(request: Request, exc: Exception) -> JSONResponse`
  - Respuesta: 500 con
    `RespuestaError(codigo="ERROR_INTERNO", mensaje="Ha ocurrido un error interno. Contacte al administrador.", detalle=None).model_dump()`.
  - **Nunca** incluir en el cuerpo la traza, el tipo de excepción, `str(exc)` ni rutas de archivos.
  - `logger = logging.getLogger(__name__)` y
    `logger.exception("Error no controlado en %s %s", request.method, request.url.path)`
    (nivel `ERROR` con traza completa). Ver Step 7.

#### Step 5: [Actualizar manejadores existentes al esquema único]
- **File**: `src/presentation/exception_handlers/domain_handler.py`
  - Emitir `RespuestaError(codigo=exc.code, mensaje=exc.message, detalle=None).model_dump()`
    conservando `status_code=exc.http_status`.
  - Agregar log `WARNING` (sin traza) con código, método y ruta.
- **File**: `src/presentation/exception_handlers/validation_handler.py`
  - Emitir 422 con
    `RespuestaError(codigo="ERROR_VALIDACION", mensaje="La petición contiene datos inválidos.", detalle=jsonable_encoder(exc.errors())).model_dump()`.
  - Serializar `exc.errors()` una sola vez (asignarlo a una variable local).
  - Agregar log `WARNING` (sin traza) con código, método y ruta.

#### Step 6: [Registro centralizado de manejadores]
- **File**: `src/presentation/exception_handlers/__init__.py`
- **Content**: función `registrar_manejadores_excepciones(app: FastAPI) -> None`
  que registre los cuatro manejadores:
  ```python
  def registrar_manejadores_excepciones(app: FastAPI) -> None:
      app.add_exception_handler(DomainException, domain_exception_handler)
      app.add_exception_handler(RequestValidationError, validation_exception_handler)
      app.add_exception_handler(StarletteHTTPException, http_exception_handler)
      app.add_exception_handler(Exception, excepcion_no_controlada_handler)
  ```
  (Nota mypy strict: si `add_exception_handler` exige `cast` por la varianza de los
  tipos de handler, usar `app.exception_handler(Tipo)(handler)` o un `cast` explícito
  y documentarlo con un comentario.)
- **File**: `src/main.py` — reemplazar las dos llamadas `app.exception_handler(...)`
  (líneas 18–19) y sus imports por una única llamada a
  `registrar_manejadores_excepciones(app)`.

#### Step 7: [Infrastructure — logging configurable]
- **File (crear)**: `src/infrastructure/config/configuracion_logging.py`
  - Función `configurar_logging(nivel: str = "INFO") -> None`:
    - Normalizar el nivel a mayúsculas y validarlo (p. ej. con
      `logging.getLevelName(nivel)` — si el resultado no es un `int`, el nivel es
      inválido); ante un nivel inválido degradar a `INFO` sin lanzar excepción.
    - Invocar `logging.basicConfig(level=..., format="%(asctime)s %(levelname)s %(name)s %(message)s")`.
- **File (modificar)**: `src/infrastructure/config/settings.py`
  - Agregar campo `log_level: str = "INFO"` a `Settings` (pydantic-settings ya lo
    mapea desde la variable de entorno `LOG_LEVEL`).
- **File (modificar)**: `src/main.py`
  - Invocar `configurar_logging(settings.log_level)` inmediatamente después de
    `settings = get_settings()` y antes de crear la instancia `app`.
- **File (modificar)**: `.env.example` — documentar `LOG_LEVEL` en una nueva sección
  de configuración de la aplicación:
  ```bash
  # ── Aplicación ────────────────────────────────────────────────
  # Nivel de log del backend: DEBUG | INFO | WARNING | ERROR | CRITICAL
  # LOG_LEVEL=INFO
  ```
- **Restricción de seguridad**: ningún mensaje de log incluye cuerpos de petición,
  cabeceras, tokens ni credenciales; solo código de error, método HTTP y ruta.

#### Step 8: [Unit Tests]
- **File (modificar)**: `tests/presentation/test_exception_handlers.py`
  - Reconstruir la app de prueba usando `registrar_manejadores_excepciones(app)` en
    lugar de registrar manejadores a mano; agregar un endpoint que lance `RuntimeError`.
  - Instanciar `TestClient(app, raise_server_exceptions=False)` para que el manejador
    de `Exception` sea quien responda.
  - Casos (patrón AAA, nombres `test_should_..._when_...`):
    - `test_should_devolver_esquema_error_cuando_se_lanza_domain_exception` —
      `DomainException("recurso no encontrado", code="NOT_FOUND", http_status=404)`
      → 404 y cuerpo exacto `{exito: false, codigo: "NOT_FOUND", mensaje: ..., detalle: null}`.
    - `test_should_devolver_error_dominio_por_defecto_cuando_no_se_da_codigo` —
      `DomainException("x")` → `codigo == "ERROR_DOMINIO"`.
    - `test_should_devolver_error_validacion_cuando_payload_es_invalido` — POST con
      cuerpo vacío → 422, `codigo == "ERROR_VALIDACION"`, `mensaje` legible,
      `detalle` lista no vacía.
    - `test_should_devolver_esquema_error_cuando_ruta_no_existe` — GET `/no-existe`
      → 404 con `codigo == "ERROR_HTTP"` (manejador de `StarletteHTTPException`).
    - `test_should_devolver_500_generico_cuando_excepcion_no_controlada` — endpoint
      que lanza `RuntimeError("secreto interno")` → 500, `codigo == "ERROR_INTERNO"`,
      mensaje genérico.
    - `test_should_no_exponer_traza_en_respuesta_cuando_falla_interno` — el cuerpo
      del 500 no contiene `"Traceback"`, `"RuntimeError"`, `"secreto interno"` ni
      nombres de archivo (`.py`).
    - `test_should_registrar_traza_cuando_excepcion_no_controlada` — con `caplog`:
      registro de nivel `ERROR` que incluye método HTTP, ruta y traza (`exc_info`).
    - `test_should_registrar_warning_cuando_error_de_dominio` — con `caplog`:
      nivel `WARNING` sin traza para dominio/validación.
- **File (crear)**: `tests/infrastructure/test_configuracion_logging.py`
  - `test_should_usar_nivel_info_cuando_log_level_no_definido` — nivel por defecto `INFO`.
  - `test_should_aplicar_nivel_debug_cuando_log_level_es_debug` — nivel efectivo `DEBUG`.
  - `test_should_degradar_a_info_cuando_nivel_es_invalido` — `"NO_EXISTE"` → `INFO`
    sin lanzar excepción.
  - Verificar el formato configurado (`%(asctime)s %(levelname)s %(name)s %(message)s`).
  - Nota: `logging.basicConfig` no reconfigura un root logger ya inicializado; en las
    pruebas usar `force=True` en la implementación o resetear los handlers del root
    logger en un fixture para que cada caso sea determinista.
- **File (modificar)**: `tests/infrastructure/test_settings.py`
  - Extender los tests existentes: valor por defecto `log_level == "INFO"` y lectura
    de `LOG_LEVEL` desde el entorno con `monkeypatch.setenv`.
- **Regresión**: `tests/presentation/test_health_router.py` y `tests/test_main.py`
  deben seguir pasando sin cambios de contrato (`/health` → 200).

#### Step 9: Update Technical Documentation
- **File**: `ai-specs/specs/api-spec.yml`
  - Agregar `components.schemas.RespuestaError` con los campos `exito` (bool),
    `codigo` (string), `mensaje` (string), `detalle` (nullable, `oneOf` array/object),
    con ejemplos para 422 y 500.
  - Referenciarlo como respuesta de error por defecto (p. ej. `components.responses.ErrorPorDefecto`
    y/o respuestas `4XX`/`5XX` reutilizables), sin alterar el contrato 200 de `/health`.
- **File**: `ai-specs/specs/data-model.md` — no cambia (sin cambios de esquema de datos).

## 4. Implementation Order

1. **Step 0** — Crear rama `feature/SP-138-backend`.
2. **Step 2** — `DomainException.code` → `"ERROR_DOMINIO"` (+ test de dominio).
3. **Step 3** — Crear DTO `RespuestaError` y exportarlo.
4. **Step 7** — `configuracion_logging.py` + `Settings.log_level` + `.env.example` (+ tests de infraestructura).
5. **Step 5** — Actualizar `domain_handler.py` y `validation_handler.py` al esquema único con log `WARNING`.
6. **Step 4** — Crear `http_handler.py` y `no_controlado_handler.py`.
7. **Step 6** — `registrar_manejadores_excepciones(app)` y simplificar `src/main.py` (incluye llamada a `configurar_logging`).
8. **Step 8** — Completar y ejecutar toda la suite de pruebas (`pytest`, cobertura ≥ 90 %).
9. **Step 9** — Actualizar `ai-specs/specs/api-spec.yml` con el componente `RespuestaError`.

## 5. Testing Checklist

- [ ] `pytest` pasa con 0 fallos
- [ ] `pytest --cov --cov-report=html` muestra ≥ 90 %
- [ ] `ruff check .` y `mypy --strict` pasan sin errores
- [ ] Verificación manual de los cuatro casos de error: `DomainException`, payload inválido (422), ruta inexistente (404 `ERROR_HTTP`), excepción no controlada (500 `ERROR_INTERNO`)
- [ ] El cuerpo del 500 no expone traza, tipo de excepción ni rutas de archivos
- [ ] El log registra el 500 con nivel `ERROR`, traza, método y ruta; dominio/validación a `WARNING` sin traza
- [ ] `LOG_LEVEL=DEBUG` cambia el nivel efectivo; un valor inválido degrada a `INFO`
- [ ] `/health` sigue respondiendo 200 con su contrato actual (sin regresión)

## 6. Tooling Reference

| Purpose | Command |
|---|---|
| Build | `pip install -r requirements.txt` |
| Test | `pytest` |
| Run | `uvicorn main:app --reload` |
| Lint | `ruff check .` |
| Coverage | `pytest --cov --cov-report=html` |

## 7. Error Response Format

Este ticket **redefine** el contrato de error del proyecto. A partir de SP-138 el
esquema único (DTO `RespuestaError`) es:

```json
{
  "exito": false,
  "codigo": "CODIGO_ERROR",
  "mensaje": "Descripción legible en español",
  "detalle": null
}
```

Mapeo excepción → respuesta:

| Excepción capturada | Status HTTP | `codigo` | `detalle` |
|---|---|---|---|
| `DomainException` (y subclases) | `exc.http_status` | `exc.code` (por defecto `ERROR_DOMINIO`) | `null` |
| `RequestValidationError` | 422 | `ERROR_VALIDACION` | `jsonable_encoder(exc.errors())` |
| `StarletteHTTPException` | `exc.status_code` | `ERROR_HTTP` | `null` |
| `Exception` (no controlada) | 500 | `ERROR_INTERNO` | `null` |

Ejemplos:

```json
// 422 — validación
{
  "exito": false,
  "codigo": "ERROR_VALIDACION",
  "mensaje": "La petición contiene datos inválidos.",
  "detalle": [{"loc": ["body", "name"], "msg": "Field required", "type": "missing"}]
}

// 500 — error no controlado
{
  "exito": false,
  "codigo": "ERROR_INTERNO",
  "mensaje": "Ha ocurrido un error interno. Contacte al administrador.",
  "detalle": null
}
```

## 8. Dependencies

Ninguna dependencia nueva. Se usa `logging` de la biblioteca estándar de Python,
Pydantic v2 y Starlette/FastAPI ya presentes en `requirements.txt`.

## 9. Notes

- **Ruptura de contrato aceptada**: el cambio `success/code/message` →
  `exito/codigo/mensaje/detalle` rompe el formato de SP-137, aceptable en `0.1.0`
  porque aún no hay consumidores externos. Debe quedar reflejado en `api-spec.yml`.
- **Importar `HTTPException` desde `starlette.exceptions`** en `http_handler.py`:
  registrar el manejador sobre la clase de Starlette captura también los 404/405
  generados por el enrutador; `fastapi.HTTPException` es subclase, así que queda cubierta.
- **`TestClient(app, raise_server_exceptions=False)`** es obligatorio para probar el
  manejador de `Exception`; sin ese flag el `TestClient` relanza la excepción en la prueba.
- **Sin fuga de información**: el cuerpo del 500 usa siempre el mensaje genérico fijo;
  el detalle completo (traza) vive únicamente en el log. No registrar cuerpos de
  petición, cabeceras ni credenciales.
- **Pureza del dominio**: `DomainException` no importa nada de FastAPI/Starlette;
  los manejadores viven en `presentation/exception_handlers/`; la configuración de
  logging en `infrastructure/config/`.
- **No usar middlewares ASGI personalizados**: los exception handlers de FastAPI son
  suficientes y más idiomáticos (decisión explícita del ticket).
- **mypy `--strict`**: type hints en todas las firmas nuevas y modificadas; atención
  a la firma esperada por `add_exception_handler` (puede requerir `cast`).
- Este ticket no toca conceptos del dominio SST (peligros, riesgos, auditorías), por
  lo que no requiere validación contra `.sst-agent-document.md`.

## 10. Implementation Verification Checklist

- [ ] Code quality: sin errores de compilación, `ruff` y `mypy --strict` pasan, sin instanciación manual de servicios
- [ ] Domain: `DomainException` permanece pura (sin imports de framework) con código por defecto `ERROR_DOMINIO`
- [ ] Application: `RespuestaError` con type hints completos y validación Pydantic v2, exportado en `dto/__init__.py`
- [ ] Presentation: los cuatro manejadores emiten exactamente `{exito, codigo, mensaje, detalle}`; `main.py` registra todo con una sola llamada
- [ ] Migrations: no aplica (sin cambios de esquema de datos)
- [ ] Tests: todos en verde, cobertura ≥ 90 %, cubiertos 404, 422, 500 y `http_status` personalizado
- [ ] Documentation: `api-spec.yml` incorpora el componente `RespuestaError`; `.env.example` documenta `LOG_LEVEL`

<!--
## Verificación manual (Step 5) — 2026-07-07

Servidor levantado con: py -m uvicorn src.main:app --port 8137

# Regresión /health → 200 con contrato intacto
curl -s -w "\nSTATUS=%{http_code}\n" http://127.0.0.1:8137/health
# → {"status":"ok","app":"SST Auditor Agent Pro","version":"0.1.0"} STATUS=200

# Ruta inexistente → 404 ERROR_HTTP con esquema único
curl -s -w "\nSTATUS=%{http_code}\n" http://127.0.0.1:8137/no-existe
# → {"exito":false,"codigo":"ERROR_HTTP","mensaje":"Not Found","detalle":null} STATUS=404

# Método no permitido → 405 ERROR_HTTP con esquema único
curl -s -w "\nSTATUS=%{http_code}\n" -X POST http://127.0.0.1:8137/health
# → {"exito":false,"codigo":"ERROR_HTTP","mensaje":"Method Not Allowed","detalle":null} STATUS=405

# Log observado (formato configurado + nivel WARNING sin traza):
# 2026-07-07 20:25:32,748 WARNING src.presentation.exception_handlers.http_handler Error HTTP 404 ERROR_HTTP en GET /no-existe

Los casos 422 (ERROR_VALIDACION), DomainException y 500 (ERROR_INTERNO) no son
reproducibles contra la app real porque /health es el único endpoint; quedan
cubiertos por la suite automática (tests/presentation/test_exception_handlers.py)
con app de prueba y TestClient(raise_server_exceptions=False).
-->
