# Backend Implementation Plan: SP-141 Configurar PostgreSQL y Alembic para migraciones

## 1. Overview

Completar la infraestructura de base de datos entregada parcialmente con SP-140. La conexión
async, la sesión por petición, el entorno de Alembic y la migración base de `usuarios` **ya
existen y funcionan** — esta HU NO los reimplementa. El alcance real es cerrar cuatro brechas:

1. **Pool de conexión configurable** (SP-178): exponer en `Settings` los parámetros de pool
   (`pool_size`, `max_overflow`, `pool_pre_ping`, `pool_recycle`, `echo`) como variables de
   entorno tipadas con validación fail-fast, y pasarlos a `create_async_engine` en
   `obtener_motor()`.
2. **Entorno local reproducible**: `docker-compose.yml` con PostgreSQL 16 (healthcheck +
   volumen nombrado), coherente con el `URL_BASE_DATOS` de ejemplo.
3. **Precisión del autogenerate** (SP-179): `compare_type=True` y `compare_server_default=True`
   en la configuración offline y online de `alembic/env.py`.
4. **Verificación del ciclo de migración** (SP-180): `upgrade head` → `downgrade base` →
   `upgrade head` contra el PostgreSQL del compose, autogenerate vacío con esquema al día y
   seed del administrador end-to-end. Verificación manual/CI — no genera código commiteable.

La HU es **exclusivamente de infraestructura**: no crea ni modifica endpoints HTTP, no toca
`domain/`, `application/` ni `presentation/`, y `alembic/versions/` queda intacto.

- Stack activo: `python-fastapi` (Python 3.12 + FastAPI).

## 2. Architecture Context

- Active stack: `python-fastapi` (`Python 3.12 + FastAPI`)
- Capas involucradas:

| Capa | Archivo | Acción |
|---|---|---|
| Infrastructure | `src/infrastructure/config/settings.py` | Modificar — 5 campos de pool + validadores |
| Infrastructure | `src/infrastructure/database/sesion.py` | Modificar — pasar parámetros de pool al motor |
| Infrastructure | `alembic/env.py` | Modificar — flags de comparación del autogenerate |
| Infrastructure | `docker-compose.yml` (raíz) | Crear — PostgreSQL 16 local |
| Infrastructure | `.env.example` | Modificar — documentar variables de pool |
| Documentación | `README.md` | Modificar — flujo de arranque local con Docker + Alembic |
| Tests | `tests/infrastructure/test_settings.py` | Modificar — defaults y validación de pool |
| Tests | `tests/unit/infrastructure/test_sesion.py` | Modificar — motor recibe configuración de pool |

Domain, Application y Presentation: **sin cambios**.

### Subtask Mapping

| Subtask key | Summary | Implementation Step(s) |
|---|---|---|
| `SP-178` | Instalar y configurar conexión a PostgreSQL | Step 1, Step 2, Step 3, Step 5 (parcial), Step 6 |
| `SP-179` | Inicializar Alembic y configurar entorno de migraciones | Step 4, Step 7 (verificación autogenerate) |
| `SP-180` | Crear migración base inicial | Step 7 (verificación del ciclo upgrade/downgrade + seed) |

## 3. Implementation Steps

#### Step 0: Create Feature Branch
- **Action**: Crear y cambiar a la rama de la HU.
- **Branch**: `feature/SP-141-backend`
- **Commands**:
  ```bash
  git checkout develop && git pull origin develop
  git checkout -b feature/SP-141-backend
  ```
- Nota: el flujo del repo hace PR → `develop` (convención de `os-commit`), por eso la rama
  parte de `develop` y no de `main`.

#### Step 1: Settings — campos de pool de conexión (TDD primero en Step 5)
- **File**: `src/infrastructure/config/settings.py`
- **Changes**: agregar a `Settings`, en una sección «Pool de conexión a la base de datos»
  junto a `url_base_datos`:

  ```python
  bd_pool_tamano: int = 5
  bd_pool_max_extra: int = 10
  bd_pool_pre_ping: bool = True
  bd_pool_reciclar_segundos: int = 1800
  bd_echo_sql: bool = False
  ```

