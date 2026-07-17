# Modelo de datos — SST Auditor Agent Pro

Este documento describe las entidades persistidas del backend. Se actualiza
en cada ticket que agregue o modifique el esquema.

## Fuente de referencia del dominio

El modelado de cualquier entidad SST debe partir de la referencia normativa
[`.sst-agent-document.md`](../../.sst-agent-document.md) (raíz del repo), que define:

- El ciclo **PHVA** y los componentes del SG-SST (política, objetivos, matriz
  legal, plan anual, COPASST, capacitación).
- La **gestión de peligros y riesgos (GTC 45)**: clasificación de actividades,
  identificación de peligros, cálculo del nivel de riesgo (`NR = NP × NC` con
  sus tablas de ND, NE y NC) y niveles de aceptabilidad.
- La **jerarquía de controles** (eliminación, sustitución, ingeniería,
  administrativos, EPP).
- Las **reglas normativas específicas** (Decreto 1072 de 2015, Resolución 312
  de 2019) con sus artículos y acciones exigidas al agente.

Las entidades, enumeraciones y rangos de valores (por ejemplo, los valores
válidos de ND/NE/NC o los niveles de riesgo I–IV) deben coincidir con las
tablas de ese documento.

---

## Entidad `Usuario`

Representa a un usuario del sistema con credenciales cifradas (nunca
contraseña en claro) y un rol de acceso RBAC.

### Dominio

| Campo | Tipo | Notas |
|---|---|---|
| `id` | `UUID` | Identificador; `None` solo antes de persistir |
| `nombre_completo` | `str` | Obligatorio, no vacío |
| `correo` | `str` | Normalizado a minúsculas; formato validado en dominio |
| `hash_contrasena` | `str` | Hash bcrypt (costo 12); nunca expuesto en DTOs de respuesta |
| `rol` | `RolUsuario` | Ver enum abajo |
| `activo` | `bool` | `false` impide login y refresh |
| `fecha_creacion` | `datetime` | UTC |
| `fecha_actualizacion` | `datetime` | UTC |

Factoría: `Usuario.crear(nombre_completo, correo, hash_contrasena, rol)`.

### Enum `RolUsuario`

| Valor | Uso |
|---|---|
| `ADMINISTRADOR` | Gestión de usuarios y configuración del sistema |
| `AUDITOR_SST` | Acceso a auditorías, información médica ocupacional e índices de siniestralidad |
| `CONSULTA` | Solo lectura de información no sensible |

### Tabla `usuarios` (PostgreSQL / Alembic)

Migración inicial: `alembic/versions/a1b2c3d4e5f6_crear_tabla_usuarios.py`.

| Columna | Tipo SQL | Restricciones |
|---|---|---|
| `id` | `UUID` | PK; generado en aplicación (`uuid4`) |
| `nombre_completo` | `VARCHAR(150)` | NOT NULL |
| `correo` | `VARCHAR(254)` | NOT NULL, UNIQUE (índice único), almacenado en minúsculas |
| `hash_contrasena` | `VARCHAR(72)` | NOT NULL |
| `rol` | `VARCHAR(30)` | NOT NULL (`ADMINISTRADOR` \| `AUDITOR_SST` \| `CONSULTA`) |
| `activo` | `BOOLEAN` | NOT NULL, default `true` |
| `fecha_creacion` | `TIMESTAMPTZ` | NOT NULL, `server_default=now()` |
| `fecha_actualizacion` | `TIMESTAMPTZ` | NOT NULL, `server_default=now()`, `onupdate` |

El esquema de producción se aplica **solo** vía Alembic (`alembic upgrade head`).
`Base.metadata.create_all()` está reservado a pruebas de integración.

---

## Modelo SST — diagrama Entidad-Relación (SP-142)

Modelo del dominio SST que sirve de **contrato para las migraciones Alembic y
entidades de dominio** de los tickets siguientes. Cubre los estándares mínimos
(Res. 312 de 2019), la gestión de peligros y riesgos (GTC 45:2012, anexos A y B)
y el ciclo PHVA, según la referencia normativa `.sst-agent-document.md`.

