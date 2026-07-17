# Plan de implementación backend: SP-144 Modelo de Base de Datos para Estándares Mínimos (Res. 0312)

## 1. Resumen

Implementar la persistencia y la API REST de la autoevaluación de estándares
mínimos (Resolución 0312 de 2019), tomando como contrato el modelo ER validado
en SP-183 (`docs/diagramas/diagrama_er_sst.dbml` y `ai-specs/specs/data-model.md`,
sección «Modelo SST»). El catálogo `estandares_minimos` (60 ítems) y la
autenticación JWT con RBAC ya existen (SP-143 y tickets previos): esta HU agrega
las tres tablas transaccionales (`empresas`, `autoevaluaciones`,
`calificaciones_estandar`), los agregados de dominio con la lógica de
calificación derivada, y 8 endpoints bajo `/api/v1`.

- **Stack activo**: `python-fastapi` (Python 3.12 + FastAPI, SQLAlchemy 2.x
  async, Alembic, PostgreSQL, Pydantic v2).
- **Arquitectura**: DDD por capas — dominio puro (sin SQLAlchemy/FastAPI),
  servicios de aplicación con DTOs Pydantic, routers finos con `Depends()`,
  ORM y repositorios concretos solo en `infrastructure/`.
- **Fuente normativa**: `.sst-agent-document.md` (umbral 85 %, calificación
  CUMPLE/NO_CUMPLE/NO_APLICA, obligación de plan de mejoramiento).

**Fuera de alcance**: pantalla Angular (SP-189, repo frontend),
`planes_mejoramiento` y demás entidades del ER (tickets posteriores), gestión
completa de empresas (solo CRUD mínimo de soporte).

## Estimación de puntos de historia

<!-- STORY_POINTS:8 -->
- **HU total**: 8 (Fibonacci: 1, 2, 3, 5, 8, 13)
- **Justificación**: migración de 3 tablas con FKs e índices únicos, 4 agregados
  de dominio con lógica derivada (puntaje, puntaje_total, umbral 85,
  inmutabilidad tras finalizar), 3 repositorios con doble interfaz +
  implementación, 8 endpoints con RBAC y upsert idempotente, y una suite de
  integración amplia (flujo feliz de 60 ítems + matriz de errores
  401/403/404/409/422). La incertidumbre es baja porque el ER está validado y
  el catálogo/autenticación ya existen; el volumen de archivos y pruebas
  justifica el 8. Coincide con la estimación ya registrada en Jira.
- **Subtareas**:
  | Subtarea | Puntos | Nota |
  |---|---|---|
  | SP-187 | 3 | Migración + ORM + dominio + repositorios (sin endpoints) |
  | SP-188 | 5 | 8 endpoints con RBAC, upsert, finalización y suite de integración |
  | SP-189 | 5 | Pantalla Angular — repo frontend, **no cubierta por este plan** |
<!-- /STORY_POINTS -->

## 2. Contexto de arquitectura

- Stack activo: `python-fastapi` (`Python 3.12 + FastAPI`)
- Capas involucradas:

| Capa | Archivos afectados |
|---|---|
| Infrastructure | `alembic/versions/c3d4e5f6a7b8_crear_tablas_autoevaluacion.py` (nueva); `src/infrastructure/database/modelos/{empresa_orm,autoevaluacion_orm,calificacion_estandar_orm}.py` (nuevos); `src/infrastructure/database/modelos/__init__.py` (registrar ORMs); `src/infrastructure/repositories/{repositorio_empresa_sqlalchemy,repositorio_estandar_minimo_sqlalchemy,repositorio_autoevaluacion_sqlalchemy}.py` (nuevos) |
| Domain | `src/domain/models/{empresa,estandar_minimo,autoevaluacion}.py` (nuevos; `autoevaluacion.py` incluye `CalificacionEstandar`); `src/domain/exceptions/autoevaluacion.py` (nuevo); `src/domain/repositories/{repositorio_empresa,repositorio_estandar_minimo,repositorio_autoevaluacion}.py` (nuevos) |
| Application | `src/application/dto/` (7 DTOs nuevos); `src/application/mappers/{mapper_empresa,mapper_autoevaluacion,mapper_estandar_minimo}.py` (nuevos); `src/application/services/{servicio_empresas,servicio_autoevaluaciones}.py` (nuevos) |
| Presentation | `src/presentation/routers/{empresas_router,autoevaluaciones_router,estandares_router}.py` (nuevos); `src/presentation/dependencies/autoevaluacion.py` (nuevo — factorías + guard escritor); `src/presentation/routers/__init__.py` (registrar los 3 routers en el agregador — el patrón del repo evita tocar `src/main.py`) |
| Docs | `ai-specs/specs/api-spec.yml`, `ai-specs/specs/data-model.md` |
| Tests | `tests/unit/domain/`, `tests/unit/application/`, `tests/integration/` (nuevos módulos; ver Paso 10) |

