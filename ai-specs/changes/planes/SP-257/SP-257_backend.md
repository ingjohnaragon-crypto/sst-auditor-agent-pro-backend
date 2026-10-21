# Plan de implementación backend: SP-257 Modelar plan de mejora y actividades del cronograma

## 1. Resumen

Persistir el plan de mejora que nace de una autoevaluación ya finalizada y las actividades de su cronograma. La regla de alta vive en el dominio. La base garantiza el vínculo y que una autoevaluación tenga como máximo un plan.

No hay endpoint, DTO, servicio ni repositorio. No se recalcula `requiere_plan_mejora`. No se crea `acciones_mejora` ni se agrega `evidencias.accion_mejora_id`.

- **Stack activo**: `python-fastapi` (Python 3.12 + FastAPI).
- **Capas**: Domain e Infrastructure (ORM + Alembic). Application y Presentation no cambian.
- **Fuera de alcance**: alta HTTP del plan, estados `ABIERTO | EN_EJECUCION | CERRADO`, `reportado_arl`, acciones de mejora y pantallas.

## Estimación de puntos de historia

<!-- STORY_POINTS:5 -->
- **HU total**: 5 (Fibonacci: 1, 2, 3, 5, 8, 13)
- **Justificación**: Confirma los 5 del enriquecimiento. Tres tablas, invariantes del agregado y pruebas de dominio. Sin contrato HTTP.
- **Subtareas**: no hay subtareas en Jira.
<!-- /STORY_POINTS -->

## 2. Contexto de arquitectura

- Stack activo: `python-fastapi` (Python 3.12 + FastAPI)
- Una autoevaluación está finalizada cuando `puntaje_total` no es null (`Autoevaluacion.esta_finalizada`). Ese flag y el umbral de 85 ya quedaron fijados en `finalizar`.
- El modelo de datos dejaba `planes_mejoramiento.autoevaluacion_id` nullable y la relación en 1—N. Esta historia lo deja NOT NULL y UNIQUE (0..1).
- `responsable` es texto. No es FK a `usuarios`.

| Capa | Archivos |
|---|---|
| Dominio | `src/domain/models/plan_mejora.py` (crear), `src/domain/exceptions/plan_mejora.py` (crear) |
| Application | Sin cambios |
| Presentation | Sin cambios |
| Infrastructure | Tres ORM nuevos, `modelos/__init__.py`, `alembic/env.py`, migración nueva |
| Docs | `ai-specs/specs/data-model.md` |
| Tests | `tests/unit/domain/test_plan_mejora.py` |

### Mapeo de subtareas

No hay subtareas: el plan sale directo de la tarea.

## 3. Pasos de implementación

### Paso 0: Crear la rama feature

- **Rama**: `feature/SP-257-backend` desde `develop`.
- **Comandos**:
  ```bash
  git checkout develop && git pull origin develop
  git checkout -b feature/SP-257-backend
  ```

### Paso 1: Migración Alembic

Archivo nuevo a mano, al estilo de `c3d4e5f6a7b8_crear_tablas_autoevaluacion.py`. No usar autogenerate.

- `down_revision`: `f6a7b8c9d0e1` (head actual, accesos de evidencia).
- `upgrade` crea, en este orden: `planes_mejoramiento`, `actividades_cronograma`, `meses_actividad`.
- `downgrade` las elimina en orden inverso.

`planes_mejoramiento`:

- `id` UUID PK.
- `empresa_id` UUID NOT NULL, FK → `empresas.id`, índice `ix_planes_mejoramiento_empresa_id`. Sin `ON DELETE`, igual que `autoevaluaciones`.
- `autoevaluacion_id` UUID NOT NULL, FK → `autoevaluaciones.id`, `UniqueConstraint` `uq_planes_mejoramiento_autoevaluacion_id`.
- `fecha_creacion` y `fecha_actualizacion` `DateTime(timezone=True)` NOT NULL, `server_default=now()`.

`actividades_cronograma`:

- `id` UUID PK.
- `plan_mejoramiento_id` UUID NOT NULL, FK → `planes_mejoramiento.id` con `ondelete="CASCADE"`, índice `ix_actividades_cronograma_plan_id`.
- `descripcion` TEXT NOT NULL.
- `responsable` VARCHAR(150) NOT NULL.
- `indicador` VARCHAR(200) NOT NULL.
- `fecha_creacion` y `fecha_actualizacion` TIMESTAMPTZ NOT NULL, `server_default=now()`.

