# Plan de implementación backend: SP-145 Persistencia de Matriz de Riesgos y Peligros (GTC 45)

## 1. Resumen

Implementar la persistencia y la API REST de la **matriz de peligros y riesgos
(GTC 45:2012 §2.1 y Anexo A)**, tomando como contrato el modelo ER validado en
SP-183 (`docs/diagramas/diagrama_er_sst.dbml` y `ai-specs/specs/data-model.md`).
El catálogo GTC (`catalogos_referencia`, ND Bajo = 0 — decisión D1), las
`empresas` y la autenticación JWT con RBAC ya existen (SP-143 / SP-144): esta HU
agrega las cuatro tablas transaccionales (`procesos_actividades`, `peligros`,
`evaluaciones_riesgo`, `controles_riesgo`), el dominio con cálculo derivado
`NP = ND × NE`, `NR = NP × NC`, interpretación NR (I–IV) y aceptabilidad
(tabla A.3), y los endpoints bajo `/api/v1` para alimentar la planilla.

- **Stack activo**: `python-fastapi` (Python 3.12 + FastAPI, SQLAlchemy 2.x
  async, Alembic, PostgreSQL, Pydantic v2).
- **Arquitectura**: DDD por capas — dominio puro (sin SQLAlchemy/FastAPI),
  servicios de aplicación con DTOs Pydantic, routers finos con `Depends()`,
  ORM y repositorios concretos solo en `infrastructure/`.
- **Fuente normativa**: `.sst-agent-document.md` Anexo A/B; decisión D1
  (ND «Bajo» = 0 → NP = 0, NR = 0, interpretación IV).

**Fuera de alcance**: pantalla Angular (SP-192, repo frontend), auditorías /
hallazgos / planes de mejora, cambiar D1, rehacer catálogos o empresas.

## Estimación de puntos de historia

<!-- STORY_POINTS:13 -->
- **HU total**: 13 (Fibonacci: 1, 2, 3, 5, 8, 13)
- **Justificación**: migración de 4 tablas jerárquicas con FKs, dominio GTC con
  conjuntos discretos ND/NE/NC y derivados (NP/NR/interpretación/aceptabilidad)
  incluyendo bordes A.3 y D1, 4 repositorios + vista agregada sin N+1, CRUD
  anidado con RBAC y suite de integración amplia. La incertidumbre es baja
  (ER validado, patrones SP-144 reutilizables); el volumen y la lógica Anexo A
  justifican el 13. Coincide con la estimación ya registrada en Jira.
- **Subtareas**:
  | Subtarea | Puntos | Nota |
  |---|---|---|
  | SP-190 | 5 | Migración 4 tablas + ORM + dominio Anexo A + repositorios |
  | SP-191 | 5 | Endpoints CRUD anidado + matriz agregada + integración httpx |
  | SP-192 | 5 | Planilla Angular — repo frontend, **no cubierta por este plan** |
<!-- /STORY_POINTS -->

## 2. Contexto de arquitectura

- Stack activo: `python-fastapi` (`Python 3.12 + FastAPI`)
- Capas involucradas:

| Capa | Archivos afectados |
|---|---|
| Infrastructure | `alembic/versions/d4e5f6a7b8c9_crear_tablas_matriz_gtc45.py` (nueva); `src/infrastructure/database/modelos/{proceso_actividad_orm,peligro_orm,evaluacion_riesgo_orm,control_riesgo_orm}.py` (nuevos); `src/infrastructure/database/modelos/__init__.py` (registrar ORMs); `src/infrastructure/repositories/{repositorio_proceso_actividad_sqlalchemy,repositorio_peligro_sqlalchemy,repositorio_evaluacion_riesgo_sqlalchemy,repositorio_control_riesgo_sqlalchemy,repositorio_matriz_riesgo_sqlalchemy}.py` (nuevos; el último puede ser un método en proceso o un repo de lectura agregada) |
| Domain | `src/domain/models/{proceso_actividad,peligro,evaluacion_riesgo,control_riesgo}.py` (nuevos); `src/domain/exceptions/matriz_riesgo.py` (nuevo); `src/domain/repositories/{repositorio_proceso_actividad,repositorio_peligro,repositorio_evaluacion_riesgo,repositorio_control_riesgo}.py` (nuevos) |
| Application | `src/application/dto/` (solicitudes/respuestas proceso, peligro, evaluación, control, matriz); `src/application/mappers/mapper_matriz_riesgo.py` (nuevo); `src/application/services/servicio_matriz_riesgos.py` (nuevo) |
| Presentation | `src/presentation/routers/matriz_riesgos_router.py` (nuevo; o routers por recurso si se prefiere split); `src/presentation/dependencies/matriz_riesgo.py` (nuevo — factorías + reutilizar `requerir_rol_escritor`); `src/presentation/routers/__init__.py` (registrar) |
| Docs | `ai-specs/specs/api-spec.yml`, `ai-specs/specs/data-model.md` |
| Tests | `tests/unit/domain/`, `tests/unit/application/`, `tests/integration/` |