**Artefacto canónico del diagrama**: [`docs/diagramas/diagrama_er_sst.dbml`](../../docs/diagramas/diagrama_er_sst.dbml)
(fuente DBML, dbdiagram.io) con exportación en
[`docs/diagramas/diagrama_er_sst.svg`](../../docs/diagramas/diagrama_er_sst.svg).
Cualquier desviación futura del esquema debe pasar primero por actualizar el
DBML y este documento.

> Este modelo es de **diseño**: no existen aún tablas, migraciones ni endpoints
> para estas entidades (solo `usuarios` está implementada). Las migraciones se
> crearán en tickets posteriores tomando este diagrama como fuente de verdad.

### Convenciones transversales

- PK `id UUID` generada en aplicación (`uuid4`) en toda entidad, igual que `usuarios`.
- `fecha_creacion` y `fecha_actualizacion` `TIMESTAMPTZ` en UTC en toda tabla.
- Nombres de tablas y columnas en snake_case y en español.
- Campos **derivados** (`nivel_probabilidad`, `nivel_riesgo`,
  `requiere_plan_mejora`) se calculan en dominio; nunca se aceptan del cliente.
- **Borrado lógico** en `evidencias` (`activo` + `fecha_eliminacion`), nunca
  borrado físico: conservación documental 20 años tras el cese laboral
  (D. 1072, Art. 2.2.4.6.13).
- Índices únicos: `empresas.nit`, `usuarios.correo`,
  `calificaciones_estandar (autoevaluacion_id, estandar_id)`,
  `estandares_minimos.numeral`.
- **Extensibilidad Res. 312**: `estandares_minimos` es un catálogo plano que
  soporta las tres tablas (7, 21 y 60 ítems) sin cambio de esquema; el
  subconjunto aplicable a cada empresa se resuelve por reglas de negocio a
  partir de `nivel_riesgo_arl` y `numero_trabajadores`.
- **Exclusión de datos sensibles**: las historias clínicas NO se modelan — su
  custodia es exclusiva de la IPS (referencia §2.2). Solo se modelarían
  metadatos de evaluaciones ocupacionales si se requieren, sin contenido clínico.

### Enumeraciones

| Enum | Valores | Origen normativo |
|---|---|---|
| `nivel_riesgo_arl` | `I \| II \| III \| IV \| V` | Res. 312 (determina tabla de 7, 21 o 60 estándares) |
| `ciclo_phva` | `PLANEAR \| HACER \| VERIFICAR \| ACTUAR` | D. 1072 (ciclo de mejora continua) |
| `resultado_calificacion` | `CUMPLE \| NO_CUMPLE \| NO_APLICA` | Res. 312 (calificación por ítem) |
| `nivel_deficiencia` (ND) | `10 \| 6 \| 2 \| 0` | GTC 45, Anexo A, tabla A.1 (ver decisión D1 sobre el «0») |
| `nivel_exposicion` (NE) | `4 \| 3 \| 2 \| 1` | GTC 45, Anexo A |
| `nivel_consecuencia` (NC) | `100 \| 60 \| 25 \| 10` | GTC 45, Anexo A, tabla A.2 |
| `interpretacion_nr` | `I (600–4000) \| II (150–500) \| III (40–120) \| IV (20)` | GTC 45, Anexo A, tabla A.3 |
| `aceptabilidad_riesgo` | `NO_ACEPTABLE \| ACEPTABLE_CON_CONTROL \| MEJORABLE \| ACEPTABLE` | GTC 45, Anexo A, tabla A.3 |
| `clasificacion_peligro` | `BIOLOGICO \| FISICO \| QUIMICO \| PSICOSOCIAL \| BIOMECANICO \| CONDICIONES_SEGURIDAD \| FENOMENOS_NATURALES` | GTC 45 (tabla de peligros) |
| `tipo_control` | `ELIMINACION \| SUSTITUCION \| INGENIERIA \| ADMINISTRATIVO \| EPP` | GTC 45 / D. 1072 (jerarquía de controles, Anexo B) |
| `origen_accion` | `AUTOEVALUACION \| AUDITORIA \| INVESTIGACION` | Referencia §4 |
| `tipo_accion` | `PREVENTIVA \| CORRECTIVA` | Referencia §4 |
| `estado_plan_mejoramiento` | `ABIERTO \| EN_EJECUCION \| CERRADO` | Propuesto (no normativo — validar, decisión D6) |
| `estado_accion_mejora` | `PENDIENTE \| EN_CURSO \| COMPLETADA \| VERIFICADA` | Propuesto (no normativo — validar, decisión D6) |
| `tipo_hallazgo` | `NO_CONFORMIDAD \| OBSERVACION \| OPORTUNIDAD_MEJORA` | Propuesto (no normativo — validar, decisión D6) |

