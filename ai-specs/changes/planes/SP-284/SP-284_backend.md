# Plan de implementación backend: SP-284 Publicar API de carga listado y descarga

## 1. Resumen

Tercera subtarea de SP-249. Publica cuatro operaciones HTTP sobre el repositorio documental de empresa, usando `AlmacenR2` (SP-282) y `archivos_documentales` (SP-283). El router es delgado: valida sesión, rol, MIME y magic bytes **antes** de escribir en R2. La descarga transmite el binario con Bearer de sesión (sin URL pública del bucket).

**No** forma parte de esta historia: cambiar el DI de evidencias a R2 (SP-285), pantalla Angular (SP-286) ni la suite exhaustiva sin red de SP-287 (aunque los tests de esta HU usen `AlmacenMemoria`).

Stack activo: `python-fastapi` (Python 3.12 + FastAPI).

## Estimación de puntos de historia

<!-- STORY_POINTS:5 -->
- **HU total**: 5 (Fibonacci: 1, 2, 3, 5, 8, 13)
- **Justificación**: Confirma los 5 del enriquecimiento (cuatro operaciones HTTP sobre el puerto de SP-282). El modelo y el almacén ya existen; el esfuerzo está en servicio, DI, router, RBAC y pruebas de integración HTTP.
- **Subtareas**: ninguna. SP-284 es la subtarea.
<!-- /STORY_POINTS -->

## 2. Contexto de arquitectura

- Stack activo: `python-fastapi` (Python 3.12 + FastAPI)
- Prefijo: `/api/v1/empresas/{empresa_id}/archivos`
- Puerto de bytes: `AlmacenEvidencias` (`guardar` / `leer` / `eliminar`) — implementaciones `AlmacenR2` y `AlmacenMemoria`
- Metadatos: `RepositorioArchivoDocumental` + `ArchivoDocumental.crear` / `construir_clave_objeto`
- Patrón de referencia: `evidencias_router.cargar_archivo_evidencia` + `ServicioCargaEvidencia` (tope 64 KiB, magic, compensación si falla la fila)
- RBAC: `requerir_rol_escritor` para POST/DELETE; `obtener_usuario_actual` para GET
- Respuesta de listado/alta: **sin** `clave_objeto` ni URL permanente

| Capa | Archivos |
|---|---|
| Application | DTO respuesta, mapper, `servicio_archivos_documentales.py` |
| Presentation | `archivos_documentales_router.py`, DI, registro en `routers/__init__.py` |
| Infrastructure | Solo ensamblado DI (`crear_almacen_r2` / settings); sin cambio de ORM |
| Docs | `ai-specs/specs/api-spec.yml` |
| Tests | unitarios del servicio + integración HTTP con `AlmacenMemoria` |

### Mapeo de subtareas

No hay subtareas: el plan sale de SP-284.

## 3. Pasos de implementación

### Paso 0: Crear la rama

```bash
git checkout develop
git pull origin develop
git checkout -b feature/SP-284-backend
```

La base es `develop` (con SP-282 y SP-283 mergeados). Si faltara alguno, rebasear/mergear antes de implementar.

### Paso 1: Migración

No hay migración. La tabla ya existe (SP-283).

### Paso 2: Dominio

Sin entidades nuevas. Reutilizar:

- `ArchivoInvalidoError`, `ArchivoNoEncontradoError`, `ArchivoObjetoNoDisponibleError`
- `AlmacenamientoNoConfiguradoError`
- Excepción de acceso denegado ya usada por `requerir_rol_escritor`

Opcional: helper compartido de magic bytes (extraer `MAGIC` / `_exigir_magic` desde carga de evidencias) para no divergir firmas; si se extrae, evidencias pueden seguir importando el mismo módulo. **No** cambiar el flujo de evidencias a R2.

### Paso 3: Repositorio

Sin cambios de contrato. El servicio usará `guardar`, `listar_por_empresa`, `buscar_por_id`, `eliminar`, `existe_empresa`.