### Mapeo de subtareas

| Clave | Resumen | Paso(s) de implementación |
|---|---|---|
| `SP-190` | Modelar tablas para procesos actividades y peligros GTC 45 | Pasos 1, 2, 3, 8, 10 (unitarios dominio + integración repos/migración), 11 (`data-model.md`) |
| `SP-191` | Desarrollar endpoints de persistencia de Matriz GTC 45 | Pasos 4, 5, 6, 7, 9, 10 (integración httpx), 11 (`api-spec.yml`) |
| `SP-192` | Crear planilla interactiva editable en Angular | Fuera de este repo (frontend) — sin pasos aquí |

## 3. Pasos de implementación

### Paso 0: Crear la rama feature

- **Acción**: crear y cambiar a la rama de la HU (PRs a `develop`).
- **Rama**: `feature/SP-145-backend`
- **Comandos**:
  ```bash
  git checkout develop && git pull origin develop
  git checkout -b feature/SP-145-backend
  ```

### Paso 1: Migración Alembic — tablas matriz GTC 45

- **Archivo**: `alembic/versions/d4e5f6a7b8c9_crear_tablas_matriz_gtc45.py`
- **`down_revision`**: `c3d4e5f6a7b8` (autoevaluación SP-144).
- **Contenido** (tipos exactos del ER; `id UUID` PK en aplicación;
  `fecha_creacion`/`fecha_actualizacion` `TIMESTAMPTZ NOT NULL
  server_default=now()`):
  - **`procesos_actividades`**: `empresa_id UUID NOT NULL FK → empresas.id`
    + índice `ix_procesos_actividades_empresa_id`, `nombre VARCHAR(150) NOT NULL`,
    `es_rutinaria BOOLEAN NOT NULL`, `zona_lugar VARCHAR(150) NULL`.
  - **`peligros`**: `proceso_actividad_id UUID NOT NULL FK →
    procesos_actividades.id` + índice, `clasificacion VARCHAR(40) NOT NULL`,
    `descripcion TEXT NOT NULL`, `efectos_posibles TEXT NULL`.
  - **`evaluaciones_riesgo`**: `peligro_id UUID NOT NULL FK → peligros.id` +
    **único** `uq_evaluaciones_riesgo_peligro_id` (1—1), `nivel_deficiencia
    SMALLINT NOT NULL`, `nivel_exposicion SMALLINT NOT NULL`,
    `nivel_consecuencia SMALLINT NOT NULL`, `nivel_probabilidad SMALLINT NOT
    NULL`, `nivel_riesgo INTEGER NOT NULL`, `interpretacion_nr VARCHAR(5)
    NOT NULL`, `aceptabilidad VARCHAR(40) NOT NULL`.
  - **`controles_riesgo`**: `evaluacion_riesgo_id UUID NOT NULL FK →
    evaluaciones_riesgo.id` + índice, `tipo VARCHAR(20) NOT NULL`,
    `descripcion TEXT NOT NULL`.
  - **FK / borrado**: `ON DELETE CASCADE` en la cadena proceso → peligro →
    evaluación → controles (eliminar un proceso limpia la rama). Documentar en
    notas del plan y en `data-model.md`.
  - **`downgrade()`**: drop en orden inverso
    (`controles_riesgo` → `evaluaciones_riesgo` → `peligros` →
    `procesos_actividades`).