- **Validadores** (mismo patrón `@field_validator` + `@classmethod` ya usado para
  `jwt_secreto`):
  - `validar_pool_positivo` sobre `("bd_pool_tamano", "bd_pool_reciclar_segundos")`: rechaza
    valores `< 1` con mensaje en español que nombre la variable de entorno (fail-fast al
    arranque, igual que `URL_BASE_DATOS`/`JWT_SECRETO`).
  - `validar_pool_no_negativo` sobre `bd_pool_max_extra`: rechaza valores `< 0`.
  - Alternativa equivalente aceptable: `Field(ge=1)` / `Field(ge=0)`; se prefiere el
    `field_validator` para controlar el mensaje de error en español, consistente con el
    validador de `jwt_secreto`.
- Pydantic Settings mapea automáticamente `BD_POOL_TAMANO` → `bd_pool_tamano`, etc.
  (case-insensitive); no hace falta `alias`.
- Docstrings y type hints en todo (mypy strict).

#### Step 2: Motor async — trasladar la configuración de pool
- **File**: `src/infrastructure/database/sesion.py`
- **Changes**: en `obtener_motor()` (conservando el `@lru_cache`), pasar a
  `create_async_engine`:

  | Campo de `Settings` | Parámetro del motor |
  |---|---|
  | `bd_echo_sql` | `echo` |
  | `bd_pool_pre_ping` | `pool_pre_ping` |
  | `bd_pool_reciclar_segundos` | `pool_recycle` |
  | `bd_pool_tamano` | `pool_size` |
  | `bd_pool_max_extra` | `max_overflow` |

- **⚠️ Restricción crítica descubierta en el análisis**: la suite de tests corre con
  `URL_BASE_DATOS=sqlite+aiosqlite:///:memory:` (fijada en `tests/conftest.py`), y para
  SQLite en memoria SQLAlchemy usa `StaticPool`, que **no acepta** `pool_size` ni
  `max_overflow` (lanza `TypeError: Invalid argument(s)`). Pasarlos incondicionalmente rompe
  los tests existentes de `test_sesion.py`, que crean un motor real. En cambio, `echo`,
  `pool_pre_ping` y `pool_recycle` son argumentos de la clase base `Pool` y se aceptan
  siempre.
- **Solución**: construir los kwargs condicionalmente. Implementación propuesta:

  ```python
  def _argumentos_motor() -> dict[str, object]:
      """Kwargs del motor desde Settings; los de QueuePool solo aplican fuera de SQLite."""
      settings = get_settings()
      argumentos: dict[str, object] = {
          "echo": settings.bd_echo_sql,
          "pool_pre_ping": settings.bd_pool_pre_ping,
          "pool_recycle": settings.bd_pool_reciclar_segundos,
      }
      # SQLite (tests) usa StaticPool, que no acepta dimensionamiento de pool.
      if not settings.url_base_datos.startswith("sqlite"):
          argumentos["pool_size"] = settings.bd_pool_tamano
          argumentos["max_overflow"] = settings.bd_pool_max_extra
      return argumentos


  @lru_cache
  def obtener_motor() -> AsyncEngine:
      """Crea (una sola vez) el motor async a partir de `URL_BASE_DATOS`."""
      settings = get_settings()
      return create_async_engine(settings.url_base_datos, **_argumentos_motor())
  ```

  (El helper `_argumentos_motor` además facilita el test unitario con mock: se puede
  verificar el dict completo sin desempaquetar la llamada.)

#### Step 3: docker-compose.yml — PostgreSQL local reproducible
- **File**: `docker-compose.yml` (raíz del repo — **crear**)
- **Content** (solo desarrollo local, nunca producción):

  ```yaml
  # PostgreSQL local para desarrollo — credenciales alineadas con .env.example.
  services:
    postgres:
      image: postgres:16-alpine
      container_name: sst_auditor_postgres
      environment:
        POSTGRES_DB: sst_auditor
        POSTGRES_USER: usuario
        POSTGRES_PASSWORD: contrasena
      ports:
        - "5432:5432"
      volumes:
        - datos_postgres:/var/lib/postgresql/data
      healthcheck:
        test: ["CMD-SHELL", "pg_isready -U usuario -d sst_auditor"]
        interval: 5s
        timeout: 3s
        retries: 10

  volumes:
    datos_postgres:
  ```

