# Plan de implementación backend: SP-152 Acceso seguro a archivos adjuntos

## 1. Resumen

Autorizar la descarga de una evidencia con un enlace de vida corta, volver a comprobar el rol al canjearlo y dejar constancia en base de datos. SP-151 ya persistió los metadatos; esta historia no sube el binario ni añade S3.

El enlace es un JWT HS256 `tipo=descarga` (PyJWT, el mismo de la sesión). Un Bearer `tipo=acceso` no sirve para descargar, y el token de descarga no entra en el resto de la API.

- **Stack activo**: `python-fastapi` (Python 3.12 + FastAPI, SQLAlchemy 2.x async, Alembic, PostgreSQL, Pydantic v2).
- **Arquitectura**: DDD por capas. El servicio decide rol, vigencia y contención de la ruta. El router solo delega.
- **Dependencia**: tabla `evidencias` (migración `e5f6a7b8c9d0`). Si no está en la rama, no empezar.

**Fuera de alcance**:

- Subida del archivo y SDK de object storage.
- Pantalla Angular.
- Histórico consultable de la auditoría (solo se escribe).
- Historias clínicas.

**Decisiones cerradas**:

1. `POST /api/v1/evidencias/{id}/enlace-descarga` exige Bearer de acceso y rol escritor (`ADMINISTRADOR` o `AUDITOR_SST`). Body vacío.
2. TTL por defecto 300 segundos, tope 900, variable `DESCARGA_SEGUNDOS_EXPIRACION`. Reutilizable hasta `exp`; no es de un solo uso.
3. Claims: `sub`, `evidencia_id`, `tipo=descarga`, `exp`, `jti`. Sin ruta ni MIME dentro del token.
4. `CONSULTA` recibe 403. No se exige ser el usuario que cargó el archivo: la «propiedad» es evidencia existente y `activo=true`.
5. Evidencia ausente o inactiva al pedir el enlace: 404 `EVIDENCIA_NO_ENCONTRADA`, sin distinguir ambos casos.
6. `GET /api/v1/descargas/evidencias?token=` no lleva Bearer de sesión. Revalida firma, expiración, tipo, evidencia activa y usuario activo con rol escritor.
7. Solo se abre el archivo si `ALMACENAMIENTO_LOCAL_RAIZ` está definida y `Path.resolve()` cae dentro de esa raíz. Si no hay archivo: 404 `ARCHIVO_NO_DISPONIBLE`.
8. Cada canje con token ya válido inserta `accesos_evidencia` (`AUTORIZADO`, `ARCHIVO_NO_DISPONIBLE` o `DENEGADO`) antes de abrir el archivo. Firma inválida: no hay fila.

## Estimación de puntos de historia

<!-- STORY_POINTS:8 -->
- **HU total**: 8 (Fibonacci: 1, 2, 3, 5, 8, 13)
- **Justificación**: Token de descarga distinto al de sesión, doble control de rol, lectura acotada a una raíz local y una tabla de auditoría. Sin proveedor cloud. Coincide con el enriquecimiento.
- **Subtareas**:
  | Subtarea | Puntos | Nota |
  |---|---|---|
  | SP-211 | 3 | JWT `tipo=descarga` y URL relativa |
  | SP-212 | 3 | Rol al emitir y al canjear; contención de ruta |
  | SP-213 | 2 | Tabla `accesos_evidencia` y tres resultados |
<!-- /STORY_POINTS -->

## 2. Contexto de arquitectura

- Stack activo: `python-fastapi` (`Python 3.12 + FastAPI`)
- Capas involucradas:

| Capa | Archivos afectados |
|---|---|
| Infrastructure | `alembic/versions/<rev>_crear_tabla_accesos_evidencia.py` (`down_revision` = `e5f6a7b8c9d0`); `src/infrastructure/database/modelos/acceso_evidencia_orm.py`; registro en `modelos/__init__.py`; `src/infrastructure/repositories/repositorio_acceso_evidencia_sqlalchemy.py`; `src/infrastructure/security/tokens_jwt.py`; `src/infrastructure/config/settings.py` |
| Domain | `src/domain/models/acceso_evidencia.py`; `src/domain/exceptions/evidencia.py`; `src/domain/repositories/repositorio_acceso_evidencia.py` |
| Application | `src/application/dto/respuesta_enlace_descarga.py`; `src/application/services/servicio_descarga_evidencia.py` |
| Presentation | `src/presentation/routers/evidencias_router.py`; `src/presentation/dependencies/evidencia.py` |
| Docs | `ai-specs/specs/api-spec.yml`; `ai-specs/specs/data-model.md` |
| Tests | `tests/unit/application/test_servicio_descarga_evidencia.py`; `tests/integration/test_descarga_evidencias.py` |

