# Plan de implementación backend: SP-287 Probar el repositorio sin servicios externos

## 1. Resumen

Última subtarea de cierre de SP-249 orientada a **pruebas**, no a features nuevas. La suite debe ejercer el puerto de almacenamiento (`guardar` / `leer` / `eliminar`) con el doble en memoria `AlmacenMemoria`, sin LocalStack, sin llamadas a Cloudflare y **sin token R2**. Cubre el ciclo feliz más tipo inválido, tope de tamaño y `401` en descarga. La verificación contra el bucket real `sst-auditor-dev` queda solo como prueba manual documentada en `docs/cloudflare-r2.md`.

Gran parte del trabajo ya llegó con SP-282 (doble + mocks boto3), SP-284 (HTTP archivos + `AlmacenMemoria`) y SP-285 (evidencias con override en memoria). SP-287 **audita gaps**, cierra los casos de aceptación que falten, endurece que pytest no dependa de `R2_*` y deja la nota manual explícita.

**No** forma parte: pantalla Angular (SP-286), migrar evidencias históricas de disco, ni conectar CI a R2 real.

Stack activo: `python-fastapi` (Python 3.12 + FastAPI).

## Estimación de puntos de historia

<!-- STORY_POINTS:3 -->
- **HU total**: 3 (Fibonacci: 1, 2, 3, 5, 8, 13)
- **Justificación**: Es una tarea de verificación y cierre. El doble y la mayoría de casos HTTP/unitarios ya existen; el esfuerzo está en inventariar cobertura vs criterios de aceptación, rellenar huecos (p. ej. tope 10 MiB y `401` en descarga de archivos), asegurar entorno de pytest sin `R2_*` y pulir la nota manual del panel. Sin migraciones ni routers nuevos.
- **Subtareas**: ninguna. SP-287 es la subtarea.
<!-- /STORY_POINTS -->

## 2. Contexto de arquitectura

- Stack activo: `python-fastapi` (Python 3.12 + FastAPI)
- Puerto: `AlmacenEvidencias` — producción `AlmacenR2`, pruebas `AlmacenMemoria` (+ mocks de `boto3` solo para el cliente R2 unitario)
- Flujos cubiertos por la épica: evidencias (`/calificaciones-estandar/.../archivo`, canje descarga) y repositorio documental (`/empresas/{id}/archivos`)
- Auth de API: JWT de sesión (Bearer). «Sin token» en los CA = sin **credenciales Cloudflare R2**, no sin JWT de prueba
- Docs: `docs/cloudflare-r2.md` (manual), `ai-specs/specs/integraciones/cloudflare-r2.md` (OpenSpec)

| Capa | Archivos previstos |
|---|---|
| Domain / Application / Presentation | Sin cambios de producto salvo gaps mínimos descubiertos al auditar |
| Infrastructure | Solo si hace falta endurecer fábrica/settings para tests sin `R2_*` |
| Tests | `tests/unit/infrastructure/test_almacen_r2.py`, `tests/integration/test_archivos_documentales.py`, `tests/integration/test_carga_evidencias.py` / `test_descarga_evidencias.py`, unitarios de servicio; `tests/conftest.py` si se limpian env R2 |
| Docs | `docs/cloudflare-r2.md` (sección manual panel); opcional línea en README de tests |

### Inventario actual (baseline)

| Criterio de aceptación | Estado hoy | Notas |
|---|---|---|
| Doble en memoria del puerto | Hecho | `AlmacenMemoria` + override en integración |
| Guardar / leer / borrar | Hecho | Unitario memoria + HTTP archivos + evidencias |
| Tipo inválido | Hecho | Magic/MIME → 422 `ARCHIVO_INVALIDO` (archivos y evidencias) |
| Tope de tamaño | Parcial | Dominio/evidencias unitario; falta HTTP explícito en archivos documentales |
| `401` en descarga | Parcial | Archivos: `401` en listado anónimo; falta `401` en `GET .../archivos/{id}`. Evidencias: canje/enlace ya cubren 401 en descarga |
| Sin LocalStack / sin red a Cloudflare | Hecho en intención | Confirmar: no hay cliente real en pytest; `AlmacenR2` unitario usa `MagicMock` |
| Nota manual panel `sst-auditor-dev` | Hecho (base) | Revisar que el paso a paso sea copiable y claro |
| `pytest` sin `R2_*` | Revisar | `conftest` fija JWT/DB; asegurar que variables R2 del `.env` del desarrollador no activen cliente real en tests |

