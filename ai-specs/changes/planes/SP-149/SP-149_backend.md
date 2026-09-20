# Plan de implementación backend: SP-149 Motor de Calificación PHVA y Estado Res. 0312

## 1. Resumen

Implementar el **motor de calificación ponderada por perfil empresarial** (Res. 0312) y la **segmentación de cumplimiento por fases PHVA**, exponiendo un endpoint de lectura para que el frontend (SP-204) renderice barras y brechas.

La autoevaluación transaccional ya existe (SP-144): catálogo de 60 ítems, calificación derivada (`CUMPLE`/`NO_APLICA` → `valor_porcentual`; `NO_CUMPLE` → 0), `finalizar` con `puntaje_total` y umbral 85 %. Hoy `finalizar` exige 60 calificaciones manuales **sin** resolver perfil ni autoasignar `NO_APLICA` a ítems no exigibles (Art. 27).

- **Stack activo**: `python-fastapi` (Python 3.12 + FastAPI, SQLAlchemy 2.x async, Alembic, PostgreSQL, Pydantic v2).
- **Arquitectura**: DDD por capas — motor puro en `domain/services/` (sin FastAPI/SQLAlchemy), casos de uso en application, router fino con `Depends()`.
- **Fuente normativa**: `.sst-agent-document.md` + Res. 0312 Arts. 3, 8, 9, 15, 16 y Tabla de Valores Art. 27.

**Fuera de alcance de este plan backend**:

- SP-204 (gráficos Angular) — repo `sst-auditor-agent-pro-frontend`; este plan solo fija el contrato API que consume.
- Unidades Agropecuarias Art. 7 (3 estándares).
- CRUD de planes de mejoramiento.
- Cambios al seed de los 60 ítems / pesos PHVA.
- Semáforo GTC 45 (SP-148).

**Decisiones de diseño (cerradas en este plan)**:

1. **Preview en vivo** en `GET .../cumplimiento-phva`: no exige finalización; ítems exigibles sin calificar cuentan 0; ítems no exigibles del perfil se tratan como `NO_APLICA` virtual (puntaje máximo) solo para el resumen. Campo `finalizada: bool` en la respuesta.
2. **Política al finalizar**: autoasignar `NO_APLICA` **solo si el ítem aún no tiene calificación**; no pisar calificaciones manuales existentes.
3. **Sin migración Alembic**: no hay cambio de esquema; el mapeo de perfil vive en JSON de datos.

## Estimación de puntos de historia

<!-- STORY_POINTS:8 -->
- **HU total**: 8 (Fibonacci: 1, 2, 3, 5, 8, 13)
- **Justificación**: Coincide con el enriquecimiento en Jira. El volumen no es de esquema nuevo, pero sí de reglas normativas (perfil + mapeo de numerales), cambio del flujo `finalizar`, motor PHVA con `Decimal`, endpoint + OpenAPI y suite unitaria/integración. La incertidumbre media está en completar el mapeo `TABLA_7`/`TABLA_21` de numerales no aplicables (validación de producto). SP-204 suma esfuerzo en frontend pero **no** se implementa en este repo.
- **Subtareas**:
  | Subtarea | Puntos | Nota |
  |---|---|---|
  | SP-202 | 5 | Resolutor de perfil + JSON de mapeo + ajuste de `finalizar` + unitarios |
  | SP-203 | 3 | Segmentación PHVA + `GET .../cumplimiento-phva` + OpenAPI + integración |
  | SP-204 | 3 | Angular — **fuera de este plan** (repo frontend) |
<!-- /STORY_POINTS -->

## 2. Contexto de arquitectura

- Stack activo: `python-fastapi` (`Python 3.12 + FastAPI`)
- Capas involucradas:

| Capa | Archivos afectados |
|---|---|
| Domain | `src/domain/models/perfil_estandares.py` (nuevo); `src/domain/services/motor_calificacion_res312.py` (nuevo); `src/domain/models/autoevaluacion.py` (modificar: helper aplicar NO_APLICA / completar no exigibles); excepciones solo si hace falta mensaje más específico (reutilizar `AutoevaluacionIncompletaError`) |
| Application | `src/application/dto/respuesta_cumplimiento_phva.py` (nuevo); `src/application/mappers/mapper_cumplimiento_phva.py` (nuevo); `src/application/services/servicio_autoevaluaciones.py` (modificar: `finalizar` + `obtener_cumplimiento_phva`); carga del mapa JSON (módulo helper en application o domain package resource) |
| Presentation | `src/presentation/routers/autoevaluaciones_router.py` (nueva ruta GET) |
| Data | `scripts/datos/perfil_estandares_res312.json` (nuevo) |
| Docs | `ai-specs/specs/api-spec.yml`, `ai-specs/specs/data-model.md` |
| Tests | `tests/unit/domain/services/test_motor_calificacion_res312.py`; `tests/unit/application/test_servicio_autoevaluaciones_perfil.py` (o extender el existente); `tests/integration/test_cumplimiento_phva.py` |
| Infrastructure | Sin cambios de ORM/migración; reutilizar repos de autoevaluación, empresa y estándares |