### Mapeo de subtareas

| Clave | Resumen | Paso(s) de implementación |
|---|---|---|
| `SP-187` | Diseñar tabla de estándares y estado de evaluaciones | Pasos 1, 2, 3, 8 (parcial: ORM/repos), 10 (unitarios de dominio + integración de repositorios/migración), 11 (data-model.md) |
| `SP-188` | Desarrollar API REST CRUD para autoevaluación 0312 | Pasos 4, 5, 6, 7, 9, 10 (integración httpx), 11 (api-spec.yml) |
| `SP-189` | Crear pantalla responsiva de diagnóstico en Angular | Fuera de este repo (frontend) — sin pasos aquí |

## 3. Pasos de implementación

### Paso 0: Crear la rama feature

- **Acción**: crear y cambiar a la rama de la HU (las features del proyecto
  parten de `develop` y sus PRs apuntan a `develop`).
- **Rama**: `feature/SP-144-backend`
- **Comandos**:
  ```bash
  git checkout develop && git pull origin develop
  git checkout -b feature/SP-144-backend
  ```

### Paso 1: Migración Alembic — tablas transaccionales

- **Archivo**: `alembic/versions/c3d4e5f6a7b8_crear_tablas_autoevaluacion.py`
- **`down_revision`**: `b2c3d4e5f6a7` (catálogos SST de SP-143).
- **Contenido** (tipos y restricciones exactos del ER validado; toda tabla con
  `id UUID` PK generado en aplicación y `fecha_creacion`/`fecha_actualizacion`
  `TIMESTAMPTZ NOT NULL server_default=now()`, con `onupdate` en el ORM):
  - **`empresas`**: `razon_social VARCHAR(200) NOT NULL`,
    `nit VARCHAR(20) NOT NULL` + **índice único** `uq_empresas_nit`,
    `actividad_economica VARCHAR(200) NOT NULL`,
    `nivel_riesgo_arl VARCHAR(5) NOT NULL` (valores `I..V`, validados en dominio),
    `numero_trabajadores INTEGER NOT NULL` (invariante `> 0` en dominio).
  - **`autoevaluaciones`**: `empresa_id UUID NOT NULL FK → empresas.id` con
    índice (`ix_autoevaluaciones_empresa_id`), `usuario_id UUID NOT NULL FK →
    usuarios.id`, `fecha DATE NOT NULL`, `puntaje_total NUMERIC(5,2) NULL`,
    `requiere_plan_mejora BOOLEAN NOT NULL server_default=false`.
  - **`calificaciones_estandar`**: `autoevaluacion_id UUID NOT NULL FK →
    autoevaluaciones.id` con índice (`ix_calificaciones_estandar_autoevaluacion_id`),
    `estandar_id UUID NOT NULL FK → estandares_minimos.id`,
    `resultado VARCHAR(20) NOT NULL`, `puntaje NUMERIC(5,2) NOT NULL`,
    `observaciones TEXT NULL`, **índice único compuesto**
    `uq_calificaciones_estandar_autoevaluacion_estandar (autoevaluacion_id, estandar_id)`.
  - **`downgrade()`** completo: elimina las tres tablas en orden inverso
    (`calificaciones_estandar` → `autoevaluaciones` → `empresas`).
- **Verificación**: `alembic upgrade head` y `alembic downgrade -1` contra
  PostgreSQL (Docker disponible en el entorno).

### Paso 2: Modelos de dominio (puros, sin frameworks)