### Mapeo de subtareas

| Clave | Resumen | Paso(s) de implementación |
|---|---|---|
| `SP-211` | URLs firmadas con expiración | Pasos 5 y 6 (emisión), Paso 8 |
| `SP-212` | Permisos antes de servir el archivo | Pasos 5, 6 y 7, Paso 8 |
| `SP-213` | Auditoría de accesos | Pasos 1, 2, 3 y 5, Paso 9 (`data-model.md`) |

## 3. Pasos de implementación

### Paso 0: Crear la rama feature

- **Rama**: `feature/SP-152-backend` (desde `develop`).
- **Comandos**:
  ```bash
  git checkout develop && git pull origin develop
  git checkout -b feature/SP-152-backend
  ```
- Confirmar que `e5f6a7b8c9d0` es la cabeza Alembic. Si no está, SP-151 no está en la base.

### Paso 1: Migración Alembic

- **Archivo**: `alembic/versions/<rev>_crear_tabla_accesos_evidencia.py`
- **`down_revision`**: `e5f6a7b8c9d0`
- **Tabla `accesos_evidencia`**:
  - `id UUID` PK
  - `evidencia_id UUID NOT NULL` FK → `evidencias.id`, índice `ix_accesos_evidencia_evidencia_id`
  - `usuario_id UUID NOT NULL` FK → `usuarios.id`
  - `resultado VARCHAR(32) NOT NULL`
  - `fecha TIMESTAMPTZ NOT NULL`
- **`downgrade()`**: `drop_index` y `drop_table`
- No guardar token, ruta ni bytes. No usar `Base.metadata.create_all()` en producción.
- Importar el ORM en `tests/integration/conftest.py` para que el SQLite de pruebas cree la tabla.

### Paso 2: Dominio

- **`src/domain/models/acceso_evidencia.py`**: dataclass con factoría `registrar(evidencia_id, usuario_id, resultado)`. `resultado` cerrado: `AUTORIZADO`, `ARCHIVO_NO_DISPONIBLE`, `DENEGADO`. `fecha` en UTC dentro de la factoría.
- **`src/domain/exceptions/evidencia.py`**: añadir `ArchivoNoDisponibleError` (404, `ARCHIVO_NO_DISPONIBLE`). Reutilizar `EvidenciaNoEncontradaError`, `AccesoDenegadoError`, `TokenInvalidoException` y `TokenExpiradoException`.

### Paso 3: Repositorio

- Puerto `RepositorioAccesoEvidencia.guardar(acceso)`.
- Implementación SQLAlchemy que mapea dominio ↔ ORM.
- La lectura de la evidencia sigue en `RepositorioEvidencia.buscar_por_id`. No hace falta un puerto nuevo de usuarios si el router ya entrega el `Usuario` autenticado; al canjear, el servicio necesita el usuario del `sub`. Añadir `buscar_por_id` al puerto de usuarios solo si aún no existe.

### Paso 4: Configuración y token

- **`settings.py`**: `almacenamiento_local_raiz: str | None = None` (`ALMACENAMIENTO_LOCAL_RAIZ`) y `descarga_segundos_expiracion: int = 300`. Validar `1 <= valor <= 900`.
- **`tokens_jwt.py`**: emitir y decodificar un JWT con `tipo=descarga`. Rechazar en el flujo de sesión cualquier `tipo` distinto de `acceso` (ya ocurre). Rechazar en la descarga cualquier `tipo` distinto de `descarga`, mapeando vencido a `TOKEN_EXPIRADO` e inválido a `TOKEN_INVALIDO`.

### Paso 5: DTOs y servicio

- `RespuestaEnlaceDescarga`: `url: str`, `expira_en_segundos: int`.
- `ServicioDescargaEvidencia`:
  - `emitir_enlace(evidencia_id, usuario)`: 403 si el rol no es escritor; 404 si no hay evidencia activa; firmar; devolver URL relativa `/api/v1/descargas/evidencias?token=`.
  - `canjear(token)`: validar JWT; cargar usuario y evidencia; si el usuario no está activo o no es escritor, guardar `DENEGADO` y lanzar 403; si la evidencia no está activa, 404 sin abrir disco; resolver la ruta bajo la raíz; si falta raíz, archivo o la ruta escapa, guardar `ARCHIVO_NO_DISPONIBLE` y lanzar 404; si el archivo está dentro, guardar `AUTORIZADO` y devolver ruta absoluta ya contenida más el `tipo_mime` y el nombre.
- La contención es `ruta_resuelta.relative_to(raiz_resuelta)` después de `resolve()`. Cualquier `ValueError` es archivo no disponible, no un 500.
- No loguear el token ni la ruta.

