# Plan de implementación backend: SP-245 Catálogo documental del ciclo PHVA

## 1. Resumen

Épica de catálogo SG-SST por fases PHVA (PLANEAR / HACER / VERIFICAR / ACTUAR): diez tipos obligatorios sembrados, documento por empresa+tipo con estados `PENDIENTE` → `CARGADO` → `REVISADO`, binario en Cloudflare R2 (puerto de SP-249) y metadatos en PostgreSQL. Complementa evidencias del diagnóstico (SP-151…153): aquí el archivo cuelga del **tipo de documento**, no de un ítem de calificación.

**Dependencia cumplida:** SP-249 (R2 + `AlmacenMemoria` + offline tests). Reutilizar `AlmacenEvidencias` / `crear_almacen_r2` / magic+tope 10 MiB. **No** reimplementar cliente R2 ni SP-150 (AWS).

**Fuera de este plan de backend:** la pantalla Angular es **SP-267** (`os-plan` / `os-develop` en `sst-auditor-agent-pro-frontend`). Este archivo cubre el orden de subtareas de API/datos y el detalle de las de backend.

Stack activo: `python-fastapi` (Python 3.12 + FastAPI).

## Estimación de puntos de historia

<!-- STORY_POINTS:20 -->
- **HU total**: 20 (Fibonacci compuesto de subtareas: 2+5+5+5+3)
- **Justificación**: Confirma el enriquecimiento. Semilla + modelo/ORM + API HTTP + vínculo opcional 0312 + pantalla (frontend). El cliente R2 no se reestima (SP-249).
- **Subtareas**:
  | Subtarea | Puntos | Nota |
  |---|---|---|
  | SP-264 | 2 | Semilla idempotente de 10 tipos |
  | SP-265 | 5 | Modelo `DocumentoEmpresa` + migración |
  | SP-266 | 5 | API listar/cargar/descargar/PATCH |
  | SP-267 | 5 | Pantalla Angular (otro repo) |
  | SP-268 | 3 | Vínculo tipo ↔ estándar 0312 |
<!-- /STORY_POINTS -->

## 2. Contexto de arquitectura

- Stack activo: `python-fastapi` (Python 3.12 + FastAPI)
- Puerto de bytes: `AlmacenEvidencias` (`guardar` / `leer` / `eliminar`) — prod `AlmacenR2`, tests `AlmacenMemoria`
- Clave R2 de este catálogo: `documentos/{empresa_id}/{tipo_codigo}/{uuid}{ext}` (distinta de `evidencias/...` y del repositorio libre SP-284)
- Validación de archivo: misma regla que evidencias/archivos (PDF/JPEG/PNG, magic, 10 MiB, `leer_con_tope`)
- RBAC: `CONSULTA` lista/descarga; `ADMINISTRADOR` / `AUDITOR_SST` cargan y marcan `REVISADO`
- Sin `R2_*` → carga `503` `ALMACENAMIENTO_NO_CONFIGURADO`, sin fila a medias
- Respuestas HTTP: **sin** URL permanente de bucket ni secretos; descarga = Bearer + streaming (o enlace firmado breve si se decide; preferir streaming como SP-284)

| Capa | Archivos previstos (backend) |
|---|---|
| Domain | `tipo_documento_sst.py`, `documento_empresa.py`, repos, excepciones |
| Application | DTOs, mappers, `servicio_documentos_empresa.py` |
| Infrastructure | ORM, repos SQLAlchemy, semilla, migración Alembic |
| Presentation | `catalogo_documentos_router` / `documentos_empresa_router`, DI |
| Docs | `api-spec.yml`, `data-model.md` |
| Tests | unitarios + integración HTTP con `AlmacenMemoria` |
| Frontend (SP-267) | `features/documentos/` en el otro repo |

### Diez tipos (semilla)

| Fase | Documentos |
|---|---|
| PLANEAR | Política de SST, Matriz de riesgos (GTC 45), Plan de trabajo anual, Programa de capacitación |
| HACER | Registros de entrega de EPP, Actas de COPASST o Vigía, Reportes de accidentes (FURAT) |
| VERIFICAR | Indicadores de gestión, Informe de auditoría interna |
| ACTUAR | Plan de mejora |

Códigos estables (propuesta; fijar en semilla/JSON): p. ej. `POLITICA_SST`, `MATRIZ_RIESGOS_GTC45`, `PLAN_TRABAJO_ANUAL`, `PROGRAMA_CAPACITACION`, `REGISTRO_EPP`, `ACTAS_COPASST`, `FURAT`, `INDICADORES_GESTION`, `AUDITORIA_INTERNA`, `PLAN_MEJORA`.

### Endpoints (contrato enriquecido)

