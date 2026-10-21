# Integración: Cloudflare R2

OpenSpec carga este archivo junto al stack activo (`python-fastapi` o `frontend-angular`). No lo reemplaza. Un `os-stack` nuevo para R2 dejaría fuera las reglas de FastAPI o Angular.

## Decisión

Los bytes documentales viven en Cloudflare R2. El disco del servidor no guarda archivos. No hay bucket de AWS ni VPC. La historia SP-150 queda cerrada. Los metadatos (nombre, tipo, tamaño, `clave_objeto`, empresa, estado) viven solo en PostgreSQL.

Hay dos buckets distintos: `sst-auditor-dev` para desarrollo y otro de producción. Nunca se mezclan.

## Variables

`R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `R2_ENDPOINT`.

Si falta alguna, el caso de uso responde 503. Los secretos no van al repositorio ni al prompt. El navegador no recibe credenciales de R2 ni habla con el bucket.

## Claves de objeto

- Evidencias de autoevaluación: `evidencias/{empresa_id}/{uuid}{ext}`
- Catálogo PHVA: `documentos/{empresa_id}/{tipo_codigo}/{uuid}{ext}`

Tipos aceptados: PDF, JPEG y PNG. Tope 10 MiB. La validación de tipo y tamaño ocurre antes de subir.

## Contrato de almacenamiento

El puerto `AlmacenEvidencias` gana `leer` además de `guardar` y `eliminar`. La implementación de producción es `AlmacenR2`. Las pruebas usan un doble en memoria y no salen a la red. Una comprobación manual contra el bucket de desarrollo basta; no hay LocalStack.

La descarga exige sesión. El API autoriza y entrega el archivo en streaming o con una URL firmada de vida corta. Los objetos no son públicos. No hay Workers ni dominio propio del bucket.

## Curva de aprendizaje

La primera historia del repositorio (SP-282) incluye leer el panel de Cloudflare y dejar el instructivo en `docs/cloudflare-r2.md` antes de escribir el cliente. El despliegue (SP-308) repite el recorrido para el bucket de producción. El volumen de Docker de producción no monta documentos; el respaldo es solo `pg_dump`.

## Qué no hacer

No reimplementar el almacén local como destino nuevo. Las evidencias ya guardadas en disco se documentan como migración manual. Lo nuevo no escribe en disco.
