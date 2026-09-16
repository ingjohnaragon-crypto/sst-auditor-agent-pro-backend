# Pruebas de cálculos estadísticos SST

Esta suite valida las fórmulas documentadas en
`ai-specs/specs/development_guide.md`, sin FastAPI, base de datos ni servicios
externos.

## Matriz de casos

| Función | Casos nominales y límites | Errores esperados |
|---|---|---|
| `calcular_tasa_frecuencia` | factor `240000`, factor alternativo, cero accidentes y redondeo final | accidentes negativos; horas o factor no positivos/no finitos |
| `calcular_tasa_severidad` | incapacidad, días cargados, suma de ambos y cero días | días negativos; horas o factor no positivos/no finitos |
| `proyectar_valor_anual` | primer período, período intermedio, cierre, acumulado cero y total personalizado | acumulado negativo/no finito; períodos no positivos o fuera del total |
| `comparar_meta_anual` | minimizar, maximizar, igualdad, meta cero, desviaciones y precisión menor a `0.01` | valor/meta negativos o no finitos; sentido inválido |
| `redondear_dos_decimales` | positivos, negativos, cero y empate `ROUND_HALF_UP` | `NaN` e infinitos |
| `validar_no_negativo` | cero y positivos | negativos y no finitos |
| `validar_positivo` | positivos | cero, negativos y no finitos |
| `dividir_seguro` | numerador positivo, cero y negativo | denominador no positivo/no finito y numerador no finito |
| `ValorEstadisticoInvalidoError` | código, estado HTTP y mensaje | No aplica |

`None` no forma parte de las firmas públicas `Decimal | int`; mypy rechaza ese
uso. Si estas funciones se exponen mediante HTTP en otro ticket, Pydantic debe
rechazar los valores nulos antes de llegar al dominio.

## Ejecución

Pruebas dirigidas sin la cobertura global configurada:

```bash
pytest -o addopts="" \
  tests/unit/domain/services \
  tests/unit/domain/exceptions/test_estadisticas_sst.py
```

Cobertura exclusiva de los servicios estadísticos:

```bash
pytest -o addopts="" tests/unit/domain/services \
  --cov=src.domain.services.calculos_estadisticos_sst \
  --cov=src.domain.services.utilidades_matematicas \
  --cov-report=term-missing \
  --cov-fail-under=100
```

Suite y cobertura global según `pyproject.toml`:

```bash
pytest
```
