# Plan de implementación backend: SP-258 Publicar API del plan de mejora

## 1. Resumen

Publicar el CRUD del plan de mejora y de sus actividades de cronograma. Abrir el plan es `POST /api/v1/autoevaluaciones/{autoevaluacion_id}/plan-mejora` y llama a `PlanMejora.crear`. El cuerpo no manda `empresa_id`, `autoevaluacion_id` ni `requiere_plan_mejora`.

Las «acciones» de la historia son `actividades_cronograma`. No se crea `acciones_mejora`. No hay migración. No se recalcula el umbral de 85.

- **Stack activo**: `python-fastapi` (Python 3.12 + FastAPI).
- **Capas**: Domain (métodos y excepciones), Application (DTO, mapper, servicio), Infrastructure (repositorio), Presentation (router y dependencia).
- **Fuera de alcance**: estados del plan, `reportado_arl`, evidencias ligadas a una acción y pantallas.

**Precondición:** SP-257 ya está en la base (migración `a7b8c9d0e1f2`, `PlanMejora.crear` y las tres tablas). Si `develop` no la tiene, la rama sale de `feature/SP-257-backend`. `os-develop` parte de `develop` y se llevaría el modelo; en ese caso no se usa esa rama automática.

## Estimación de puntos de historia

<!-- STORY_POINTS:8 -->
- **HU total**: 8 (Fibonacci: 1, 2, 3, 5, 8, 13)
- **Justificación**: Confirma los 8 del enriquecimiento. Repositorio, servicio, siete rutas y pruebas de rol. El alta de dominio y el esquema ya existen.
- **Subtareas**: no hay subtareas en Jira.
<!-- /STORY_POINTS -->

## 2. Contexto de arquitectura

- Stack activo: `python-fastapi` (Python 3.12 + FastAPI)
- El servicio depende de puertos. No importa SQLAlchemy.
- `requerir_rol_escritor` ya deja fuera a `CONSULTA` con 403 `ACCESO_DENEGADO`. Los GET usan `obtener_usuario_actual`.
- El manejador global traduce `DomainException` a `RespuestaError` (`exito`, `codigo`, `mensaje`, `detalle`).

| Capa | Archivos |
|---|---|
| Dominio | `plan_mejora.py` y `exceptions/plan_mejora.py` (modificar), `repositorio_plan_mejora.py` (crear) |
| Application | `solicitud_plan_mejora.py`, `respuesta_plan_mejora.py`, `mapper_plan_mejora.py`, `servicio_planes_mejora.py` |
| Infrastructure | `repositorio_plan_mejora_sqlalchemy.py` |
| Presentation | `planes_mejora_router.py`, `dependencies/autoevaluacion.py`, `routers/__init__.py` |
| Docs | `ai-specs/specs/api-spec.yml` |
| Tests | `tests/unit/application/test_servicio_planes_mejora.py`, `tests/integration/test_planes_mejora.py` |

### Mapeo de subtareas

No hay subtareas: el plan sale directo de la tarea.

## 3. Pasos de implementación

### Paso 0: Crear la rama feature

- **Rama**: `feature/SP-258-backend`.
- Si `develop` contiene `alembic/versions/a7b8c9d0e1f2_crear_tablas_plan_mejora.py`:
  ```bash
  git checkout develop && git pull origin develop
  git checkout -b feature/SP-258-backend
  ```
- Si no la contiene, partir de `feature/SP-257-backend` y no de `develop`.

### Paso 1: Sin migración

No hay tablas ni columnas nuevas. `autoevaluacion_id` UNIQUE y el CASCADE de actividades y meses ya están.

### Paso 2: Completar el agregado

En `src/domain/models/plan_mejora.py`:

- `actualizar_actividad(actividad_id, descripcion, responsable, indicador, meses)` busca la actividad por id. Si no está, `ActividadNoEncontradaError`. Arma una nueva con `ActividadCronograma.crear` y conserva el mismo `id`.
- `quitar_actividad(actividad_id)` la saca de la lista. Si no está, `ActividadNoEncontradaError`.

En `src/domain/exceptions/plan_mejora.py`:

- `PlanMejoraYaExisteError` — `PLAN_MEJORA_YA_EXISTE` — 409.
- `PlanMejoraNoEncontradoError` — `PLAN_MEJORA_NO_ENCONTRADO` — 404.
- `ActividadNoEncontradaError` — `ACTIVIDAD_NO_ENCONTRADA` — 404.

No tocar `PlanMejora.crear` ni el umbral de 85.

