# Plan de implementación backend: SP-199 — Cálculo automático de NP (ND × NE)

## 1. Resumen

SP-199 es subtarea de **SP-148** (motor GTC 45). Capa: **dominio FastAPI**, no Angular.
El cálculo `NP = ND × NE` **ya está entregado** en la matriz GTC 45 (línea SP-145 /
SP-192) y es la fuente de verdad de persistencia.

Este plan **no pide reimplementar** la fórmula ni extraerla a un servicio nuevo.
El alcance restante es **verificar** el contrato (dominio + PUT) contra GTC 45
Anexo A.1 y la decisión D1, cubrir huecos menores de prueba si aparecen, y
cerrar la subtarea en Jira.

- **Stack activo**: `python-fastapi` (Python 3.12 + FastAPI, SQLAlchemy 2.x
  async, Alembic, PostgreSQL, Pydantic v2).
- **Arquitectura**: DDD — `EvaluacionRiesgo.crear` / `recalcular` calculan NP;
  el cliente solo envía ND/NE/NC.
- **Fuente normativa**: `.sst-agent-document.md` Anexo A.1 (`NP = ND × NE`);
  `ai-specs/specs/data-model.md` decisión D1 (ND «Bajo» = 0 → NP = 0).
- **Padre / hermanos**: SP-148 (HU); SP-200 (NR + interpretación I–IV +
  aceptabilidad — **fuera de este plan**); SP-201 (semáforo Angular — repo
  frontend).

**Fuera de alcance**: reescribir `EvaluacionRiesgo`; duplicar la fórmula en
otro servicio; interpretación cualitativa de NP (Muy Alto 24–40, etc.);
espejo TypeScript `ServicioCalculoRiesgoGtc45` (preview UX de SP-148/SP-201);
cambiar rangos ND/NE; migraciones.

## Estimación de puntos de historia

<!-- STORY_POINTS:2 -->
- **HU total**: 2 (Fibonacci: 1, 2, 3, 5, 8, 13)
- **Justificación**: la fórmula de dominio, validación ND/NE, D1 y el PUT que
  no acepta NP del cliente ya existen. El esfuerzo restante es auditoría de
  tests, posible aserción explícita de `NP = nd * ne` en la matriz parametrizada
  y cierre en Jira. Coincide con los 2 puntos registrados en el ticket.
  Esfuerzo restante estimado: **0–1** (solo verificación).
- **Subtareas**: ninguna (SP-199 es ella misma subtarea de SP-148).

| Relacionada | Puntos | Nota |
|---|---:|---|
| SP-199 (esta) | 2 | Ya entregada; verificar y cerrar. |
| SP-200 | 3 | NR/aceptabilidad — plan aparte. |
| SP-201 | — | Frontend; no cubierto aquí. |

<!-- /STORY_POINTS -->

## 2. Contexto de arquitectura

- Stack activo: `python-fastapi` (`Python 3.12 + FastAPI`)
- Capas involucradas (solo lectura / posible refuerzo de tests):

| Capa | Archivos | Rol en SP-199 |
|---|---|---|
| Domain | `src/domain/models/evaluacion_riesgo.py` | `np = nd * ne` en `crear` y `recalcular` |
| Domain | `src/domain/models/gtc45.py` | `ND_VALIDOS = {10, 6, 2, 0}`, `NE_VALIDOS = {4, 3, 2, 1}` |
| Domain | `src/domain/exceptions/matriz_riesgo.py` | `ValorGtcInvalidoError` (`VALOR_GTC_INVALIDO`) |
| Application | `src/application/dto/matriz_riesgo.py` | `SolicitudUpsertEvaluacion` solo ND/NE/NC, `extra="forbid"` |
| Application | `src/application/services/servicio_matriz_riesgos.py` | `upsert_evaluacion` llama `crear`/`recalcular`; no lee NP del DTO |
| Presentation | `src/presentation/routers/matriz_riesgos_router.py` | `PUT /api/v1/peligros/{peligro_id}/evaluacion` |
| Infrastructure | `src/infrastructure/database/modelos/evaluacion_riesgo_orm.py` | persiste `nivel_probabilidad` ya calculado |
| Tests | `tests/unit/domain/test_evaluacion_riesgo.py` | NP=40 (10×4) y NP=0 (D1) |
| Tests | `tests/integration/test_matriz_riesgos.py` | PUT 201 con `nivel_probabilidad == 40` |
| Docs | `ai-specs/specs/data-model.md`, `ai-specs/specs/api-spec.yml` | ya documentan NP derivado |