- **Verificación**: `alembic upgrade head` y `alembic downgrade -1` contra
  PostgreSQL.

### Paso 2: Modelos de dominio (puros, sin frameworks)

- **Enums / constantes** (pueden vivir en `evaluacion_riesgo.py` o módulo
  `src/domain/models/gtc45.py`):
  - `ND_VALIDOS = frozenset({10, 6, 2, 0})`
  - `NE_VALIDOS = frozenset({4, 3, 2, 1})`
  - `NC_VALIDOS = frozenset({100, 60, 25, 10})`
  - `ClasificacionPeligro`: `BIOLOGICO | FISICO | QUIMICO | PSICOSOCIAL |
    BIOMECANICO | CONDICIONES_SEGURIDAD | FENOMENOS_NATURALES`
  - `TipoControl`: `ELIMINACION | SUSTITUCION | INGENIERIA | ADMINISTRATIVO | EPP`
  - `InterpretacionNR`: `I | II | III | IV`
  - `AceptabilidadRiesgo`: `NO_ACEPTABLE | ACEPTABLE_CON_CONTROL | MEJORABLE |
    ACEPTABLE`

- **`src/domain/models/proceso_actividad.py`** — `@dataclass ProcesoActividad`
  con `ProcesoActividad.crear(empresa_id, nombre, es_rutinaria, zona_lugar=None)`:
  `nombre` no vacío (strip); violación → `DatosProcesoInvalidosError` (422).

- **`src/domain/models/peligro.py`** — `@dataclass Peligro` con
  `Peligro.crear(proceso_actividad_id, clasificacion, descripcion,
  efectos_posibles=None)`: `descripcion` no vacía; `clasificacion` ∈ enum.

- **`src/domain/models/evaluacion_riesgo.py`** — núcleo normativo:
  - `EvaluacionRiesgo.crear(peligro_id, nivel_deficiencia, nivel_exposicion,
    nivel_consecuencia)`:
    1. Validar ND/NE/NC ∈ conjuntos; si no → `ValorGtcInvalidoError` (422,
       código `VALOR_GTC_INVALIDO`).
    2. `nivel_probabilidad = ND * NE` (0–40).
    3. `nivel_riesgo = NP * NC` (0–4000).
    4. `interpretacion_nr` por rangos A.3:
       - NR ∈ [600, 4000] → `I`
       - NR ∈ [150, 500] → `II`
       - NR ∈ [40, 120] → `III`
       - NR ≤ 20 (incluye 0) → `IV`
       - **Nota**: el ER/norma no define banda 21–39 ni 501–599; si aparece un
         NR “hueco” (no debería con conjuntos discretos), fallar con
         `ValorGtcInvalidoError` o mapear al nivel más cercano **solo si** un
         test de producto lo exige — por defecto fallar en test si el producto
         ND×NE×NC cae fuera (verificar con tabla de productos válidos en tests).
    5. `aceptabilidad` fija por interpretación:
       - I → `NO_ACEPTABLE`
       - II → `ACEPTABLE_CON_CONTROL`
       - III → `MEJORABLE`
       - IV → `ACEPTABLE`
  - Método `recalcular(nd, ne, nc)` para PUT (reemplazo 1—1).
  - Los derivados **nunca** se pasan al constructor público desde fuera.

- **`src/domain/models/control_riesgo.py`** — `@dataclass ControlRiesgo` con
  `ControlRiesgo.crear(evaluacion_riesgo_id, tipo, descripcion)`: `tipo` ∈
  enum; `descripcion` no vacía. (Aviso EPP-único es responsabilidad de UI /
  opcional en servicio; no bloquear persistencia.)

### Paso 3: Interfaces de repositorio (dominio)

- **`RepositorioProcesoActividad`**: `guardar`, `buscar_por_id`,
  `listar_por_empresa(empresa_id)`, `eliminar(id)`.
