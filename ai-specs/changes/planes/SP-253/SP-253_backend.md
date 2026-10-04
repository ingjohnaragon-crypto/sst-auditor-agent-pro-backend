# Plan de implementación backend: SP-253 Exponer resumen ejecutivo por empresa

## 1. Resumen

Endpoint de solo lectura que arma el resumen de una empresa para el inicio. Usa filas ya persistidas: autoevaluaciones, `interpretacion_nr` de la matriz GTC 45 y las calificaciones de los numerales `1.1.1` y `1.1.4`. No llama a `motor_calificacion_res312` ni a `interpretar_nr`. No hay migración.

- **Stack activo**: `python-fastapi` (Python 3.12 + FastAPI).
- **Capas**: Application (DTO y servicio), Presentation (router y dependencia). Dominio e infraestructura se reutilizan.
- **Fuera de alcance**: pantallas SP-254, SP-255 y SP-256; recálculo del puntaje 0312; multa ilustrativa.

## Estimación de puntos de historia

<!-- STORY_POINTS:5 -->
- **HU total**: 5 (Fibonacci: 1, 2, 3, 5, 8, 13)
- **Justificación**: un GET, un DTO y un servicio de lectura sobre repositorios que ya existen. El esfuerzo está en el desempate de la última autoevaluación, el conteo de la matriz y las pruebas. Jira ya tiene 5 puntos; se confirman.
- **Subtareas**: no hay subtareas en Jira.
<!-- /STORY_POINTS -->

## 2. Contexto de arquitectura

- Stack activo: `python-fastapi` (Python 3.12 + FastAPI)
- El servicio depende de puertos, no de SQLAlchemy.

| Capa | Archivos |
|---|---|
| Dominio | Sin modelo nuevo. Reutilizar `EmpresaNoEncontradaError`, `RepositorioEmpresa`, `RepositorioAutoevaluacion`, `RepositorioEstandarMinimo`, `RepositorioProcesoActividad` |
| Application | `respuesta_resumen_ejecutivo.py` (crear), `servicio_resumen_ejecutivo.py` (crear) |
| Presentation | `resumen_ejecutivo_router.py` (crear), `dependencies/autoevaluacion.py` (proveer el servicio), `routers/__init__.py` (registrar) |
| Infrastructure | Sin cambios. `obtener_repositorio_proceso` ya existe en `dependencies/matriz_riesgo.py` |
| Docs | `ai-specs/specs/api-spec.yml` |
| Tests | `tests/unit/application/test_servicio_resumen_ejecutivo.py`, `tests/integration/test_resumen_ejecutivo.py` |

### Mapeo de subtareas

No hay subtareas: el plan sale directo de la tarea.

## 3. Pasos de implementación

### Paso 0: Crear la rama feature

- **Rama**: `feature/SP-253-backend` desde `develop`.
- **Comandos**:
  ```bash
  git checkout develop && git pull origin develop
  git checkout -b feature/SP-253-backend
  ```

### Paso 1: Sin migración

No hay tablas ni columnas nuevas. No crear revisión de Alembic.

### Paso 2: Sin entidad nueva

No se amplía el dominio. `SIN_CALIFICAR` no entra en `ResultadoCalificacion`; solo existe en el DTO de esta respuesta.

### Paso 3: Sin puerto nuevo

- Empresa: `buscar` del repositorio de empresas (el mismo que usa `ServicioEmpresas` para el 404).
- Autoevaluaciones: `listar_por_empresa`. Ya carga calificaciones. Ordena por `fecha`, no por `fecha_creacion`.
- Catálogo: `RepositorioEstandarMinimo.listar`.
- Matriz: `obtener_matriz_por_empresa`. Cada peligro trae `evaluacion: EvaluacionRiesgo | None`.

### Paso 4: DTO de respuesta

