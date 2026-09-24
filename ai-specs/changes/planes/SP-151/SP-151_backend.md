# Plan de implementación backend: SP-151 Metadatos de documentos adjuntos de soporte

## 1. Resumen

Persistir los **metadatos** de evidencias de soporte (no el binario) según el ER validado en SP-183 (decisión D4) y el Decreto 1072, Art. 2.2.4.6.13: nombre, MIME, tamaño, ruta relativa, fecha de carga, usuario que carga y calificación del estándar evaluado. Borrado lógico, nunca físico.

La tabla `evidencias` está especificada y **no migrada**. `calificaciones_estandar` y `usuarios` ya existen. `acciones_mejora` no existe: esta historia no crea `accion_mejora_id`.

- **Stack activo**: `python-fastapi` (Python 3.12 + FastAPI, SQLAlchemy 2.x async, Alembic, PostgreSQL, Pydantic v2).
- **Arquitectura**: DDD por capas. La factoría de dominio valida MIME, extensión, tamaño y ruta. El router solo delega.
- **Fuente normativa**: `.sst-agent-document.md` (conservación documental) y `ai-specs/specs/data-model.md` (entidad `evidencias`).

**Fuera de alcance**:

- Subida o lectura del archivo binario (disco, S3, URL firmada).
- Pantalla Angular.
- FK a `acciones_mejora` y el CHECK «al menos una asociación» del ER (hasta que exista esa tabla).
- Historias clínicas.

**Decisiones cerradas**:

1. El estándar evaluado se vincula con `calificacion_estandar_id` (NOT NULL). No hay FK directa a `estandares_minimos`.
2. `usuario_id` sale del Bearer. El body no lo acepta.
3. MIME permitidos: `application/pdf`, `image/jpeg`, `image/png`. Extensión del nombre debe coincidir (`.pdf`, `.jpg`/`.jpeg`, `.png`).
4. `tamano_bytes` > 0 y ≤ 10 MiB (`10485760`).
5. `ruta_almacenamiento` es relativa, sin `..` y sin esquema (`http`, `https`, `file`).
6. `DELETE` marca `activo=false` y `fecha_eliminacion`; el listado solo devuelve activas.

## Estimación de puntos de historia

<!-- STORY_POINTS:5 -->
- **HU total**: 5 (Fibonacci: 1, 2, 3, 5, 8, 13)
- **Justificación**: Una tabla, un agregado con validaciones cerradas y tres operaciones HTTP. No hay almacenamiento binario ni dependencia de planes de mejora. Coincide con el enriquecimiento.
- **Subtareas**:
  | Subtarea | Puntos | Nota |
  |---|---|---|
  | SP-208 | 2 | Migración + ORM + modelo de dominio |
  | SP-209 | 2 | MIME, extensión, tamaño y ruta |
  | SP-210 | 3 | FKs, servicio, router e integración |
<!-- /STORY_POINTS -->

## 2. Contexto de arquitectura

- Stack activo: `python-fastapi` (`Python 3.12 + FastAPI`)
- Capas involucradas:

| Capa | Archivos afectados |
|---|---|
| Infrastructure | `alembic/versions/<rev>_crear_tabla_evidencias.py` (`down_revision` = `d4e5f6a7b8c9`); `src/infrastructure/database/modelos/evidencia_orm.py`; registro en `modelos/__init__.py`; `src/infrastructure/repositories/repositorio_evidencia_sqlalchemy.py` |
| Domain | `src/domain/models/evidencia.py`; `src/domain/exceptions/evidencia.py`; `src/domain/repositories/repositorio_evidencia.py` |
| Application | `src/application/dto/solicitud_registrar_evidencia.py`; `src/application/dto/respuesta_evidencia.py`; `src/application/mappers/mapper_evidencia.py`; `src/application/services/servicio_evidencias.py` |
| Presentation | `src/presentation/routers/evidencias_router.py`; `src/presentation/dependencies/evidencia.py`; `src/presentation/routers/__init__.py` (`include_router`) |
| Docs | `ai-specs/specs/api-spec.yml`; `ai-specs/specs/data-model.md` |
| Tests | `tests/unit/domain/test_evidencia.py`; `tests/unit/application/test_servicio_evidencias.py`; `tests/integration/test_evidencias.py` |

### Mapeo de subtareas

