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