- **`src/domain/models/empresa.py`** — `@dataclass Empresa` con
  `NIVELES_RIESGO_ARL = ("I", "II", "III", "IV", "V")` y factoría
  `Empresa.crear(razon_social, nit, actividad_economica, nivel_riesgo_arl,
  numero_trabajadores)` que valida invariantes: `razon_social` y
  `actividad_economica` no vacíos, `nit` no vacío, `nivel_riesgo_arl ∈ I..V`,
  `numero_trabajadores > 0`. Violación → `DatosEmpresaInvalidosError`
  (o `ValueError` de dominio mapeado a 422; ver Paso 7).
- **`src/domain/models/estandar_minimo.py`** — `@dataclass EstandarMinimo`
  (lectura del catálogo): `id`, `ciclo_phva` (enum `CicloPHVA`:
  `PLANEAR | HACER | VERIFICAR | ACTUAR`), `numeral`, `descripcion`,
  `valor_porcentual: Decimal`.
- **`src/domain/models/autoevaluacion.py`** — agregado raíz con:
  - Enum `ResultadoCalificacion`: `CUMPLE | NO_CUMPLE | NO_APLICA`.
  - Constante de dominio `UMBRAL_PLAN_MEJORA = Decimal("85")` y
    `TOTAL_ESTANDARES = 60`.
  - `@dataclass CalificacionEstandar` con factoría
    `CalificacionEstandar.calificar(estandar: EstandarMinimo, resultado,
    observaciones)` que **deriva** `puntaje`: `valor_porcentual` del ítem si
    `resultado ∈ {CUMPLE, NO_APLICA}`, `Decimal("0")` si `NO_CUMPLE`. El
    `puntaje` **nunca** se acepta del cliente.
  - `@dataclass Autoevaluacion` con `calificaciones: dict[UUID,
    CalificacionEstandar]` (clave `estandar_id`) y métodos:
    - `Autoevaluacion.crear(empresa_id, usuario_id, fecha)` — nace sin
      calificaciones, `puntaje_total = None`, `requiere_plan_mejora = False`.
    - `esta_finalizada` (propiedad): `puntaje_total is not None`.
    - `calificar(estandar, resultado, observaciones)` — upsert en el dict
      (recalificar reemplaza, no duplica); si `esta_finalizada` lanza
      `AutoevaluacionFinalizadaError`.
    - `finalizar()` — exige `len(calificaciones) == TOTAL_ESTANDARES`
      (si no, `AutoevaluacionIncompletaError` con el número de faltantes en
      `detalle`); fija `puntaje_total = suma de puntajes` y
      `requiere_plan_mejora = puntaje_total < UMBRAL_PLAN_MEJORA`
      (85.00 → `False`; 84.99 → `True`). Refinalizar lanza
      `AutoevaluacionFinalizadaError`.
- **Aritmética**: usar `Decimal` en todo el cálculo de puntajes (nunca `float`).

### Paso 3: Interfaces de repositorio (dominio)

- **`src/domain/repositories/repositorio_empresa.py`** — ABC `RepositorioEmpresa`:
  - `async def guardar(self, empresa: Empresa) -> Empresa`
  - `async def buscar_por_id(self, id: UUID) -> Empresa | None`
  - `async def buscar_por_nit(self, nit: str) -> Empresa | None`
  - `async def listar(self) -> list[Empresa]`
- **`src/domain/repositories/repositorio_estandar_minimo.py`** — ABC
  `RepositorioEstandarMinimo`:
  - `async def listar(self, ciclo_phva: CicloPHVA | None = None) -> list[EstandarMinimo]`
  - `async def buscar_por_id(self, id: UUID) -> EstandarMinimo | None`
  - `async def contar(self) -> int` (soporta la regla de finalización sin
    fijar 60 en duro si el catálogo variara)
- **`src/domain/repositories/repositorio_autoevaluacion.py`** — ABC
  `RepositorioAutoevaluacion`:
  - `async def guardar(self, autoevaluacion: Autoevaluacion) -> Autoevaluacion`
    (persiste el agregado completo: upsert de calificaciones incluido, en una
    transacción)
  - `async def buscar_por_id(self, id: UUID) -> Autoevaluacion | None`
    (calificaciones embebidas, cargadas con `selectinload`)
  - `async def listar_por_empresa(self, empresa_id: UUID) -> list[Autoevaluacion]`
    (orden `fecha` desc)
- Todas devuelven **modelos de dominio**, nunca ORM.