El enum `RolUsuario` de la entidad existente `Usuario` se documenta arriba y no
se modifica en este modelo.

### Entidades

Todas incluyen `id UUID` (PK), `fecha_creacion` y `fecha_actualizacion`
(`TIMESTAMPTZ`, UTC); esas columnas no se repiten en las tablas siguientes.

#### `empresas` — Res. 312 de 2019

| Columna | Tipo | Restricciones |
|---|---|---|
| `razon_social` | `VARCHAR(200)` | NOT NULL |
| `nit` | `VARCHAR(20)` | NOT NULL, UNIQUE |
| `actividad_economica` | `VARCHAR(200)` | NOT NULL |
| `nivel_riesgo_arl` | `nivel_riesgo_arl` | NOT NULL |
| `numero_trabajadores` | `INTEGER` | NOT NULL, > 0 |

El nivel de riesgo ARL y el número de trabajadores determinan qué tabla de
estándares mínimos aplica (7, 21 o 60 ítems) — regla de negocio, no de esquema.

#### `estandares_minimos` — Res. 312 de 2019 (catálogo)

| Columna | Tipo | Restricciones |
|---|---|---|
| `ciclo_phva` | `ciclo_phva` | NOT NULL |
| `numeral` | `VARCHAR(20)` | NOT NULL, UNIQUE (p. ej. `1.1.1`) |
| `descripcion` | `TEXT` | NOT NULL |
| `valor_porcentual` | `NUMERIC(5,2)` | NOT NULL (peso del ítem en la tabla de valores) |

#### `autoevaluaciones` — Res. 312 / D. 1072 (evaluación inicial)

| Columna | Tipo | Restricciones |
|---|---|---|
| `empresa_id` | `UUID` | NOT NULL, FK → `empresas.id` |
| `usuario_id` | `UUID` | NOT NULL, FK → `usuarios.id` (quien evalúa) |
| `fecha` | `DATE` | NOT NULL |
| `puntaje_total` | `NUMERIC(5,2)` | NULL mientras esté en curso |
| `requiere_plan_mejora` | `BOOLEAN` | NOT NULL, **derivado**: `puntaje_total < 85` |

Puntaje total < 85 % obliga a plan de mejoramiento con reporte a la ARL
(referencia §4).

#### `calificaciones_estandar` — Res. 312 (tabla intermedia N—N)

Tabla intermedia **nombrada** de la relación N—N
`autoevaluaciones ↔ estandares_minimos`.

| Columna | Tipo | Restricciones |
|---|---|---|
| `autoevaluacion_id` | `UUID` | NOT NULL, FK → `autoevaluaciones.id` |
| `estandar_id` | `UUID` | NOT NULL, FK → `estandares_minimos.id` |
| `resultado` | `resultado_calificacion` | NOT NULL |
| `puntaje` | `NUMERIC(5,2)` | NOT NULL (CUMPLE y NO_APLICA otorgan el valor del ítem; NO_CUMPLE otorga 0) |
| `observaciones` | `TEXT` | NULL |

Índice único: `(autoevaluacion_id, estandar_id)`.

#### `procesos_actividades` — GTC 45 §2.1 (paso 1)

| Columna | Tipo | Restricciones |
|---|---|---|
| `empresa_id` | `UUID` | NOT NULL, FK → `empresas.id` |
| `nombre` | `VARCHAR(150)` | NOT NULL |
| `es_rutinaria` | `BOOLEAN` | NOT NULL |
| `zona_lugar` | `VARCHAR(150)` | NULL |

#### `peligros` — GTC 45 §2.1 (paso 2)

