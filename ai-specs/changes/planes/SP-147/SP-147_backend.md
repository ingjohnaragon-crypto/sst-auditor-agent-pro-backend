# Plan de implementación backend: SP-147 — Pruebas unitarias de cálculos con Pytest

## 1. Resumen
Auditar y fortalecer las pruebas unitarias de los cálculos estadísticos SST implementados en SP-146. El trabajo comprende completar casos límite, validar el contrato de la excepción, medir explícitamente la cobertura de los módulos estadísticos y documentar la matriz de escenarios.

La rama `develop` ya contiene:

- `calculos_estadisticos_sst.py`;
- `utilidades_matematicas.py`;
- pruebas nominales y de error;
- `pytest-cov` con umbral global del 90 %;
- documentación inicial de las fórmulas.

Por tanto, la implementación debe ampliar la base existente sin duplicarla ni modificar código productivo salvo que una nueva prueba demuestre un defecto real.

## Estimación de puntos de historia
<!-- STORY_POINTS:5 -->
- **HU total**: 5
- **Justificación**: la infraestructura y la suite base ya existen; el esfuerzo corresponde a análisis de brechas, casos de precisión y valores no finitos, contrato de excepción, cobertura dirigida, ajuste menor de CI y documentación.
- **Subtareas**:

| Subtarea | Puntos | Nota |
|---|---:|---|
| SP-196 | 3 | Ampliación parametrizada de pruebas y contrato de excepción. |
| SP-197 | 1 | Verificación de cobertura y ajuste descriptivo de CI. |
| SP-198 | 1 | README con matriz de casos límite y errores. |

<!-- /STORY_POINTS -->

## 2. Contexto de arquitectura
- **Stack activo**: `python-fastapi` — Python 3.12 + FastAPI.
- **Dominio**: objeto bajo prueba; no se prevén cambios funcionales.
- **Aplicación**: sin cambios.
- **Presentación**: sin cambios.
- **Infraestructura**: sin cambios.
- **Pruebas**: `tests/unit/domain/services/` y `tests/unit/domain/exceptions/`.
- **Configuración**: `pyproject.toml` y `.github/workflows/ci.yml`.
- **Documentación**: README de la suite y referencia en la guía de desarrollo.

### Mapeo de subtareas
| Clave | Resumen | Pasos |
|---|---|---|
| SP-196 | Escribir casos de prueba para utilidades estadísticas | Pasos 1, 2, 3 y 4 |
| SP-197 | Configurar cobertura de pruebas | Pasos 5 y 7 |
| SP-198 | Documentar casos límite y de error cubiertos | Paso 6 |

## 3. Pasos de implementación

### Paso 0: Crear la rama de funcionalidad
- Actualizar `develop` y crear `feature/SP-147-backend`.

```bash
git checkout develop
git pull --ff-only origin develop
git checkout -b feature/SP-147-backend
```

- Confirmar que no existan cambios locales ajenos al ticket antes de preparar el commit.

### Paso 1: Auditar la cobertura existente
- Revisar:
  - `src/domain/services/calculos_estadisticos_sst.py`;
  - `src/domain/services/utilidades_matematicas.py`;
  - `src/domain/exceptions/estadisticas_sst.py`;
  - sus pruebas actuales.
- Generar un reporte dirigido:

```bash
pytest -o addopts="" tests/unit/domain/services \
  --cov=src.domain.services.calculos_estadisticos_sst \
  --cov=src.domain.services.utilidades_matematicas \
  --cov-report=term-missing \
  --cov-fail-under=100
```

- Registrar líneas o ramas no ejercitadas.
- No crear pruebas redundantes si una parametrización existente ya demuestra el comportamiento.

### Paso 2: Probar el contrato de la excepción estadística
- **Crear** `tests/unit/domain/exceptions/test_estadisticas_sst.py`.
- Verificar que `ValorEstadisticoInvalidoError`:
  - hereda de `DomainException`;
  - expone `code == "VALOR_ESTADISTICO_INVALIDO"`;
  - expone `http_status == 422`;
  - conserva `message` y `str(error)`;
  - permite identificar el campo inválido en el mensaje.
