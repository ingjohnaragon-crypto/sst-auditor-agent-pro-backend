# Pruebas de integración HTTP

Validan endpoints clave del backend vía FastAPI + httpx + SQLite async
(`cliente_async` en `conftest.py`). No cubren fórmulas de dominio: esas
pertenecen a SP-147 (`tests/unit/domain/services/`).

## Fixtures

| Fixture | Uso |
|---|---|
| `cliente_async` | App ASGI con BD en memoria, usuarios y 3 estándares semilla |
| `usuarios_semilla` | Correos admin / consulta / inactivo y contraseña de prueba |
| `catalogo_semilla` | IDs de estándares sembrados (suma 85.00) |
| `obtener_token` / `bearer` | Login y header Authorization (`helpers_auth.py`) |

## Matriz endpoint → prueba → códigos

| Endpoint | Método | Archivo | Códigos cubiertos |
|---|---|---|---|
| `/api/v1/auth/login` | POST | `test_auth_login.py` | 200, 401, 422 |
| `/api/v1/auth/refresh` | POST | `test_auth_refresh.py` | 200, 401, 422 |
| `/api/v1/auth/yo` | GET | `test_auth_yo.py` | 200, 401 |
| Guard RBAC | GET auxiliar | `test_requerir_roles.py` | 200, 403 |
| `/api/v1/empresas` | POST/GET | `test_empresas.py` | 201, 200, 401, 403, 409 |
| `/api/v1/empresas/{id}` | GET | `test_empresas.py` | 200, 404 |
| `/api/v1/estandares-minimos` | GET | `test_estandares.py` | 200, 401, 422 |
| `/api/v1/autoevaluaciones` | POST/GET | `test_autoevaluacion_*.py` | 201, 200, 403, 404, 422 |
| `/api/v1/autoevaluaciones/{id}` | GET | `test_autoevaluacion_*.py` | 200, 404 |
| `.../calificaciones/{id}` | PUT | `test_autoevaluacion_*.py` | 200, 403, 404, 409, 422 |
| `.../finalizar` | POST | `test_autoevaluacion_*.py` | 200, 403, 409 |
| Matriz GTC 45 | CRUD anidado | `test_matriz_riesgos.py` | 200/201/204, 401, 403, 404, 422 |
| `PUT .../peligros/{id}/evaluacion` | PUT | `test_matriz_riesgos.py` | NP = ND×NE (201/200); extra `nivel_probabilidad` → 422 `ERROR_VALIDACION` (SP-199) |
| `PUT .../peligros/{id}/evaluacion` | PUT | `test_matriz_riesgos.py` | NR/I–IV/aceptabilidad (201/200 D1 ACEPTABLE); extra derivados → 422 (SP-200) |

Contrato de error esperado: `exito`, `codigo`, `mensaje` (y `detalle` opcional).

## Ejecución

```bash
# Solo integración (sin cobertura global del proyecto)
pytest -o addopts="" tests/integration -q

# Suite completa + cobertura ≥ 90 % (como CI)
pytest
```

## Relación con SP-147

| Ticket | Alcance |
|---|---|
| SP-147 | Cálculos de dominio (`calculos_estadisticos_sst`, utilidades) |
| SP-157 | Suites HTTP de endpoints (esta carpeta) |
