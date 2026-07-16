"""Implementación bcrypt del puerto `ServicioHashContrasena`."""

import asyncio

import bcrypt

from src.domain.repositories.servicio_hash_contrasena import ServicioHashContrasena

COSTO_BCRYPT_POR_DEFECTO = 12


class HashBcrypt(ServicioHashContrasena):
    """Hashing bcrypt con salt por usuario; las llamadas CPU-bound van a un hilo."""

    def __init__(self, costo: int = COSTO_BCRYPT_POR_DEFECTO) -> None:
        self._costo = costo

    async def generar_hash(self, contrasena: str) -> str:
        return await asyncio.to_thread(self._generar_hash_sincrono, contrasena)

    async def verificar(self, contrasena: str, hash_contrasena: str) -> bool:
        return await asyncio.to_thread(
            bcrypt.checkpw, contrasena.encode("utf-8"), hash_contrasena.encode("utf-8")
        )

    def _generar_hash_sincrono(self, contrasena: str) -> str:
        salt = bcrypt.gensalt(rounds=self._costo)
        return bcrypt.hashpw(contrasena.encode("utf-8"), salt).decode("utf-8")