- Las credenciales `usuario`/`contrasena` son exactamente las del `URL_BASE_DATOS` de
  ejemplo en `.env.example`
  (`postgresql+asyncpg://usuario:contrasena@localhost:5432/sst_auditor`) — un desarrollador
  nuevo copia `.env.example` a `.env` y la conexión funciona sin editar nada más.
- No incluir clave `version:` (obsoleta en Compose v2, genera warning).

#### Step 4: alembic/env.py — precisión del autogenerate
- **File**: `alembic/env.py`
- **Changes**:
  1. En `run_migrations_offline()`, agregar a `context.configure(...)`:
     `compare_type=True, compare_server_default=True`.
  2. En `ejecutar_migraciones()` (ruta online), agregar los mismos dos flags a su
     `context.configure(...)`.
  3. Agregar (o ampliar) el comentario junto al import de `UsuarioORM` documentando la
     convención de registro de modelos futuros: todo nuevo modelo ORM en
     `src/infrastructure/database/modelos/` debe exportarse en el `__init__.py` del paquete
     e importarse aquí para que `Base.metadata` lo registre y el autogenerate lo detecte.
- Sin estos flags, `alembic revision --autogenerate` no detecta cambios de tipo de columna
  ni de `server_default` en migraciones futuras.
- **No** re-ejecutar `alembic init`, **no** reescribir el entorno, **no** tocar
  `alembic/versions/`.

#### Step 5: Unit Tests (TDD — escribir antes de Steps 1–2)
- **File**: `tests/infrastructure/test_settings.py` — agregar (patrón existente:
  `Settings(_env_file=None)` + `monkeypatch`):
  - `test_should_usar_defaults_de_pool_when_no_hay_variables_de_entorno`: sin vars de pool →
    `5 / 10 / True / 1800 / False`.
  - `test_should_leer_configuracion_de_pool_when_variables_definidas`: con
    `BD_POOL_TAMANO=20`, `BD_POOL_MAX_EXTRA=5`, `BD_POOL_PRE_PING=false`,
    `BD_POOL_RECICLAR_SEGUNDOS=900`, `BD_ECHO_SQL=true` → los campos reflejan el entorno.
  - `test_should_fallar_when_bd_pool_tamano_no_es_positivo`: `BD_POOL_TAMANO=0` y `-1` →
    `pydantic.ValidationError` (parametrizar con `pytest.mark.parametrize`).
  - `test_should_fallar_when_bd_pool_reciclar_segundos_no_es_positivo`:
    `BD_POOL_RECICLAR_SEGUNDOS=0` → `ValidationError`.
  - `test_should_fallar_when_bd_pool_max_extra_es_negativo`: `BD_POOL_MAX_EXTRA=-1` →
    `ValidationError` (`0` sí es válido).