| Clave | Resumen | Paso(s) de implementación |
|---|---|---|
| `SP-208` | Diseñar tabla de metadatos de archivos adjuntos | Pasos 1, 2, 8 (parcial), 9 (`data-model.md`) |
| `SP-209` | Definir tipos de archivo permitidos y validaciones | Paso 2 (factoría), Paso 7, Paso 8 (unitarios de rechazo) |
| `SP-210` | Relacionar metadatos con estándar y usuario que carga | Pasos 3, 4, 5, 6, 8 (integración), 9 (`api-spec.yml`) |

## 3. Pasos de implementación

### Paso 0: Crear la rama feature

- **Rama**: `feature/SP-151-backend` (desde `develop`).
- **Comandos**:
  ```bash
  git checkout develop && git pull origin develop
  git checkout -b feature/SP-151-backend
  ```

### Paso 1: Migración Alembic

- **Archivo**: `alembic/versions/<rev>_crear_tabla_evidencias.py`
- **`down_revision`**: `d4e5f6a7b8c9`
- **Tabla `evidencias`**:
  - `id UUID` PK
  - `calificacion_estandar_id UUID NOT NULL` FK → `calificaciones_estandar.id`, índice `ix_evidencias_calificacion_estandar_id`
  - `usuario_id UUID NOT NULL` FK → `usuarios.id`
  - `nombre_archivo VARCHAR(255) NOT NULL`
  - `tipo_mime VARCHAR(100) NOT NULL`
  - `tamano_bytes INTEGER NOT NULL`
  - `ruta_almacenamiento VARCHAR(500) NOT NULL`
  - `fecha_carga TIMESTAMPTZ NOT NULL`
  - `activo BOOLEAN NOT NULL` default `true`
  - `fecha_eliminacion TIMESTAMPTZ NULL`
  - `fecha_creacion` / `fecha_actualizacion TIMESTAMPTZ NOT NULL` `server_default=now()`
- **`downgrade()`**: `drop_table("evidencias")`
- No usar `Base.metadata.create_all()` en producción.

### Paso 2: Dominio

- **`src/domain/models/evidencia.py`**
  - Constantes: `TAMANO_MAXIMO_BYTES = 10 * 1024 * 1024`
  - Mapa MIME → extensiones: pdf, jpeg/jpg, png
  - `@dataclass Evidencia` con factoría `crear(calificacion_estandar_id, usuario_id, nombre_archivo, tipo_mime, tamano_bytes, ruta_almacenamiento)`
  - Validar nombre no vacío (≤ 255), MIME permitido, extensión coherente, tamaño en rango, ruta relativa segura
  - Método `dar_de_baja()` → `activo=False`, `fecha_eliminacion=now(UTC)`; si ya está inactiva, lanzar conflicto de dominio
- **`src/domain/exceptions/evidencia.py`**: `EvidenciaInvalidaError` (422), `CalificacionNoEncontradaError` (404) si no existe ya en autoevaluación, `EvidenciaNoEncontradaError` (404), `EvidenciaYaInactivaError` (409). Reutilizar `AccesoDenegadoError` del módulo de autoevaluación.

### Paso 3: Repositorio

- Puerto `RepositorioEvidencia`: `guardar`, `listar_activas_por_calificacion`, `buscar_por_id`
- Implementación SQLAlchemy que mapea ORM ↔ dominio y filtra `activo.is_(True)` en el listado
- El repositorio de calificaciones debe poder resolver una calificación por id (añadir `buscar_calificacion_por_id` solo si el puerto actual no lo expone)

### Paso 4: DTOs

- `SolicitudRegistrarEvidencia`: `nombre_archivo`, `tipo_mime`, `tamano_bytes`, `ruta_almacenamiento`. `extra=forbid`. Sin `usuario_id`.
- `RespuestaEvidencia`: `id`, `calificacion_estandar_id`, `usuario_id`, `nombre_archivo`, `tipo_mime`, `tamano_bytes`, `ruta_almacenamiento`, `fecha_carga`, `activo`

### Paso 5: Servicio

`ServicioEvidencias`:

- `registrar(calificacion_id, dto, usuario_id)`: 404 si la calificación no existe; `Evidencia.crear(...)`; persistir; 201
- `listar_activas(calificacion_id)`: 404 si la calificación no existe; solo activas
- `dar_de_baja(evidencia_id)`: 404 si no existe; 409 si ya está inactiva

