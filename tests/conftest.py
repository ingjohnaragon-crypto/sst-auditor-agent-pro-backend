"""Configuración global de pruebas — entorno mínimo antes de importar la aplicación.

`Settings` exige `JWT_SECRETO` y `URL_BASE_DATOS` sin defaults (fail-fast en
producción); aquí se fijan valores de prueba para todo el proceso de pytest.

Las variables R2 se anulan (cadena vacía) para que un `.env` local con
credenciales Cloudflare **no** active `AlmacenR2` real: la suite es offline
(SP-287). En pydantic-settings el entorno gana sobre `env_file`.
"""

import os

_VARIABLES_R2 = (
    "R2_ACCOUNT_ID",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_BUCKET",
    "R2_ENDPOINT",
)

for _clave_r2 in _VARIABLES_R2:
    os.environ[_clave_r2] = ""

os.environ.setdefault("JWT_SECRETO", "secreto-exclusivo-de-pruebas-con-mas-de-32-caracteres")
os.environ.setdefault("URL_BASE_DATOS", "sqlite+aiosqlite:///:memory:")