### Paso 6: Router

- `POST /evidencias/{id}/enlace-descarga` en el router de evidencias, `requerir_rol_escritor`, 200 `RespuestaEnlaceDescarga`.
- `GET /descargas/evidencias` sin `obtener_usuario_actual`. Query `token`. Si el servicio autoriza, `FileResponse` con `media_type` del MIME guardado y `filename` igual a `nombre_archivo` (sin directorios).
- Registrar la ruta de descarga en `src/presentation/routers/__init__.py` con `settings.api_prefix` si queda en un router distinto. No tocar `main.py`.

### Paso 7: Excepciones

El handler global de `DomainException` ya cubre `code` y `http_status`. No añadir handler nuevo. `ArchivoNoDisponibleError` debe heredar de `DomainException`.

### Paso 8: Pruebas

- Unitarias del servicio con repos y token mockeados: enlace con `tipo=descarga` y TTL ≤ 900; `CONSULTA` no firma; evidencia inactiva → 404; token de acceso → 401; token vencido → 401; usuario desactivado → `DENEGADO`; raíz vacía o archivo ausente → `ARCHIVO_NO_DISPONIBLE` y fila de auditoría; ruta fuera de la raíz no se abre; archivo dentro → `AUTORIZADO` y el MIME guardado.
- Integración HTTP: 200 del enlace con auditor; 403 `CONSULTA`; 404 evidencia inexistente; canje 401 con token de sesión; canje 404 `ARCHIVO_NO_DISPONIBLE` sin sembrar archivo; segundo caso con archivo temporal bajo una raíz de prueba → 200 y `Content-Disposition`.

### Paso 9: Documentación

- `ai-specs/specs/api-spec.yml`: los dos paths, `RespuestaEnlaceDescarga` y los códigos 401, 403 y 404.
- `ai-specs/specs/data-model.md`: tabla `accesos_evidencia` y la nota de que el binario sigue fuera de la base.

## 4. Orden de implementación

1. Paso 0 — Rama `feature/SP-152-backend`
2. Paso 8 (parcial) — Tests de emisión y canje en rojo
3. Paso 2 — Dominio y excepción `ARCHIVO_NO_DISPONIBLE`
4. Paso 1 — Migración y ORM
5. Pasos 3 y 4 — Repositorio, settings y JWT de descarga
6. Paso 5 — DTO y servicio
7. Paso 6 — Router
8. Paso 8 — Integración HTTP, incluido un archivo real bajo raíz temporal
9. Paso 9 — `api-spec.yml` y `data-model.md`

## 5. Checklist de pruebas

- [ ] `pytest` pasa con 0 fallos
- [ ] `pytest --cov --cov-report=html` muestra cobertura ≥ 90 %
- [ ] Enlace emitido solo con rol escritor
- [ ] Canje rechaza token de sesión, token vencido y rol revocado
- [ ] Sin archivo en la raíz: 404 `ARCHIVO_NO_DISPONIBLE` y fila de auditoría
- [ ] Con archivo dentro de la raíz: 200 y ninguna lectura fuera de ese directorio
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
  "codigo": "ARCHIVO_NO_DISPONIBLE",
  "mensaje": "Descripción legible en español",
  "detalle": null
}
```

Mapeo: 401 `TOKEN_INVALIDO` / `TOKEN_EXPIRADO` | 403 `ACCESO_DENEGADO` | 404 `EVIDENCIA_NO_ENCONTRADA` / `ARCHIVO_NO_DISPONIBLE` | 422 `ERROR_VALIDACION` | 500 `ERROR_INTERNO`.

## 8. Dependencias

Ninguna librería nueva. PyJWT ya firma los tokens de sesión.

## 9. Notas

- `ALMACENAMIENTO_LOCAL_RAIZ` vacía es el comportamiento de producción hasta que un ticket posterior escriba los bytes. Los canjes autorizados responden `ARCHIVO_NO_DISPONIBLE`.
- No comparar `evidencia.usuario_id` con el del token. Un auditor descarga evidencias que cargó otro.
- No loguear el query `token`, la ruta ni el contenido.
- Commits en español, conventional commits: `feat(evidencias): autorizar descarga con enlace de vida corta`.
- Rama y PR contra `develop`.

## 10. Checklist de verificación de implementación

- [ ] Ruff/mypy OK; inyección con `Depends`
- [ ] Invariantes de resultado de auditoría en la factoría de dominio
- [ ] Servicio sin SQLAlchemy ni FastAPI
- [ ] Router fino; el GET de descarga no exige Bearer de sesión
- [ ] Esquema solo vía Alembic
- [ ] Tests verdes y cobertura ≥ 90 %
- [ ] `api-spec.yml` y `data-model.md` actualizados
