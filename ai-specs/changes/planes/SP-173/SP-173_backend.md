# Backend Implementation Plan: SP-173 Validar conectividad ping/pong backend-frontend (CORS)

## 1. Overview
Objetivo: Implementar y validar el soporte CORS para el endpoint de salud `GET /api/v1/ping` de modo que el frontend Angular pueda consumirlo desde `http://localhost:4200` y que peticiones desde orígenes no permitidos sean bloqueadas. Active stack: frontend-angular (contexto: el frontend consume `http://localhost:8000/api/v1/ping`).

Principios: configuración explícita de orígenes desde Settings (no '*'), pruebas TDD (tests unitarios e integración para preflight y override), y documentación OpenAPI/README.

## 2. Architecture Context
- Active stack: frontend-angular (Angular)
- Capas involucradas:
  - Infraestructura / Config
    - `src/infrastructure/config/settings.py` (nueva propiedad `origenes_cors: list[str]`)
    - `.env.example` (añadir `ORIGENES_CORS` ejemplo)
  - Presentation (HTTP)
    - `src/main.py` (registro de CORSMiddleware usando settings)
    - `src/presentation/routers/ping_router.py` (router GET /ping)
    - `src/presentation/api_router.py` o punto de montaje del `api_prefix`
  - Application / DTOs
    - `src/application/dto/respuesta_ping.py` (Pydantic/DTO RespuestaPing)
  - Tests
    - `tests/test_ping.py` (happy path)
    - `tests/test_cors.py` (preflight origen permitido y no permitido, override env)
  - Documentación
    - `ai-specs/specs/api-spec.yml` (OpenAPI) y `/docs` (si aplica)

### Subtask Mapping
No subtasks — plan derivado directamente de la HU SP-173.

## 3. Implementation Steps

#### Step 0: Create Feature Branch
- Branch: `feature/SP-173-backend`
- Commands:
  ```bash
  git checkout main && git pull origin main
  git checkout -b feature/SP-173-backend
  ```

#### Step 1: Settings y variables de entorno
- File: `src/infrastructure/config/settings.py`
- Añadir campo tipado:
  ```py
  from pydantic import BaseSettings
  from typing import List

  class Settings(BaseSettings):
      api_prefix: str = "/api/v1"
      origenes_cors: List[str] = ["http://localhost:4200"]
      # otros settings...
  
  settings = Settings()
  ```
- File: `.env.example` — añadir:
  ```env
  ORIGENES_CORS='["http://localhost:4200"]'
  ```
- Notas: documentar formateo esperado (JSON array) y cómo overridear en CI/entornos.

#### Step 2: Registro de CORS en el arranque
- File: `src/main.py`
- Antes de incluir routers, añadir:
  ```py
  from fastapi.middleware.cors import CORSMiddleware
  from infrastructure.config.settings import settings

  app.add_middleware(
      CORSMiddleware,
      allow_origins=settings.origenes_cors,
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```
- Verificar que `settings.origenes_cors` es una lista y no contiene `"*"` por defecto.

#### Step 3: Router ping
- File: `src/presentation/routers/ping_router.py`
- Crear router con path relativo `/ping` y tag `Salud`:
  ```py
  from fastapi import APIRouter
  from application.dto.respuesta_ping import RespuestaPing

  router = APIRouter()

  @router.get("/ping", response_model=RespuestaPing, tags=["Salud"])
  def ping():
      return RespuestaPing(mensaje="pong")
  ```
- Montaje: en el archivo donde se monta `api_router`, incluir: `app.include_router(api_router, prefix=settings.api_prefix)`, o si se usa un `api_router` central, agregar `api_router.include_router(ping_router.router)`.

#### Step 4: DTO RespuestaPing
- File: `src/application/dto/respuesta_ping.py`
- Contenido:
  ```py
  from pydantic import BaseModel

  class RespuestaPing(BaseModel):
      mensaje: str = "pong"
  ```
- Incluir ejemplos y descripciones en la clase para OpenAPI.

#### Step 5: Tests (TDD)
- Crear tests antes de implementar o como verificación posterior:
  - `tests/test_ping.py` — Caso feliz: `GET /api/v1/ping` → 200 y JSON `{ "mensaje": "pong" }`.
  - `tests/test_cors.py` — Preflight y orígenes:
    - Test preflight OPTION request con Origin igual a `http://localhost:4200` → respuesta 200 y cabeceras CORS apropiadas (`access-control-allow-origin: http://localhost:4200` o similar).
    - Test preflight OPTION request con Origin no permitido (ej. `http://malicious.local:4300`) → respuesta 200/403 según framework, pero sin cabecera `access-control-allow-origin` o con denegación. Afirmar que la cabecera `access-control-allow-origin` no es igual al origin inseguro.
    - Test de override: iniciar aplicación con `ORIGENES_CORS='["http://otro:4300"]'` y verificar comportamiento acorde.
