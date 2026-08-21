# Integración del frontend con el guardado de progreso de validación (flujo eFirma)

## Contexto

El backend ahora guarda el **progreso de la validación por pasos** (flujo eFirma, identificado por `id_firmador`/`efirmaId`). El objetivo es que una persona que arranca la validación pueda **continuar en el paso exacto donde quedó**, incluso en otro dispositivo.

El backend **no escribe progreso** en las rutas de validación de cada paso (`/ocr/anverso`, `/ocr/reverso`, liveness). El guardado lo dispara **el frontend** únicamente en dos momentos por paso:

1. El paso se **completó** correctamente.
2. Se **agotaron los intentos** y se avanza al siguiente paso.

Mientras la persona está intentando un paso (reintentando), **no se debe guardar nada**.

## Requisitos de autenticación (todos los endpoints)

- Header `Authorization: Bearer <token>` (JWT obtenido con `/auth/generate-token` enviando `x-api-key`).
- Header `X-Country-Code` con el país (`COL` o `HND`) para el routing de la base de datos.

## Endpoints disponibles en el backend

### 1) Obtener progreso (resume)

```
GET /validation/progreso?efirmaId={id}
```

Respuesta:

```json
{
  "progreso": {
    "id": 1,
    "idFirmador": 123,
    "pasoActual": "REVERSO",
    "estado": "EN_PROGRESO",
    "progreso": {
      "ANVERSO": { "resultado": "OK", "validSide": true, "pctName": 95, "pctLastname": 88, "pctID": 90 }
    },
    "creadoEn": "2026-08-13T15:00:00",
    "actualizadoEn": "2026-08-13T15:04:00",
    "completadoEn": null
  },
  "evidencias": {
    "anverso": "data:image/jpeg;base64,...",
    "reverso": "data:image/jpeg;base64,...",
    "selfie": "data:image/jpeg;base64,..."
  }
}
```

- `progreso == null` → no existe sesión previa; arranca desde el inicio.
- `progreso.estado == "EN_PROGRESO"` y `pasoActual != "INICIO"` → hay que ofrecer continuar.
- `progreso.estado == "COMPLETADO"` → la validación ya terminó; no mostrar resume.
- `progreso.estado == "ABANDONADO"` → quedó inactiva por TTL; arranca desde el inicio.
- `evidencias` solo incluye las imágenes que ya se guardaron (por eso la misma-device y cross-device pueden restaurarse).

### 2) Guardar paso (disparado solo al completar o agotar intentos)

```
POST /validation/progreso
Content-Type: application/json
```

Body:

```json
{
  "efirmaId": 123,
  "paso": "ANVERSO",
  "resultado": "OK",
  "metadata": { "validSide": true, "tries": 3, "pctName": 95, "pctLastname": 88, "pctID": 90 },
  "evidencias": { "anverso": "data:image/jpeg;base64,..." }
}
```

- `paso`: uno de `ANVERSO | REVERSO | SELFIE | FINALIZADO` (también se admite `INICIO` si se quiere registrar el arranque).
- `resultado`: `"OK"` si el paso se completó, `"!OK"` si se agotaron los intentos y se avanza igual.
- `metadata`: objeto libre con el detalle del resultado del paso.
- `evidencias`: objeto con las imágenes a persistir (`anverso`, `reverso`, `selfie`). Solo enviar la del paso que termina (ver reglas por paso).

Respuesta:

```json
{ "idSesion": 1, "paso": "ANVERSO", "resultado": "OK" }
```

El backend comprime las imágenes (máx. 800px, JPEG q75) y las guarda en `./evidencias-progreso/{id_firmador}/`.

### 3) Reporte de sesiones inactivas (detección de abandono)

```
GET /validation/abandonadas?minutos=30
```

Devuelve las sesiones `EN_PROGRESO` sin actualizar en los últimos `minutos`.

### 4) Mantenimiento / limpieza TTL (lo corre un script o cron)

```
POST /validation/limpiar-progreso?ttl_horas=24
```

Marca como `ABANDONADO` las sesiones inactivas y borra las viejas. No lo usa el frontend en el flujo normal.

## Reglas de guardado por paso

### ANVERSO (`/ocr/anverso`)
- Guardar **solo cuando**:
  - la respuesta tiene `validSide: true` (paso completado), o
  - se agotaron los intentos permitidos y se avanza al reverso.
- Body: `paso: "ANVERSO"`, `resultado: "OK"|"!OK"`, `metadata` (validSide, tries, porcentajes, etc.), `evidencias.anverso` con la imagen del documento (usar la que devuelve el backend en `image`, o la captura original).
- Mientras se reintenta, **no guardar**.

### REVERSO (`/ocr/reverso`)
- Ídem ANVERSO con `paso: "REVERSO"` y `evidencias.reverso`.

### SELFIE / prueba de vida
- Guardar **solo cuando** la prueba de vida termina (éxito o agotamiento).
- Body: `paso: "SELFIE"`, `resultado: "OK"|"!OK"`, `metadata` (movimiento, antiSpoof, etc.).
- **No es necesario** enviar `evidencias.selfie`: el backend ya guarda el video/foto de liveness en `evidencias-vida` como hoy. (Opcional enviar la foto si se quiere tener el thumb también.)

### FINALIZADO
- Al enviar la validación completa (`/validation/type-3`), el backend marca la sesión como `COMPLETADO` y borra la carpeta temporal. El frontend **no** debe llamar a `POST /validation/progreso` para esto.
- Tras un envío exitoso, limpiar cualquier estado local del flujo.

## Flujo de resume (a implementar en el frontend)

1. Al cargar el flujo eFirma con `efirmaId`, llamar `GET /validation/progreso?efirmaId=` antes de mostrar el primer paso.
2. Lógica según la respuesta:
   - `progreso == null` → flujo normal desde el inicio.
   - `estado == "COMPLETADO"` → no ofrecer resume.
   - `pasoActual == "ANVERSO"` → mostrar pantalla de "continuar validación" con el anverso restaurado; al continuar, ir a **REVERSO** (el anverso ya está validado).
   - `pasoActual == "REVERSO"` → continuar en **SELFIE** (restaurar anverso y reverso).
   - `pasoActual == "SELFIE"` → continuar en el **envío final** (restaurar anverso, reverso y selfie).
3. Restaurar las imágenes desde `evidencias` (dataURLs) para no re-capturar.
4. Reutilizar los resultados ya guardados en `progreso.progreso[PASO]` para no re-validar el paso hecho.

## Consideraciones

- Las imágenes guardadas ya vienen comprimidas por el backend; las del POST pueden enviarse en la resolución que devuelven los endpoints de validación (el backend re-comprime).
- Cuidar el tamaño del body: `MAX_CONTENT_LENGTH` del backend es 10 MB.
- No escribir progreso en cada intento fallido; solo en transición de paso (completado o agotado).
- El `efirmaId` es el mismo id que se usa en `/validation/type-3` y en `/validation/validation-params`.
