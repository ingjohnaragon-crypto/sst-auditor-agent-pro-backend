# Plan de implementación backend: SP-282 Dejar el disco local como adaptador único de archivos

## 1. Resumen

Primera subtarea de la épica SP-249. El título de Jira habla de disco; el enriquecimiento manda **Cloudflare R2** como único almacén de producción. Se sigue el enriquecimiento. **SP-150 (AWS S3 / VPC) no se implementa.**

Orden obligatorio: primero el panel de Cloudflare y la nota de una página; después el cliente. `AlmacenR2` implementa `guardar`, `leer` y `eliminar` contra el endpoint S3 de R2. Si falta cualquiera de las cinco variables, no se construye el cliente y se lanza `AlmacenamientoNoConfiguradoError` (503). No se escribe en disco ni en R2.

Esta historia **no** publica el API de archivos (SP-284), **no** crea `archivos_documentales` (SP-283) y **no** cambia el DI de evidencias (SP-285). El flujo multipart actual sigue usando `AlmacenLocal` hasta SP-285. `AlmacenLocal` no es el almacén de producción.

Stack activo: `python-fastapi` (Python 3.12 + FastAPI).

## Estimación de puntos de historia

<!-- STORY_POINTS:8 -->
- **HU total**: 8 (Fibonacci: 1, 2, 3, 5, 8, 13)
- **Justificación**: Confirma los 8 del enriquecimiento (3 de aprendizaje del panel y 5 del cliente). Van juntos para no conectar el API a ciegas. Sin migración ni router nuevo.
- **Subtareas**: ninguna. SP-282 es la subtarea de SP-249.
<!-- /STORY_POINTS -->

## 2. Contexto de arquitectura

- Stack activo: `python-fastapi` (Python 3.12 + FastAPI)
- El puerto `AlmacenEvidencias` vive en `src/application/services/servicio_carga_evidencia.py` y hoy solo tiene `guardar` y `eliminar` (parámetro `relativa`).
- `AlmacenLocal` (`src/infrastructure/almacenamiento/almacen_local.py`) escribe bajo `ALMACENAMIENTO_LOCAL_RAIZ` y no sale de esa raíz.
- La clave la arma el llamador; el almacén no inventa rutas. Convención de evidencias: `evidencias/{empresa_id}/{uuid}{ext}`.
- `AlmacenamientoNoConfiguradoError` ya existe (`src/domain/exceptions/evidencia.py`, código `ALMACENAMIENTO_NO_CONFIGURADO`, HTTP 503).
- Secretos solo en `.env` local. `.env.example` declara nombres vacíos (hoy no tiene sección R2).
- Integración de referencia: `ai-specs/specs/integraciones/cloudflare-r2.md`.

| Capa | Archivos |
|---|---|
| Application | `servicio_carga_evidencia.py` — el protocolo gana `leer` |
| Infrastructure | `almacen_r2.py` (crear), `almacen_local.py` (`leer` para cumplir el puerto), `settings.py` |
| Docs | `docs/cloudflare-r2.md` (crear), `.env.example` |
| Tests | `tests/unit/infrastructure/test_almacen_r2.py`, doble en memoria |
| Dependencias | `boto3` pinneado en `pyproject.toml` y `requirements.txt` |

Sin cambios: routers, ORM, migraciones, OpenAPI, `ServicioCargaEvidencia.cargar`, `ServicioDescargaEvidencia`, DI de evidencias.

### Mapeo de subtareas

No hay subtareas: el plan sale de SP-282.

## 3. Pasos de implementación

### Paso 0: Crear la rama

```bash
git checkout develop
git pull origin develop
git checkout -b feature/SP-282-backend
```

La base es `develop`, no `main`.

### Paso 0b: Panel de Cloudflare (antes de código)

Lo hace quien implementa, con la cuenta del proyecto. El agente no entra al panel ni pega tokens en el repo.

1. Crear o usar la cuenta de Cloudflare. Activar R2.
2. Crear el bucket `sst-auditor-dev`. No mezclar con producción.
3. Crear un token API con permiso **solo** sobre ese bucket (Object Read & Write).
4. Subir un PDF de prueba desde el panel y comprobar que aparece.
5. Anotar `account id`, `access key`, `secret`, `bucket` y `endpoint` en el `.env` local. Nunca en Git.