### Mapeo de subtareas

| Clave | Resumen | Paso(s) de implementación |
|---|---|---|
| `SP-202` | Programar algoritmo de cumplimiento ponderado global | Pasos 1, 2, 3, 5 (parcial: `finalizar`), 7, 8 (unitarios de perfil/ponderación) |
| `SP-203` | Desarrollar motor de segmentación por fases PHVA | Pasos 2 (segmentación), 4, 5 (caso de uso resumen), 6, 8 (unitarios PHVA + integración), 9 |
| `SP-204` | Crear gráficos dinámicos de cumplimiento en Angular | Fuera de este repo — sin pasos aquí; contrato API en Pasos 4 y 9 |

## 3. Pasos de implementación

### Paso 0: Crear la rama feature

- **Acción**: crear y cambiar a la rama de la HU (las features del proyecto parten de `develop` y sus PRs apuntan a `develop`).
- **Rama**: `feature/SP-149-backend`
- **Comandos**:
  ```bash
  git checkout develop && git pull origin develop
  git checkout -b feature/SP-149-backend
  ```

### Paso 1: Datos de mapeo de perfil (sin migración)

- **Archivo**: `scripts/datos/perfil_estandares_res312.json`
- **Contenido mínimo**:
  ```json
  {
    "fuente": "Resolucion 0312 de 2019 — Arts. 3, 8, 9, 15, 16 y Art. 27",
    "version": "1.0.0",
    "perfiles": {
      "TABLA_7": { "numerales_no_aplican": [] },
      "TABLA_21": { "numerales_no_aplican": [] },
      "TABLA_60": { "numerales_no_aplican": [] }
    }
  }
  ```
- **Obligatorio antes de merge**: completar `numerales_no_aplican` de `TABLA_7` y `TABLA_21` con el cruce normativo Art. 3 / Art. 9 ↔ Tabla de Valores Art. 27 (todos los numerales deben existir en `estandares_minimos_res312.json`). `TABLA_60` permanece `[]`.
- **Validación en tests**: fixture con listas pequeñas controladas; test de humo que todo numeral del JSON ∈ catálogo de 60.
- **Nota**: Art. 7 agropecuario no se modela.

### Paso 2: Modelos y motor de dominio

#### 2.1 Enum / value objects — `src/domain/models/perfil_estandares.py`

- `PerfilEstandaresRes312(StrEnum)`: `TABLA_7`, `TABLA_21`, `TABLA_60`.
- `@dataclass(frozen=True) MapaPerfilEstandares`: carga en memoria `dict[PerfilEstandaresRes312, frozenset[str]]` de numerales no aplicables.
- Factoría `MapaPerfilEstandares.desde_dict(datos: dict) -> MapaPerfilEstandares` con validación básica (perfiles requeridos, numerales string no vacíos).

#### 2.2 Motor — `src/domain/services/motor_calificacion_res312.py`

Funciones puras (estilo `calculos_estadisticos_sst.py`), tipadas, con `Decimal`:

| Función | Contrato |
|---|---|
| `resolver_perfil_estandares(nivel_riesgo_arl: str, numero_trabajadores: int) -> PerfilEstandaresRes312` | Reglas: (≤10 ∧ I\|II\|III) → `TABLA_7`; (11–50 ∧ I\|II\|III) → `TABLA_21`; resto (incl. IV\|V cualquier tamaño, >50 cualquier riesgo) → `TABLA_60`. Rechazar `numero_trabajadores <= 0` o riesgo inválido con excepción de dominio existente (`DatosEmpresaInvalidosError`) o una específica ligera si se prefiere. |
| `numerales_no_aplican(perfil, mapa) -> frozenset[str]` | Lookup en el mapa. |
| `aplicar_no_aplica_faltantes(autoevaluacion, estandares_por_id, numerales_na) -> None` | Para cada estándar cuyo `numeral ∈ numerales_na` y **aún no** está en `autoevaluacion.calificaciones`, insertar calificación `NO_APLICA` (reutilizar `CalificacionEstandar.calificar`). No modificar calificaciones ya presentes. |
| `calcular_cumplimiento_phva(estandares, calificaciones, perfil, puntaje_total_persistido \| None, finalizada: bool) -> ResumenCumplimientoPHVA` | Agrega por `ciclo_phva` las cuatro fases siempre; usa puntajes reales o 0 si falta calificación; para resumen en vivo, simular aporte `valor_porcentual` de numerales_na sin calificación. |