### Implementación de referencia (no reescribir)

```python
# EvaluacionRiesgo.crear / recalcular
np = nd * ne
```

- ND ∈ {10, 6, 2, 0}, NE ∈ {4, 3, 2, 1} vía `_validar_nd_ne_nc`.
- D1: ND=0 → NP=0 (independiente de NE).
- `SolicitudUpsertEvaluacion` **no tiene** `nivel_probabilidad`; `extra="forbid"`
  hace que un body con NP del cliente responda **422** (`ERROR_VALIDACION`), no
  que se persista un valor inyectado.

### Mapeo de subtareas

No hay subtareas — el plan se deriva directamente de SP-199.

| Clave | Resumen | Paso(s) de implementación |
|---|---|---|
| `SP-199` | Cálculo automático de NP (ND × NE) | Pasos 1–6 (verificar); 0 y 2–4 solo si hay defecto |

## 3. Pasos de implementación

### Paso 0: Rama feature — solo si hay defecto

- **Acción por defecto**: **no** abrir rama. El código productivo no debe
  cambiar si los tests de NP están verdes.
- **Si** el Paso 1 demuestra un bug vs tabla A.1 / D1 (NP distinto de `ND × NE`,
  PUT que persistiera NP del cliente, ND=0 sin NP=0):
  - **Rama**: `feature/SP-199-backend`
  - **Base**: `develop` (PRs de este repo no van a `main`).

```bash
git checkout develop
git pull --ff-only origin develop
git checkout -b feature/SP-199-backend
```

### Paso 1: Auditar el cálculo NP en dominio

- **Archivos** (solo lectura):
  - `src/domain/models/evaluacion_riesgo.py`
  - `src/domain/models/gtc45.py`
  - `tests/unit/domain/test_evaluacion_riesgo.py`
- **Confirmar**:
  1. `crear` y `recalcular` usan `nivel_probabilidad = nd * ne` (nunca un
     parámetro de entrada NP).
  2. ND/NE inválidos lanzan `ValorGtcInvalidoError` antes de calcular.
  3. D1: `EvaluacionRiesgo.crear(..., 0, 4, 100)` → `nivel_probabilidad == 0`.
  4. Caso canónico: ND=10, NE=4 → NP=40.
- **Comando**:

```bash
pytest tests/unit/domain/test_evaluacion_riesgo.py -q
```

- **Hueco conocido (opcional, no bloquea el cierre)**: el parametrizado
  `test_should_mapear_bordes_a3` afirma NR/interpretación/aceptabilidad pero
  **no** `assert ev.nivel_probabilidad == nd * ne`. Si se toca el archivo de
  tests, añadir esa aserción (y, si se desea, un parametrizado cartesiano
  ND×NE). No extraer un `ServicioCalculoNp` nuevo.

### Paso 2: Dominio — solo ante defecto

- **Archivo**: `src/domain/models/evaluacion_riesgo.py`
- **Cambio permitido**: corregir `crear`/`recalcular` para que NP sea
  estrictamente `nd * ne` tras validar conjuntos GTC. No mover la fórmula a
  aplicación/infraestructura.
- **No crear** migración: `nivel_probabilidad` ya es `SMALLINT NOT NULL` derivado.

### Paso 3: Contrato de escritura (DTO + servicio) — solo ante defecto

- **Archivos**:
  - `src/application/dto/matriz_riesgo.py` — `SolicitudUpsertEvaluacion`
  - `src/application/services/servicio_matriz_riesgos.py` — `upsert_evaluacion`
- **Invariante**: el DTO permanece con **tres campos** (`nivel_deficiencia`,
  `nivel_exposicion`, `nivel_consecuencia`) y `extra="forbid"`.