### Paso 4: DTOs (Pydantic v2)

- **`src/application/dto/solicitud_crear_empresa.py`** —
  `SolicitudCrearEmpresa`: `razon_social: str`, `nit: str`,
  `actividad_economica: str`, `nivel_riesgo_arl: str`,
  `numero_trabajadores: int`. Validación de formato en Pydantic
  (`min_length`, `gt=0`, `Literal["I","II","III","IV","V"]`); las invariantes
  se re-verifican en dominio.
- **`src/application/dto/respuesta_empresa.py`** — `RespuestaEmpresa`: todos
  los campos + `id`, `fecha_creacion`, `fecha_actualizacion`.
- **`src/application/dto/solicitud_crear_autoevaluacion.py`** —
  `SolicitudCrearAutoevaluacion`: `empresa_id: UUID`, `fecha: date`.
  **Sin** `usuario_id` (sale del token), **sin** campos derivados.
- **`src/application/dto/respuesta_autoevaluacion.py`** —
  `RespuestaAutoevaluacion`: `id`, `empresa_id`, `usuario_id`, `fecha`,
  `puntaje_total: Decimal | None`, `requiere_plan_mejora: bool`,
  `calificaciones: list[RespuestaCalificacionEstandar]` (vacía en el listado
  histórico, embebidas en el detalle), timestamps.
- **`src/application/dto/solicitud_calificar_estandar.py`** —
  `SolicitudCalificarEstandar`: `resultado: Literal["CUMPLE","NO_CUMPLE","NO_APLICA"]`,
  `observaciones: str | None = None`. Pydantic con `extra="forbid"` (o
  equivalente) para **rechazar** `puntaje` u otros campos derivados enviados
  por el cliente → 422.
- **`src/application/dto/respuesta_calificacion_estandar.py`** —
  `RespuestaCalificacionEstandar`: `estandar_id`, `resultado`,
  `puntaje: Decimal`, `observaciones`.
- **`src/application/dto/respuesta_estandar_minimo.py`** —
  `RespuestaEstandarMinimo`: `id`, `ciclo_phva`, `numeral`, `descripcion`,
  `valor_porcentual`.
- Aplicar `extra="forbid"` también en `SolicitudCrearAutoevaluacion` para
  rechazar `puntaje_total`/`requiere_plan_mejora`/`usuario_id` del cliente.

### Paso 5: Mappers y servicios de aplicación

- **Mappers** (funciones puras dominio ↔ DTO):
  `mapper_empresa.py`, `mapper_autoevaluacion.py` (incluye calificaciones),
  `mapper_estandar_minimo.py`.
- **`src/application/services/servicio_empresas.py`** — `ServicioEmpresas`
  (inyección por constructor de `RepositorioEmpresa`):
  - `crear(dto) -> RespuestaEmpresa`: si `buscar_por_nit` encuentra →
    `NitDuplicadoError` (409); si no, `Empresa.crear(...)` + `guardar`.
  - `listar() -> list[RespuestaEmpresa]`.
  - `obtener(id) -> RespuestaEmpresa`: `None` → `EmpresaNoEncontradaError` (404).
- **`src/application/services/servicio_autoevaluaciones.py`** —
  `ServicioAutoevaluaciones` (inyecta `RepositorioAutoevaluacion`,
  `RepositorioEmpresa`, `RepositorioEstandarMinimo`):
  - `crear(dto, usuario_id) -> RespuestaAutoevaluacion`: valida empresa
    existente (`EmpresaNoEncontradaError` si no) y crea vía
    `Autoevaluacion.crear`.
  - `listar_por_empresa(empresa_id)` — histórico desc.
  - `obtener(id)` — `None` → `AutoevaluacionNoEncontradaError` (404).
  - `calificar(autoevaluacion_id, estandar_id, dto) ->
    RespuestaCalificacionEstandar`: carga autoevaluación (404) y estándar
    (`EstandarNoEncontradoError`, 404), delega en `autoevaluacion.calificar`
    (dominio lanza 409 si finalizada, deriva el puntaje) y persiste el
    agregado. Upsert idempotente.
  - `finalizar(autoevaluacion_id) -> RespuestaAutoevaluacion`: usa
    `repositorio_estandar_minimo.contar()` como total exigido, delega en
    `autoevaluacion.finalizar()` (409 incompleta / 409 finalizada) y persiste.
  - `listar_estandares(ciclo_phva)` — puede vivir aquí o en un servicio de
    catálogo mínimo; mantenerlo en `ServicioAutoevaluaciones` evita un tercer
    servicio para un solo método de lectura.
