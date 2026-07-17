# Plan de implementación backend: SP-142 Diseñar diagrama Entidad-Relación completo SST

## 1. Resumen

Diseñar el diagrama Entidad-Relación (ER) completo del dominio SST, que servirá de
**contrato para todas las migraciones Alembic y entidades de dominio** de los tickets
siguientes. El modelo cubre los estándares mínimos (Resolución 312 de 2019), la gestión
de peligros y riesgos (GTC 45:2012, anexos A y B) y el ciclo PHVA, tomando como fuente
de verdad la referencia normativa `.sst-agent-document.md` (raíz del repo) y el modelo
existente de `ai-specs/specs/data-model.md`.

**Naturaleza del ticket**: diseño y documentación. **No** se crean tablas, migraciones,
modelos SQLAlchemy ni endpoints. Los entregables son artefactos versionables:

1. `docs/diagramas/diagrama_er_sst.dbml` — fuente DBML (dbdiagram.io).
2. `docs/diagramas/diagrama_er_sst.png` (o `.svg`) — exportación para stakeholders.
3. `ai-specs/specs/data-model.md` actualizado con entidades, enums, relaciones y la
   sección «Decisiones de validación».

Stack activo: `python-fastapi` (Python 3.12 + FastAPI). El stack solo condiciona las
convenciones del modelo (PK UUID generada en aplicación, `TIMESTAMPTZ` UTC, snake_case
en español), no hay código que escribir.

## Estimación de puntos de historia

<!-- STORY_POINTS:5 -->
- **HU total**: 5 (Fibonacci: 1, 2, 3, 5, 8, 13)
- **Justificación**: se confirma la estimación de 5 puntos ya registrada en Jira.
  Modelado de ~14 entidades con reglas normativas estrictas (valores discretos de
  ND/NE/NC, niveles I–IV, jerarquía de controles, umbral del 85 %), trazabilidad
  normativa por tabla, diagramación en DBML y una sesión de validación con el
  responsable de SST. Sin código ni migraciones, pero con alta carga de análisis
  y riesgo de re-trabajo si la validación pide ajustes (absorbido por SP-183).
- **Subtareas**:
  | Subtarea | Puntos | Nota |
  |---|---|---|
  | SP-181 | 3 | Inventario de entidades, atributos, enums y relaciones desde la norma |
  | SP-182 | 2 | Transcripción a DBML + exportación PNG/SVG |
  | SP-183 | 1 | Sesión de validación + registro de decisiones y ajustes |

  La suma de subtareas (6) supera en 1 la HU (5); es aceptable porque la estimación
  de la HU descuenta el solapamiento entre SP-181 y SP-182 (el inventario es insumo
  directo del DBML). No se propone ajuste en Jira.
<!-- /STORY_POINTS -->

## 2. Contexto de arquitectura

- Stack activo: `python-fastapi` (`Python 3.12 + FastAPI`)
- Capas involucradas: **ninguna capa de código**. Los archivos afectados son solo
  de documentación:

| Capa | Archivos afectados |
|---|---|
| Documentación (diagramas) | `docs/diagramas/diagrama_er_sst.dbml` (crear), `docs/diagramas/diagrama_er_sst.png` (crear) |
| Documentación (specs) | `ai-specs/specs/data-model.md` (modificar) |

El directorio `docs/` no existe aún en el repo; este ticket lo crea con la
subcarpeta `diagramas/`.

Las capas `domain/`, `application/`, `presentation/` e `infrastructure/` **no se
tocan**. Las entidades de dominio y migraciones Alembic derivadas de este diagrama
se implementarán en tickets posteriores.

### Mapeo de subtareas

| Clave | Resumen | Pasos del plan |
|---|---|---|
| `SP-181` | Levantar entidades y relaciones del dominio SST | Paso 1, Paso 2 |
| `SP-182` | Construir diagrama ER en herramienta de modelado | Paso 3, Paso 4 |
| `SP-183` | Validar el modelo con stakeholders del proyecto | Paso 5, Paso 6 |

## 3. Pasos de implementación