- **`RepositorioPeligro`**: `guardar`, `buscar_por_id`,
  `listar_por_proceso(proceso_id)`, `eliminar(id)`.
- **`RepositorioEvaluacionRiesgo`**: `guardar` (upsert por `peligro_id`),
  `buscar_por_peligro(peligro_id)`, `buscar_por_id`, `eliminar_por_peligro`.
- **`RepositorioControlRiesgo`**: `guardar`, `buscar_por_id`,
  `listar_por_evaluacion(evaluacion_id)`, `eliminar(id)`.
- **Lectura agregada** (opción A preferida): método
  `RepositorioProcesoActividad.obtener_matriz_por_empresa(empresa_id)` que
  retorna procesos con peligros, evaluación y controles cargados
  (`selectinload` en la implementación). Opción B: repo dedicado de lectura.
- Todas devuelven **modelos de dominio**, nunca ORM.

### Paso 4: DTOs (Pydantic v2)

- Solicitudes con `model_config = ConfigDict(extra="forbid")` para rechazar
  derivados:
  - `SolicitudCrearProcesoActividad` / `SolicitudActualizarProcesoActividad`:
    `nombre`, `es_rutinaria`, `zona_lugar: str | None`.
  - `SolicitudCrearPeligro` / `SolicitudActualizarPeligro`: `clasificacion`,
    `descripcion`, `efectos_posibles: str | None`.
  - `SolicitudUpsertEvaluacion`: solo `nivel_deficiencia: int`,
    `nivel_exposicion: int`, `nivel_consecuencia: int` — **sin** NP/NR/
    interpretación/aceptabilidad.
  - `SolicitudCrearControl` / `SolicitudActualizarControl`: `tipo`,
    `descripcion`.
- Respuestas incluyen ids, timestamps y, en evaluación, todos los derivados.
- `RespuestaMatrizRiesgos`: árbol
  `procesos[] → peligros[] → evaluacion? → controles[]`.

### Paso 5: Mappers y servicio de aplicación

- **`mapper_matriz_riesgo.py`**: funciones puras dominio ↔ DTO.
- **`ServicioMatrizRiesgos`** (inyecta repos de matriz + `RepositorioEmpresa`):
  - Procesos: `listar`/`crear`/`obtener`/`actualizar`/`eliminar` por
    `empresa_id` (404 `EMPRESA_NO_ENCONTRADA` / `PROCESO_NO_ENCONTRADO`).
  - Peligros: CRUD anidado a proceso (404 `PROCESO_NO_ENCONTRADO` /
    `PELIGRO_NO_ENCONTRADO`).
  - Evaluación: `obtener_evaluacion(peligro_id)`,
    `upsert_evaluacion(peligro_id, dto)` → dominio calcula derivados; 404
    peligro; 422 `VALOR_GTC_INVALIDO`.
  - Controles: CRUD bajo evaluación (404 `EVALUACION_NO_ENCONTRADA` /
    `CONTROL_NO_ENCONTRADO`).
  - `obtener_matriz(empresa_id)` → vista agregada.
- Sin imports de SQLAlchemy ni FastAPI.

### Paso 6: Routers y dependencias (presentación)

- **`src/presentation/dependencies/matriz_riesgo.py`**: factorías
  `Depends()` de repos y `ServicioMatrizRiesgos`. Reutilizar
  `requerir_rol_escritor` de `dependencies/autoevaluacion.py` (mismo código
  `ACCESO_DENEGADO`) — importar desde allí o mover el guard a un módulo
  compartido `dependencies/rbac.py` si se prefiere (refactor mínimo opcional).
- **`src/presentation/routers/matriz_riesgos_router.py`** (un router o varios
  con prefijos claros):

