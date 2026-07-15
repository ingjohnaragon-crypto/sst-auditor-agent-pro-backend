"""Excepción base del dominio, independiente de FastAPI o SQLAlchemy."""


class DomainException(Exception):
    """Excepción base para violaciones de reglas de negocio del dominio.

    Las subclases pueden fijar `code` y `http_status` como atributos de clase,
    o sobreescribirlos por instancia al construir la excepción.
    """

    code: str = "ERROR_DOMINIO"
    http_status: int = 400

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        http_status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if http_status is not None:
            self.http_status = http_status