| Columna | Tipo | Restricciones |
|---|---|---|
| `proceso_actividad_id` | `UUID` | NOT NULL, FK → `procesos_actividades.id` |
| `clasificacion` | `clasificacion_peligro` | NOT NULL |
| `descripcion` | `TEXT` | NOT NULL |
| `efectos_posibles` | `TEXT` | NULL |

#### `evaluaciones_riesgo` — GTC 45, Anexo A

| Columna | Tipo | Restricciones |
|---|---|---|
| `peligro_id` | `UUID` | NOT NULL, FK → `peligros.id` |
| `nivel_deficiencia` | `nivel_deficiencia` | NOT NULL, ND ∈ {10, 6, 2, 0} |
| `nivel_exposicion` | `nivel_exposicion` | NOT NULL, NE ∈ {4, 3, 2, 1} |
| `nivel_consecuencia` | `nivel_consecuencia` | NOT NULL, NC ∈ {100, 60, 25, 10} |
| `nivel_probabilidad` | `SMALLINT` | NOT NULL, **derivado**: `NP = ND × NE` (2–40) |
| `nivel_riesgo` | `INTEGER` | NOT NULL, **derivado**: `NR = NP × NC` (20–4000) |
| `interpretacion_nr` | `interpretacion_nr` | NOT NULL (I–IV) |
| `aceptabilidad` | `aceptabilidad_riesgo` | NOT NULL |

Interpretación de NP: Muy Alto (24–40), Alto (10–20), Medio (6–8), Bajo (2–4).

#### `controles_riesgo` — GTC 45 / D. 1072 (jerarquía de controles)

| Columna | Tipo | Restricciones |
|---|---|---|
| `evaluacion_riesgo_id` | `UUID` | NOT NULL, FK → `evaluaciones_riesgo.id` |
| `tipo` | `tipo_control` | NOT NULL |
| `descripcion` | `TEXT` | NOT NULL |

#### `auditorias` — Referencia §3 (Verificar)

| Columna | Tipo | Restricciones |
|---|---|---|
| `empresa_id` | `UUID` | NOT NULL, FK → `empresas.id` |
| `auditor_id` | `UUID` | NOT NULL, FK → `usuarios.id` (rol `AUDITOR_SST`) |
| `fecha` | `DATE` | NOT NULL |
| `alcance` | `TEXT` | NOT NULL |

Auditoría anual interna, planificada con el COPASST.

#### `hallazgos` — Referencia §3

| Columna | Tipo | Restricciones |
|---|---|---|
| `auditoria_id` | `UUID` | NOT NULL, FK → `auditorias.id` |
| `tipo` | `tipo_hallazgo` | NOT NULL |
| `descripcion` | `TEXT` | NOT NULL |

#### `planes_mejoramiento` — Referencia §4 / Res. 312

| Columna | Tipo | Restricciones |
|---|---|---|
| `empresa_id` | `UUID` | NOT NULL, FK → `empresas.id` |
| `autoevaluacion_id` | `UUID` | NULL, FK → `autoevaluaciones.id` (presente si el plan lo origina una autoevaluación < 85 %) |
| `estado` | `estado_plan_mejoramiento` | NOT NULL, default `ABIERTO` |
| `reportado_arl` | `BOOLEAN` | NOT NULL, default `false` |

#### `acciones_mejora` — Referencia §4

| Columna | Tipo | Restricciones |
|---|---|---|
| `plan_mejoramiento_id` | `UUID` | NOT NULL, FK → `planes_mejoramiento.id` |
| `responsable_id` | `UUID` | NOT NULL, FK → `usuarios.id` |
| `origen` | `origen_accion` | NOT NULL |
| `tipo` | `tipo_accion` | NOT NULL |
| `descripcion` | `TEXT` | NOT NULL |
| `fecha_limite` | `DATE` | NOT NULL |
| `estado` | `estado_accion_mejora` | NOT NULL, default `PENDIENTE` |

#### `evidencias` — D. 1072, Art. 2.2.4.6.13