- Sin imports de SQLAlchemy ni FastAPI en esta capa.

### Paso 6: Routers y dependencias (presentación)

- **`src/presentation/dependencies/autoevaluacion.py`** (nuevo):
  - Factorías `Depends()`: `obtener_repositorio_empresa`,
    `obtener_repositorio_estandar_minimo`, `obtener_repositorio_autoevaluacion`
    (sobre `obtener_sesion`), `obtener_servicio_empresas`,
    `obtener_servicio_autoevaluaciones`.
  - **Guard escritor** `requerir_rol_escritor`: dependencia que parte de
    `obtener_usuario_actual` y, si `usuario.rol == RolUsuario.CONSULTA`, lanza
    `AccesoDenegadoError` (403, código `ACCESO_DENEGADO`). No se reutiliza
    `requerir_roles` de `dependencies/autenticacion.py` porque ese guard emite
    `PERMISOS_INSUFICIENTES` y el criterio de aceptación exige el código
    estable `ACCESO_DENEGADO` (ver Nota en §9).
- **`src/presentation/routers/estandares_router.py`** —
  `GET /estandares-minimos` → 200 `list[RespuestaEstandarMinimo]`; query param
  opcional `ciclo_phva: Literal["PLANEAR","HACER","VERIFICAR","ACTUAR"] | None`
  (valor inválido → 422). Lectura: exige usuario autenticado
  (`obtener_usuario_actual`), los tres roles pueden.
- **`src/presentation/routers/empresas_router.py`**:
  - `POST /empresas` → 201 `RespuestaEmpresa` (guard escritor; 409 `NIT_DUPLICADO`).
  - `GET /empresas` → 200 lista (autenticado).
  - `GET /empresas/{id}` → 200 | 404 `EMPRESA_NO_ENCONTRADA` (autenticado).
- **`src/presentation/routers/autoevaluaciones_router.py`**:
  - `POST /autoevaluaciones` → 201 (guard escritor; `usuario_id` tomado del
    usuario del token, jamás del body).
  - `GET /autoevaluaciones?empresa_id=<uuid>` → 200 histórico desc (autenticado).
  - `GET /autoevaluaciones/{id}` → 200 detalle con calificaciones | 404.
  - `PUT /autoevaluaciones/{id}/calificaciones/{estandar_id}` → 200 upsert
    (guard escritor; 404 autoevaluación/estándar; 409 `AUTOEVALUACION_FINALIZADA`).
  - `POST /autoevaluaciones/{id}/finalizar` → 200 con `puntaje_total` y
    `requiere_plan_mejora` (guard escritor; 409 `AUTOEVALUACION_INCOMPLETA` |
    `AUTOEVALUACION_FINALIZADA`).
- **Registro**: añadir los tres routers en
  `src/presentation/routers/__init__.py` con `prefix=settings.api_prefix`
  (patrón del agregador del repo — `src/main.py` no requiere cambios).
- Routers finos: validar con Pydantic, llamar al servicio, devolver DTO.

### Paso 7: Excepciones de dominio y manejo de errores

- **Archivo**: `src/domain/exceptions/autoevaluacion.py` — subclases de
  `DomainException` (ya aporta `code`/`http_status` y el handler global ya
  serializa `RespuestaError`):

| Excepción | `codigo` | HTTP |
|---|---|---|
| `EmpresaNoEncontradaError` | `EMPRESA_NO_ENCONTRADA` | 404 |
| `NitDuplicadoError` | `NIT_DUPLICADO` | 409 |
| `AutoevaluacionNoEncontradaError` | `AUTOEVALUACION_NO_ENCONTRADA` | 404 |
| `EstandarNoEncontradoError` | `ESTANDAR_NO_ENCONTRADO` | 404 |
| `AutoevaluacionIncompletaError` | `AUTOEVALUACION_INCOMPLETA` | 409 |
| `AutoevaluacionFinalizadaError` | `AUTOEVALUACION_FINALIZADA` | 409 |
| `AccesoDenegadoError` | `ACCESO_DENEGADO` | 403 |
| `DatosEmpresaInvalidosError` | `DATOS_EMPRESA_INVALIDOS` | 422 |