| Método | Ruta | Auth |
|---|---|---|
| GET | `/empresas/{empresa_id}/procesos-actividades` | autenticado |
| POST | `/empresas/{empresa_id}/procesos-actividades` | escritor → 201 |
| GET/PATCH/DELETE | `/procesos-actividades/{id}` | GET auth / mutación escritor; DELETE → 204 |
| GET/POST | `/procesos-actividades/{id}/peligros` | idem |
| GET/PATCH/DELETE | `/peligros/{id}` | idem |
| GET/PUT | `/peligros/{id}/evaluacion` | PUT escritor; 200 si reemplaza, 201 si crea |
| GET/POST | `/evaluaciones-riesgo/{id}/controles` | idem |
| PATCH/DELETE | `/controles-riesgo/{id}` | idem |
| GET | `/empresas/{empresa_id}/matriz-riesgos` | autenticado |

- **Registro**: incluir el router en `src/presentation/routers/__init__.py`
  con `prefix=settings.api_prefix` (`src/main.py` sin cambios).

### Paso 7: Excepciones de dominio

- **Archivo**: `src/domain/exceptions/matriz_riesgo.py` — subclases de
  `DomainException`:

| Excepción | `code` | HTTP |
|---|---|---|
| `ProcesoNoEncontradoError` | `PROCESO_NO_ENCONTRADO` | 404 |
| `PeligroNoEncontradoError` | `PELIGRO_NO_ENCONTRADO` | 404 |
| `EvaluacionNoEncontradaError` | `EVALUACION_NO_ENCONTRADA` | 404 |
| `ControlNoEncontradoError` | `CONTROL_NO_ENCONTRADO` | 404 |
| `ValorGtcInvalidoError` | `VALOR_GTC_INVALIDO` | 422 |
| `DatosProcesoInvalidosError` | `DATOS_PROCESO_INVALIDOS` | 422 |
| `DatosPeligroInvalidosError` | `DATOS_PELIGRO_INVALIDOS` | 422 |
| `DatosControlInvalidosError` | `DATOS_CONTROL_INVALIDOS` | 422 |

- Reutilizar `EmpresaNoEncontradaError` y `AccesoDenegadoError` existentes
  (SP-144). No hace falta handler nuevo: `domain_handler.py` ya serializa
  `RespuestaError` (`exito`, `codigo`, `mensaje`, `detalle`).

### Paso 8: ORM e implementaciones SQLAlchemy

- ORMs en `src/infrastructure/database/modelos/` (patrón `empresa_orm.py`:
  `Uuid()`, `default=uuid4`, timestamps `server_default`/`onupdate`).
  - Relaciones: `ProcesoActividadORM.peligros` cascade delete-orphan;
    `PeligroORM.evaluacion` uselist=False; `EvaluacionRiesgoORM.controles`.
  - Registrar en `modelos/__init__.py`.
- Repositorios: `_a_dominio` / `_a_orm` (o sync inline como autoevaluación);
  `selectinload` en matriz y en detalle de peligro+evaluación; nunca exponer
  ORM.

### Paso 9: Seguridad (transversal)

- Bearer JWT en todos los endpoints (`obtener_usuario_actual`; sin token →
  401).
- POST/PUT/PATCH/DELETE: `requerir_rol_escritor` → `CONSULTA` 403
  `ACCESO_DENEGADO`.
- DTOs `extra="forbid"` + cálculo exclusivo en dominio para derivados.

### Paso 10: Pruebas (TDD)

- **Unitarias de dominio** (`tests/unit/domain/`):
  - `test_evaluacion_riesgo.py`: ND=10, NE=4, NC=100 → NP=40, NR=4000, I,
    `NO_ACEPTABLE`; ND=0 → NP=0, NR=0, IV, `ACEPTABLE` (D1); bordes NR 600/500/
    120/20; ND/NE/NC inválidos → `ValorGtcInvalidoError`.
  - `test_proceso_actividad.py`, `test_peligro.py`, `test_control_riesgo.py`:
    factorías y validaciones.
- **Unitarias de servicio** (`tests/unit/application/`): empresa/proceso/
  peligro inexistentes; upsert evaluación; mocks de repos.
- **Integración** (`tests/integration/`):
  - Flujo feliz: empresa existente (fixture SP-144) → proceso → peligro →
    PUT evaluación → controles → `GET matriz-riesgos`.
  - 401 sin token; 403 `CONSULTA` en POST; 404; 422 ND inválido; body con
    `nivel_riesgo` extra → 422; DELETE proceso cascada limpia hijos.
  - Migración upgrade/downgrade en BD de integración (si el suite ya lo cubre
    para SP-144, replicar patrón).