- Archivo: `src/application/dto/respuesta_resumen_ejecutivo.py`
- `RespuestaResumenEjecutivo`:
  - `empresa_id: UUID`
  - `cantidad_autoevaluaciones: int`
  - `autoevaluacion_id: UUID | None`
  - `requiere_plan_mejora: bool`
  - `riesgos_nivel_i: int`
  - `riesgos_nivel_ii: int`
  - `distribucion_riesgos`: modelo con alias JSON `I`, `II`, `III`, `IV` (enteros)
  - `irrenunciables`: lista de dos ítems, cada uno con `numeral`, `descripcion`, `resultado`
- `resultado` admite `CUMPLE`, `NO_CUMPLE`, `NO_APLICA` y `SIN_CALIFICAR`.
- Serializar los alias `I`–`IV` en la respuesta JSON (`serialization_alias` o equivalente en Pydantic v2).

### Paso 5: Servicio

- Archivo: `src/application/services/servicio_resumen_ejecutivo.py`
- Constructor: los cuatro repositorios nombrados en el paso 3.
- Método: `async def obtener(self, empresa_id: UUID) -> RespuestaResumenEjecutivo`
- Reglas:
  1. Si la empresa no existe, `EmpresaNoEncontradaError`.
  2. `cantidad_autoevaluaciones` es el largo de `listar_por_empresa`.
  3. La última es la de mayor `fecha` y, en empate, la de mayor `fecha_creacion`. El desempate se hace en el servicio, no en el SQL.
  4. De esa fila se copian `id` y `requiere_plan_mejora`. No se recalcula el umbral de 85.
  5. Sin autoevaluaciones: `autoevaluacion_id` null, `requiere_plan_mejora` false.
  6. Recorrer la matriz. Si `evaluacion` es `null`, no cuenta. Si existe, sumar `evaluacion.interpretacion_nr` persistida. No llamar a `interpretar_nr`.
  7. `riesgos_nivel_i` y `riesgos_nivel_ii` son los mismos enteros que `I` y `II`.
  8. Irrenunciables en orden `1.1.1`, `1.1.4`. `descripcion` del catálogo. `resultado` de la calificación de la última autoevaluación con el mismo `estandar_id`. Si no hay autoevaluación o no hay esa calificación, `SIN_CALIFICAR`.
  9. Si el catálogo no trae uno de esos numerales, no inventar la descripción: fallar con un error de dominio (no responder 200).

### Paso 6: Router

- Archivo: `src/presentation/routers/resumen_ejecutivo_router.py`
- `GET /empresas/{empresa_id}/resumen-ejecutivo`
- Registrar en `src/presentation/routers/__init__.py` con `settings.api_prefix`, de modo que la ruta pública sea `GET /api/v1/empresas/{empresa_id}/resumen-ejecutivo`.
- Auth: `obtener_usuario_actual`. No usar `requerir_rol_escritor`. `CONSULTA` puede leer.
- `response_model=RespuestaResumenEjecutivo`, status 200.
- Errores documentados con `RespuestaError`: 401 `TOKEN_INVALIDO`, 404 `EMPRESA_NO_ENCONTRADA`.
- Proveer el servicio en `src/presentation/dependencies/autoevaluacion.py` reutilizando `obtener_repositorio_empresa`, `obtener_repositorio_autoevaluacion`, `obtener_repositorio_estandar_minimo` y `obtener_repositorio_proceso`.

### Paso 7: Errores

No crear un 404 nuevo. Reutilizar `EmpresaNoEncontradaError` (`EMPRESA_NO_ENCONTRADA`, 404). El manejador global ya lo traduce a `RespuestaError`.

Para el catálogo incompleto, un error de dominio propio, código `CATALOGO_IRRENUNCIABLE_INCOMPLETO`, HTTP 500. No forma parte del contrato feliz.

### Paso 8: Pruebas