Si el panel aún no está listo, igual se escribe la nota y el cliente; la prueba manual queda pendiente. La suite no llama a Cloudflare.

### Paso 1: Migración

No hay migración.

### Paso 2: Dominio / puerto

En `AlmacenEvidencias` agregar (misma firma de parámetro que `guardar` / `eliminar`):

```python
def leer(self, relativa: str) -> bytes:
    """Devuelve el binario. Si no existe, lanza FileNotFoundError."""
```

Para R2, `relativa` es la clave de objeto (p. ej. `evidencias/{empresa_id}/{uuid}.pdf`).

El almacén no lanza HTTP. `AlmacenamientoNoConfiguradoError` lo lanza la fábrica al construir, no cada `put`.

`AlmacenLocal.leer`: lee el archivo contenido en la raíz; si no es un archivo, `FileNotFoundError`. No convierte a `AlmacenLocal` en destino de producción.

### Paso 3: Repositorio

Sin cambios. El puerto de almacenamiento no es un repositorio SQL.

### Paso 4: DTOs

Sin cambios. No hay endpoint nuevo.

### Paso 5: Settings y `AlmacenR2`

**`settings.py`** (opcionales, `None` si faltan o vienen vacías; mismo patrón que `almacenamiento_local_raiz`):

- `r2_account_id`
- `r2_access_key_id`
- `r2_secret_access_key`
- `r2_bucket`
- `r2_endpoint`

Método o propiedad `r2_configurado`: las cinco tienen texto no vacío. Cadena vacía cuenta como ausente (validator tipo `vacio_es_sin_raiz`).

**Fábrica** (p. ej. `crear_almacen_r2` en el mismo módulo de `AlmacenR2` o junto al DI futuro):

- Si no `r2_configurado` → `AlmacenamientoNoConfiguradoError`. No se instancia `boto3.client`.
- Si está completo → `AlmacenR2` con `endpoint_url=r2_endpoint`, `aws_access_key_id`, `aws_secret_access_key`, región `auto` (la que exija el endpoint de R2).

**`AlmacenR2`** en `src/infrastructure/almacenamiento/almacen_r2.py`:

| Método | Acción |
|---|---|
| `guardar(relativa, contenido)` | `put_object` Bucket/Key/Body |
| `leer(relativa)` | `get_object`; `NoSuchKey` (o equivalente) → `FileNotFoundError` |
| `eliminar(relativa)` | `delete_object`; no falla si el objeto ya no está |

La clave se usa tal cual. El llamador (SP-284 / SP-285) pondrá `evidencias/{empresa_id}/{uuid}{ext}`. No loguear el secreto ni el access key.

Pinneado: `boto3` en `[project].dependencies` y regenerar `requirements.txt` como el resto del repo (`poetry export`). No LocalStack. No `aiobotocore`. El puerto sigue síncrono, igual que `AlmacenLocal`.

### Paso 6: Router

Sin router nuevo. No cambiar `obtener_servicio_carga_evidencia`: sigue inyectando `AlmacenLocal` hasta SP-285.

### Paso 7: Excepciones

Reutilizar `AlmacenamientoNoConfiguradoError` (`503`, `ALMACENAMIENTO_NO_CONFIGURADO`). Sin códigos nuevos.

### Paso 8: Pruebas

Archivo: `tests/unit/infrastructure/test_almacen_r2.py`.

Doble o `unittest.mock` del cliente S3. **Sin red.**

- Fábrica sin variables / con alguna vacía → `AlmacenamientoNoConfiguradoError` y el cliente no se crea.
- `guardar` llama `put_object` con bucket, clave y body.
- `leer` devuelve los bytes de `Body.read()`.
- `leer` de clave inexistente → `FileNotFoundError`.
- `eliminar` llama `delete_object` y no explota si el mock simula ausencia.
- Un doble en memoria (`dict[str, bytes]`) cubre guardar, leer y borrar. Lo reutilizarán SP-284 y SP-287.

Si el protocolo exige `leer` en `AlmacenLocal`, un test corto con `tmp_path`: guardar y leer; una clave que escaparía de la raíz se sigue rechazando.

No tocar `test_carga_evidencias.py` ni PHVA. El `_Almacen` de `test_servicio_carga_evidencia.py` solo necesita `leer` si mypy o el servicio lo piden; si el servicio aún no llama `leer`, dejarlo.

