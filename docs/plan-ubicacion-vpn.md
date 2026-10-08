# Plan técnico — Validación de ubicación obligatoria + anti‑VPN en `validacion-back`

> Servicio backend: repo `validacion-identidad-api` (Flask) expuesto como `/validacion-back/*`.
> Cliente: SPA `pki-validacion-identidad` (React + Vite). Contrato de referencia:
> `pki-validacion-identidad/docs/prompt-backend-ubicacion-vpn.md`.
> Estado: **plan pendiente de aprobación. No implementado.**

---

## 1. Alcance

1. Endpoint `GET /validation/document-config` con flags de configuración del documento.
2. Aceptar `location: {latitude, longitude, accuracy}` en los POST de firma
   (`/validation/standalone` y `/validation/type-3`).
3. Pipeline de validación geográfica + detección VPN/proxy.
4. Contrato de errores `{ error: { code, message } }` en todos los 4xx/5xx nuevos.

---

## 2. Hallazgos de la exploración

| # | Hallazgo | Evidencia |
|---|---|---|
| H1 | La ruta `validation/document-config` del frontend **ya es la definitiva**: Flask monta el blueprint con prefijo `/validation` y el proxy recorta `/validacion-back`. No hay que tocar `urls.ts`. | `blueprints/validation_bp.py:30`, `src/nucleo/api-urls/urls.ts:36,58` |
| H2 | `/validation/type-3` **ya lee JSON** → solo falta leer `location`. | `validation_bp.py:528` |
| H3 | **Bug preexistente:** `/validation/standalone` lee `request.form.*`, pero la SPA envía **JSON** desde el commit `f05fd0c`. Todos los `form.get` devuelven `None` → `int(None)` → 500. | `validacion-identidad.tsx:529-531` |
| H4 | Peor: leer el JSON "pelado" rompería la semántica. `standalone` compara contra `'OK'`, pero la SPA manda **booleanos** (`face`, `countryCheck`, `typeCheck`, `isExpired`). | `informacion-identidad.interface.ts:49,93,96` |
| H5 | No existe dónde guardar los flags: `pki_validacion.sql` solo define `documento_usuario`, `evidencias_*`, `comprobacion_proceso`. | dump completo |
| H6 | El `country` ya llega a todos los endpoints (interceptor axios → `get_country_code()` → elige BD). | `api.ts:32-34`, `controlador_db.py:190-200` |
| H7 | `efirmaId` = `idUsuario` = `pki_firma_electronica.firmador_pki.id`. | `get-user`, `validation-params`, `get-livenesstest` |
| H8 | Gunicorn `workers=3`, `worker_class=eventlet`, `timeout=30` → cache de IP por worker y timeouts HTTP cortos. | `gunicorn_config.py` |
| H9 | `shapely` y `requests` ya están en `requirements.txt`; `tests/` está en `.gitignore` (no viaja al repo). | — |

---

## 3. Decisiones cerradas

| Tema | Decisión |
|---|---|
| Origen de la config | **Columnas en `usuarios.entidades`**, una fila por entidad (sin tabla nueva) |
| Detección VPN/proxy | API externa con key — **`ipapi.is`** (1.000 req/día gratis, comercial permitido, `is_vpn/is_proxy/is_tor/is_datacenter` + geolip). Adaptador swapeable por env. |
| Región esperada | Centro `(region_lat, region_lng)` + `location_radius_meters` por documento |
| IP autoritativa | `X-Forwarded-For` (1er hop) → `remote_addr` → `info.ip` si el resultado es privado/loopback (con log) |
| Fallo del proveedor | **Fail‑open** con log y auditoría (no bloquea la firma) |
| Standalone | Lector JSON con fallback a form‑data **+ tabla de normalización de tipos** (H4) |

---

## 4. Esquema BD y migración

**No hay tabla nueva.** La config son cinco columnas de `usuarios.entidades`, que
ya es la tabla de parámetros de validación por entidad (`validacion_vida`,
`porcentaje_acierto`, `intentos_documentos`, `intentos_deteccion`,
`intentos_rostro`). El documento se resuelve a su entidad con los mismos joins
que ya usa `/validation-params`.

`ALTER` a ejecutar **por pais** (COL y HND), con el DBA del schema `usuarios`
— el microservicio no aplica migraciones:

```sql
ALTER TABLE `usuarios`.`entidades`
  ADD COLUMN `validar_ubicacion`  TINYINT(1)    NOT NULL DEFAULT 0 COMMENT 'Exige location en la firma',
  ADD COLUMN `bloquear_vpn`      TINYINT(1)    NOT NULL DEFAULT 0 COMMENT 'Bloquea VPN/proxy/Tor/datacenter',
  ADD COLUMN `radio_ubicacion_m` INT           NULL COMMENT 'Radio en metros; NULL = LOCATION_DEFAULT_RADIUS_METERS',
  ADD COLUMN `ubicacion_lat`     DECIMAL(10,7) NULL COMMENT 'Centro permitido, WGS84',
  ADD COLUMN `ubicacion_lng`     DECIMAL(10,7) NULL COMMENT 'Centro permitido, WGS84';
```

- Nombres en español para seguir la convención de la tabla; el JSON de la API
  sigue en inglés (`require_location_validation`, `block_on_vpn`).
- `TINYINT(1) NOT NULL DEFAULT 0` es la convención real de esa tabla:
  `validacion_vida` se lee y se compara con `== 1`.
- **Granularidad por entidad**, no por documento: no se puede exigir ubicación
  para una firma puntual de una entidad que la tiene desactivada.
- **Sin columna `country`**: la BD ya se elige por query param (patrón del resto del código).
- **Columnas sin aplicar / entidad sin fila → defaults fail‑open**
  (`false/false`), idénticos a `DEFAULT_DOCUMENT_CONFIG` del frontend, con
  aviso en el log. Ojo: `selectData` no propaga `pymysql.Error`, así que un
  `Unknown column` llega como fila vacía, no como excepción.
- El dump `pki_validacion.sql` **no se toca**: no incluye el schema `usuarios`.

---

## 5. Módulos nuevos (`utilities/`)

| Archivo | Responsabilidad |
|---|---|
| `api_errors.py` | `error_response(code, message, status)` → `jsonify({"error": {"code","message"}}), status`. Única fuente de verdad del shape. |
| `request_fields.py` | `request_fields()` → dict del JSON si `Content-Type: application/json`, si no `request.form`. Normalizadores: `is_ok(v)`, `is_truthy(v)`, `is_expired_ok(v)`, `norm_str(v)`. |
| `document_config.py` | `load_document_config(hash_, efirma_id)` → dataclass `DocumentConfig`; query parametrizada; defaults si no hay fila. |
| `location_guard.py` | `haversine_m()`, `validate_location(location, config)` → `None` o `(code, message, status)`. Rangos WGS84, `accuracy > radio`, `distancia(centro, punto) > radio`. |
| `ip_intel.py` | `client_ip()` (XFF → remote_addr → `info.ip`), `check_ip(ip)` → `IpVerdict`. Cache en memoria TTL, timeout corto, `IpVerdict.unknown()` ante cualquier fallo (**fail‑open** + log). |
| `signature_security.py` | Orquestador `evaluate_signature_security(...) -> (config, None) \| (config, error_response)`. Punto único de entrada para los 2 POST de firma. |

### Variables de entorno nuevas

```bash
IP_INTEL_PROVIDER=ipapi.is
IP_INTEL_API_KEY=...
IP_INTEL_TIMEOUT=3
IP_INTEL_CACHE_TTL=300
IP_INTEL_BLOCK_FLAGS=is_vpn,is_proxy,is_tor,is_datacenter
LOCATION_DEFAULT_RADIUS_METERS=500
TRUST_XFF=true
```

---

## 6. Contrato API

### 6.1 `GET /validation/document-config?hash=…|efirmaId=…&country=…`

- Auth: `Authorization: Bearer <JWT>` (`@token_required`).
- `hash` tiene prioridad; cadenas vacías = ausentes.
- `200`:

```json
{
  "require_location_validation": true,
  "block_on_vpn": true,
  "location_radius_meters": 500
}
```

- `location_radius_meters` solo se incluye si está configurado (el frontend solo lo conserva si es `number`).
- `400` si no llega ninguno de los dos identificadores:
  `{"error":{"code":"INVALID_PARAMS","message":"Se requiere hash o efirmaId."}}`
- Sin fila de config → `200` con `false/false` (fail‑open; el backend sigue siendo autoridad en la firma).

### 6.2 Errores de los endpoints de firma

Shape obligatorio en **todos** los 4xx/5xx nuevos:

```json
{ "error": { "code": "VPN_DETECTED", "message": "Se detectó uso de VPN. Desactívala para continuar." } }
```

