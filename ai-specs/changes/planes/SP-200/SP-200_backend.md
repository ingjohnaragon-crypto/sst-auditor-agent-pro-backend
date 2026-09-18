# Plan de implementación backend: SP-200 — Matriz cruzada de NR (NP × NC) y aceptabilidad

## 1. Resumen

SP-200 es subtarea de **SP-148** (motor GTC 45). Capa: **dominio FastAPI**, no Angular.
`NR = NP × NC`, la interpretación I–IV (tabla A.3) y el mapa de aceptabilidad
**ya están entregados** en la matriz GTC 45 (línea SP-145 / SP-192). Son la
fuente de verdad de persistencia.

Este plan **no pide reimplementar** el algoritmo ni extraerlo a un servicio
nuevo. El alcance restante es **verificar** el contrato (dominio + respuesta PUT)
contra GTC 45 Anexo A.3 y la decisión D1, cubrir huecos menores de prueba si
aparecen, y cerrar la subtarea en Jira (hoy: **En curso**).

- **Stack activo**: `python-fastapi` (Python 3.12 + FastAPI, SQLAlchemy 2.x
  async, Alembic, PostgreSQL, Pydantic v2).
- **Arquitectura**: DDD — `EvaluacionRiesgo.crear` / `recalcular` calculan NR;
  `interpretar_nr` asigna I–IV; `ACEPTABILIDAD_POR_INTERPRETACION` mapea
  aceptabilidad. El cliente solo envía ND/NE/NC.
- **Fuente normativa**: `.sst-agent-document.md` Anexo A.2/A.3 (`NR = NP × NC`);
  `ai-specs/specs/data-model.md` (rangos A.3 y D1: NR=0 → IV / ACEPTABLE).
- **Padre / hermanos**: SP-148 (HU); SP-199 (NP = ND × NE — plan aparte, ya
  cubierto); SP-201 (semáforo Angular — repo frontend).

**Fuera de alcance**: reescribir `EvaluacionRiesgo` o `interpretar_nr` salvo bug
vs A.3; duplicar la matriz en aplicación; interpretación cualitativa de NP
(Muy Alto 24–40, etc. — eso es SP-199/Anexo A.1); espejo TypeScript
`ServicioCalculoRiesgoGtc45`; cambiar rangos A.3; migraciones.

## Estimación de puntos de historia

<!-- STORY_POINTS:3 -->
- **HU total**: 3 (Fibonacci: 1, 2, 3, 5, 8, 13)
- **Justificación**: rangos A.3 + mapa de aceptabilidad + D1 ya viven en
  dominio y hay casos (10,4,100)→NR 4000 / I / NO_ACEPTABLE, bordes A.3 y
  PUT 201. El esfuerzo restante es auditoría, aserciones HTTP de D1
  (`aceptabilidad`) y cierre en Jira. Coincide con los 3 puntos del ticket.
  Esfuerzo restante estimado: **0–1** (solo verificación).
- **Subtareas**: ninguna (SP-200 es ella misma subtarea de SP-148).

| Relacionada | Puntos | Nota |
|---|---:|---|
| SP-199 | 2 | NP — no reabrir aquí. |
| SP-200 (esta) | 3 | Ya entregada; verificar y cerrar. |
| SP-201 | — | Frontend; no cubierto aquí. |

<!-- /STORY_POINTS -->

## 2. Contexto de arquitectura

- Stack activo: `python-fastapi` (`Python 3.12 + FastAPI`)
- Capas involucradas (solo lectura / posible refuerzo de tests):

