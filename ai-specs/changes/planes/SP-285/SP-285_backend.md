# Plan de implementación backend: SP-285 Unificar las evidencias del diagnóstico en el repositorio

## 1. Resumen

Cuarta subtarea de SP-249. Cablea la carga y la descarga de evidencias de calificación al puerto R2 ya entregado en SP-282. `ServicioCargaEvidencia` deja de escribir con `AlmacenLocal`; persiste la clave de objeto en `ruta_almacenamiento`. `ServicioDescargaEvidencia.canjear` deja de abrir un `Path` bajo disco y lee bytes con `almacen.leer`. El flujo JWT `tipo=descarga`, el TTL y el RBAC de SP-152 **no cambian**.

**No** forma parte de esta historia: API del repositorio documental de empresa (SP-284, ya hecha), pantalla Angular (SP-286), suite exhaustiva sin red (SP-287), ni un job de migración de evidencias viejas en disco (solo documentar deuda).

Stack activo: `python-fastapi` (Python 3.12 + FastAPI).

## Estimación de puntos de historia

<!-- STORY_POINTS:3 -->
- **HU total**: 3 (Fibonacci: 1, 2, 3, 5, 8, 13)
- **Justificación**: Confirma los 3 del enriquecimiento y de Jira. El puerto R2 y `leer` ya existen; el esfuerzo es cambiar DI + servicios de carga/descarga, resolver `empresa_id` para la clave, adaptar el router de canje (de `FileResponse` a bytes) y migrar tests de `tmp_path`/`AlmacenLocal` a `AlmacenMemoria`. Sin migración de esquema ni pantalla.
- **Subtareas**: ninguna. SP-285 es la subtarea.
<!-- /STORY_POINTS -->

## 2. Contexto de arquitectura

- Stack activo: `python-fastapi` (Python 3.12 + FastAPI)
- Puerto: `AlmacenEvidencias` (`guardar` / `leer` / `eliminar`) — producción `AlmacenR2`, tests `AlmacenMemoria`
- Columna existente: `evidencias.ruta_almacenamiento` (String 500) pasa a guardar la **clave R2** (sin rename de columna en esta HU)
- Clave nueva: `evidencias/{empresa_id}/{uuid}{ext}` (hoy es `evidencias/{calificacion_id}/{uuid}{ext}`)
- Resolver `empresa_id`: join calificación → autoevaluación → empresa (añadir método al repo de evidencias o consulta dedicada)
- Descarga: JWT corto + canje en `/api/v1/descargas/evidencias?token=…` (SP-152); `CONSULTA` sigue sin descargar evidencias
- `AlmacenLocal` permanece en el repo como referencia/adaptador de laboratorio; **producción no lo inyecta**

| Capa | Archivos |
|---|---|
| Application | `servicio_carga_evidencia.py`, `servicio_descarga_evidencia.py` (`ArchivoAutorizado`) |
| Domain / Repo | `repositorio_evidencia.py` (+ SQLAlchemy): obtener `empresa_id` por calificación |
| Presentation | `dependencies/evidencia.py`, `evidencias_router.py` (canje) |
| Docs | `docs/cloudflare-r2.md` o nota corta; `api-spec.yml` solo si cambia el contrato de descarga |
| Tests | unitarios carga/descarga + integración `test_carga_evidencias` / `test_descarga_evidencias` |

### Mapeo de subtareas

No hay subtareas: el plan sale de SP-285.

## 3. Pasos de implementación

### Paso 0: Crear la rama

```bash
git checkout develop
git pull origin develop
git checkout -b feature/SP-285-backend
```

La base es `develop` con SP-282, SP-283 y SP-284 mergeados. Si SP-284 aún no está en `develop`, rebasear/mergear antes.

### Paso 1: Migración

No hay migración Alembic. La columna `ruta_almacenamiento` ya existe y acepta la clave.

Documentar en el plan / `docs/cloudflare-r2.md` (sección corta): evidencias históricas con ruta solo de disco quedan **pendientes de migración manual**; las nuevas ya no escriben en disco.

### Paso 2: Dominio / contrato de clave

- Reutilizar validaciones MIME/tope/magic de `ServicioCargaEvidencia` (sin cambiar reglas de negocio de SP-214).
- Opcional: helper `construir_clave_evidencia(empresa_id, extension)` alineado con el patrón de `construir_clave_objeto` de archivos documentales, o generar la clave inline en el servicio con el mismo formato.
- El campo del modelo sigue llamándose `ruta_almacenamiento`; su semántica pasa a “clave de objeto en R2” para filas nuevas.