- Mantener pruebas puras, sin inicializar FastAPI.

### Paso 3: Completar pruebas de utilidades matemáticas
- **Modificar** `tests/unit/domain/services/test_utilidades_matematicas.py`.
- Revisar y completar:
  - `ROUND_HALF_UP` para empate positivo y negativo;
  - cero con dos decimales;
  - valores enteros y `Decimal`;
  - valores negativos;
  - `NaN`, `Infinity` y `-Infinity`;
  - división con numerador positivo, cero y negativo;
  - denominador cero, negativo y no finito;
  - mensaje con nombre del denominador.
- Usar `pytest.mark.parametrize`.
- Comparar `Decimal` exactamente.

### Paso 4: Completar pruebas de cálculos SST
- **Modificar** `tests/unit/domain/services/test_calculos_estadisticos_sst.py`.
- Frecuencia:
  - comprobar explícitamente el factor predeterminado `240000`;
  - factor alternativo;
  - cero accidentes;
  - valores negativos;
  - horas/factor no positivos y no finitos;
  - redondeo final sin aproximaciones.
- Severidad:
  - incapacidad sola;
  - días cargados solos;
  - suma de ambos;
  - ambos en cero;
  - cada numerador negativo;
  - horas/factor inválidos y no finitos.
- Proyección:
  - primer período, período intermedio y último;
  - total de períodos personalizado;
  - acumulado cero;
  - acumulado no finito;
  - períodos cero, negativos y superiores al total.
- Comparación:
  - `MINIMIZAR` y `MAXIMIZAR` por debajo, en igualdad y por encima;
  - meta cero;
  - desviaciones con signo;
  - valor `10.004` frente a meta `10`;
  - meta positiva menor a `0.01`;
  - valores no finitos;
  - sentido inválido;
  - inmutabilidad y `slots` de `ResultadoMetaAnual`.
- Los casos deliberadamente fuera del contrato tipado deben usar un `type: ignore` específico.

### Paso 5: Verificar cobertura y actualizar CI
- **Revisar** `pyproject.toml`.
- Confirmar:
  - dependencia `pytest-cov`;
  - `--cov=src`;
  - `--cov-fail-under=90`;
  - `fail_under = 90`.
- No modificar `pyproject.toml` si estos valores siguen vigentes.
- **Modificar** `.github/workflows/ci.yml`:
  - renombrar `Run placeholder tests` a `Run tests with coverage`;
  - conservar `pytest tests/ -v`, ya que hereda `addopts`;
  - evitar una segunda ejecución redundante de pytest.
- Ejecutar cobertura dirigida con umbral de 100 %.
- Ejecutar cobertura global con umbral de 90 %.

### Paso 6: Documentar la matriz de casos
- **Crear** `tests/unit/domain/services/README.md`.
- Incluir:
  - módulos y funciones cubiertos;
  - casos nominales;
  - casos cero;
  - negativos;
  - valores no finitos;
  - denominadores inválidos;
  - límites de períodos;
  - sentidos de meta;
  - precisión previa al redondeo;
  - excepción esperada.
- Aclarar que:
  - `None` no pertenece a las firmas `Decimal | int`;
  - mypy rechaza ese uso;
  - una futura entrada HTTP deberá validarse con Pydantic.
- Incluir comandos para pruebas dirigidas y cobertura.
- **Modificar** `ai-specs/specs/development_guide.md` únicamente para enlazar el README y el comando dirigido; no repetir todas las fórmulas.

### Paso 7: Ejecutar verificación integral
- Pruebas dirigidas sin cobertura global:

```bash
pytest -o addopts="" tests/unit/domain/services tests/unit/domain/exceptions/test_estadisticas_sst.py
```

- Cobertura dirigida:

```bash
pytest -o addopts="" tests/unit/domain/services \
  --cov=src.domain.services.calculos_estadisticos_sst \
  --cov=src.domain.services.utilidades_matematicas \
  --cov-report=term-missing \
  --cov-fail-under=100
```

- Calidad y tipado:

```bash
ruff check src tests
mypy src
```

- Suite completa:

```bash
pytest
```

- Confirmar 0 fallos, 100 % dirigido y al menos 90 % global.

## 4. Orden de implementación
1. Paso 0: crear rama desde `develop`.
2. Paso 1: auditar la cobertura existente.
3. Paso 2: probar la excepción.
4. Paso 3: completar utilidades matemáticas.
5. Paso 4: completar cálculos SST.
6. Paso 5: validar cobertura y ajustar CI.
7. Paso 6: documentar la matriz de casos.
8. Paso 7: ejecutar verificación integral.

## 5. Lista de verificación de pruebas
- [ ] Pruebas actuales revisadas antes de añadir casos.
- [ ] Excepción de dominio cubierta.
- [ ] Factor predeterminado cubierto explícitamente.
- [ ] Valores `NaN`, `Infinity` y `-Infinity` cubiertos.
- [ ] Cero permitido y cero inválido diferenciados por campo.
- [ ] Ambos sentidos de meta e igualdad cubiertos.
- [ ] No hay falsos cumplimientos por redondeo.
- [ ] Meta positiva pequeña conserva su porcentaje.
- [ ] Resultado anual inmutable.
- [ ] Cobertura dirigida del 100 %.
- [ ] Cobertura global mínima del 90 %.
- [ ] Ruff y mypy strict aprobados.
- [ ] Suite completa sin regresiones.

## 6. Referencia de herramientas
| Propósito | Comando |
|---|---|
| Instalación/build | `pip install -r requirements.txt` |
| Pruebas | `pytest` |
| Pruebas dirigidas | `pytest tests/unit/domain/services --no-cov` |
| Cobertura | `pytest --cov --cov-report=html` |
| Lint | `ruff check src tests` |
| Tipado | `mypy src` |
| Ejecución | `uvicorn main:app --reload` |

## 7. Formato de respuesta de error
No se crean endpoints ni respuestas HTTP. Las pruebas validan la excepción:

```python
error = ValorEstadisticoInvalidoError(
    "El campo horas_trabajadas debe ser mayor que cero"
)
```

Contrato esperado:

```text
code = VALOR_ESTADISTICO_INVALIDO
http_status = 422
message = El campo horas_trabajadas debe ser mayor que cero
```

## 8. Dependencias
- No se agregan dependencias.
- `pytest`, `pytest-cov`, Ruff y mypy ya están configurados.
- No se requieren PostgreSQL, Alembic, Docker ni servicios externos.

## 9. Notas
- SP-147 depende funcionalmente de SP-146, ya fusionada en `develop`.
- Una prueba nueva que revele un defecto puede justificar un cambio mínimo en dominio, acompañado de una regresión; no ampliar el alcance funcional.
- No usar `pytest.approx` para `Decimal`.
- No probar métodos privados de forma directa cuando el comportamiento pueda demostrarse mediante la API pública.
- La cobertura es una señal, no el objetivo único: cada caso debe representar una regla o límite real.
- No incluir archivos `.openspec-cli/.tmp_*` ni configuraciones locales del workspace.

## 10. Lista de verificación de implementación
- [ ] Rama `feature/SP-147-backend` creada desde `develop`.
- [ ] Solo archivos relacionados con pruebas, cobertura y documentación.
- [ ] Contrato de excepción validado.
- [ ] Brechas reales de la suite cubiertas sin duplicación.
- [ ] CI nombra correctamente la ejecución con cobertura.
- [ ] README de casos límite creado.
- [ ] Código productivo sin cambios innecesarios.
- [ ] 100 % de cobertura dirigida.
- [ ] Al menos 90 % de cobertura global.
- [ ] Ruff, mypy y pytest aprobados.
- [ ] Plan y enriquecimiento incluidos en el commit de SP-147.
