# Cloudflare R2 — almacenamiento de archivos

Guía corta para quien configura el bucket de desarrollo y el cliente
`AlmacenR2` del backend. Los secretos no van al repositorio ni al frontend.

## Objeto y clave

En R2 un **objeto** es el archivo binario (PDF, JPEG o PNG) más sus metadatos
mínimos en el bucket.

La **clave** es el identificador único del objeto dentro del bucket. No es una
ruta de disco del servidor. El backend la arma y la guarda en PostgreSQL; R2
solo conoce la clave y los bytes.

Convenciones previstas:

| Uso | Clave |
|---|---|
| Evidencias de autoevaluación | `evidencias/{empresa_id}/{uuid}{ext}` |
| Catálogo PHVA (más adelante) | `documentos/{empresa_id}/{tipo_codigo}/{uuid}{ext}` |

Ejemplo: `evidencias/a1b2c3d4-…/9f8e7d6c-….pdf`.

## Dónde se pega el token

1. Copia `.env.example` a `.env` (si aún no existe).
2. Rellena en **tu** `.env` local:
   - `R2_ACCOUNT_ID`
   - `R2_ACCESS_KEY_ID`
   - `R2_SECRET_ACCESS_KEY`
   - `R2_BUCKET` (en desarrollo: `sst-auditor-dev`)
   - `R2_ENDPOINT` (endpoint S3 de la cuenta, p. ej. `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`)
3. Nunca pegues el secret en Git, en el chat, en el frontend ni en tests.

Si falta cualquiera de las cinco, el backend no construye el cliente R2 y
responde `AlmacenamientoNoConfiguradoError` (HTTP 503). No escribe en disco
ni en R2.

## Por qué el archivo no es público

No hay Workers ni dominio propio del bucket. Los objetos no son públicos.
El navegador no recibe credenciales de R2 ni habla con el bucket: el API
autoriza la sesión y entrega o firma el acceso.

## Crear `sst-auditor-dev` y comprobar un PDF a mano

1. Entra al panel de Cloudflare → R2.
2. Crea el bucket `sst-auditor-dev` (no mezclar con producción).
3. Crea un token de API con permiso **solo** sobre ese bucket (lectura y escritura de objetos).
4. Sube un PDF desde el panel y verifica que aparece en el listado del bucket.
5. Anota account id, access key, secret, bucket y endpoint en tu `.env`.

Hay dos buckets distintos (desarrollo y producción). Nunca se mezclan.

## Comprobar un objeto subido por `AlmacenR2`

Con las cinco variables en `.env`, desde un REPL o script local (fuera de CI):

1. Construye el almacén con la fábrica (`crear_almacen_r2`).
2. Llama `guardar` con una clave de prueba, p. ej.
   `evidencias/00000000-0000-0000-0000-000000000001/prueba.pdf`.
3. Abre el panel de `sst-auditor-dev` y confirma que el objeto aparece.
4. Llama `leer` y comprueba los bytes.
5. Llama `eliminar` y confirma que el panel ya no muestra el objeto.

La suite de pytest usa un doble en memoria o mocks de boto3: **no** llama a
Cloudflare.

## Evidencias del diagnóstico (SP-285)

Las evidencias **nuevas** se cargan con `AlmacenR2` y la clave
`evidencias/{empresa_id}/{uuid}{ext}` queda en `ruta_almacenamiento`.
La descarga (JWT corto de SP-152) lee el objeto con `almacen.leer`.
Producción **no** usa `ALMACENAMIENTO_LOCAL_RAIZ` ni `AlmacenLocal`.

Las evidencias **históricas** que solo tengan un path de disco local quedan
**pendientes de migración manual** al bucket. Hasta migrarlas, el canje
responde `ARCHIVO_NO_DISPONIBLE` (404).