- **File**: `tests/unit/infrastructure/test_sesion.py` — agregar:
  - `test_should_crear_motor_con_parametros_de_pool_when_settings_configurados`:
    - *Arrange*: `monkeypatch.setenv("URL_BASE_DATOS", "postgresql+asyncpg://u:p@localhost/db")`
      (URL no-SQLite para que apliquen `pool_size`/`max_overflow`),
      `get_settings.cache_clear()`, `obtener_motor.cache_clear()`,
      `obtener_fabrica_sesiones.cache_clear()`, y
      `unittest.mock.patch` sobre `src.infrastructure.database.sesion.create_async_engine`.
    - *Act*: `obtener_motor()`.
    - *Assert*: el mock fue invocado con `pool_size=5`, `max_overflow=10`,
      `pool_pre_ping=True`, `pool_recycle=1800`, `echo=False`.
    - *Cleanup* (obligatorio — `lru_cache` es estado global): volver a limpiar las tres
      cachés al final (idealmente con un fixture `autouse` o `try/finally`) para no
      contaminar los demás tests del módulo, que esperan el motor SQLite real.
  - `test_should_omitir_dimensionamiento_de_pool_when_url_es_sqlite`: con la URL SQLite de
    pruebas y el mock, verificar que la llamada NO incluye `pool_size` ni `max_overflow`
    pero SÍ `pool_pre_ping`/`pool_recycle`/`echo` (protege la restricción del Step 2).
  - `test_should_reusar_motor_when_se_invoca_dos_veces`: `obtener_motor() is obtener_motor()`
    (ya cubierto por `test_should_cachear_el_motor_y_la_fabrica` — verificar que sigue verde;
    solo agregar el alias si se quiere trazabilidad 1:1 con la HU).
- Todos los tests: AAA, type hints completos, nombres y docstrings en español.

#### Step 6: .env.example y README
- **File**: `.env.example` — en la sección «Base de datos», debajo de `URL_BASE_DATOS`,
  agregar las 5 variables comentadas con sus defaults y una línea de explicación cada una:

  ```bash
  # Pool de conexión (defaults conservadores para una instancia; ajustar por entorno).
  # BD_POOL_TAMANO=5
  # BD_POOL_MAX_EXTRA=10
  # BD_POOL_PRE_PING=true
  # BD_POOL_RECICLAR_SEGUNDOS=1800
  # BD_ECHO_SQL=false
  ```

- **File**: `README.md` — en «Inicio rápido» (o una subsección «Base de datos local»
  inmediatamente después), documentar el flujo de arranque local completo:
  1. `cp .env.example .env`
  2. `docker compose up -d` (espera al healthcheck)
  3. `poetry run alembic upgrade head`
  4. `poetry run python -m scripts.crear_usuario_admin` (seed del administrador)
  5. `poetry run uvicorn src.main:app --reload`

  Mantener el estilo del README (comandos con prefijo `poetry run`, callouts con `>`).
  Mencionar que las variables `BD_POOL_*` son opcionales con defaults seguros.

#### Step 7: Verificación de integración contra PostgreSQL real (manual — no unit tests)
- **Pre-requisito**: `docker compose up -d` con healthcheck saludable
  (`docker compose ps` → `healthy`), `.env` apuntando al compose.
- **Ciclo de migración (SP-180)**:
  1. Con BD limpia: `alembic upgrade head` → aplica `a1b2c3d4e5f6` sin errores.
  2. `alembic current` → reporta `a1b2c3d4e5f6 (head)`; verificar en la BD que existe la
     tabla `usuarios` con el índice único `ix_usuarios_correo`
     (`docker compose exec postgres psql -U usuario -d sst_auditor -c "\d usuarios"`).
  3. `alembic downgrade base` → tabla e índice eliminados; solo queda `alembic_version`.
  4. `alembic upgrade head` → re-aplica limpiamente (ciclo idempotente).
- **Autogenerate vacío (SP-179)**:
  5. Con esquema en `head`: `alembic revision --autogenerate -m "verificacion"` → el archivo
     generado tiene `upgrade()`/`downgrade()` con solo `pass` (sin deriva ORM↔BD, y evidencia
     de que `compare_type`/`compare_server_default` no producen falsos positivos con los
     `server_default` existentes de `usuarios`). **Eliminar el archivo generado** — no se
     commitea.
  6. `alembic upgrade head --sql` (modo offline) sigue funcionando tras los cambios de env.py.
- **Seed end-to-end (SP-180)**:
  7. `python -m scripts.crear_usuario_admin` sobre el esquema migrado crea el administrador
     (con `ADMIN_INICIAL_*` del `.env`); re-ejecutar debe ser seguro (idempotente).
- **Persistencia**: `docker compose down` (sin `-v`) + `docker compose up -d` → los datos
  sobreviven al reinicio (volumen nombrado).
