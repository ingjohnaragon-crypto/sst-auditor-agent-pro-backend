# Backend Implementation Plan: SP-140 Autenticación JWT y Roles de SST

## 1. Overview

Implementar el sistema de autenticación y autorización del backend de **SST Auditor Agent Pro**
mediante JWT (HS256) con control de acceso basado en roles (RBAC). Esta HU introduce por primera
vez la **capa de persistencia** del proyecto: SQLAlchemy 2.x async + PostgreSQL + Alembic.

Alcance backend:

- Entidad de dominio `Usuario` + enum `RolUsuario` (`ADMINISTRADOR`, `AUDITOR_SST`, `CONSULTA`).
- Contraseñas cifradas con **bcrypt** (costo 12, ejecución vía `asyncio.to_thread`).
- Endpoints `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`, `GET /api/v1/auth/yo`.
- Tokens de acceso (30 min, claims `sub`, `rol`, `tipo="acceso"`, `iat`, `exp`, `jti`) y de
  refresco (7 días, claims `sub`, `tipo="refresco"`, `iat`, `exp`, `jti` — sin rol).
- Dependencias reutilizables `obtener_usuario_actual` y fábrica `requerir_roles(*roles)`.
- Migración Alembic inicial (tabla `usuarios`) y seed idempotente del administrador.

Principios obligatorios del repo: DDD estricto (el dominio define los **puertos**
`RepositorioUsuario`, `ServicioHashContrasena` y `ServicioTokens` como ABCs; la infraestructura
aporta las implementaciones con SQLAlchemy, bcrypt y PyJWT). Ni `domain/` ni `application/`
importan FastAPI, SQLAlchemy, bcrypt ni jwt. Todos los errores usan el contrato único
`RespuestaError` ya existente, resuelto por el `domain_handler` global.

**Stack activo**: `python-fastapi` (Python 3.12 + FastAPI).

## 2. Architecture Context

- Active stack: `python-fastapi` (`Python 3.12 + FastAPI`)
- Estado actual del backend: solo `/health` y `/api/v1/ping`, sin base de datos. Los routers se
  registran en el agregador `src/presentation/routers/__init__.py` (patrón del repo — **no** se
  toca `src/main.py` para añadir routers). Los manejadores globales ya traducen
  `DomainException` (`code`, `http_status`, `message`) a `RespuestaError`.

Capas involucradas y archivos afectados:

| Capa | Archivos |
|---|---|
| Domain | `src/domain/models/usuario.py`, `src/domain/repositories/repositorio_usuario.py`, `src/domain/repositories/servicio_hash_contrasena.py`, `src/domain/repositories/servicio_tokens.py`, `src/domain/exceptions/autenticacion.py` |
| Application | `src/application/dto/solicitud_login.py`, `solicitud_refresh.py`, `respuesta_tokens.py`, `respuesta_usuario.py`, `src/application/mappers/mapper_usuario.py`, `src/application/services/servicio_autenticacion.py` |
| Presentation | `src/presentation/routers/auth_router.py`, `src/presentation/routers/__init__.py` (registro), `src/presentation/dependencies/autenticacion.py` |
| Infrastructure | `src/infrastructure/database/base.py`, `sesion.py`, `modelos/usuario_orm.py`, `src/infrastructure/repositories/repositorio_usuario_sqlalchemy.py`, `src/infrastructure/security/hash_bcrypt.py`, `tokens_jwt.py`, `src/infrastructure/config/settings.py` (modificar) |
| Migraciones | `alembic.ini`, `alembic/env.py`, `alembic/versions/<rev>_crear_tabla_usuarios.py` |
| Scripts | `scripts/crear_usuario_admin.py` |
| Config | `pyproject.toml` (dependencias), `.env.example` |
| Tests | `tests/unit/...`, `tests/integration/...` |
| Docs | `ai-specs/specs/api-spec.yml`, `ai-specs/specs/data-model.md` |

### Subtask Mapping