`meses_actividad`:

- `actividad_id` UUID NOT NULL, FK → `actividades_cronograma.id` con `ondelete="CASCADE"`.
- `mes` SMALLINT NOT NULL.
- PK compuesta (`actividad_id`, `mes`). No agregar otro UNIQUE.
- `CheckConstraint` `mes >= 1 AND mes <= 12`, nombre `ck_meses_actividad_mes`.

No crear columnas `estado` ni `reportado_arl`. No crear `acciones_mejora`.

Registrar los tres ORM en `src/infrastructure/database/modelos/__init__.py` (`__all__` incluido). Añadirlos también al import de `alembic/env.py`. El `conftest` de integración importa el paquete; con el `__init__.py` actualizado, `create_all` de esas pruebas ve las tablas nuevas.

### Paso 2: Agregado de dominio

Archivo: `src/domain/models/plan_mejora.py`.

`ActividadCronograma`:

- Campos: `id: UUID | None`, `descripcion`, `responsable`, `indicador`, `meses: tuple[int, ...]`.
- `crear(descripcion, responsable, indicador, meses)`:
  - Recorta espacios. Descripción, responsable e indicador vacíos lanzan `ActividadCronogramaInvalidaError`.
  - Responsable de más de 150 caracteres, o indicador de más de 200, lanzan el mismo error.
  - `meses` tiene al menos un valor. Cada uno es entero entre 1 y 12. Un repetido lanza el mismo error.
  - Se guarda una tupla ordenada, sin duplicados. `id` queda en `None`.

`PlanMejora`:

- Campos: `id: UUID | None`, `empresa_id`, `autoevaluacion_id`, `actividades: list[ActividadCronograma]`, `fecha_creacion`, `fecha_actualizacion` (UTC, como `Autoevaluacion`).
- `crear(autoevaluacion: Autoevaluacion)`:
  - Si `autoevaluacion.id` es `None`, `AutoevaluacionSinPersistirError`.
  - Si no `esta_finalizada`, `AutoevaluacionEnBorradorError`.
  - Si `requiere_plan_mejora` es false, `PlanMejoraNoRequeridoError`.
  - Copia `empresa_id` y `autoevaluacion_id`. La lista de actividades nace vacía. `id` del plan queda en `None`.
- `agregar_actividad(...)` delega en `ActividadCronograma.crear` y la agrega a la lista.

No leer ni escribir `puntaje_total` para decidir el plan. No llamar a `finalizar`.

### Paso 3: Sin repositorio

No hay puerto ni implementación SQLAlchemy. El mapeo fila ↔ agregado queda para el ticket que exponga el alta.

### Paso 4: Sin DTO

No hay cuerpo de entrada ni respuesta.

### Paso 5: Sin servicio

La fábrica `PlanMejora.crear` es la regla de negocio. Un caso de uso posterior debe usarla y no repetir el `if`.

### Paso 6: Sin router

No se registra ruta. `api-spec.yml` no cambia.

### Paso 7: Excepciones

Archivo: `src/domain/exceptions/plan_mejora.py`, subclases de `DomainException`.

- `AutoevaluacionEnBorradorError` — `AUTOEVALUACION_EN_BORRADOR` — 409. No reutilizar `AutoevaluacionFinalizadaError`: esa bloquea cambios sobre una evaluación ya cerrada.
- `PlanMejoraNoRequeridoError` — `PLAN_MEJORA_NO_REQUERIDO` — 409.
- `AutoevaluacionSinPersistirError` — `AUTOEVALUACION_SIN_PERSISTIR` — 409.
- `ActividadCronogramaInvalidaError` — `ACTIVIDAD_CRONOGRAMA_INVALIDA` — 422.

El manejador global ya traduce `DomainException` a `RespuestaError`. Este ticket no añade un manejador.

### Paso 8: Pruebas

Archivo: `tests/unit/domain/test_plan_mejora.py`.

Ayuda local: armar la autoevaluación con `Autoevaluacion.crear`, calificar y `finalizar(total_requerido=1)`. Puntaje `84.99` deja `requiere_plan_mejora` true; `85.00` lo deja false. Asignar `id = uuid4()` solo cuando el caso exige una fila persistida. El borrador no llama a `finalizar`.

Casos:

- Finalizada, con id y `requiere_plan_mejora` true: el plan copia `empresa_id` y `autoevaluacion_id`, y nace sin actividades.
- Borrador con id: `AutoevaluacionEnBorradorError`.
- Finalizada con id y `requiere_plan_mejora` false: `PlanMejoraNoRequeridoError`.
- Finalizada que requiere plan pero `id` es null: `AutoevaluacionSinPersistirError`.
- `agregar_actividad` con meses `12` y `1` guarda la tupla `(1, 12)`.
- Mes `0`, mes `13` y mes repetido lanzan `ActividadCronogramaInvalidaError`.
- Descripción, responsable o indicador vacíos o solo espacios lanzan el mismo error.
- Responsable de 151 caracteres, o indicador de 201, lanzan el mismo error.

No hay prueba HTTP. No hace falta cubrir el rechazo del segundo plan en base: el UNIQUE queda en la migración y no hay repositorio que lo provoque.

### Paso 9: Documentación

En `ai-specs/specs/data-model.md`:

- Sustituir el bloque de `planes_mejoramiento` por las columnas de esta migración. `autoevaluacion_id` NOT NULL y UNIQUE.
- Documentar `actividades_cronograma` y `meses_actividad`.
- En relaciones, `autoevaluaciones` → `planes_mejoramiento` pasa a 1—0..1. `planes_mejoramiento` → `actividades_cronograma` es 1—N. `actividades_cronograma` → `meses_actividad` es 1—N.
- Dejar `acciones_mejora` como está, marcada pendiente. No inventar el cruce con evidencias.
- Anotar que `estado` y `reportado_arl` no entran en SP-257.

## 4. Orden de implementación

1. Paso 0 — rama `feature/SP-257-backend`.
2. Paso 7 — excepciones.
3. Paso 2 — agregado.
4. Paso 8 — pruebas de dominio, en verde antes de la migración.
5. Paso 1 — migración y registro de los ORM.
6. Paso 9 — `data-model.md`.
7. Los pasos 3, 4, 5 y 6 no producen archivos.

## 5. Checklist de pruebas

- [ ] `pytest` termina con 0 fallos
- [ ] La cobertura global sigue en el umbral de `pyproject.toml` (`--cov-fail-under=90`)
- [ ] No hay prueba de endpoint: este ticket no abre una ruta
- [ ] Las pruebas actuales de autoevaluación siguen en verde

## 6. Referencia de herramientas

| Uso | Comando |
|---|---|
| Build | `pip install -r requirements.txt` |
| Test | `pytest` |
| Run | `uvicorn main:app --reload` |
| Coverage | `pytest --cov --cov-report=html` |
| Lint | `ruff check .` |

En local, el intérprete del proyecto es `.\.venv\Scripts\python.exe`.

## 7. Formato de error

No hay respuesta HTTP nueva. Cuando un ticket posterior exponga el alta, el manejador actual debe seguir este cuerpo:

```json
{
  "success": false,
  "code": "ERROR_CODE",
  "message": "Descripción legible",
  "details": []
}
```

Códigos de este agregado: 409 `AUTOEVALUACION_EN_BORRADOR`, 409 `PLAN_MEJORA_NO_REQUERIDO`, 409 `AUTOEVALUACION_SIN_PERSISTIR`, 422 `ACTIVIDAD_CRONOGRAMA_INVALIDA`.

## 8. Dependencias

Ninguna. No se agregan librerías.

## 9. Notas

- El UNIQUE no reemplaza el rechazo de borrador ni el de `requiere_plan_mejora` false. Esas reglas cruzan tablas y viven en `PlanMejora.crear`.
- Una empresa puede tener varios planes, uno por cada autoevaluación que lo requiera.
- Los meses son un conjunto del 1 al 12, no un solo mes ni doce columnas booleanas.
- El esquema de producción entra solo por Alembic. `Base.metadata.create_all()` sigue reservado a pruebas.
- Commits en español, por ejemplo `feat(plan-mejora): modela el plan y el cronograma`.
- PR contra `develop`.

## 10. Checklist de verificación de implementación

- [ ] `PlanMejora.crear` no recalcula el umbral de 85
- [ ] No hay router, DTO, servicio ni repositorio nuevos
- [ ] La migración revisa `f6a7b8c9d0e1` y el `downgrade` elimina las tres tablas
- [ ] Los ORM están exportados en `modelos/__init__.py` y en `alembic/env.py`
- [ ] `data-model.md` muestra `autoevaluacion_id` obligatorio y único
- [ ] `pytest` en verde y cobertura global ≥ 90 %