Dataclasses de resultado (pueden vivir en el mismo módulo o en `perfil_estandares.py`):

- `CumplimientoFasePHVA`: `ciclo_phva`, `peso_maximo: Decimal`, `puntaje_obtenido: Decimal`, `porcentaje_cumplimiento: Decimal`, `brecha: Decimal`
- `ResumenCumplimientoPHVA`: `perfil`, `puntaje_total: Decimal` (provisional o persistido), `umbral_plan_mejora: Decimal = 85`, `requiere_plan_mejora: bool`, `finalizada: bool`, `fases: list[CumplimientoFasePHVA]` (orden fijo PLANEAR → HACER → VERIFICAR → ACTUAR)

**Fórmulas** (por fase):

- `peso_maximo` = Σ `valor_porcentual` de ítems de la fase
- `puntaje_obtenido` = Σ aporte (calificación real, o virtual NO_APLICA si numeral no aplica y falta, o 0 si exigible sin calificar)
- `porcentaje_cumplimiento` = `(puntaje_obtenido / peso_maximo) * 100` si `peso_maximo > 0` else `0`; redondear a 2 decimales con la utilidad existente (`redondear_dos_decimales`)
- `brecha` = `peso_maximo - puntaje_obtenido`
- Invariante: Σ `peso_maximo` de las 4 fases = 100 (sobre el catálogo completo)

Pesos del seed actual: PLANEAR 25 · HACER 60 · VERIFICAR 5 · ACTUAR 10.

#### 2.3 Extensión de `Autoevaluacion` — `src/domain/models/autoevaluacion.py`

- Método de instancia o función de dominio usada por el servicio:
  `aplicar_no_aplica_por_perfil(...)` delegando al motor (evitar duplicar lógica).
- `finalizar` **no** cambia su firma pública sustancialmente; el servicio orquesta: (1) resolver perfil, (2) aplicar NO_APLICA faltantes, (3) `finalizar(total_requerido=len(catalogo))` exigiendo 60 filas tras el auto-relleno.

### Paso 3: Carga del mapa (application / resource)

- Helper `cargar_mapa_perfil_estandares() -> MapaPerfilEstandares` que lee `scripts/datos/perfil_estandares_res312.json` (ruta relativa al repo o `importlib.resources` si se empaqueta). Preferir una sola carga lazy/caché a nivel de módulo o inyección en el servicio.
- El dominio **no** abre archivos en las funciones puras del motor; recibe el `MapaPerfilEstandares` ya construido.

### Paso 4: DTOs y mapper

- **`src/application/dto/respuesta_cumplimiento_phva.py`**
  - `RespuestaCumplimientoFasePHVA`: campos alineados al dataclass (strings Decimal serializados como en el resto del API, o `Decimal` con el mismo patrón que `RespuestaAutoevaluacion`).
  - `RespuestaCumplimientoPHVA`: `autoevaluacion_id`, `empresa_id`, `perfil`, `puntaje_total`, `umbral_plan_mejora`, `requiere_plan_mejora`, `finalizada`, `fases: list[...]`.
- **`src/application/mappers/mapper_cumplimiento_phva.py`**: `a_respuesta(resumen, autoevaluacion_id, empresa_id) -> RespuestaCumplimientoPHVA`.

### Paso 5: Servicio de aplicación

Archivo: `src/application/services/servicio_autoevaluaciones.py`

#### 5.1 Ajuste de `finalizar`

1. Cargar autoevaluación; 404 si no existe.
2. Cargar empresa de `autoevaluacion.empresa_id`; 404 si no existe.
3. `perfil = resolver_perfil_estandares(empresa.nivel_riesgo_arl, empresa.numero_trabajadores)`.
4. Cargar catálogo completo (`listar()`).
5. `aplicar_no_aplica_faltantes(...)` con `numerales_no_aplican(perfil, mapa)`.
6. `autoevaluacion.finalizar(total_requerido=len(estandares))` — sigue exigiendo 60 calificaciones tras el auto-relleno; los exigibles sin calificar → `AutoevaluacionIncompletaError` (409).
7. Persistir y devolver respuesta.