### Paso 0: Crear la rama de trabajo
- **Acción**: crear y cambiar a una nueva rama de feature
- **Rama**: `feature/SP-142-backend`
- **Comandos**:
  ```bash
  git checkout develop && git pull origin develop
  git checkout -b feature/SP-142-backend
  ```
  > Nota: en este repo las ramas de feature parten de `develop` (no de `main`),
  > coherente con los PRs previos (SP-141, SP-180).

### Paso 1: Levantar el inventario de entidades y enums (SP-181)
- **Archivo**: borrador estructurado como sección nueva de `ai-specs/specs/data-model.md`
  (sección «Modelo SST — inventario de entidades», que el Paso 4 consolidará).
- **Acción**: recorrer las cuatro fases PHVA de `.sst-agent-document.md` y extraer
  los conceptos persistibles. Para cada entidad definir: nombre de tabla (snake_case,
  español), atributos con tipo y obligatoriedad, enums con valores exactos y
  relaciones con cardinalidad.
- **Entidades del alcance (14)**, con su origen normativo:

  | Entidad (tabla) | Origen normativo |
  |---|---|
  | `usuarios` (existente — se integra sin rediseñar) | SP-140 / data-model.md |
  | `empresas` | Res. 312 (tamaño y nivel de riesgo determinan la tabla de estándares) |
  | `estandares_minimos` | Res. 312 (catálogo por ciclo PHVA, numeral, valor porcentual) |
  | `autoevaluaciones` | Res. 312 + D. 1072 (evaluación inicial / línea base) |
  | `calificaciones_estandar` | Res. 312 (CUMPLE \| NO_CUMPLE \| NO_APLICA + puntaje) |
  | `planes_mejoramiento` | Res. 312 / referencia §4 (obligatorio si puntaje < 85 %, reporte a ARL) |
  | `acciones_mejora` | Referencia §4 (preventivas / correctivas; origen: autoevaluación, auditoría, investigación) |
  | `procesos_actividades` | GTC 45 §2.1 (rutinaria / no rutinaria) |
  | `peligros` | GTC 45 §2.1 (clasificación GTC 45) |
  | `evaluaciones_riesgo` | GTC 45 Anexo A (ND, NE, NC, NP, NR, interpretación, aceptabilidad) |
  | `controles_riesgo` | GTC 45 / D. 1072 Anexo B (jerarquía de controles) |
  | `evidencias` | D. 1072, Art. 2.2.4.6.13 (conservación documental 20 años → borrado lógico) |
  | `auditorias` | Referencia §3 (auditoría anual interna) |
  | `hallazgos` | Referencia §3 (resultado de auditoría) |

- **Enums a documentar con valores exactos del anexo A y B**:
  - `ciclo_phva`: `PLANEAR | HACER | VERIFICAR | ACTUAR`
  - `resultado_calificacion`: `CUMPLE | NO_CUMPLE | NO_APLICA`
  - `nivel_deficiencia` (ND): `10 | 6 | 2` + caso «Bajo» (ver conflicto en §9)
  - `nivel_exposicion` (NE): `4 | 3 | 2 | 1`
  - `nivel_consecuencia` (NC): `100 | 60 | 25 | 10`
  - `interpretacion_nr`: `I | II | III | IV` (I: 600–4000, II: 150–500, III: 40–120, IV: 20)
  - `aceptabilidad`: `NO_ACEPTABLE | ACEPTABLE_CON_CONTROL | MEJORABLE | ACEPTABLE`
  - `tipo_control`: `ELIMINACION | SUSTITUCION | INGENIERIA | ADMINISTRATIVO | EPP`
  - `origen_accion`: `AUTOEVALUACION | AUDITORIA | INVESTIGACION`
  - `tipo_accion`: `PREVENTIVA | CORRECTIVA`
  - `nivel_riesgo_arl` (empresa): `I | II | III | IV | V`
- **Campos derivados** (documentar como calculados, no editables):
  `nivel_probabilidad = ND × NE`, `nivel_riesgo = NP × NC`,
  `requiere_plan_mejora = puntaje_total < 85`.
