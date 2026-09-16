# Plan de implementación backend: SP-146 — Utilidades de cálculos estadísticos SST

## 1. Resumen
Implementar utilidades puras de dominio para calcular tasas de frecuencia y severidad de accidentalidad, proyectar indicadores al cierre anual y comparar los valores proyectados contra metas SST.

La solución se desarrollará con Python 3.12 y `Decimal`, sin persistencia, endpoints ni dependencias de FastAPI/SQLAlchemy. Se centralizarán redondeo, división segura y validaciones para evitar fórmulas duplicadas entre las subtareas.

## Estimación de puntos de historia
<!-- STORY_POINTS:8 -->
- **HU total**: 8
- **Justificación**: incluye definición de contratos matemáticos, manejo preciso de decimales, reglas para metas de minimización/maximización, casos límite de división por cero, documentación y pruebas exhaustivas.
- **Subtareas**:

| Subtarea | Puntos | Nota |
|---|---:|---|
| SP-193 | 3 | Fórmulas de frecuencia y severidad, validaciones y redondeo. |
| SP-194 | 3 | Proyección anual, comparación de metas y desviaciones. |
| SP-195 | 2 | Primitivas matemáticas compartidas y pruebas directas. |

<!-- /STORY_POINTS -->

## 2. Contexto de arquitectura
- **Stack activo**: `python-fastapi` — Python 3.12 + FastAPI.
- **Dominio**:
  - nuevas utilidades matemáticas puras;
  - fórmulas estadísticas SST;
  - enum y objeto de valor para el resultado de metas;
  - excepción de validación estadística.
- **Aplicación**: sin cambios; no se solicita un caso de uso ni orquestación.
- **Presentación**: sin cambios; no se crean endpoints.
- **Infraestructura**: sin cambios; no existe persistencia ni migración.
- **Pruebas**: unitarias y síncronas bajo `tests/unit/domain/services/`.
- **Documentación**: fórmulas, factor, precisión y semántica de metas en la guía de desarrollo.

### Mapeo de subtareas
| Clave | Resumen | Pasos de implementación |
|---|---|---|
| SP-193 | Implementar funciones de cálculo de tasa de accidentalidad | Pasos 3 y 5 |
| SP-194 | Implementar utilidades de cálculo de metas anuales | Pasos 4 y 5 |
| SP-195 | Crear módulo común de utilidades matemáticas | Pasos 1, 2 y 5 |

## 3. Pasos de implementación

### Paso 0: Crear la rama de funcionalidad
- **Rama base**: `develop`.
- **Rama nueva**: `feature/SP-146-backend`.
- **Comandos**:

```bash
git checkout develop
git pull --ff-only origin develop
git checkout -b feature/SP-146-backend
```

- Confirmar antes de crearla que los archivos locales no relacionados permanezcan fuera del commit.

### Paso 1: Definir la excepción de dominio
- **Crear** `src/domain/exceptions/estadisticas_sst.py`.
- Implementar `ValorEstadisticoInvalidoError(DomainException)`:
  - `code = "VALOR_ESTADISTICO_INVALIDO"`;
  - `http_status = 422`;
  - constructor con mensaje concreto en español.
- No importar FastAPI; `http_status` conserva el patrón de excepciones existente.
- Evaluar la exportación desde `src/domain/exceptions/__init__.py`; mantener el archivo sin cambios si el proyecto continúa usando importaciones explícitas por módulo.

### Paso 2: Crear las utilidades matemáticas compartidas
- **Crear** `src/domain/services/__init__.py`.
- **Crear** `src/domain/services/utilidades_matematicas.py`.
- Definir una única constante de precisión:

```python
PRECISION_DOS_DECIMALES = Decimal("0.01")
```

- Implementar funciones tipadas:
  - `redondear_dos_decimales(valor: Decimal) -> Decimal`;
  - `validar_no_negativo(valor: Decimal | int, nombre_campo: str) -> None`;
  - `validar_positivo(valor: Decimal | int, nombre_campo: str) -> None`;
  - `dividir_seguro(numerador: Decimal, denominador: Decimal, nombre_denominador: str) -> Decimal`.
- Aplicar `ROUND_HALF_UP` explícitamente.
- `dividir_seguro` debe validar el denominador antes de dividir y devolver un `Decimal` sin convertir a `float`.
- Las validaciones deben mencionar el campo inválido y lanzar `ValorEstadisticoInvalidoError`.
- No mantener estado mutable ni realizar I/O.

### Paso 3: Implementar las tasas de accidentalidad
- **Crear** `src/domain/services/calculos_estadisticos_sst.py`.
- Definir:

```python
FACTOR_NORMALIZACION_SST = Decimal("240000")
```

- Implementar:

```python
def calcular_tasa_frecuencia(
    numero_accidentes: int,
    horas_trabajadas: Decimal,
    factor: Decimal = FACTOR_NORMALIZACION_SST,
) -> Decimal: ...
```