#### 5.2 Nuevo caso de uso `obtener_cumplimiento_phva(autoevaluacion_id: UUID) -> RespuestaCumplimientoPHVA`

1. Cargar autoevaluación + empresa + catálogo (evitar N+1: una lectura de autoevaluación con calificaciones, una de empresa, una lista de estándares).
2. Resolver perfil y mapa.
3. Invocar `calcular_cumplimiento_phva(...)` con `finalizada=autoevaluacion.esta_finalizada`.
4. Si finalizada, preferir `puntaje_total` persistido; si no, usar el provisional del motor.
5. Mapear a DTO.

Inyectar `MapaPerfilEstandares` en el constructor del servicio (o cargarlo en la factoría de `presentation/dependencies/autoevaluacion.py`).

### Paso 6: Router

Archivo: `src/presentation/routers/autoevaluaciones_router.py`

```text
GET /api/v1/autoevaluaciones/{id}/cumplimiento-phva
```

- Auth: `Depends(obtener_usuario_actual)` — lectura permitida a `ADMINISTRADOR`, `AUDITOR_SST` y `CONSULTA` (igual que `GET /{id}`).
- `response_model=RespuestaCumplimientoPHVA`
- Responses: 401, 404 (`AUTOEVALUACION_NO_ENCONTRADA` / `EMPRESA_NO_ENCONTRADA`), 422 si aplica.
- **No** exigir rol escritor.
- Registrar ruta **antes** o junto a `/{id}` de forma que no colisione (path estático `cumplimiento-phva` bajo `/{id}/...` — sin conflicto con rutas actuales).

Actualizar docstring de `finalizar_autoevaluacion` para mencionar el auto-`NO_APLICA` por perfil.

### Paso 7: Excepciones

- Reutilizar:
  - `AutoevaluacionNoEncontradaError` → 404
  - `EmpresaNoEncontradaError` → 404
  - `AutoevaluacionIncompletaError` → 409
  - `AutoevaluacionFinalizadaError` → 409
  - `DatosEmpresaInvalidosError` → 422 (si el resolutor valida riesgo/trabajadores)
- **No** hace falta excepción nueva para “no finalizada” (preview permitido).
- Si el JSON de perfil está corrupto al arrancar: fallar en carga (error de configuración), no en cada request a medias.

### Paso 8: Pruebas

#### Unitarios — `tests/unit/domain/services/test_motor_calificacion_res312.py`

- Perfil: 8 trab. riesgo II → `TABLA_7`; 25 trab. III → `TABLA_21`; 8 trab. IV → `TABLA_60`; 100 trab. I → `TABLA_60`.
- Límites: 10 / 11 / 50 / 51.
- `aplicar_no_aplica_faltantes`: no pisa calificación manual; rellena solo faltantes; aporte = `valor_porcentual`.
- PHVA: todo CUMPLE → % = 100, brecha = 0 por fase; parcial con `Decimal` exacto; suma de `peso_maximo` = 100.
- Preview: exigible sin calificar → aporta 0 a la fase.

#### Unitarios de servicio

- `finalizar` con perfil `TABLA_7` (mapa fixture): tras auto-NO_APLICA, solo exige calificar exigibles; `puntaje_total` correcto; umbral 85.
- `TABLA_60` sin cambio de comportamiento respecto a SP-144 cuando el mapa NA está vacío.

#### Integración — `tests/integration/test_cumplimiento_phva.py`

- `GET .../cumplimiento-phva` → 200 con 4 fases y `perfil`.
- 404 autoevaluación inexistente.
- 401 sin token.
- Rol `CONSULTA` puede leer.
- Opcional: flujo finalizar + GET refleja `finalizada=true` y `puntaje_total` persistido.

### Paso 9: Documentación técnica

- **`ai-specs/specs/api-spec.yml`**: documentar `GET /api/v1/autoevaluaciones/{id}/cumplimiento-phva` (schemas, preview en vivo, códigos de error); actualizar descripción de `POST .../finalizar` (auto-NO_APLICA por perfil).
- **`ai-specs/specs/data-model.md`**: sección de reglas de negocio — resolución de perfil Res. 0312, Art. 27 (`NO_APLICA` = puntaje máximo en ítems no exigibles), referencia al JSON de mapeo; sin cambio de tablas.