- `tests/unit/application/test_servicio_resumen_ejecutivo.py` con repositorios falsos:
  - Dos autoevaluaciones: conteo 2 y gana la de `fecha` mayor.
  - Misma `fecha`: gana la `fecha_creacion` más reciente.
  - Sin autoevaluaciones: conteo 0, id null, `requiere_plan_mejora` false, ambos irrenunciables `SIN_CALIFICAR` con la descripción del catálogo.
  - Matriz con una evaluación I, una II y un peligro sin evaluación: I=1, II=1, III=0, IV=0. Los campos `riesgos_nivel_i` y `riesgos_nivel_ii` coinciden.
  - 1.1.1 en `NO_CUMPLE` y 1.1.4 sin calificación: esos dos resultados.
  - Empresa inexistente: `EmpresaNoEncontradaError`.
  - Parchear `interpretar_nr` y el motor y afirmar que no se llamaron.
  - Catálogo sin `1.1.1`: no responde el DTO.
- `tests/integration/test_resumen_ejecutivo.py`:
  - `CONSULTA` recibe 200.
  - Sin token, 401.
  - UUID de empresa desconocido, 404 `EMPRESA_NO_ENCONTRADA`.

### Paso 9: Documentación

- Añadir `GET /api/v1/empresas/{empresa_id}/resumen-ejecutivo` en `ai-specs/specs/api-spec.yml`, junto a las rutas de empresa ya existentes.
- No cambiar `data-model.md`: el esquema no cambia.

## 4. Orden de implementación

1. Paso 0 — Rama `feature/SP-253-backend`
2. Paso 4 — DTO
3. Paso 7 — Error de catálogo incompleto, si se crea
4. Paso 5 — Servicio
5. Paso 6 — Dependencia y router
6. Paso 8 — Pruebas unitarias e integración
7. Paso 9 — OpenAPI en `api-spec.yml`

## 5. Checklist de pruebas

- [ ] `pytest` pasa con 0 fallos
- [ ] `pytest --cov --cov-report=html` se mantiene en el umbral del 90 %
- [ ] `GET` probado: 200 con `CONSULTA`, 401 sin token, 404 empresa inexistente
- [ ] Los tests existentes de autoevaluación y matriz siguen en verde

## 6. Referencia de tooling

| Propósito | Comando |
|---|---|
| Build | `pip install -r requirements.txt` |
| Test | `pytest` |
| Run | `uvicorn main:app --reload` |
| Lint | `ruff check .` |
| Coverage | `pytest --cov --cov-report=html` |

## 7. Formato de error

El API usa `RespuestaError`, no el esquema genérico en inglés:

```json
{
  "exito": false,
  "codigo": "EMPRESA_NO_ENCONTRADA",
  "mensaje": "La empresa no fue encontrada",
  "detalle": null
}
```

Mapeo de este ticket: 401 `TOKEN_INVALIDO`, 404 `EMPRESA_NO_ENCONTRADA`. El catálogo incompleto no es un caso de cliente.

## 8. Dependencias

Ninguna librería nueva.

## 9. Notas

- `calificacion_id` de evidencias no interviene. Aquí el id relevante es el de la autoevaluación y el `estandar_id` del catálogo.
- Un peligro sin evaluación no entra en I–IV.
- La actividad reciente y las tarjetas del dashboard no se implementan en este repositorio.
- Commits en español, por ejemplo `feat(resumen): expone el resumen ejecutivo por empresa`.
- PR contra `develop`.

## 10. Checklist de verificación de implementación

- [ ] El servicio no abre sesión SQL ni llama al motor ni a `interpretar_nr`
- [ ] El router solo autentica y delega
- [ ] No hay migración
- [ ] OpenAPI muestra el `response_model` y los alias `I`–`IV`
- [ ] Pruebas en verde y cobertura del servicio y del router dentro del umbral
- [ ] `api-spec.yml` actualizado

## Verificación HTTP

El catálogo de integración no trae `1.1.1` ni `1.1.4`; la prueba de 200 los inserta en la misma base. Contra un API con el catálogo Res. 0312 sembrado:

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/empresas/$EMPRESA_ID/resumen-ejecutivo
curl -s -o /dev/null -w "%{http_code}" \
  http://localhost:8000/api/v1/empresas/$EMPRESA_ID/resumen-ejecutivo
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/empresas/00000000-0000-0000-0000-000000000000/resumen-ejecutivo
```

Esperado: 200 con `CONSULTA`, 401 sin token, 404 si la empresa no existe.