| Subtask key | Summary | Implementation Step(s) |
|---|---|---|
| `SP-174` | Modelar tablas de usuarios y encriptación de claves | Step 1, Step 2, Step 3 (parcial), Step 5, Step 6, Step 7 (hash), Step 8, Step 13, Step 14 (parcial) |
| `SP-175` | Desarrollar endpoints de Login y Refresh JWT | Step 3 (`ServicioTokens`), Step 4, Step 7 (JWT), Step 9, Step 10, Step 11, Step 12, Step 14, Step 15, Step 16 |
| `SP-176` | Implementar Interceptor HTTP de JWT en Angular | **Fuera de alcance** — repositorio frontend Angular |
| `SP-177` | Crear AuthGuard de rutas y directivas estructurales | **Fuera de alcance** — repositorio frontend Angular |

## 3. Implementation Steps

#### Step 0: Create Feature Branch
- **Action**: Crear y cambiar a la rama de la HU.
- **Branch**: `feature/SP-140-backend`
- **Commands**:
  ```bash
  git checkout develop && git pull origin develop
  git checkout -b feature/SP-140-backend
  ```
- Nota: el flujo del repo hace PR → `develop` (convención de `os-commit`), por eso la rama parte
  de `develop` y no de `main`.

#### Step 1: Dependencias y configuración (`Settings` + `.env.example`)
- **File**: `pyproject.toml` — añadir a `[project].dependencies`:
  - `sqlalchemy[asyncio]` 2.x, `asyncpg`, `alembic`, `bcrypt`, `pyjwt`,
    `pydantic[email]` (o `email-validator` — requerido por `EmailStr`).
  - Dev/test (`[tool.poetry.group.dev.dependencies]`): `aiosqlite` (BD de integración en memoria).
  - Sincronizar con `poetry lock` / `poetry install` (el repo usa Poetry en `package-mode = false`).
- **File**: `src/infrastructure/config/settings.py` — agregar campos tipados:

  | Variable | Tipo | Default / Notas |
  |---|---|---|
  | `url_base_datos` | `str` | `postgresql+asyncpg://...` — sin default real en producción |
  | `jwt_secreto` | `str` | obligatoria; `field_validator` que exige longitud ≥ 32 |
  | `jwt_algoritmo` | `str` | `"HS256"` |
  | `jwt_minutos_expiracion_acceso` | `int` | `30` |
  | `jwt_dias_expiracion_refresco` | `int` | `7` |

  Las variables `ADMIN_INICIAL_CORREO` / `ADMIN_INICIAL_CONTRASENA` / `ADMIN_INICIAL_NOMBRE`
  se leen solo en el script de seed (no contaminan `Settings` de la app; leerlas con `os.environ`
  o un `BaseSettings` propio del script).
- **File**: `.env.example` — documentar `URL_BASE_DATOS`, `JWT_SECRETO` (placeholder de ≥ 32
  caracteres, nunca un secreto real), `JWT_ALGORITMO`, `JWT_MINUTOS_EXPIRACION_ACCESO`,
  `JWT_DIAS_EXPIRACION_REFRESCO`, `ADMIN_INICIAL_*`.

#### Step 2: Modelo de dominio `Usuario` + enum `RolUsuario`
- **File**: `src/domain/models/usuario.py`
- Dataclass pura (sin SQLAlchemy/FastAPI/Pydantic):
  - Campos: `id: UUID | None`, `nombre_completo: str`, `correo: str`, `hash_contrasena: str`,
    `rol: RolUsuario`, `activo: bool`, `fecha_creacion: datetime`, `fecha_actualizacion: datetime`.
  - `class RolUsuario(StrEnum)`: `ADMINISTRADOR`, `AUDITOR_SST`, `CONSULTA`.
  - Factoría `Usuario.crear(nombre_completo, correo, hash_contrasena, rol)` que valida
    invariantes: nombre no vacío, correo con formato válido (regex simple del dominio, sin
    `email-validator`), y **normaliza el correo a minúsculas**. Lanza `DomainException`
    (o subclase de validación) si falla.
  - Ningún método loguea ni expone la contraseña en claro.