## 4. Orden de implementación

1. Paso 0 — Rama `feature/SP-149-backend`
2. Paso 1 — JSON de mapeo (esqueleto + listas; completar TABLA_7/21 antes de merge)
3. Paso 2 — Enum, mapa, motor puro + helpers en `Autoevaluacion`
4. Paso 3 — Carga del mapa / DI
5. Paso 8 (parcial) — Unitarios del motor en rojo → verde (TDD)
6. Paso 5.1 — Ajuste de `finalizar` + unitarios de servicio
7. Paso 4 — DTOs y mapper
8. Paso 5.2 — `obtener_cumplimiento_phva`
9. Paso 6 — Router
10. Paso 7 — Verificar mapeo de excepciones existentes
11. Paso 8 — Integración HTTP
12. Paso 9 — `api-spec.yml` + `data-model.md`

## 5. Checklist de pruebas

- [ ] `pytest` pasa con 0 fallos
- [ ] `pytest --cov --cov-report=html` muestra cobertura ≥ 90 %
- [ ] `GET /api/v1/autoevaluaciones/{id}/cumplimiento-phva` probado manualmente (borrador y finalizada)
- [ ] `POST .../finalizar` con empresa `TABLA_7` / `TABLA_21` / `TABLA_60` (auto-NO_APLICA + incompleta)
- [ ] Casos 401 / 404 / 409 no rotos en autoevaluaciones existentes
- [ ] Ruff + mypy strict sin errores nuevos

## 6. Referencia de tooling

| Propósito | Comando |
|---|---|
| Build | `pip install -r requirements.txt` |
| Test | `pytest` |
| Run | `uvicorn main:app --reload` |
| Coverage | `pytest --cov --cov-report=html` |

## 7. Formato de respuesta de error

Contrato del proyecto (`RespuestaError`):

```json
{
  "exito": false,
  "codigo": "AUTOEVALUACION_NO_ENCONTRADA",
  "mensaje": "Descripción legible en español",
  "detalle": null
}
```

Mapeo HTTP habitual: 401 `TOKEN_INVALIDO` | 403 `ACCESO_DENEGADO` | 404 `*_NO_ENCONTRADA` | 409 `AUTOEVALUACION_INCOMPLETA` / `AUTOEVALUACION_FINALIZADA` | 422 `DATOS_EMPRESA_INVALIDOS` / `ERROR_VALIDACION` | 500 `ERROR_INTERNO`.

## 8. Dependencias

Ninguna librería nueva. Reutilizar `Decimal`, Pydantic v2, FastAPI, pytest/httpx ya presentes.

## 9. Notas

- **Fuente de verdad del cálculo**: backend. El cliente Angular (SP-204) solo visualiza el DTO; no debe reimplementar reglas de perfil ni pesos PHVA.
- **Mapeo TABLA_7 / TABLA_21**: bloqueante de negocio — no mergear con listas vacías “placeholder” sin validación SST / cruce Art. 27. Los tests pueden usar fixtures reducidas independientes del JSON de producción.
- **Idempotencia**: re-finalizar una autoevaluación ya finalizada sigue lanzando `AutoevaluacionFinalizadaError`.
- **RBAC**: escritura en `finalizar` con `requerir_rol_escritor`; lectura PHVA abierta a cualquier usuario autenticado (como el detalle actual).
- **Contrato para SP-204** (frontend): consumir `RespuestaCumplimientoPHVA`; barras = `fases[].porcentaje_cumplimiento`; brecha = `fases[].brecha` y/o `85 - puntaje_total` cuando `finalizada`.
- Commits: conventional commits en el idioma activo del proyecto (`es`), p. ej. `feat(autoevaluacion): añadir cumplimiento PHVA por perfil Res. 0312`.

## 10. Checklist de verificación de implementación

- [ ] Calidad: sin errores de compilación; Ruff/mypy OK; inyección por constructor/`Depends`
- [ ] Dominio: motor puro; invariantes de perfil y Decimal; sin I/O en funciones del motor
- [ ] Application: DTOs Pydantic; orquestación sin SQLAlchemy/FastAPI
- [ ] Presentation: handler fino; validación de path UUID; auth correcta
- [ ] Migraciones: no aplica (sin cambio de esquema)
- [ ] Tests: verdes; cobertura ≥ 90 %; 200/401/404 (/409 en finalizar) cubiertos
- [ ] Documentación: `api-spec.yml` y `data-model.md` actualizados
