"""Base declarativa de SQLAlchemy 2.x — punto único de registro de metadatos."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarativa de la que heredan todos los modelos ORM."""
