# Ticket enriquecido: SP-147 — Escribir pruebas unitarias de cálculos con Pytest

## Descripción original



Verificar solidez de cálculos aritméticos en el backend de Python.



## Descripción mejorada

Fortalecer y documentar la suite unitaria de los cálculos estadísticos SST incorporados en SP-146. La validación debe cubrir las APIs públicas de:

- `src/domain/services/calculos_estadisticos_sst.py`;
- `src/domain/services/utilidades_matematicas.py`;
- `src/domain/exceptions/estadisticas_sst.py`.

El repositorio ya contiene pruebas nominales y configuración global de `pytest-cov` con umbral del 90 %. Esta historia no debe duplicarlas: debe auditar la cobertura existente, completar los escenarios faltantes, comprobar explícitamente la cobertura de los módulos estadísticos y documentar la matriz de casos.

Las pruebas usarán `Decimal` con aserciones exactas, `pytest.mark.parametrize` para familias de entradas y patrón Arrange-Act-Assert. No se usarán aproximaciones de punto flotante, base de datos, red, FastAPI ni mocks innecesarios.

Los valores `None` permanecen fuera de las firmas públicas (`Decimal | int`); su rechazo corresponde al tipado estricto y, cuando exista una futura entrada HTTP, a Pydantic. Las pruebas de dominio deben centrarse en valores numéricos válidos, negativos, cero, no finitos, límites temporales y sentidos de meta inválidos.

## Criterios de aceptación

- [ ] Todas las funciones públicas de los dos módulos de servicios tienen al menos un caso nominal y un caso límite.
- [ ] Frecuencia y severidad cubren cero, factor predeterminado, factor alternativo, valores negativos, denominadores no positivos y valores no finitos.
- [ ] Proyección anual cubre primer período, período intermedio, último período, total personalizado y rangos inválidos.
- [ ] Comparación de metas cubre `MINIMIZAR`, `MAXIMIZAR`, igualdad, meta cero, desviaciones positivas/negativas y precisión cercana al límite.
- [ ] Se verifica que no haya redondeos intermedios al decidir el cumplimiento.
- [ ] Se comprueba la inmutabilidad de `ResultadoMetaAnual`.
- [ ] Se comprueban `code`, `http_status` y mensaje de `ValorEstadisticoInvalidoError`.
- [ ] Las pruebas dirigidas de los módulos estadísticos alcanzan 100 % de líneas y ramas ejecutables.
- [ ] La suite completa mantiene cobertura global igual o superior al 90 %.
- [ ] El workflow de CI identifica correctamente el paso como pruebas con cobertura y falla si no se alcanza el umbral.
- [ ] Existe documentación legible de entradas, resultado y errores para cada familia de casos.
- [ ] Ruff y mypy strict finalizan sin errores.



## Campos y endpoints

No se crean campos, endpoints, DTO, tablas ni migraciones. El alcance es exclusivamente de pruebas, configuración de cobertura y documentación.

- Objetivos bajo prueba:
  - `calcular_tasa_frecuencia`;
  - `calcular_tasa_severidad`;
  - `proyectar_valor_anual`;
  - `comparar_meta_anual`;
  - `redondear_dos_decimales`;
  - `validar_no_negativo`;
  - `validar_positivo`;
  - `dividir_seguro`;
  - `ValorEstadisticoInvalidoError`.
- Comando de cobertura dirigida:

```bash
pytest -o addopts="" tests/unit/domain/services \
  --cov=src.domain.services.calculos_estadisticos_sst \
  --cov=src.domain.services.utilidades_matematicas \
  --cov-report=term-missing \
  --cov-fail-under=100
```

- Comando de cobertura global: `pytest`, usando `addopts` y `fail_under = 90` de `pyproject.toml`.



## Archivos a crear o modificar

- `tests/unit/domain/services/test_calculos_estadisticos_sst.py` — Pruebas — Ampliar los escenarios faltantes de tasas, proyección y metas.
- `tests/unit/domain/services/test_utilidades_matematicas.py` — Pruebas — Ampliar validación de redondeo, finitud y división segura.
- `tests/unit/domain/exceptions/test_estadisticas_sst.py` — Pruebas — Crear pruebas del contrato de la excepción.
- `tests/unit/domain/services/README.md` — Documentación — Crear la matriz de casos nominales, límites y errores.
- `pyproject.toml` — Configuración — Verificar la configuración existente; modificarla solo si no permite medir correctamente los módulos o el umbral global.
- `.github/workflows/ci.yml` — CI — Renombrar “Run placeholder tests” a “Run tests with coverage” y conservar la ejecución de `pytest tests/ -v`, que hereda la configuración del proyecto.
- `ai-specs/specs/development_guide.md` — Documentación — Referenciar la suite y el comando de cobertura dirigida si no están documentados.



## Casos de prueba unitarios