- **Relaciones clave con cardinalidad** (todas 1—N salvo indicación):
  - `empresas` 1—N `autoevaluaciones`, 1—N `procesos_actividades`, 1—N `auditorias`
  - `autoevaluaciones` 1—N `calificaciones_estandar` N—1 `estandares_minimos`
    (la tabla intermedia nombrada de la relación N—N autoevaluación↔estándar es
    `calificaciones_estandar`)
  - `procesos_actividades` 1—N `peligros` 1—N `evaluaciones_riesgo` 1—N `controles_riesgo`
  - `auditorias` 1—N `hallazgos`; `planes_mejoramiento` 1—N `acciones_mejora`
  - `evidencias` N—1 opcional a `calificaciones_estandar` y N—1 opcional a
    `acciones_mejora` (con regla: al menos una FK presente)
  - `usuarios` participa como: evaluador (`autoevaluaciones.usuario_id`), cargador
    (`evidencias.usuario_id`), auditor (`auditorias.auditor_id`) y responsable
    (`acciones_mejora.responsable_id`) — **sin modificar la entidad existente**
- **Exclusiones documentadas**: las historias clínicas NO se modelan (custodia
  exclusiva de la IPS, referencia §2.2); solo metadatos de evaluaciones
  ocupacionales si llegaran a requerirse, sin contenido clínico.

### Paso 2: Definir convenciones transversales del modelo (SP-181)
- **Acción**: fijar en el borrador las reglas que aplican a toda entidad:
  - PK `id UUID` generada en aplicación (`uuid4`), igual que `usuarios`.
  - `fecha_creacion` y `fecha_actualizacion` `TIMESTAMPTZ` UTC en todas las tablas.
  - Borrado lógico en `evidencias` (y entidades con retención normativa):
    `activo BOOLEAN` + `fecha_eliminacion TIMESTAMPTZ NULL` — nunca borrado físico
    (D. 1072, Art. 2.2.4.6.13: conservación 20 años tras el cese laboral).
  - Índice único en `empresas.nit`.
  - Extensibilidad Res. 312: `estandares_minimos` es catálogo plano que soporta las
    tres tablas (7, 21 y 60 ítems) sin cambio de esquema — el subconjunto aplicable
    se resuelve por reglas de negocio a partir de `empresas.nivel_riesgo_arl` y
    `empresas.numero_trabajadores`, no por esquema.

### Paso 3: Construir el diagrama DBML (SP-182)
- **Archivo**: `docs/diagramas/diagrama_er_sst.dbml` — Crear
- **Contenido**:
  - `Enum` de DBML para cada enum del Paso 1.
  - `Table` por cada una de las 14 entidades, incluida `usuarios` con sus columnas
    actuales exactas (tomadas de `data-model.md` / migración `a1b2c3d4e5f6`).
  - `Ref` con cardinalidad explícita para todas las relaciones; ninguna FK puede
    apuntar a una tabla inexistente.
  - `Note` por tabla citando el origen normativo (numeral Res. 312, anexo GTC 45
    o artículo del D. 1072), según la tabla del Paso 1 — requisito de trazabilidad.
  - Índices: `unique` en `empresas.nit` y `usuarios.correo`.
- **Verificación antes de comitear**: el DBML debe compilar sin errores. Opciones:
  pegarlo en dbdiagram.io, o validarlo localmente con `@dbml/cli`
  (`npx -y @dbml/cli dbml2sql docs/diagramas/diagrama_er_sst.dbml -o /tmp/er.sql`
  — si genera SQL sin error, compila).

### Paso 4: Exportar imagen y actualizar data-model.md (SP-182)
- **Archivos**:
  - `docs/diagramas/diagrama_er_sst.png` (o `.svg`) — Crear. Exportación desde
    dbdiagram.io (paso manual: importar el `.dbml`, exportar imagen, guardar en
    el repo).
  - `ai-specs/specs/data-model.md` — Modificar. Consolidar el inventario del
    Paso 1 como secciones nuevas: entidades SST (tabla de campos por entidad),
    enums con valores exactos, relaciones con cardinalidad, convenciones
    transversales y exclusiones. Referenciar la fuente DBML
    (`docs/diagramas/diagrama_er_sst.dbml`) como artefacto canónico del diagrama.
- **Regla de sincronización**: toda entidad del DBML debe aparecer en
  `data-model.md` y viceversa (verificación cruzada del Paso 7).