- **No añadir** `nivel_probabilidad` al request aunque el frontend lo calcule
  en preview (SP-201).

### Paso 4: Router — sin cambios previstos

- **Archivo**: `src/presentation/routers/matriz_riesgos_router.py`
- **Contrato**: `PUT /api/v1/peligros/{peligro_id}/evaluacion`
  - 201 si crea, 200 si recalcula.
  - Body: `SolicitudUpsertEvaluacion`.
  - Respuesta: `RespuestaEvaluacionRiesgo` incluye `nivel_probabilidad` derivado.
- No hay endpoint nuevo.

### Paso 5: Excepciones — sin cambios previstos

- ND/NE/NC fuera de conjunto → `ValorGtcInvalidoError` → HTTP 422,
  código `VALOR_GTC_INVALIDO`.
- Campo extra (`nivel_probabilidad` en PUT) → validación Pydantic → HTTP 422,
  código `ERROR_VALIDACION`.
- Peligro inexistente → `PELIGRO_NO_ENCONTRADO` (404). No forma parte del
  cálculo NP; no ampliar aquí.

### Paso 6: Pruebas (verificación + huecos menores)

**Unitarios existentes** (`tests/unit/domain/test_evaluacion_riesgo.py`):

| Caso | Esperado NP |
|---|---|
| ND=10, NE=4, NC=100 | 40 |
| ND=0, NE=4, NC=100 (D1) | 0 |
| `recalcular(0, 1, 10)` | 0 |
| ND=5 (inválido) | excepción, no calcula |

**Integración existente** (`tests/integration/test_matriz_riesgos.py`):

- PUT con `{10, 4, 100}` → 201 y `nivel_probabilidad == 40`.
- PUT posterior D1 `{0, 4, 100}` recalcula (hoy se afirma NR; NP=0 queda
  implícito en dominio).

**Refuerzos opcionales** (solo si el Paso 1 se hace en rama):

1. Aserción `nivel_probabilidad == nd * ne` en el parametrizado de bordes A.3.
2. Integración: PUT con `nivel_probabilidad` extra → 422 (`ERROR_VALIDACION`).
3. Tras upsert D1, afirmar `body["nivel_probabilidad"] == 0` en HTTP.

**Comandos**:

```bash
pytest tests/unit/domain/test_evaluacion_riesgo.py tests/integration/test_matriz_riesgos.py -q
pytest --cov --cov-report=html
```

### Paso 7: Documentación

- **No actualizar** `data-model.md` ni `api-spec.yml` salvo que el Paso 2–4
  cambie el contrato (no se espera).
- Ambos ya describen NP como derivado `ND × NE` y el PUT «solo ND/NE/NC».
- Si se añade el caso HTTP de campo extra, una línea en
  `tests/integration/README.md` (si existe y ya documenta la matriz) es
  suficiente; no crear docs nuevos.

## 4. Orden de implementación

1. Paso 1 — correr unitarios + integración de evaluación y contrastar con A.1/D1.
2. Si todo verde: saltar 0 y 2–4; opcionalmente el hueco de aserción NP del Paso 6
   **sin** rama si el equipo acepta un commit mínimo de tests en la rama actual;
   si no, ir directo al cierre (Paso 7 implícito + Jira).
3. Si hay defecto: Paso 0 → 2 → 3 → 4 → 5 → 6 → 7.
4. Cerrar SP-199 en Jira (`os-transition SP-199 "Done"` o equivalente) con
   evidencia de tests verdes.

## 5. Lista de verificación de pruebas

- [x] `pytest` pasa con 0 fallos (322 passed)
- [x] `pytest --cov --cov-report=html` muestra cobertura >= 90 % (98.19 %)
- [x] `pytest tests/unit/domain/test_evaluacion_riesgo.py` verde
- [x] `pytest tests/integration/test_matriz_riesgos.py` verde
- [x] NP = 40 para (10, 4); NP = 0 para ND = 0
- [x] PUT no incluye NP en el schema de escritura (`SolicitudUpsertEvaluacion`)
- [x] No se reabrió trabajo de SP-200 (NR/aceptabilidad) ni de SP-201 (semáforo)
- [x] Tests existentes no rotos

