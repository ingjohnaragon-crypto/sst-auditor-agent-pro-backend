Enriched content saved to `ai-specs/changes/SP-138_enriched.md`.
3 subtask(s) will also be updated.
Run `os-enrich-apply SP-138` to upload it to Jira.

Puntos clave del enriquecimiento:

- **Partí del código real**: SP-137 ya dejó los manejadores de `DomainException` y `RequestValidationError`, así que el ticket se redefinió como completar y unificar (no crear desde cero): manejadores nuevos para `StarletteHTTPException` y `Exception` (500), registro centralizado vía `registrar_manejadores_excepciones(app)`, y logging configurable.
- **Esquema único de error** formalizado como DTO Pydantic `RespuestaError` con campos `exito`, `codigo`, `mensaje`, `detalle` (en español, según la directiva de idioma), lo que implica migrar el formato actual `success/code/message` — ruptura aceptable en `0.1.0` sin consumidores externos, señalada explícitamente en los requisitos no funcionales.
- **Las 3 subtareas** (SP-167, SP-168, SP-169) eran de una línea, así que las tres recibieron versión enriquecida con archivos concretos, firmas de funciones y criterios de aceptación verificables, incluyendo detalles no obvios como `raise_server_exceptions=False` en `TestClient` para probar el manejador de 500.
