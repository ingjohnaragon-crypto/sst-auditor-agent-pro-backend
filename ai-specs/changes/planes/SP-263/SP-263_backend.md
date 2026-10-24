# Plan de implementación backend: SP-263 Probar el API del plan de mejora

## 1. Resumen

Completar la suite HTTP del plan de mejora. No hay endpoint ni regla nueva. Los casos que ya pasan se dejan quietos. Se agregan el `422` de meses inválidos al agregar o actualizar una actividad, y el `403` de `CONSULTA` al escribir o borrar el cronograma y el plan.

No se reescriben `tests/integration/test_borrador_acciones.py`, `tests/unit/domain/test_plan_mejora.py` ni las pruebas del motor PHVA y de finalización.

Stack activo: `python-fastapi` (Python 3.12 + FastAPI).

## Estimación de puntos de historia

<!-- STORY_POINTS:3 -->
- **HU total**: 3 (Fibonacci: 1, 2, 3, 5, 8, 13)
- **Justificación**: Confirma los 3 de Jira y del enriquecimiento. El alta, el `409` cuando no aplica plan y el borrador desde `NO_CUMPLE` ya existen. El trabajo es un archivo de integración y tres casos.
- **Subtareas**: ninguna. SP-263 es la tarea.
<!-- /STORY_POINTS -->

## 2. Contexto de arquitectura

- Stack activo: `python-fastapi` (Python 3.12 + FastAPI)
- Capas: ninguna de producción. El cambio vive en pruebas de presentación contra la app ya montada.
- `ActividadCronograma.crear` ya rechaza meses vacíos, fuera de 1 a 12 o repetidos con `ActividadCronogramaInvalidaError` (`422`, `ACTIVIDAD_CRONOGRAMA_INVALIDA`).
- `requerir_rol_escritor` ya niega `CONSULTA` con `403` `ACCESO_DENEGADO`.
- El cuerpo de error es `RespuestaError`: `exito`, `codigo`, `mensaje`, `detalle`.

Archivo a modificar:

- `tests/integration/test_planes_mejora.py`

Sin cambios:

- Dominio, aplicación, routers, ORM, migraciones
- `ai-specs/specs/api-spec.yml`
- `ai-specs/specs/data-model.md`
- `tests/integration/test_borrador_acciones.py`
- Pruebas de cumplimiento PHVA y de `finalizar`

### Mapeo de subtareas

No hay subtareas: el plan sale directamente de la tarea.

## 3. Pasos de implementación

### Paso 0: Crear la rama

- **Acción**: partir de `develop`.
- **Rama**: `feature/SP-263-backend`

```bash
git checkout develop
git pull origin develop
git checkout -b feature/SP-263-backend
```

### Paso 1: Migración

No hay migración.

### Paso 2: Dominio

No se toca `src/domain/models/plan_mejora.py`. `_meses_validos` ya exige al menos un entero entre 1 y 12, sin repetir, y ordena el resultado.

### Paso 3: Repositorio

Sin cambios.

### Paso 4: DTOs

Sin cambios. `SolicitudActividadCronograma` sigue con `descripcion`, `responsable`, `indicador` y `meses`.

### Paso 5: Servicio

Sin cambios. `agregar_actividad` y `actualizar_actividad` delegan en el dominio. Un mes inválido no persiste.

### Paso 6: Router

Sin cambios. Los caminos que ejercen las pruebas nuevas:

- `POST /api/v1/planes-mejora/{plan_id}/actividades` — escritor, `201` o `422`
- `PUT /api/v1/planes-mejora/{plan_id}/actividades/{actividad_id}` — escritor, `200` o `422`
- `DELETE` de esa actividad y `DELETE /api/v1/planes-mejora/{plan_id}` — escritor, `204` o `403`
- `GET /api/v1/autoevaluaciones/{autoevaluacion_id}/plan-mejora` — autenticado, `200`

### Paso 7: Excepciones

Sin clases nuevas. Códigos que deben aparecer en el cuerpo:

- `422` `ACTIVIDAD_CRONOGRAMA_INVALIDA`
- `403` `ACCESO_DENEGADO`

### Paso 8: Pruebas HTTP

Solo `tests/integration/test_planes_mejora.py`. Reutilizar `_autoevaluacion_finalizada`, `_error`, `obtener_token` y `bearer`. El usuario de consulta es `usuarios_semilla.correo_consulta`.

No reescribir los seis tests que ya existen.

Casos nuevos:

- Abrir un plan vacío con `exige_plan=True`. Cuatro `POST` de actividad, con el mismo texto válido y `meses` `[0]`, `[13]`, `[]` y `[1, 1]`. Cada uno responde `422` y `_error` comprueba `ACTIVIDAD_CRONOGRAMA_INVALIDA`. El `GET` del plan sigue con `actividades` vacías.
- Agregar una actividad con `meses: [3]`. El `PUT` con `meses: [13]` responde `422` y el mismo código. El `GET` conserva `meses: [3]` y el mismo id.
- Un escritor abre el plan y agrega una actividad. `CONSULTA` hace `GET` y recibe `200`. Con ese token, el `POST` de otra actividad, el `PUT`, el `DELETE` de la actividad y el `DELETE` del plan responden `403` `ACCESO_DENEGADO`. Un `GET` final sigue devolviendo la actividad original.

El cuerpo inválido lleva descripción, responsable e indicador válidos. Así el `422` sale del dominio y no de un campo ausente.

No agregar otra prueba de `POST /planes-mejora/{plan_id}/acciones/borrador` ni del umbral de 85.

### Paso 9: Documentación

No se actualiza `api-spec.yml` ni `data-model.md`.

## 4. Orden de implementación

1. Paso 0 — rama `feature/SP-263-backend` desde `develop`
2. Paso 8 — los tres casos en `test_planes_mejora.py`
3. `pytest` y la cobertura

Los pasos 1 a 7 y el 9 no producen archivos.

## 5. Lista de verificación de pruebas

- [x] `pytest` termina con 0 fallos
- [x] La cobertura global sigue en 90 % o más
- [x] Meses `0`, `13`, `[]` y `[1, 1]` no crean ni cambian actividades
- [x] `CONSULTA` no puede escribir el cronograma ni borrar el plan, y sí puede leerlo
- [x] La suite del borrador y la del motor PHVA siguen igual

## 6. Referencia de herramientas

| Propósito | Comando |
|---|---|
| Build | `pip install -r requirements.txt` |
| Test | `pytest` |
| Run | `uvicorn src.main:app --reload` |
| Coverage | `pytest --cov --cov-report=html` |

En este repo el intérprete de desarrollo es `.\.venv\Scripts\python.exe` y `pytest` ya aplica el umbral de cobertura.

## 7. Formato de respuesta de error

```json
{
  "exito": false,
  "codigo": "ACTIVIDAD_CRONOGRAMA_INVALIDA",
  "mensaje": "El mes debe estar entre 1 y 12",
  "detalle": null
}
```

`CONSULTA` en una ruta de escritor responde `403` con `codigo` `ACCESO_DENEGADO`. No hay códigos nuevos.

## 8. Dependencias

Ninguna.

## 9. Notas

- Rama `feature/SP-263-backend`. Nunca `-frontend` en este repo.
- La base es `develop`, no `main`.
- Un `bool` también es `int` en Python y el dominio lo rechaza. Esta historia no pide ese caso.
- Los meses válidos se guardan ordenados. `[12, 1]` ya se afirma en el test de alta existente.
- No bajar el umbral de cobertura para dejar pasar la suite.

## 10. Lista de verificación de la implementación

- [x] No hay diff en `src/`
- [x] `tests/integration/test_planes_mejora.py` cubre el `422` de meses y el `403` de `CONSULTA` en el cronograma
- [x] `pytest` en verde y cobertura global ≥ 90 %
- [x] OpenAPI y el modelo de datos no cambian
- [x] Rama `feature/SP-263-backend`, creada desde `develop`