#### Step 3: Puertos del dominio (ABCs)
- **File**: `src/domain/repositories/repositorio_usuario.py`
  ```python
  class RepositorioUsuario(ABC):
      async def buscar_por_correo(self, correo: str) -> Usuario | None: ...
      async def buscar_por_id(self, id: UUID) -> Usuario | None: ...
      async def guardar(self, usuario: Usuario) -> Usuario: ...
      async def existe_por_correo(self, correo: str) -> bool: ...
  ```
- **File**: `src/domain/repositories/servicio_hash_contrasena.py`
  - ABC `ServicioHashContrasena`: `async generar_hash(contrasena: str) -> str`,
    `async verificar(contrasena: str, hash_contrasena: str) -> bool`.
- **File**: `src/domain/repositories/servicio_tokens.py`
  - ABC `ServicioTokens`: `emitir_token_acceso(usuario: Usuario) -> str`,
    `emitir_token_refresco(usuario: Usuario) -> str`,
    `decodificar(token: str) -> dict[str, object]` (lanza excepciones de dominio del Step 4).

#### Step 4: Excepciones de dominio de autenticación
- **File**: `src/domain/exceptions/autenticacion.py`
- Subclases de `DomainException` existente (fijan `code` y `http_status` como atributos de clase,
  patrón ya usado en `src/domain/exceptions/base.py`):

  | Excepción | `code` | `http_status` |
  |---|---|---|
  | `CredencialesInvalidasException` | `CREDENCIALES_INVALIDAS` | 401 |
  | `TokenInvalidoException` | `TOKEN_INVALIDO` | 401 |
  | `TokenExpiradoException` | `TOKEN_EXPIRADO` | 401 |
  | `PermisosInsuficientesException` | `PERMISOS_INSUFICIENTES` | 403 |

- El `domain_handler` global existente ya las convierte a `RespuestaError` — no requiere cambios.
- `CredencialesInvalidasException` usa **siempre el mismo mensaje genérico** (constante única),
  sin distinguir correo inexistente / contraseña incorrecta / usuario inactivo.

#### Step 5: Infraestructura de base de datos
- **File**: `src/infrastructure/database/base.py` — `class Base(DeclarativeBase)` (SQLAlchemy 2.x).
- **File**: `src/infrastructure/database/sesion.py` — `create_async_engine(settings.url_base_datos)`,
  `async_sessionmaker(expire_on_commit=False)` y dependencia `obtener_sesion()`
  (async generator `AsyncSession` para `Depends`). Engine creado de forma perezosa/cacheada para
  que los tests puedan sustituirlo.
- **File**: `src/infrastructure/database/modelos/usuario_orm.py` — `UsuarioORM` (tabla `usuarios`):

  | Columna | Tipo | Restricciones |
  |---|---|---|
  | `id` | `UUID` | PK, default `uuid4` generado en app |
  | `nombre_completo` | `VARCHAR(150)` | NOT NULL |
  | `correo` | `VARCHAR(254)` | NOT NULL, UNIQUE (índice único), minúsculas |
  | `hash_contrasena` | `VARCHAR(72)` | NOT NULL |
  | `rol` | `VARCHAR(30)` | NOT NULL |
  | `activo` | `BOOLEAN` | NOT NULL, default `true` |
  | `fecha_creacion` | `TIMESTAMPTZ` | NOT NULL, `server_default=func.now()` |
  | `fecha_actualizacion` | `TIMESTAMPTZ` | NOT NULL, `server_default=func.now()`, `onupdate=func.now()` |

#### Step 6: Repositorio SQLAlchemy
- **File**: `src/infrastructure/repositories/repositorio_usuario_sqlalchemy.py`
- `RepositorioUsuarioSQLAlchemy(RepositorioUsuario)` con `AsyncSession` inyectada por constructor.
- Métodos privados de mapeo ORM ↔ dominio; **devuelve siempre `Usuario` del dominio, nunca
  instancias ORM**. `buscar_por_correo` consulta con el correo normalizado a minúsculas
  (aprovecha el índice único).

