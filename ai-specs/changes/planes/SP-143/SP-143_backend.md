# Plan de implementación backend: SP-143 Seeds de cargue Res 0312 y GTC 45

## Estado (os-develop)

Implementado en `feature/SP-143-backend`:

- ORM: `EstandarMinimoORM`, `CatalogoReferenciaORM`
- Migración Alembic `b2c3d4e5f6a7` (`down_revision=a1b2c3d4e5f6`)
- Fixtures: `scripts/datos/estandares_minimos_res312.json` (60 ítems, suma 100) y `catalogos_gtc45.json` (incl. ND Bajo = 0)
- Seeds idempotentes + orquestador `scripts.sembrar_datos`
- Tests unitarios; `pytest` 133 passed, cobertura ~99%
- README + `data-model.md` actualizados

## Uso local

```bash
poetry run alembic upgrade head
poetry run python -m scripts.sembrar_datos
```

## Notas

- Fuente Res. 312: tabla Art. 27 / Anexo Técnico (60 ítems).
- GTC 45: Anexos A/B + decisión D1 (ND Bajo = 0).
- Sin endpoints HTTP; Domain/Application/Presentation sin cambios.
