# Plan de implementación backend: SP-260 Generar borrador de acciones desde incumplimientos

## 1. Resumen

Generar el borrador de acciones de un plan ya abierto. Por cada calificación `NO_CUMPLE` se crea una `AccionMejora` con el ítem, el `ciclo_phva` copiado del estándar y `responsable_sugerido` vacío. Un segundo llamado no duplica el mismo estándar.

La acción no es una fila de `actividades_cronograma`. No se agregan `origen`, `tipo`, `fecha_limite`, `estado` ni `responsable_id`. No se llama a un modelo de lenguaje. No se abre el plan ni se recalcula el umbral de 85. `evidencias.accion_mejora_id` no se crea.

- **Stack activo**: `python-fastapi` (Python 3.12 + FastAPI).
- **Capas**: Domain (entidad), Infrastructure (migración, ORM, repositorio), Application (servicio, DTO, mapper), Presentation (router y dependencia).
- **Fuera de alcance**: editar el responsable, cronograma, estados de la acción, pantallas y R2.

**Precondición:** SP-257 y SP-258 (tablas del plan y `planes_mejora_router.py`). SP-259 no hace falta. Si `develop` no tiene ese router, la rama sale de `feature/SP-258-backend`.

## Estimación de puntos de historia

<!-- STORY_POINTS:5 -->
- **HU total**: 5 (Fibonacci: 1, 2, 3, 5, 8, 13)
- **Justificación**: Confirma los 5 del enriquecimiento. Una tabla, un caso de uso idempotente y dos rutas. El plan, las calificaciones y el catálogo ya existen.
- **Subtareas**: no hay subtareas en Jira.
<!-- /STORY_POINTS -->

## 2. Contexto de arquitectura

- Stack activo: `python-fastapi` (Python 3.12 + FastAPI).
- `Autoevaluacion.buscar_por_id` ya trae `calificaciones` con `estandar_id` y `resultado`. `RepositorioEstandarMinimo.listar` trae `numeral`, `descripcion` y `ciclo_phva`.
- `PlanMejoraNoEncontradoError` (404) y `EstandarNoEncontradoError` (404) ya existen. No hace falta una excepción nueva.
- El POST usa `requerir_rol_escritor`. El GET usa `obtener_usuario_actual`.
- El manejador global traduce `DomainException` a `RespuestaError` (`exito`, `codigo`, `mensaje`, `detalle`).
- La acción no entra en `PlanMejora.guardar`. Un repositorio propio evita mezclar el sync del cronograma.

| Capa | Archivos |
|---|---|
| Dominio | `accion_mejora.py`, `repositorio_accion_mejora.py` |
| Infrastructure | migración, `accion_mejora_orm.py`, `repositorio_accion_mejora_sqlalchemy.py`, `modelos/__init__.py`, `alembic/env.py` |
| Application | `respuesta_accion_mejora.py`, `mapper_accion_mejora.py`, `servicio_borrador_acciones.py` |
| Presentation | `acciones_mejora_router.py`, `dependencies/autoevaluacion.py`, `routers/__init__.py` |
| Docs | `ai-specs/specs/data-model.md`, `ai-specs/specs/api-spec.yml` |
| Tests | `tests/unit/application/test_servicio_borrador_acciones.py`, `tests/integration/test_borrador_acciones.py` |

### Mapeo de subtareas

No hay subtareas: el plan sale directo de la tarea.

## 3. Pasos de implementación

### Paso 0: Crear la rama feature

- **Rama**: `feature/SP-260-backend`.
- Si `develop` contiene `src/presentation/routers/planes_mejora_router.py`:

```bash
git checkout develop && git pull origin develop
git checkout -b feature/SP-260-backend
```

- Si no lo contiene, crear la rama desde `feature/SP-258-backend` antes de `os-develop`.

### Paso 1: Migración

Revisión escrita a mano, no autogenerate. `down_revision` es el head vigente. Hoy es `a7b8c9d0e1f2`; confirmarlo con `alembic heads` antes de crear el archivo.

Tabla `acciones_mejora`:

- `id` UUID PK.
- `plan_mejoramiento_id` UUID NOT NULL, FK a `planes_mejoramiento.id`, índice. Sin ON DELETE CASCADE.
- `estandar_minimo_id` UUID NOT NULL, FK a `estandares_minimos.id`.
- `ciclo_phva` VARCHAR(20) NOT NULL.
- `responsable_sugerido` VARCHAR(150) NULL.
- UNIQUE `(plan_mejoramiento_id, estandar_minimo_id)` con nombre `uq_acciones_mejora_plan_estandar`.

`downgrade` quita el UNIQUE y la tabla. No tocar `evidencias` ni `actividades_cronograma`.

### Paso 2: Dominio

`AccionMejora` en `src/domain/models/accion_mejora.py`:

- Campos persistidos: `id`, `plan_id`, `estandar_id`, `ciclo_phva`, `responsable_sugerido`.
- `crear(plan_id, estandar)` copia `estandar.id` y `estandar.ciclo_phva`, y deja `responsable_sugerido` en `None`. No recibe el responsable por parámetro.

No agregar métodos de edición. Esta historia no completa el responsable.

### Paso 3: ORM y puerto

`AccionMejoraORM` en `accion_mejora_orm.py`. Exportarlo en `modelos/__init__.py` (orden alfabético, junto a `AccesoEvidenciaORM`) y en la lista de imports de `alembic/env.py`.

`RepositorioAccionMejora`:

- `listar_por_plan(plan_id) -> list[AccionMejora]`
- `guardar(accion) -> AccionMejora`

`guardar` inserta. Si `IntegrityError` menciona `uq_acciones_mejora_plan_estandar` o `estandar_minimo_id`, recarga la fila existente y la devuelve. No es un 409: la generación es idempotente. No actualiza `responsable_sugerido` ni `ciclo_phva` de una fila ya guardada.

### Paso 4: Servicio

`ServicioBorradorAcciones.generar(plan_id) -> list[RespuestaAccionMejora]` y `listar(plan_id)` con la misma forma de respuesta.

`generar`:

1. `buscar_por_id` del plan. Si no está, `PlanMejoraNoEncontradoError`.
2. `buscar_por_id` de `plan.autoevaluacion_id`. Si no está, `AutoevaluacionNoEncontradaError`.
3. `listar()` del catálogo, una vez, indexado por id.
4. Acciones ya guardadas, indexadas por `estandar_id`.
5. Por cada calificación con `resultado == NO_CUMPLE`: si el estándar ya tiene acción, seguir. Si el ítem no está en el catálogo, `EstandarNoEncontradoError`. Si no, `AccionMejora.crear` y `guardar`.
6. `CUMPLE` y `NO_APLICA` se ignoran. No se borran acciones viejas.

`listar` hace los pasos 1 y 4 y arma la respuesta. No guarda.

El orden de la lista es el numeral partido por `.` y comparado como enteros (`1.1.2` antes de `1.1.10`). Numeral y descripción salen del catálogo en el mapper, no de columnas de la acción.

### Paso 5: DTO, mapper y router

`RespuestaAccionMejora`: `id`, `plan_id`, `estandar_id`, `numeral`, `descripcion`, `ciclo_phva`, `responsable_sugerido` (`str | None`).

`MapperAccionMejora.a_respuesta(accion, estandar)`.

Router nuevo, prefijo `/planes-mejora`, tag `Planes de mejora`:

- `POST /{plan_id}/acciones/borrador` — 200, sin cuerpo, `requerir_rol_escritor`.
- `GET /{plan_id}/acciones` — 200, `obtener_usuario_actual`.

Registrar ambos con `settings.api_prefix` en `routers/__init__.py`, después de `planes_mejora_router`. La dependencia nueva vive en `dependencies/autoevaluacion.py` y reutiliza los proveedores que ya existen.

### Paso 6: Pruebas

`tests/unit/application/test_servicio_borrador_acciones.py`, con fakes de los cuatro puertos:

- `NO_CUMPLE`, `CUMPLE` y `NO_APLICA`: se guarda una acción, con el ciclo del estándar y responsable `None`.
- El estándar ya está en el fake: `guardar` no se llama otra vez.
- Plan ausente: `PlanMejoraNoEncontradoError`.
- Cero `NO_CUMPLE`: lista vacía y ningún `guardar`.
- Ítem fuera del catálogo: `EstandarNoEncontradoError`.