| Capa | Archivos | Rol en SP-200 |
|---|---|---|
| Domain | `src/domain/models/evaluacion_riesgo.py` | `nr = np * nc`; `interpretar_nr` |
| Domain | `src/domain/models/gtc45.py` | `NC_VALIDOS`, `InterpretacionNR`, `ACEPTABILIDAD_POR_INTERPRETACION` |
| Domain | `src/domain/exceptions/matriz_riesgo.py` | `ValorGtcInvalidoError` si NR no encaja en A.3 |
| Application | `src/application/dto/matriz_riesgo.py` | request solo ND/NE/NC; respuesta incluye NR/interpretación/aceptabilidad |
| Application | `src/application/services/servicio_matriz_riesgos.py` | `upsert_evaluacion` no lee derivados del DTO |
| Presentation | `src/presentation/routers/matriz_riesgos_router.py` | `PUT /api/v1/peligros/{peligro_id}/evaluacion` |
| Infrastructure | `src/infrastructure/database/modelos/evaluacion_riesgo_orm.py` | persiste derivados ya calculados |
| Tests | `tests/unit/domain/test_evaluacion_riesgo.py` | (10,4,100), D1, bordes A.3 |
| Tests | `tests/integration/test_matriz_riesgos.py` | PUT 201 con NR/I/NO_ACEPTABLE |
| Docs | `ai-specs/specs/data-model.md`, `ai-specs/specs/api-spec.yml` | NR derivado y rangos A.3 |

### Implementación de referencia (no reescribir)

```python
np = nd * ne
nr = np * nc
interpretacion = interpretar_nr(nr)
aceptabilidad = ACEPTABILIDAD_POR_INTERPRETACION[interpretacion]
```

Rangos `interpretar_nr` (extensión D1 de IV a NR=0):

| Interpretación | NR | Aceptabilidad |
|---|---|---|
| I | 600–4000 | `NO_ACEPTABLE` |
| II | 150–500 | `ACEPTABLE_CON_CONTROL` |
| III | 40–120 | `MEJORABLE` |
| IV | 0–20 | `ACEPTABLE` |

La GTC 45 A.3 en `.sst-agent-document.md` lista IV como «20»; el proyecto
**extiende** IV a `0–20` (decisión D1 documentada). No reabrir ND anulable.

`SolicitudUpsertEvaluacion` no tiene `nivel_riesgo`, `interpretacion_nr` ni
`aceptabilidad`; `extra="forbid"` → 422 `ERROR_VALIDACION` si el cliente los envía.

Los productos discretos ND×NE×NC **no caen** en los huecos A.3 (21–39, 121–149,
501–599). El `raise` de `interpretar_nr` es defensa; no aparece en el flujo PUT
válido.

### Mapeo de subtareas

No hay subtareas — el plan se deriva directamente de SP-200.

| Clave | Resumen | Paso(s) de implementación |
|---|---|---|
| `SP-200` | Matriz cruzada NR y aceptabilidad | Pasos 1–6 (verificar); 0 y 2–4 solo si hay defecto |

## 3. Pasos de implementación

### Paso 0: Rama feature — solo si hay defecto

- **Acción por defecto**: **no** abrir rama. El código productivo no debe
  cambiar si los tests de NR/A.3 están verdes.
- **Si** el Paso 1 demuestra un bug vs tabla A.3 / D1 (NR ≠ NP×NC,
  interpretación fuera de rango, D1 sin IV/ACEPTABLE, PUT que persistiera
  derivados del cliente):
  - **Rama**: `feature/SP-200-backend`
  - **Base**: `develop`

```bash
git checkout develop
git pull --ff-only origin develop
git checkout -b feature/SP-200-backend
```

### Paso 1: Auditar NR, interpretación y aceptabilidad

- **Archivos** (solo lectura):
  - `src/domain/models/evaluacion_riesgo.py` (`crear`, `recalcular`, `interpretar_nr`)
  - `src/domain/models/gtc45.py`
  - `tests/unit/domain/test_evaluacion_riesgo.py`
  - `tests/integration/test_matriz_riesgos.py`
- **Confirmar**:
  1. `nivel_riesgo = nivel_probabilidad * nc` (nunca un NR de entrada).
  2. Caso canónico: ND=10, NE=4, NC=100 → NP=40, NR=4000, I, `NO_ACEPTABLE`.
  3. D1: ND=0 → NR=0, IV, `ACEPTABLE`.
  4. Bordes A.3 ya parametrizados: 600/I, 500/II, 120/III, 20/IV.
  5. Respuesta PUT incluye `nivel_riesgo`, `interpretacion_nr`, `aceptabilidad`.
