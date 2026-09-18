# Plan de implementación backend: SP-157 — Suites de pruebas HTTP de endpoints clave

## 1. Resumen
Auditar, completar y documentar las suites de integración HTTP (Pytest + httpx) de los endpoints clave del backend, y endurecer su ejecución en CI.

La base ya existe en `develop` / ramas fusionadas previas:

- Auth: `test_auth_login.py`, `test_auth_refresh.py`, `test_auth_yo.py`, `test_requerir_roles.py`.
- Autoevaluación 0312: `test_autoevaluacion_flujo.py`, `test_autoevaluacion_errores.py`.
- Matriz GTC 45: `test_matriz_riesgos.py` (CRUD, 404, 403 CONSULTA).
- CI: paso `Run tests with coverage` → `pytest tests/ -v` con `--cov-fail-under=90`.
- SP-147: pruebas de dominio matemáticas (fuera de alcance; no duplicar).

Esta historia cierra **brechas** (empresas/estándares como suites dedicadas, huecos RBAC/HTTP residuales), publica una **matriz endpoint → prueba** y asegura que CI falle de forma explícita ante regresiones.

## Estimación de puntos de historia
<!-- STORY_POINTS:8 -->
- **HU total**: 8
- **Justificación**: gran parte de la suite ya existe; el esfuerzo está en inventario de brechas, consolidación de empresas/estándares, documentación HTTP, endurecimiento de CI y verificación sin regresiones.
- **Subtareas**:

| Subtarea | Puntos | Nota |
|---|---:|---|
| SP-226 | 3 | Auditoría auth/RBAC y huecos residuales. |
| SP-227 | 3 | Autoevaluación, matriz, empresas y estándares. |
| SP-228 | 2 | Endurecimiento CI + documentación operativa. |

<!-- /STORY_POINTS -->

## 2. Contexto de arquitectura
- **Stack activo**: `python-fastapi` — Python 3.12 + FastAPI.
- **Dominio / Aplicación / Presentación**: sin cambios funcionales previstos.
- **Infraestructura**: sin migraciones ni cambios de ORM.
- **Pruebas**: ampliar `tests/integration/`; reutilizar `conftest.py`, `helpers_auth.py`, semillas.
- **Configuración**: `.github/workflows/ci.yml`; `pyproject.toml` solo si se añaden markers.
- **Documentación**: `tests/integration/README.md` y enlace en `development_guide.md`.

### Mapeo de subtareas
| Clave | Resumen | Pasos |
|---|---|---|
| SP-226 | Pruebas de autenticación y roles | Pasos 1 y 2 |
| SP-227 | Autoevaluación, matriz, empresas, estándares | Pasos 1, 3 y 4 |
| SP-228 | CI automática y documentación | Pasos 5, 6 y 7 |

## 3. Pasos de implementación

### Paso 0: Crear la rama de funcionalidad
- Partir de `develop` actualizado (no de `feature/SP-147-backend`).

```bash
git checkout develop
git pull --ff-only origin develop
git checkout -b feature/SP-157-backend
```

- Incluir solo artefactos de SP-157 (plan, enriquecimiento, pruebas, CI, docs).
- No mezclar cambios locales ajenos (workspace, scripts temporales).

### Paso 1: Inventariar endpoints vs. pruebas existentes
- Listar rutas de:
  - `auth_router.py`
  - `empresas_router.py`
  - `estandares_router.py`
  - `autoevaluaciones_router.py`
  - `matriz_riesgos_router.py`
- Cruzar con `tests/integration/**/*.py`.
- Registrar en una tabla (luego irá al README):

| Endpoint | Método | Archivo de prueba | Códigos cubiertos | Brecha |
|---|---|---|---|---|
| `/auth/login` | POST | `test_auth_login.py` | 200, 401, 422 | … |