- No se requieren handlers nuevos: `domain_handler.py` ya mapea cualquier
  `DomainException` al contrato `RespuestaError` (`exito`, `codigo`,
  `mensaje`, `detalle`); `validation_handler.py` ya cubre el 422 de Pydantic.
- Defensa en profundidad: capturar `IntegrityError` del índice único de NIT en
  el repositorio de empresas y relanzar `NitDuplicadoError` (carrera entre el
  chequeo previo y el INSERT).

### Paso 8: Modelos ORM e implementaciones de repositorio (infraestructura)

- **ORM** (`src/infrastructure/database/modelos/`, patrón de
  `estandar_minimo_orm.py`: `Mapped`/`mapped_column`, `Uuid()`, `default=uuid4`,
  timestamps con `server_default=func.now()` + `onupdate`):
  - `empresa_orm.py` — `EmpresaORM`, `nit` con `unique=True, index=True`.
  - `autoevaluacion_orm.py` — `AutoevaluacionORM` con
    `relationship("CalificacionEstandarORM", cascade="all, delete-orphan")`.
  - `calificacion_estandar_orm.py` — `CalificacionEstandarORM` con
    `UniqueConstraint("autoevaluacion_id", "estandar_id")`.
  - Registrar los tres en `src/infrastructure/database/modelos/__init__.py`
    para que `Base.metadata` los conozca (tests con `create_all`).
- **Repositorios** (`src/infrastructure/repositories/`):
  - `repositorio_empresa_sqlalchemy.py` — mapea ORM ↔ dominio; traduce
    `IntegrityError` de NIT a `NitDuplicadoError`.
  - `repositorio_estandar_minimo_sqlalchemy.py` — lectura del catálogo con
    filtro `ciclo_phva` y `contar()`.
  - `repositorio_autoevaluacion_sqlalchemy.py` — `buscar_por_id` y
    `listar_por_empresa` con `selectinload` de calificaciones (sin N+1);
    `guardar` sincroniza el agregado (inserta/actualiza calificaciones por
    `(autoevaluacion_id, estandar_id)`) dentro de la transacción de la sesión.
- Nunca exponen objetos ORM fuera de la capa.

### Paso 9: Seguridad (transversal a los Pasos 4–6)

- Bearer JWT obligatorio en los 8 endpoints (`obtener_usuario_actual`;
  sin token → 401 `TOKEN_INVALIDO`, contrato ya existente).
- Escrituras (POST/PUT) solo `ADMINISTRADOR` y `AUDITOR_SST`; `CONSULTA` →
  403 `ACCESO_DENEGADO` vía `requerir_rol_escritor`.
- Campos derivados (`puntaje`, `puntaje_total`, `requiere_plan_mejora`) y
  `usuario_id` jamás aceptados del cliente (DTOs con `extra="forbid"` +
  derivación exclusiva en dominio).

### Paso 10: Pruebas (TDD — escribir primero las que definan cada regla)

- **Unitarias de dominio** (`tests/unit/domain/`; sin FastAPI ni SQLAlchemy):
  - `test_calificacion_estandar.py`: puntaje = `valor_porcentual` con
    `CUMPLE` y `NO_APLICA`; puntaje = 0 con `NO_CUMPLE`.
  - `test_autoevaluacion.py`: `finalizar` suma `puntaje_total`;
    `requiere_plan_mejora = True` con 84.99 y `False` con 85.00 (borde
    exacto, `Decimal`); finalizar con < 60 ítems →
    `AutoevaluacionIncompletaError`; recalificar tras finalizar →
    `AutoevaluacionFinalizadaError`; recalificar antes de finalizar reemplaza
    sin duplicar; refinalizar → `AutoevaluacionFinalizadaError`.
  - `test_empresa.py`: `Empresa.crear` rechaza `numero_trabajadores <= 0`,
    `nivel_riesgo_arl` fuera de `I..V`, NIT vacío.
- **Unitarias de servicios** (`tests/unit/application/`; repos mockeados):
  - crear autoevaluación con `empresa_id` inexistente →
    `EmpresaNoEncontradaError`; calificar `estandar_id` inexistente →
    `EstandarNoEncontradoError`; upsert reutiliza la calificación existente;
    crear empresa con NIT existente → `NitDuplicadoError`.