### Paso 3: Puerto y repositorio

`RepositorioPlanMejora`:

- `guardar(plan) -> PlanMejora`
- `buscar_por_id(id) -> PlanMejora | None`
- `buscar_por_autoevaluacion(autoevaluacion_id) -> PlanMejora | None`
- `eliminar(id) -> None`

`RepositorioPlanMejoraSQLAlchemy` devuelve dominio, nunca el ORM. Carga actividades y meses con `selectinload`.

- Alta: si `plan.id` es `None`, asigna `uuid4` al plan y a cada actividad sin id. Inserta el plan, las actividades y los meses.
- Actualización: reemplaza la colección de actividades y sus meses con el estado del agregado, para que `delete-orphan` borre las que ya no están. Los id que el dominio conservó se mantienen.
- `IntegrityError` del UNIQUE `uq_planes_mejoramiento_autoevaluacion_id` se traduce a `PlanMejoraYaExisteError`.
- `eliminar` borra la fila del plan. El CASCADE de la base limpia actividades y meses. Si no existe, no hace nada: el servicio ya respondió 404.

### Paso 4: DTOs

`solicitud_plan_mejora.py`:

- `SolicitudActividadCronograma`: `descripcion: str`, `responsable: str`, `indicador: str`, `meses: list[int]`.
- `SolicitudAbrirPlanMejora`: `actividades: list[SolicitudActividadCronograma] = []`.
- Pydantic solo fija el tipo. No uses `min_length` ni rangos: la regla de negocio debe seguir siendo `ACTIVIDAD_CRONOGRAMA_INVALIDA`, no un 422 genérico de validación.

`respuesta_plan_mejora.py`:

- `RespuestaActividadCronograma`: `id`, `descripcion`, `responsable`, `indicador`, `meses: list[int]`.
- `RespuestaPlanMejora`: `id`, `empresa_id`, `autoevaluacion_id`, `actividades`.

El mapper exige `plan.id` y `actividad.id` no nulos. `meses` sale de la tupla, ya ordenada.

### Paso 5: Servicio

`ServicioPlanesMejora` recibe `RepositorioPlanMejora` y `RepositorioAutoevaluacion`.

- `abrir(autoevaluacion_id, solicitud)`:
  1. `buscar_por_id`. Si no está, `AutoevaluacionNoEncontradaError`.
  2. Si `buscar_por_autoevaluacion` devuelve un plan, `PlanMejoraYaExisteError` y no llama a `guardar`.
  3. `PlanMejora.crear(autoevaluacion)`.
  4. `agregar_actividad` por cada ítem del cuerpo.
  5. `guardar` y mapear.
- `obtener_por_autoevaluacion` y `obtener`: `None` → `PlanMejoraNoEncontradoError`.
- `agregar_actividad`: carga el plan, `agregar_actividad`, `guardar`, devuelve el plan.
- `actualizar_actividad`: carga el plan, `actualizar_actividad`, `guardar`.
- `quitar_actividad`: carga el plan, `quitar_actividad`, `guardar`.
- `eliminar`: 404 si no existe; si existe, `eliminar`.

### Paso 6: Router

Archivo `src/presentation/routers/planes_mejora_router.py`, dos `APIRouter` con tag `Planes de mejora`. Incluir ambos en `routers/__init__.py` con `settings.api_prefix`.

`router_por_autoevaluacion`, prefijo `/autoevaluaciones`:

- `POST /{autoevaluacion_id}/plan-mejora` — 201 — `requerir_rol_escritor`.
- `GET /{autoevaluacion_id}/plan-mejora` — 200 — `obtener_usuario_actual`.

`router`, prefijo `/planes-mejora`:

- `GET /{plan_id}` — 200 — `obtener_usuario_actual`.
- `DELETE /{plan_id}` — 204 — `requerir_rol_escritor`.
- `POST /{plan_id}/actividades` — 201 — `requerir_rol_escritor`. Devuelve el plan.
- `PUT /{plan_id}/actividades/{actividad_id}` — 200 — `requerir_rol_escritor`.
- `DELETE /{plan_id}/actividades/{actividad_id}` — 204 — `requerir_rol_escritor`.

No hay `PUT` del plan. Documentar `RespuestaError` en 401, 403, 404, 409 y 422. Proveer el servicio en `dependencies/autoevaluacion.py` con `obtener_sesion`, junto a `obtener_repositorio_autoevaluacion`.

### Paso 7: Errores