- Herramientas: pytest + TestClient (FastAPI).

#### Step 6: OpenAPI y documentación
- File: `ai-specs/specs/api-spec.yml` — añadir definición del endpoint `/api/v1/ping` con schema `RespuestaPing` (nombre, tipo, ejemplo) y tag `Salud`.
- Actualizar `/docs` o README para describir cómo probar manualmente (curl, navegador).

#### Step 7: Manual E2E y evidencia
- Instrucciones que deberán aparecer en el PR (pasos para reproducir manualmente):
  1. Levantar backend: `uvicorn src.main:app --reload --port 8000`
  2. Levantar frontend: `ng serve` (desde repo frontend en http://localhost:4200)
  3. Abrir navegador en http://localhost:4200 y verificar que el componente raíz muestra `pong` y que la consola no registra errores CORS.
  4. Prueba negativa: servir frontend desde otro origen (e.g., `http://localhost:4300`) y verificar que la petición es bloqueada por CORS (evidencia: captura de consola y Network sin cabecera access-control-allow-origin igual al origin).
- Añadir capturas de pantalla o logs en la descripción del PR.

#### Step 8: Commits y PR
- Hacer commits pequeños y autocontenidos (configuración, router, DTO, tests, docs).
- Mensajes en español y convencionales. Ejemplo:
  ```
  feat(api): añadir endpoint GET /api/v1/ping (Resuelve SP-173)
  ```
- Abrir PR describiendo pruebas manuales y adjuntando evidencias.

## 4. Implementation Order
1. Step 0: Crear branch
2. Step 1: Añadir Settings y `.env.example`
3. Step 2: Registrar CORSMiddleware en `src/main.py`
4. Step 4: Crear DTO `RespuestaPing`
5. Step 3: Crear router `ping_router` y montar en `api_prefix`
6. Step 5: Escribir tests (TDD): `test_ping`, `test_cors`
7. Step 6: Actualizar OpenAPI (`ai-specs/specs/api-spec.yml`)
8. Step 7: Pruebas manuales e incluir evidencia en PR
9. Step 8: Commit, push y PR

## 5. Testing Checklist
- [ ] Tests unitarios y de integración pasan (`pytest`) con 0 fallos
- [ ] Tests de CORS: preflight permitido y no permitido cubiertos
- [ ] `GET /api/v1/ping` devuelve `200` y `{ "mensaje": "pong" }`
- [ ] Verificación manual desde `http://localhost:4200` sin errores CORS y bloqueo desde origen no permitido
- [ ] OpenAPI actualizado y documentación adjunta en PR

## 6. Tooling Reference
| Purpose | Command |
|---|---|
| Run backend (desarrollo) | `uvicorn src.main:app --reload --port 8000` |
| Tests | `pytest` |
| Lint (backend) | `ruff check .` o `flake8` |

## 7. Error Response Format
Usar formato estandarizado de errores (en español):
```json
{
  "success": false,
  "code": "ERROR_CODE",
  "message": "Descripción legible por humanos",
  "details": ["campo: mensaje de validación"]
}
```
HTTP mapping: 400 VALIDATION_ERROR | 404 NOT_FOUND | 409 CONFLICT | 422 BUSINESS_RULE_VIOLATION | 500 INTERNAL_ERROR

## 8. Dependencies
- FastAPI, uvicorn, pydantic, pytest (dev). Ya asumidos en el stack del backend mínimo.

## 9. Notes
- No usar `"*"` en allow_origins en entornos productivos.
- Documentar claramente el formato de `ORIGENES_CORS` en `.env.example` y en README.
- Mantener mensajes y nombres en español según estándar del proyecto.
- Diseñar tests para ser deterministas: arrancar la app en fixtures y usar TestClient para requests y preflight.

## 10. Implementation Verification Checklist
- [ ] Código probado y commits en branch feature/SP-173-backend
- [ ] Tests pasan y coverage local aceptable
- [ ] OpenAPI y docs actualizados
- [ ] PR con evidencia E2E (capturas, logs) abierto

---

He creado este plan en soporte de la subtarea SP-173. Sigue el flujo TDD y documenta la validación manual requerida para aceptación.

---

## Estado de implementación (os-develop SP-173)

- La configuración CORS, el DTO `RespuestaPing`, el router `GET /api/v1/ping`,
  OpenAPI y la mayor parte de los tests se entregaron en **SP-139**
  (rama base `feature/SP-139-backend`).
- SP-173 cierra la validación: test de override `ORIGENES_CORS` a nivel de
  preflight y checklist E2E documentado en `README.md`.
- Dependencia: frontend SP-172 con `ServicioSalud` consumiendo
  `http://localhost:8000/api/v1/ping`.