#### Step 7: Implementaciones de seguridad (bcrypt + PyJWT)
- **File**: `src/infrastructure/security/hash_bcrypt.py`
  - `HashBcrypt(ServicioHashContrasena)` con costo 12 (`bcrypt.gensalt(rounds=12)`).
  - Las llamadas CPU-bound (`hashpw`, `checkpw`) se ejecutan con `asyncio.to_thread` para no
    bloquear el event loop (~100 ms por verificación).
- **File**: `src/infrastructure/security/tokens_jwt.py`
  - `TokensJWT(ServicioTokens)` con PyJWT; recibe `Settings` por constructor.
  - Token de acceso: claims `sub` (str del UUID), `rol`, `tipo="acceso"`, `iat`, `exp`
    (`+jwt_minutos_expiracion_acceso`), `jti` (uuid4).
  - Token de refresco: claims `sub`, `tipo="refresco"`, `iat`, `exp`
    (`+jwt_dias_expiracion_refresco`), `jti`. **Sin claim `rol`**.
  - `decodificar`: `jwt.decode(token, secreto, algorithms=["HS256"])` — lista de algoritmos
    **fija y explícita** (previene ataque de algoritmo `none`). Mapea `ExpiredSignatureError` →
    `TokenExpiradoException` y cualquier otro `InvalidTokenError` → `TokenInvalidoException`.

#### Step 8: Alembic — inicialización async y migración inicial
- **Files**: `alembic.ini`, `alembic/env.py`, `alembic/versions/<rev>_crear_tabla_usuarios.py`
- `alembic init alembic` con plantilla async: `env.py` usa `async_engine_from_config` y toma
  la URL de `Settings` (`url_base_datos`), importando `Base.metadata` y `UsuarioORM` como
  `target_metadata`.
- Migración `crear_tabla_usuarios`: crea la tabla `usuarios` con todas las columnas del Step 5 y
  el índice único sobre `correo`; `downgrade` elimina la tabla.
- Prohibido `Base.metadata.create_all()` fuera de tests.

#### Step 9: DTOs y mapper (Application)
- **File**: `src/application/dto/solicitud_login.py` — `SolicitudLogin(BaseModel)`:
  `correo: EmailStr`, `contrasena: str` (`min_length=8`). Normalizar correo a minúsculas
  (`field_validator`). `repr`/serialización nunca incluyen la contraseña
  (`contrasena: SecretStr` o `repr=False`).
- **File**: `src/application/dto/solicitud_refresh.py` — `SolicitudRefresh`: `token_refresco: str`.
- **File**: `src/application/dto/respuesta_tokens.py` —
  `RespuestaTokens`: `token_acceso`, `token_refresco`, `tipo_token: str = "Bearer"`,
  `expira_en_segundos: int` (1800);
  `RespuestaTokenAcceso`: `token_acceso`, `tipo_token`, `expira_en_segundos`.
- **File**: `src/application/dto/respuesta_usuario.py` — `RespuestaUsuario`: `id: UUID`,
  `nombre_completo`, `correo`, `rol` — **sin `hash_contrasena`**.
- **File**: `src/application/mappers/mapper_usuario.py` — función/clase estática
  `a_respuesta(usuario: Usuario) -> RespuestaUsuario`.

#### Step 10: Servicio de autenticación (casos de uso)
- **File**: `src/application/services/servicio_autenticacion.py`
- `ServicioAutenticacion` con inyección por constructor de los tres puertos:
  `RepositorioUsuario`, `ServicioHashContrasena`, `ServicioTokens` (+ expiración de acceso en
  segundos como valor primitivo, para no importar `Settings` de infraestructura).