### Paso 5: Sesión de validación con el responsable de SST (SP-183)
- **Acción**: sesión usando la exportación PNG/SVG. Agenda mínima (los cinco
  puntos deben confirmarse explícitamente):
  1. El catálogo de estándares mínimos cubre las tres tablas de la Res. 312
     (7, 21 y 60 ítems) y la regla del umbral del 85 % para el plan de mejoramiento.
  2. Los valores/rangos de ND, NE, NC y niveles I–IV coinciden con la práctica
     real del auditor (GTC 45) — incluir aquí la resolución del conflicto ND
     «Bajo» descrito en §9.
  3. Tipos de evidencia reales (formatos, tamaños esperados) y entidades a las
     que deben poder asociarse.
  4. Confirmación de la exclusión de historias clínicas (custodia de la IPS).
  5. Ciclo de vida de la autoevaluación: ¿una por año por empresa o múltiples?
     ¿Se versionan?

### Paso 6: Registrar decisiones y aplicar ajustes (SP-183)
- **Archivos**:
  - `ai-specs/specs/data-model.md` — agregar sección «Decisiones de validación»
    (acta breve: fecha, participantes, decisiones por punto de agenda, ajustes
    acordados).
  - `docs/diagramas/diagrama_er_sst.dbml` y la exportación PNG/SVG — aplicar los
    ajustes acordados, re-validar compilación y re-exportar.

### Paso 7: Verificación de calidad del entregable
No aplica pruebas de código (ticket de diseño). Verificaciones manuales:
- El DBML compila sin errores (dbdiagram.io o `@dbml/cli`).
- Cada FK del diagrama apunta a una PK existente; no hay entidades huérfanas ni
  relaciones sin cardinalidad.
- Los valores de los enums coinciden con las tablas de los anexos A y B de
  `.sst-agent-document.md` (revisión cruzada manual).
- `ai-specs/specs/data-model.md` referencia todas las entidades del DBML y
  viceversa (sin desincronización).
- Toda entidad tiene PK UUID, `fecha_creacion` y `fecha_actualizacion`, y las
  tablas/columnas están en snake_case y en español.

### Paso 8: Actualizar documentación técnica
- `ai-specs/specs/data-model.md` — ya cubierto en los Pasos 4 y 6 (es el
  entregable principal).
- `ai-specs/specs/api-spec.yml` — **no aplica** (sin endpoints).
- Estándares de stack — **no aplica** (sin librerías ni patrones nuevos).

## 4. Orden de implementación

1. Paso 0 — Crear rama `feature/SP-142-backend`
2. Paso 1 — Inventario de entidades, enums y relaciones (SP-181)
3. Paso 2 — Convenciones transversales del modelo (SP-181)
4. Paso 3 — Construir `diagrama_er_sst.dbml` y validar compilación (SP-182)
5. Paso 4 — Exportar PNG/SVG y consolidar `data-model.md` (SP-182)
6. Paso 5 — Sesión de validación con responsable de SST (SP-183)
7. Paso 6 — Registrar decisiones y aplicar ajustes (SP-183)
8. Paso 7 — Verificación de calidad del entregable
9. Paso 8 — Cierre de documentación

## 5. Checklist de pruebas

Verificación posterior (adaptada: ticket sin código):
- [ ] `pytest` sigue pasando con 0 fallos (la suite existente no debe romperse;
      este ticket no toca código, ejecutar como humo de regresión)
- [ ] El DBML compila sin errores en dbdiagram.io o con `@dbml/cli`
- [ ] Ninguna FK apunta a tabla inexistente; todas las relaciones tienen cardinalidad
- [ ] Enums cotejados 1:1 contra los anexos A y B de `.sst-agent-document.md`
- [ ] `data-model.md` y el DBML sincronizados (mismas entidades en ambos)
- [ ] Fuente DBML y exportación PNG/SVG comiteadas
- [ ] Sección «Decisiones de validación» diligenciada tras la sesión SP-183

## 6. Referencia de herramientas

Comandos resueltos de `openspec/config.yaml` para el stack activo:

| Propósito | Comando |
|---|---|
| Build | `pip install -r requirements.txt` |
| Test | `pytest` |
| Run | `uvicorn main:app --reload` |
| Lint | `ruff check .` |
| Coverage | `pytest --cov --cov-report=html` |

Herramienta adicional de este ticket (opcional, sin agregar a requirements):
validación local de DBML con `npx -y @dbml/cli`.

## 7. Formato de respuesta de error

No aplica en este ticket (no se exponen endpoints). Se conserva la referencia
del proyecto para los tickets que implementen el modelo:

```json
{
  "success": false,
  "code": "CODIGO_ERROR",
  "message": "Descripción legible",
  "details": ["campo: mensaje de validación"]
}
```
Mapeo HTTP: 400 VALIDATION_ERROR | 404 NOT_FOUND | 409 CONFLICT | 422 BUSINESS_RULE_VIOLATION | 500 INTERNAL_ERROR

## 8. Dependencias

Ninguna dependencia nueva de Python. Herramientas de diagramación:
- **dbdiagram.io** (web, sin instalación) — edición y exportación PNG/SVG.
- **`@dbml/cli`** (opcional, vía `npx`, requiere Node.js) — validación local del
  DBML sin salir de la terminal.

## 9. Notas

- **Conflicto normativo a resolver en SP-183 (marcar, no adivinar)**: el ticket
  define `nivel_deficiencia ∈ {10, 6, 2, 0}`, pero la tabla A.1 de
  `.sst-agent-document.md` asigna al nivel «Bajo» el valor «—» (sin valor
  numérico; en GTC 45 el nivel Bajo no puntúa y el riesgo se considera
  controlado). Opciones a validar con el responsable de SST: (a) modelar `0`
  como convención de aplicación, o (b) columna anulable / registro sin
  evaluación. La decisión queda en «Decisiones de validación».
- **Umbral 85 %**: `requiere_plan_mejora` es derivado (`puntaje_total < 85`);
  el plan de mejoramiento con reporte a la ARL es obligatorio bajo ese umbral
  (Res. 312 / referencia §4).
- **Campos calculados**: `nivel_probabilidad` (ND × NE) y `nivel_riesgo`
  (NP × NC) se documentan como derivados; en la implementación futura se
  calcularán en dominio, nunca aceptados del cliente.
- **Datos sensibles**: sin entidad de historia clínica; custodia exclusiva de la
  IPS (referencia §2.2).
- **Conservación documental**: borrado lógico obligatorio en `evidencias`
  (D. 1072, Art. 2.2.4.6.13 — 20 años tras el cese laboral).
- **`usuarios` es inmutable en este ticket**: se integra al diagrama tal cual
  está; cualquier cambio que la validación sugiera sobre ella sería un ticket
  aparte.
- **Paso manual**: la exportación PNG/SVG desde dbdiagram.io no es
  automatizable desde la CLI; quien implemente debe hacerla a mano y comitear
  el archivo.
- Este diagrama es la **fuente de verdad** de las migraciones Alembic de los
  tickets siguientes; cualquier desviación futura debe pasar por actualizar
  primero el DBML y `data-model.md`.

## 10. Checklist de verificación de implementación

Adaptado a un ticket de diseño (sin código):
- [ ] Calidad: DBML compila sin errores; nombres snake_case en español coherentes con `usuarios`
- [ ] Dominio: invariantes normativas capturadas (enums exactos de anexos A y B, umbral 85 %, jerarquía de controles)
- [ ] Trazabilidad: cada tabla del DBML tiene `Note` con su origen normativo
- [ ] Relaciones: cardinalidad explícita en todas; N—N con tabla intermedia nombrada; sin entidades huérfanas
- [ ] Convenciones: PK UUID, `fecha_creacion`/`fecha_actualizacion` TIMESTAMPTZ UTC en toda entidad; borrado lógico en evidencias
- [ ] Migraciones: **ninguna creada** (fuera de alcance — verificar que `alembic/versions/` no cambió)
- [ ] Documentación: `data-model.md` sincronizado con el DBML y con la sección «Decisiones de validación» diligenciada
- [ ] Validación: sesión con responsable de SST realizada y los cinco puntos de agenda confirmados por escrito