Caso manual (fuera de CI), descrito en la nota: un script o REPL que construya `AlmacenR2` con el `.env` local, haga `guardar` / `leer` / `eliminar` de un objeto de prueba y se vea en el panel de `sst-auditor-dev`.

### Paso 9: Documentación

**`.env.example`** — nombres sin valores secretos (añadir sección; el archivo actual no tiene R2):

```
# ── Cloudflare R2 ─────────────────────────────────────────────
# Token solo sobre sst-auditor-dev. El secreto no se versiona.
# R2_ACCOUNT_ID=
# R2_ACCESS_KEY_ID=
# R2_SECRET_ACCESS_KEY=
# R2_BUCKET=
# R2_ENDPOINT=
```

**`docs/cloudflare-r2.md`** (una página, en español, **antes** de dar por cerrado el cliente):

- Qué es un objeto y qué es la clave.
- Dónde se pega el token (`.env`, nunca el repo ni el frontend).
- Por qué el archivo no es público (sin Workers, sin dominio del bucket).
- Cómo crear `sst-auditor-dev` y comprobar un PDF subido a mano.
- Cómo comprobar un objeto que subió `AlmacenR2`.
- Claves previstas: `evidencias/{empresa_id}/{uuid}{ext}` y, más adelante, `documentos/{empresa_id}/{tipo_codigo}/{uuid}{ext}`.

No actualizar `api-spec.yml` (no hay endpoint nuevo). En `data-model.md` no se agrega tabla; opcional una línea de que los binarios de producción no viven en `ALMACENAMIENTO_LOCAL_RAIZ`.

## 4. Orden de implementación

1. Paso 0 — rama `feature/SP-282-backend`
2. Paso 0b y 9 — nota `docs/cloudflare-r2.md` y `.env.example` (el panel puede ir en paralelo)
3. Paso 2 — `leer` en el protocolo
4. Paso 5 — settings, fábrica, `AlmacenR2`
5. Paso 8 — pruebas con mock / doble
6. `AlmacenLocal.leer` para cumplir el puerto
7. `pytest` y cobertura

Los pasos 1, 3, 4 y 6 (router) no producen archivos de producción.

## 5. Lista de verificación de pruebas

- [ ] `pytest` termina con 0 fallos
- [ ] Cobertura global ≥ 90 %
- [ ] La fábrica sin R2 no instancia cliente ni escribe disco
- [ ] `guardar` / `leer` / `eliminar` cubiertos sin red
- [ ] El secreto no aparece en Git
- [ ] Manual: el PDF de prueba se ve en `sst-auditor-dev` y `eliminar` lo quita

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
  "codigo": "ALMACENAMIENTO_NO_CONFIGURADO",
  "mensaje": "El almacenamiento de archivos no está configurado",
  "detalle": null
}
```

En esta historia el 503 lo lanza la fábrica. Aún no hay ruta HTTP nueva que lo exponga.

## 8. Dependencias

`boto3` pinneado. Cliente con `endpoint_url` de R2. Sin LocalStack, sin SDK de Cloudflare en el API, sin Workers.

## 9. Notas

- Rama `feature/SP-282-backend`. Nunca `-frontend` en este repo.
- El agente no crea la cuenta de Cloudflare. La nota describe el recorrido; el humano pega el token en `.env`.
- No leer `.env` en el chat ni copiar secretos al plan o a tests.
- No cablear evidencias ni el router de empresa.
- `CONSULTA` y MIME se prueban en SP-284.
- El título original de Jira se conserva; el comportamiento es R2.
- Evidencias ya guardadas en disco: migración manual documentada; lo nuevo no escribe en disco (SP-285).

## 10. Lista de verificación de la implementación

- [ ] `docs/cloudflare-r2.md` existe y no contiene secretos
- [ ] `.env.example` declara las cinco variables vacías
- [ ] `AlmacenR2` implementa `guardar`, `leer` y `eliminar`
- [ ] Sin variables: `AlmacenamientoNoConfiguradoError`, sin cliente
- [ ] No hay diff de routers ni de migraciones
- [ ] `pytest` en verde y cobertura ≥ 90 %
- [ ] Rama `feature/SP-282-backend` desde `develop`
