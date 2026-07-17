# SP-180 — Crear migración base inicial (verificación del ciclo de vida)

> **Naturaleza del ticket**: la migración base `a1b2c3d4e5f6_crear_tabla_usuarios.py`
> ya existía (entregada con SP-140) y es inmutable. Este ticket NO agrega ni modifica
> archivos en `alembic/versions/`; su entregable es la **verificación formal** del
> ciclo de vida de la migración contra un PostgreSQL real y este registro de evidencia.

## Contexto de ejecución

- Fecha: 2026-07-16
- Rama: `feature/SP-180-backend`
- Motor: PostgreSQL 16 (imagen `postgres:16-alpine`) en contenedor Docker efímero,
  puerto local 5433, credenciales/BD idénticas a las del `.env` (`postgres` /
  `sst_auditor`).
- Nota: el `docker-compose.yml` previsto por SP-178 aún no existe en el repo
  (SP-178 sin implementar). Para no invadir ese alcance, la verificación usó un
  contenedor equivalente levantado con `docker run`; los resultados son
  independientes del mecanismo de arranque del contenedor.

```powershell
docker run -d --name sp180-postgres-verif `
  -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=administrator `
  -e POSTGRES_DB=sst_auditor -p 5433:5432 postgres:16-alpine
$env:URL_BASE_DATOS = 'postgresql+asyncpg://postgres:administrator@localhost:5433/sst_auditor'
```

## Evidencia por criterio de aceptación

### 1. `alembic upgrade head` sobre BD limpia

```
INFO  [alembic.runtime.migration] Running upgrade  -> a1b2c3d4e5f6, Crea la tabla `usuarios` ...
$ alembic current
a1b2c3d4e5f6 (head)
```

Esquema resultante (`\d usuarios`):

```
 id                  | uuid                     | not null |
 nombre_completo     | character varying(150)   | not null |
 correo              | character varying(254)   | not null |
 hash_contrasena     | character varying(72)    | not null |
 rol                 | character varying(30)    | not null |
 activo              | boolean                  | not null | true
 fecha_creacion      | timestamp with time zone | not null | now()
 fecha_actualizacion | timestamp with time zone | not null | now()
Indexes:
    "usuarios_pkey" PRIMARY KEY, btree (id)
    "ix_usuarios_correo" UNIQUE, btree (correo)
```

✅ Tabla `usuarios` creada con PK UUID, índice único `ix_usuarios_correo`,
`activo` con default `true` y timestamps `TIMESTAMPTZ` con `now()`.

### 2. Ciclo `downgrade base` → `upgrade head`

```
INFO  [alembic.runtime.migration] Running downgrade a1b2c3d4e5f6 -> , ...
```

Estado tras el downgrade — solo queda `alembic_version` (vacía) y su PK; sin
residuos de tabla ni índice:

```
 table_name      : alembic_version
 indexname       : alembic_version_pkc
 alembic_version : (0 rows)
```

Re-aplicación:

```
INFO  [alembic.runtime.migration] Running upgrade  -> a1b2c3d4e5f6, ...
$ alembic current
a1b2c3d4e5f6 (head)
```

✅ Ciclo idempotente sin errores ni residuos de esquema.

### 3. Seed del administrador sobre el esquema migrado

```
$ python -m scripts.crear_usuario_admin
INFO:__main__:Usuario administrador john.aragon@sst-innova.com creado correctamente
$ python -m scripts.crear_usuario_admin   # segunda ejecución
INFO:__main__:El usuario administrador john.aragon@sst-innova.com ya existe; no se duplica
```

Fila persistida:

```
 correo                     | rol           | activo | long_hash | tiene_fecha
 john.aragon@sst-innova.com | ADMINISTRADOR | t      | 60        | t
```

✅ Seed end-to-end funcional e idempotente contra la BD real (hash bcrypt de 60
caracteres, timestamps poblados por el `server_default`).

### 4. `ai-specs/specs/data-model.md` vs esquema real

La tabla documentada (columnas, tipos SQL, restricciones, índice único y
defaults) coincide columna a columna con el esquema aplicado en el paso 1.
✅ Sin discrepancias — no se requiere corrección.

### 5. Sin cambios en `alembic/versions/`

`git status` confirma que `alembic/versions/` no tiene archivos nuevos ni
modificados. ✅

## Verificación de regresión

```
$ pytest --cov
113 passed — cobertura total 99.20 % (umbral 90 %)
```

## Limpieza

```powershell
docker rm -f sp180-postgres-verif
```