- Criterio: cada endpoint clave debe tener ≥1 feliz y ≥1 error relevante.
- No reescribir suites ya verdes; solo marcar huecos.

### Paso 2: Cerrar brechas de autenticación y RBAC (SP-226)
- Revisar:
  - `tests/integration/test_auth_login.py`
  - `tests/integration/test_auth_refresh.py`
  - `tests/integration/test_auth_yo.py`
  - `tests/integration/test_requerir_roles.py`
- Completar solo si falta:
  - refresh inválido/expirado/malformado;
  - `/auth/yo` con Bearer inválido;
  - 403 de escritura SST para `CONSULTA` (empresa, matriz o autoevaluación);
  - aserción de mensaje genérico sin enumeración de usuarios.
- Reutilizar `obtener_token` / `helpers_auth.py` y `usuarios_semilla`.
- No tocar lógica de JWT salvo bug demostrado con regresión.

### Paso 3: Suites dedicadas de empresas y estándares (SP-227)
- **Crear** `tests/integration/test_empresas.py` si el inventario confirma que empresas solo se usan como setup:
  - `POST /empresas` → 201 (escritor);
  - `POST` duplicado → 409 `NIT_DUPLICADO`;
  - `POST` con `CONSULTA` → 403;
  - `GET /empresas` → 200;
  - `GET /empresas/{id}` → 200 y 404;
  - sin token → 401.
- **Crear** `tests/integration/test_estandares.py` extrayendo/ampliando los casos hoy embebidos en `test_autoevaluacion_errores.py`:
  - listado completo autenticado;
  - filtro `ciclo_phva=PLANEAR` (u otro válido);
  - valor inválido → 422;
  - sin token → 401.
- Mantener AAA y nombres `test_should_…_when_…`.

### Paso 4: Completar autoevaluación y matriz (SP-227)
- Auditar `test_autoevaluacion_flujo.py` y `test_autoevaluacion_errores.py`:
  - flujo crear → calificar → finalizar → listar/detalle;
  - empresa inexistente, estandar fantasma, finalizar indebido.
- Auditar `test_matriz_riesgos.py`:
  - matriz agregada;
  - CRUD proceso/peligro/evaluación/control;
  - 404 de recursos fantasma;
  - 403 CONSULTA en escritura.
- Añadir solo casos faltantes del inventario del Paso 1.
- Verificar contrato de error: `exito`, `codigo`, `mensaje`.

### Paso 5: Endurecer CI (SP-228)
- Revisar `.github/workflows/ci.yml`.
- Estado actual: paso `Run tests with coverage` ejecuta `pytest tests/ -v` y hereda `addopts` de `pyproject.toml`.
- Cambios mínimos sugeridos:
  - Mantener el nombre claro del paso.
  - Asegurar que el job falle si pytest sale ≠ 0 (por defecto ya lo hace).
  - Opcional: añadir tras pytest un echo o step que muestre que el umbral es 90 % (sin duplicar la corrida).
  - Opcional y preferible si el tiempo lo permite: pasos `ruff check src tests` y `mypy src` **después** de instalar deps; no añadir paquetes nuevos.
- No bajar `fail_under` / `--cov-fail-under`.
- No introducir codecov u otras herramientas salvo decisión explícita fuera de ticket.

### Paso 6: Documentar matriz HTTP y diferenciar SP-147
- **Crear** `tests/integration/README.md` con:
  - propósito (integración HTTP vs. unitarias de dominio);
  - tabla endpoint → archivo → códigos;
  - fixtures clave (`cliente_async`, `usuarios_semilla`);
  - comandos:

```bash
# Solo integración (sin cobertura global del proyecto)
pytest -o addopts="" tests/integration -q

# Suite completa + cobertura ≥ 90 % (como CI)
pytest
```

- **Modificar** `ai-specs/specs/development_guide.md`:
  - enlace a `tests/integration/README.md`;
  - aclarar: SP-147 = cálculos de dominio; SP-157 = endpoints HTTP.