- **Comando**:

```bash
pytest tests/unit/domain/test_evaluacion_riesgo.py tests/integration/test_matriz_riesgos.py -q
```

### Paso 2: Dominio — solo ante defecto

- **Archivos**: `evaluacion_riesgo.py`, `gtc45.py`
- **Cambio permitido**: corregir `nr = np * nc` y/o rangos A.3 para coincidir
  con `data-model.md`. No mover la matriz a aplicación/infraestructura.
- **No crear** migración: columnas derivadas ya existen.

### Paso 3: Contrato de escritura (DTO + servicio) — solo ante defecto

- **Invariante**: `SolicitudUpsertEvaluacion` permanece con tres campos y
  `extra="forbid"`.
- **No añadir** `nivel_riesgo` / `interpretacion_nr` / `aceptabilidad` al
  request aunque el preview Angular (SP-201) los calcule.

### Paso 4: Router — sin cambios previstos

- `PUT /api/v1/peligros/{peligro_id}/evaluacion` — 201 crea, 200 recalcula.
- `RespuestaEvaluacionRiesgo` ya expone los tres derivados de SP-200.
- No hay endpoint nuevo.

### Paso 5: Excepciones — sin cambios previstos

| HTTP | Código | Cuándo |
|---|---|---|
| 422 | `VALOR_GTC_INVALIDO` | ND/NE/NC fuera de conjunto; o NR que no encaja en A.3 (solo si se llama `interpretar_nr` con un entero ajeno a los productos discretos) |
| 422 | `ERROR_VALIDACION` | Body con `nivel_riesgo` / `interpretacion_nr` / `aceptabilidad` extra |
| 404 | `PELIGRO_NO_ENCONTRADO` | PUT sobre peligro inexistente |

No introducir códigos nuevos.

### Paso 6: Pruebas (verificación + huecos menores)

**Ya cubierto (no duplicar):**

| Caso | Esperado |
|---|---|
| (10, 4, 100) dominio + PUT 201 | NR=4000, I, `NO_ACEPTABLE` |
| (0, 4, 100) dominio | NR=0, IV, `ACEPTABLE` |
| Bordes A.3 (600, 500, 120, 20) | I / II / III / IV + mapa de aceptabilidad |
| PUT extra `nivel_riesgo` | 422 `ERROR_VALIDACION` (junto con NP, SP-199) |

**Huecos opcionales** (no bloquean el cierre si el Paso 1 está verde):

1. PUT D1 HTTP 200: afirmar `aceptabilidad == "ACEPTABLE"` (hoy se afirma NR=0 e IV).
2. `recalcular` D1: afirmar `aceptabilidad == ACEPTABLE`.
3. Tests unitarios directos de `interpretar_nr` en bordes (0, 20, 40, 120, 150,
   500, 600, 4000) y un valor de hueco (p. ej. 21) → `ValorGtcInvalidoError`.
4. Extra en PUT: `interpretacion_nr` / `aceptabilidad` además de NR (mismo 422).

No hace falta un cartesiano de 64 combinaciones ND×NE×NC: los productos
discretos no caen en huecos A.3; los bordes ya anclan cada banda.

**Comandos**:

```bash
pytest tests/unit/domain/test_evaluacion_riesgo.py tests/integration/test_matriz_riesgos.py -q
pytest --cov --cov-report=html
```

### Paso 7: Documentación

- **No actualizar** `data-model.md` ni `api-spec.yml` salvo defecto de contrato
  (no se espera). Ya documentan NR derivado y rangos A.3.
- Si se añade la aserción HTTP de `aceptabilidad` en D1, una línea en
  `tests/integration/README.md` basta.

## 4. Orden de implementación