### Mapeo de subtareas

No hay subtareas: el plan sale de SP-287.

## 3. Pasos de implementación

### Paso 0: Crear la rama

```bash
git checkout develop
git pull origin develop
git checkout -b feature/SP-287-backend
```

Base: `develop` con SP-282…SP-285 mergeados.

### Paso 1: Migración / dominio / API

No hay migración, entidades nuevas, DTOs ni routers. Si al auditar aparece un bug de producto, se corrige en el ticket con el mínimo diff; no ampliar alcance.

### Paso 2: Auditar y fijar entorno de pytest «sin R2»

- En `tests/conftest.py` (o fixture de sesión): `delenv` / `setdefault` vacío de `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `R2_ENDPOINT` **antes** de construir settings en tests que podrían usar la fábrica real, o invalidar caché de `get_settings` si aplica.
- Objetivo: un desarrollador con `.env` R2 mal configurado (p. ej. `SignatureDoesNotMatch`) **sigue** pasando la suite offline.
- Los tests de integración deben seguir haciendo **override** con `AlmacenMemoria` + `r2_configurado=True` (simulan almacén disponible sin red).
- Los unitarios de `AlmacenR2` siguen con `MagicMock` de boto3; no instancia cliente real.

### Paso 3: Cerrar gaps de aceptación — archivos documentales

En `tests/integration/test_archivos_documentales.py` (y/o unitarios de servicio si el HTTP es demasiado pesado para el tope):

1. **Tope 10 MiB**: POST con payload `> TAMANO_MAXIMO_BYTES` (o lectura con tope si el router corta streaming) → `422` `ARCHIVO_INVALIDO` (o el código ya acordado) y **cero** objetos en `AlmacenMemoria`.
2. **`401` en descarga**: `GET /api/v1/empresas/{id}/archivos/{archivo_id}` sin `Authorization` → `401` (además del 401 de listado ya existente).

Mantener los casos ya verdes: ciclo cargar/listar/descargar/eliminar, magic inválido, 503 sin R2, 403 `CONSULTA` en escritura, 404 empresa.

### Paso 4: Cerrar gaps — evidencias (si faltan en el inventario)

Releer `test_carga_evidencias.py` / `test_descarga_evidencias.py` / unitarios:

- Guardar + leer (canje) + borrar implícito / compensación.
- Tipo inválido y tope (ya en unitario de carga).
- `401` en descarga/canje (ya aparece en descarga).

Solo añadir lo que el inventario marque como ausente. No duplicar escenarios.

### Paso 5: Puerto en memoria (regresión)

Confirmar (y ampliar solo si hace falta) en `tests/unit/infrastructure/test_almacen_r2.py`:

- `AlmacenMemoria`: guardar → leer → eliminar; eliminar ausente idempotente.
- `AlmacenR2` con mock: `put_object` / `get_object` / `delete_object` **sin red**.

Opcional: un test que falle si alguien llama a la red (p. ej. patch de `botocore.client.BaseClient._make_api_call` en un módulo de smoke) — solo si aporta señal clara; no sobre-diseñar.

### Paso 6: Documentación manual

Actualizar `docs/cloudflare-r2.md` para que la sección «Comprobar un objeto…» / panel diga de forma inequívoca:

1. Cómo subir un objeto de prueba desde el panel (o vía API local con R2_* válidos).
2. Dónde ver la clave en `sst-auditor-dev`.
3. Cómo borrar el objeto de prueba.
4. Recordatorio: **pytest no usa ese bucket**; CI/local sin token R2.

No pegar secretos. No pedir LocalStack.

Opcional: una línea en el README de tests o en la sección de desarrollo del README raíz: «La suite de almacenamiento es offline (`AlmacenMemoria`); no requiere `R2_*`.»

### Paso 7: Verificación de la suite

```bash
poetry run pytest
poetry run pytest --cov --cov-report=term-missing
```

Criterio: 0 fallos, cobertura global ≥ 90 %, ejecución sin variables R2 válidas y sin red hacia Cloudflare.

### Paso 8: OpenAPI / data-model

Sin cambios de contrato. No tocar `api-spec.yml` salvo que se descubra un bug documentado como CA.

## 4. Orden de implementación

1. Paso 0 — rama `feature/SP-287-backend`
2. Paso 2 — entorno pytest sin dependencia de `R2_*`
3. Paso 3 — gaps HTTP archivos (tope + 401 descarga)
4. Paso 4 — gaps evidencias solo si el inventario lo exige
5. Paso 5 — regresión `AlmacenMemoria` / mocks R2
6. Paso 6 — docs manuales panel
7. Paso 7 — `pytest` + cobertura
8. Paso 8 — confirmar que no hace falta OpenAPI

## 5. Lista de verificación de pruebas

- [ ] `pytest` con 0 fallos **sin** `R2_*` válidos en el entorno
- [ ] Cobertura ≥ 90 %
- [ ] Guardar / leer / borrar ejercitados vía `AlmacenMemoria`
- [ ] Tipo inválido y tope de tamaño cubiertos
- [ ] Descarga anónima → `401`
- [ ] Ningún test levanta LocalStack ni llama al endpoint R2 real
- [ ] `docs/cloudflare-r2.md` describe cómo ver un objeto en el panel `sst-auditor-dev`
- [ ] Tests existentes de SP-284/285 siguen verdes

## 6. Referencia de herramientas

| Propósito | Comando |
|---|---|
| Build | `pip install -r requirements.txt` / `poetry install` |
| Test | `pytest` |
| Run | `poetry run uvicorn src.main:app --reload` |
| Coverage | `pytest --cov --cov-report=html` |
| Lint | `ruff check .` / `mypy` |

## 7. Formato de respuesta de error

El backend usa el envelope SST:

```json
{
  "exito": false,
  "codigo": "ARCHIVO_INVALIDO",
  "mensaje": "…",
  "detalle": null
}
```

Códigos relevantes a esta suite: `ARCHIVO_INVALIDO` (422), `ALMACENAMIENTO_NO_CONFIGURADO` (503), `ACCESO_DENEGADO` (403), sin sesión → `401`, `EMPRESA_NO_ENCONTRADA` / `ARCHIVO_NO_ENCONTRADO` (404).

## 8. Dependencias

Ninguna nueva. Reutilizar `AlmacenMemoria`, `httpx` AsyncClient, fixtures de auth existentes.

## 9. Notas

- Rama: `feature/SP-287-backend`.
- «Sin token» = sin token/credenciales **R2**; los tests de API siguen usando JWT de semilla.
- No introducir LocalStack ni minio.
- No validar en CI contra `sst-auditor-dev`.
- El fallo manual `SignatureDoesNotMatch` con R2 mal configurado **no** es regresión de esta HU: la suite offline no debe depender de esas claves.
- Scope: cierre de SP-249 en backend; frontend (SP-286) ya separado.

## 10. Lista de verificación de la implementación

- [ ] Pytest offline sin `R2_*` / sin red Cloudflare
- [ ] Criterios del ticket cubiertos (CRUD memoria, inválido, tope, 401 descarga)
- [ ] Nota manual del panel actualizada y usable
- [ ] Sin cambios de producto innecesarios
- [ ] Cobertura ≥ 90 % y lint OK
- [ ] Rama desde `develop`