Reutilizar `AutoevaluacionNoEncontradaError`, `AutoevaluacionEnBorradorError`, `PlanMejoraNoRequeridoError` y `ActividadCronogramaInvalidaError`. Los tres códigos nuevos salen del paso 2. No añadir otro manejador.

### Paso 8: Pruebas

`tests/unit/application/test_servicio_planes_mejora.py` con repositorios falsos:

- Finalizada que requiere plan: guarda una vez, copia `empresa_id` y `autoevaluacion_id`, y deja las actividades.
- Cuerpo sin actividades: el plan se guarda vacío.
- `requiere_plan_mejora` false: `PlanMejoraNoRequeridoError` y `guardar` no se llama.
- Borrador: `AutoevaluacionEnBorradorError` y `guardar` no se llama.
- Autoevaluación ausente: `AutoevaluacionNoEncontradaError`.
- Ya existe plan: `PlanMejoraYaExisteError` y no hay segundo `guardar`.
- Mes 13 o texto vacío: `ActividadCronogramaInvalidaError`.
- Actualizar o quitar un id que no está: `ActividadNoEncontradaError`.
- Quitar una actividad la excluye de lo que se persiste.

`tests/integration/test_planes_mejora.py`, con el mismo armado de usuarios que el resto de integración:

- Escritor: 201 al abrir y 200 al leer por autoevaluación.
- Segundo POST: 409 `PLAN_MEJORA_YA_EXISTE`.
- `CONSULTA`: 200 en el GET y 403 `ACCESO_DENEGADO` en el POST.
- Sin token: 401.
- Autoevaluación finalizada en 85 o más: 409 `PLAN_MEJORA_NO_REQUERIDO`.

### Paso 9: Documentación

Añadir las siete rutas en `ai-specs/specs/api-spec.yml`. No cambiar `data-model.md`.

## 4. Orden de implementación

1. Paso 0 — rama con SP-257 debajo.
2. Paso 2 — métodos y excepciones.
3. Paso 3 — puerto y SQLAlchemy.
4. Paso 4 — DTOs y mapper.
5. Paso 5 — servicio.
6. Paso 8 — pruebas de servicio, en verde antes del router.
7. Paso 6 — router, dependencia y registro.
8. Paso 8 — integración.
9. Paso 9 — OpenAPI.
10. El paso 1 no produce archivos. El paso 7 queda cubierto por el paso 2.

## 5. Checklist de pruebas

- [ ] `pytest` termina con 0 fallos
- [ ] La cobertura global sigue en el umbral de `pyproject.toml` (`--cov-fail-under=90`)
- [ ] 201, 200, 204, 401, 403, 404 y 409 quedan cubiertos en integración
- [ ] Las pruebas de autoevaluación y de SP-257 siguen en verde

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

```json
{
  "exito": false,
  "codigo": "ERROR_CODE",
  "mensaje": "Descripción legible",
  "detalle": null
}
```

Códigos de esta historia: 409 `PLAN_MEJORA_NO_REQUERIDO`, 409 `AUTOEVALUACION_EN_BORRADOR`, 409 `PLAN_MEJORA_YA_EXISTE`, 404 `AUTOEVALUACION_NO_ENCONTRADA`, 404 `PLAN_MEJORA_NO_ENCONTRADO`, 404 `ACTIVIDAD_NO_ENCONTRADA`, 422 `ACTIVIDAD_CRONOGRAMA_INVALIDA`, 403 `ACCESO_DENEGADO`, 401 `TOKEN_INVALIDO`.

## 8. Dependencias

Ninguna. No se agregan librerías.

## 9. Notas

- El servicio consulta el plan existente antes de `guardar`. El UNIQUE sigue cubriendo dos altas a la vez.
- Una actividad actualizada conserva su id. Los meses se reemplazan, no se acumulan.
- `CONSULTA` lee. No poner `requerir_rol_escritor` en los GET.
- Commits en español, por ejemplo `feat(plan-mejora): publica el API del plan y el cronograma`.
- PR contra `develop`. Si la rama nació de `feature/SP-257-backend`, el PR debe esperar a que SP-257 esté en `develop`, o incluir ese historial a propósito.

## 10. Checklist de verificación de implementación

- [ ] `abrir` llama a `PlanMejora.crear` y no recalcula el 85
- [ ] El cuerpo no fija empresa ni autoevaluación
- [ ] No hay migración ni tabla `acciones_mejora`
- [ ] `CONSULTA` recibe 403 solo en escritura
- [ ] OpenAPI lista las siete rutas y `RespuestaError`
- [ ] `pytest` en verde y cobertura global ≥ 90 %