| `code` | HTTP | `message` |
|---|---|---|
| `LOCATION_REQUIRED` | 400 | `Tu ubicación es requerida para completar la firma. Activa la ubicación e inténtalo de nuevo.` |
| `LOCATION_MISMATCH` | 403 | `Tu ubicación no coincide con la región permitida para esta firma.` |
| `LOCATION_UNAVAILABLE` | 403 | `No pudimos verificar tu ubicación. Inténtalo de nuevo.` |
| `VPN_DETECTED` | 403 | `Se detectó uso de VPN. Desactívala para continuar.` |
| `PROXY_DETECTED` | 403 | `Se detectó uso de proxy. Desactívalo para continuar.` |

Los mensajes prevalecen sobre los textos por defecto del modal (`alerta-bloqueo.tsx:88`),
por eso se escriben con el mismo tono.

---

## 7. Pipeline de validación (orden exacto)

Se ejecuta **después** de `@token_required` y **antes** de cualquier procesamiento pesado,
en `/validation/type-3` y `/validation/standalone`:

```
1. Cargar la config de la entidad del documento (hash o efirmaId + country)

2. if require_location_validation:
   2a. ¿existe y es dict `location`?                    no → 400 LOCATION_REQUIRED
   2b. lat/lng numéricos en rango WGS84, accuracy >= 0  no → 400 LOCATION_REQUIRED
   2c. accuracy > location_radius_meters                → 403 LOCATION_MISMATCH
   2d. ¿hay centro configurado? y haversine(punto, centro) > radio
                                                        → 403 LOCATION_MISMATCH
       (sin centro: solo se valida accuracy y se loguea)

3. if block_on_vpn:
   3a. client_ip(); no resoluble/bogon sin fallback     → 403 LOCATION_UNAVAILABLE
   3b. check_ip() (con cache TTL)
       - fallo/timeout del proveedor → fail-open + log  (NO bloquea)
       - is_proxy activo                            → 403 PROXY_DETECTED
       - flag activo de IP_INTEL_BLOCK_FLAGS         → 403 VPN_DETECTED

4. Registrar veredicto en logs y en g.location_security
5. Devolver config al caller → continuar la validación normal
```

Notas:
- `location` se **ignora** cuando `require_location_validation=false`.
- La VPN **no se evalúa** cuando `block_on_vpn=false` (evita llamadas HTTP inútiles).
- La geolip de la IP **no** se compara con el GPS (decisión: centro + radio); se loguea solo como evidencia.

### Auditoría

- `g.location_security = {"location", "distance_m", "ip", "ip_flags", "provider", "checked_at"}`
  se mezcla como clave `location_security` dentro de `checks_json` de `evidencias_adicionales`
  (columna ya existente y ya escrita por ambos endpoints).
- Línea de log en `Logs/ekyc/logs_python.txt`.

---

## 8. Cambios en endpoints existentes

### 8.1 `/validation/type-3` (mínimo)

- Tras `reqBody = request.get_json()` (línea 528): llamar
  `evaluate_signature_security(efirma_id=idUsuario, location=reqBody.get('location'), info_ip=reqBody['info']['ip'])`;
  si devuelve error → `return error`.
- Al generar `checkValuesJSON` (línea 924): añadir `location_security`.

### 8.2 `/validation/standalone` (cambio delicado)

1. Sustituir los ~45 `request.form.get(...)` por `fields.get(...)` con `fields = request_fields()`.
2. Llamar el guard con `hash_=userHash`.
3. **Tabla de normalización obligatoria** (riesgo H4):

| Campo | Form legacy | JSON SPA | Normalizador |
|---|---|---|---|
| `face` | `'OK'` | `boolean` | `is_ok()` |
| `movement_test` | `'OK'` | `"OK"/"!OK"` | `is_ok()` |
| `front/back_country_check`, `_type_check` | `'OK'` | `boolean` | `is_ok()` |
| `front_isExpired` | `'OK'` = check OK | `boolean` (`true` = expirado) | `is_expired_ok()` — **inverso** |
| `codigo_barras` | `'OK'` | `string \| null` | `is_truthy()` |
| `failed`, `failed_back`, `failed_front` | `'OK'/'!OK'` | no se envían | sin cambio (`None` → no falla) |
| `nombres/apellidos/documento` | `'NULL'` | `''` / ausente | `norm_str()` → deja la lógica de la línea 1081 intacta |

