# Plan de implementación backend: SP-214 API multipart de evidencias

## 1. Resumen

Subir el PDF o la imagen de un estándar ya calificado. El servidor mide el archivo, comprueba los magic bytes, lo guarda bajo `ALMACENAMIENTO_LOCAL_RAIZ` y crea la fila de `evidencias` con una ruta que él genera. El cliente no envía ruta, tamaño ni usuario.

SP-214 es subtarea de SP-153. SP-215 y SP-216 (Angular) quedan fuera de este repositorio. El POST JSON de metadatos de SP-151 no se modifica y no escribe disco. El descarte del usuario sigue siendo el `DELETE` lógico ya existente.

- **Stack activo**: `python-fastapi` (Python 3.12 + FastAPI, SQLAlchemy 2.x async, Alembic, PostgreSQL, Pydantic v2).
- **Arquitectura**: DDD por capas. `Evidencia.crear` valida nombre, MIME, extensión y tamaño. El servicio añade los magic bytes y la contención de la ruta. El router solo recibe `UploadFile`.
- **Dependencia**: tabla `evidencias` y raíz de SP-152. Sin raíz configurada no hay alta.

**Fuera de alcance**:

- Pantalla de arrastre y visor PDF.
- S3 u otro SDK.
- Borrar el binario ya confirmado.
- Cambiar el contrato del POST JSON de metadatos.

**Decisiones cerradas**:

1. `POST /api/v1/calificaciones-estandar/{calificacion_id}/archivo`, `multipart/form-data`, un solo campo `archivo`. 201 `RespuestaEvidencia`.
2. Ruta relativa generada: `evidencias/{calificacion_id}/{uuid}{ext}`. Extensión según MIME (`.pdf`, `.jpg`, `.png`).
3. Magic bytes obligatorios: PDF `%PDF`, JPEG `FF D8 FF`, PNG `89 50 4E 47`. El `Content-Type` del part debe coincidir con la extensión del nombre.
4. Tope 10 MiB, leído por bloques de 64 KiB. Al superar el tope se corta y no queda archivo.
5. Rol escritor. `CONSULTA` → 403. Calificación inexistente → 404. Sin raíz → 503 `ALMACENAMIENTO_NO_CONFIGURADO`.
6. Si `Evidencia.crear` o `guardar` fallan después de escribir, se borra el archivo. Ese es el único borrado físico.
7. `usuario_id` sale del Bearer.

## Estimación de puntos de historia

<!-- STORY_POINTS:5 -->
- **HU total**: 5 (Fibonacci: 1, 2, 3, 5, 8, 13)
- **Justificación**: Un endpoint multipart, validación de contenido y escritura atómica respecto a la fila. Sin migración. Coincide con el enriquecimiento de SP-214. La UI no entra.
- **Subtareas**: esta clave es la subtarea; no tiene hijas.
<!-- /STORY_POINTS -->

## 2. Contexto de arquitectura

- Stack activo: `python-fastapi` (`Python 3.12 + FastAPI`)
- Capas involucradas:

| Capa | Archivos afectados |
|---|---|
| Domain | `src/domain/exceptions/evidencia.py` (`AlmacenamientoNoConfiguradoError`, 503) |
| Application | `src/application/services/servicio_carga_evidencia.py` |
| Infrastructure | `src/infrastructure/almacenamiento/almacen_local.py` |
| Presentation | `src/presentation/routers/evidencias_router.py`; `src/presentation/dependencies/evidencia.py` |
| Docs | `ai-specs/specs/api-spec.yml` |
| Tests | `tests/unit/application/test_servicio_carga_evidencia.py`; `tests/integration/test_carga_evidencias.py` |

No hay migración. `data-model.md` no cambia de columnas. La ruta generada cabe en `ruta_almacenamiento` VARCHAR(500).

### Mapeo de subtareas

No hay subtareas hijas. El plan sale de SP-214, subtarea de SP-153.

## 3. Pasos de implementación

### Paso 0: Crear la rama feature

- **Rama**: `feature/SP-214-backend` (desde `develop`).
- **Comandos**:
  ```bash
  git checkout develop && git pull origin develop
  git checkout -b feature/SP-214-backend
  ```
- Confirmar que existen `evidencias` y el canje de SP-152. Sin ellos la prueba de “el enlace devuelve estos bytes” no tiene destino.

### Paso 1: Excepción

- **`src/domain/exceptions/evidencia.py`**: `AlmacenamientoNoConfiguradoError`, `code = "ALMACENAMIENTO_NO_CONFIGURADO"`, `http_status = 503`.
- Reutilizar `EvidenciaInvalidaError` (422), `CalificacionNoEncontradaError` (404) y `AccesoDenegadoError` (403).
- El handler global de `DomainException` ya traduce `code` y `http_status`. No añadir handler.

### Paso 2: Almacén local

- **`src/infrastructure/almacenamiento/almacen_local.py`**.
- Recibe la raíz (`Path | None`) y expone guardar y borrar una ruta relativa.
- `guardar(relativa, contenido: BinaryIO) -> None`: resuelve `raiz / relativa` con `resolve()` + `relative_to`. Si escapa de la raíz, no escribe. Crea el directorio padre. Escribe el contenido.
- `eliminar(relativa) -> None`: mismo chequeo de contención; si el archivo existe, lo borra. Si no existe, no falla.
- Raíz `None`: no escribe; el servicio ya habrá lanzado 503 antes de llamar.

### Paso 3: Servicio