- **Integración** (`tests/integration/`; httpx `AsyncClient` + BD de prueba,
  catálogo de 60 ítems sembrado en fixture):
  - Flujo feliz completo: crear empresa → crear autoevaluación → calificar
    60 ítems → finalizar (verificar `puntaje_total` y
    `requiere_plan_mejora`) → consultar histórico y detalle.
  - 401 sin token en cada grupo de endpoints; 403 `ACCESO_DENEGADO` con rol
    `CONSULTA` en POST/PUT; 409 `NIT_DUPLICADO`; 422 con `resultado` inválido
    y con campos derivados en el body; 404 en empresa/autoevaluación/estándar
    inexistentes; recalificar un ítem no crea filas duplicadas (unicidad
    `(autoevaluacion_id, estandar_id)`); 409 `AUTOEVALUACION_FINALIZADA` al
    recalificar tras finalizar; 409 `AUTOEVALUACION_INCOMPLETA` con ítems
    faltantes; filtro `?ciclo_phva=` del catálogo.
  - Migración: `upgrade head` / `downgrade -1` reversibles contra la BD de
    integración (PostgreSQL en Docker).
- Convención `test_should_<algo>_when_<condicion>` traducida al proyecto
  (nombres en español, patrón AAA), como los tests existentes.

### Paso 11: Actualizar documentación técnica

- **`ai-specs/specs/data-model.md`**: marcar `empresas`, `autoevaluaciones` y
  `calificaciones_estandar` como **implementadas** con su migración
  (`c3d4e5f6a7b8_crear_tablas_autoevaluacion.py`) y ajustar la nota «solo
  `usuarios` está implementada» del bloque del modelo SST.
- **`ai-specs/specs/api-spec.yml`**: añadir los 8 endpoints con sus esquemas
  (request/response), seguridad Bearer, y las respuestas de error
  (`RespuestaError` con los códigos estables de este ticket).

## 4. Orden de implementación

1. Paso 0 — rama `feature/SP-144-backend`.
2. Paso 2 — modelos de dominio + Paso 7 (excepciones), guiados por los tests
   unitarios de dominio del Paso 10 (TDD).
3. Paso 3 — interfaces de repositorio.
4. Paso 1 — migración Alembic (verificar upgrade/downgrade).
5. Paso 8 — ORM + repositorios SQLAlchemy (test de integración de
   persistencia del agregado).
6. Paso 4 — DTOs y Paso 5 — mappers + servicios (tests unitarios con mocks).
7. Paso 6 + Paso 9 — dependencias, guard escritor y routers.
8. Paso 10 — completar suite de integración httpx (flujo feliz + matriz de
   errores) y verificación de cobertura ≥ 90 %.
9. Paso 11 — documentación (`data-model.md`, `api-spec.yml`).

## 5. Checklist de pruebas

- [ ] `pytest` pasa con 0 fallos
- [ ] `pytest --cov --cov-report=html` muestra ≥ 90 %
- [ ] `ruff check .` y `mypy --strict` sin errores
- [ ] `alembic upgrade head` y `alembic downgrade -1` reversibles contra PostgreSQL
- [ ] Los 8 endpoints probados manualmente (flujo feliz + 401/403/404/409/422)
- [ ] Recalificar un ítem no duplica filas; finalizar bloquea escrituras
- [ ] Los tests existentes (auth, catálogos, health/ping) siguen en verde

## 6. Referencia de tooling

| Propósito | Comando |
|---|---|
| Build | `pip install -r requirements.txt` |
| Test | `pytest` |
| Run | `uvicorn main:app --reload` |
| Lint | `ruff check .` |
| Cobertura | `pytest --cov --cov-report=html` |

> Nota del entorno local: los comandos se ejecutan vía Poetry
> (`poetry run pytest`, `poetry run alembic upgrade head`), con PostgreSQL de
> integración en Docker.

## 7. Formato de respuesta de error

Contrato único ya implementado (`src/application/dto/respuesta_error.py` +
handlers globales):

```json
{
  "exito": false,
  "codigo": "CODIGO_ERROR",
  "mensaje": "Descripción legible para humanos",
  "detalle": [{"campo": "mensaje de validación"}]
}
```