| Método | Ruta | Notas |
|---|---|---|
| `GET` | `/api/v1/catalogo-documentos` | Tipos: id, nombre, fase, obligatorio, descripcion |
| `GET` | `/api/v1/empresas/{empresa_id}/documentos` | Por tipo: estado, fecha_carga, nombre_original; **no** exponer `clave_objeto` al cliente |
| `POST` | `/api/v1/empresas/{empresa_id}/documentos/{tipo_id}/archivo` | multipart `archivo` → 201 CARGADO |
| `GET` | `/api/v1/empresas/{empresa_id}/documentos/{tipo_id}/archivo` | binario autenticado |
| `PATCH` | `/api/v1/empresas/{empresa_id}/documentos/{tipo_id}` | `{ "estado": "REVISADO" }` solo desde CARGADO |

Avance del gestor (UI): `(no_PENDIENTE / total) * 100` con datos del GET (el backend puede devolver conteos o dejar el cálculo al front; preferir campos claros por documento).

### Mapeo de subtareas

| Subtarea | Resumen | Pasos de implementación |
|---|---|---|
| SP-264 | Sembrar catálogo por fase | Paso 1–2 |
| SP-265 | Modelar documento y estados | Paso 3–4 |
| SP-266 | Publicar API | Paso 5–8 |
| SP-268 | Vínculo con estándar 0312 | Paso 9 |
| SP-267 | Pantalla gestor (frontend) | Fuera de este repo — plan aparte |

## 3. Pasos de implementación

### Paso 0: Rama y prerequisitos

```bash
git checkout develop
git pull origin develop
git checkout -b feature/SP-264-backend   # o feature/SP-245-backend si se entrega en un solo PR
```

Preferencia de entrega: **un PR por subtarea** (`feature/SP-264-backend`, …) para PRs revisables. Alternativa: rama épica larga solo si el equipo lo acuerda.

Verificar en `develop`: `AlmacenR2`, `AlmacenMemoria`, `leer_con_tope`, tests offline SP-287.

### Paso 1 (SP-264): Migración de catálogo de tipos

- Tabla `tipos_documento_sst` (nombre final alineado a convención del repo): `id`, `codigo` (unique), `nombre`, `fase` (enum/check), `descripcion`, `obligatorio` (bool, default true), timestamps si aplica.
- **No** tocar `estandares_minimos`.

### Paso 2 (SP-264): Semilla idempotente

- Script/JSON de los 10 tipos + función `sembrar_tipos_documento_sst` (mismo patrón que `sembrar_estandares_minimos` / `sembrar_catalogos_gtc45`).
- Enganchar en `scripts.sembrar_datos`.
- Test: ejecutar dos veces → siguen 10 filas, mismos códigos; conteo de estándares 0312 invariante.

### Paso 3 (SP-265): Dominio

- Enums: `FasePhvaDocumento` (`PLANEAR`…), `EstadoDocumentoEmpresa` (`PENDIENTE`, `CARGADO`, `REVISADO`).
- `TipoDocumentoSst` (lectura de catálogo).
- `DocumentoEmpresa.crear` / transiciones: factory con invariantes (estado inicial PENDIENTE sin clave; al cargar exige clave+metadatos y pasa a CARGADO; `marcar_revisado` solo desde CARGADO → si no, conflicto de dominio → 409).
- Helper `construir_clave_documento(empresa_id, tipo_codigo, extension)` → `documentos/{empresa_id}/{tipo_codigo}/{uuid}{ext}`.
- Excepciones: documento no encontrado, transición inválida, tipo no encontrado, reutilizar `ArchivoInvalidoError` / `AlmacenamientoNoConfiguradoError` donde encaje.

### Paso 4 (SP-265): ORM + repositorio

- ORM `documento_empresa` (+ FK a empresa y tipo).
- Unique `(empresa_id, tipo_id)`.
- `RepositorioDocumentoEmpresa` / `RepositorioTipoDocumentoSst`: listar tipos, listar/obtener por empresa+tipo, guardar, actualizar.
- Migración Alembic. Tests de unicidad y factory.

**Nota de producto:** el enriquecimiento habla de “como máximo un vigente”. Con unique estricto no hay histórico; si más adelante se necesita historial, sería soft-replace de clave (SP-266) sin segunda fila.

### Paso 5 (SP-266): Servicio de aplicación

- `listar_catalogo`, `listar_por_empresa` (si no hay fila, presentar como PENDIENTE virtual o materializar lazy — **decidir**: preferir **vista**: GET no inserta filas; solo POST crea/actualiza).
- `cargar(tipo_id, archivo…)`: validar → R2 `guardar` → persistir CARGADO; si ya había clave, `eliminar` la anterior tras éxito (o antes con compensación).
- `descargar`: sesión + `almacen.leer`.
- `marcar_revisado`.
- Sin R2 configurado → 503 antes de escribir.

### Paso 6 (SP-266): DTOs y mappers

- Respuestas **sin** `clave_objeto` al cliente.
- Request PATCH con `estado: REVISADO` validado.

### Paso 7 (SP-266): Routers y DI