Si el listado debe mostrar nombre/correo del cargador y el repo actual no hace join, enriquecer en el servicio con `RepositorioUsuario.buscar_por_id` (mismo criterio práctico que otras respuestas: como mínimo `usuario_id`; ideal `usuario_id` + `nombre_completo` o `correo`).

### Paso 4: DTOs

**`RespuestaArchivoDocumental`** (Pydantic):

| Campo | Notas |
|---|---|
| `id` | UUID |
| `empresa_id` | UUID |
| `nombre_original` | |
| `tipo_mime` | |
| `tamano_bytes` | |
| `fecha_carga` | |
| `usuario_id` | |
| `usuario_nombre` o `usuario_correo` | Opcional si se enriquece; no exponer `clave_objeto` ni `hash` en la API pública salvo necesidad explícita (el plan de épica no pide `hash` en respuesta) |

POST: `multipart/form-data`, campo `archivo` (`UploadFile`). Sin DTO de ruta/tamaño del cliente.

Mapper: `MapperArchivoDocumental.a_respuesta(...)`.

### Paso 5: Servicio

**`ServicioArchivosDocumentales`**:

```text
__init__(repo_archivo, almacen: AlmacenEvidencias, *, r2_configurado: bool, repo_usuario?: ...)
```

| Método | Comportamiento |
|---|---|
| `listar(empresa_id)` | 404 si no `existe_empresa`; lista ordenada |
| `cargar(empresa_id, nombre, content_type, contenido, usuario_id)` | Ver flujo abajo → 201 |
| `descargar(empresa_id, archivo_id)` | Valida empresa + archivo; `almacen.leer`; `FileNotFoundError` → `ArchivoObjetoNoDisponibleError` |
| `eliminar(empresa_id, archivo_id)` | Busca fila; `almacen.eliminar(clave)`; `repo.eliminar(id)` → 204 |

**Flujo `cargar` (orden obligatorio):**

1. Si no `r2_configurado` → `AlmacenamientoNoConfiguradoError` (503). **No** escribir disco ni R2.
2. Si empresa no existe → 404 empresa (reutilizar excepción de empresas o `ArchivoNoEncontradoError` / dedicada coherente con el API).
3. `leer_con_tope` / tope 10 MiB + magic bytes **antes** de `guardar` en R2. Inválido → `ArchivoInvalidoError` (422) y **ningún** `put`.
4. `hash` = SHA-256 hex del contenido.
5. `clave = construir_clave_objeto(empresa_id, extension)`.
6. `ArchivoDocumental.crear(...)`.
7. `almacen.guardar(clave, contenido)`.
8. `repo.guardar`; si falla → `almacen.eliminar(clave)` y propagar.

**Descarga:** devolver bytes + `tipo_mime` + `nombre_original` al router; el router arma `StreamingResponse` / `Response` con `Content-Disposition: attachment`. No devolver URL de R2 al cliente.

### Paso 6: Router y DI

**Router** `archivos_documentales_router.py`:

Prefijo del router: `/empresas/{empresa_id}/archivos` (luego `include_router` con `settings.api_prefix`).

| Método | Ruta | Dependencias | Status |
|---|---|---|---|
| GET | `/` | `obtener_usuario_actual` | 200 `list[RespuestaArchivoDocumental]` |
| POST | `/` | `requerir_rol_escritor`, `File(...)` | 201 |
| GET | `/{archivo_id}` | `obtener_usuario_actual` | 200 binario |
| DELETE | `/{archivo_id}` | `requerir_rol_escritor` | 204 |

Respuestas documentadas: 401, 403 (escritura), 404, 422, 503.

**DI** (p. ej. `presentation/dependencies/archivo_documental.py`):

- Repo SQLAlchemy con sesión.
- Almacén: si `settings.r2_configurado` → `crear_almacen_r2(settings)`; si no, el servicio recibe `r2_configurado=False` y no se instancia cliente (o se pasa un almacén dummy nunca llamado). En tests de integración, override del Depends con `AlmacenMemoria` + `r2_configurado=True`.
- **No** modificar `obtener_servicio_carga_evidencia` (sigue `AlmacenLocal` hasta SP-285).