- `async iniciar_sesion(dto: SolicitudLogin) -> RespuestaTokens`:
  1. Busca usuario por correo (minúsculas).
  2. **Siempre ejecuta la verificación bcrypt**: si el usuario no existe, verifica contra un
     hash dummy precomputado (mitigación de enumeración por timing).
  3. Si no existe, contraseña incorrecta o `activo=False` → `CredencialesInvalidasException`
     (mismo mensaje genérico).
  4. Éxito: log INFO (solo el correo), emite par de tokens.
  5. Fallo: log WARNING (solo el correo, jamás la contraseña).
- `async refrescar_token(dto: SolicitudRefresh) -> RespuestaTokenAcceso`:
  decodifica; exige claim `tipo == "refresco"` (si no → `TokenInvalidoException`); carga el
  usuario por `sub` y exige `activo=True` (si no → `CredencialesInvalidasException`); emite
  nuevo token de acceso.
- `async obtener_perfil(id: UUID) -> RespuestaUsuario`:
  busca por id; si no existe → `TokenInvalidoException`; mapea a DTO.

#### Step 11: Dependencias de autorización (Presentation)
- **File**: `src/presentation/dependencies/autenticacion.py`
- Wiring con `Depends()`: fábricas `obtener_repositorio_usuario(sesion)`,
  `obtener_servicio_autenticacion(...)` que ensamblan puertos → servicio.
- `obtener_usuario_actual`: usa `HTTPBearer(auto_error=False)`; sin credenciales →
  `TokenInvalidoException` (401); decodifica el token, **exige claim `tipo == "acceso"`**
  (un token de refresco como Bearer → 401 `TOKEN_INVALIDO`); carga el usuario y exige
  `activo=True`. Devuelve el `Usuario` de dominio.
- Fábrica `requerir_roles(*roles: RolUsuario)`: devuelve una dependencia que reutiliza
  `obtener_usuario_actual` y lanza `PermisosInsuficientesException` (403) si el rol del usuario
  no está en la lista. Reutilizable por los endpoints de tickets futuros (información médica →
  solo `AUDITOR_SST`/`ADMINISTRADOR`).

#### Step 12: Router de autenticación
- **File**: `src/presentation/routers/auth_router.py` — `APIRouter(tags=["Autenticación"])`,
  handlers delgados (validar → servicio → respuesta):

  | Método | Path (relativo) | Auth | Request | Respuesta 200 |
  |---|---|---|---|---|
  | POST | `/auth/login` | Pública | `SolicitudLogin` | `RespuestaTokens` |
  | POST | `/auth/refresh` | Pública | `SolicitudRefresh` | `RespuestaTokenAcceso` |
  | GET | `/auth/yo` | Bearer (cualquier rol) | — | `RespuestaUsuario` |

  Documentar en cada endpoint las respuestas de error (`responses={401: {"model": RespuestaError}, ...}`).
- **File**: `src/presentation/routers/__init__.py` — registrar
  `api_router.include_router(auth_router, prefix=settings.api_prefix)` (patrón del repo; el
  prefijo `/auth` vive en el propio router). `src/main.py` no requiere cambios.

#### Step 13: Script de seed del administrador inicial
- **File**: `scripts/crear_usuario_admin.py`
- Script async ejecutable (`python -m scripts.crear_usuario_admin` o `python scripts/crear_usuario_admin.py`):
  1. Lee `ADMIN_INICIAL_CORREO`, `ADMIN_INICIAL_CONTRASENA`, `ADMIN_INICIAL_NOMBRE` del entorno
     (falla con mensaje claro si faltan; nunca hardcodea credenciales).
  2. **Idempotente**: si `existe_por_correo` → loguea y sale con código 0 sin duplicar ni fallar.
  3. Crea el `Usuario` con rol `ADMINISTRADOR` vía factoría de dominio + `HashBcrypt` +
     `RepositorioUsuarioSQLAlchemy`.
  4. Jamás loguea la contraseña ni el hash.