- Registrar routers bajo `/api/v1`.
- DI: mismo patrón que `archivo_documental` / evidencias (`obtener_almacen` + `r2_configurado`).
- Auth: `obtener_usuario_actual` / `requerir_rol_escritor`.

### Paso 8 (SP-266): Tests HTTP

Con `AlmacenMemoria`, sin red:

- Semilla + GET catálogo = 10.
- Alta feliz → CARGADO + objeto en memoria.
- Magic inválido → 422, sin objeto ni fila CARGADO.
- Segunda carga reemplaza clave / borra objeto viejo.
- `CONSULTA` POST → 403; GET archivo OK.
- Descarga sin sesión → 401.
- PATCH REVISADO desde PENDIENTE → 409; desde CARGADO → 200.
- Sin R2 → 503 en POST.

### Paso 9 (SP-268): Vínculo tipo ↔ estándar 0312

- Tabla `tipo_documento_estandar (tipo_id, estandar_id)` unique compuesto.
- Semilla opcional / endpoints de lectura (p. ej. incluir `estandares_ids` en catálogo o `GET .../tipos/{id}/estandares`).
- No copia objeto R2. Tipo sin vínculo sigue cargable.
- Tests: tipo sin vínculo carga; vínculo no duplica bytes.

### Paso 10: Documentación

- `ai-specs/specs/api-spec.yml` — paths nuevos.
- `ai-specs/specs/data-model.md` — tablas.
- No variables R2 nuevas.

### Paso 11 (SP-267, recordatorio frontend)

En el repo frontend, tras SP-266 en `develop`:

```bash
os-plan SP-267   # en sst-auditor-agent-pro-frontend
os-develop SP-267
```

Feature `documentos`, pestañas PHVA, avance `(no pendientes/total)*100`, sin SDK R2.

## 4. Orden de implementación

1. Paso 0 — rama(s) desde `develop`
2. SP-264 — Pasos 1–2 (semilla)
3. SP-265 — Pasos 3–4 (modelo)
4. SP-266 — Pasos 5–8 (API + tests)
5. SP-268 — Paso 9 (vínculo 0312)
6. Paso 10 — docs OpenAPI / data-model
7. SP-267 — plan/develop en frontend (paralelo solo tras contrato de SP-266 estable)

## 5. Lista de verificación de pruebas

- [ ] Semilla dos veces → 10 tipos; estándares 0312 intactos
- [ ] `pytest` offline (`AlmacenMemoria`), sin LocalStack
- [ ] Cobertura ≥ 90 %
- [ ] Inválido / tope / 401 / 403 / 409 / 503 cubiertos
- [ ] Segunda carga reemplaza objeto anterior
- [ ] Cliente nunca recibe URL de bucket ni `clave_objeto` en JSON público
- [ ] SP-150 no reaparece (sin disco de documentos en prod)

## 6. Referencia de herramientas

| Propósito | Comando |
|---|---|
| Build | `poetry install` / `pip install -r requirements.txt` |
| Test | `pytest` |
| Run | `poetry run uvicorn src.main:app --reload` |
| Coverage | `pytest --cov --cov-report=html` |
| Semilla | `poetry run python -m scripts.sembrar_datos` |

## 7. Formato de respuesta de error

```json
{
  "exito": false,
  "codigo": "ARCHIVO_INVALIDO",
  "mensaje": "…",
  "detalle": null
}
```

Códigos esperados: `ARCHIVO_INVALIDO` (422), `ALMACENAMIENTO_NO_CONFIGURADO` (503), `ACCESO_DENEGADO` (403), `TOKEN_INVALIDO`/401, `CONFLICTO_ESTADO` o equivalente (409), `NO_ENCONTRADO` (404).

## 8. Dependencias

Ninguna librería nueva. Reutilizar boto3/`AlmacenR2`, validación de evidencias, auth JWT, patrón de semilla existente.

## 9. Notas

- Jira no estuvo reachable al generar este plan (DNS); fuente: `SP-245_enriched.md.applied`.
- Distinguir este catálogo del **repositorio libre** SP-284 (`/empresas/{id}/archivos`): propósitos y claves distintas.
- Preferir streaming Bearer frente a URL firmada R2 (menos superficie; alineado a SP-284).
- Entregar por subtarea reduce riesgo de PRs enormes de 20 puntos.
- Primera implementación sugerida tras aprobar este plan: `os-develop SP-264` (o plan fino de SP-264 si se quiere un `_backend.md` por subtarea).

## 10. Lista de verificación de la implementación

- [ ] SP-264 semilla idempotente
- [ ] SP-265 modelo + unique empresa/tipo + clave R2
- [ ] SP-266 API completa y tests offline
- [ ] SP-268 vínculo catálogo 0312
- [ ] Docs api-spec / data-model
- [ ] SP-267 planificado/desarrollado en frontend
- [ ] Sin AWS/S3/VPC ni volumen de documentos en servidor