- Fórmula: `(Decimal(numero_accidentes) * factor) / horas_trabajadas`.
- Validar accidentes no negativos, horas positivas y factor positivo.
- Cero accidentes debe devolver `Decimal("0.00")`.
- Implementar:

```python
def calcular_tasa_severidad(
    dias_incapacidad: int,
    dias_cargados: int,
    horas_trabajadas: Decimal,
    factor: Decimal = FACTOR_NORMALIZACION_SST,
) -> Decimal: ...
```

- Fórmula: `(Decimal(dias_incapacidad + dias_cargados) * factor) / horas_trabajadas`.
- Validar cada numerador por separado, además de horas y factor.
- Cero días debe devolver `Decimal("0.00")`.
- Redondear únicamente el resultado final a dos decimales.
- Agregar docstrings con fórmula, unidades esperadas, factor y excepciones.

### Paso 4: Implementar proyección y comparación de metas
- En `src/domain/services/calculos_estadisticos_sst.py`, definir:

```python
class SentidoMeta(StrEnum):
    MINIMIZAR = "MINIMIZAR"
    MAXIMIZAR = "MAXIMIZAR"
```

- Definir `ResultadoMetaAnual` como `@dataclass(frozen=True, slots=True)` con:
  - `valor_proyectado: Decimal`;
  - `meta: Decimal`;
  - `sentido: SentidoMeta`;
  - `cumplida: bool`;
  - `desviacion_absoluta: Decimal`;
  - `desviacion_porcentual: Decimal | None`.
- Implementar:

```python
def proyectar_valor_anual(
    valor_acumulado: Decimal,
    periodos_transcurridos: int,
    periodos_totales: int = 12,
) -> Decimal: ...
```

- Fórmula: `valor_acumulado / periodos_transcurridos * periodos_totales`.
- Validar:
  - valor acumulado no negativo;
  - `periodos_totales > 0`;
  - `periodos_transcurridos > 0`;
  - `periodos_transcurridos <= periodos_totales`.
- Redondear solamente el resultado final.
- Implementar:

```python
def comparar_meta_anual(
    valor_proyectado: Decimal,
    meta: Decimal,
    sentido: SentidoMeta,
) -> ResultadoMetaAnual: ...
```

- Validar valor proyectado y meta no negativos.
- `MINIMIZAR`: cumplir cuando `valor_proyectado <= meta`.
- `MAXIMIZAR`: cumplir cuando `valor_proyectado >= meta`.
- Desviación absoluta: `valor_proyectado - meta`.
- Desviación porcentual para meta positiva: `(desviacion_absoluta / meta) * Decimal("100")`.
- Para `meta == 0`, establecer `desviacion_porcentual = None`.
- Redondear valores derivados a dos decimales.

### Paso 5: Crear las pruebas unitarias
- **Crear** `tests/unit/domain/services/__init__.py`.
- **Crear** `tests/unit/domain/services/test_utilidades_matematicas.py`.
- Cubrir:
  - redondeo hacia arriba en empate con `ROUND_HALF_UP`;
  - conservación de dos decimales;
  - validaciones de cero, positivos y negativos;
  - división nominal;
  - denominador cero y negativo.
- **Crear** `tests/unit/domain/services/test_calculos_estadisticos_sst.py`.
- Usar pruebas parametrizadas y patrón AAA.
- Casos para frecuencia:
  - cero accidentes;
  - cálculo nominal conocido;
  - factor alternativo;
  - resultado con más de dos decimales;
  - accidentes negativos;
  - horas cero/negativas;
  - factor cero/negativo.
- Casos para severidad:
  - cero días;
  - incapacidad sin días cargados;
  - días cargados sin incapacidad;
  - suma de ambos;
  - cada numerador negativo;
  - horas y factor inválidos.
- Casos para proyección:
  - primer período;
  - período intermedio;
  - último período;
  - acumulado cero;
  - transcurridos cero/negativos;
  - transcurridos mayores al total;
  - total cero/negativo.
- Casos para metas:
  - `MINIMIZAR` por debajo, igual y por encima;
  - `MAXIMIZAR` por debajo, igual y por encima;
  - signo de desviación absoluta;
  - porcentaje con meta positiva;
  - meta cero sin división;
  - valores negativos;
  - inmutabilidad de `ResultadoMetaAnual`.
- Verificar tipos y valores exactos de `Decimal`, no aproximaciones de punto flotante.

### Paso 6: Actualizar la documentación técnica
- **Modificar** `ai-specs/specs/development_guide.md`.
- Añadir una sección “Cálculos estadísticos SST” con:
  - las dos fórmulas de accidentalidad;
  - factor predeterminado `240000` y posibilidad de configurarlo por llamada;
  - política de `Decimal` y `ROUND_HALF_UP`;
  - reglas de proyección anual;
  - semántica de `MINIMIZAR` y `MAXIMIZAR`;
  - comportamiento cuando la meta es cero;
  - ejemplo breve de uso.