#### Step 14: Unit Tests
- **Paths**: `tests/unit/application/test_servicio_autenticacion.py`,
  `tests/unit/domain/test_usuario.py`, `tests/unit/domain/test_excepciones_autenticacion.py`,
  `tests/unit/infrastructure/test_hash_bcrypt.py`, `tests/unit/infrastructure/test_tokens_jwt.py`,
  `tests/unit/infrastructure/test_mapeo_usuario_orm.py`, `tests/unit/scripts/test_crear_usuario_admin.py`
- Sin FastAPI ni SQLAlchemy en los unitarios de servicio/dominio; puertos mockeados
  (`unittest.mock.AsyncMock`). Patrón AAA. Casos (del enriquecimiento):
  - `test_should_devolver_tokens_when_credenciales_validas`
  - `test_should_lanzar_credenciales_invalidas_when_correo_no_existe` — verifica que
    **igualmente** se invoca la verificación de hash (mitigación de timing).
  - `test_should_lanzar_credenciales_invalidas_when_contrasena_incorrecta`
  - `test_should_lanzar_credenciales_invalidas_when_usuario_inactivo`
  - `test_should_emitir_nuevo_token_acceso_when_refresh_valido`
  - `test_should_lanzar_token_invalido_when_refresh_recibe_token_de_acceso` (claim `tipo`)
  - `test_should_lanzar_token_expirado_when_token_vencido`
  - Factoría: `test_should_crear_usuario_when_datos_validos`,
    `test_should_lanzar_error_when_correo_invalido`, normalización a minúsculas.
  - bcrypt: hash ≠ contraseña en claro; `verificar` verdadero/falso; dos hashes de la misma
    contraseña difieren (salt).
  - JWT: claims presentes (`sub`, `rol`, `tipo`, `exp`, `jti`); firma inválida rechazada;
    algoritmo `none` rechazado; token de refresco sin claim `rol`.
  - Mapeo ORM ↔ dominio: ida y vuelta sin pérdida; el repositorio devuelve dominio, no ORM.
  - Seed: crea una vez; segunda ejecución no duplica ni falla.

#### Step 15: Integration Tests
- **Paths**: `tests/integration/test_auth_login.py`, `test_auth_refresh.py`, `test_auth_yo.py`,
  `test_requerir_roles.py`, `conftest.py` (fixtures: app + BD aiosqlite en memoria con
  `Base.metadata.create_all` **solo en tests**, override de `obtener_sesion`, usuario semilla).
- httpx `AsyncClient` (ASGITransport) contra la app real:
  - `POST /api/v1/auth/login`: 200 (contrato completo con `expira_en_segundos=1800`), 401
    correo inexistente y contraseña incorrecta (mensajes idénticos), 401 usuario inactivo,
    422 body inválido → `ERROR_VALIDACION` con esquema `RespuestaError`.
  - `POST /api/v1/auth/refresh`: 200 con refresco válido; 401 con token de acceso
    (`TOKEN_INVALIDO`), expirado (`TOKEN_EXPIRADO`) y mal firmado.
  - `GET /api/v1/auth/yo`: 200 con Bearer válido (sin `hash_contrasena` en el body); 401 sin
    token, token corrupto y token de refresco como Bearer.
  - Endpoint dummy de test protegido con `requerir_roles(RolUsuario.ADMINISTRADOR)` → 403
    `PERMISOS_INSUFICIENTES` para rol `CONSULTA`, 200 para `ADMINISTRADOR`.
  - Aserción transversal: toda respuesta de error valida contra `RespuestaError`
    (`exito=false`, `codigo`, `mensaje`).
  - Migración: test que aplica `alembic upgrade head` sobre BD vacía sin errores (o verificación
    documentada en el PR si se ejecuta contra PostgreSQL vía Docker).

