# Plan de implementación backend: SP-259 Publicar API del cronograma anual

## 1. Resumen

Cerrar el contrato del cronograma anual sobre las rutas que SP-258 ya publica. Una actividad sigue siendo `descripcion`, `responsable`, `indicador` y `meses`. El alta, la edición y la baja no se reescriben.

El hueco es el orden de la respuesta. La relación ORM de `actividades` no tiene `order_by`, así que dos GET del mismo plan pueden no coincidir. Los meses ya salen ordenados en `_a_dominio` con `sorted`; la relación de `meses` tampoco declara orden.

- **Stack activo**: `python-fastapi` (Python 3.12 + FastAPI).
- **Capas**: Infrastructure (orden en el ORM y al mapear) y pruebas. Presentation y dominio se tocan solo si una prueba demuestra que el orden se pierde al recargar.
- **Fuera de alcance**: rutas nuevas, migración, `acciones_mejora`, `estado`, `reportado_arl`, pantallas y el umbral de 85.

**Precondición:** SP-257 (tablas y `ActividadCronograma.crear`) y SP-258 (router, servicio y repositorio). Si `develop` no tiene `src/presentation/routers/planes_mejora_router.py`, la rama sale de `feature/SP-258-backend`.

## Estimación de puntos de historia

<!-- STORY_POINTS:3 -->
- **HU total**: 3 (Fibonacci: 1, 2, 3, 5, 8, 13)
- **Justificación**: Confirma los 3 del enriquecimiento. El CRUD y el 422 de meses ya existen. El trabajo es el `order_by`, el orden al mapear tras el flush y las pruebas de orden, de baja y de mes fuera de rango.
- **Subtareas**: no hay subtareas en Jira.
<!-- /STORY_POINTS -->

## 2. Contexto de arquitectura

- Stack activo: `python-fastapi` (Python 3.12 + FastAPI).
- `POST`, `PUT` y `DELETE` de actividades ya usan `requerir_rol_escritor`. Los GET usan `obtener_usuario_actual`.
- `guardar` hace flush y vuelve a cargar la fila. En la misma sesión, SQLAlchemy puede devolver la colección en el orden de los `append`, sin aplicar el `order_by`. El orden tiene que quedar fijado al mapear a dominio, con `fecha_creacion` ya leída de la base.
- El manejador global traduce `ActividadCronogramaInvalidaError` a 422 `ACTIVIDAD_CRONOGRAMA_INVALIDA`. Pydantic no debe poner `ge`, `le` ni `min_length` en `meses`.

| Capa | Archivos |
|---|---|
| Infrastructure | `plan_mejoramiento_orm.py`, `actividad_cronograma_orm.py`, `repositorio_plan_mejora_sqlalchemy.py` |
| Docs | `ai-specs/specs/api-spec.yml` (solo la descripción del orden) |
| Tests | `tests/integration/test_planes_mejora.py` |

### Mapeo de subtareas

No hay subtareas: el plan sale directo de la tarea.

## 3. Pasos de implementación

### Paso 0: Crear la rama feature

- **Rama**: `feature/SP-259-backend`.
- Si `develop` contiene `src/presentation/routers/planes_mejora_router.py`:

```bash
git checkout develop && git pull origin develop
git checkout -b feature/SP-259-backend
```

- Si no lo contiene, crear la rama desde `feature/SP-258-backend` antes de `os-develop`. Ese comando parte de `develop` cuando la rama no existe.

### Paso 1: Sin migración

No hay tablas ni columnas. `fecha_creacion` de `actividades_cronograma` ya existe y el `PUT` no la pisa: `_sincronizar_actividades` solo asigna descripción, responsable e indicador. No añadir `orden` ni tocar `fecha_creacion`.

### Paso 2: Orden en las relaciones

En `PlanMejoramientoORM.actividades`, agregar `order_by` por `ActividadCronogramaORM.fecha_creacion` y `ActividadCronogramaORM.id`. Usar la forma de cadena para no crear un import circular.

En `ActividadCronogramaORM.meses`, agregar `order_by` por `MesActividadORM.mes`.

El dominio no gana campos. `ActividadCronograma` sigue sin `fecha_creacion`.

### Paso 3: Orden al mapear

En `RepositorioPlanMejoraSQLAlchemy.guardar`, después del `flush`, expirar la colección `actividades` antes del segundo `_cargar`. Así el `selectinload` vuelve a leer y `fecha_creacion` llega desde la base, incluido el `server_default`.

En `_a_dominio`, ordenar las filas por `(fecha_creacion, id)` y seguir armando `meses` con `tuple(sorted(...))`. Ese orden es el que ven el POST, el PUT y el GET, aunque la colección en memoria haya quedado en orden de `append`.

`quitar_actividad` y `actualizar_actividad` no cambian de firma. El `PUT` conserva el id y, al no tocar `fecha_creacion`, conserva la posición.

### Paso 4: Los DTO y el router se quedan

`SolicitudActividadCronograma` sigue con `extra="forbid"` y sin rangos de Pydantic. Las tres rutas se mantienen:

- `POST /api/v1/planes-mejora/{plan_id}/actividades` — 201, plan completo.
- `PUT /api/v1/planes-mejora/{plan_id}/actividades/{actividad_id}` — 200, mismo id.
- `DELETE /api/v1/planes-mejora/{plan_id}/actividades/{actividad_id}` — 204. El plan sigue.

### Paso 5: Pruebas

`tests/unit/domain/test_plan_mejora.py` ya cubre meses `[12, 1]`, mes fuera de 1–12, lista vacía y mes repetido. No duplicar esos casos.

Ampliar `tests/integration/test_planes_mejora.py`:

- Abrir un plan y crear dos actividades en dos POST. Dos `GET /api/v1/planes-mejora/{plan_id}` devuelven la misma lista de ids.
- El `PUT` de la primera no mueve su posición: la secuencia de ids queda igual.
- Enviar `meses: [12, 1]` devuelve `[1, 12]`.
- `meses: [13]` responde 422 `ACTIVIDAD_CRONOGRAMA_INVALIDA` y el GET sigue sin esa actividad.
- `DELETE` de una actividad responde 204. El GET siguiente responde 200, sin ese id y con la otra actividad. No borrar el plan en ese caso.
- `CONSULTA` recibe 200 en el GET y 403 `ACCESO_DENEGADO` en POST, PUT y DELETE de actividades.

El criterio de orden es la igualdad entre lecturas. Si las dos filas comparten `fecha_creacion` (el `now()` de una sola transacción), el desempate es el `id`. No afirmar que el orden coincida con el de creación cuando el timestamp empata.

### Paso 6: Documentación

En `ai-specs/specs/api-spec.yml`, describir que `actividades` viaja ordenada por fecha de creación e id, y que `meses` de la respuesta viaja en orden ascendente. No agregar `minimum`, `maximum` ni `minItems`: el 422 lo sigue emitiendo el dominio. No cambiar `data-model.md`.

## 4. Orden de implementación

1. Paso 0 — rama con SP-258 debajo.
2. Paso 2 — `order_by` en las dos relaciones.
3. Paso 3 — expirar la colección y ordenar en `_a_dominio`.
4. Paso 5 — integración de orden, baja y mes 13.
5. Paso 6 — descripción en OpenAPI.
6. Los pasos 1 y 4 no producen archivos.

## 5. Checklist de pruebas

- [ ] `pytest` termina con 0 fallos
- [ ] La cobertura global sigue en el umbral de `pyproject.toml` (`--cov-fail-under=90`)
- [ ] Dos GET del mismo plan repiten el orden de actividades y los meses salen ascendente
- [ ] Borrar una actividad deja el plan en 200
- [ ] Mes 13 responde 422 y `CONSULTA` recibe 403 al escribir una actividad
- [ ] Las pruebas de SP-257 y SP-258 siguen en verde

## 6. Referencia de herramientas

| Uso | Comando |
|---|---|
| Build | `pip install -r requirements.txt` |
| Test | `pytest` |
| Run | `uvicorn main:app --reload` |
| Coverage | `pytest --cov --cov-report=html` |
| Lint | `ruff check .` |

En local, el intérprete del proyecto es `.\.venv\Scripts\python.exe`. Para un subconjunto, `pytest -o addopts=` evita que el umbral global falle antes de tiempo. El cierre es la suite completa.

## 7. Formato de error

```json
{
  "exito": false,
  "codigo": "ERROR_CODE",
  "mensaje": "Descripción legible",
  "detalle": null
}
```

Códigos que esta historia debe seguir viendo: 422 `ACTIVIDAD_CRONOGRAMA_INVALIDA`, 404 `PLAN_MEJORA_NO_ENCONTRADO`, 404 `ACTIVIDAD_NO_ENCONTRADA`, 403 `ACCESO_DENEGADO`, 401 `TOKEN_INVALIDO`.

## 8. Dependencias

Ninguna. No se agregan librerías.

## 9. Notas

- El orden estable es `(fecha_creacion, id)` para actividades y el número de mes para `meses`. No hace falta una columna `orden`.
- Un `PUT` que cambiara `fecha_creacion` movería la actividad. `_sincronizar_actividades` no debe asignarla.
- `CONSULTA` lee. No poner `requerir_rol_escritor` en el GET.
- Commits en español, por ejemplo `fix(cronograma): fija el orden estable de las actividades`.
- PR contra `develop`. Si la rama nació de `feature/SP-258-backend`, el PR espera a que SP-258 esté en `develop`, o incluye ese historial a propósito.

## 10. Checklist de verificación de implementación

- [ ] No hay rutas nuevas ni migración
- [ ] Las relaciones declaran `order_by` y `_a_dominio` ordena aunque la sesión haya hecho `append`
- [ ] `fecha_creacion` se lee de la base antes de ordenar
- [ ] El `DELETE` de una actividad no borra el plan
- [ ] Un mes fuera de 1–12 sigue en 422 `ACTIVIDAD_CRONOGRAMA_INVALIDA`
- [ ] OpenAPI describe el orden y no le quita el 422 al dominio
- [ ] `pytest` en verde y cobertura global ≥ 90 %