1. Paso 1 — unitarios + integración de evaluación vs A.3/D1.
2. Si todo verde: saltar 0 y 2–4; opcionalmente los huecos del Paso 6; ir al
   cierre Jira.
3. Si hay defecto: Paso 0 → 2 → 3 → 4 → 5 → 6 → 7.
4. `os-transition SP-200 "Done"` (o equivalente) con evidencia de tests verdes.

## 5. Lista de verificación de pruebas

- [x] `pytest` pasa con 0 fallos (332 passed)
- [x] `pytest --cov --cov-report=html` muestra cobertura >= 90 % (98.24 %)
- [x] `pytest tests/unit/domain/test_evaluacion_riesgo.py` verde
- [x] `pytest tests/integration/test_matriz_riesgos.py` verde
- [x] (10, 4, 100) → NR=4000, I, `NO_ACEPTABLE` (dominio y PUT)
- [x] ND=0 → NR=0, IV, `ACEPTABLE`
- [x] PUT no incluye NR/interpretación/aceptabilidad en el schema de escritura
- [x] No se reabrió SP-199 (fórmula NP) ni SP-201 (semáforo)
- [x] Tests existentes no rotos

### Evidencia HTTP (os-develop)

```bash
# 201 — NR derivado 40×100 = 4000 / I / NO_ACEPTABLE
curl -sS -X PUT "$BASE/api/v1/peligros/$PELIGRO_ID/evaluacion" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"nivel_deficiencia":10,"nivel_exposicion":4,"nivel_consecuencia":100}'

# 200 — D1: ND=0 → NR=0 / IV / ACEPTABLE
curl -sS -X PUT "$BASE/api/v1/peligros/$PELIGRO_ID/evaluacion" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"nivel_deficiencia":0,"nivel_exposicion":4,"nivel_consecuencia":100}'

# 422 ERROR_VALIDACION — el cliente no inyecta NR/interpretación/aceptabilidad
curl -sS -X PUT "$BASE/api/v1/peligros/$PELIGRO_ID/evaluacion" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"nivel_deficiencia":2,"nivel_exposicion":2,"nivel_consecuencia":10,"nivel_riesgo":999,"interpretacion_nr":"I","aceptabilidad":"NO_ACEPTABLE"}'
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

Mapeo HTTP: 422 `VALOR_GTC_INVALIDO` / `ERROR_VALIDACION` | 404 `PELIGRO_NO_ENCONTRADO`
| 401 `TOKEN_INVALIDO` | 403 `ACCESO_DENEGADO`.

## 8. Dependencias

Ninguna librería nueva. No hay cambios de `requirements.txt`.

## 9. Notas

- **Fuente de verdad**: backend. El preview Angular (SP-148/SP-201) espeja A.3
  y **no** sustituye esta subtarea ni debe enviarse en el PUT.
- **No duplicar** `NR = NP × NC` ni `interpretar_nr` en un servicio de
  aplicación.
- SP-199 cubre solo NP; no mezclar criterios de aceptación.
- Ticket Jira en **En curso**; tras evidencia de tests, pasar a Done.
- Plan hermano corto (HU): frontend
  `ai-specs/changes/planes/SP-148/SP-148_backend.md`. Este archivo es el plan
  **ejecutable** de SP-200 en el backend.

## 10. Lista de verificación de la implementación

- [x] Calidad: sin errores de compilación, `ruff check .` pasa
- [x] Dominio: NR/interpretación/aceptabilidad en factoría/`recalcular`; no se aceptan del cliente
- [x] Aplicación: DTO de escritura solo ND/NE/NC
- [x] Presentación: router delgado
- [x] Migraciones: ninguna
- [x] Tests: verdes, cobertura 98.24 %, PUT 201/200 demuestra derivados; `interpretar_nr` al 100 %
- [x] Documentación: README de integración anota D1 ACEPTABLE y extra derivados
- [ ] Jira: SP-200 en Done tras pytest verde (siguiente: `os-commit` / `os-transition`)