### Paso 7: Verificación integral
```bash
pytest -o addopts="" tests/integration -q
ruff check src tests
mypy src
pytest
```

- Confirmar: 0 fallos, cobertura global ≥ 90 %, CI local equivalente al workflow.
- Si una prueba nueva revela un bug de API: hotfix mínimo + regresión; no ampliar alcance funcional.

## 4. Orden de implementación
1. Paso 0: rama desde `develop`.
2. Paso 1: inventario endpoint ↔ prueba.
3. Paso 2: brechas auth/RBAC.
4. Paso 3: suites empresas y estándares.
5. Paso 4: brechas autoevaluación/matriz.
6. Paso 5: CI.
7. Paso 6: README + guía.
8. Paso 7: verificación completa.

## 5. Lista de verificación de pruebas
- [ ] Inventario documentado sin endpoints clave huérfanos.
- [ ] Auth: login, refresh, yo — éxito y error.
- [ ] RBAC: CONSULTA denegado en escritura SST.
- [ ] Empresas: CRUD mínimo + 401/403/404/409.
- [ ] Estándares: listado + filtro PHVA + 422.
- [ ] Autoevaluación: flujo feliz y errores de negocio.
- [ ] Matriz: CRUD + 404 + 403.
- [ ] Contrato de error uniforme.
- [ ] `pytest` ≥ 90 % cobertura global.
- [ ] Ruff y mypy sin errores nuevos.
- [ ] CI ejecuta la misma suite y falla ante regresiones.

## 6. Referencia de herramientas
| Propósito | Comando |
|---|---|
| Instalación | `pip install -r requirements.txt` |
| Integración | `pytest -o addopts="" tests/integration -q` |
| Suite + cobertura | `pytest` |
| Lint | `ruff check src tests` |
| Tipado | `mypy src` |
| CI local | `pytest tests/ -v` |

## 7. Formato de respuesta de error
Las pruebas deben asertar el contrato HTTP vigente:

```json
{
  "exito": false,
  "codigo": "CODIGO_DOMINIO_O_VALIDACION",
  "mensaje": "Descripción legible",
  "detalle": null
}
```

Códigos frecuentes: `CREDENCIALES_INVALIDAS`, `TOKEN_INVALIDO`, `ACCESO_DENEGADO`, `EMPRESA_NO_ENCONTRADA`, `NIT_DUPLICADO`, `ERROR_VALIDACION`, códigos 404 de matriz.

## 8. Dependencias
- Ninguna nueva.
- Reutilizar pytest, pytest-asyncio, pytest-cov, httpx, aiosqlite.
- No Docker adicional: la suite de integración usa la DB de prueba del `conftest` existente.

## 9. Notas
- SP-157 ≠ SP-147: no tocar `calculos_estadisticos_sst` salvo dependencia accidental.
- Preferir ampliar archivos existentes antes de crear duplicados.
- No incluir `.openspec-cli/.tmp_*` ni `*.code-workspace` en el commit.
- Si `feature/SP-147-backend` aún no está mergeada, implementar SP-157 desde `develop` limpio; los cambios de SP-147 no son prerequisito de SP-157.
- El título del ticket dice “unitarias”; en la práctica del proyecto los endpoints se prueban como **integración HTTP** — documentarlo en el README para evitar confusión.

## 10. Lista de verificación de implementación
- [ ] Rama `feature/SP-157-backend` desde `develop`.
- [ ] Inventario y README de integración publicados.
- [ ] Suites empresas/estándares dedicadas si había hueco.
- [ ] Auth/RBAC/autoevaluación/matriz sin brechas críticas.
- [ ] CI endurecido y documentado.
- [ ] Guía de desarrollo actualizada.
- [ ] Suite completa verde y cobertura ≥ 90 %.
- [ ] Commit limitado a SP-157 (+ plan/enriquecimiento).