### Evidencia HTTP (os-develop)

La suite de integración cubre los mismos contratos. Curls equivalentes (token de
escritor, `PELIGRO_ID` real):

```bash
# 201 — NP derivado 10×4 = 40 (el body no lleva nivel_probabilidad)
curl -sS -X PUT "$BASE/api/v1/peligros/$PELIGRO_ID/evaluacion" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"nivel_deficiencia":10,"nivel_exposicion":4,"nivel_consecuencia":100}'

# 200 — D1: ND=0 → NP=0
curl -sS -X PUT "$BASE/api/v1/peligros/$PELIGRO_ID/evaluacion" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"nivel_deficiencia":0,"nivel_exposicion":4,"nivel_consecuencia":100}'

# 422 ERROR_VALIDACION — el cliente no puede inyectar NP
curl -sS -X PUT "$BASE/api/v1/peligros/$PELIGRO_ID/evaluacion" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"nivel_deficiencia":2,"nivel_exposicion":2,"nivel_consecuencia":10,"nivel_probabilidad":99}'
```

## 6. Referencia de herramientas

Comandos resueltos desde `openspec/config.yaml` para el stack activo:

| Propósito | Comando |
|---|---|
| Build | `pip install -r requirements.txt` |
| Test | `pytest` |
| Run | `uvicorn main:app --reload` |
| Coverage | `pytest --cov --cov-report=html` |
| Lint | `ruff check .` |

## 7. Formato de respuesta de error

Contrato del proyecto (`RespuestaError`):

```json
{
  "exito": false,
  "codigo": "VALOR_GTC_INVALIDO",
  "mensaje": "Descripción legible",
  "detalle": null
}
```

Mapeo HTTP relevante para SP-199:

| HTTP | Código | Cuándo |
|---|---|---|
| 422 | `VALOR_GTC_INVALIDO` | ND/NE/NC fuera de conjunto GTC |
| 422 | `ERROR_VALIDACION` | Body con campos extra (p. ej. `nivel_probabilidad`) o tipos inválidos |
| 404 | `PELIGRO_NO_ENCONTRADO` | PUT sobre peligro inexistente |
| 401 | `TOKEN_INVALIDO` | sin bearer |
| 403 | `ACCESO_DENEGADO` | rol CONSULTA en escritura |

No introducir códigos nuevos.

## 8. Dependencias

Ninguna librería nueva. No hay cambios de `requirements.txt`.

## 9. Notas

- **Fuente de verdad**: backend. El preview Angular (SP-148/SP-201) espeja la
  misma fórmula y **no** sustituye esta subtarea ni debe enviarse en el PUT.
- **No duplicar** `NP = ND × NE` en un servicio de aplicación. Vive en
  `EvaluacionRiesgo`.
- SP-200 cubre `NR = NP × NC`, `interpretar_nr` y aceptabilidad; no mezclar
  criterios de aceptación.
- Decisión D1 ya confirmada (2026-07-17): ND Bajo = 0, columna NOT NULL; no
  reabrir la opción de ND anulable.
- Ticket Jira en estado **Listo**; tras evidencia de tests, pasar a Done.
- Plan hermano de verificación más corto (contexto HU): frontend
  `ai-specs/changes/planes/SP-148/SP-148_backend.md` (repo frontend). Este
  archivo es el plan **ejecutable** de la subtarea SP-199 en el backend.

## 10. Lista de verificación de la implementación

- [x] Calidad: sin errores de compilación, `ruff check .` pasa, inyección por constructor
- [x] Dominio: NP se calcula en factoría/`recalcular`; no se acepta del cliente
- [x] Aplicación: DTO de escritura solo ND/NE/NC; servicio no toca SQL
- [x] Presentación: router delgado; validación Pydantic antes del servicio
- [x] Migraciones: ninguna
- [x] Tests: verdes, cobertura 98.19 %, 422 cubierto para valor GTC inválido y NP extra
- [x] Documentación: README de integración anota PUT que rechaza NP extra
- [ ] Jira: SP-199 en Done tras pytest verde (siguiente: `os-commit` / `os-transition`)