- No modificar `ai-specs/specs/data-model.md`, OpenAPI ni Alembic porque no cambia el esquema ni se exponen endpoints.

### Paso 7: Ejecutar verificación integral
- Ejecutar primero las pruebas nuevas:

```bash
pytest tests/unit/domain/services -q
```

- Ejecutar calidad y tipado:

```bash
ruff check src tests
mypy src
```

- Ejecutar la suite completa y cobertura:

```bash
pytest
```

- Confirmar cobertura global mínima del 90 % y revisar que cada rama de validación nueva esté cubierta.

## 4. Orden de implementación
1. Paso 0: crear rama desde `develop`.
2. Paso 1: crear la excepción de dominio.
3. Paso 2: implementar utilidades matemáticas comunes.
4. Paso 3: implementar tasas de frecuencia y severidad.
5. Paso 4: implementar proyección y comparación de metas.
6. Paso 5: crear pruebas unitarias.
7. Paso 6: documentar fórmulas y decisiones.
8. Paso 7: ejecutar verificación integral.

## 5. Lista de verificación de pruebas
- [ ] `pytest tests/unit/domain/services -q` pasa sin fallos.
- [ ] `ruff check src tests` pasa sin errores.
- [ ] `mypy src` pasa en modo estricto.
- [ ] `pytest` pasa con cobertura global igual o superior al 90 %.
- [ ] Se verifican valores exactos `Decimal`.
- [ ] Se cubren todos los límites y errores de división.
- [ ] Se cubren ambos sentidos de meta y la igualdad.
- [ ] Meta cero no produce división por cero.
- [ ] No se rompen las pruebas existentes.
- [ ] No aplica prueba manual de endpoints porque el ticket no expone API HTTP.

## 6. Referencia de herramientas
| Propósito | Comando |
|---|---|
| Instalación/build | `pip install -r requirements.txt` |
| Pruebas | `pytest` |
| Ejecución | `uvicorn main:app --reload` |
| Cobertura | `pytest --cov --cov-report=html` |
| Lint | `ruff check src tests` |
| Tipado | `mypy src` |

## 7. Formato de respuesta de error
No se crea respuesta HTTP en este ticket. Las entradas inválidas lanzan:

```python
ValorEstadisticoInvalidoError(
    "El campo horas_trabajadas debe ser mayor que cero"
)
```

Si una capa HTTP reutiliza estas utilidades en un ticket posterior, el manejador global de `DomainException` deberá conservar el formato vigente y mapear el error a HTTP `422` con código `VALOR_ESTADISTICO_INVALIDO`.

## 8. Dependencias
- No se agregan librerías.
- Se utiliza exclusivamente `decimal`, `dataclasses` y `enum` de la biblioteca estándar.
- Se mantienen las versiones actuales de Python, pytest, Ruff y mypy.

## 9. Notas
- El factor `240000` corresponde al valor predeterminado acordado en el enriquecimiento y debe permanecer como constante visible y documentada.
- No aceptar `float` en las firmas públicas; los consumidores deben construir `Decimal` desde texto o enteros.
- No redondear resultados intermedios para evitar acumulación de error.
- Una desviación positiva siempre significa que el valor proyectado está por encima de la meta; el booleano `cumplida` interpreta esa desviación según el sentido.
- La meta cero es válida, especialmente para indicadores que deben minimizarse; por eso su porcentaje de desviación es `None`.
- Mantener las utilidades independientes de entidades, repositorios y sesiones.
- No incluir los archivos locales preexistentes `.openspec-cli/.tmp_*` ni `sst-auditor-agent-pro-backend.code-workspace` en la rama.

## 10. Lista de verificación de implementación
- [ ] Rama `feature/SP-146-backend` creada desde `develop` actualizado.
- [ ] Excepción de dominio implementada sin dependencias de framework.
- [ ] Utilidades compartidas usan `Decimal` y `ROUND_HALF_UP`.
- [ ] Frecuencia y severidad respetan las fórmulas acordadas.
- [ ] Proyección anual valida correctamente los períodos.
- [ ] Comparación de metas soporta `MINIMIZAR`, `MAXIMIZAR` y meta cero.
- [ ] Objetos de resultado inmutables y completamente tipados.
- [ ] No se crean endpoints, DTO Pydantic, repositorios, modelos ORM ni migraciones.
- [ ] Pruebas nuevas y suite completa en verde.
- [ ] Cobertura global igual o superior al 90 %.
- [ ] Ruff y mypy sin errores.
- [ ] Guía de desarrollo actualizada.
- [ ] Commit limitado a SP-146 y sus subtareas.