### Paso 3: Repositorio

Añadir al puerto `RepositorioEvidencia` (e implementación SQLAlchemy) algo equivalente a:

```text
async def obtener_empresa_id_por_calificacion(calificacion_id: UUID) -> UUID | None
```

Join: `CalificacionEstandarORM` → `AutoevaluacionORM.empresa_id`.  
Si no hay fila → el flujo de carga ya responde `CalificacionNoEncontradaError` (o unificar con `existe_calificacion`).

Sin cambios de contrato en `guardar` / `listar` / baja lógica.

### Paso 4: DTOs

Sin DTO nuevo. `RespuestaEvidencia.ruta_almacenamiento` sigue expuesta como hoy (ya era la ruta relativa; ahora será la clave). **No** exponer credenciales ni URL de R2.

Si el equipo prefiere ocultar la clave al cliente en una HU futura, no es alcance de SP-285 (el contrato actual ya la devuelve).

### Paso 5: Servicios

**`ServicioCargaEvidencia`:**

| Antes | Después |
|---|---|
| `raiz_configurada: bool` + `AlmacenLocal` | `r2_configurado: bool` + `AlmacenEvidencias` (R2 / memoria) |
| Clave `evidencias/{calificacion_id}/{uuid}{ext}` | Clave `evidencias/{empresa_id}/{uuid}{ext}` |
| 503 si no hay raíz local | 503 si no `r2_configurado` (`AlmacenamientoNoConfiguradoError`) |

Flujo (orden):

1. Si no `r2_configurado` → 503; no put.
2. Resolver `empresa_id` (y validar calificación).
3. Tope + magic **antes** de `guardar`.
4. Armar clave; `Evidencia.crear(... ruta_almacenamiento=clave ...)`.
5. `almacen.guardar`; si falla `repo.guardar` → `almacen.eliminar` y propagar.

**`ServicioDescargaEvidencia`:**

| Antes | Después |
|---|---|
| `raiz_almacenamiento: Path \| None` | `almacen: AlmacenEvidencias` (+ opcional `r2_configurado` si se quiere 503 explícito) |
| `_resolver_archivo` abre `Path` | `almacen.leer(evidencia.ruta_almacenamiento)`; `FileNotFoundError` → `ArchivoNoDisponibleError` |
| `ArchivoAutorizado.ruta: Path` | Cambiar a `contenido: bytes` (o nombre equivalente) |

`emitir_enlace`, auditoría y chequeo de rol escritor **sin cambios**.

Evidencias viejas solo en disco: `leer` fallará → `ARCHIVO_NO_DISPONIBLE` (404); documentado como migración manual, no como bug de esta HU.

### Paso 6: Router y DI

**DI** `presentation/dependencies/evidencia.py`:

- `obtener_almacen_evidencias()` (o reutilizar el patrón de `archivo_documental`): si `settings.r2_configurado` → `crear_almacen_r2`; si no → `AlmacenMemoria` dummy (servicio corta con 503).
- `obtener_servicio_carga_evidencia`: inyectar ese almacén + `r2_configurado`; **dejar de** construir `AlmacenLocal(raiz)`.
- `obtener_servicio_descarga_evidencia`: inyectar el mismo almacén; **dejar de** depender de `obtener_raiz_almacenamiento` para el camino feliz.
- `obtener_raiz_almacenamiento` puede quedar deprecado/unused o eliminarse si ningún caller lo usa tras el cambio.

**Router** `canjear_descarga`:

- Dejar de usar `FileResponse(path=...)`.
- Servir `Response` / `StreamingResponse` con `content=archivo.contenido`, `media_type` y `Content-Disposition` (sanitizar nombre como en SP-284).

Carga multipart y endpoints de metadatos: sin cambio de rutas HTTP.

### Paso 7: Excepciones

Reutilizar códigos existentes:

| Código | HTTP | Cuándo |
|---|---|---|
| `ALMACENAMIENTO_NO_CONFIGURADO` | 503 | Sin variables R2 en carga (y opcionalmente descarga) |
| `EVIDENCIA_INVALIDA` | 422 | MIME/magic/tamaño |
| `CALIFICACION_NO_ENCONTRADA` | 404 | Calificación ausente |
| `ARCHIVO_NO_DISPONIBLE` | 404 | Clave sin objeto en R2 (o legado solo-disco) |
| `ACCESO_DENEGADO` | 403 | `CONSULTA` en emisión/canje |
| `TOKEN_INVALIDO` / expirado | 401 | Token de descarga inválido |

Cuerpo: `exito`, `codigo`, `mensaje`, `detalle`.

### Paso 8: Pruebas

| Tipo | Casos |
|---|---|
| Unitario carga | Magic inválido → no `guardar`; fallo repo → `eliminar`; sin R2 → 503; clave contiene `empresa_id` (no `calificacion_id` como único segmento de carpeta); no se instancia `AlmacenLocal` en el DI de producción |
| Unitario descarga | `leer` OK → bytes; `FileNotFoundError` → `ArchivoNoDisponibleError`; RBAC/auditoría intactos |
| Integración | Override con `AlmacenMemoria` + `r2_configurado=True`; POST carga 201 + objeto en el doble; emitir enlace + canje 200 con el mismo binario; sin R2 → 503 en carga; `CONSULTA` sigue 403 en descarga |

Migrar `tests/integration/test_carga_evidencias.py` y `test_descarga_evidencias.py` desde override de `obtener_raiz_almacenamiento`/`tmp_path` hacia override de almacén (mismo espíritu que SP-284).  
Unitarios que prueban `AlmacenLocal` como adaptador pueden permanecer en `test_almacen_*`; no deben ser el camino de `ServicioCargaEvidencia` en producción.

### Paso 9: Documentación

- `docs/cloudflare-r2.md`: nota de que evidencias nuevas usan R2; legado local = migración manual.
- `ai-specs/specs/api-spec.yml`: actualizar descripción del canje si aún dice “bajo `ALMACENAMIENTO_LOCAL_RAIZ`”; el path y el JWT no cambian.
- No tocar `data-model.md` salvo aclarar semántica de `ruta_almacenamiento` como clave de objeto.

## 4. Orden de implementación

1. Paso 0 — rama `feature/SP-285-backend`
2. Paso 3 — `obtener_empresa_id_por_calificacion`
3. Paso 5 — servicios carga + descarga (TDD con `AlmacenMemoria`)
4. Paso 6 — DI + router de canje
5. Paso 8 — adaptar tests integración/unitarios
6. Paso 9 — docs / api-spec
7. `pytest` y cobertura ≥ 90 %

## 5. Lista de verificación de pruebas

- [ ] `pytest` con 0 fallos
- [ ] Cobertura ≥ 90 %
- [ ] Evidencia nueva: objeto en el doble/R2; descarga recupera los mismos bytes
- [ ] Flujo feliz de carga **no** construye `AlmacenLocal`
- [ ] Sin R2 → 503 y ninguna fila nueva
- [ ] Magic inválido → 422 y cero objetos en el doble
- [ ] `CONSULTA` no emite ni canjea descarga de evidencias (403)
- [ ] Tests existentes de metadatos/baja lógica de evidencias siguen verdes

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

## 8. Dependencias

Ninguna nueva. `boto3` / `AlmacenR2` ya están por SP-282.

## 9. Notas

- Rama `feature/SP-285-backend`.
- Preferir reutilizar `crear_almacen_r2` / patrón DI de `archivo_documental.py` para no duplicar settings.
- Compensación R2↔BD obligatoria en carga (igual que hoy con disco y que SP-284).
- No borrar `AlmacenLocal` del repo en esta HU; solo dejar de inyectarlo en evidencias.
- No cambiar el contrato JWT ni el hecho de que la descarga de evidencias exige rol escritor.
- SP-286 (Angular) y SP-287 (suite) quedan fuera.

## 10. Lista de verificación de la implementación

- [ ] Carga de evidencias usa R2 (o doble) con clave `evidencias/{empresa_id}/{uuid}{ext}`
- [ ] Descarga lee con `almacen.leer`; router sirve bytes, no `FileResponse` de disco
- [ ] DI de evidencias ya no instancia `AlmacenLocal` en el camino feliz
- [ ] 503 sin variables R2
- [ ] Legado local documentado como migración manual
- [ ] Tests verdes y cobertura ≥ 90 %
- [ ] Rama desde `develop`