Mapeo HTTP de esta HU: 401 `TOKEN_INVALIDO` | 403 `ACCESO_DENEGADO` |
404 `EMPRESA_NO_ENCONTRADA` / `AUTOEVALUACION_NO_ENCONTRADA` /
`ESTANDAR_NO_ENCONTRADO` | 409 `NIT_DUPLICADO` / `AUTOEVALUACION_INCOMPLETA` /
`AUTOEVALUACION_FINALIZADA` | 422 `VALIDATION_ERROR` (Pydantic) /
`DATOS_EMPRESA_INVALIDOS` (invariantes de dominio) | 500 `ERROR_INTERNO`.

## 8. Dependencias

Ninguna librería nueva: FastAPI, SQLAlchemy 2.x async, Alembic, Pydantic v2,
pytest/httpx/pytest-asyncio y PostgreSQL ya están en el proyecto.

## 9. Notas

- **Contrato ER inmutable**: cualquier desviación del esquema debe pasar
  primero por `docs/diagramas/diagrama_er_sst.dbml` y `data-model.md`
  (decisión SP-183). Esta HU implementa el ER tal cual está validado.
- **Conflicto detectado y resuelto — código 403**: el guard existente
  `requerir_roles` emite `PERMISOS_INSUFICIENTES`, pero los criterios de
  aceptación de SP-144 exigen el código estable `ACCESO_DENEGADO`. El plan
  crea `AccesoDenegadoError` + `requerir_rol_escritor` para los endpoints
  nuevos y **no toca** los endpoints de autenticación existentes (que
  conservan su contrato). Si se prefiere unificar códigos en todo el API, es
  un ticket aparte.
- **Umbral 85 con borde exacto**: `requiere_plan_mejora = puntaje_total < 85`;
  85.00 no requiere plan, 84.99 sí. Usar `Decimal` end-to-end (los
  `valor_porcentual` son `NUMERIC(5,2)` y suman 100).
- **Derivados jamás del cliente**: `puntaje`, `puntaje_total`,
  `requiere_plan_mejora` y `usuario_id` (evaluador) se calculan/toman en
  servidor; DTOs con `extra="forbid"` los rechazan con 422.
- **Regla de los 60 ítems**: el total exigido al finalizar se toma de
  `RepositorioEstandarMinimo.contar()` (hoy 60), no de una constante mágica en
  el servicio; la constante de dominio queda documentada.
- **Consistencia**: calificar y finalizar ocurren dentro de la transacción de
  la sesión (patrón de sesión por request ya existente); timestamps en UTC
  (`TIMESTAMPTZ`).
- **Inmutabilidad tras finalizar**: la regla vive en el dominio
  (`Autoevaluacion.calificar`/`finalizar`), no en el router — cualquier vía de
  escritura futura la hereda.
- **`create_all` solo en tests**: el esquema de producción se aplica
  únicamente con Alembic.
- **Registro de routers**: el patrón del repo usa el agregador
  `src/presentation/routers/__init__.py`; `src/main.py` no cambia (el ticket
  lo lista por convención, pero el agregador lo hace innecesario).

## 10. Checklist de verificación de la implementación

- [ ] Calidad: sin errores de lint (`ruff`), `mypy --strict` limpio, inyección
      por constructor en servicios y repositorios
- [ ] Dominio: `Empresa`, `Autoevaluacion` y `CalificacionEstandar` imponen
      invariantes vía factorías; cero imports de SQLAlchemy/FastAPI en
      `src/domain/` y `src/application/`
- [ ] Aplicación: servicios reciben DTOs Pydantic y delegan en interfaces de
      repositorio — sin acceso directo a BD
- [ ] Presentación: routers finos, guard escritor en todas las escrituras,
      entradas validadas antes de llegar al servicio
- [ ] Migraciones: esquema solo vía Alembic (`down_revision b2c3d4e5f6a7`),
      upgrade/downgrade reversibles
- [ ] Tests: todos en verde, cobertura ≥ 90 %, todos los códigos HTTP del
      contrato cubiertos (201/200, 401, 403, 404, 409, 422)
- [ ] Documentación: `data-model.md` (tablas marcadas como implementadas) y
      `api-spec.yml` (8 endpoints) actualizados
