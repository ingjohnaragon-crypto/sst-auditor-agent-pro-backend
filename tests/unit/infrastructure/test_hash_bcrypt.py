"""Pruebas de la implementación bcrypt del puerto de hashing."""

from src.infrastructure.security.hash_bcrypt import COSTO_BCRYPT_POR_DEFECTO, HashBcrypt

# Costo mínimo de bcrypt: acelera las pruebas sin cambiar el comportamiento.
COSTO_PRUEBAS = 4
CONTRASENA = "ContrasenaSegura123"


async def test_should_generar_hash_distinto_a_la_contrasena_en_claro() -> None:
    servicio = HashBcrypt(costo=COSTO_PRUEBAS)

    hash_generado = await servicio.generar_hash(CONTRASENA)

    assert hash_generado != CONTRASENA
    assert CONTRASENA not in hash_generado


async def test_should_verificar_verdadero_when_contrasena_correcta() -> None:
    servicio = HashBcrypt(costo=COSTO_PRUEBAS)
    hash_generado = await servicio.generar_hash(CONTRASENA)

    assert await servicio.verificar(CONTRASENA, hash_generado) is True


async def test_should_verificar_falso_when_contrasena_incorrecta() -> None:
    servicio = HashBcrypt(costo=COSTO_PRUEBAS)
    hash_generado = await servicio.generar_hash(CONTRASENA)

    assert await servicio.verificar("OtraContrasena456", hash_generado) is False


async def test_should_generar_hashes_distintos_para_la_misma_contrasena() -> None:
    # Cada hash lleva su propio salt: dos hashes de la misma contraseña difieren.
    servicio = HashBcrypt(costo=COSTO_PRUEBAS)

    primero = await servicio.generar_hash(CONTRASENA)
    segundo = await servicio.generar_hash(CONTRASENA)

    assert primero != segundo


async def test_should_usar_costo_12_por_defecto() -> None:
    assert COSTO_BCRYPT_POR_DEFECTO == 12
    servicio = HashBcrypt()

    hash_generado = await servicio.generar_hash(CONTRASENA)

    assert hash_generado.startswith("$2b$12$")