Registrar en `src/presentation/routers/__init__.py`.

### Paso 7: Excepciones

| Código | HTTP | Cuándo |
|---|---|---|
| `TOKEN_INVALIDO` / anónimo | 401 | Sin Bearer |
| `ACCESO_DENEGADO` | 403 | `CONSULTA` en POST/DELETE |
| `ARCHIVO_INVALIDO` | 422 | MIME/magic/tamaño |
| `ALMACENAMIENTO_NO_CONFIGURADO` | 503 | Sin variables R2 |
| Empresa / archivo ausente | 404 | |
| `ARCHIVO_NO_DISPONIBLE` | 404 | Fila sí, objeto no en almacén |

Cuerpo: `exito`, `codigo`, `mensaje`, `detalle`.

### Paso 8: Pruebas

| Tipo | Casos |
|---|---|
| Unitario servicio | Magic inválido → no llama `guardar`; fallo de repo → llama `eliminar`; sin R2 → 503; dos claves distintas; descarga con `FileNotFoundError` → `ArchivoObjetoNoDisponibleError`; eliminar llama almacén + repo |
| Integración HTTP | Anónimo → 401; `CONSULTA` POST/DELETE → 403; `CONSULTA` GET listado/descarga → 200; escritor POST 201 + listado; DELETE 204 y el objeto desaparece del doble; archivo inválido → 422 y doble vacío; empresa inexistente → 404 |

Doble: `AlmacenMemoria`. **Sin red.** Reutilizar fixtures de auth/JWT del proyecto.

### Paso 9: Documentación

- `ai-specs/specs/api-spec.yml`: los cuatro endpoints bajo `/empresas/{empresa_id}/archivos`.
- No tocar `data-model.md` salvo detalle menor de API.
- No reinventar `docs/cloudflare-r2.md`.

## 4. Orden de implementación

1. Paso 0 — rama `feature/SP-284-backend`
2. Paso 4 — DTO + mapper
3. Paso 5 — servicio (TDD unitario con `AlmacenMemoria`)
4. Paso 6 — DI + router + registro
5. Paso 8 — tests de integración HTTP
6. Paso 9 — `api-spec.yml`
7. `pytest` y cobertura ≥ 90 %

## 5. Lista de verificación de pruebas

- [ ] `pytest` con 0 fallos
- [ ] Cobertura ≥ 90 %
- [ ] Anónimo → 401
- [ ] Archivo inválido → 422 y cero objetos en el doble
- [ ] `CONSULTA` no carga ni borra (403); sí lista y descarga
- [ ] Sin R2 configurado → 503 y ninguna fila
- [ ] DELETE quita fila y objeto del almacén

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
  "mensaje": "El contenido no coincide con el tipo de archivo",
  "detalle": null
}
```

## 8. Dependencias

Ninguna nueva. `python-multipart` y `boto3` ya están por historias previas.

## 9. Notas

- Rama `feature/SP-284-backend`.
- Preferir `StreamingResponse` con sesión Bearer frente a URL firmada expuesta al Angular (SP-286 no consume firmadas).
- Campo multipart: `archivo` (igual espíritu que evidencias).
- Compensación R2↔DB obligatoria en carga y borrado ordenado (objeto luego fila, o documentar compensación).
- No cablear evidencias a R2 en este PR.

## 10. Lista de verificación de la implementación

- [ ] Cuatro rutas registradas bajo `/api/v1/empresas/{empresa_id}/archivos`
- [ ] Magic/MIME/tope antes de `guardar`
- [ ] Respuestas sin `clave_objeto`
- [ ] `CONSULTA` / anónimo cubiertos
- [ ] DI de evidencias intacto
- [ ] `api-spec.yml` actualizado
- [ ] `pytest` verde y cobertura ≥ 90 %
- [ ] Rama desde `develop`
