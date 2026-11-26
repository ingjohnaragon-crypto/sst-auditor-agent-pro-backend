# Plan de implementación backend: SP-283 Modelar el archivo documental y sus metadatos

## 1. Resumen

Segunda subtarea de la épica SP-249. Entrega el **modelo de dominio**, la **tabla** `archivos_documentales`, el **ORM**, el **puerto** de repositorio y su implementación SQLAlchemy. Los binarios no viven en PostgreSQL: solo metadatos y la `clave_objeto` de R2 (no una ruta de disco).

SP-282 ya dejó `AlmacenR2` / `AlmacenMemoria` y el puerto `leer`. Esta historia **no** publica HTTP (SP-284), **no** cablea el DI de evidencias (SP-285) y **no** monta la pantalla Angular (SP-286).

Borrado: a diferencia de `evidencias` (lógico), aquí el borrado de fila es **físico**. El criterio «borrar el registro borra el objeto en R2» se garantiza con el contrato `clave_objeto` + `eliminar` del almacén; la orquestación servicio (fila + R2) se cablea en SP-284 junto al DELETE HTTP. En SP-283 el repositorio debe poder borrar la fila por id.

Stack activo: `python-fastapi` (Python 3.12 + FastAPI).

## Estimación de puntos de historia

<!-- STORY_POINTS:5 -->
- **HU total**: 5 (Fibonacci: 1, 2, 3, 5, 8, 13)
- **Justificación**: Confirma los 5 del enriquecimiento y de SP-249 (modelo + ORM + migración + puerto/repo). Sin router ni cliente R2 nuevo. Volumen acotado y patrones ya existentes en `Evidencia` / `EvidenciaORM`.
- **Subtareas**: ninguna. SP-283 es la subtarea.
<!-- /STORY_POINTS -->

## 2. Contexto de arquitectura

- Stack activo: `python-fastapi` (Python 3.12 + FastAPI)
- Referencias: `Evidencia` / `EvidenciaORM` / `RepositorioEvidencia` (metadatos + validación MIME/tamaño), pero **sin** `activo` / borrado lógico.
- Clave R2 (convención del repositorio documental de empresa, misma familia que evidencias en la épica): `evidencias/{empresa_id}/{uuid}{ext}`. La genera el llamador (servicio en SP-284); el dominio valida que `clave_objeto` sea un identificador de objeto, **no** una ruta de disco (`..`, `file://`, absoluta).
- Dos cargas con el mismo `nombre_original` → dos UUID de objeto → dos `clave_objeto` distintas (índice único opcional solo sobre `clave_objeto`, no sobre el nombre).
- `hash`: SHA-256 hexadecimal del contenido (64 caracteres). Lo calcula el servicio al cargar (SP-284); el dominio exige formato válido.
- Integración: `ai-specs/specs/integraciones/cloudflare-r2.md`. `AlmacenR2` ya existe (SP-282).

| Capa | Archivos |
|---|---|
| Domain | `archivo_documental.py`, `repositorio_archivo_documental.py`, excepciones propias |
| Infrastructure | migración Alembic, `archivo_documental_orm.py`, `repositorio_archivo_documental_sqlalchemy.py`, registro en `modelos/__init__.py` |
| Docs | `ai-specs/specs/data-model.md` |
| Tests | unitarios de dominio + repo (sqlite/async como el resto) |

Sin cambios: routers, OpenAPI, `AlmacenR2`, DI de evidencias, `ServicioCargaEvidencia`.

### Mapeo de subtareas

No hay subtareas: el plan sale de SP-283.

## 3. Pasos de implementación

### Paso 0: Crear la rama

```bash
git checkout develop
git pull origin develop
git checkout -b feature/SP-283-backend
```

La base es `develop`, no `main`. Si SP-282 aún no está en `develop`, basar en `develop` actual y asumir que `AlmacenR2` llegará por merge; SP-283 no depende del cliente R2 en código (solo del contrato de clave).

### Paso 1: Migración

Nueva revisión Alembic (p. ej. `…_crear_tabla_archivos_documentales.py`) creando `archivos_documentales`:

| Columna | Tipo | Restricciones |
|---|---|---|
| `id` | UUID | PK, default `gen_random_uuid()` / `uuid4` en ORM |
| `empresa_id` | UUID | NOT NULL, FK → `empresas.id`, **índice** |
| `nombre_original` | VARCHAR(255) | NOT NULL |
| `tipo_mime` | VARCHAR(100) | NOT NULL |
| `tamano_bytes` | INTEGER | NOT NULL |
| `hash` | CHAR(64) | NOT NULL (SHA-256 hex) |
| `clave_objeto` | VARCHAR(500) | NOT NULL, **único** (una clave R2 ↔ una fila) |
| `usuario_id` | UUID | NOT NULL, FK → `usuarios.id` |
| `fecha_carga` | TIMESTAMPTZ | NOT NULL |
| `fecha_creacion` | TIMESTAMPTZ | NOT NULL, server default `now()` |
| `fecha_actualizacion` | TIMESTAMPTZ | NOT NULL, server default / `onupdate` |

Sin columnas `activo` / `fecha_eliminacion`. Downgrade: `DROP TABLE`.

### Paso 2: Dominio — modelo y excepciones

**`src/domain/exceptions/archivo_documental.py`** (o módulo cercano):

| Clase | Código | HTTP | Uso |
|---|---|---|---|
| `ArchivoInvalidoError` | `ARCHIVO_INVALIDO` | 422 | MIME, tamaño, nombre, hash, clave |
| `ArchivoNoEncontradoError` | `ARCHIVO_NO_ENCONTRADO` | 404 | Fila ausente (SP-284) |
| `ArchivoNoDisponibleError` | `ARCHIVO_NO_DISPONIBLE` | 404 | Fila existe, objeto ausente en R2 (SP-284) |

En SP-283 bastan las excepciones usadas por el modelo; las 404 de servicio se pueden declarar ya para no renombrar en SP-284.

**`src/domain/models/archivo_documental.py`**:

```python
@dataclass
class ArchivoDocumental:
    id: UUID | None
    empresa_id: UUID
    nombre_original: str
    tipo_mime: str
    tamano_bytes: int
    hash: str
    clave_objeto: str
    usuario_id: UUID
    fecha_carga: datetime
    fecha_creacion: datetime
    fecha_actualizacion: datetime

    @classmethod
    def crear(...) -> "ArchivoDocumental":
        """Valida MIME/extensión/tamaño (mismos que Evidencia: PDF/JPEG/PNG, ≤ 10 MiB),
        hash de 64 hex, y clave_objeto como identificador R2 (no ruta de disco)."""
```

- Reutilizar constantes de MIME / tope (`TAMANO_MAXIMO_BYTES`, extensiones) — import desde `evidencia` o módulo compartido mínimo; no duplicar reglas divergentes.
- **No** validar la clave como path con `..` del mismo modo que `ruta_almacenamiento` de evidencias legado: sí rechazar vacía, esquemas (`file://`, `http://`), absolutas y longitud > 500. Aceptar `evidencias/{empresa_id}/{uuid}.pdf`.
- Helper de fábrica de clave (opcional en el mismo módulo o en aplicación SP-284):

  `construir_clave_objeto(empresa_id: UUID, extension: str) -> str`  
  → `evidencias/{empresa_id}/{uuid4()}{ext}`

  Dos llamadas → dos claves. Si se deja en dominio, cubre el CA «mismo nombre, dos claves» en unitarios de SP-283.

### Paso 3: Repositorio

**Puerto** `src/domain/repositories/repositorio_archivo_documental.py`:

| Método | Comportamiento |
|---|---|
| `guardar(archivo) -> ArchivoDocumental` | Inserta metadatos; asigna `id` si venía `None` |
| `listar_por_empresa(empresa_id) -> list[ArchivoDocumental]` | Orden por `fecha_carga` desc |
| `buscar_por_id(id) -> ArchivoDocumental \| None` | |
| `eliminar(id) -> None` | **DELETE físico** de la fila; no-op o no falla si ya no está (definir: preferible idempotente) |
| `existe_empresa(empresa_id) -> bool` | Para 404 de empresa en SP-284 |

**SQLAlchemy** `src/infrastructure/repositories/repositorio_archivo_documental_sqlalchemy.py`: mapeo ORM ↔ dominio; sin lógica de R2.

**ORM** `src/infrastructure/database/modelos/archivo_documental_orm.py` + export en `modelos/__init__.py`.

### Paso 4: DTOs

Sin cambios en esta historia. Los DTO de listado/alta (sin `clave_objeto` en la respuesta) son SP-284.

### Paso 5: Servicio

Sin servicio HTTP ni caso de uso de carga en SP-283. No cablear `AlmacenR2` aquí.