#### Step 16: Update Technical Documentation
- `ai-specs/specs/api-spec.yml` — añadir los tres endpoints de `/auth`, esquemas
  (`SolicitudLogin`, `RespuestaTokens`, `RespuestaTokenAcceso`, `RespuestaUsuario`) y
  `components.securitySchemes.bearerAuth` (`type: http`, `scheme: bearer`, `bearerFormat: JWT`);
  marcar `/auth/yo` con `security: [bearerAuth]`.
- `ai-specs/specs/data-model.md` — documentar la entidad `Usuario`, el enum `RolUsuario` y la
  tabla `usuarios` (columnas, índice único de `correo`).

## 4. Implementation Order

1. Step 0 — Crear rama `feature/SP-140-backend`
2. Step 1 — Dependencias, `Settings` y `.env.example`
3. Step 2 — Modelo de dominio `Usuario` + `RolUsuario` (con sus tests unitarios primero, TDD)
4. Step 3 — Puertos del dominio (ABCs)
5. Step 4 — Excepciones de dominio de autenticación
6. Step 5 — Infraestructura de BD (`Base`, sesión async, `UsuarioORM`)
7. Step 6 — `RepositorioUsuarioSQLAlchemy`
8. Step 7 — `HashBcrypt` y `TokensJWT`
9. Step 8 — Alembic async + migración `crear_tabla_usuarios`
10. Step 9 — DTOs y mapper
11. Step 10 — `ServicioAutenticacion`
12. Step 11 — Dependencias `obtener_usuario_actual` / `requerir_roles`
13. Step 12 — `auth_router` + registro en el agregador
14. Step 13 — `scripts/crear_usuario_admin.py`
15. Step 14 — Unit tests (completar los pendientes de cada paso)
16. Step 15 — Integration tests
17. Step 16 — Documentación (`api-spec.yml`, `data-model.md`)

Trabajar en baby steps: cada paso con sus tests en verde antes de avanzar al siguiente.

## 5. Testing Checklist

- [ ] `pytest` pasa con 0 fallos
- [ ] `pytest --cov --cov-report=html` muestra cobertura ≥ 90 % (umbral ya forzado en `pyproject.toml`)
- [ ] `ruff check .` y `mypy --strict` (config de `pyproject.toml`) sin errores
- [ ] `alembic upgrade head` aplica la migración sobre una BD vacía sin errores
- [ ] Todos los endpoints probados manualmente: happy path + todos los casos de error
      (401 `CREDENCIALES_INVALIDAS` / `TOKEN_INVALIDO` / `TOKEN_EXPIRADO`, 403
      `PERMISOS_INSUFICIENTES`, 422 `ERROR_VALIDACION`)
- [ ] Los tests existentes (`/health`, `/ping`, CORS, handlers) siguen en verde
- [ ] Ningún log, respuesta ni excepción expone contraseñas ni hashes

## 6. Tooling Reference

| Purpose | Command |
|---|---|
| Build | `pip install -r requirements.txt` (repo gestiona deps con Poetry: `poetry install`) |
| Test | `pytest` |
| Run | `uvicorn main:app --reload` (en este repo: `uvicorn src.main:app --reload --port 8000`) |
| Lint | `ruff check .` |
| Coverage | `pytest --cov --cov-report=html` |

## 7. Error Response Format

El proyecto ya define el contrato único en `src/application/dto/respuesta_error.py`
(campos en español — usar este, no el genérico en inglés):

```json
{
  "exito": false,
  "codigo": "CREDENCIALES_INVALIDAS",
  "mensaje": "Correo o contraseña incorrectos",
  "detalle": null
}
```

Mapeo HTTP de esta HU: 401 `CREDENCIALES_INVALIDAS` | 401 `TOKEN_INVALIDO` | 401
`TOKEN_EXPIRADO` | 403 `PERMISOS_INSUFICIENTES` | 422 `ERROR_VALIDACION`.
Las excepciones de dominio se resuelven con el `domain_handler` global ya registrado.

## 8. Dependencies

Nuevas (producción, `pyproject.toml` → `[project].dependencies`, versiones fijadas al instalar):