- **`src/application/services/servicio_carga_evidencia.py`**.
- `cargar(calificacion_id, nombre, tipo_mime, contenido, usuario_id)`.
- Orden:
  1. 503 si no hay raíz.
  2. 404 si `existe_calificacion` es falso.
  3. Leer por bloques hasta 10 MiB + 1. Si se pasa, `EvidenciaInvalidaError` y no escribir.
  4. Comprobar magic bytes según el MIME ya normalizado. Si no coinciden, 422.
  5. `Evidencia.crear(...)` con el tamaño medido y una ruta `evidencias/{calificacion_id}/{uuid}{ext}` aún no publicada.
  6. Escribir en el almacén.
  7. `repositorio.guardar`. Si lanza, `eliminar` la ruta y propagar.
- El MIME permitido y la extensión siguen saliendo de `Evidencia.crear`. El servicio solo añade el magic y la ruta.
- No loguear bytes.

### Paso 4: Router y dependencias

- En `evidencias_router.py`, sobre el router de calificaciones: `POST /{calificacion_id}/archivo`.
- `File(...)` de FastAPI, nombre de campo `archivo`. `requerir_rol_escritor`. 201 `RespuestaEvidencia`.
- `usuario_id` del escritor. Si `id` es `None`, `TokenInvalidoException`, igual que el alta de metadatos.
- `obtener_servicio_carga_evidencia` en `dependencies/evidencia.py`, reutilizando `obtener_raiz_almacenamiento`, `obtener_repositorio_evidencia` y el almacén local.
- No tocar `main.py`. El router de calificaciones ya está incluido con `settings.api_prefix`.

### Paso 5: Pruebas

- Unitarias con almacén y repositorio mockeados, y un directorio temporal real para la contención:
  - PDF `%PDF` → ruta bajo `evidencias/{id}/` y `guardar` llamado una vez.
  - JPEG `.jpg` / `.jpeg` y PNG válidos.
  - PNG con nombre `.pdf`, HTML y `.exe` → 422 y `eliminar` o ninguna escritura.
  - Buffer mayor de 10 MiB → 422 sin escritura.
  - Calificación ausente → no se llama al almacén.
  - Raíz ausente → 503.
  - `guardar` del repositorio lanza → `eliminar` de la ruta.
  - `usuario_id` de la evidencia es el argumento.
- Integración HTTP con `tmp_path` sobre `obtener_raiz_almacenamiento`:
  - 201 y el archivo existe en disco.
  - 403 `CONSULTA`.
  - 404 calificación inexistente.
  - 422 magic incoherente y el directorio queda vacío.
  - 503 sin override de raíz (o con override a `None`).
  - Tras el 201, `POST .../enlace-descarga` y el `GET` del enlace devuelven los mismos bytes.

### Paso 6: Documentación

- `ai-specs/specs/api-spec.yml`: path, `multipart/form-data`, campo `archivo`, respuestas 201, 403, 404, 422 y 503.
- No hace falta columna nueva en `data-model.md`. Una frase de que la ruta de una carga la genera el servidor basta si el párrafo de `ruta_almacenamiento` aún dice que la elige el cliente.

## 4. Orden de implementación

1. Paso 0 — Rama `feature/SP-214-backend`
2. Paso 5 (parcial) — Tests de magic, tope y limpieza en rojo
3. Paso 1 — Excepción 503
4. Paso 2 — Almacén local
5. Paso 3 — Servicio
6. Paso 4 — Router
7. Paso 5 — Integración HTTP, incluido el canje de SP-152
8. Paso 6 — `api-spec.yml`

## 5. Checklist de pruebas

- [ ] `pytest` pasa con 0 fallos
- [ ] `pytest --cov --cov-report=html` muestra cobertura ≥ 90 %
- [ ] 201 deja bytes en la raíz y fila en `evidencias`
- [ ] Magic incoherente y tamaño de más no dejan residuo
- [ ] `CONSULTA` recibe 403
- [ ] Sin raíz: 503 y ninguna fila
- [ ] El enlace de SP-152 devuelve el archivo recién subido
- [ ] Ruff y mypy strict sin errores nuevos

## 6. Referencia de tooling

| Propósito | Comando |
|---|---|
| Build | `pip install -r requirements.txt` |
| Test | `pytest` |
| Run | `uvicorn main:app --reload` |
| Coverage | `pytest --cov --cov-report=html` |

## 7. Formato de respuesta de error

```json
{
  "exito": false,
  "codigo": "EVIDENCIA_INVALIDA",
  "mensaje": "Descripción legible en español",
  "detalle": null
}
```

Mapeo: 401 `TOKEN_INVALIDO` / `TOKEN_EXPIRADO` | 403 `ACCESO_DENEGADO` | 404 `CALIFICACION_NO_ENCONTRADA` | 422 `EVIDENCIA_INVALIDA` | 503 `ALMACENAMIENTO_NO_CONFIGURADO` | 500 `ERROR_INTERNO`.

## 8. Dependencias

Ninguna librería nueva. `UploadFile` y `python-multipart` ya forman parte de FastAPI.

## 9. Notas

- No borrar el binario confirmado. El `DELETE` lógico de SP-151 deja de servirlo vía SP-152.
- La limpieza física solo ocurre si la carga no llegó a confirmarse.
- No loguear el contenido del part.
- Commits en español: `feat(evidencias): recibir el archivo del estándar calificado`.
- Rama y PR contra `develop`.

## 10. Checklist de verificación de implementación

- [ ] Ruff/mypy OK; inyección con `Depends`
- [ ] MIME, extensión y tamaño siguen en `Evidencia.crear`; el magic vive en el servicio
- [ ] Servicio sin FastAPI ni SQLAlchemy
- [ ] Router fino; `usuario_id` solo desde el token
- [ ] Sin migración
- [ ] Tests verdes y cobertura ≥ 90 %
- [ ] `api-spec.yml` actualizado