Nota de diseño para SP-284: al eliminar, orden recomendado = `almacen.eliminar(clave)` y luego `repo.eliminar(id)` (o al revés con compensación documentada); si falla la fila tras `guardar` en R2, llamar `almacen.eliminar` como en `ServicioCargaEvidencia`.

### Paso 6: Router

Sin router. No registrar rutas nuevas.

### Paso 7: Excepciones

Las del paso 2. Reutilizar `AlmacenamientoNoConfiguradoError` solo cuando SP-284 ensamble el almacén. Registrar handlers globales solo si aún no cubre `DomainException` genérico (hoy sí lo cubre).

### Paso 8: Pruebas

| Archivo | Casos |
|---|---|
| `tests/unit/domain/test_archivo_documental.py` | `crear` feliz; MIME inválido; tamaño 0 / > 10 MiB; hash corto; clave vacía / con `file://`; dos `construir_clave_objeto` distintas con mismo nombre |
| `tests/unit/infrastructure/test_repositorio_archivo_documental.py` | `guardar`, `listar_por_empresa`, `buscar_por_id`, `eliminar` físico (fila desaparece), `clave_objeto` única |

Sin red. Sin tocar suites PHVA ni evidencias multipart salvo que el registro ORM rompa imports (no debería).

### Paso 9: Documentación

Actualizar `ai-specs/specs/data-model.md` con la tabla `archivos_documentales` (columnas, FKs, borrado físico, `clave_objeto` ≠ ruta local, binario en R2).

No tocar `api-spec.yml` (sin endpoints). No tocar `docs/cloudflare-r2.md` salvo una línea opcional que apunte a la tabla de metadatos.

## 4. Orden de implementación

1. Paso 0 — rama `feature/SP-283-backend`
2. Paso 2 — excepciones + modelo (+ helper de clave)
3. Paso 8 (TDD dominio) — tests rojos → verdes
4. Paso 1 — migración Alembic
5. Paso 3 — ORM + puerto + SQLAlchemy
6. Paso 8 — tests de repositorio
7. Paso 9 — `data-model.md`
8. `pytest` y cobertura ≥ 90 %

## 5. Lista de verificación de pruebas

- [ ] `pytest` termina con 0 fallos
- [ ] Cobertura global ≥ 90 %
- [ ] `clave_objeto` no se valida como path de disco con las mismas reglas que `ruta_almacenamiento` legado de escritura local
- [ ] `eliminar` del repo quita la fila (borrado físico)
- [ ] Dos claves generadas para el mismo `nombre_original` son distintas
- [ ] Migración upgrade/downgrade coherente

## 6. Referencia de herramientas

| Propósito | Comando |
|---|---|
| Build | `pip install -r requirements.txt` |
| Test | `pytest` |
| Run | `uvicorn src.main:app --reload` |
| Coverage | `pytest --cov --cov-report=html` |

Intérprete local: `.\.venv\Scripts\python.exe`.

## 7. Formato de respuesta de error

```json
{
  "exito": false,
  "codigo": "ARCHIVO_INVALIDO",
  "mensaje": "Descripción legible",
  "detalle": null
}
```

En SP-283 las excepciones de dominio quedan listas; el mapeo HTTP se ejercita en SP-284.

## 8. Dependencias

Ninguna nueva. `boto3` / R2 ya están por SP-282; no se usan en este ticket.

## 9. Notas

- Rama `feature/SP-283-backend`.
- No exponer `clave_objeto` en DTO de API (SP-284).
- No mezclar mensajes de `EVIDENCIA_INVALIDA` en el repositorio documental de empresa: usar `ARCHIVO_INVALIDO`.
- Prefijo `documentos/{empresa_id}/{tipo_codigo}/…` queda para el catálogo PHVA (SP-245); este repositorio ligero usa la convención de clave de la épica SP-249.
- Evidencias de calificación siguen en su tabla; no migrar filas aquí.

## 10. Lista de verificación de la implementación

- [ ] Tabla `archivos_documentales` migrada con `clave_objeto` UNIQUE
- [ ] Dominio `ArchivoDocumental.crear` valida MIME, tamaño, hash y clave
- [ ] Repo: guardar / listar / buscar / eliminar físico
- [ ] ORM registrado en `modelos/__init__.py`
- [ ] `data-model.md` actualizado
- [ ] Sin routers ni cambios de evidencias
- [ ] `pytest` en verde y cobertura ≥ 90 %
- [ ] Rama `feature/SP-283-backend` desde `develop`