Esto además **arregla H3** (standalone responde 500 hoy con la SPA actual) sin romper
a ningún caller legacy que aún mande form‑data.

---

## 9. Tests

Estilo del repo: `unittest` + mocks de `controlador_db` (ver `tests/test_type3_recortes.py`).

| Archivo | Cubre |
|---|---|
| `tests/test_document_config.py` | 200 por `hash` y por `efirmaId`; sin fila → defaults; sin params → 400; sin JWT → 401; shape exacto. |
| `tests/test_location_guard.py` | haversine, `LOCATION_REQUIRED` (ausente/malformado), `LOCATION_MISMATCH` por accuracy y por distancia, centro ausente, `LOCATION_UNAVAILABLE`. |
| `tests/test_ip_intel.py` | parseo del provider, `PROXY_DETECTED` vs `VPN_DETECTED`, **fail‑open** ante timeout/5xx/sin key, cache TTL, `client_ip()` con XFF. |
| `tests/test_standalone_json.py` | fixture JSON con booleanos ⇒ mismo resultado que el form legacy; y fixture form legacy ⇒ idéntico (regresión). |
| `tests/test_signature_security_errors.py` | 5 codes × status × body en ambos POST; `block_on_vpn=false` no bloquea. |

### Verificación

```bash
python -m unittest discover -s tests -v
python -m compileall blueprints utilities
python -m unittest tests.test_type3_recortes tests.test_process_revalidation -v   # regresión
```

---

## 10. Despliegue e integración

1. `ALTER` de las cinco columnas en `usuarios.entidades`, en BD **COL** y **HND**
   (lo aplica el DBA de ese schema; el microservicio no toca el esquema).
2. Añadir `IP_INTEL_API_KEY` (+ resto de env) al entorno de testing.
3. Activar con `UPDATE usuarios.entidades SET validar_ubicacion = 1, ...`
   en una entidad de prueba.
4. Verificar en staging que nginx inyecta `X-Forwarded-For`
   (si no, `client_ip()` cae a `info.ip` y queda logueado).
5. Aviso al frontend: la ruta es definitiva
   `GET /validacion-back/validation/document-config` → solo quitar el comentario TODO de `urls.ts`.

---

## 11. Criterios de aceptación

1. `document-config` devuelve ambos flags según la entidad del documento.
2. Firma sin `location` siendo obligatoria → `400 LOCATION_REQUIRED`.
3. Firma con VPN y `bloquear_vpn=1` → `403 VPN_DETECTED`;
   con `bloquear_vpn=0` → procesa normalmente.
4. Coordenadas fuera del radio/centro → `403 LOCATION_MISMATCH`.
5. Todos los errores nuevos cumplen `{ error: { code, message } }`.
6. Los flujos existentes (type‑3 y standalone) siguen comportándose igual
   con payloads legados form‑data.

---

## 12. Riesgos y pendientes

- **H3/H4 es el mayor riesgo**: tocar ~45 lecturas de `standalone`.
  Mitigado con la tabla de normalización + tests de regresión dual (JSON y form).
- `tests/` está en `.gitignore` → los tests nuevos **no se commitean**.
  *Pendiente de decisión: ¿sacarlo del gitignore para que viajen en el repo?*
- `usuarios.entidades` es del schema compartido con firma/portal: el `ALTER` con
  columnas `NOT NULL` rompe cualquier `INSERT INTO usuarios.entidades` que no
  liste columnas. Revisar con el DBA antes de aplicar.
- Cache de IP por worker (3 workers) → como máximo 3 llamadas por IP/TTL.
- Sin key de `ipapi.is` el guard de VPN queda en fail‑open silencioso (solo log):
  hay que generar la key antes de dar por entregado el criterio de aceptación nº 3.

---

## 13. Pasos de implementación (orden)

1. Columnas en `usuarios.entidades` (sin archivo de migración en el repo: se aplican a mano).
2. `utilities/api_errors.py` + `utilities/request_fields.py`.
3. `utilities/document_config.py` + endpoint `GET /validation/document-config`.
4. `utilities/location_guard.py`.
5. `utilities/ip_intel.py`.
6. `utilities/signature_security.py` (orquestador).
7. Integrar el guard en `/validation/type-3`.
8. Portar `/validation/standalone` a lector dual + normalización + guard.
9. Tests nuevos + suite de regresión.
10. README: columnas de la entidad + variables de entorno.
