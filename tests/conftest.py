"""Configuración global de pruebas — entorno mínimo antes de importar la aplicación.

`Settings` exige `JWT_SECRETO` y `URL_BASE_DATOS` sin defaults (fail-fast en
producción); aquí se fijan valores de prueba para todo el proceso de pytest.
"""

import os

os.environ.setdefault("JWT_SECRETO", "secreto-exclusivo-de-pruebas-con-mas-de-32-caracteres")
os.environ.setdefault("URL_BASE_DATOS", "sqlite+aiosqlite:///:memory:")