- Frecuencia con factor predeterminado y resultado exacto.
- Frecuencia con factor alternativo.
- Frecuencia con cero accidentes.
- Frecuencia con accidentes negativos, horas cero/negativas y factor cero/negativo.
- Frecuencia con horas o factor `NaN`/`Infinity`.
- Severidad con incapacidad, días cargados, ambos y ambos en cero.
- Severidad con cada numerador negativo y denominadores inválidos.
- Proyección en períodos 1, intermedio y final.
- Proyección con acumulado cero y total de períodos personalizado.
- Proyección con acumulado negativo, períodos cero/negativos y transcurridos mayores al total.
- Metas de minimización y maximización por debajo, en igualdad y por encima.
- Meta cero sin división por cero.
- Meta positiva menor que `0.01` conserva el cálculo porcentual.
- Valor `10.004` frente a meta `10` no se considera cumplido al minimizar.
- Desviación absoluta y porcentual con signo correcto.
- Sentido de meta inválido genera excepción de dominio.
- `ResultadoMetaAnual` no permite mutación.
- Redondeo `ROUND_HALF_UP` para positivos, negativos, cero y empate.
- Valores `NaN` e infinitos generan excepción controlada.
- La excepción expone `VALOR_ESTADISTICO_INVALIDO`, estado `422` y el mensaje recibido.



## Requisitos no funcionales

- Python 3.12 y pytest según las versiones fijadas por el proyecto.
- Pruebas deterministas, síncronas, sin I/O ni estado compartido.
- Tiempo objetivo de la suite dirigida inferior a dos segundos en CI.
- 100 % de cobertura de líneas en los módulos estadísticos y mínimo global del 90 %.
- Nombres de pruebas con patrón `test_should_<resultado>_when_<condicion>`.
- Tipado completo; los `type: ignore` deberán incluir código específico y limitarse a pruebas deliberadas de entradas fuera de contrato.
- Ninguna dependencia nueva.
- La documentación no debe duplicar fórmulas; debe enlazar la guía de desarrollo como fuente normativa.



## Puntos de historia



**5** — La base de pruebas y cobertura ya existe; el esfuerzo se concentra en auditar brechas, añadir regresiones de precisión, validar la excepción, ajustar CI y documentar la matriz de casos.



## Subtareas



### Subtarea: SP-196 — Escribir casos de prueba para utilidades estadísticas



#### Descripción original



Cubrir con Pytest las funciones de tasa de accidentalidad y metas anuales.



#### Descripción mejorada

Auditar y ampliar `test_calculos_estadisticos_sst.py` y `test_utilidades_matematicas.py` para cubrir todas las rutas públicas de frecuencia, severidad, proyección, comparación, validación y redondeo. Reutilizar parametrización, realizar aserciones exactas con `Decimal` y agregar pruebas específicas del contrato de `ValorEstadisticoInvalidoError`.

#### Criterios de aceptación

- [ ] Cada función pública tiene casos nominales, de límite y error.
- [ ] Se cubren valores cero, negativos, no finitos y denominadores inválidos.
- [ ] Se cubren ambos sentidos de meta, meta cero y precisión previa al redondeo.
- [ ] Se verifica el contrato de la excepción de dominio.
- [ ] Las pruebas son deterministas y no requieren infraestructura.



#### Puntos de historia



**3** — Ampliación y organización de una suite parametrizada con múltiples ramas matemáticas.







### Subtarea: SP-197 — Configurar cobertura de pruebas (coverage)



#### Descripción original



Integrar pytest-cov para medir porcentaje de cobertura del módulo de cálculos.



#### Descripción mejorada

Validar la integración existente de `pytest-cov` en `pyproject.toml`, ejecutar una medición dirigida con umbral del 100 % para los módulos estadísticos y conservar el umbral global del 90 %. Actualizar el nombre del paso de CI para que refleje que `pytest tests/ -v` ejecuta pruebas con cobertura, sin duplicar opciones ya definidas en `addopts`.

#### Criterios de aceptación

- [ ] La cobertura dirigida de los módulos estadísticos es 100 %.
- [ ] La cobertura global permanece al menos en 90 %.
- [ ] CI falla cuando no se cumple el umbral configurado.
- [ ] El paso de GitHub Actions se denomina “Run tests with coverage”.
- [ ] No se agregan herramientas de cobertura redundantes.



#### Puntos de historia



**1** — La dependencia y configuración ya existen; requiere validación y un ajuste menor de CI.







### Subtarea: SP-198 — Documentar casos límite y de error cubiertos



#### Descripción original



Registrar en el código o README los escenarios extremos validados (valores nulos, negativos, cero).



#### Descripción mejorada

Crear `tests/unit/domain/services/README.md` con una matriz concisa de funciones, casos nominales, límites, errores esperados y archivo de prueba. Aclarar que `None` se rechaza mediante el contrato de tipos y que la validación HTTP futura corresponderá a Pydantic; el dominio valida números negativos, cero según el campo y valores no finitos.

#### Criterios de aceptación

- [ ] El README enumera casos nominales, cero, negativos, no finitos y límites temporales.
- [ ] Cada escenario identifica el resultado o excepción esperada.
- [ ] Se documenta el tratamiento de `None` sin ampliar innecesariamente las firmas de dominio.
- [ ] Se incluyen comandos de pruebas dirigidas y cobertura.
- [ ] La documentación enlaza la guía de cálculos estadísticos existente.



#### Puntos de historia



**1** — Documentación breve de una suite ya estructurada.