| Librería | Uso |
|---|---|
| `sqlalchemy[asyncio]` 2.x | ORM async |
| `asyncpg` | Driver PostgreSQL async |
| `alembic` | Migraciones |
| `bcrypt` | Hash de contraseñas (uso directo, **sin passlib**) |
| `pyjwt` | Emisión/validación de JWT |
| `email-validator` (o `pydantic[email]`) | Soporte de `EmailStr` en Pydantic v2 |

Dev/test: `aiosqlite` (BD de integración en memoria). Instalación: `poetry add <paquete>` /
`poetry add --group dev aiosqlite`; luego `poetry lock`.

## 9. Notes

- **Seguridad**:
  - Bcrypt costo ≥ 12; contraseña en claro nunca logueada ni retornada; `hash_contrasena`
    excluido de todos los DTOs de respuesta.
  - Mensaje de login genérico e idéntico para "usuario no existe", "contraseña incorrecta" y
    "usuario inactivo"; siempre ejecutar la comparación bcrypt (hash dummy si no hay usuario)
    para evitar enumeración por tiempo de respuesta.
  - `JWT_SECRETO` solo vía entorno, longitud mínima 32 validada en `Settings`; decodificar
    siempre con `algorithms=["HS256"]` explícito (previene ataque `none`).
  - Los tokens de refresco no otorgan acceso a recursos; distinguir por claim `tipo`.
  - CORS ya restringido a `http://localhost:4200` con `allow_headers=["*"]` — el header
    `Authorization` ya está permitido; no tocar esa configuración.
- **Rendimiento**: verificación bcrypt CPU-bound (~100 ms) vía `asyncio.to_thread`; consulta de
  login por el índice único de `correo`.
- **DDD**: ni `domain/` ni `application/` importan FastAPI, SQLAlchemy, bcrypt ni jwt — los tests
  unitarios deben poder ejecutarse sin esas librerías en las capas internas.
- **Arquitectura del repo**: los routers nuevos se registran en
  `src/presentation/routers/__init__.py` (agregador `api_router`), no en `src/main.py` — la
  tabla del enriquecimiento menciona modificar `main.py`, pero el patrón vigente del repo lo
  hace innecesario.
- **Observabilidad**: INFO para inicios de sesión exitosos, WARNING para fallidos (solo el
  correo), usando `configurar_logging` existente.
- **Idioma**: todo en español (identificadores, comentarios, logs, tests, commits, PR) salvo
  palabras reservadas y APIs de terceros. Commits convencionales, p. ej.
  `feat(auth): implementa login y refresh JWT para SP-140`.
- **Dominio SST**: los roles siguen `.sst-agent-document.md` — `AUDITOR_SST` y `ADMINISTRADOR`
  tendrán acceso futuro a información médica e índices de siniestralidad; `CONSULTA` es solo
  lectura de información no sensible. `requerir_roles` es la pieza que lo hará cumplir.
- SP-176 y SP-177 son del repositorio frontend Angular — fuera del alcance de código de este repo.

## 10. Implementation Verification Checklist

- [ ] Calidad: sin errores de lint (`ruff`) ni de tipos (`mypy --strict`); inyección por constructor en servicios y repositorios
- [ ] Dominio: `Usuario.crear()` valida invariantes; enum `RolUsuario` alineado con el frontend
- [ ] Aplicación: `ServicioAutenticacion` usa DTOs y puertos — sin acceso directo a BD ni imports de infraestructura
- [ ] Presentación: handlers delgados; toda entrada validada por Pydantic antes del servicio; `requerir_roles` reutilizable
- [ ] Migraciones: tabla `usuarios` creada solo vía Alembic (`create_all` únicamente en tests)
- [ ] Tests: todos en verde, cobertura ≥ 90 %, todos los códigos HTTP cubiertos (200, 401×3, 403, 422)
- [ ] Seed idempotente verificado (doble ejecución)
- [ ] Documentación: `data-model.md` y `api-spec.yml` actualizados con entidad, enum, endpoints y `bearerAuth`