- Registrar los resultados de esta verificación en la descripción del PR.

#### Step 8: Update Technical Documentation
- `ai-specs/specs/data-model.md` — **solo si** la verificación del Step 7 revela alguna
  discrepancia entre lo documentado y el esquema real (criterio de SP-180); en caso
  contrario, sin cambios.
- `ai-specs/specs/api-spec.yml` — **sin cambios** (la HU no toca endpoints).
- `README.md` — cubierto en Step 6.

## 4. Implementation Order

1. Step 0 — Crear rama `feature/SP-141-backend`.
2. Step 5 (parcial) — Escribir los tests de `Settings` y del motor (TDD: deben fallar).
3. Step 1 — Campos de pool en `Settings` con validadores → tests de settings en verde.
4. Step 2 — `obtener_motor()` con kwargs condicionales → tests de sesión en verde.
5. Step 3 — Crear `docker-compose.yml`.
6. Step 4 — Flags de comparación en `alembic/env.py` + comentario de convención.
7. Step 6 — Actualizar `.env.example` y README.
8. Step 7 — Verificación de integración contra el PostgreSQL del compose (ciclo de
   migración, autogenerate vacío, seed, persistencia).
9. Step 8 — Ajustar `data-model.md` solo si el Step 7 detecta discrepancias.
10. Verificación final: `ruff check .`, `mypy` (strict), `pytest --cov` ≥ 90 %.

## 5. Testing Checklist

- [ ] `pytest` pasa con 0 fallos (incluidos los tests preexistentes de sesión con SQLite).
- [ ] `pytest --cov --cov-report=html` muestra ≥ 90 %.
- [ ] `ruff check .` y mypy strict sin errores.
- [ ] Verificación manual del Step 7 completa: upgrade/downgrade/re-upgrade, autogenerate
      vacío (archivo descartado), modo offline `--sql`, seed admin, persistencia del volumen.
- [ ] Ningún test existente roto (en particular `test_should_cachear_el_motor_y_la_fabrica`
      y los tests async de `obtener_sesion`, sensibles a las cachés `lru_cache`).
- [ ] No hay endpoints nuevos que probar (HU sin superficie HTTP).

## 6. Tooling Reference

| Purpose | Command |
|---|---|
| Build | `pip install -r requirements.txt` |
| Test | `pytest` |
| Run | `uvicorn main:app --reload` |
| Lint | `ruff check .` |
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

*No aplica a esta HU (sin endpoints); la configuración inválida de pool falla al arranque
con `ValidationError` de Pydantic, no con respuesta HTTP.*

## 8. Dependencies

**Ninguna dependencia nueva de Python.** `sqlalchemy[asyncio]`, `asyncpg`, `alembic`,
`pydantic-settings` y `python-dotenv` ya están en `pyproject.toml` / `requirements.txt`
(entregadas con SP-140). No regenerar `requirements.txt`.

Requisito de entorno local (no de la aplicación): Docker Desktop / Docker Engine con
Compose v2 para el `docker-compose.yml`.

## 9. Notes

- **No reimplementar lo entregado en SP-140**: `Settings.url_base_datos`, la sesión async,
  `alembic.ini`/`env.py` y la migración `a1b2c3d4e5f6` quedan como están. Las migraciones
  aplicadas son **inmutables** — prohibido modificar `a1b2c3d4e5f6_crear_tabla_usuarios.py`.
- **Restricción SQLite/StaticPool** (Step 2): es el punto más delicado de la HU. `pool_size`
  y `max_overflow` solo aplican a pools tipo `QueuePool`; con la URL SQLite de los tests
  provocan `TypeError`. El kwargs condicional es imprescindible y tiene su propio test.
- **Estado global en tests**: `get_settings`, `obtener_motor` y `obtener_fabrica_sesiones`
  usan `lru_cache`. Todo test que altere `URL_BASE_DATOS` o variables `BD_*` debe limpiar
  las cachés en arrange **y** en cleanup para no contaminar el resto de la suite.