`tests/integration/test_borrador_acciones.py`, reutilizando el armado de `test_planes_mejora.py` (autoevaluación finalizada que exige plan, NIT nuevo):

- Escritor: 200, una acción por el ítem `NO_CUMPLE`, meses no aplican, `responsable_sugerido` null, `ciclo_phva` el del estándar.
- Segundo POST: la misma cantidad de ids.
- Un ítem `NO_APLICA` no aparece.
- `CONSULTA`: 200 en el GET y 403 `ACCESO_DENEGADO` en el POST.
- Sin token: 401.
- Plan desconocido: 404 `PLAN_MEJORA_NO_ENCONTRADO`.

### Paso 7: Documentación

En `data-model.md`, reemplazar el pendiente de `acciones_mejora` por las columnas de esta historia. Dejar escrito que `origen`, `tipo`, `fecha_limite`, `estado`, `responsable_id` y `evidencias.accion_mejora_id` siguen fuera.

En `api-spec.yml`, las dos rutas y `RespuestaAccionMejora`. Sin `minimum` ni campos de cronograma.

## 4. Orden de implementación

1. Paso 0 — rama con el plan de SP-258 debajo.
2. Paso 1 — migración.
3. Paso 2 — entidad.
4. Paso 3 — ORM, puerto y repositorio.
5. Paso 4 — servicio, con las pruebas de unidad en verde antes del router.
6. Paso 5 — DTO, mapper, router y registro.
7. Paso 6 — integración.
8. Paso 7 — `data-model.md` y OpenAPI.

## 5. Checklist de pruebas

- [ ] `pytest` termina con 0 fallos
- [ ] La cobertura global sigue en el umbral de `pyproject.toml` (`--cov-fail-under=90`)
- [ ] El segundo POST no aumenta las acciones del mismo estándar
- [ ] `CUMPLE` y `NO_APLICA` no aparecen en el borrador
- [ ] `CONSULTA` recibe 403 solo en el POST
- [ ] Las pruebas del plan y del cronograma siguen en verde

## 6. Referencia de herramientas

| Uso | Comando |
|---|---|
| Build | `pip install -r requirements.txt` |
| Test | `pytest` |
| Run | `uvicorn main:app --reload` |
| Coverage | `pytest --cov --cov-report=html` |
| Lint | `ruff check .` |

En local, el intérprete del proyecto es `.\.venv\Scripts\python.exe`. Para un subconjunto, `pytest -o addopts=` evita que el umbral global falle antes de tiempo. El cierre es la suite completa. La migración se aplica con `poetry run alembic upgrade head` solo cuando se quiera probar contra la base local.

## 7. Formato de error

```json
{
  "exito": false,
  "codigo": "ERROR_CODE",
  "mensaje": "Descripción legible",
  "detalle": null
}
```

Códigos de esta historia: 404 `PLAN_MEJORA_NO_ENCONTRADO`, 404 `AUTOEVALUACION_NO_ENCONTRADA`, 404 `ESTANDAR_NO_ENCONTRADO`, 403 `ACCESO_DENEGADO`, 401 `TOKEN_INVALIDO`.

## 8. Dependencias

Ninguna. No se agregan librerías.

## 9. Notas

- Regenerar no actualiza ni borra. El UNIQUE es la red ante dos POST simultáneos.
- `responsable_sugerido` nace en `None`. No hay `PUT` en esta historia.
- `CONSULTA` lee. No poner `requerir_rol_escritor` en el GET.
- Commits en español, por ejemplo `feat(acciones): genera el borrador desde los incumplimientos`.
- PR contra `develop`. Si la rama nació de `feature/SP-258-backend`, el PR espera a que ese plan esté en `develop`, o incluye ese historial a propósito.

## 10. Checklist de verificación de implementación

- [ ] No se crean filas de cronograma ni se llama a un modelo de lenguaje
- [ ] `CUMPLE` y `NO_APLICA` no generan acción
- [ ] El segundo `generar` conserva la acción y su responsable
- [ ] La migración no altera `evidencias`
- [ ] OpenAPI lista el POST y el GET
- [ ] `pytest` en verde y cobertura global ≥ 90 %