| Columna | Tipo | Restricciones |
|---|---|---|
| `calificacion_estandar_id` | `UUID` | NULL, FK → `calificaciones_estandar.id` |
| `accion_mejora_id` | `UUID` | NULL, FK → `acciones_mejora.id` |
| `usuario_id` | `UUID` | NOT NULL, FK → `usuarios.id` (quien carga) |
| `nombre_archivo` | `VARCHAR(255)` | NOT NULL |
| `tipo_mime` | `VARCHAR(100)` | NOT NULL |
| `ruta_almacenamiento` | `VARCHAR(500)` | NOT NULL |
| `fecha_carga` | `TIMESTAMPTZ` | NOT NULL |
| `activo` | `BOOLEAN` | NOT NULL, default `true` (borrado lógico) |
| `fecha_eliminacion` | `TIMESTAMPTZ` | NULL mientras esté activa |

Regla (CHECK en la implementación): **al menos una** de las dos FK opcionales
(`calificacion_estandar_id`, `accion_mejora_id`) debe estar presente. Nunca
borrado físico (conservación 20 años tras el cese laboral).

### Relaciones (cardinalidad)

| Relación | Cardinalidad |
|---|---|
| `empresas` → `autoevaluaciones` | 1—N |
| `empresas` → `procesos_actividades` | 1—N |
| `empresas` → `auditorias` | 1—N |
| `empresas` → `planes_mejoramiento` | 1—N |
| `autoevaluaciones` ↔ `estandares_minimos` | N—N vía `calificaciones_estandar` (tabla intermedia nombrada) |
| `procesos_actividades` → `peligros` | 1—N |
| `peligros` → `evaluaciones_riesgo` | 1—N |
| `evaluaciones_riesgo` → `controles_riesgo` | 1—N |
| `auditorias` → `hallazgos` | 1—N |
| `autoevaluaciones` → `planes_mejoramiento` | 1—N (FK opcional en el plan) |
| `planes_mejoramiento` → `acciones_mejora` | 1—N |
| `calificaciones_estandar` → `evidencias` | 1—N (FK opcional) |
| `acciones_mejora` → `evidencias` | 1—N (FK opcional) |
| `usuarios` → `autoevaluaciones` | 1—N (evaluador) |
| `usuarios` → `evidencias` | 1—N (quien carga) |
| `usuarios` → `auditorias` | 1—N (auditor) |
| `usuarios` → `acciones_mejora` | 1—N (responsable) |

`usuarios` participa en el modelo **sin modificarse**: cualquier cambio sobre
esa entidad sería un ticket aparte.

### Decisiones de validación (acta — SP-183)

**Estado: PENDIENTE de sesión con el responsable de SST.** Las decisiones
siguientes son la propuesta técnica llevada a la sesión; cada una debe
confirmarse o ajustarse por escrito aquí (fecha, participantes y decisión
final por punto). Hasta entonces, el diagrama refleja la propuesta.

| # | Punto de agenda | Propuesta llevada a la sesión | Decisión final |
|---|---|---|---|
| D1 | ND nivel «Bajo»: la tabla A.1 de GTC 45 no le asigna valor («—»), pero el ticket define ND ∈ {10, 6, 2, 0} | Modelar `0` como convención de aplicación (opción a), documentado en el enum; alternativa: columna anulable (opción b) | _Pendiente_ |
| D2 | Cobertura del catálogo de estándares (tablas de 7, 21 y 60 ítems) y umbral del 85 % | Catálogo plano `estandares_minimos` + `requiere_plan_mejora` derivado de `puntaje_total < 85` | _Pendiente_ |
| D3 | Valores/rangos ND, NE, NC y niveles I–IV vs. práctica real del auditor | Valores exactos de los anexos A.1–A.3 de la referencia | _Pendiente_ |
| D4 | Tipos y asociaciones de evidencias | Metadatos de archivo + FKs opcionales a `calificaciones_estandar` y `acciones_mejora` (al menos una presente); borrado lógico | _Pendiente_ |
| D5 | Exclusión de historias clínicas | No se persisten; custodia exclusiva de la IPS (referencia §2.2) | _Pendiente_ |
| D6 | Ciclo de vida de la autoevaluación (¿una por año por empresa?, ¿se versiona?) y enums de estado propuestos (`estado_plan_mejoramiento`, `estado_accion_mejora`, `tipo_hallazgo`) | Múltiples autoevaluaciones por empresa (histórico por `fecha`), sin versionado; enums de estado propuestos no normativos | _Pendiente_ |