- **Booleans de Pydantic Settings**: acepta `true/false/1/0` (case-insensitive) para
  `BD_POOL_PRE_PING` / `BD_ECHO_SQL`; documentar en `.env.example` con `true`/`false`.
- **Seguridad**: `alembic.ini` mantiene `sqlalchemy.url` vacío; la URL solo llega por
  entorno. Las credenciales del compose (`usuario`/`contrasena`) son exclusivamente de
  desarrollo local. `.env` sigue en `.gitignore`.
- **Operación**: el esquema real se aplica solo vía `alembic upgrade head`;
  `Base.metadata.create_all()` sigue reservado a pruebas.
- **Idioma**: todo en español — identificadores, docstrings, mensajes de error de los
  validadores, comentarios del compose y del env.py, commits
  (p. ej. `feat(bd): configura pool de conexion y compose local para SP-141`).
- La migración de verificación del autogenerate (Step 7.5) se **elimina** tras verificar;
  el criterio de aceptación de SP-180 exige que `alembic/versions/` no cambie en el PR.

## 10. Implementation Verification Checklist

- [ ] Code quality: Ruff y mypy strict sin errores; sin código sin tipar.
- [ ] Domain: sin cambios (verificar que el diff no toca `src/domain/`).
- [ ] Application: sin cambios (verificar que el diff no toca `src/application/`).
- [ ] Presentation: sin cambios (verificar que el diff no toca `src/presentation/`).
- [ ] Migrations: `alembic/versions/` idéntico a `develop`; solo `alembic/env.py` cambia.
- [ ] Settings: 5 campos nuevos con defaults 5 / 10 / `True` / 1800 / `False` y validación
      fail-fast; `obtener_motor()` traslada los valores al motor (con la salvedad SQLite).
- [ ] Compose: `docker compose up -d` levanta PostgreSQL 16 `healthy` con volumen nombrado
      y credenciales coherentes con `.env.example`.
- [ ] Tests: todos en verde, cobertura ≥ 90 %, cachés `lru_cache` restauradas entre tests.
- [ ] Documentation: `.env.example` y README actualizados; `data-model.md` revisado
      (sin cambios salvo discrepancia detectada); `api-spec.yml` intacto.

---

## Registro de verificación de la implementación (2026-07-16)

### Automatizada (esta máquina)
- `pytest` — 123 tests en verde; cobertura total 99.24 % (umbral 90 % cumplido).
- `ruff check .` y `ruff format --check .` — sin errores.
- `mypy` (strict) — sin errores en 50 archivos.
- TDD respetado: los 10 tests nuevos fallaron primero por la razón correcta y
  pasaron tras implementar Settings y `obtener_motor()`.
- `alembic upgrade head --sql` (offline) — genera el DDL completo de `usuarios`
  con `ix_usuarios_correo` sin errores tras agregar `compare_type` /
  `compare_server_default`.
- `alembic downgrade head:base --sql` (offline) — genera el DDL inverso limpio.
- `docker-compose.yml` — YAML validado (servicio `postgres` con image,
  environment, ports, volumes, healthcheck y volumen nombrado `datos_postgres`).

### Pendiente (Step 7 — requiere Docker, no disponible en esta máquina)
Docker Engine/Desktop no está instalado en el entorno de desarrollo actual, por
lo que el ciclo contra PostgreSQL real queda pendiente de ejecutar donde haya
Docker (o en CI):
1. `docker compose up -d` → esperar healthcheck `healthy`.
2. `alembic upgrade head` → aplica `a1b2c3d4e5f6`; verificar `\d usuarios`.
3. `alembic downgrade base` → revierte; `alembic upgrade head` → re-aplica.
4. `alembic revision --autogenerate -m "verificacion"` → upgrade()/downgrade()
   vacíos (descartar el archivo, no commitear).
5. `python -m scripts.crear_usuario_admin` → seed idempotente.
6. `docker compose down` + `up -d` → los datos persisten (volumen nombrado).

No hay endpoints nuevos ni modificados: no aplican pruebas manuales con curl.