### Paso 11: Documentación técnica

- **`ai-specs/specs/data-model.md`**: marcar las 4 tablas como implementadas
  con migración `d4e5f6a7b8c9`; anotar CASCADE.
- **`ai-specs/specs/api-spec.yml`**: paths, schemas de request/response,
  códigos de error, seguridad Bearer.

## 4. Orden de implementación

1. Paso 0 — rama `feature/SP-145-backend`
2. Paso 1 — migración Alembic
3. Paso 2 — modelos de dominio (+ tests unitarios Anexo A / D1)
4. Paso 3 — interfaces de repositorio
5. Paso 8 — ORM + repositorios SQLAlchemy (+ test integración persistencia)
6. Paso 7 — excepciones
7. Paso 4 — DTOs
8. Paso 5 — mappers + servicio
9. Paso 6 + 9 — routers, deps, RBAC
10. Paso 10 — completar suite integración httpx
11. Paso 11 — `data-model.md` + `api-spec.yml`

(SP-190 ≈ pasos 1–3, 8, parte 10/11; SP-191 ≈ 4–7, 9, resto 10/11.)

## 5. Checklist de pruebas

- [ ] `pytest` pasa con 0 fallos
- [ ] `pytest --cov --cov-report=html` muestra cobertura ≥ 90 %
- [ ] Endpoints nuevos verificados (feliz + 401/403/404/422)
- [ ] Tests existentes no rotos
- [ ] `ruff` y `mypy --strict` limpios

## 6. Referencia de tooling

| Propósito | Comando |
|---|---|
| Build | `pip install -r requirements.txt` |
| Test | `pytest` |
| Run | `uvicorn src.main:app --reload` |
| Coverage | `pytest --cov --cov-report=html` |
| Lint | `ruff check .` / `mypy --strict src` |

## 7. Formato de respuesta de error

```json
{
  "exito": false,
  "codigo": "VALOR_GTC_INVALIDO",
  "mensaje": "Descripción legible",
  "detalle": null
}
```

HTTP: 401 token | 403 `ACCESO_DENEGADO` | 404 entidad | 422 `VALOR_GTC_INVALIDO`
/ validación Pydantic | 500 interno (handler existente).

## 8. Dependencias

Ninguna librería nueva. Reutilizar stack actual (FastAPI, SQLAlchemy 2.x async,
Alembic, Pydantic v2, httpx en tests).

## 9. Notas

- **D1**: ND Bajo = 0 es decisión de producto ya validada; no “inventar” ND=1.
- **Derivados**: jamás persistir valores enviados por el cliente para NP/NR/
  interpretación/aceptabilidad.
- **1—1 peligro↔evaluación**: unique en `peligro_id`; PUT es upsert.
- **CASCADE**: borrar proceso elimina peligros, evaluación y controles de esa
  rama; documentar en OpenAPI.
- **EPP**: no bloquear API si el único control es EPP; la planilla (SP-192)
  puede advertir.
- **SP-192**: implementar en `sst-auditor-agent-pro-frontend` tras SP-191;
  consumir `GET .../matriz-riesgos` y mostrar derivados en solo lectura.
- Reutilizar patrones de SP-144 (`requerir_rol_escritor`, `RespuestaError`,
  registro de routers, tests `unit/` + `integration/`).

## 10. Checklist de verificación de implementación

- [ ] Calidad: sin errores de compilación, lint OK, inyección por constructor
- [ ] Dominio: invariantes vía factorías; sin SQLAlchemy/FastAPI
- [ ] Application: DTOs + repos; sin acceso crudo a BD
- [ ] Presentation: routers finos; inputs validados antes del servicio
- [ ] Migraciones: solo Alembic (no `create_all` en producción)
- [ ] Tests: verdes, cobertura ≥ 90 %, códigos HTTP cubiertos
- [ ] Docs: `data-model.md` y `api-spec.yml` actualizados