### Paso 6: Router

Registrar en `src/presentation/routers/__init__.py` con `settings.api_prefix`.

- `POST /api/v1/calificaciones-estandar/{calificacion_id}/evidencias` — `requerir_rol_escritor`, 201
- `GET /api/v1/calificaciones-estandar/{calificacion_id}/evidencias` — usuario autenticado, 200
- `DELETE /api/v1/evidencias/{id}` — escritor, borrado lógico, 204

Errores con `RespuestaError`: 401, 403, 404, 409, 422.

### Paso 7: Excepciones

Registrar solo si el handler global de `DomainException` ya cubre `code` y `http_status` (sí lo cubre). No hace falta handler nuevo.

### Paso 8: Pruebas

- Unitarias de factoría: PDF válido; JPEG con `.jpg` y `.jpeg`; PNG; extensión cruzada; HTML/exe; tamaño 0 y 10 MiB + 1; ruta `../` y `https://`
- Unitarias de servicio con repositorios mock: 404 calificación, usuario del argumento (no del DTO), listado sin inactivas, baja lógica
- Integración HTTP: 201, GET sin inactivas, 403 `CONSULTA`, 404, 422, 204 y segundo DELETE → 409

### Paso 9: Documentación

- `ai-specs/specs/api-spec.yml`: los tres paths y `RespuestaEvidencia` / `SolicitudRegistrarEvidencia`
- `ai-specs/specs/data-model.md`: tabla implementada, columna `tamano_bytes`, nota de que `accion_mejora_id` sigue pendiente

## 4. Orden de implementación

1. Paso 0 — Rama `feature/SP-151-backend`
2. Paso 8 (parcial) — Tests de factoría en rojo
3. Paso 2 — Dominio y excepciones
4. Paso 1 — Migración y ORM
5. Paso 3 — Repositorio
6. Pasos 4 y 5 — DTOs, mapper y servicio
7. Paso 6 — Router y registro
8. Paso 8 — Integración HTTP
9. Paso 9 — `api-spec.yml` y `data-model.md`

## 5. Checklist de pruebas

- [ ] `pytest` pasa con 0 fallos
- [ ] `pytest --cov --cov-report=html` muestra cobertura ≥ 90 %
- [ ] Alta, listado y baja lógica probados con token de auditor
- [ ] Rol `CONSULTA` no escribe
- [ ] Ruff y mypy strict sin errores nuevos

## 6. Referencia de tooling

| Propósito | Comando |
|---|---|
| Build | `pip install -r requirements.txt` |
| Test | `pytest` |
| Run | `uvicorn main:app --reload` |
| Coverage | `pytest --cov --cov-report=html` |

## 7. Formato de respuesta de error

```json
{
  "exito": false,
  "codigo": "EVIDENCIA_INVALIDA",
  "mensaje": "Descripción legible en español",
  "detalle": null
}
```

Mapeo: 401 `TOKEN_INVALIDO` | 403 `ACCESO_DENEGADO` | 404 `CALIFICACION_NO_ENCONTRADA` / `EVIDENCIA_NO_ENCONTRADA` | 409 `EVIDENCIA_YA_INACTIVA` | 422 `EVIDENCIA_INVALIDA` / `ERROR_VALIDACION` | 500 `ERROR_INTERNO`.

## 8. Dependencias

Ninguna librería nueva.

## 9. Notas

- La ruta guardada no es una URL de descarga. Un ticket posterior puede almacenar el binario y firmar el acceso.
- No loguear el contenido del archivo (no se recibe) ni datos clínicos.
- Commits en español, conventional commits: `feat(evidencias): persistir metadatos de documentos de soporte`.
- Rama y PR contra `develop`.

## 10. Checklist de verificación de implementación

- [ ] Ruff/mypy OK; inyección con `Depends`
- [ ] Invariantes solo en `Evidencia.crear` y `dar_de_baja`
- [ ] Servicio sin SQLAlchemy ni FastAPI
- [ ] Router fino; `usuario_id` solo desde el token
- [ ] Esquema solo vía Alembic
- [ ] Tests verdes y cobertura ≥ 90 %
- [ ] `api-spec.yml` y `data-model.md` actualizados
